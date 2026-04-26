from sqlalchemy import Column, Integer, String, Text, BigInteger, Numeric
from .base import BaseModel


class Order(BaseModel):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    package_id = Column(Integer, nullable=False)

    payment_provider = Column(String(20), nullable=False)

    external_order_no = Column(String(128), index=True)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")

    status = Column(String(20), nullable=False, default="pending")

    created_time = Column(BigInteger, nullable=False)
    paid_time = Column(BigInteger, default=0)
    cancelled_time = Column(BigInteger, default=0)

    callback_data = Column(Text)

    order_metadata = Column(Text, default="{}")


class OrderStatus:
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class OrderMetadata:
    def __init__(self, return_url: str = "", cancel_url: str = ""):
        self.return_url = return_url
        self.cancel_url = cancel_url

    def to_dict(self) -> dict:
        return {"return_url": self.return_url, "cancel_url": self.cancel_url}

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json(json_str: str) -> "OrderMetadata":
        import json
        data = json.loads(json_str) if json_str else {}
        return OrderMetadata(
            return_url=data.get("return_url", ""),
            cancel_url=data.get("cancel_url", "")
        )