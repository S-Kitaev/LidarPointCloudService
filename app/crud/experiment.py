from sqlalchemy import insert
from sqlalchemy.orm import Session
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentCreate
from datetime import datetime


def insert_experiment(db: Session, experiment: ExperimentCreate):
    result = db.execute(
        insert(Experiment).values(
            exp_dt=str(datetime.now()),
            room_description=experiment.room_description,
            address=experiment.address,
            object_description=experiment.object_description
        ).returning(Experiment.id)
    )
    return result.scalar()


def get_all_experiments(db: Session):
    """Получить все эксперименты"""
    return db.query(Experiment).all()


def get_experiment_by_id(db: Session, experiment_id: int):
    """Получить эксперимент по ID"""
    return db.query(Experiment).filter(Experiment.id == experiment_id).first()