from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_session
from controllers.package import PackageController
from controllers.order import OrderController
from services.payment_service import PaymentService
from schemas.request import APIResponse
from middleware.auth import require_admin, AuthContext

router = APIRouter(prefix="/admin")


@router.get("/package/")
async def list_all_packages(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = PackageController(db)
    packages = controller.get_all_packages_admin()
    return APIResponse(success=True, data=packages)


@router.post("/package/")
async def create_package(
    request: Request,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    body = await request.json()
    controller = PackageController(db)
    result = controller.create_package(body)
    return APIResponse(success=True, data=result)


@router.put("/package/{package_id}")
async def update_package(
    package_id: int,
    request: Request,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    body = await request.json()
    controller = PackageController(db)
    success = controller.update_package(package_id, body)
    if success:
        return APIResponse(success=True)
    return APIResponse(success=False, message="Package not found or update failed")


@router.delete("/package/{package_id}")
async def delete_package(
    package_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = PackageController(db)
    success = controller.delete_package(package_id)
    if success:
        return APIResponse(success=True)
    return APIResponse(success=False, message="Package not found or delete failed")


@router.get("/order/")
async def list_all_orders(
    p: int = 0,
    status: str = None,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = OrderController(db)
    orders = controller.get_all_orders(p=p, status=status, ctx=ctx)
    return APIResponse(success=True, data=orders)


@router.get("/order/stats")
async def get_order_stats(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = OrderController(db)
    stats = controller.get_order_stats(ctx)
    return APIResponse(success=True, data=stats)


@router.post("/order/{order_no}/cancel")
async def cancel_order(
    order_no: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = OrderController(db)
    success = await controller.cancel_order(order_no, ctx)
    if success:
        return APIResponse(success=True)
    return APIResponse(success=False, message="Failed to cancel order")


@router.post("/order/{order_no}/refund")
async def refund_order(
    order_no: str,
    request: Request,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    body = await request.json()
    amount = body.get("amount")

    payment_service = PaymentService(db)
    success = await payment_service.refund_order(order_no, amount)

    if success:
        return APIResponse(success=True)
    return APIResponse(success=False, message="Failed to refund order")