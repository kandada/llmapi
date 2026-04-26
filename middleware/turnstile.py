from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from config import config


class TurnstileMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not config.TurnstileCheckEnabled:
            return await call_next(request)

        if request.method == "GET":
            return await call_next(request)

        turnstile_token = request.headers.get("CF-Turnstile-Token") or \
                        request.form().get("cf-turnstile-response") if request.method == "POST" else None

        if not turnstile_token:
            body = await request.body()
            if body:
                try:
                    import json
                    data = json.loads(body)
                    turnstile_token = data.get("cf-turnstile-response")
                except:
                    pass

        if not turnstile_token:
            raise HTTPException(status_code=403, detail="Turnstile verification required")

        is_valid = await self._verify_token(turnstile_token, request.client.host if request.client else "")

        if not is_valid:
            raise HTTPException(status_code=403, detail="Turnstile verification failed")

        return await call_next(request)

    async def _verify_token(self, token: str, ip: str) -> bool:
        if not config.TurnstileSecretKey:
            return True

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                    data={
                        "secret": config.TurnstileSecretKey,
                        "response": token,
                        "remoteip": ip,
                    }
                )

            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)
        except Exception as e:
            print(f"Turnstile verification error: {e}")

        return False


async def verify_turnstile_token(token: str, ip: str = "") -> bool:
    if not config.TurnstileCheckEnabled:
        return True

    if not token:
        return False

    if not config.TurnstileSecretKey:
        return True

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": config.TurnstileSecretKey,
                    "response": token,
                    "remoteip": ip,
                }
            )

        if response.status_code == 200:
            result = response.json()
            return result.get("success", False)
    except Exception as e:
        print(f"Turnstile verification error: {e}")

    return False