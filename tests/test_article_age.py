"""文章新鲜度工具单测。"""

from __future__ import annotations

from datetime import datetime, timedelta

from wechat_collector.utils.article_age import is_publish_time_too_old


def test_is_publish_time_too_old_respects_cutoff() -> None:
    now = datetime(2026, 6, 27, 12, 0, 0)
    recent = now - timedelta(days=3)
    stale = now - timedelta(days=30)

    assert not is_publish_time_too_old(recent, max_age_days=14, now=now)
    assert is_publish_time_too_old(stale, max_age_days=14, now=now)


def test_is_publish_time_too_old_disabled_when_zero() -> None:
    stale = datetime(2020, 1, 1)
    assert not is_publish_time_too_old(stale, max_age_days=0)


def test_is_publish_time_too_old_unknown_publish_time() -> None:
    assert not is_publish_time_too_old(None, max_age_days=14)
