from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
import os


@dataclass
class PaymentResult:
    success: bool
    payment_url: str = ""
    external_order_no: str = ""
    error_message: str = ""


@dataclass
class CallbackResult:
    success: bool
    order_no: str = ""
    external_order_no: str = ""
    amount: float = 0
    currency: str = ""
    error_message: str = ""


class PaymentAdapter(ABC):
    name: str = ""

    def __init__(self):
        self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def _check_enabled(self) -> bool:
        return self._enabled

    @abstractmethod
    def get_config_schema(self) -> dict:
        """返回配置项描述，用于管理后台配置UI"""
        return {}

    @abstractmethod
    async def create_payment(
        self,
        order_no: str,
        amount: float,
        currency: str,
        description: str,
        metadata: dict = None
    ) -> PaymentResult:
        """创建支付会话/链接"""
        pass

    @abstractmethod
    async def verify_callback(self, request) -> CallbackResult:
        """验证回调签名"""
        pass

    @abstractmethod
    async def handle_callback(self, request) -> CallbackResult:
        """处理支付成功回调"""
        pass

    @abstractmethod
    async def refund(self, order_no: str, external_order_no: str, amount: float = None) -> bool:
        """退款"""
        pass

    @abstractmethod
    async def cancel_order(self, order_no: str, external_order_no: str) -> bool:
        """取消订单"""
        pass


class PaymentRegistry:
    _adapters = {}

    @classmethod
    def register(cls, name: str, adapter_class: type):
        cls._adapters[name] = adapter_class

    @classmethod
    def get(cls, name: str) -> Optional[PaymentAdapter]:
        adapter_class = cls._adapters.get(name)
        if adapter_class:
            return adapter_class()
        return None

    @classmethod
    def list_adapters(cls) -> list:
        return list(cls._adapters.keys())

    @classmethod
    def initialize_adapters(cls, config: dict):
        """根据配置初始化所有适配器"""
        for name, adapter_class in cls._adapters.items():
            adapter = adapter_class()
            adapter._enabled = config.get(name, {}).get("enabled", False)
            cls._adapters[name] = adapter
        return cls


def register_payment_adapter(name: str):
    """装饰器：注册支付适配器"""
    def decorator(cls):
        PaymentRegistry.register(name, cls)
        return cls
    return decorator