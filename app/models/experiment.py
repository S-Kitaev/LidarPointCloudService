from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Уникальный идентификатор эксперимента"
    )
    exp_dt = Column(
        DateTime,
        comment="Дата и время эксперимента"
    )
    room_description = Column(
        String(300),
        nullable=True,
        comment="Описание помещения"
    )
    address = Column(
        String(100),
        comment="Адрес объекта"
    )
    object_description = Column(
        String(300),
        nullable=True,
        comment="Описание объекта"
    )

    measurements = relationship("Measurement", back_populates="experiment", cascade="all, delete-orphan")