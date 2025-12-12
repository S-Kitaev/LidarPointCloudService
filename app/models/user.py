from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"  

    id = Column(Integer, primary_key=True, index=True)
    user_name  = Column(String(20), nullable=False, unique=True, index=True)
    user_password = Column(String(60), nullable=False)
    email = Column(String(50), nullable=True, unique=True, index=True)

    experiments = relationship(
        "ExperimentChd", 
        back_populates="user"
    )