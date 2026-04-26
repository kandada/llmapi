from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

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