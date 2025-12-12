from sqlalchemy import insert
from sqlalchemy.orm import Session
from app.models.experiment import Experiment, ExperimentChd
from app.models.user import User
from app.models.measurement import Measurement
from app.schemas.experiment import ExperimentCreate
from datetime import datetime
import asyncio
from typing import List
from app.db.session import SessionLocal, SessionChd 


def insert_experiment(db: Session, experiment: ExperimentCreate):
    result = db.execute(
        insert(Experiment).values(
            exp_dt=experiment.exp_dt,
            room_description=experiment.room_description,
            address=experiment.address,
            object_description=experiment.object_description,
            user_id=experiment.user_id
        ).returning(Experiment.id)
    )
    return result.scalar()


def insert_local_experiments_sync():
    """
    Копирует пользователей, эксперименты и измерения из local_db в global_db.
    Выполняется в рамках одной транзакции: либо сохранится всё, либо ничего.
    """
    print("Начало синхронизации...")
    chd_loaded_dt = datetime.now()
    
    with SessionLocal() as local_db, SessionChd() as global_db:
        try:
            local_users = local_db.query(User).all()
            user_map = {} 

            for l_user in local_users:
                g_user = global_db.query(User).filter(
                    User.user_name == l_user.user_name,
                    User.email == l_user.email
                ).first()
                
                if not g_user:
                    g_user = User(
                        user_name=l_user.user_name,
                        email=l_user.email,
                        user_password=l_user.user_password
                    )
                    global_db.add(g_user)
                    global_db.flush() 
                
                user_map[l_user.id] = g_user.id

            local_experiments = local_db.query(Experiment).all()

            for l_exp in local_experiments:
                local_user_id = l_exp.user_id
                global_user_id = user_map.get(local_user_id)

                if not global_user_id:
                    print(f"Skipping experiment {l_exp.id}: User not found.")
                    continue
                exists_identical = global_db.query(ExperimentChd).filter(
                    ExperimentChd.exp_dt == l_exp.exp_dt,
                    ExperimentChd.room_description == l_exp.room_description,
                    ExperimentChd.address == l_exp.address,
                    ExperimentChd.object_description == l_exp.object_description,
                    ExperimentChd.user_id == global_user_id
                ).first()
                if exists_identical:
                    print(f"Эксперимент {l_exp.id} уже есть в ЦХД, продолжаем")
                    continue
                
                g_exp = ExperimentChd(
                    exp_dt=l_exp.exp_dt,
                    room_description=l_exp.room_description,
                    address=l_exp.address,
                    object_description=l_exp.object_description,
                    user_id=global_user_id,          
                    chd_loaded_dt=chd_loaded_dt 
                )
                global_db.add(g_exp)
                global_db.flush() 

                local_measurements = local_db.query(Measurement).filter(
                    Measurement.experiment_id == l_exp.id
                ).all()


                mappings = [
                {
                    "experiment_id": g_exp.id,
                    "phi": m.phi,
                    "theta": m.theta,
                    "r": m.r
                }
                for m in local_measurements
                ]
                if mappings:
                    global_db.bulk_insert_mappings(Measurement, mappings)
            
            global_db.commit()
            print("Синхронизация успешно завершена.")

        except TimeoutError as e:
            global_db.rollback()
            print(f"Ошибка при синхронизации. Откат изменений. Детали: {str(e)}")
            raise TimeoutError(f"Ошибка {str(e)}")
        
        except SQLAlchemyError as e:
            global_db.rollback()
            print(f"Ошибка при синхронизации. Откат изменений. Детали: {str(e)}")
            raise SQLAlchemyError(f"Ошибка {str(e)}")
        
        except Exception as e:
            global_db.rollback()
            print(f"Неизвестная ошибка: {str(e)}")
            raise e


async def insert_local_experiments_to_chd():
    """
    Асинхронная обертка. Запускает синхронную логику в threadpool,
    чтобы не блокировать основной цикл FastAPI.
    """
    try:
        await asyncio.wait_for(
            asyncio.to_thread(insert_local_experiments_sync),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        print("Синхронизация прервана по таймауту.")
        raise TimeoutError("Время ожидания истекло. Не удалось синхронизировать БД.")


def get_mapped_global_user_id(local_user_id: int, global_session: Session) -> int | None:
    """
    Находит ID пользователя в глобальной БД, соответствующего локальному пользователю.
    """
    with SessionLocal() as local_db:
        l_user = local_db.query(User).filter(User.id == local_user_id).first()
    
    if not l_user:
        return None

    g_user = global_session.query(User).filter(
        User.user_name == l_user.user_name,
        User.email == l_user.email
    ).first()
    
    return g_user.id if g_user else None


def get_all_experiments(user_id: int | None = None, is_global_db: bool = False):
    if is_global_db:
        SessionFactory = SessionChd
    else:
        SessionFactory = SessionLocal

    with SessionFactory() as db:
        query = db.query(Experiment)

        if user_id is not None:
            target_id = user_id

            if is_global_db:
                target_id = get_mapped_global_user_id(user_id, db)
                if target_id is None:
                    return [] 

            query = query.filter(Experiment.user_id == target_id)

        return query.all()


async def get_all_experiments_async(user_id: int=None, is_global_db: bool=False):
    """
    Асинхронная оболочка для sync get_all_experiments.
    Выполняет блокирующую работу в threadpool.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(get_all_experiments, user_id, is_global_db),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        print("Получение экспериментов прервано по таймауту.")
        raise TimeoutError("Время ожидания истекло. Не удалось получить эксперименты.")



def get_experiment_by_id(experiment_id: int, source: str):
    """Получить эксперимент по ID"""
    if source == "chd":
        SessionFactory = SessionChd
    else:
        SessionFactory = SessionLocal

    with SessionFactory() as db:
        return db.query(Experiment).filter(
            Experiment.id == experiment_id
            ).first()