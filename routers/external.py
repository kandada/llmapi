from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import time
import secrets

from database import get_session
from controllers.user import UserController
from schemas.request import APIResponse
from middleware.auth import SystemAuthContext, require_system_token

router = APIRouter(prefix="/api/external")

# In-memory storage for auto-login tokens
# Format: { token: { user_id, expires_at, used } }
_auto_login_tokens = {}


@router.post("/auto-login")
async def create_auto_login_token(
    request: Request,
    ctx: SystemAuthContext = Depends(require_system_token),
    db: Session = Depends(get_session),
):
    body = await request.json()
    user_id = body.get("user_id")

    if not user_id:
        return APIResponse(success=False, message="user_id is required")

    controller = UserController(db)
    user = controller.user_service.get_user_by_id(user_id)

    if not user:
        return APIResponse(success=False, message="User not found")

    # Generate short-lived token (5 minutes expiry)
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + 300  # 5 minutes

    _auto_login_tokens[token] = {
        "user_id": user_id,
        "expires_at": expires_at,
        "used": False,
    }

    return APIResponse(success=True, data={
        "auto_login_token": token,
        "expires_in": 300,
    })


@router.get("/verify-auto-login")
async def verify_auto_login(request: Request):
    token = request.query_params.get("token")

    if not token:
        return APIResponse(success=False, message="token is required")

    if token not in _auto_login_tokens:
        return APIResponse(success=False, message="Invalid token")

    token_info = _auto_login_tokens[token]

    if time.time() > token_info["expires_at"]:
        del _auto_login_tokens[token]
        return APIResponse(success=False, message="Token expired")

    if token_info["used"]:
        return APIResponse(success=False, message="Token already used")

    token_info["used"] = True

    user_id = token_info["user_id"]
    from database import get_db_session
    with get_db_session() as db:
        controller = UserController(db)
        user = controller.user_service.get_user_by_id(user_id)
        if not user:
            return APIResponse(success=False, message="User not found")

        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role
        request.session["status"] = user.status

        return APIResponse(success=True, data={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "quota": user.quota,
            "used_quota": user.used_quota,
        })


@router.post("/user/link-or-create")
async def link_or_create_user(
    request: Request,
    ctx: SystemAuthContext = Depends(require_system_token),
    db: Session = Depends(get_session),
):
    body = await request.json()
    email = body.get("email")
    username = body.get("username")
    display_name = body.get("display_name")

    if not email:
        return APIResponse(success=False, message="Email is required")

    controller = UserController(db)
    result = controller.link_or_create_user(
        email=email,
        username=username,
        display_name=display_name
    )

    if not result.get("success"):
        return APIResponse(success=False, message=result.get("error"))

    return APIResponse(success=True, data={
        "user_id": result["user_id"],
        "username": result["username"],
        "email": result["email"],
        "quota": result["quota"],
        "used_quota": result["used_quota"],
        "api_key": result["api_key"],
        "created": result["created"],
    })


@router.get("/user/{user_id}/quota")
async def get_user_quota(
    user_id: int,
    ctx: SystemAuthContext = Depends(require_system_token),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    result = controller.get_user_quota(user_id)

    if not result.get("success"):
        return APIResponse(success=False, message=result.get("error"))

    return APIResponse(success=True, data=result)


@router.get("/user/{user_id}/api-key")
async def get_user_api_key(
    user_id: int,
    ctx: SystemAuthContext = Depends(require_system_token),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    result = controller.get_user_api_key(user_id)

    if not result.get("success"):
        return APIResponse(success=False, message=result.get("error"))

    return APIResponse(success=True, data={
        "user_id": result["user_id"],
        "api_key": result["api_key"],
        "remain_quota": result["remain_quota"],
        "unlimited_quota": result["unlimited_quota"],
    })