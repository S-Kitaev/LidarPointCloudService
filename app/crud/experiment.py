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
    """
    chd_loaded_dt = datetime.now()
    with SessionLocal() as local_db, SessionChd() as global_db:
        local_users = local_db.query(User).all()
        user_map = {} 

        for l_user in local_users:
            g_user = global_db.query(User).filter(User.user_name == l_user.user_name).first()
            
            if not g_user:
                g_user = User(
                    user_name=l_user.user_name,
                    user_password=l_user.user_password,
                    email=l_user.email
                )
                global_db.add(g_user)
                global_db.commit()
                global_db.refresh(g_user)
            
            user_map[l_user.id] = g_user.id

        
        local_experiments = local_db.query(Experiment).all()

        for l_exp in local_experiments:
            local_user_id = l_exp.user_id
                
            global_user_id = user_map.get(local_user_id)

            if not global_user_id:
                print(f"Skipping experiment {l_exp.id}: User not found.")
                continue
            

            exists_identical = global_db.query(Experiment).filter(
                Experiment.exp_dt == l_exp.exp_dt,
                Experiment.room_description == l_exp.room_description,
                Experiment.address == l_exp.address,
                Experiment.object_description == l_exp.object_description,
                Experiment.user_id == global_user_id
            ).first()

            if exists_identical:
                # Эксперимент уже синхронизирован, пропускаем
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
            global_db.commit()
            global_db.refresh(g_exp) 

            local_measurements = local_db.query(Measurement).filter(
                Measurement.experiment_id == l_exp.id
            ).all()

            for l_meas in local_measurements:
                g_meas = Measurement(
                    experiment_id=g_exp.id,
                    phi=l_meas.phi,
                    theta=l_meas.theta,
                    r=l_meas.r
                )
                global_db.add(g_meas)
            
            global_db.commit()

        print("Синхронизация завершена.")

async def insert_local_experiments_to_chd():
    """
    Асинхронная обертка. Запускает синхронную логику в threadpool,
    чтобы не блокировать основной цикл FastAPI.
    """
    try:
        await asyncio.wait_for(
            asyncio.to_thread(insert_local_experiments_sync),
            timeout=20.0
        )
    except asyncio.TimeoutError:
        print("Синхронизация прервана по таймауту.")
        raise TimeoutError("Время ожидания истекло. Не удалось синхронизировать БД.")


def get_all_experiments(user_id: int=None, is_global_db=False):
    if is_global_db:
        SessionFactory = SessionChd
    else:
        SessionFactory = SessionLocal
    
    with SessionFactory() as db:
        if user_id is None:
            experiments = db.query(Experiment).all()
        elif isinstance(user_id, int):
            if is_global_db:
                 experiments = db.query(Experiment).filter(Experiment.user_id == user_id).all()
            else:
                 experiments = db.query(Experiment).all() 
        else:
            raise ValueError("invalid user_id")
    
    return experiments


async def get_all_experiments_async(user_id: int=None, is_global_db: bool=False):
    """
    Асинхронная оболочка для sync get_all_experiments.
    Выполняет блокирующую работу в threadpool.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(get_all_experiments, user_id, is_global_db),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        print("Получение экспериментов прервано по таймауту.")
        raise TimeoutError("Время ожидания истекло. Не удалось получить эксперименты.")



def get_experiment_by_id(db: Session, experiment_id: int):
    """Получить эксперимент по ID"""
    return db.query(Experiment).filter(
        Experiment.id == experiment_id
        ).first()