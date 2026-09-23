from functools import lru_cache
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Aphrodize"
    app_env: str = "development"
    database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_user: str = "aphrodize"
    postgres_password: str = ""
    postgres_db: str = "aphrodize"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aphrodize"
    minio_secret_key: str = "change-me-in-production"
    minio_secure: bool = False
    minio_bucket: str = "aphrodize-private"
    label_studio_url: str = "http://localhost:8080"
    label_studio_api_key: str = ""
    api_username: str = "aphrodize"
    api_password: str = ""
    mlflow_tracking_uri: str = "http://localhost:5000"
    model_version: str = "unconfigured"
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            "postgresql+asyncpg://"
            f"{quote(self.postgres_user, safe='')}:{quote(self.postgres_password, safe='')}"
            f"@{self.postgres_host}:5432/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
