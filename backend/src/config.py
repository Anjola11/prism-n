from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    IS_PRODUCTION: bool

    JWT_KEY: str
    JWT_ALGORITHM: str
    ALLOWED_ORIGINS: list
    REDIS_URL: str
    BREVO_API_KEY: str
    BREVO_SENDER_NAME: str
    BREVO_EMAIL: str 
    DATABASE_URL: str
    ADMIN_EMAIL: str

    BAYSE_API_KEY: str

    model_config = SettingsConfigDict(
        env_file =".env",
        extra = "ignore"
    )

Config = Settings()
