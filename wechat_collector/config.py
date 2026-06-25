from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    collector_db_url: str = "sqlite:///./wechat_collector.db"
    collector_api_token: str = "change-me-in-production"
    scheduler_max_account_interval_seconds: int = 60
    scheduler_empty_source_threshold: int = 3
    discovery_request_delay_seconds: float = 1.5

    @property
    def is_sqlite(self) -> bool:
        return self.collector_db_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
