"""文章发布时间新鲜度判断（发现层 / Worker 共用）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from wechat_collector.parsers.wechat import parse_wechat_article_html


def is_publish_time_too_old(
    publish_time: datetime | None,
    *,
    max_age_days: int,
    now: datetime | None = None,
) -> bool:
    """发布时间早于 cutoff 则视为过旧；max_age_days<=0 表示不限制。"""
    if max_age_days <= 0 or publish_time is None:
        return False
    reference = now or datetime.now()
    cutoff = reference - timedelta(days=max_age_days)
    return publish_time < cutoff


def extract_publish_time_from_html(html: str, *, url: str | None = None) -> datetime | None:
    parsed = parse_wechat_article_html(html, url=url, save_snapshot_on_error=False)
    return parsed.publish_time
