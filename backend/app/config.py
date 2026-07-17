from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration. Values come from environment variables or backend/.env.

    DATABASE_URL defaults to a local SQLite file so the app runs with zero setup.
    Point it at Postgres (e.g. postgresql://journey:journey_pass@localhost:5432/journey_db)
    when the Docker database is running.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./journey.db"
    app_secret: str = "dev-only-secret-do-not-use-in-production-1234567890"
    token_expire_minutes: int = 60

    # "dev": /auth/apple|google accept any string as the identity (local testing).
    # "production": id_tokens are verified against Apple/Google JWKS.
    auth_mode: str = "dev"
    apple_audience: str = ""   # your iOS bundle id, e.g. com.akhil.thejourney
    google_audience: str = ""  # your Google OAuth client id


@lru_cache
def get_settings() -> Settings:
    return Settings()
