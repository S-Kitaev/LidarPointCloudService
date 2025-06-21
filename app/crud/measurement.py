from sqlalchemy.orm import Session
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementCreate


def insert_measurements(db: Session, measurement_data: MeasurementCreate, experiment_id: int):
    measurements = [
        Measurement(
            experiment_id=experiment_id,
            phi=item.phi,
            theta=item.theta,
            r=item.r,
            # position
        )
        for item in measurement_data.measurements
    ]

    db.bulk_save_objects(measurements)


def get_measurements_by_experiment_id(db: Session, experiment_id: int):
    """Получить все измерения для конкретного эксперимента"""
    return db.query(Measurement).filter(Measurement.experiment_id == experiment_id).all()
