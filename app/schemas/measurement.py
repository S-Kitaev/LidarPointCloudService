from pydantic import BaseModel
from typing import List


class MeasurementData(BaseModel):
    phi: float
    theta: float
    r: float


class MeasurementCreate(BaseModel):
    measurements: List[MeasurementData]


class MeasurementRead(BaseModel):
    id: int
    experiment_id: int
    phi: float
    theta: float
    r: float
    # position: int