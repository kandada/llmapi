from typing import Optional, List
from sqlalchemy.orm import Session
import uuid
import json

from models.order import Order, OrderStatus
from utils.time import get_timestamp


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def generate_order_no(self) -> str:
        return f"ORD-{uuid.uuid4().hex[:16].upper()}"

    def get_order_by_no(self, order_no: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_no == order_no).first()

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_user_orders(self, user_id: int, offset: int = 0, limit: int = 25) -> List[Order]:
        return self.db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(Order.created_time.desc()).offset(offset).limit(limit).all()

    def get_all_orders(self, offset: int = 0, limit: int = 25, status: str = None) -> List[Order]:
        query = self.db.query(Order)
        if status:
            query = query.filter(Order.status == status)
        return query.order_by(Order.created_time.desc()).offset(offset).limit(limit).all()

    def get_orders_by_external_no(self, external_order_no: str) -> Optional[Order]:
        return self.db.query(Order).filter(
            Order.external_order_no == external_order_no
        ).first()

    def create_order(
        self,
        user_id: int,
        package_id: int,
        payment_provider: str,
        amount: float,
        currency: str,
        metadata: dict = None
    ) -> Order:
        order_no = self.generate_order_no()
        now = get_timestamp()

        metadata_json = json.dumps(metadata) if metadata else "{}"

        order = Order(
            order_no=order_no,
            user_id=user_id,
            package_id=package_id,
            payment_provider=payment_provider,
            amount=amount,
            currency=currency,
            status=OrderStatus.PENDING,
            created_time=now,
            metadata=metadata_json,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_order_status(
        self,
        order_no: str,
        status: str,
        external_order_no: str = None,
        callback_data: str = None
    ) -> Optional[Order]:
        order = self.get_order_by_no(order_no)
        if not order:
            return None

        order.status = status
        if external_order_no:
            order.external_order_no = external_order_no
        if callback_data:
            order.callback_data = callback_data

        if status == OrderStatus.PAID:
            order.paid_time = get_timestamp()
        elif status == OrderStatus.CANCELLED:
            order.cancelled_time = get_timestamp()

        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order_stats(self) -> dict:
        total = self.db.query(Order).count()
        pending = self.db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
        paid = self.db.query(Order).filter(Order.status == OrderStatus.PAID).count()
        cancelled = self.db.query(Order).filter(Order.status == OrderStatus.CANCELLED).count()

        return {
            "total": total,
            "pending": pending,
            "paid": paid,
            "cancelled": cancelled
        }