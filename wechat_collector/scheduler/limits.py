"""采集频率与并发限制（方案 §6.3）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from wechat_collector.config import get_settings
from wechat_collector.db.models import ArticleCandidate
from wechat_collector.scheduler.retry import utcnow


def account_recently_crawled(
    db: Session,
    account_id: int | None,
    *,
    now: datetime | None = None,
) -> bool:
    if account_id is None:
        return False

    settings = get_settings()
    interval = timedelta(seconds=settings.scheduler_max_account_interval_seconds)
    threshold = (now or utcnow()) - interval

    recent = db.scalar(
        select(ArticleCandidate.id)
        .where(
            ArticleCandidate.account_id == account_id,
            ArticleCandidate.status.in_(("processing", "success")),
            ArticleCandidate.crawled_at.is_not(None),
            ArticleCandidate.crawled_at >= threshold,
        )
        .limit(1)
    )
    if recent:
        return True

    processing = db.scalar(
        select(ArticleCandidate.id)
        .where(
            ArticleCandidate.account_id == account_id,
            ArticleCandidate.status == "processing",
        )
        .limit(1)
    )
    return processing is not None
