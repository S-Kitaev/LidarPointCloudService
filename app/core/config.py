from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path(__file__) = /app/lidar/app/core/config.py
# .parent.parent.parent = /app/lidar
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    DATABASE_URL: str
    JWT_PRIVATE_KEY_PATH: str = str(BASE_DIR / "certs" / "jwt-private.pem")
    JWT_PUBLIC_KEY_PATH:  str = str(BASE_DIR / "certs" / "jwt-public.pem")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Lidar SSH
    LIDAR_HOST: str = "192.168.0.101"
    LIDAR_USER: str = "vr"
    LIDAR_PASS: str = "vr"
    LIDAR_REMOTE_PATH: str = "/home/vr/Desktop/lidar"

settings = Settings()