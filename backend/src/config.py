import json
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    IS_PRODUCTION: bool = False

    JWT_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: list[str] = ["*"]
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 12
    REDIS_OPERATION_CONCURRENCY: int = 6
    BREVO_API_KEY: str = ""
    BREVO_SENDER_NAME: str = "Prism"
    BREVO_EMAIL: str = ""
    DATABASE_URL: str

    BAYSE_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

Config = Settings()

