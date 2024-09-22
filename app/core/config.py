from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets
from urllib.parse import quote_plus

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changethissecretkey"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SERVER_NAME: Optional[str] = None
    SERVER_HOST: Optional[str] = None
    BACKEND_CORS_ORIGINS: List[str] = []

    PROJECT_NAME: str = "Lottery Aggregator"
    SENTRY_DSN: Optional[str] = None

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str

    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEMPLATES_DIR: str = "/app/app/email-templates/build"
    EMAILS_ENABLED: bool = False

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return "postgresql://{}:{}@{}:{}/{}".format(
            self.POSTGRES_USER,
            quote_plus(self.POSTGRES_PASSWORD),
            self.POSTGRES_SERVER,
            self.POSTGRES_PORT,
            self.POSTGRES_DB
        )

    FIRST_SUPERUSER: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    USERS_OPEN_REGISTRATION: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
print(f"Database URL: {settings.SQLALCHEMY_DATABASE_URI}")