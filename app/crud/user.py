from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password

def get_user_by_name(db: Session, user_name: str):
    return db.query(User).filter(User.user_name == user_name).first()

def get_user_by_id(db, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_in: UserCreate):
    user = User(
        user_name = user_in.user_name,
        user_password = hash_password(user_in.password),
        email = user_in.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user