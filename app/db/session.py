from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
engine_chd = create_engine(settings.CHD_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionChd = sessionmaker(autocommit=False, autoflush=False, bind=engine_chd)

def get_db():
    db = SessionLocal() 
    try:
        yield db
    finally:
        db.close()

def get_chd():
    db = SessionChd()
    try:
        yield db
    finally:
        db.close()
