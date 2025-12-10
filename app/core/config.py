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

    JWT_PRIVATE_KEY_PATH: str = str(BASE_DIR / "certs" / "jwt-private.pem")
    JWT_PUBLIC_KEY_PATH:  str = str(BASE_DIR / "certs" / "jwt-public.pem")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Lidar SSH
    LIDAR_HOST: str = "192.168.0.101"
    LIDAR_USER: str = "vr"
    LIDAR_PASS: str = "vr"
    LIDAR_REMOTE_PATH: str = "/home/vr/Desktop/lidar"

    DATABASE_URL: str
    
    CHD_HOST: str
    CHD_PORT: str = "5432"  
    CHD_USER: str
    CHD_PASS: str
    CHD_NAME: str


    @property
    def CHD_URL(self) -> str:
        encoded_pass = self.CHD_PASS
        
        return (
            f"postgresql://{self.CHD_USER}:{encoded_pass}"
            f"@{self.CHD_HOST}:{self.CHD_PORT}/{self.CHD_NAME}"
        )

settings = Settings()