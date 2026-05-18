from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://liquidmind:liquidmind_dev@localhost:5432/liquidmind"
    database_url_sync: str = "postgresql://liquidmind:liquidmind_dev@localhost:5432/liquidmind"
    redis_url: str = "redis://localhost:6379/0"
    app_name: str = "LiquidMind"
    debug: bool = True

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
