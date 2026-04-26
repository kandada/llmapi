# Routers package
from .api import router as api_router
from .relay import router as relay_router
from .web import router as web_router
from .external import router as external_router

__all__ = [
    "api_router",
    "relay_router",
    "web_router",
    "external_router",
]
