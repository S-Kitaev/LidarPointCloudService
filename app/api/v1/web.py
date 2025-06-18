import pathlib

from pydantic import ValidationError
from fastapi import (
    APIRouter, Request, Depends, Form, Cookie, HTTPException, Header, Path
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status

from app.crud.user import (
    get_user_by_name, get_user_by_id, get_user_by_email, create_user
)
from app.schemas.user import UserCreate
from app.core.security import verify_password, create_access_token, decode_access_token
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

# где лежат ваши html-шаблоны
TEMPLATES_DIR = pathlib.Path(__file__).resolve().parents[3] / "templates"
templates = Jinja2Templates(str(TEMPLATES_DIR))


def get_token(
    authorization_header: str | None = Header(None, alias="Authorization"),
    authorization_cookie: str | None = Cookie(None, alias="Authorization"),
) -> str:
    """Вытащить Bearer-токен из заголовка или из куки."""
    raw = authorization_header or authorization_cookie
    if not raw or not raw.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return raw.split(" ", 1)[1]


def require_authenticated_user(
    token: str = Depends(get_token),
    user_id: int = Path(..., ge=1),
    db=Depends(get_db),
):
    """
    Зависимость для защищённых эндпоинтов.
    Проверяет JWT, сравнивает sub с user_id и загружает пользователя из БД.
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if int(payload.get("sub", 0)) != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.get("/", response_class=HTMLResponse)
async def home_anon(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/registration", response_class=HTMLResponse)
async def registration_form(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})


@router.post("/registration", response_class=HTMLResponse)
async def registration_web(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    db=Depends(get_db),
):
    # проверяем дубликаты
    if get_user_by_name(db, username):
        error = "Имя пользователя уже занято"
    elif get_user_by_email(db, email):
        error = "Email уже зарегистрирован"
    elif len(username) > 20:
        error = "Логин не более 20 символов"
    elif len(email) > 50:
        error = "Email не более 50 символов"
    elif password != password2:
        error = "Пароли не совпадают"
    else:
        # валидируем email и хешируем пароль
        try:
            user_in = UserCreate(user_name=username, password=password, email=email)
        except ValidationError as ve:
            errs = ve.errors()
            error = "Неверный формат email" if errs and errs[0]["loc"] == ("email",) else "Некорректные данные"
        else:
            create_user(db, user_in)
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "registration.html", {"request": request, "error": error}
    )


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    user = get_user_by_name(db, username)
    if not user or not verify_password(password, user.user_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Неправильные учётные данные"}
        )

    token = create_access_token({"sub": str(user.user_id)})
    resp = RedirectResponse(f"/{user.user_id}", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        "Authorization", f"Bearer {token}",
        httponly=True, secure=False, samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    return resp


@router.get("/{user_id}", response_class=HTMLResponse)
async def home_user(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "home_main.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )


@router.get("/{user_id}/create", response_class=HTMLResponse)
async def create_cloud(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )


@router.get("/{user_id}/check", response_class=HTMLResponse)
async def check_cloud(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "check.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )


@router.get("/{user_id}/connect", response_class=HTMLResponse)
async def connect_cxd(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "connect.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )
