from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "dev"

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str

    OPERATOR_API_KEY: str

    SECRET_KEY: str


settings = Settings()