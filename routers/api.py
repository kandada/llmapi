from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_session
from controllers.user import UserController
from controllers.channel import ChannelController
from controllers.token import TokenController
from controllers.redemption import RedemptionController
from controllers.option import OptionController
from controllers.log import LogController
from schemas.user import UserLogin, UserCreate, UserUpdate
from schemas.channel import ChannelCreate, ChannelUpdate
from schemas.token import TokenCreate, TokenUpdate
from schemas.redemption import RedemptionCreate, RedemptionUpdate
from schemas.request import APIResponse, OptionUpdate, ResetPasswordRequest
from middleware.auth import require_user, require_admin, require_root, AuthContext

router = APIRouter(prefix="/api")


@router.get("/status")
async def get_status():
    from schemas.request import APIResponse
    return APIResponse(success=True, data={
        "version": "0.0.1",
        "status": "ok",
        "mode": "normal",
    })


# Open registration endpoint for Shop page (no auth required)
@router.post("/user/open-register", response_model=APIResponse)
async def open_register(
    request: Request,
    db: Session = Depends(get_session),
):
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    email = body.get("email", "").strip()

    if not username:
        return APIResponse(success=False, message="Username is required")
    if len(username) < 3 or len(username) > 32:
        return APIResponse(success=False, message="Username must be 3-32 characters")
    if not password or len(password) < 8:
        return APIResponse(success=False, message="Password must be at least 8 characters")

    controller = UserController(db)
    from services.user_service import UserService
    user_service = UserService(db)

    # Check if username exists
    if user_service.get_user_by_username(username):
        return APIResponse(success=False, message="Username already exists")

    # Check if email exists (if provided)
    if email and user_service.get_user_by_email(email):
        return APIResponse(success=False, message="Email already exists")

    # Create user with role=1 (COMMON)
    from models.user import UserRole
    user_data = {
        "username": username,
        "password": password,
        "email": email if email else None,
        "display_name": username,
        "role": UserRole.COMMON,
    }
    user = user_service.create_user(user_data)

    # Auto login after registration
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
    })


# User change own password
@router.post("/user/change-password", response_model=APIResponse)
async def change_password(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    body = await request.json()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not old_password or not new_password:
        return APIResponse(success=False, message="Old and new password are required")

    if len(new_password) < 8:
        return APIResponse(success=False, message="New password must be at least 8 characters")

    controller = UserController(db)
    success, error = controller.change_password(ctx.user_id, old_password, new_password)

    if not success:
        return APIResponse(success=False, message=error)

    return APIResponse(success=True, message="Password changed successfully")


# Admin change user password
@router.post("/user/{user_id}/reset-password", response_model=APIResponse)
async def admin_reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    new_password = body.new_password

    if not new_password or len(new_password) < 8:
        return APIResponse(success=False, message="New password must be at least 8 characters")

    controller = UserController(db)
    success, error = controller.admin_reset_password(user_id, new_password)

    if not success:
        return APIResponse(success=False, message=error)

    return APIResponse(success=True, message="Password reset successfully")


@router.post("/user/register", response_model=APIResponse)
async def register(
    user_data: UserCreate,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.register(user_data, ctx)


@router.post("/user/send-code", response_model=APIResponse)
async def send_verification_code(
    request: Request,
    db: Session = Depends(get_session),
):
    body = await request.json()
    email = body.get("email")
    code_type = body.get("type", "register")

    if not email:
        return APIResponse(success=False, message="Email is required")

    if code_type not in ("register", "login"):
        return APIResponse(success=False, message="Invalid type")

    controller = UserController(db)
    success, message = controller.user_service.send_verification_code(email, code_type)

    return APIResponse(success=success, message=message)


@router.post("/user/verify-code", response_model=APIResponse)
async def verify_code_and_login_register(
    request: Request,
    db: Session = Depends(get_session),
):
    body = await request.json()
    email = body.get("email")
    code = body.get("code")
    code_type = body.get("type", "register")
    password = body.get("password")  # For register

    if not email or not code:
        return APIResponse(success=False, message="Email and code are required")

    controller = UserController(db)
    success, error = controller.user_service.verify_code(email, code, code_type)

    if not success:
        return APIResponse(success=False, message=error)

    # Code verified, now login or register
    user = controller.user_service.get_user_by_email(email)

    if code_type == "register":
        if not user:
            # Create new user
            user = controller.user_service.create_user_with_email(
                email=email,
                password=password,
            )
        # If user exists from previous register, just login

    # Set session (login)
    from fastapi import Request as FastRequest
    # Get session from request context
    if hasattr(request, 'session'):
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


@router.post("/user/login", response_model=APIResponse)
async def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.login(request, login_data)


@router.get("/user/logout", response_model=APIResponse)
async def logout(
    request: Request,
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.logout(request)


@router.get("/user/self", response_model=APIResponse)
async def get_self(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.get_self(ctx)


@router.put("/user/self", response_model=APIResponse)
async def update_self(
    update_data: dict,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.update_self(update_data, ctx)


@router.delete("/user/self", response_model=APIResponse)
async def delete_self(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.delete_self(ctx)


@router.post("/user/topup", response_model=APIResponse)
async def topup(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    body = await request.json()
    key = body.get("key", "")
    controller = UserController(db)
    return await controller.topup(key, ctx)


@router.get("/user/token", response_model=APIResponse)
async def generate_access_token(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.generate_access_token(ctx)


@router.get("/user/", response_model=APIResponse)
async def get_all_users(
    p: int = 0,
    order: str = "",
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.get_all_users(p, order, ctx)


@router.get("/user/search", response_model=APIResponse)
async def search_users(
    keyword: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.search_users(keyword=keyword, ctx=ctx)


@router.get("/user/{user_id}", response_model=APIResponse)
async def get_user(
    user_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.get_user(user_id, ctx)


@router.post("/user/", response_model=APIResponse)
async def create_user(
    user_data: dict,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.create_user(user_data, ctx)


@router.put("/user/", response_model=APIResponse)
async def update_user(
    update_data: dict,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.update_user(update_data, ctx)


@router.delete("/user/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.delete_user(user_id, ctx)


@router.post("/user/manage", response_model=APIResponse)
async def manage_user(
    username: str,
    action: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.manage_user(username, action, ctx)


@router.post("/topup", response_model=APIResponse)
async def admin_topup(
    user_id: int,
    quota: int,
    remark: str = "",
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = UserController(db)
    return await controller.admin_topup(user_id, quota, remark, ctx)


channel_controller = ChannelController
token_controller = TokenController
redemption_controller = RedemptionController
option_controller = OptionController
log_controller = LogController


@router.get("/channel/", response_model=APIResponse)
async def get_all_channels(
    p: int = 0,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.get_all_channels(p, ctx)


@router.get("/channel/search", response_model=APIResponse)
async def search_channels(
    keyword: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.search_channels(keyword, ctx)


@router.get("/channel/{channel_id}", response_model=APIResponse)
async def get_channel(
    channel_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.get_channel(channel_id, ctx)


@router.post("/channel/", response_model=APIResponse)
async def add_channel(
    channel_data: ChannelCreate,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.add_channel(channel_data, ctx)


@router.put("/channel/", response_model=APIResponse)
async def update_channel(
    update_data: ChannelUpdate,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.update_channel(update_data, ctx)


@router.delete("/channel/{channel_id}", response_model=APIResponse)
async def delete_channel(
    channel_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.delete_channel(channel_id, ctx)


@router.delete("/channel/disabled", response_model=APIResponse)
async def delete_disabled_channels(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.delete_disabled_channels(ctx)


@router.get("/channel/test/{channel_id}", response_model=APIResponse)
async def test_channel(
    channel_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.test_channel(channel_id, ctx)


@router.get("/channel/test", response_model=APIResponse)
async def test_all_channels(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.test_all_channels(ctx)


@router.get("/channel/update_balance/{channel_id}", response_model=APIResponse)
async def update_channel_balance(
    channel_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.update_channel_balance(channel_id, ctx)


@router.get("/token/", response_model=APIResponse)
async def get_all_tokens(
    p: int = 0,
    order: str = "",
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.get_all_tokens(p, order, ctx)


@router.get("/token/search", response_model=APIResponse)
async def search_tokens(
    keyword: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.search_tokens(keyword, ctx)


@router.get("/token/{token_id}", response_model=APIResponse)
async def get_token(
    token_id: int,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.get_token(token_id, ctx)


@router.post("/token/", response_model=APIResponse)
async def add_token(
    token_data: TokenCreate,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.add_token(token_data, ctx)


@router.put("/token/", response_model=APIResponse)
async def update_token(
    update_data: TokenUpdate,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.update_token(update_data, ctx)


@router.delete("/token/{token_id}", response_model=APIResponse)
async def delete_token(
    token_id: int,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = TokenController(db)
    return await controller.delete_token(token_id, ctx)


@router.get("/redemption/", response_model=APIResponse)
async def get_all_redemptions(
    p: int = 0,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.get_all_redemptions(p, ctx)


@router.get("/redemption/search", response_model=APIResponse)
async def search_redemptions(
    keyword: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.search_redemptions(keyword, ctx)


@router.get("/redemption/{redemption_id}", response_model=APIResponse)
async def get_redemption(
    redemption_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.get_redemption(redemption_id, ctx)


@router.post("/redemption/", response_model=APIResponse)
async def add_redemption(
    redemption_data: RedemptionCreate,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.add_redemption(redemption_data, ctx)


@router.put("/redemption/", response_model=APIResponse)
async def update_redemption(
    update_data: RedemptionUpdate,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.update_redemption(update_data, ctx)


@router.delete("/redemption/{redemption_id}", response_model=APIResponse)
async def delete_redemption(
    redemption_id: int,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = RedemptionController(db)
    return await controller.delete_redemption(redemption_id, ctx)


@router.get("/option/", response_model=APIResponse)
async def get_options(
    ctx: AuthContext = Depends(require_root),
    db: Session = Depends(get_session),
):
    controller = OptionController(db)
    return await controller.get_options(ctx)


@router.put("/option/", response_model=APIResponse)
async def update_option(
    option_data: OptionUpdate,
    ctx: AuthContext = Depends(require_root),
    db: Session = Depends(get_session),
):
    controller = OptionController(db)
    return await controller.update_option(option_data, ctx)


@router.get("/log/", response_model=APIResponse)
async def get_all_logs(
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
    db: Session = Depends(get_session),
):
    controller = LogController(db)
    return await controller.get_all_logs(p, limit, log_type, start_timestamp, end_timestamp, model_name, username, token_name, channel_id, ctx)


@router.get("/log/self", response_model=APIResponse)
async def get_user_logs(
    p: int = 0,
    limit: int = 25,
    log_type: int = 0,
    start_timestamp: int = 0,
    end_timestamp: int = 0,
    model_name: str = "",
    token_name: str = "",
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = LogController(db)
    return await controller.get_user_logs(p, limit, log_type, start_timestamp, end_timestamp, model_name, token_name, ctx)


@router.delete("/log/", response_model=APIResponse)
async def delete_old_logs(
    days: int = 30,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = LogController(db)
    return await controller.delete_old_logs(days, ctx)


@router.get("/log/stat", response_model=APIResponse)
async def get_logs_stat(
    start_timestamp: int = 0,
    end_timestamp: int = 0,
    model_name: str = "",
    username: str = "",
    token_name: str = "",
    channel_id: int = 0,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = LogController(db)
    return await controller.get_logs_stat(start_timestamp, end_timestamp, model_name, username, token_name, channel_id, ctx)


@router.get("/ability/list", response_model=APIResponse)
async def get_abilities(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    from models.ability import Ability
    abilities = db.query(Ability).all()
    return APIResponse(success=True, data=[{
        "group": a.group,
        "model": a.model,
        "channel_id": a.channel_id,
        "enabled": a.enabled,
        "priority": a.priority,
    } for a in abilities])


@router.get("/channel/group/", response_model=APIResponse)
async def get_all_channel_groups(
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.get_all_groups(ctx)


@router.get("/channel/group/{group}", response_model=APIResponse)
async def get_channel_group(
    group: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.get_channels_by_group(group, ctx)


@router.put("/channel/group/", response_model=APIResponse)
async def rename_channel_group(
    old_group: str,
    new_group: str,
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.rename_group(old_group, new_group, ctx)


@router.delete("/channel/group/{group}", response_model=APIResponse)
async def delete_channel_group(
    group: str,
    move_to: str = "default",
    ctx: AuthContext = Depends(require_admin),
    db: Session = Depends(get_session),
):
    controller = ChannelController(db)
    return await controller.delete_group(group, move_to, ctx)


@router.get("/i18n/{lang}", response_model=APIResponse)
async def get_i18n(lang: str):
    from i18n import LANG_EN, LANG_ZH
    if lang == "en":
        return APIResponse(success=True, data=LANG_EN)
    return APIResponse(success=True, data=LANG_ZH)


@router.get("/i18n/", response_model=APIResponse)
async def get_i18n_current():
    from i18n import get_current_lang, LANG_EN, LANG_ZH
    lang = get_current_lang()
    translations = LANG_EN if lang == "en" else LANG_ZH
    return APIResponse(success=True, data={"lang": lang, "translations": translations})


@router.post("/i18n/set-language", response_model=APIResponse)
async def set_language(
    request: Request,
    ctx: AuthContext = Depends(require_user),
):
    body = await request.json()
    lang = body.get("lang", "zh")
    if lang not in ("en", "zh"):
        return APIResponse(success=False, message="Invalid language")
    from i18n import set_current_lang
    set_current_lang(lang)
    request.session["lang"] = lang
    return APIResponse(success=True, message="Language updated")
