import pathlib

from pydantic import ValidationError
from fastapi import (
    APIRouter, Request, Depends, Form, Cookie, HTTPException, Header, Path, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette import status

from app.crud.user import (
    get_user_by_name, get_user_by_id, get_user_by_email, create_user
)
from app.crud.experiment import insert_experiment, get_all_experiments, get_experiment_by_id
from app.crud.measurement import insert_measurements, get_measurements_by_experiment_id
from app.schemas.user import UserCreate
from app.schemas.experiment import ExperimentCreate
from app.schemas.measurement import MeasurementCreate, MeasurementData
from app.core.security import verify_password, create_access_token, decode_access_token
from app.db.session import get_db
from app.core.config import settings
from sqlalchemy.exc import SQLAlchemyError
import json

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
async def check_cloud(request: Request, user=Depends(require_authenticated_user), db=Depends(get_db)):
    """Страница выбора эксперимента для просмотра"""
    experiments = get_all_experiments(db)
    return templates.TemplateResponse(
        "check.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id, "experiments": experiments}
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
            "user_id": user.user_id, 
            "experiment": experiment,
            "experiment_id": experiment_id
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
    user=Depends(require_authenticated_user), 
    db=Depends(get_db)
):
    """API для получения измерений эксперимента в сферических координатах"""
    experiment = get_experiment_by_id(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Эксперимент не найден")
    
    measurements = get_measurements_by_experiment_id(db, experiment_id)
    
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
        db=Depends(get_db),
):
    try:
        content = await measurements_file.read()
        measurements_dict = json.loads(content)
        experiment = ExperimentCreate(exp_dt=date,
                                      room_description=room_description,
                                      address=address,
                                      object_description=object_description)

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


@router.get("/{user_id}/connect", response_class=HTMLResponse)
async def connect_cxd(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "connect.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id}
    )

@router.get("/{user_id}/capture", response_class=HTMLResponse)
async def connect_cxd(request: Request, user=Depends(require_authenticated_user)):
    return templates.TemplateResponse(
        "capture.html",
        {"request": request, "username": user.user_name, "user_id": user.user_id})

