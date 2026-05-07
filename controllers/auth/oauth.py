from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import httpx
import json
import secrets

from database import get_session
from services.user_service import UserService
from config import config
from middleware.auth import AuthContext, require_user

router = APIRouter(prefix="/api/oauth")


class OAuthController:
    def __init__(self, db: Session = Depends(get_session)):
        self.db = db
        self.user_service = UserService(db)

    async def github_callback(self, code: str, state: str = None) -> JSONResponse:
        if not config.GitHubOAuthEnabled:
            raise HTTPException(status_code=400, detail="GitHub OAuth is not enabled")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code is required")

        token_url = "https://github.com/login/oauth/access_token"
        user_url = "https://api.github.com/user"

        try:
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    token_url,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": config.GitHubClientId,
                        "client_secret": config.GitHubClientSecret,
                        "code": code,
                    },
                )

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise HTTPException(status_code=400, detail="Failed to get access token")

                user_response = await client.get(
                    user_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                user_data = user_response.json()
                github_id = str(user_data.get("id"))
                username = user_data.get("login", f"github_{github_id}")
                email = user_data.get("email")
                display_name = user_data.get("name", username)

                user = self.user_service.get_user_by_github_id(github_id)

                if not user:
                    existing_user = self.user_service.get_user_by_username(username)
                    if existing_user:
                        username = f"{username}_{github_id}"

                    user = self.user_service.create_user({
                        "username": username,
                        "password": secrets.token_hex(16),
                        "display_name": display_name or username,
                        "github_id": github_id,
                        "email": email,
                    }, inviter_id=0)

                return JSONResponse(content={
                    "success": True,
                    "data": {
                        "user_id": user.id,
                        "username": user.username,
                    }
                })

        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {str(e)}")

    def get_github_login_url(self, state: str = None) -> str:
        if not state:
            state = secrets.token_hex(16)
        return f"https://github.com/login/oauth/authorize?client_id={config.GitHubClientId}&redirect_uri={config.ServerAddress}/api/oauth/github/callback&scope=read:user,user:email&state={state}"

    async def lark_callback(self, code: str, state: str = None) -> JSONResponse:
        if not config.LarkClientId:
            raise HTTPException(status_code=400, detail="Lark OAuth is not enabled")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code is required")

        token_url = "https://open.feishu.cn/open-apis/authen/v1/oauth/access_token"
        user_url = "https://open.feishu.cn/open-apis/authen/v1/user_info"

        try:
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    token_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "app_id": config.LarkClientId,
                        "app_secret": config.LarkClientSecret,
                        "grant_type": "authorization_code",
                        "code": code,
                    },
                )

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise HTTPException(status_code=400, detail="Failed to get access token")

                user_response = await client.get(
                    user_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                user_data = user_response.json()
                lark_id = str(user_data.get("user_id"))
                username = user_data.get("username", f"lark_{lark_id}")
                display_name = user_data.get("name", username)
                email = user_data.get("email")

                user = self.user_service.get_user_by_lark_id(lark_id)

                if not user:
                    existing_user = self.user_service.get_user_by_username(username)
                    if existing_user:
                        username = f"{username}_{lark_id}"

                    user = self.user_service.create_user({
                        "username": username,
                        "password": secrets.token_hex(16),
                        "display_name": display_name or username,
                        "lark_id": lark_id,
                        "email": email,
                    }, inviter_id=0)

                return JSONResponse(content={
                    "success": True,
                    "data": {
                        "user_id": user.id,
                        "username": user.username,
                    }
                })

        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"Lark OAuth error: {str(e)}")

    def get_lark_login_url(self, state: str = None) -> str:
        if not state:
            state = secrets.token_hex(16)
        return f"https://open.feishu.cn/connect/connectnext/appKey/{config.LarkClientId}/authorize?redirect_uri={config.ServerAddress}/api/oauth/lark/callback&scope=contact:user.email:readonly&state={state}&app_id={config.LarkClientId}"

    async def oidc_callback(self, code: str, state: str = None) -> JSONResponse:
        if not config.OidcEnabled:
            raise HTTPException(status_code=400, detail="OIDC OAuth is not enabled")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code is required")

        token_url = config.OidcTokenEndpoint
        user_url = config.OidcUserinfoEndpoint

        try:
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": f"{config.ServerAddress}/api/oauth/oidc/callback",
                        "client_id": config.OidcClientId,
                        "client_secret": config.OidcClientSecret,
                    },
                )

                token_data = token_response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise HTTPException(status_code=400, detail="Failed to get access token")

                user_response = await client.get(
                    user_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                user_data = user_response.json()
                oidc_id = str(user_data.get("sub"))
                username = user_data.get("preferred_username", f"oidc_{oidc_id}")
                display_name = user_data.get("name", username)
                email = user_data.get("email")

                user = self.user_service.get_user_by_oidc_id(oidc_id)

                if not user:
                    existing_user = self.user_service.get_user_by_username(username)
                    if existing_user:
                        username = f"{username}_{oidc_id}"

                    user = self.user_service.create_user({
                        "username": username,
                        "password": secrets.token_hex(16),
                        "display_name": display_name or username,
                        "oidc_id": oidc_id,
                        "email": email,
                    }, inviter_id=0)

                return JSONResponse(content={
                    "success": True,
                    "data": {
                        "user_id": user.id,
                        "username": user.username,
                    }
                })

        except httpx.HTTPError as e:
            raise HTTPException(status_code=400, detail=f"OIDC OAuth error: {str(e)}")

    def get_oidc_login_url(self, state: str = None) -> str:
        if not state:
            state = secrets.token_hex(16)
        return f"{config.OidcAuthorizationEndpoint}?client_id={config.OidcClientId}&redirect_uri={config.ServerAddress}/api/oauth/oidc/callback&response_type=code&scope=openid profile email&state={state}"

    def generate_state(self) -> str:
        return secrets.token_hex(16)


_oauth_controller = OAuthController


def get_oauth_controller(db: Session = Depends(get_session)) -> OAuthController:
    return _oauth_controller(db)


@router.get("/github")
async def github_login():
    return RedirectResponse(url=f"https://github.com/login/oauth/authorize?client_id={config.GitHubClientId}&redirect_uri={config.ServerAddress}/api/oauth/github/callback&scope=read:user,user:email")


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_session),
):
    controller = get_oauth_controller(db)
    return await controller.github_callback(code, state)


@router.get("/lark")
async def lark_login():
    return RedirectResponse(url=f"https://open.feishu.cn/connect/connectnext/appKey/{config.LarkClientId}/authorize?redirect_uri={config.ServerAddress}/api/oauth/lark/callback&scope=contact:user.email:readonly")


@router.get("/lark/callback")
async def lark_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_session),
):
    controller = get_oauth_controller(db)
    return await controller.lark_callback(code, state)


@router.get("/oidc")
async def oidc_login():
    if not config.OidcEnabled or not config.OidcAuthorizationEndpoint:
        raise HTTPException(status_code=400, detail="OIDC is not enabled or not configured")
    state = secrets.token_hex(16)
    return RedirectResponse(url=f"{config.OidcAuthorizationEndpoint}?client_id={config.OidcClientId}&redirect_uri={config.ServerAddress}/api/oauth/oidc/callback&response_type=code&scope=openid profile email&state={state}")


@router.get("/oidc/callback")
async def oidc_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_session),
):
    controller = get_oauth_controller(db)
    return await controller.oidc_callback(code, state)


@router.get("/state")
async def generate_oauth_state():
    return {"state": secrets.token_hex(16)}


@router.get("/wechat")
async def wechat_login():
    if not config.WeChatAuthEnabled:
        raise HTTPException(status_code=400, detail="WeChat OAuth is not enabled")
    return RedirectResponse(url=f"{config.ServerAddress}/api/oauth/wechat/qrcode")


@router.get("/wechat/qrcode")
async def wechat_qrcode():
    if not config.WeChatAuthEnabled:
        raise HTTPException(status_code=400, detail="WeChat OAuth is not enabled")
    return JSONResponse(content={
        "error": "WeChat OAuth requires additional WeChat server deployment. Please deploy WeChat server separately."
    })


@router.get("/wechat/callback")
async def wechat_callback(
    code: str = None,
    state: str = None,
    db: Session = Depends(get_session),
):
    if not config.WeChatAuthEnabled:
        raise HTTPException(status_code=400, detail="WeChat OAuth is not enabled")
    raise HTTPException(status_code=501, detail="WeChat OAuth requires additional WeChat server deployment")


@router.get("/wechat/bind")
async def wechat_bind(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    if not config.WeChatAuthEnabled:
        raise HTTPException(status_code=400, detail="WeChat OAuth is not enabled")
    raise HTTPException(status_code=501, detail="WeChat OAuth requires additional WeChat server deployment")