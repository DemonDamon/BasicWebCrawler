"""Admin 可读写的采集配置（映射 Settings / .env）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from wechat_collector.config import Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"

SettingType = Literal["string", "int", "float", "bool"]
SettingGroup = Literal["database", "auth", "worker", "sogou"]


@dataclass(frozen=True)
class SettingFieldMeta:
    env_key: str
    attr: str
    label: str
    group: SettingGroup
    field_type: SettingType
    description: str
    sensitive: bool = False
    default: str | int | float | bool | None = None


SETTING_FIELDS: tuple[SettingFieldMeta, ...] = (
    SettingFieldMeta(
        "COLLECTOR_DB_URL",
        "collector_db_url",
        "数据库 URL",
        "database",
        "string",
        "SQLite 或 PostgreSQL 连接串",
    ),
    SettingFieldMeta(
        "COLLECTOR_API_TOKEN",
        "collector_api_token",
        "API Token",
        "auth",
        "string",
        "插件与 Admin 鉴权 Token",
        sensitive=True,
    ),
    SettingFieldMeta(
        "WORKER_MIN_DELAY_SECONDS",
        "worker_min_delay_seconds",
        "抓取最短间隔（秒）",
        "worker",
        "float",
        "两次抓取之间的最短随机等待",
        default=30.0,
    ),
    SettingFieldMeta(
        "WORKER_MAX_DELAY_SECONDS",
        "worker_max_delay_seconds",
        "抓取最长间隔（秒）",
        "worker",
        "float",
        "两次抓取之间的最长随机等待",
        default=180.0,
    ),
    SettingFieldMeta(
        "WORKER_IDLE_SLEEP_SECONDS",
        "worker_idle_sleep_seconds",
        "队列空闲轮询（秒）",
        "worker",
        "float",
        "候选池为空时的 sleep",
        default=60.0,
    ),
    SettingFieldMeta(
        "WORKER_FETCH_TIMEOUT_SECONDS",
        "worker_fetch_timeout_seconds",
        "HTTP 超时（秒）",
        "worker",
        "int",
        "单次抓取请求超时",
        default=20,
    ),
    SettingFieldMeta(
        "WORKER_MAX_ARTICLE_AGE_DAYS",
        "worker_max_article_age_days",
        "Worker 文章年龄（天）",
        "worker",
        "int",
        "丢弃早于 N 天的文章；0=不限制",
        default=14,
    ),
    SettingFieldMeta(
        "SCHEDULER_MAX_ACCOUNT_INTERVAL_SECONDS",
        "scheduler_max_account_interval_seconds",
        "同号最短抓取间隔（秒）",
        "worker",
        "int",
        "同一公众号两次抓取的最短间隔",
        default=60,
    ),
    SettingFieldMeta(
        "DISCOVERY_REQUEST_DELAY_SECONDS",
        "discovery_request_delay_seconds",
        "发现任务延迟（秒）",
        "worker",
        "float",
        "通用发现任务请求间隔",
        default=1.5,
    ),
    SettingFieldMeta(
        "SOGOU_PLAYWRIGHT_ENABLED",
        "sogou_playwright_enabled",
        "启用搜狗 Playwright 发现",
        "sogou",
        "bool",
        "为 true 时 sogou_poller 才会运行",
        default=False,
    ),
    SettingFieldMeta(
        "SOGOU_POLL_INTERVAL_SECONDS",
        "sogou_poll_interval_seconds",
        "搜狗巡检间隔（秒）",
        "sogou",
        "int",
        "sogou_poller 轮询间隔",
        default=14400,
    ),
    SettingFieldMeta(
        "SOGOU_MAX_ARTICLES_PER_ACCOUNT",
        "sogou_max_articles_per_account",
        "每号每轮最多文章数",
        "sogou",
        "int",
        "每个公众号每轮最多跟随的文章链接数",
        default=5,
    ),
    SettingFieldMeta(
        "SOGOU_MAX_QUERIES_PER_ORG",
        "sogou_max_queries_per_org",
        "每 org 搜索 query 数",
        "sogou",
        "int",
        "每个组织使用的搜狗搜索 query 数量上限",
        default=4,
    ),
    SettingFieldMeta(
        "SOGOU_USER_DATA_DIR",
        "sogou_user_data_dir",
        "浏览器 Profile 目录",
        "sogou",
        "string",
        "Playwright 持久化浏览器用户数据目录",
        default=".playwright/sogou",
    ),
    SettingFieldMeta(
        "SOGOU_HEADLESS",
        "sogou_headless",
        "搜狗无头模式",
        "sogou",
        "bool",
        "false 时可手动过验证码",
        default=True,
    ),
    SettingFieldMeta(
        "SOGOU_ARTICLE_DELAY_MIN_SECONDS",
        "sogou_article_delay_min_seconds",
        "搜狗文章间最短延迟（秒）",
        "sogou",
        "float",
        "搜狗文章跳转之间的最短等待",
        default=1.5,
    ),
    SettingFieldMeta(
        "SOGOU_ARTICLE_DELAY_MAX_SECONDS",
        "sogou_article_delay_max_seconds",
        "搜狗文章间最长延迟（秒）",
        "sogou",
        "float",
        "搜狗文章跳转之间的最长等待",
        default=3.0,
    ),
    SettingFieldMeta(
        "SOGOU_ACCOUNT_DELAY_MIN_SECONDS",
        "sogou_account_delay_min_seconds",
        "搜狗账号间最短延迟（秒）",
        "sogou",
        "float",
        "搜狗账号切换之间的最短等待",
        default=3.0,
    ),
    SettingFieldMeta(
        "SOGOU_ACCOUNT_DELAY_MAX_SECONDS",
        "sogou_account_delay_max_seconds",
        "搜狗账号间最长延迟（秒）",
        "sogou",
        "float",
        "搜狗账号切换之间的最长等待",
        default=6.0,
    ),
    SettingFieldMeta(
        "SOGOU_PAGE_TIMEOUT_MS",
        "sogou_page_timeout_ms",
        "搜狗页面超时（毫秒）",
        "sogou",
        "int",
        "Playwright 页面加载超时",
        default=30000,
    ),
    SettingFieldMeta(
        "SOGOU_MAX_ARTICLE_AGE_DAYS",
        "sogou_max_article_age_days",
        "搜狗发现文章年龄（天）",
        "sogou",
        "int",
        "0=不限制",
        default=14,
    ),
)

GROUP_LABELS: dict[SettingGroup, str] = {
    "database": "数据库",
    "auth": "API 鉴权",
    "worker": "Worker 抓取",
    "sogou": "搜狗 Playwright 发现",
}


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "••••" + value[-4:]


def _serialize_value(value: Any, field_type: SettingType) -> str | int | float | bool:
    if field_type == "bool":
        return bool(value)
    if field_type == "int":
        return int(value)
    if field_type == "float":
        return float(value)
    return str(value)


def _format_env_value(value: Any, field_type: SettingType) -> str:
    if field_type == "bool":
        return "true" if value else "false"
    return str(value)


def list_settings_for_admin() -> list[dict[str, Any]]:
    settings = get_settings()
    items: list[dict[str, Any]] = []
    for meta in SETTING_FIELDS:
        raw = getattr(settings, meta.attr)
        display = _serialize_value(raw, meta.field_type)
        if meta.sensitive and display:
            display = _mask_secret(str(display))
        items.append(
            {
                "key": meta.env_key,
                "label": meta.label,
                "group": meta.group,
                "group_label": GROUP_LABELS[meta.group],
                "type": meta.field_type,
                "description": meta.description,
                "sensitive": meta.sensitive,
                "default": meta.default,
                "value": display,
            }
        )
    return items


def _parse_update_value(raw: str, field_type: SettingType) -> str | int | float | bool:
    if field_type == "bool":
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if field_type == "int":
        return int(raw)
    if field_type == "float":
        return float(raw)
    return raw


_ENV_LINE_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def update_env_settings(updates: dict[str, str]) -> list[str]:
    """写入 .env，返回已更新的 env key 列表。敏感项传空或含 • 则跳过。"""
    meta_by_key = {m.env_key: m for m in SETTING_FIELDS}
    applied: list[str] = []

    normalized: dict[str, str] = {}
    for key, raw in updates.items():
        meta = meta_by_key.get(key)
        if meta is None:
            continue
        if meta.sensitive and (not raw or "•" in raw):
            continue
        value = _parse_update_value(raw, meta.field_type)
        normalized[key] = _format_env_value(value, meta.field_type)
        applied.append(key)

    if not normalized:
        return applied

    lines: list[str] = []
    seen: set[str] = set()
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        match = _ENV_LINE_RE.match(stripped)
        if match and match.group(1) in normalized:
            env_key = match.group(1)
            new_lines.append(f"{env_key}={normalized[env_key]}")
            seen.add(env_key)
        else:
            new_lines.append(line)

    for key, val in normalized.items():
        if key not in seen:
            new_lines.append(f"{key}={val}")

    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    get_settings.cache_clear()
    return applied


def env_example_exists() -> bool:
    return ENV_EXAMPLE_PATH.exists()
