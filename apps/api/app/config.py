from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ABA_", env_file=".env", extra="ignore")

    app_name: str = "ABA Family API"
    environment: str = "development"
    database_url: str = "sqlite:///./aba_api.db"
    jwt_secret: str = "development-only-change-me-please"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = "http://localhost:5173"
    minimax_api_key: str | None = None
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M2.7"
    knowledge_path: str = "docs/知识库"
    upload_path: str = "uploads"
    redis_url: str | None = None
    storage_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "aba-reports"
    s3_region: str = "us-east-1"
    login_rate_limit: int = 10
    public_chat_rate_limit: int = 20

    def validate_runtime(self) -> None:
        if self.environment != "production":
            return
        if len(self.jwt_secret) < 32 or self.jwt_secret == "development-only-change-me-please":
            raise RuntimeError("生产环境必须配置至少 32 位的 ABA_JWT_SECRET")
        if not self.database_url.startswith("postgresql"):
            raise RuntimeError("生产环境必须使用 PostgreSQL")
        if not self.redis_url:
            raise RuntimeError("生产环境必须配置 ABA_REDIS_URL")
        if self.storage_backend not in {"local", "s3"}:
            raise RuntimeError("ABA_STORAGE_BACKEND 必须是 local 或 s3")
        if self.storage_backend == "s3" and not all(
            (self.s3_endpoint_url, self.s3_access_key, self.s3_secret_key, self.s3_bucket)
        ):
            raise RuntimeError("S3 存储需要完整配置 endpoint、access key、secret key 和 bucket")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
