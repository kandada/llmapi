from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers import api, relay, web
from routers import shop, callback, admin_shop, external
from controllers.auth import oauth_router
from database import init_db
from config import config

import payment.adapters.stripe_adapter
import payment.adapters.paypal_adapter


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM API Gateway",
        description="OpenAI-compatible API Gateway",
        version="0.0.1",
    )

    app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        init_db()

    app.include_router(api.router)
    app.include_router(relay.router)
    app.include_router(oauth_router)
    app.include_router(web.router)

    app.include_router(shop.router)
    app.include_router(callback.router)
    app.include_router(admin_shop.router)
    app.include_router(external.router)

    web.mount_static_files(app)

    return app