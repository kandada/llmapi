from fastapi import Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_session
from services.order_service import OrderService
from services.payment_service import PaymentService
from middleware.auth import AuthContext, require_admin, require_user
from payment.adapter import PaymentRegistry
import json


class OrderController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.order_service = OrderService(db)
        self.payment_service = PaymentService(db)

    async def create_order(
        self,
        package_id: int,
        currency: str,
        payment_provider: str,
        return_url: str,
        cancel_url: str,
        ctx: AuthContext = Depends(require_user)
    ) -> dict:
        order, payment_result = await self.payment_service.create_order_and_payment(
            user_id=ctx.user_id,
            package_id=package_id,
            payment_provider=payment_provider,
            currency=currency,
            return_url=return_url,
            cancel_url=cancel_url
        )

        if not order:
            return {"success": False, "error": payment_result.error_message}

        return {
            "success": True,
            "order_no": order.order_no,
            "payment_url": payment_result.payment_url,
            "external_order_no": payment_result.external_order_no,
        }

    def get_order(self, order_no: str, ctx: AuthContext = Depends(require_user)) -> dict:
        order = self.order_service.get_order_by_no(order_no)
        if not order:
            return {"success": False, "error": "Order not found"}

        if order.user_id != ctx.user_id and ctx.user.role < 10:
            return {"success": False, "error": "Permission denied"}

        return {
            "success": True,
            "order": {
                "order_no": order.order_no,
                "package_id": order.package_id,
                "payment_provider": order.payment_provider,
                "amount": float(order.amount),
                "currency": order.currency,
                "status": order.status,
                "created_time": order.created_time,
                "paid_time": order.paid_time,
            }
        }

    def get_user_orders(self, ctx: AuthContext = Depends(require_user)) -> List[dict]:
        orders = self.order_service.get_user_orders(ctx.user_id)
        return [
            {
                "order_no": o.order_no,
                "package_id": o.package_id,
                "payment_provider": o.payment_provider,
                "amount": float(o.amount),
                "currency": o.currency,
                "status": o.status,
                "created_time": o.created_time,
                "paid_time": o.paid_time,
            }
            for o in orders
        ]

    def get_all_orders(
        self,
        p: int = 0,
        status: str = None,
        ctx: AuthContext = Depends(require_admin)
    ) -> List[dict]:
        orders = self.order_service.get_all_orders(offset=p * 50, limit=50, status=status)
        return [
            {
                "id": o.id,
                "order_no": o.order_no,
                "user_id": o.user_id,
                "package_id": o.package_id,
                "payment_provider": o.payment_provider,
                "amount": float(o.amount),
                "currency": o.currency,
                "status": o.status,
                "created_time": o.created_time,
                "paid_time": o.paid_time,
            }
            for o in orders
        ]

    def get_order_stats(self, ctx: AuthContext = Depends(require_admin)) -> dict:
        return self.order_service.get_order_stats()

    async def cancel_order(self, order_no: str, ctx: AuthContext = Depends(require_user)) -> bool:
        order = self.order_service.get_order_by_no(order_no)
        if not order:
            return False

        if order.user_id != ctx.user_id and ctx.user.role < 10:
            return False

        return await self.payment_service.cancel_order(
            order_no,
            user_id=ctx.user_id,
            is_admin=ctx.user.role >= 10
        )

    def list_payment_providers(self) -> dict:
        providers = []
        for name in PaymentRegistry.list_adapters():
            adapter = PaymentRegistry.get(name)
            if adapter and adapter.is_enabled():
                providers.append({
                    "name": name,
                    "enabled": True
                })
        return {"providers": providers}