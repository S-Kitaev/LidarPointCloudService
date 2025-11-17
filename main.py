# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.exception_handlers import http_exception_handler as default_http_handler
from fastapi.openapi.utils import get_openapi

from app.api.v1.web import router as web_router
from app.api.v1.lidar import router as lidar_router
from app.db.base import Base
from app.db.session import engine

# Авто-создаём все таблицы (для разработки)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lidar API")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    # Определяем схему bearerAuth
    schema.setdefault("components", {}) \
          .setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Добавляем её ко всем операциям по умолчанию
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            operation.setdefault("security", []).append({"bearerAuth": []})

    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi


# Статика для CSS/JS/картинок
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS — разрешаем фронту на 8000/8001
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# favicon
BASE_DIR = Path(__file__).resolve().parent

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(BASE_DIR / "static" / "images" / "logo.png")


# Перехватываем 401 и редиректим на /login
@app.exception_handler(HTTPException)
async def auth_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=303)
    return await default_http_handler(request, exc)


# Все ваши веб-роуты в одном месте
app.include_router(web_router)
app.include_router(lidar_router, prefix="/api/lidar")