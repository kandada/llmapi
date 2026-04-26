from fastapi import Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
from sqlalchemy.orm import Session
import httpx
import json
import time

from database import get_session
from services.user_service import UserService
from services.token_service import TokenService
from services.channel_service import ChannelService
from services.log_service import LogService
from services.cache_service import cache_service
from billing.calculator import RelayService as BillingRelayService, PreconsumeQuotaService
from middleware.auth import AuthContext, require_user, validate_token_model_permission
from middleware.distributor import Distributor
from relay.adaptor import AdaptorFactory
from schemas.request import APIResponse
from config import config


class RelayController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.user_service = UserService(db)
        self.token_service = TokenService(db)
        self.channel_service = ChannelService(db)
        self.log_service = LogService(db)
        self.billing_service = BillingRelayService(db)
        self.preconsume_service = PreconsumeQuotaService(db)

    def _estimate_prompt_tokens(self, body: dict, model: str) -> int:
        messages = body.get("messages", [])
        content = ""
        for msg in messages:
            if isinstance(msg, dict):
                content += msg.get("content", "")
            elif hasattr(msg, "content"):
                content += msg.content
        return len(content) // 4

    async def chat_completions(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "")
        if not model:
            raise HTTPException(status_code=400, detail="Model is required")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        user_group = ctx.user.group or "default"
        token_channel_group = ctx.token_channel_group or ""
        is_stream = body.get("stream", False)
        output_format = body.get("response_format", request.headers.get("X-Response-Format", "openai"))
        body.pop("response_format", None)

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, token_channel_group)

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        meta = {
            "model": mapped_model,
            "api_key": channel.key,
            "base_url": base_url,
            "channel_type": channel.type,
            "channel_id": channel.id,
            "llm_gateway": getattr(channel, 'llm_gateway', 'openai'),
            "config": json.loads(channel.config) if channel.config else {},
            "output_format": output_format,
        }

        adaptor = AdaptorFactory.get_adaptor(channel.type, meta["llm_gateway"])
        converted_request = await adaptor.convert_request(body, meta)

        start_time = time.time()
        retry_times = config.RetryTimes
        last_error = None
        tried_channel_ids = {channel.id}

        preconsumed_quota = 0
        if ctx.token:
            prompt_tokens = self._estimate_prompt_tokens(body, model)
            max_tokens = body.get("max_tokens", 0)
            success, preconsumed_quota = self.preconsume_service.preconsume(
                ctx.token_id, ctx.user_id, model, prompt_tokens, max_tokens, user_group, channel.type
            )
            if not success:
                raise HTTPException(status_code=403, detail="Insufficient quota")

        for i in range(retry_times + 1):
            try:
                if i > 0:
                    channel = distributor.select_channel(user_group, model, token_channel_group, ignore_priority=True)
                    if not channel:
                        break
                    if channel.id in tried_channel_ids:
                        continue
                    tried_channel_ids.add(channel.id)
                    mapped_model = distributor.map_model(channel, model)
                    base_url = distributor.get_base_url(channel)
                    meta["model"] = mapped_model
                    meta["base_url"] = base_url
                    meta["channel_id"] = channel.id
                    converted_request = await adaptor.convert_request(body, meta)

                if is_stream:
                    return await self._handle_stream(
                        adaptor, converted_request, meta, ctx, channel, mapped_model, start_time, user_group, preconsumed_quota
                    )
                else:
                    return await self._handle_normal(
                        adaptor, converted_request, meta, ctx, channel, mapped_model, start_time, user_group, preconsumed_quota
                    )

            except httpx.TimeoutException:
                last_error = "Request timeout"
                if i < retry_times:
                    self._record_channel_error(channel.id, "timeout")
                    continue
                break
            except RetryableError as e:
                last_error = e.message
                if i < retry_times:
                    self._record_channel_error(channel.id, e.message)
                    continue
                break
            except Exception as e:
                last_error = str(e)
                if i < retry_times:
                    self._record_channel_error(channel.id, str(e))
                    continue
                break

        if preconsumed_quota > 0:
            self.preconsume_service.return_preconsumed(ctx.token_id, ctx.user_id, preconsumed_quota)

        raise HTTPException(status_code=503, detail=f"Request failed after {retry_times + 1} attempts: {last_error}")

    async def _handle_normal(
            self, adaptor, converted_request, meta, ctx, channel, mapped_model, start_time, user_group, preconsumed_quota=0
        ):
            skip_quota = preconsumed_quota > 0
            response, is_success = await self.billing_service._relay_normal(
                adaptor, converted_request, meta,
                ctx.user_id, ctx.token_id,
                ctx.token.name if ctx.token else "",
                mapped_model, channel.type, user_group,
                skip_quota_deduction=skip_quota
            )

            elapsed_time = int((time.time() - start_time) * 1000)

            if not is_success:
                self._record_channel_error(channel.id, f"status_{response.status_code}")
                if preconsumed_quota > 0:
                    self.preconsume_service.return_preconsumed(ctx.token_id, ctx.user_id, preconsumed_quota)

                status_code = response.status_code
                if status_code == 429 or status_code >= 500:
                    raise RetryableError(status_code, f"status_{status_code}")

                return JSONResponse(
                    status_code=status_code,
                    content=response.json() if hasattr(response, 'json') else {"error": {"message": str(response), "type": "upstream_error"}},
                )

            await self._record_channel_success(channel.id)

            if preconsumed_quota > 0:
                data = response.json()
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                actual_quota = self.billing_service.calculate_quota(mapped_model, prompt_tokens, completion_tokens, user_group, channel.type)
                self.preconsume_service.post_consume(ctx.token_id, ctx.user_id, actual_quota, preconsumed_quota)
                data = await adaptor.convert_response(data, meta.get("output_format", "openai"))
                return JSONResponse(content=data)

            data = response.json()
            data = await adaptor.convert_response(data, meta.get("output_format", "openai"))

            return JSONResponse(content=data)

    async def _handle_stream(
            self, adaptor, converted_request, meta, ctx, channel, mapped_model, start_time, user_group, preconsumed_quota=0
        ):
            skip_quota = preconsumed_quota > 0
            response, is_success = await self.billing_service._relay_stream(
                adaptor, converted_request, meta,
                ctx.user_id, ctx.token_id,
                ctx.token.name if ctx.token else "",
                mapped_model, channel.type, user_group,
                skip_quota_deduction=skip_quota
            )

            first_chunk = True
            error_occurred = False
            completion_tokens = 0
            prompt_tokens = 0

            async def generate():
                nonlocal first_chunk, error_occurred, completion_tokens, prompt_tokens
                try:
                    async for chunk in response:
                        if first_chunk and chunk.startswith("data: "):
                            data_str = chunk[6:]
                            if not data_str.startswith("[DONE]"):
                                try:
                                    data = json.loads(data_str)
                                    if data.get("error"):
                                        error_occurred = True
                                        self._record_channel_error(channel.id, data["error"].get("message", "stream_error"))
                                except:
                                    pass
                            first_chunk = False

                        if chunk.startswith("data: "):
                            data_str = chunk[6:]
                            if data_str == "[DONE]\n\n":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("error"):
                                    error_occurred = True
                                    self._record_channel_error(channel.id, data["error"].get("message", "stream_error"))
                                if "usage" in data:
                                    prompt_tokens = data["usage"].get("prompt_tokens", 0)
                                    completion_tokens = data["usage"].get("completion_tokens", 0)
                            except:
                                pass
                        yield chunk

                    if not error_occurred:
                        self._record_channel_success(channel.id)
                        if preconsumed_quota > 0:
                            actual_quota = self.billing_service.calculate_quota(mapped_model, prompt_tokens, completion_tokens, user_group, channel.type)
                            self.preconsume_service.post_consume(ctx.token_id, ctx.user_id, actual_quota, preconsumed_quota)
                    elif preconsumed_quota > 0:
                        self.preconsume_service.return_preconsumed(ctx.token_id, ctx.user_id, preconsumed_quota)

                except Exception as e:
                    error_occurred = True
                    if preconsumed_quota > 0:
                        self.preconsume_service.return_preconsumed(ctx.token_id, ctx.user_id, preconsumed_quota)
                    self._record_channel_error(channel.id, str(e))
                    import json
                    error_json = json.dumps({"error": {"message": str(e), "type": "upstream_error"}})
                    yield f"data: {error_json}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")

    def _record_channel_success(self, channel_id: int):
        cache_key = f"channel_success:{channel_id}"
        cache_service.set(cache_key, True, ttl=60)

    def _record_channel_error(self, channel_id: int, error_msg: str):
        cache_key = f"channel_error:{channel_id}"
        errors = cache_service.get(cache_key) or []
        errors.append(error_msg)
        if len(errors) > 10:
            errors = errors[-10:]
        cache_service.set(cache_key, errors, ttl=60)

        if len(errors) >= 5:
            recent_errors = errors[-5:]
            error_counts = {}
            for err in recent_errors:
                error_counts[err] = error_counts.get(err, 0) + 1
            max_count = max(error_counts.values())
            if max_count >= 4:
                self.channel_service.disable_channel(channel_id)

    async def completions(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        body["model"] = body.get("model", "gpt-3.5-turbo")
        if "messages" not in body and "prompt" in body:
            prompt = body.pop("prompt")
            body["messages"] = [{"role": "user", "content": prompt}]

        return await self.chat_completions(request, ctx)

    async def embeddings(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "text-embedding-ada-002")
        input_texts = body.get("input", [])

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        if isinstance(input_texts, str):
            input_texts = [input_texts]

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        embeddings_data = []
        for text in input_texts:
            embed_request = {
                "model": mapped_model,
                "input": text,
            }

            try:
                meta_with_model = {
                    "model": mapped_model,
                    "api_key": channel.key,
                    "base_url": base_url,
                    "config": json.loads(channel.config) if channel.config else {},
                }
                url = adaptor.get_request_url(meta_with_model, "/v1/embeddings")
                headers = adaptor.get_headers(meta_with_model)

                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, headers=headers, json=embed_request)

                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("data", [{}])[0].get("embedding", [])
                    embeddings_data.append({"object": "embedding", "embedding": embedding, "index": len(embeddings_data)})

            except Exception as e:
                print(f"Embedding error: {e}")

        return JSONResponse(content={
            "object": "list",
            "data": embeddings_data,
            "model": model,
        })

    async def images_generations(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "dall-e-3")
        prompt = body.get("prompt", "")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        image_request = {
            "model": mapped_model,
            "prompt": prompt,
        }

        if "n" in body:
            image_request["n"] = body["n"]
        if "size" in body:
            image_request["size"] = body["size"]
        if "quality" in body:
            image_request["quality"] = body["quality"]

        try:
            meta = {
                "model": mapped_model,
                "api_key": channel.key,
                "base_url": base_url,
                "config": json.loads(channel.config) if channel.config else {},
            }

            url = adaptor.get_request_url(meta, "/v1/images/generations")
            headers = adaptor.get_headers(meta)

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=image_request)

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": response.text}},
                )

            data = response.json()
            return JSONResponse(content=data)

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

    async def audio_transcriptions(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            form_data = await request.form()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        file = form_data.get("file")
        model = form_data.get("model", "whisper-1")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        if not file:
            raise HTTPException(status_code=400, detail="File is required")

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        try:
            meta = {
                "model": mapped_model,
                "api_key": channel.key,
                "base_url": base_url,
                "config": json.loads(channel.config) if channel.config else {},
            }

            url = adaptor.get_request_url(meta, "/v1/audio/transcriptions")
            headers = adaptor.get_headers(meta)

            file_content = await file.read()

            async with httpx.AsyncClient(timeout=120.0) as client:
                files = {"file": (file.filename, file_content, file.content_type)}
                response = await client.post(url, headers=headers, files=files, data={"model": mapped_model})

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": {"message": response.text}},
                )

            data = response.json()
            return JSONResponse(content=data)

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

    async def audio_translations(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        return await self.audio_transcriptions(request, ctx)

    async def audio_speech(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "tts-1")
        input_text = body.get("input", "")
        voice = body.get("voice", "alloy")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        if not input_text:
            raise HTTPException(status_code=400, detail="Input text is required")

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        try:
            meta = {
                "model": mapped_model,
                "api_key": channel.key,
                "base_url": base_url,
                "config": json.loads(channel.config) if channel.config else {},
            }

            url = adaptor.get_request_url(meta, "/v1/audio/speech")
            headers = adaptor.get_headers(meta)

            speech_request = {
                "model": mapped_model,
                "input": input_text,
                "voice": voice,
            }

            if "response_format" in body:
                speech_request["response_format"] = body["response_format"]
            if "speed" in body:
                speech_request["speed"] = body["speed"]

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=speech_request)

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": {"message": response.text}},
                )

            return Response(content=response.content, media_type="audio/mpeg")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

    async def list_models(self, ctx: AuthContext = Depends(require_user)) -> JSONResponse:
        models = []
        channels = self.channel_service.get_all_enabled_channels()

        for channel in channels:
            if channel.models:
                channel_models = [m.strip() for m in channel.models.split(",") if m.strip()]
                for m in channel_models:
                    if m not in models:
                        models.append(m)

        if not models:
            models = ["gpt-4", "gpt-3.5-turbo"]

        return JSONResponse(content={
            "object": "list",
            "data": [{"id": m, "object": "model"} for m in models],
        })

    async def retrieve_model(self, model: str, ctx: AuthContext = Depends(require_user)) -> JSONResponse:
        return JSONResponse(content={
            "id": model,
            "object": "model",
            "owned_by": "openai",
        })

    async def edits(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "gpt-3.5-turbo")
        input_text = body.get("input", "")
        instruction = body.get("instruction", "")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        if not input_text:
            raise HTTPException(status_code=400, detail="Input text is required")

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        try:
            meta = {
                "model": mapped_model,
                "api_key": channel.key,
                "base_url": base_url,
                "config": json.loads(channel.config) if channel.config else {},
            }

            url = adaptor.get_request_url(meta, "/v1/edits")
            headers = adaptor.get_headers(meta)

            edit_request = {
                "model": mapped_model,
                "input": input_text,
                "instruction": instruction,
            }

            if "temperature" in body:
                edit_request["temperature"] = body["temperature"]
            if "top_p" in body:
                edit_request["top_p"] = body["top_p"]
            if "n" in body:
                edit_request["n"] = body["n"]

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=edit_request)

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": response.text}},
                )

            data = response.json()
            return JSONResponse(content=data)

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

    async def moderations(self, request: Request, ctx: AuthContext = Depends(require_user)) -> Response:
        try:
            body = await request.json()
        except:
            raise HTTPException(status_code=400, detail="Invalid request body")

        model = body.get("model", "text-moderation-latest")
        input_text = body.get("input", "")

        if ctx.token:
            model_error = validate_token_model_permission(ctx.token, model)
            if model_error:
                raise HTTPException(status_code=403, detail=model_error)

        if not input_text:
            raise HTTPException(status_code=400, detail="Input text is required")

        user_group = ctx.user.group or "default"

        distributor = Distributor(self.db)
        channel = distributor.select_channel(user_group, model, "")

        if not channel:
            raise HTTPException(status_code=503, detail=f"No available channel for model {model}")

        mapped_model = distributor.map_model(channel, model)
        base_url = distributor.get_base_url(channel)

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        try:
            meta = {
                "model": mapped_model,
                "api_key": channel.key,
                "base_url": base_url,
                "config": json.loads(channel.config) if channel.config else {},
            }

            url = adaptor.get_request_url(meta, "/v1/moderations")
            headers = adaptor.get_headers(meta)

            moderation_request = {
                "model": mapped_model,
                "input": input_text,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=moderation_request)

            if response.status_code != 200:
                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": {"message": response.text}},
                )

            data = response.json()
            return JSONResponse(content=data)

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")

class RetryableError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

    def __str__(self):
        return f"[{self.status_code}] {self.message}"
