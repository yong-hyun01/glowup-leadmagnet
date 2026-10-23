from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./dev.db"
    # 공개 폼이 외부에 노출되는 기준 URL (배포 링크·CSP connect-src 에 사용)
    public_base_url: str = "http://localhost:8000"
    session_max_age_seconds: int = 60 * 60 * 8
    max_html_bytes: int = 512 * 1024
    admin_email: str = "admin@example.com"
    admin_password: str = "admin1234"


@lru_cache
def get_settings() -> Settings:
    return Settings()
