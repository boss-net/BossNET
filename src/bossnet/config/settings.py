import os
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator, model_validator, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Bangladesh Education Data Warehouse"

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "False").lower() in ("true", "1", "t")
    WORKERS: int = int(os.getenv("WORKERS", "1"))

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes",
        json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"},
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "student_data_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # SQLAlchemy
    SQL_ECHO: bool = DEBUG
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # Email (for password reset, etc.)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Testing
    TESTING: bool = os.getenv("TESTING", "False").lower() in ("true", "1", "t")
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_student_data_db"
    )

    # Security Headers
    SECURITY_HEADERS: Dict[str, Any] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }

    # Logging
    LOG_LEVEL: str = "INFO"

    # First superuser
    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "changethis")

    # Computed properties
    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            if not self.DATABASE_URL.startswith("postgresql+asyncpg"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Validators
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return v

    @validator("DEBUG", pre=True)
    def validate_debug(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and v:
            raise ValueError("DEBUG cannot be True in production")
        return v

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @model_validator(mode="before")
    @classmethod
    def assemble_cors_origins(cls, values: dict) -> dict:
        if "CORS_ORIGINS" in values:
            cors_origins = values["CORS_ORIGINS"]
            if isinstance(cors_origins, str):
                if not cors_origins.startswith("["):
                    values["CORS_ORIGINS"] = [i.strip() for i in cors_origins.split(",") if i.strip()]
            elif not isinstance(cors_origins, list):
                raise ValueError("CORS_ORIGINS must be a string or a list of strings")
        return values

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES", mode="before")
    def parse_access_token_expire_minutes(cls, v):
        if isinstance(v, str):
            # Extract just the number if there's a comment
            v = v.split("#")[0].strip()
            try:
                return int(v)
            except ValueError:
                raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer")
        return v

    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return v

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", env_file_encoding="utf-8", extra="ignore"  # Ignore extra environment variables
    )


# Create settings instance
settings = Settings()


# For dependency injection
def get_settings() -> Settings:
    return settings
