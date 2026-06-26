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

    # RSSHub 巡检配置
    rsshub_base_url: str = "http://127.0.0.1:1200"
    rss_poll_interval_seconds: int = 1800          # 巡检轮询间隔（30min）
    rss_request_delay_min_seconds: float = 2.0     # 每条路由请求后最短等待
    rss_request_delay_max_seconds: float = 5.0     # 每条路由请求后最长等待
    rss_request_timeout_seconds: int = 15          # RSS 请求超时

    # Playwright 搜狗发现（默认关闭，需显式开启）
    sogou_playwright_enabled: bool = False
    sogou_poll_interval_seconds: int = 14400       # 巡检间隔（4h）
    sogou_max_articles_per_account: int = 5        # 每账号每轮最多跟随跳转的文章数
    sogou_user_data_dir: str = ".playwright/sogou"  # 持久化浏览器 profile（养 cookie）
    sogou_headless: bool = True
    sogou_article_delay_min_seconds: float = 1.5   # 文章跳转间最短等待
    sogou_article_delay_max_seconds: float = 3.0   # 文章跳转间最长等待
    sogou_account_delay_min_seconds: float = 3.0   # 账号间最短等待
    sogou_account_delay_max_seconds: float = 6.0   # 账号间最长等待
    sogou_page_timeout_ms: int = 30000             # 页面加载超时（毫秒）

    @property
    def is_sqlite(self) -> bool:
        return self.collector_db_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
