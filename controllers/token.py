from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_session
from services.token_service import TokenService
from middleware.auth import AuthContext, require_user
from schemas.token import TokenCreate, TokenUpdate
from schemas.request import APIResponse
from models.channel import Channel


class TokenController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.token_service = TokenService(db)

    def _enrich_token(self, d: dict) -> dict:
        group = d.get("channel_group") or "default"
        channels = self.db.query(Channel).filter(
            Channel.group == group,
            Channel.status == 1,
        ).all()
        models = set()
        for ch in channels:
            if ch.models:
                for m in ch.models.split(","):
                    m = m.strip()
                    if m:
                        models.add(m)
        d["available_models"] = sorted(models) if models else []
        return d

    async def get_all_tokens(self, p: int = 0, order: str = "", ctx: AuthContext = Depends(require_user)) -> APIResponse:
        tokens = self.token_service.get_user_tokens(ctx.user_id, offset=p * 25, limit=25)
        data = []
        for t in tokens:
            d = t.__dict__
            d.pop("_sa_instance_state", None)
            data.append(self._enrich_token(d))
        return APIResponse(success=True, data=data)

    async def search_tokens(self, keyword: str, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        tokens = self.token_service.search_user_tokens(ctx.user_id, keyword)
        data = []
        for t in tokens:
            d = t.__dict__
            d.pop("_sa_instance_state", None)
            data.append(self._enrich_token(d))
        return APIResponse(success=True, data=data)

    async def get_token(self, token_id: int, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        token = self.token_service.get_token_by_id(token_id)
        if not token or token.user_id != ctx.user_id:
            return APIResponse(success=False, message="Token not found")

        d = token.__dict__
        d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=self._enrich_token(d))

    async def add_token(self, token_data: TokenCreate, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        data = token_data.dict()
        if ctx.user.role < 10:
            data["channel_group"] = "default"
        token = self.token_service.create_token(ctx.user_id, data)
        return APIResponse(success=True, data={
            "id": token.id,
            "key": token.key,
            "name": token.name,
        })

    async def update_token(self, update_data: TokenUpdate, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        data = update_data.dict(exclude_unset=True)
        if ctx.user.role < 10:
            data["channel_group"] = "default"
        token = self.token_service.update_token(update_data.id, ctx.user_id, data)
        if not token:
            return APIResponse(success=False, message="Token not found")

        return APIResponse(success=True, data=token.__dict__)

    async def delete_token(self, token_id: int, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        success = self.token_service.delete_token(token_id, ctx.user_id)
        if not success:
            return APIResponse(success=False, message="Token not found")

        return APIResponse(success=True)
