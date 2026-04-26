from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_session
from services.token_service import TokenService
from middleware.auth import AuthContext, require_user
from schemas.token import TokenCreate, TokenUpdate
from schemas.request import APIResponse


class TokenController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.token_service = TokenService(db)

    async def get_all_tokens(self, p: int = 0, order: str = "", ctx: AuthContext = Depends(require_user)) -> APIResponse:
        tokens = self.token_service.get_user_tokens(ctx.user_id, offset=p * 25, limit=25)
        data = [t.__dict__ for t in tokens]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def search_tokens(self, keyword: str, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        tokens = self.token_service.search_user_tokens(ctx.user_id, keyword)
        data = [t.__dict__ for t in tokens]
        for d in data:
            d.pop("_sa_instance_state", None)
        return APIResponse(success=True, data=data)

    async def get_token(self, token_id: int, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        token = self.token_service.get_token_by_id(token_id)
        if not token or token.user_id != ctx.user_id:
            return APIResponse(success=False, message="Token not found")

        return APIResponse(success=True, data=token.__dict__)

    async def add_token(self, token_data: TokenCreate, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        token = self.token_service.create_token(ctx.user_id, token_data.dict())
        return APIResponse(success=True, data={
            "id": token.id,
            "key": token.key,
            "name": token.name,
        })

    async def update_token(self, update_data: TokenUpdate, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        token = self.token_service.update_token(update_data.id, ctx.user_id, update_data.dict(exclude_unset=True))
        if not token:
            return APIResponse(success=False, message="Token not found")

        return APIResponse(success=True, data=token.__dict__)

    async def delete_token(self, token_id: int, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        success = self.token_service.delete_token(token_id, ctx.user_id)
        if not success:
            return APIResponse(success=False, message="Token not found")

        return APIResponse(success=True)
