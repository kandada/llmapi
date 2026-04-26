from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_session
from services.log_service import LogService
from middleware.auth import AuthContext, require_user, require_admin
from schemas.request import APIResponse


class LogController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.log_service = LogService(db)

    async def get_all_logs(
        self,
        p: int = 0,
        limit: int = 25,
        log_type: int = 0,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        username: str = "",
        token_name: str = "",
        channel_id: int = 0,
        ctx: AuthContext = Depends(require_admin),
    ) -> APIResponse:
        logs = self.log_service.get_all_logs(
            log_type=log_type,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            model_name=model_name,
            username=username,
            token_name=token_name,
            channel_id=channel_id,
            offset=p * limit,
            limit=limit,
        )
        data = [log.__dict__ for log in logs]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def get_user_logs(
        self,
        p: int = 0,
        limit: int = 25,
        log_type: int = 0,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        token_name: str = "",
        ctx: AuthContext = Depends(require_user),
    ) -> APIResponse:
        logs = self.log_service.get_user_logs(
            user_id=ctx.user_id,
            log_type=log_type,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            model_name=model_name,
            token_name=token_name,
            offset=p * limit,
            limit=limit,
        )
        data = [log.__dict__ for log in logs]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def delete_old_logs(self, days: int = 30, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        from utils.time import get_timestamp
        target_timestamp = get_timestamp() - days * 86400
        count = self.log_service.delete_old_logs(target_timestamp)
        return APIResponse(success=True, data={"count": count})

    async def get_logs_stat(
        self,
        start_timestamp: int = 0,
        end_timestamp: int = 0,
        model_name: str = "",
        username: str = "",
        token_name: str = "",
        channel_id: int = 0,
        ctx: AuthContext = Depends(require_admin),
    ) -> APIResponse:
        quota = self.log_service.sum_used_quota(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            model_name=model_name,
            username=username,
            token_name=token_name,
            channel_id=channel_id,
        )
        return APIResponse(success=True, data={"quota": quota})
