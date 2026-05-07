from typing import Optional, AsyncGenerator
import httpx
import json
import time
import logging

from models.channel import Channel
from services.channel_service import ChannelService
from services.user_service import UserService
from services.token_service import TokenService
from services.log_service import LogService
from services.cache_service import cache_service
from billing.ratio import (
    get_model_ratio_from_db,
    get_completion_ratio_from_db,
    get_group_ratio_from_db,
)
from relay.adaptor import AdaptorFactory, get_http_client
from utils.time import get_timestamp
from config import config

logger = logging.getLogger(__name__)


class RelayService:
    def __init__(self, db):
        self.db = db
        self.channel_service = ChannelService(db)
        self.user_service = UserService(db)
        self.token_service = TokenService(db)
        self.log_service = LogService(db)

    def calculate_quota(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        group: str = "default",
        channel_type: int = 0,
    ) -> int:
        model_ratio = get_model_ratio_from_db(model, channel_type)
        completion_ratio = get_completion_ratio_from_db(model, channel_type)
        group_ratio = get_group_ratio_from_db(group)

        input_cost = prompt_tokens * model_ratio
        output_cost = completion_tokens * model_ratio * completion_ratio

        total = input_cost + output_cost
        return int(total * group_ratio)

    def calculate_preconsume_quota(
        self,
        model: str,
        prompt_tokens: int,
        max_tokens: int = 0,
        group: str = "default",
        channel_type: int = 0,
    ) -> int:
        model_ratio = get_model_ratio_from_db(model, channel_type)
        completion_ratio = get_completion_ratio_from_db(model, channel_type)
        group_ratio = get_group_ratio_from_db(group)

        preconsumed_tokens = config.PreConsumedQuota + prompt_tokens
        if max_tokens > 0:
            preconsumed_tokens += max_tokens

        input_cost = preconsumed_tokens * model_ratio
        output_cost = preconsumed_tokens * model_ratio * completion_ratio
        total = input_cost + output_cost

        return int(total * group_ratio)

    async def relay_request(
        self,
        request: dict,
        channel: Channel,
        model: str,
        base_url: str,
        user_id: int,
        token_id: int,
        token_name: str,
        user_group: str = "default",
    ) -> tuple[httpx.Response, bool]:
        api_key = channel.key
        config_dict = {}
        if channel.config:
            try:
                config_dict = json.loads(channel.config)
            except:
                pass

        meta = {
            "channel_type": channel.type,
            "channel_id": channel.id,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "config": config_dict,
            "group": user_group,
        }

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))
        converted_request = await adaptor.convert_request(request, meta)

        is_stream = request.get("stream", False)

        if is_stream:
            return await self._relay_stream(adaptor, converted_request, meta, user_id, token_id, token_name, model, channel.type, user_group)
        else:
            return await self._relay_normal(adaptor, converted_request, meta, user_id, token_id, token_name, model, channel.type, user_group)

    async def _relay_normal(
        self,
        adaptor,
        request: dict,
        meta: dict,
        user_id: int,
        token_id: int,
        token_name: str,
        model: str,
        channel_type: int,
        user_group: str = "default",
        skip_quota_deduction: bool = False,
    ) -> tuple[httpx.Response, bool]:
        try:
            response = await adaptor.relay(request, meta)
            is_success = response.status_code == 200

            if is_success:
                try:
                    data = response.json()
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                    quota = self.calculate_quota(model, prompt_tokens, completion_tokens, user_group, channel_type)

                    if quota > 0 and not skip_quota_deduction:
                        self._record_consume(
                            user_id, token_id, token_name, model,
                            quota, prompt_tokens, completion_tokens,
                            meta.get("channel_id", 0), "", 0, False
                        )
                        self.token_service.decrease_quota(token_id, quota)
                        self.user_service.decrease_quota(user_id, quota)
                except Exception as e:
                    logger.error(f"Error processing response: {e}")

            return response, is_success

        except httpx.TimeoutException:
            return self._create_error_response("Request timeout"), False
        except Exception as e:
            return self._create_error_response(str(e)), False

    async def _relay_stream(
        self,
        adaptor,
        request: dict,
        meta: dict,
        user_id: int,
        token_id: int,
        token_name: str,
        model: str,
        channel_type: int,
        user_group: str = "default",
        skip_quota_deduction: bool = False,
    ) -> tuple[AsyncGenerator, bool]:
        async def generate():
            nonlocal skip_quota_deduction
            prompt_tokens = 0
            completion_tokens = 0
            total_content = ""
            start_time = time.time()

            try:
                async for chunk in adaptor.relay_stream(request, meta):
                    if chunk.startswith("data: "):
                        data_str = chunk[6:]
                        if data_str == "[DONE]\n\n":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get("choices"):
                                delta = data["choices"][0].get("delta", {})
                                if delta.get("content"):
                                    total_content += delta["content"]
                            if "usage" in data:
                                usage = data["usage"]
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
                        except:
                            pass
                    yield chunk

                elapsed_time = int((time.time() - start_time) * 1000)

                p, c = prompt_tokens, completion_tokens
                if p == 0 and c == 0 and total_content:
                    c = len(total_content) // 4
                quota = self.calculate_quota(model, p, c, user_group, channel_type)
                if quota > 0 and not skip_quota_deduction:
                    self._record_consume(
                        user_id, token_id, token_name, model,
                        quota, prompt_tokens, completion_tokens,
                        meta.get("channel_id", 0), "", elapsed_time, True
                    )
                    self.token_service.decrease_quota(token_id, quota)
                    self.user_service.decrease_quota(user_id, quota)

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f'data: {{"error": {{"message": "{str(e)}", "type": "upstream_error"}}}}\n\n'
                yield "data: [DONE]\n\n"

        return generate(), True

    def _create_error_response(self, message: str) -> httpx.Response:
        class MockResponse:
            def __init__(self):
                self.status_code = 500
                self._content = json.dumps({"error": {"message": message, "type": "upstream_error"}}).encode()

            def json(self):
                return json.loads(self._content)

        return MockResponse()

    def _record_consume(
        self,
        user_id: int,
        token_id: int,
        token_name: str,
        model: str,
        quota: int,
        prompt_tokens: int,
        completion_tokens: int,
        channel_id: int,
        request_id: str,
        elapsed_time: int,
        is_stream: bool,
    ):
        user = self.user_service.get_user_by_id(user_id)
        username = user.username if user else ""

        self.log_service.record_consume(
            user_id=user_id,
            username=username,
            token_name=token_name,
            model_name=model,
            quota=quota,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            channel_id=channel_id,
            request_id=request_id,
            elapsed_time=elapsed_time,
            is_stream=is_stream,
        )


class PreconsumeQuotaService:
    def __init__(self, db):
        self.db = db
        self.channel_service = ChannelService(db)
        self.token_service = TokenService(db)
        self.user_service = UserService(db)
        self.billing_service = RelayService(db)

    # ============================================================
    # 额度预扣费流程 (Pre-consume Quota Flow)
    # ============================================================
    # 1. 计算预估消耗
    # 2. 检查额度（Admin/Root 跳过 User 级别检查）
    # 3. 预扣 Token 和 User 的额度
    # ============================================================
    def preconsume(self, token_id: int, user_id: int, model: str, prompt_tokens: int, max_tokens: int = 0, group: str = "default", channel_type: int = 0) -> tuple[bool, int]:
        token = self.token_service.get_token_by_id(token_id)
        if not token:
            return False, 0

        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False, 0

        estimated_quota = self.billing_service.calculate_preconsume_quota(model, prompt_tokens, max_tokens, group, channel_type)

        # ============================================================
        # Admin/Root 用户：不检查 User 额度限制，跳过预扣
        # ============================================================
        if user.role >= 10:  # Admin or Root
            # Admin/Root 的 unlimited token 完全不扣额度
            if token.unlimited_quota:
                return True, 0
            # Admin/Root 的有限 token 只扣 Token.remain_quota，不扣 User.quota
            if token.remain_quota < estimated_quota:
                return False, 0
            self.token_service.decrease_quota(token_id, estimated_quota)
            return True, estimated_quota

        # ============================================================
        # 普通用户：先检查 Token 是否 unlimited
        # ============================================================
        if token.unlimited_quota:
            # Token 是 unlimited 时，User quota 只用于校验上限，不做强制检查
            # 只扣除 User.used_quota，不扣 Token.remain_quota
            self.user_service.decrease_quota(user_id, estimated_quota)
            return True, 0  # 返回 0 表示没有预扣 Token 额度

        # ============================================================
        # 有限 Token：检查 User.remain_quota 和 Token.remain_quota
        # ============================================================
        user_remain = user.quota - user.used_quota

        # 如果 User 额度不足，拒绝
        if user_remain <= 0:
            return False, 0

        # 检查 Token.remain_quota
        if token.remain_quota < estimated_quota:
            return False, 0

        # 预扣 Token 和 User 的额度
        self.token_service.decrease_quota(token_id, estimated_quota)
        self.user_service.decrease_quota(user_id, estimated_quota)
        return True, estimated_quota

    def return_preconsumed(self, token_id: int, user_id: int, preconsumed_quota: int):
        if preconsumed_quota > 0:
            self.token_service.increase_quota(token_id, preconsumed_quota)
            self.user_service.increase_quota(user_id, preconsumed_quota)

    # ============================================================
    # 额度调整流程 (Post-consume Quota Adjustment)
    # ============================================================
    # 1. 实际消耗 < 预扣：退还多余部分
    # 2. 实际消耗 > 预扣：补扣差额（普通用户）
    # ============================================================
    def post_consume(self, token_id: int, user_id: int, actual_quota: int, preconsumed_quota: int):
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return

        # Admin/Root 用户：只调整 Token，不调整 User
        if user.role >= 10:
            if actual_quota < preconsumed_quota:
                self.token_service.increase_quota(token_id, preconsumed_quota - actual_quota)
            elif actual_quota > preconsumed_quota:
                self.token_service.decrease_quota(token_id, actual_quota - preconsumed_quota)
            return

        # 普通用户：同时调整 Token 和 User
        if actual_quota < preconsumed_quota:
            self.token_service.increase_quota(token_id, preconsumed_quota - actual_quota)
            self.user_service.increase_quota(user_id, preconsumed_quota - actual_quota)
        elif actual_quota > preconsumed_quota:
            self.token_service.decrease_quota(token_id, actual_quota - preconsumed_quota)
            self.user_service.decrease_quota(user_id, actual_quota - preconsumed_quota)