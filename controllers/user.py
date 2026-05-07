from fastapi import Request, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_session
from services.user_service import UserService
from services.token_service import TokenService
from services.redemption_service import RedemptionService
from services.log_service import LogService
from schemas.user import UserLogin, UserCreate, UserResponse
from schemas.request import APIResponse
from middleware.auth import AuthContext, require_user, require_admin, require_root
from utils.hash import verify_password, hash_password
from config import config


class UserController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.user_service = UserService(db)
        self.token_service = TokenService(db)
        self.redemption_service = RedemptionService(db)
        self.log_service = LogService(db)

    async def login(self, request: Request, login_data: UserLogin) -> APIResponse:
        client_ip = request.client.host if request.client else ""
        user, error = self.user_service.validate_login(login_data.username, login_data.password, ip=client_ip)
        if error:
            return APIResponse(success=False, message=error)

        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role
        request.session["status"] = user.status

        return APIResponse(
            success=True,
            data={
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "status": user.status,
            }
        )

    async def logout(self, request: Request) -> APIResponse:
        if hasattr(request, 'session'):
            request.session.clear()
        return APIResponse(success=True)

    async def register(self, register_data: UserCreate, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        if not config.RegisterEnabled:
            return APIResponse(success=False, message="Registration is disabled")

        if not config.PasswordRegisterEnabled:
            return APIResponse(success=False, message="Password registration is disabled")

        existing = self.user_service.get_user_by_username(register_data.username)
        if existing:
            return APIResponse(success=False, message="Username already exists")

        user_data = register_data.dict()
        user = self.user_service.create_user(user_data)

        return APIResponse(success=True, data={"id": user.id})

    async def get_self(self, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        user = ctx.user
        user_data = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "status": user.status,
            "email": user.email,
            "quota": user.quota,
            "used_quota": user.used_quota,
            "group": user.group,
        }
        tokens = self.token_service.get_user_tokens(user.id, limit=1)
        if tokens:
            user_data["api_key"] = tokens[0].key
        else:
            token = self.token_service.create_token(user.id, {"name": "Default Token", "remain_quota": 0, "unlimited_quota": True})
            user_data["api_key"] = token.key
        return APIResponse(success=True, data=user_data)

    async def update_self(self, update_data: dict, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        if "password" in update_data and update_data["password"]:
            if len(update_data["password"]) < 8:
                return APIResponse(success=False, message="Password must be at least 8 characters")

        user = self.user_service.update_user(ctx.user_id, update_data)
        if not user:
            return APIResponse(success=False, message="User not found")

        return APIResponse(success=True)

    async def delete_self(self, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        if ctx.user.role >= 100:
            return APIResponse(success=False, message="Cannot delete root user")

        success = self.user_service.delete_user(ctx.user_id)
        if not success:
            return APIResponse(success=False, message="Delete failed")

        return APIResponse(success=True)

    async def topup(self, key: str, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        quota, error = self.redemption_service.redeem(key, ctx.user_id)
        if error:
            return APIResponse(success=False, message=error)

        self.user_service.increase_quota(ctx.user_id, quota)
        self.log_service.record_topup(ctx.user_id, ctx.user.username, f"Redeem code: {quota}", quota)

        return APIResponse(success=True, data={"quota": quota})

    async def generate_access_token(self, ctx: AuthContext = Depends(require_user)) -> APIResponse:
        from utils.random import generate_uuid
        user = self.user_service.get_user_by_id(ctx.user_id)
        if not user:
            return APIResponse(success=False, message="User not found")

        user.access_token = generate_uuid()
        self.user_service.update_user(ctx.user_id, {"access_token": user.access_token})

        return APIResponse(success=True, data=user.access_token)

    async def get_all_users(self, p: int = 0, order: str = "", ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        users = self.user_service.get_all_users(offset=p * 25, limit=25, order=order)
        data = [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role,
                "status": u.status,
                "email": u.email,
                "quota": u.quota,
                "used_quota": u.used_quota,
                "group": u.group,
            }
            for u in users
        ]
        return APIResponse(success=True, data=data)

    async def search_users(self, keyword: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        users = self.user_service.search_users(keyword)
        data = [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role,
                "status": u.status,
                "email": u.email,
                "quota": u.quota,
                "used_quota": u.used_quota,
                "group": u.group,
            }
            for u in users
        ]
        return APIResponse(success=True, data=data)

    async def get_user(self, user_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return APIResponse(success=False, message="User not found")

        return APIResponse(
            success=True,
            data={
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "status": user.status,
                "email": user.email,
                "quota": user.quota,
                "used_quota": user.used_quota,
                "group": user.group,
            }
        )

    async def create_user(self, user_data: dict, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        user = self.user_service.create_user(user_data)
        return APIResponse(success=True, data={"id": user.id})

    async def update_user(self, update_data: dict, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        user_id = update_data.get("id")
        if not user_id:
            return APIResponse(success=False, message="User ID required")

        user = self.user_service.update_user(user_id, update_data)
        if not user:
            return APIResponse(success=False, message="User not found")

        return APIResponse(success=True)

    async def delete_user(self, user_id: int, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        success = self.user_service.delete_user(user_id)
        if not success:
            return APIResponse(success=False, message="Delete failed")

        return APIResponse(success=True)

    async def manage_user(self, username: str, action: str, ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        user = self.user_service.get_user_by_username(username)
        if not user:
            return APIResponse(success=False, message="User not found")

        if action == "disable":
            user.status = 2
        elif action == "enable":
            user.status = 1
        elif action == "delete":
            return await self.delete_user(user.id, ctx)
        elif action == "promote":
            user.role = 10
        elif action == "demote":
            user.role = 1
        else:
            return APIResponse(success=False, message="Unknown action")

        self.user_service.update_user(user.id, {"status": user.status, "role": user.role})
        return APIResponse(success=True)

    async def admin_topup(self, user_id: int, quota: int, remark: str = "", ctx: AuthContext = Depends(require_admin)) -> APIResponse:
        self.user_service.increase_quota(user_id, quota)
        self.log_service.record_topup(user_id, "", remark or f"Admin topup: {quota}", quota)
        return APIResponse(success=True)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        # Check if user has a password (external users may not)
        if not user.password:
            return False, "Cannot change password: no password set"

        # Verify old password
        from utils.hash import verify_password
        if not verify_password(old_password, user.password):
            return False, "Old password is incorrect"

        # Update password
        self.user_service.update_user(user_id, {"password": new_password})
        return True, ""

    def admin_reset_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        # Cannot reset root password
        if user.role >= 100:
            return False, "Cannot reset root password"

        self.user_service.update_user(user_id, {"password": new_password})
        return True, ""

    def link_or_create_user(self, email: str, username: str = None, display_name: str = None) -> dict:
        existing = self.user_service.get_user_by_email(email)

        if existing:
            user = existing
            created = False
        else:
            if not config.ExternalAppAutoCreateUser:
                return {
                    "success": False,
                    "error": "Auto-create user is disabled",
                    "user_id": None,
                    "created": False
                }

            username = username or email.split("@")[0][:12]
            user_data = {
                "username": username,
                "password": "",  # No password for external users
                "email": email,
                "display_name": display_name or username,
                "role": 1,  # Regular user
            }
            user = self.user_service.create_user_external(user_data)
            created = True

        tokens = self.token_service.get_user_tokens(user.id)
        api_key = tokens[0].key if tokens else None

        if not api_key:
            token_data = {
                "name": f"Auto-created for {email}",
                "remain_quota": 0,
                "unlimited_quota": False,
            }
            token = self.token_service.create_token(user.id, token_data)
            api_key = token.key

        return {
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "quota": user.quota,
            "used_quota": user.used_quota,
            "api_key": api_key,
            "created": created
        }

    def get_user_quota(self, user_id: int) -> dict:
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        tokens = self.token_service.get_user_tokens(user.id)
        token_info = []
        for t in tokens:
            token_info.append({
                "id": t.id,
                "name": t.name,
                "key": t.key,
                "remain_quota": t.remain_quota,
                "unlimited_quota": t.unlimited_quota,
                "status": t.status
            })

        return {
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "quota": user.quota,
            "used_quota": user.used_quota,
            "tokens": token_info
        }

    def get_user_api_key(self, user_id: int) -> dict:
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        tokens = self.token_service.get_user_tokens(user.id)
        if not tokens:
            token_data = {
                "name": f"API Key for user {user_id}",
                "remain_quota": 0,
                "unlimited_quota": False,
            }
            token = self.token_service.create_token(user.id, token_data)
        else:
            token = tokens[0]

        return {
            "success": True,
            "user_id": user.id,
            "api_key": token.key,
            "remain_quota": token.remain_quota,
            "unlimited_quota": token.unlimited_quota
        }
