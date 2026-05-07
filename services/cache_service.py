import asyncio
import time
from typing import Any, Dict, Optional, List
from collections import defaultdict


class CacheService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
            cls._instance._lock = asyncio.Lock()
            cls._instance._queue_size = 10
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_cache'):
            self._cache: Dict[str, tuple[Any, float]] = {}
            self._lock = asyncio.Lock()
            self._queue_size = 10

    async def get(self, key: str) -> Any:
        async with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if expire_time == 0 or time.time() < expire_time:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        async with self._lock:
            expire_time = time.time() + ttl if ttl > 0 else 0
            self._cache[key] = (value, expire_time)

    async def delete(self, key: str):
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self):
        async with self._lock:
            self._cache.clear()

    async def get_or_set(self, key: str, factory, ttl: int = 60) -> Any:
        value = await self.get(key)
        if value is None:
            value = factory() if callable(factory) else factory
            await self.set(key, value, ttl)
        return value


class ChannelMonitorCache:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._success_rates: Dict[int, List[int]] = defaultdict(list)
        self._error_messages: Dict[int, List[str]] = defaultdict(list)
        self._queue_size = 5
        self._threshold = 0.25

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_success(self, channel_id: int):
        self._success_rates[channel_id].append(1)
        if len(self._success_rates[channel_id]) > self._queue_size:
            self._success_rates[channel_id].pop(0)

    def record_error(self, channel_id: int, error_msg: str = ""):
        self._success_rates[channel_id].append(0)
        if len(self._success_rates[channel_id]) > self._queue_size:
            self._success_rates[channel_id].pop(0)

        if error_msg:
            self._error_messages[channel_id].append(error_msg)
            if len(self._error_messages[channel_id]) > self._queue_size:
                self._error_messages[channel_id].pop(0)

    def should_disable(self, channel_id: int) -> bool:
        if channel_id not in self._success_rates:
            return False

        history = self._success_rates[channel_id]
        if len(history) < self._queue_size:
            if len(history) < self._queue_size // 2:
                return False

        rate = sum(history) / len(history)
        return rate <= self._threshold

    def get_error_summary(self, channel_id: int) -> Optional[str]:
        if channel_id not in self._error_messages:
            return None

        messages = self._error_messages[channel_id][-5:]
        error_counts = defaultdict(int)
        for msg in messages:
            error_counts[msg] += 1

        if len(error_counts) == 0:
            return None

        max_count = max(error_counts.values())
        if max_count >= 3:
            for msg, count in error_counts.items():
                if count == max_count:
                    return msg
        return None

    def reset(self, channel_id: int):
        if channel_id in self._success_rates:
            self._success_rates[channel_id].clear()
        if channel_id in self._error_messages:
            self._error_messages[channel_id].clear()


cache_service = CacheService()
channel_monitor_cache = ChannelMonitorCache.get_instance()