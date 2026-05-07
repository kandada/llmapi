from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import json

from database import get_session
from controllers.package import PackageController
from controllers.order import OrderController
from schemas.request import APIResponse
from middleware.auth import require_user, require_admin, AuthContext

router = APIRouter(prefix="/shop")


@router.get("/package/")
async def list_packages(db: Session = Depends(get_session)):
    controller = PackageController(db)
    return APIResponse(success=True, data=controller.get_public_packages())


@router.get("/package/{package_id}")
async def get_package(package_id: int, db: Session = Depends(get_session)):
    controller = PackageController(db)
    data = controller.get_package_detail(package_id)
    if not data:
        return APIResponse(success=False, message="Package not found")
    return APIResponse(success=True, data=data)


@router.get("/payment/providers")
async def list_payment_providers():
    controller = OrderController()
    return APIResponse(success=True, data=controller.list_payment_providers())


@router.post("/order/create")
async def create_order(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    body = await request.json()
    package_id = body.get("package_id")
    currency = body.get("currency", "USD")
    payment_provider = body.get("payment_provider", "stripe")
    return_url = body.get("return_url", "")
    cancel_url = body.get("cancel_url", "")

    controller = OrderController(db)
    result = await controller.create_order(
        package_id=package_id,
        currency=currency,
        payment_provider=payment_provider,
        return_url=return_url,
        cancel_url=cancel_url,
        ctx=ctx
    )

    if not result.get("success"):
        return APIResponse(success=False, message=result.get("error", "Failed to create order"))

    return APIResponse(success=True, data=result)


@router.get("/order/{order_no}")
async def get_order(
    order_no: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = OrderController(db)
    result = controller.get_order(order_no, ctx)
    if not result.get("success"):
        return APIResponse(success=False, message=result.get("error"))
    return APIResponse(success=True, data=result)


@router.get("/order/")
async def get_my_orders(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = OrderController(db)
    orders = controller.get_user_orders(ctx)
    return APIResponse(success=True, data=orders)


@router.get("/success")
async def payment_success(
    session_id: str = "",
    db: Session = Depends(get_session),
):
    result = "error"
    order_no = ""
    if session_id:
        secret_key = __import__('os').environ.get("STRIPE_SECRET_KEY", "")
        if secret_key:
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
                        headers={"Authorization": f"Bearer {secret_key}"},
                    )
                    data = resp.json()
                    payment_status = data.get("payment_status", "")
                    order_no = data.get("metadata", {}).get("order_no", "")
                    if payment_status == "paid" and order_no:
                        from services.order_service import OrderService
                        from services.user_service import UserService
                        from services.log_service import LogService
                        from models.order import OrderStatus
                        from models.package import Package
                        order_svc = OrderService(db)
                        order = order_svc.get_order_by_no(order_no)
                        if order and order.status == OrderStatus.PENDING:
                            pkg = db.query(Package).filter(Package.id == order.package_id).first()
                            if pkg:
                                order_svc.update_order_status(order_no, OrderStatus.PAID)
                                UserService(db).increase_quota(order.user_id, pkg.quota)
                                user = UserService(db).get_user_by_id(order.user_id)
                                LogService(db).record_topup(order.user_id, user.username if user else "", f"Stripe: {pkg.name}", pkg.quota)
                        result = "1"
                    elif payment_status == "unpaid":
                        result = "0"
                    else:
                        result = "error"
            except Exception:
                result = "error"

    return RedirectResponse(url=f"/shop?order={order_no}&paid={result}")