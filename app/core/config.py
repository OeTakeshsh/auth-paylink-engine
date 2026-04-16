from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url: str
    redis_url: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @field_validator('database_url')
    @classmethod
    def ensure_async_driver(cls, v: str) -> str:
        if v.startswith('postgresql://') and '+asyncpg' not in v:
            v = v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return v

settings = Settings()
