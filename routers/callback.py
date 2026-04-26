from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from database import get_session
from services.payment_service import PaymentService
from schemas.request import APIResponse

router = APIRouter(prefix="/callback")


@router.post("/stripe")
async def stripe_callback(
    request: Request,
    db: Session = Depends(get_session),
):
    payment_service = PaymentService(db)
    success, order_no, message = await payment_service.process_payment_callback(
        "stripe", request
    )

    if success:
        return APIResponse(success=True, data={"order_no": order_no, "message": message})
    else:
        return APIResponse(success=False, message=message)


@router.post("/paypal")
async def paypal_callback(
    request: Request,
    db: Session = Depends(get_session),
):
    payment_service = PaymentService(db)
    success, order_no, message = await payment_service.process_payment_callback(
        "paypal", request
    )

    if success:
        return APIResponse(success=True, data={"order_no": order_no, "message": message})
    else:
        return APIResponse(success=False, message=message)