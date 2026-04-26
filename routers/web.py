from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles
import os

from database import get_session
from schemas.request import StatusResponse
from config import config

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@router.get("/")
async def index():
    return HTMLResponse(content=open(os.path.join(BASE_DIR, "web", "index.html")).read())


@router.get("/shop")
async def shop():
    return HTMLResponse(content=open(os.path.join(BASE_DIR, "web", "shop.html")).read())


@router.get("/static/{path:path}")
async def static_files(path: str):
    file_path = os.path.join(BASE_DIR, "web", "static", path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "Not found"}, status_code=404)


def mount_static_files(app):
    static_dir = os.path.join(BASE_DIR, "web", "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")