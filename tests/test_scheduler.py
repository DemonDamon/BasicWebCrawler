from datetime import timedelta

import pytest

from wechat_collector.db.models import ArticleCandidate
from wechat_collector.scheduler.retry import (
    MANUAL_RETRY_THRESHOLD,
    compute_next_retry_at,
    should_escalate_to_manual,
    utcnow,
)
from wechat_collector.services import candidate_service, org_service


def test_backoff_schedule() -> None:
    now = utcnow()
    t1 = compute_next_retry_at(1, now=now)
    t2 = compute_next_retry_at(2, now=now)
    t3 = compute_next_retry_at(3, now=now)
    assert t1 - now == timedelta(minutes=10)
    assert t2 - now == timedelta(hours=1)
    assert t3 - now == timedelta(hours=6)


def test_manual_threshold() -> None:
    assert not should_escalate_to_manual(MANUAL_RETRY_THRESHOLD - 1)
    assert should_escalate_to_manual(MANUAL_RETRY_THRESHOLD)


def test_mark_failed_retries_then_manual(db_session, monkeypatch) -> None:
    monkeypatch.setenv("COLLECTOR_API_TOKEN", "x")
    candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=retryflow&mid=1&idx=1",
        source="manual",
    )
    task = candidate_service.get_next_task(db_session)
    assert task is not None

    for expected_status in ("retrying", "retrying", "retrying"):
        candidate_service.mark_failed(db_session, task.id, fail_reason="403")
        refreshed = db_session.get(ArticleCandidate, task.id)
        assert refreshed is not None
        assert refreshed.status == expected_status
        assert refreshed.next_retry_at is not None
        refreshed.next_retry_at = utcnow() - timedelta(minutes=1)
        db_session.commit()
        task = candidate_service.get_next_task(db_session)
        assert task is not None

    candidate_service.mark_failed(db_session, task.id, fail_reason="403")
    final = db_session.get(ArticleCandidate, task.id)
    assert final is not None
    assert final.status == "manual"
    assert final.retry_count == 4


def test_account_rate_limit_blocks_task(db_session, monkeypatch) -> None:
    monkeypatch.setenv("SCHEDULER_MAX_ACCOUNT_INTERVAL_SECONDS", "3600")
    from wechat_collector.config import get_settings

    get_settings.cache_clear()

    org = org_service.create_organization(db_session, org_code="org_rate", org_name="限频组织")
    account = org_service.bind_wechat_account(db_session, org.id, account_name="限频号")

    first, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=rate1&mid=1&idx=1",
        org_id=org.id,
        account_id=account.id,
        source="manual",
    )
    candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=rate2&mid=1&idx=1",
        org_id=org.id,
        account_id=account.id,
        source="manual",
    )

    picked = candidate_service.get_next_task(db_session)
    assert picked is not None
    candidate_service.mark_success(db_session, picked.id)

    assert candidate_service.get_next_task(db_session) is None

    get_settings.cache_clear()
