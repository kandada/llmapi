from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator, TYPE_CHECKING
import httpx
import json
import time

from models.channel import ChannelType

if TYPE_CHECKING:
    from models.channel import Channel


class BaseAdaptor(ABC):
    def __init__(self):
        self.channel_type = 0

    @abstractmethod
    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        pass

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    @abstractmethod
    async def get_models(self) -> list:
        pass

    def get_base_url(self, meta: Dict[str, Any]) -> str:
        return meta.get("base_url", "")

    def get_request_url(self, meta: Dict[str, Any], path: str = "/v1/chat/completions") -> str:
        base_url = self.get_base_url(meta)
        if not base_url:
            base_url = "https://api.openai.com"
        return f"{base_url.rstrip('/')}{path}"

    def get_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if meta.get("api_key"):
            headers["Authorization"] = f"Bearer {meta['api_key']}"
        return headers

    async def do_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: bytes = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if method == "GET":
                return await client.get(url, headers=headers)
            elif method == "POST":
                return await client.post(url, headers=headers, content=body)
            elif method == "DELETE":
                return await client.delete(url, headers=headers)
            else:
                return await client.get(url, headers=headers)

    async def relay(
        self,
        request: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> httpx.Response:
        url = self.get_request_url(meta)
        headers = self.get_headers(meta)
        body = json.dumps(request).encode()

        response = await self.do_request("POST", url, headers, body)
        return response

    async def relay_stream(
        self,
        request: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        url = self.get_request_url(meta)
        headers = self.get_headers(meta)
        headers["Accept"] = "text/event-stream"
        body = json.dumps(request).encode()

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, content=body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f'data: {{"error": {{"message": "{error_text.decode()}", "type": "upstream_error"}}}}'
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            yield f"data: {data}\n\n"
                        else:
                            yield f"{line}\n\n"

    async def handle_stream(self, response: httpx.Response, meta: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async for line in response.aiter_lines():
            if line:
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield f"data: {data}\n\n"
                else:
                    yield f"{line}\n\n"

    def get_model_list(self) -> list:
        return []

    def convert_stream_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data


class AdaptorFactory:
    _adaptors: Dict[int, type] = {}
    _gateway_adaptors: Dict[str, type] = {}

    @classmethod
    def register(cls, channel_type: int, adaptor_class: type):
        cls._adaptors[channel_type] = adaptor_class

    @classmethod
    def register_gateway(cls, gateway: str, adaptor_class: type):
        cls._gateway_adaptors[gateway] = adaptor_class

    @classmethod
    def get_adaptor(cls, channel_type: int, llm_gateway: str = "openai") -> BaseAdaptor:
        if llm_gateway and llm_gateway != "openai":
            gateway_adaptor_cls = cls._gateway_adaptors.get(llm_gateway)
            if gateway_adaptor_cls is not None:
                return gateway_adaptor_cls()

        adaptor_class = cls._adaptors.get(channel_type)
        if adaptor_class is None:
            adaptor_class = cls._adaptors.get(ChannelType.OPENAI, OpenAIAdaptor)
        return adaptor_class()

    @classmethod
    def _get_gateway_adaptor(cls, llm_gateway: str) -> Optional[type]:
        if llm_gateway and llm_gateway != "openai" and llm_gateway in cls._gateway_adaptors:
            return cls._gateway_adaptors.get(llm_gateway)
        return None

    @classmethod
    def get_all_adaptors(cls) -> Dict[int, BaseAdaptor]:
        return {ct: cls.get_adaptor(ct) for ct in cls._adaptors.keys()}


class OpenAIAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.OPENAI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ]


class AzureAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.AZURE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return []

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or ""
        config = meta.get("config", {})
        api_version = config.get("api_version", "2024-02-01")
        model = meta.get("model", "").replace(".", "")
        return f"{base_url.rstrip('/')}/openai/deployments/{model}/chat/completions?api-version={api_version}"

    def get_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": meta.get("api_key", ""),
        }


class AnthropicAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.ANTHROPIC

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        anthropic_request = {
            "model": meta.get("model", ""),
            "max_tokens": request.get("max_tokens", 4096),
            "system": request.get("system", ""),
            "messages": await self._convert_messages(request.get("messages", [])),
        }

        if "temperature" in request:
            anthropic_request["temperature"] = request["temperature"]
        if "top_p" in request:
            anthropic_request["top_p"] = request["top_p"]
        if "tools" in request:
            anthropic_request["tools"] = self._convert_tools(request["tools"])

        thinking = request.get("thinking", None)
        if thinking:
            anthropic_request["thinking"] = thinking

        return anthropic_request

    async def _convert_messages(self, messages: list) -> list:
        converted = []
        for msg in messages:
            if isinstance(msg, str):
                converted.append({"role": "user", "content": msg})
                continue

            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                continue

            claude_msg = {"role": self._convert_role(role), "content": []}

            if isinstance(content, str):
                claude_msg["content"].append({"type": "text", "text": content})
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            claude_msg["content"].append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            claude_msg["content"].append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": item.get("image_url", {}).get("detail", "image/jpeg"),
                                    "data": item.get("image_url", {}).get("url", "").split(",")[-1]
                                }
                            })
                        elif item.get("type") == "tool_use":
                            claude_msg["content"].append({
                                "type": "tool_use",
                                "id": item.get("id", ""),
                                "name": item.get("name", ""),
                                "input": item.get("function", {}).get("arguments", "{}")
                            })
                        elif item.get("type") == "tool_result":
                            claude_msg["content"].append({
                                "type": "tool_result",
                                "tool_use_id": item.get("tool_use_id", ""),
                                "content": item.get("content", "")
                            })

            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        claude_msg["content"].append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": func.get("arguments", "{}")
                        })

            converted.append(claude_msg)

        return converted

    def _convert_role(self, role: str) -> str:
        if role == "assistant":
            return "assistant"
        elif role == "tool":
            return "user"
        return role

    def _convert_tools(self, tools: list) -> list:
        converted = []
        for tool in tools:
            if isinstance(tool, dict):
                func = tool.get("function", {})
                params = func.get("parameters", {})
                if params.get("type") == "object" and not params.get("properties"):
                    input_schema = {"type": "object"}
                else:
                    input_schema = params
                converted.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": input_schema
                })
        return converted

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        if output_format == "anthropic":
            return self._convert_to_anthropic_response(response)

        content_blocks = response.get("content", [])
        text_content = ""
        tool_calls = []
        thinking_content = response.get("thinking", "")

        for block in content_blocks:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    text_content = block.get("text", "")
                elif block_type == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": block.get("input", "{}") if isinstance(block.get("input"), str) else json.dumps(block.get("input", {}))
                        }
                    })

        stop_reason = response.get("stop_reason", "stop")
        finish_reason = self._convert_stop_reason(stop_reason)

        openai_response = {
            "id": f"chatcmpl-{response.get('id', '')}",
            "object": "chat.completion",
            "created": response.get("created", 0),
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text_content,
                    "tool_calls": tool_calls if tool_calls else None,
                },
                "finish_reason": finish_reason,
            }],
            "usage": {
                "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("output_tokens", 0),
                "total_tokens": response.get("usage", {}).get("input_tokens", 0) + response.get("usage", {}).get("output_tokens", 0),
            },
        }

        if thinking_content:
            openai_response["choices"][0]["message"]["thinking"] = thinking_content

        return openai_response

    def _convert_to_anthropic_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        content_blocks = response.get("content", [])
        anthropic_content = []

        for block in content_blocks:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "text":
                    anthropic_content.append({
                        "type": "text",
                        "text": block.get("text", "")
                    })
                elif block_type == "tool_use":
                    anthropic_content.append({
                        "type": "tool_use",
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {})
                    })

        thinking = response.get("thinking", "")
        if thinking:
            anthropic_content.insert(0, {
                "type": "thinking",
                "thinking": thinking,
                "signature": response.get("signature", "")
            })

        return {
            "type": "message",
            "id": response.get("id", ""),
            "role": "assistant",
            "model": response.get("model", ""),
            "content": anthropic_content,
            "stop_reason": response.get("stop_reason", "end_turn"),
            "usage": {
                "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                "output_tokens": response.get("usage", {}).get("output_tokens", 0),
            }
        }

    def _convert_stop_reason(self, reason: str) -> str:
        if reason == "end_turn":
            return "stop"
        elif reason == "stop_sequence":
            return "stop"
        elif reason == "max_tokens":
            return "length"
        elif reason == "tool_use":
            return "tool_calls"
        return reason

    async def convert_stream_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = data.get("type", "")

        if event_type == "message_start":
            return None
        elif event_type == "content_block_start":
            block = data.get("content_block", {})
            if block.get("type") == "thinking":
                return {
                    "type": "content_block_delta",
                    "index": data.get("index", 0),
                    "delta": {"type": "thinking", "thinking": ""}
                }
            return None
        elif event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                return {
                    "index": data.get("index", 0),
                    "delta": {"role": "assistant", "content": delta.get("text", "")},
                    "finish_reason": None
                }
            elif delta_type == "thinking_delta":
                return {
                    "index": data.get("index", 0),
                    "delta": {"type": "thinking", "thinking": delta.get("thinking", "")},
                    "finish_reason": None
                }
        elif event_type == "message_delta":
            delta = data.get("delta", {})
            usage = data.get("usage", {})
            return {
                "index": data.get("index", 0),
                "delta": {},
                "finish_reason": self._convert_stop_reason(delta.get("stop_reason", "")),
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                }
            }

        return None

    async def convert_stream_chunk(self, data: Dict[str, Any], output_format: str = "openai") -> Optional[Dict[str, Any]]:
        if output_format == "anthropic":
            return self._convert_stream_to_anthropic(data)

        event_type = data.get("type", "")

        if event_type == "message_start":
            msg = data.get("message", {})
            return {
                "id": f"chatcmpl-{msg.get('id', '')}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": msg.get("model", ""),
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant"},
                    "finish_reason": None
                }]
            }

        elif event_type == "content_block_start":
            block = data.get("content_block", {})
            block_type = block.get("type", "")
            if block_type == "thinking":
                return {
                    "choices": [{
                        "index": data.get("index", 0),
                        "delta": {"type": "thinking", "thinking": ""},
                        "finish_reason": None
                    }]
                }
            elif block_type == "text":
                return None

        elif event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type", "")
            index = data.get("index", 0)

            if delta_type == "text_delta":
                return {
                    "choices": [{
                        "index": index,
                        "delta": {"content": delta.get("text", "")},
                        "finish_reason": None
                    }]
                }
            elif delta_type == "thinking_delta":
                return {
                    "choices": [{
                        "index": index,
                        "delta": {"type": "thinking", "thinking": delta.get("thinking", "")},
                        "finish_reason": None
                    }]
                }
            elif delta_type == "input_json_delta":
                return {
                    "choices": [{
                        "index": index,
                        "delta": {"content": ""},
                        "finish_reason": None
                    }]
                }

        elif event_type == "message_delta":
            delta = data.get("delta", {})
            usage = data.get("usage", {})
            stop_reason = delta.get("stop_reason", "")

            return {
                "choices": [{
                    "index": data.get("index", 0),
                    "delta": {},
                    "finish_reason": self._convert_stop_reason(stop_reason) if stop_reason else None
                }],
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                }
            }

        elif event_type == "error":
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return {
                "error": {
                    "message": error_msg,
                    "type": "upstream_error"
                }
            }

        return None

    def _convert_stream_to_anthropic(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_type = data.get("type", "")

        if event_type == "message_start":
            msg = data.get("message", {})
            return {
                "type": "message_start",
                "message": {
                    "id": msg.get("id", ""),
                    "type": "message",
                    "role": "assistant",
                    "model": msg.get("model", ""),
                    "content": [],
                    "stop_reason": None
                }
            }

        elif event_type == "content_block_start":
            block = data.get("content_block", {})
            block_type = block.get("type", "")
            index = data.get("index", 0)

            if block_type == "thinking":
                return {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {
                        "type": "thinking",
                        "thinking": "",
                        "signature": ""
                    }
                }
            elif block_type == "text":
                return {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {
                        "type": "text",
                        "text": ""
                    }
                }

        elif event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type", "")
            index = data.get("index", 0)

            if delta_type == "text_delta":
                return {
                    "type": "content_block_delta",
                    "index": index,
                    "content_block": {
                        "type": "text_delta",
                        "text": delta.get("text", "")
                    }
                }
            elif delta_type == "thinking_delta":
                return {
                    "type": "content_block_delta",
                    "index": index,
                    "content_block": {
                        "type": "thinking_delta",
                        "thinking": delta.get("thinking", "")
                    }
                }

        elif event_type == "message_delta":
            delta = data.get("delta", {})
            usage = data.get("usage", {})
            stop_reason = delta.get("stop_reason", "")

            return {
                "type": "message_delta",
                "usage": {
                    "output_tokens": usage.get("output_tokens", 0)
                },
                "delta": {
                    "stop_reason": stop_reason
                }
            }

        elif event_type == "error":
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return {
                "type": "error",
                "error": {
                    "type": "error",
                    "message": error_msg
                }
            }

        return None

    async def get_models(self) -> list:
        return [
            "claude-3-5-sonnet-latest",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-latest",
            "claude-3-haiku-latest",
        ]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.anthropic.com"
        return f"{base_url.rstrip('/')}/v1/messages"

    def get_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": meta.get("api_key", ""),
            "anthropic-version": "2023-06-01",
        }

        beta = meta.get("config", {}).get("anthropic_beta", "messages-2023-12-15")
        if beta:
            headers["anthropic-beta"] = beta

        return headers

    async def relay_stream(
        self,
        request: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        url = self.get_request_url(meta)
        headers = self.get_headers(meta)
        headers["Accept"] = "text/event-stream"
        body = json.dumps(request).encode()
        output_format = meta.get("output_format", "openai")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, content=body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f'data: {{"error": {{"message": "{error_text.decode()}", "type": "upstream_error"}}}}\n\n'
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            converted = await self.convert_stream_chunk(data, output_format)
                            if converted:
                                if output_format == "anthropic":
                                    yield f"data: {json.dumps(converted)}\n\n"
                                else:
                                    yield f"data: {json.dumps(converted)}\n\n"
                        except json.JSONDecodeError:
                            pass
                    else:
                        yield f"{line}\n\n"


class DeepSeekAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.DEEPSEEK

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["deepseek-chat", "deepseek-reasoner"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.deepseek.com/v1"
        base_url = base_url.rstrip('/')

        if path:
            if base_url.endswith('/v1') and path.startswith('/v1'):
                base_url = base_url[:-3]
            elif not base_url.endswith('/v1') and not path.startswith('/v1'):
                base_url = base_url + '/v1'
            return f"{base_url}{path}"

        if base_url.endswith('/v1'):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"


class MoonshotAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.MOONSHOT

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.moonshot.cn/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class MiniMaxAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.MINIMAX

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        content_text = ""
        if response.get("content"):
            for item in response["content"]:
                if item.get("type") == "text":
                    content_text = item.get("text", "")
                    break

        openai_response = {
            "id": response.get("id", ""),
            "object": "chat.completion",
            "created": response.get("created", 0),
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content_text,
                },
                "finish_reason": response.get("stop_reason", "stop"),
            }],
            "usage": response.get("usage", {}),
        }
        return openai_response

    async def get_models(self) -> list:
        return ["MiniMax-M2.7", "MiniMax-M2.5", "abab6.5-chat"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.minimax.chat/v1"
        base_url = base_url.rstrip('/')
        if base_url.endswith("/anthropic"):
            return f"{base_url}/v1/messages"
        return f"{base_url}/chat/completions"


class GeminiAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.GEMINI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        contents = []
        for msg in request.get("messages", []):
            role = "user" if msg.get("role") == "user" else "model"
            parts = [{"text": msg.get("content", "")}]
            contents.append({"role": role, "parts": parts})

        gemini_request = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.get("temperature", 0.9),
                "maxOutputTokens": request.get("max_tokens", 2048),
            }
        }

        if request.get("system"):
            system_instruction = {"parts": [{"text": request["system"]}]}
            gemini_request["systemInstruction"] = system_instruction

        return gemini_request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        candidates = response.get("candidates", [])
        content = ""
        if candidates and candidates[0].get("content"):
            parts = candidates[0]["content"].get("parts", [])
            content = "".join([p.get("text", "") for p in parts])

        openai_response = {
            "id": f"gemini-{response.get('createTime', '')}",
            "object": "chat.completion",
            "created": response.get("createTime", 0),
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        }
        return openai_response

    async def get_models(self) -> list:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://generativelanguage.googleapis.com/v1beta"
        model = meta.get("model", "gemini-1.5-flash")
        return f"{base_url.rstrip('/')}/models/{model}:generateContent"

    def get_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
        }


class BaiduAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.BAIDU

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        for msg in request.get("messages", []):
            role = msg.get("role", "user")
            if role == "assistant":
                role = "assistant"
            elif role == "system":
                role = "system"
            else:
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})

        return {
            "messages": messages,
            "stream": request.get("stream", False),
        }

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["ernie-4.0", "ernie-3.5", "ernie-bot"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://aip.baidubce.com"
        return f"{base_url.rstrip('/')}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"


class AliAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.ALI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        for msg in request.get("messages", []):
            role = msg.get("role", "user")
            if role == "assistant":
                role = "assistant"
            elif role == "system":
                role = "system"
            else:
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})

        return {
            "messages": messages,
            "stream": request.get("stream", False),
        }

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["qwen-turbo", "qwen-plus", "qwen-max"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://dashscope.aliyuncs.com/api/v1"
        return f"{base_url.rstrip('/')}/services/aigc/text-generation/generation"


class ZhipuAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.ZHIPU

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        for msg in request.get("messages", []):
            role = msg.get("role", "user")
            if role == "assistant":
                role = "assistant"
            elif role == "system":
                role = "system"
            else:
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})

        return {
            "messages": messages,
            "stream": request.get("stream", False),
        }

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["glm-4", "glm-3-turbo"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://open.bigmodel.cn/api/paas/v4"
        return f"{base_url.rstrip('/')}/chat/completions"


class TencentAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.TENCENT

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["hunyuan"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.hunyuan.cloud.tencent.com"
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class OllamaAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.OLLAMA

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        messages = request.get("messages", [])
        prompt = "\n".join([f"{msg.get('role')}: {msg.get('content')}" for msg in messages])

        return {
            "model": meta.get("model", "llama2"),
            "prompt": prompt,
            "stream": request.get("stream", False),
        }

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return {
            "id": f"ollama-{response.get('model', '')}",
            "object": "chat.completion",
            "created": 0,
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response.get("response", "")},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        }

    async def get_models(self) -> list:
        return ["llama2", "mistral", "codellama"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "http://localhost:11434"
        return f"{base_url.rstrip('/')}/api/generate"


class MistralAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.MISTRAL

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return [
            "open-mistral-7b",
            "open-mixtral-8x7b",
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
        ]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.mistral.ai/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class GroqAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.GROQ

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.groq.com/openai/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class CohereAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.COHERE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["command", "command-r", "command-r-plus"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.cohere.ai/v1"
        return f"{base_url.rstrip('/')}/chat"


class CloudflareAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.CLOUDFLARE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["@cf/meta/llama-3.1-8b-instruct", "@cf/meta/llama-3-70b"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        return f"{base_url.rstrip('/')}/chat"


class DeepLAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.DEEPL

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["deepl-zh", "deepl-en", "deepl-ja"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api-free.deepl.com/v2"
        return f"{base_url.rstrip('/')}/chat"


class TogetherAIAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.TOGETHERAI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["meta-llama/Llama-3-70b-chat", "meta-llama/Llama-3-8b-chat"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.together.ai/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class NovitaAIAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.NOVITA

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["NousResearch/Hermes-3-Llama-3-8B"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.novita.ai/v3"
        return f"{base_url.rstrip('/')}/chat/completions"


class SiliconFlowAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.SILICONFLOW

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["deepseek-ai/DeepSeek-V2.5", "Qwen/Qwen2-7B"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.siliconflow.cn/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class XAIAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.XAI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["grok-beta"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.x.ai/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class AWSClaudeAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.AWSCLAUDE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["anthropic.claude-3-sonnet-20240229-v1", "anthropic.claude-3-5-sonnet-20241022-v1"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        return f"{base_url.rstrip('/')}/chat/completions"


class VertexAIAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.VERTEXAI

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["gemini-1.5-pro", "gemini-1.5-flash"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        return f"{base_url.rstrip('/')}/chat/completions"


class BaiduV2Adaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.BAIDUV2

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["ernie-4.0-8k", "ernie-3.5-8k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://qianfan.baidubce.com/v2"
        return f"{base_url.rstrip('/')}/chat/completions"


class XunfeiV2Adaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.XUNFEIV2

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["SparkDesk-v4.0"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://spark-api.xf-yun.com/v4.0/chat"
        return f"{base_url.rstrip('/')}/chat"


class AliBailianAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.ALIBAILIAN

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["qwen-turbo", "qwen-plus", "qwen-max"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://dashscope.aliyuncs.com/api/v1"
        return f"{base_url.rstrip('/')}/services/aigc/text-generation/generation"


class OpenRouterAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.OPENROUTER

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["openrouter/auto"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://openrouter.ai/api/v1"
        return f"{base_url.rstrip('/')}/chat/completions"


class CozeAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.COZE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["coze-bot"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.coze.cn/v1"
        return f"{base_url.rstrip('/')}/chat"


class ReplicateAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.REPLICATE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["meta/llama-2-7b"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.replicate.com/v1"
        return f"{base_url.rstrip('/')}/chat"


class ProxyAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.PROXY

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return []

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        model = meta.get("model", "")
        return f"{base_url.rstrip('/')}/{model}"


class Ai360Adaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.AI360

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["360GPT_S2_V9"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://ai.360.cn"
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class BaichuanAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.BAICHUAN

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["Baichuan2-Turbo", "Baichuan2-Turbo-192k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.baichuan-ai.com"
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class DoubaoAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.DOUBAO

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["doubao-pro-32k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://ark.cn-beijing.volces.com"
        return f"{base_url.rstrip('/')}/api/v1/chat/completions"


class LingYiWanWuAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.LINGYIWANWU

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["yi-34b-chat-0205", "yi-34b-chat-200k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.lingyiwanwu.com"
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class StepFunAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.STEPFUN

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return ["step-1-8k", "step-1-32k", "step-1-128k"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "") or "https://api.stepfun.com"
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class OpenAICompatibleAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.OPENAICOMPATIBLE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        return request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        return response

    async def get_models(self) -> list:
        return []

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        return f"{base_url.rstrip('/')}/v1/chat/completions"


class GeminiOpenAICompatibleAdaptor(BaseAdaptor):
    def __init__(self):
        super().__init__()
        self.channel_type = ChannelType.GEMINIOPENAICOMPATIBLE

    async def convert_request(self, request: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        contents = []
        for msg in request.get("messages", []):
            role = "user" if msg.get("role") == "user" else "model"
            parts = [{"text": msg.get("content", "")}]
            contents.append({"role": role, "parts": parts})

        gemini_request = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.get("temperature", 0.9),
                "maxOutputTokens": request.get("max_tokens", 2048),
            }
        }

        if request.get("system"):
            system_instruction = {"parts": [{"text": request["system"]}]}
            gemini_request["systemInstruction"] = system_instruction

        return gemini_request

    async def convert_response(self, response: Dict[str, Any], output_format: str = "openai") -> Dict[str, Any]:
        candidates = response.get("candidates", [])
        content = ""
        if candidates and candidates[0].get("content"):
            parts = candidates[0]["content"].get("parts", [])
            content = "".join([p.get("text", "") for p in parts])

        openai_response = {
            "id": f"gemini-{response.get('createTime', '')}",
            "object": "chat.completion",
            "created": response.get("createTime", 0),
            "model": response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        }
        return openai_response

    async def get_models(self) -> list:
        return ["gemini-1.5-pro", "gemini-1.5-flash"]

    def get_request_url(self, meta: Dict[str, Any], path: str = None) -> str:
        base_url = meta.get("base_url", "")
        model = meta.get("model", "gemini-1.5-flash")
        return f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent"

    def get_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
        }


AdaptorFactory.register(ChannelType.OPENAI, OpenAIAdaptor)
AdaptorFactory.register(ChannelType.AZURE, AzureAdaptor)
AdaptorFactory.register(ChannelType.ANTHROPIC, AnthropicAdaptor)
AdaptorFactory.register(ChannelType.DEEPSEEK, DeepSeekAdaptor)
AdaptorFactory.register(ChannelType.MOONSHOT, MoonshotAdaptor)
AdaptorFactory.register(ChannelType.MINIMAX, MiniMaxAdaptor)
AdaptorFactory.register(ChannelType.GEMINI, GeminiAdaptor)
AdaptorFactory.register(ChannelType.BAIDU, BaiduAdaptor)
AdaptorFactory.register(ChannelType.ALI, AliAdaptor)
AdaptorFactory.register(ChannelType.ZHIPU, ZhipuAdaptor)
AdaptorFactory.register(ChannelType.TENCENT, TencentAdaptor)
AdaptorFactory.register(ChannelType.OLLAMA, OllamaAdaptor)
AdaptorFactory.register(ChannelType.MISTRAL, MistralAdaptor)
AdaptorFactory.register(ChannelType.GROQ, GroqAdaptor)
AdaptorFactory.register(ChannelType.COHERE, CohereAdaptor)
AdaptorFactory.register(ChannelType.CLOUDFLARE, CloudflareAdaptor)
AdaptorFactory.register(ChannelType.DEEPL, DeepLAdaptor)
AdaptorFactory.register(ChannelType.TOGETHERAI, TogetherAIAdaptor)
AdaptorFactory.register(ChannelType.NOVITA, NovitaAIAdaptor)
AdaptorFactory.register(ChannelType.SILICONFLOW, SiliconFlowAdaptor)
AdaptorFactory.register(ChannelType.XAI, XAIAdaptor)
AdaptorFactory.register(ChannelType.AWSCLAUDE, AWSClaudeAdaptor)
AdaptorFactory.register(ChannelType.VERTEXAI, VertexAIAdaptor)
AdaptorFactory.register(ChannelType.BAIDUV2, BaiduV2Adaptor)
AdaptorFactory.register(ChannelType.XUNFEIV2, XunfeiV2Adaptor)
AdaptorFactory.register(ChannelType.ALIBAILIAN, AliBailianAdaptor)
AdaptorFactory.register(ChannelType.OPENROUTER, OpenRouterAdaptor)
AdaptorFactory.register(ChannelType.COZE, CozeAdaptor)
AdaptorFactory.register(ChannelType.REPLICATE, ReplicateAdaptor)
AdaptorFactory.register(ChannelType.PROXY, ProxyAdaptor)
AdaptorFactory.register(ChannelType.AI360, Ai360Adaptor)
AdaptorFactory.register(ChannelType.BAICHUAN, BaichuanAdaptor)
AdaptorFactory.register(ChannelType.DOUBAO, DoubaoAdaptor)
AdaptorFactory.register(ChannelType.LINGYIWANWU, LingYiWanWuAdaptor)
AdaptorFactory.register(ChannelType.STEPFUN, StepFunAdaptor)
AdaptorFactory.register(ChannelType.OPENAICOMPATIBLE, OpenAICompatibleAdaptor)
AdaptorFactory.register(ChannelType.GEMINIOPENAICOMPATIBLE, GeminiOpenAICompatibleAdaptor)

AdaptorFactory.register_gateway("anthropic", AnthropicAdaptor)