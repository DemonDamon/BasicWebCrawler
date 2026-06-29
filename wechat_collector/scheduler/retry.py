"""失败重试指数退避（方案 §6.2）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

BACKOFF_MINUTES = (10, 60, 360)
MANUAL_RETRY_THRESHOLD = 4


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_next_retry_at(retry_count: int, *, now: datetime | None = None) -> datetime:
    base = now or utcnow()
    index = max(0, min(retry_count - 1, len(BACKOFF_MINUTES) - 1))
    return base + timedelta(minutes=BACKOFF_MINUTES[index])


def should_escalate_to_manual(retry_count: int) -> bool:
    return retry_count >= MANUAL_RETRY_THRESHOLD


def is_retry_due(next_retry_at: datetime | None, *, now: datetime | None = None) -> bool:
    if next_retry_at is None:
        return True
    return next_retry_at <= (now or utcnow())
