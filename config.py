# config.py
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:password@127.0.0.1:5432/fleet"
    UPLOAD_DIR: str = "./uploads"


    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_SECRET: str | None = None


    class Config:
        env_file = ".env"

settings = Settings()
UPLOAD_PATH = Path(settings.UPLOAD_DIR)
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)