import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db"
    )
    GCP_PROJECT_ID: str = "shadow-ai-discovery-demo"
    # Port to run backend
    PORT: int = 8000

    model_config = SettingsConfigDict(env_prefix="SHADOW_AI_")


settings = Settings()
