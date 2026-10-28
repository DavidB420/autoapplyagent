from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/job_agent.db"
    host: str = "0.0.0.0"
    port: int = 8000
    worker_poll_seconds: float = 3.0
    max_applications_per_run: int = 10
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    auto_submit: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def data_dir(self) -> Path:
        return Path("./data")

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
