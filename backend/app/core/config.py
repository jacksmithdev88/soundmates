from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    SPOTIFY_REDIRECT_URL: str
    JWT_SECRET: str
    
    FRONTEND_URL: str
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: str

    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()