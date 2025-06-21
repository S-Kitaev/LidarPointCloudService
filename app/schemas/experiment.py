from pydantic import BaseModel


class ExperimentCreate(BaseModel):
    exp_dt: str
    room_description: str | None = None
    address: str
    object_description: str | None = None


class ExperimentRead(BaseModel):
    exp_dt: str
    room_description: str | None
    address: str
    object_description: str | None