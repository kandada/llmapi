from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session

from database import get_session
from services.user_service import UserService
from services.token_service import TokenService
from models.user import User, UserRole, UserStatus
from models.token import Token, TokenStatus
from utils.ip import is_ip_in_subnets, get_client_ip
from utils.time import get_timestamp

security = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user: User = None, token: Token = None):
        self.user = user
        self.token = token
        self.user_id = user.id if user else 0
        self.token_id = token.id if token else 0
        self.token_channel_group = token.channel_group if token else ""


def validate_token_model_permission(token: Token, model: str) -> Optional[str]:
    if not token.models:
        return None
    allowed_models = [m.strip() for m in token.models.split(",") if m.strip()]
    if not allowed_models:
        return None
    if model in allowed_models:
        return None
    return f"Model '{model}' is not allowed for this token. Allowed models: {', '.join(allowed_models)}"


async def get_auth_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_session),
    allow_session_auth: bool = True,
) -> AuthContext:
    ctx = AuthContext()

    if credentials:
        key = credentials.credentials
        if key.startswith("Bearer "):
            key = key[7:]
        if key.startswith("sk-"):
            key = key[3:]

        token_service = TokenService(db)
        token, error = token_service.validate_token(f"sk-{key}")

        if error:
            raise HTTPException(status_code=401, detail=error)

        if token.status != TokenStatus.ENABLED:
            raise HTTPException(status_code=401, detail="Token is not enabled")

        now = get_timestamp()
        if token.expired_time != -1 and token.expired_time < now:
            raise HTTPException(status_code=401, detail="Token expired")

        if not token.unlimited_quota and token.remain_quota <= 0:
            raise HTTPException(status_code=401, detail="Token quota exhausted")

        if token.subnet:
            client_ip = get_client_ip(request)
            subnets = [s.strip() for s in token.subnet.split(",") if s.strip()]
            if subnets and not is_ip_in_subnets(client_ip, subnets):
                raise HTTPException(status_code=403, detail=f"IP not allowed: {client_ip}")

        user_service = UserService(db)
        user = user_service.get_user_by_id(token.user_id)
        if not user or user.status != UserStatus.ENABLED:
            raise HTTPException(status_code=403, detail="User is disabled")

        ctx.user = user
        ctx.token = token
        ctx.user_id = user.id
        ctx.token_id = token.id
        ctx.token_channel_group = token.channel_group if token else ""

        token_service.update_access_time(token.id)

        return ctx

    if allow_session_auth:
        session_user_id = request.session.get("user_id") if hasattr(request, 'session') else None
        if session_user_id:
            user_service = UserService(db)
            user = user_service.get_user_by_id(session_user_id)
            if user and user.status == UserStatus.ENABLED:
                ctx.user = user
                ctx.user_id = user.id

    return ctx


async def require_user(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return ctx


async def require_admin(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if ctx.user.role < UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return ctx


async def require_root(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if ctx.user.role < UserRole.ROOT:
        raise HTTPException(status_code=403, detail="Root permission required")
    return ctx


async def optional_auth(
    ctx: AuthContext = Depends(get_auth_context),
) -> Optional[AuthContext]:
    return ctx


class SystemAuthContext:
    def __init__(self, system_token: str = None, app_name: str = None):
        self.system_token = system_token
        self.app_name = app_name
        self.is_valid = True


async def require_system_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> SystemAuthContext:
    from config import config

    if not config.SystemApiTokens:
        raise HTTPException(status_code=403, detail="System API not enabled")

    if not credentials:
        raise HTTPException(status_code=401, detail="System API token required")

    token = credentials.credentials.replace("Bearer ", "")

    if token not in config.SystemApiTokens:
        raise HTTPException(status_code=403, detail="Invalid system API token")

    return SystemAuthContext(system_token=token, app_name="external")


async def optional_system_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[SystemAuthContext]:
    if not credentials:
        return None

    from config import config

    token = credentials.credentials.replace("Bearer ", "")

    if token in config.SystemApiTokens:
        return SystemAuthContext(system_token=token, app_name="external")

    return None