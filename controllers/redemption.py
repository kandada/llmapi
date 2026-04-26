from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_session
from services.redemption_service import RedemptionService
from middleware.auth import AuthContext, require_admin
from schemas.redemption import RedemptionCreate, RedemptionUpdate
from schemas.request import APIResponse


class RedemptionController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.redemption_service = RedemptionService(db)

    async def get_all_redemptions(self, p: int = 0, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        redemptions = self.redemption_service.get_all_redemptions(offset=p * 25, limit=25)
        data = [r.__dict__ for r in redemptions]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def search_redemptions(self, keyword: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        redemptions = self.redemption_service.search_redemptions(keyword)
        data = [r.__dict__ for r in redemptions]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def get_redemption(self, redemption_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        redemption = self.redemption_service.get_redemption_by_id(redemption_id)
        if not redemption:
            return APIResponse(success=False, message="Redemption not found")

        return APIResponse(success=True, data=redemption.__dict__)

    async def add_redemption(self, redemption_data: RedemptionCreate, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        if redemption_data.count > 100:
            return APIResponse(success=False, message="Count cannot exceed 100")

        keys = self.redemption_service.create_redemption(
            ctx.user_id,
            redemption_data.name,
            redemption_data.quota,
            redemption_data.count,
        )

        return APIResponse(success=True, data=keys)

    async def update_redemption(self, update_data: RedemptionUpdate, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        redemption = self.redemption_service.update_redemption(update_data.id, update_data.dict(exclude_unset=True))
        if not redemption:
            return APIResponse(success=False, message="Redemption not found")

        return APIResponse(success=True, data=redemption.__dict__)

    async def delete_redemption(self, redemption_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        success = self.redemption_service.delete_redemption(redemption_id)
        if not success:
            return APIResponse(success=False, message="Redemption not found")

        return APIResponse(success=True)
