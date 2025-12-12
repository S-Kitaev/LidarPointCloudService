from app.db.session import SessionLocal, SessionChd 
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


def get_measurements_by_experiment_id(experiment_id: int, source: str):
    if source == "chd":
        SessionFactory = SessionChd
    else:
        SessionFactory = SessionLocal

    with SessionFactory() as db:
        measurements = db.query(Measurement).filter(Measurement.experiment_id == experiment_id).all()
        return measurements
