import httpx
import json
from typing import Optional
from sqlalchemy.orm import Session

from services.channel_service import ChannelService
from config import config


class ChannelMonitor:
    def __init__(self, db: Session):
        self.db = db
        self.channel_service = ChannelService(db)
        self._success_rates = {}
        self._threshold = config.ChannelDisableThreshold
        self._queue_size = 10

    def record_request(self, channel_id: int, success: bool):
        if channel_id not in self._success_rates:
            self._success_rates[channel_id] = []

        self._success_rates[channel_id].append(1 if success else 0)

        if len(self._success_rates[channel_id]) > self._queue_size:
            self._success_rates[channel_id].pop(0)

    def should_disable(self, channel_id: int) -> bool:
        if channel_id not in self._success_rates:
            return False

        history = self._success_rates[channel_id]
        if len(history) < self._queue_size:
            return False

        rate = sum(history) / len(history)
        return rate < self._threshold

    async def test_channel(self, channel) -> tuple[bool, int]:
        from relay.adaptor import AdaptorFactory

        adaptor = AdaptorFactory.get_adaptor(channel.type, getattr(channel, 'llm_gateway', 'openai'))

        test_request = {
            "model": channel.models.split(",")[0] if channel.models else "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
        }

        config_dict = {}
        if channel.config:
            try:
                config_dict = json.loads(channel.config)
            except:
                pass

        meta = {
            "channel_type": channel.type,
            "api_key": channel.key,
            "base_url": channel.base_url or "",
            "model": test_request["model"],
            "config": config_dict,
        }

        try:
            import time
            start = time.time()

            url = adaptor.get_request_url(meta)
            headers = adaptor.get_headers(meta)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=test_request)

            elapsed = int((time.time() - start) * 1000)

            if response.status_code == 200:
                self.channel_service.update_response_time(channel.id, elapsed)
                self.record_request(channel.id, True)
                return True, elapsed
            else:
                self.record_request(channel.id, False)
                return False, 0

        except Exception as e:
            print(f"Channel test error: {e}")
            self.record_request(channel.id, False)
            return False, 0

    def disable_channel(self, channel_id: int, reason: str = ""):
        from models.channel import ChannelStatus
        self.channel_service.disable_channel(channel_id, ChannelStatus.AUTO_DISABLED)
        print(f"Channel {channel_id} auto disabled: {reason}")

    def enable_channel(self, channel_id: int):
        self.channel_service.enable_channel(channel_id)
        print(f"Channel {channel_id} enabled")
