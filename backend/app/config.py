from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite:///./aegis.db"
    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    encryption_key_previous: str = ""
    cors_origins: str = "http://localhost:3000"
    cookie_name: str = "aegis_session"
    cookie_secure: bool = False
    session_ttl_hours: int = 12
    session_idle_hours: int = 8
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_ip: int = 20
    auth_rate_limit_account: int = 10
    auth_lockout_threshold: int = 10
    auth_lockout_minutes: int = 15
    trusted_proxy_ips: str = "127.0.0.1,::1"
    max_request_bytes: int = 1_048_576
    mfa_required_for_admins: bool = False
    max_concurrent_assessments_per_org: int = 2
    max_concurrent_assessments_global: int = 8
    default_retention_days: int = 365
    log_level: str = "INFO"
    billing_enforce: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_professional: str = ""
    stripe_price_business: str = ""
    public_app_url: str = "http://localhost:3000"
    celery_broker_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = "reports@aegis.example"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
