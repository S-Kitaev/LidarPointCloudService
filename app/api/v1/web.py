import pathlib

from pydantic import ValidationError
from fastapi import (
    APIRouter, Request, Depends, Form, Cookie, HTTPException, Header, Path, UploadFile, File, Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette import status

from app.crud.user import (
    get_user_by_name, get_user_by_id, get_user_by_email, create_user
)
from app.crud.experiment import insert_experiment, get_all_experiments_async, get_experiment_by_id, insert_local_experiments_to_chd
from app.crud.measurement import insert_measurements, get_measurements_by_experiment_id
from app.schemas.user import UserCreate
from app.schemas.experiment import ExperimentCreate
from app.schemas.measurement import MeasurementCreate, MeasurementData
from app.core.security import verify_password, create_access_token, decode_access_token
from app.db.session import get_db, get_chd
from app.core.config import settings
from sqlalchemy.exc import SQLAlchemyError
import json

import markdown

router = APIRouter()

# где лежат документы
DOCS_DIR = pathlib.Path(__file__).resolve().parents[3] / "docs"

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

    token = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(f"/{user.id}", status_code=status.HTTP_303_SEE_OTHER)
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
        {"request": request, "username": user.user_name, "user_id": user.id}
    )


@router.get("/{user_id}/create", response_class=HTMLResponse)
async def create_cloud(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "username": user.user_name, "user_id": user.id}
    )


@router.get("/{user_id}/check", response_class=HTMLResponse)
async def check_cloud(
    request: Request, 
    user=Depends(require_authenticated_user)
    ):
    """Страница выбора эксперимента для просмотра"""
    try:
        experiments = await get_all_experiments_async()
    except TimeoutError as e:
        return JSONResponse(status_code=408, content={"ok": False, "message": "Не удается получить эксперименты"})
    except Exception as exc:
        experiments = []
    return templates.TemplateResponse(
        "check.html",
        {"request": request, "username": user.user_name, "user_id": user.id, "experiments": experiments}
    )


@router.get("/{user_id}/check/{experiment_id}", response_class=HTMLResponse)
async def view_cloud(
    request: Request, 
    experiment_id: int, 
    user=Depends(require_authenticated_user), 
    db=Depends(get_db)
):
    """Страница просмотра облака точек для конкретного эксперимента"""
    experiment = get_experiment_by_id(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    
    return templates.TemplateResponse(
        "view_cloud.html",
        {
            "request": request, 
            "username": user.user_name, 
            "user_id": user.id, 
            "experiment": experiment,
            "experiment_id": experiment_id,
             "active_page": "check"
        }
    )

@router.get("/{user_id}/chd", response_class=HTMLResponse)
async def check_chd_cloud(
    request: Request,
    user=Depends(require_authenticated_user),
):
    """
    Всегда рендерим check_chd.html. Список экспериментов запрашивается
    отдельным AJAX-запросом к /{user_id}/chd/experiments
    """
    return templates.TemplateResponse(
        "check_chd.html",
        {
            "request": request,
            "username": user.user_name,
            "user_id": user.id
        }
    )

@router.get("/{user_id}/chd/experiments", response_class=JSONResponse)
async def chd_get_experiments_api(
    request: Request,
    user=Depends(require_authenticated_user)
):
    try:
        experiments = await get_all_experiments_async(user_id=user.id, is_global_db=True)

        result = [
            {
                "id": e.id,
                "exp_dt": (e.exp_dt.strftime('%d.%m.%Y %H:%M') if getattr(e, "exp_dt", None) else None),
                "room_description": e.room_description or "",
                "address": e.address or "",
                "object_description": e.object_description or "",
            }
            for e in (experiments or [])
        ]

        return JSONResponse(status_code=200, content={"ok": True, "experiments": result})
    except TimeoutError as e:
        return JSONResponse(status_code=408, content={"ok": False, "message": "Не удается получить эксперименты из ЦХД"})
    except Exception:
        return JSONResponse(status_code=503, content={"ok": False, "message": "Не удается получить эксперименты из ЦХД"})


@router.get("/{user_id}/chd/{experiment_id}", response_class=HTMLResponse)
async def view_chd_cloud(
    request: Request, 
    experiment_id: int, 
    user=Depends(require_authenticated_user), 
    db=Depends(get_chd)
):
    """Страница просмотра облака точек для конкретного эксперимента"""
    experiment = get_experiment_by_id(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    
    return templates.TemplateResponse(
        "view_cloud.html",
        {
            "request": request, 
            "username": user.user_name, 
            "user_id": user.id, 
            "experiment": experiment,
            "experiment_id": experiment_id,
            "active_page": "chd"    
        }
    )


@router.get("/{user_id}/api/experiments")
async def get_experiments_api(user=Depends(require_authenticated_user), db=Depends(get_db)):
    """API для получения списка экспериментов"""
    experiments = get_all_experiments(db)
    return JSONResponse(content=[
        {
            "id": exp.id,
            "exp_dt": exp.exp_dt.strftime("%Y-%m-%d %H:%M:%S") if exp.exp_dt else None,
            "room_description": exp.room_description,
            "address": exp.address,
            "object_description": exp.object_description
        }
        for exp in experiments
    ])


@router.get("/{user_id}/api/experiments/{experiment_id}/measurements")
async def get_measurements_api(
    experiment_id: int, 
    source: str = Query("local"), # Читаем параметр ?source=... (по дефолту local)
    user=Depends(require_authenticated_user),
    local_db=Depends(get_db),
    global_db=Depends(get_chd)
):
    """API для получения измерений эксперимента в сферических координатах"""

    if source == "chd":
        current_db = global_db
    else:
        current_db = local_db


    experiment = get_experiment_by_id(current_db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    
    measurements = get_measurements_by_experiment_id(current_db, experiment_id)
    
    if not measurements:
        raise HTTPException(status_code=404, detail="Измерения не найдены")
    
    # Преобразуем в список координат
    coordinates = []
    for m in measurements:
        coordinates.append({
            'phi': m.phi,
            'r': m.r,
            'theta': m.theta
        })
    
    return JSONResponse(content={
        "experiment": {
            "id": experiment.id,
            "exp_dt": experiment.exp_dt.strftime("%Y-%m-%d %H:%M:%S") if experiment.exp_dt else None,
            "room_description": experiment.room_description,
            "address": experiment.address,
            "object_description": experiment.object_description
        },
        "measurements_count": len(measurements),
        "coordinates": coordinates
    })


@router.post("/{user_id}/create/save")
async def insert_data(
        date: str = Form(...),
        room_description: str = Form(...),
        address: str = Form(...),
        object_description: str = Form(...),
        measurements_file: UploadFile = File(...),
        user=Depends(require_authenticated_user),
        db=Depends(get_db),
):
    try:
        content = await measurements_file.read()
        measurements_dict = json.loads(content)
        experiment = ExperimentCreate(exp_dt=date,
                                      room_description=room_description,
                                      address=address,
                                      object_description=object_description,
                                      user_id=user.id)
        exp_id = insert_experiment(db=db, experiment=experiment)
        measurement_create = MeasurementCreate(
            measurements=[MeasurementData(**item) for item in measurements_dict["measurements"]]
        )
        insert_measurements(db=db, measurement_data=measurement_create, experiment_id=exp_id)
        db.commit()
        return {"status": "success", "message": "Data inserted"}
    except SQLAlchemyError as e:
        db.rollback()
        return {"status": "error", "message": f"Database error: {str(e)}"}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@router.post("/{user_id}/chd/save")
async def synchronize_local_with_global_db(
        user=Depends(require_authenticated_user)
):
    try:
        await insert_local_experiments_to_chd()
        return {"status": "success", "message": "Data inserted"}
    except TimeoutError as e:
        return {"status": "error", "message": str(e)}
    except SQLAlchemyError as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/{user_id}/capture", response_class=HTMLResponse)
async def connect_cxd(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "capture.html",
        {"request": request, "username": user.user_name, "user_id": user.id})

@router.get("/{user_id}/docs/specs", response_class=HTMLResponse)
async def docs_specs(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "docs_specs.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )

@router.get("/{user_id}/docs/setup", response_class=HTMLResponse)
async def docs_specs(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "docs_setup.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )

def render_md_to_html(md_content: str) -> str:
    # Настройка markdown: поддержка таблиц, ссылок, заголовков
    return markdown.markdown(
        md_content,
        extensions=[
            "extra",
            "toc",
            "fenced_code",
            "sane_lists",
            "nl2br",
        ],
        output_format="html5",
    )

@router.get("/{user_id}/docs/setup/{doc_name}", response_class=HTMLResponse)
async def documentation_page(
    request: Request,
    doc_name: str,
    user=Depends(require_authenticated_user),
):
    # Ищем локальный .md файл
    md_path = DOCS_DIR / f"{doc_name}.md"
    if not md_path.exists():
        md_content = f"# Документация '{doc_name}' не найдена\n\nПопробуйте [вернуться на главную страницу](/{user.user_id})."
        source_info = ""
    else:
        md_content = md_path.read_text(encoding="utf-8")
        source_info = ""

    # Рендерим Markdown в HTML
    html_content = render_md_to_html(md_content)

    return templates.TemplateResponse(
        "docs_md_template.html",
        {
            "request": request,
            "username": user.user_name,
            "user_id": user.user_id,
            "doc_title": doc_name.replace("-", " ").replace("_", " ").title(),
            "doc_html": html_content,
            "source_info": source_info,
        }
    )