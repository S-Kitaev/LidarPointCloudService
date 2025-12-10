from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
    user_id = Column(
        Integer,
        ForeignKey("users.id"), 
        nullable=False,
        comment="ID пользователя (владельца)"
    )

    measurements = relationship("Measurement", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentChd(Base):
    __tablename__ = "experiments"

    __table_args__ = {'extend_existing': True}
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Уникальный идентификатор эксперимента"
    )
    exp_dt = Column(
        DateTime,
        nullable=False,
        comment="Дата и время эксперимента"
    )
    room_description = Column(
        String(1000), 
        nullable=True,
        comment="Описание помещения"
    )
    address = Column(
        String(200),
        nullable=True,
        comment="Адрес объекта"
    )
    object_description = Column(
        String(200),
        nullable=True,
        comment="Описание объекта"
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        comment="ID пользователя (владельца)"
    )
    chd_loaded_dt = Column(
        DateTime,
        nullable=True,
        comment="Время загрузки в ЦХД"
    )

    measurements = relationship(
        "Measurement", 
        cascade="all, delete-orphan"
    )
    
    user = relationship("User")