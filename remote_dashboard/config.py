"""Settings for the dashboard frontend."""

from functools import lru_cache
from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class DashboardSettings(BaseSettings):
    api_base_url: HttpUrl | str = "http://localhost:8100/api"
    ai_base_url: str = "http://localhost:8001"
    timeout: float = 10.0
    timezone: str = "America/Sao_Paulo"

    class Config:
        env_prefix = "ARGUS_"
        env_file = ".env"


@lru_cache
def get_settings() -> DashboardSettings:
    return DashboardSettings()
