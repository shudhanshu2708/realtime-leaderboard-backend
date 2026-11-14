from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+aiomysql://root:root@localhost:3306/leaderboard"
    redis_url: str = "redis://localhost:6379/0"
    # Replace in production with a long random value (>= 32 bytes).
    jwt_secret: str = "change-this-demo-secret-to-a-long-random-value-123456"
    jwt_expiration_seconds: int = 86400


settings = Settings()
