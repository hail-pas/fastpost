import os
import pathlib
import multiprocessing
from typing import Any, Dict, List, Optional
from functools import lru_cache

from pydantic import EmailStr, BaseSettings, validator, root_validator

ROOT = pathlib.Path(__file__).parent.parent


class Settings(BaseSettings):
    # ProjectInfo
    PROJECT_NAME: str = "FastPost"
    SERVER_URL: str = "http:127.0.0.1:8000"
    DESCRIPTION: str = "Fastapi-start-kit with Postgre and sqlalchemy"
    ENVIRONMENT: str = "Development"  # Test、 Production
    DEBUG: bool = True

    # # ApiInfo
    # API_V1_ROUTE: str = "/api"
    # OPED_API_ROUTE: str = "/api/openapi.json"

    # SentryDsn
    SENTRY_DSN: Optional[str]

    # gunicorn
    WORKERS: int = multiprocessing.cpu_count() * int(os.getenv("WORKERS_PER_CORE", "2")) + 1

    @validator("SENTRY_DSN", pre=True)
    def sentry_dsn_can_be_blank(cls, v: str, values, **kwargs) -> Optional[str]:
        if not v:
            return ""
        return v

    # DataBase
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str
    DB_NAME: str
    DB_PASSWORD: str

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: str = "6379"
    REDIS_PASSWORD: str = None

    # SocketIO Redis Manager
    SIO_REDIS_URL: str = f"redis://:{REDIS_PASSWORD}@{REDIS_PORT}:{REDIS_PORT}/4"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "http://localhost:9091"

    # Template
    TEMPLATE_PATH: str = f"{ROOT}/templates"

    # Static
    STATIC_PATH: str = "/static"
    STATIC_DIR: str = f"{ROOT}/static"

    # JWT
    JWT_SECRET: str = "oUdXHMQgh1jHQu0o5xxqqeEkQ0fBfUoQilWmtOnlJdE="
    JWT_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    AES_SECRET: str = "MFu5wrmUD1POvPXyfyxWFvLYbj2kMgY6IxSSsIAUmcs="
    SIGN_SECRET: str = "REdzQ1j00HhmvVmpUs4d3GakvtISX/6QZJE3ONhMIQE="

    # logging
    LOGGING_CONFIG: Dict = None

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int]
    SMTP_HOST: Optional[str]
    SMTP_USER: Optional[str]
    SMTP_PASSWORD: Optional[str]
    EMAILS_FROM_EMAIL: Optional[EmailStr]
    EMAILS_FROM_NAME: Optional[str]

    # IP WhiteList
    ALLOWED_HOST_LIST: List[str] = []

    @validator("EMAILS_FROM_NAME")
    def get_project_name(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            return values["PROJECT_NAME"]
        return v

    @property
    def POSTGRES_DATABASE_URL_ASYNC(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def POSTGRES_DATABASE_URL_SYNC(self):
        return f"postgresql+pyscopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
