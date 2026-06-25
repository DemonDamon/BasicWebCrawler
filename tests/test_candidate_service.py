import pytest

from wechat_collector.db.models import Article
from wechat_collector.services import candidate_service, org_service
from wechat_collector.scheduler.retry import utcnow
from datetime import timedelta
from wechat_collector.services.candidate_service import InvalidCandidateTransitionError
from wechat_collector.utils.hashing import compute_content_hash


def test_enqueue_deduplicates_by_normalized_url(db_session) -> None:
    first, created_first = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=111",
        source="bing_search",
        title="标题A",
    )
    second, created_second = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=222&chksm=zzz",
        source="manual",
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert set(second.sources or []) == {"bing_search", "manual"}


def test_state_machine_invalid_transition() -> None:
    with pytest.raises(InvalidCandidateTransitionError):
        candidate_service.validate_transition("pending", "success")
    with pytest.raises(InvalidCandidateTransitionError):
        candidate_service.validate_transition("success", "processing")


def test_get_next_task_marks_processing_and_respects_priority(db_session) -> None:
    high_org = org_service.create_organization(
        db_session, org_code="org_high", org_name="高优先级", priority="high"
    )
    normal_org = org_service.create_organization(
        db_session, org_code="org_normal", org_name="普通", priority="normal"
    )

    low_candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=low&mid=1&idx=1",
        org_id=normal_org.id,
        source="bing_search",
    )
    high_candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=high&mid=1&idx=1",
        org_id=high_org.id,
        source="bing_search",
    )

    picked = candidate_service.get_next_task(db_session)
    assert picked is not None
    assert picked.id == high_candidate.id
    assert picked.status == "processing"
    assert low_candidate.status == "pending"


def test_failed_retry_flow(db_session) -> None:
    candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=retry&mid=1&idx=1",
        source="bing_search",
    )
    picked = candidate_service.get_next_task(db_session)
    assert picked is not None

    candidate_service.mark_failed(db_session, picked.id, fail_reason="403")
    refreshed = db_session.get(type(candidate), candidate.id)
    assert refreshed.status == "retrying"
    assert refreshed.next_retry_at is not None

    refreshed.next_retry_at = utcnow() - timedelta(minutes=1)
    db_session.commit()

    repicked = candidate_service.get_next_task(db_session)
    assert repicked is not None
    assert repicked.id == picked.id
    assert repicked.status == "processing"


def test_mark_success_and_ignore_from_failed(db_session) -> None:
    candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=done&mid=1&idx=1",
        source="manual",
    )
    task = candidate_service.get_next_task(db_session)
    assert task is not None
    candidate_service.mark_success(db_session, task.id)
    assert db_session.get(type(candidate), candidate.id).status == "success"

    failed_candidate, _ = candidate_service.enqueue_candidate(
        db_session,
        url="https://mp.weixin.qq.com/s?__biz=ignore&mid=1&idx=1",
        source="manual",
    )
    failed_task = candidate_service.get_next_task(db_session)
    assert failed_task is not None
    candidate_service.mark_failed(db_session, failed_task.id, fail_reason="parse_error")
    candidate_service.mark_ignored(db_session, failed_task.id)
    assert db_session.get(type(failed_candidate), failed_candidate.id).status == "ignored"


def test_article_exists_by_content_hash(db_session) -> None:
    content_text = "同正文不同链接"
    content_hash = compute_content_hash(content_text)
    assert content_hash is not None

    db_session.add(
        Article(
            title="文章1",
            url="https://mp.weixin.qq.com/s?__biz=a&mid=1&idx=1",
            content_text=content_text,
            content_hash=content_hash,
        )
    )
    db_session.commit()

    assert candidate_service.article_exists_by_content_hash(db_session, content_hash)
    assert candidate_service.article_exists_by_content_text(db_session, content_text)
    assert not candidate_service.article_exists_by_content_text(db_session, "不同正文")
