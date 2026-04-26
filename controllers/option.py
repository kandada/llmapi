from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_session
from services.option_service import OptionService
from middleware.auth import AuthContext, require_root
from schemas.request import APIResponse, OptionItem, OptionUpdate


class OptionController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.option_service = OptionService(db)

    async def get_options(self, ctx: AuthContext = Depends(require_root)) -> APIResponse:
        options = self.option_service.get_all_options()

        filtered_options = []
        for key, value in options.items():
            if key.endswith("Token") or key.endswith("Secret"):
                continue
            filtered_options.append({"key": key, "value": str(value)})

        return APIResponse(success=True, data=filtered_options)

    async def update_option(self, option_data: OptionUpdate, ctx: AuthContext = Depends(require_root)) -> APIResponse:
        self.option_service.set_option(option_data.key, option_data.value)
        return APIResponse(success=True)
