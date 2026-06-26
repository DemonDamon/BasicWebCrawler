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

    # Worker 常驻进程调度参数
    worker_min_delay_seconds: float = 30.0   # 两次抓取之间最短等待
    worker_max_delay_seconds: float = 180.0  # 两次抓取之间最长等待
    worker_idle_sleep_seconds: float = 60.0  # 队列为空时的轮询间隔
    worker_fetch_timeout_seconds: int = 20   # 单次 HTTP 请求超时

    @property
    def is_sqlite(self) -> bool:
        return self.collector_db_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
