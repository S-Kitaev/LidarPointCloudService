from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Уникальный идентификатор измерения"
    )
    experiment_id = Column(
        Integer,
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        comment="Ссылка на эксперимент"
    )
    phi = Column(
        Float,
        comment="Угол фи в полярной системе координат"
    )
    theta = Column(
        Float,
        comment="Угол тета в сферической системе координат"
    )
    r = Column(
        Float,
        comment="Радиус-вектор в полярной системе координат"
    )
    # position = Column(
    #     Integer,
    #     comment="Позиция измерения в последовательности"
    # )

    experiment = relationship("Experiment", back_populates="measurements")