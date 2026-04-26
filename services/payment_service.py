from typing import Optional
from sqlalchemy.orm import Session

from payment.adapter import PaymentRegistry, PaymentAdapter, PaymentResult
from services.order_service import OrderService
from services.package_service import PackageService
from services.user_service import UserService
from services.log_service import LogService
from models.order import Order, OrderStatus
from models.package import Package
from utils.time import get_timestamp


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.order_service = OrderService(db)
        self.package_service = PackageService(db)
        self.user_service = UserService(db)
        self.log_service = LogService(db)

    def get_adapter(self, provider: str) -> Optional[PaymentAdapter]:
        return PaymentRegistry.get(provider)

    def list_enabled_providers(self) -> list:
        providers = []
        for name in PaymentRegistry.list_adapters():
            adapter = PaymentRegistry.get(name)
            if adapter and adapter.is_enabled():
                providers.append(name)
        return providers

    async def create_order_and_payment(
        self,
        user_id: int,
        package_id: int,
        payment_provider: str,
        currency: str = "USD",
        return_url: str = "",
        cancel_url: str = ""
    ) -> tuple[Optional[Order], PaymentResult]:
        package = self.package_service.get_package_by_id(package_id)
        if not package:
            return None, PaymentResult(success=False, error_message="Package not found")

        if package.status != 1:
            return None, PaymentResult(success=False, error_message="Package not available")

        try:
            amount = self.package_service.get_price(package, currency)
        except ValueError as e:
            return None, PaymentResult(success=False, error_message=str(e))
        if amount <= 0:
            return None, PaymentResult(success=False, error_message="Invalid package price")

        adapter = self.get_adapter(payment_provider)
        if not adapter:
            return None, PaymentResult(success=False, error_message=f"Payment provider '{payment_provider}' not available")

        if not adapter.is_enabled():
            return None, PaymentResult(success=False, error_message=f"Payment provider '{payment_provider}' is not enabled")

        order = self.order_service.create_order(
            user_id=user_id,
            package_id=package_id,
            payment_provider=payment_provider,
            amount=amount,
            currency=currency,
            metadata={
                "return_url": return_url,
                "cancel_url": cancel_url,
                "package_name": package.name,
                "package_quota": package.quota,
                "unit_price": amount
            }
        )

        payment_result = await adapter.create_payment(
            order_no=order.order_no,
            amount=amount,
            currency=currency,
            description=f"Purchase: {package.name}",
            metadata={
                "return_url": return_url,
                "cancel_url": cancel_url
            }
        )

        if not payment_result.success:
            self.order_service.update_order_status(
                order.order_no,
                OrderStatus.CANCELLED
            )
            return None, payment_result

        if payment_result.external_order_no:
            self.order_service.update_order_status(
                order.order_no,
                order.status,
                external_order_no=payment_result.external_order_no
            )

        return order, payment_result

    async def process_payment_callback(
        self,
        provider: str,
        request
    ) -> tuple[bool, str, str]:
        adapter = self.get_adapter(provider)
        if not adapter:
            return False, "", "Unknown payment provider"

        callback_result = await adapter.handle_callback(request)

        if not callback_result.success:
            return False, "", callback_result.error_message

        order_no = callback_result.order_no

        order = self.db.query(Order).filter(
            Order.order_no == order_no
        ).with_for_update().first()

        if not order:
            return False, order_no, "Order not found"

        if order.status == OrderStatus.PAID and order.paid_time > 0:
            return True, order_no, "Order already paid"

        if order.status != OrderStatus.PENDING:
            return False, order_no, f"Order status is {order.status}, cannot process"

        expected_amount = float(order.amount)
        callback_amount = callback_result.amount
        if callback_amount > 0 and abs(callback_amount - expected_amount) > 0.01:
            return False, order_no, f"Amount mismatch: expected {expected_amount}, got {callback_amount}"

        package = self.package_service.get_package_by_id(order.package_id)
        if not package:
            return False, order_no, "Package not found"

        try:
            success = self.order_service.update_order_status(
                order_no,
                OrderStatus.PAID,
                callback_data=str(callback_result)
            )

            if success:
                self.user_service.increase_quota(order.user_id, package.quota)
                user = self.user_service.get_user_by_id(order.user_id)
                self.log_service.record_topup(
                    order.user_id,
                    user.username if user else "",
                    f"Payment: {package.name}",
                    package.quota
                )
        except Exception as e:
            self.db.rollback()
            return False, order_no, f"Failed to process payment: {str(e)}"

        return True, order_no, "Payment processed successfully"

    async def refund_order(self, order_no: str, amount: float = None) -> bool:
        import json
        order = self.order_service.get_order_by_no(order_no)
        if not order:
            return False

        if order.status != OrderStatus.PAID:
            return False

        adapter = self.get_adapter(order.payment_provider)
        if not adapter:
            return False

        if amount is None:
            amount = float(order.amount)
        if amount <= 0 or amount > float(order.amount):
            return False

        try:
            metadata = json.loads(order.order_metadata) if order.order_metadata else {}
        except json.JSONDecodeError:
            metadata = {}

        package_quota = metadata.get("package_quota", 0)
        if package_quota <= 0:
            return False

        success = await adapter.refund(order_no, order.external_order_no, amount, order.currency)

        if success:
            self.order_service.update_order_status(order_no, OrderStatus.REFUNDED)
            quota_to_deduct = int(amount / float(order.amount) * package_quota)
            self.user_service.decrease_quota(order.user_id, quota_to_deduct)

        return success

    async def cancel_order(self, order_no: str, user_id: int = None, is_admin: bool = False) -> bool:
        order = self.order_service.get_order_by_no(order_no)
        if not order:
            return False

        if not is_admin and order.user_id != user_id:
            return False

        if order.status != OrderStatus.PENDING:
            return False

        adapter = self.get_adapter(order.payment_provider)
        if adapter:
            await adapter.cancel_order(order_no, order.external_order_no)

        self.order_service.update_order_status(order_no, OrderStatus.CANCELLED)
        return True