"""候选池：入队、任务领取、状态机、去重。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import Session

from wechat_collector.config import get_settings
from wechat_collector.db.models import Article, ArticleCandidate, Organization
from wechat_collector.scheduler.limits import account_recently_crawled
from wechat_collector.scheduler.retry import (
    compute_next_retry_at,
    is_retry_due,
    should_escalate_to_manual,
)
from wechat_collector.utils.hashing import compute_content_hash
from wechat_collector.utils.url_normalize import normalize_wechat_url

CandidateStatus = Literal[
    "pending",
    "processing",
    "success",
    "failed",
    "retrying",
    "manual",
    "ignored",
]

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"processing"}),
    "processing": frozenset({"success", "failed"}),
    "failed": frozenset({"retrying", "manual", "ignored"}),
    "retrying": frozenset({"processing", "ignored"}),
    "manual": frozenset({"processing", "ignored"}),
    "success": frozenset(),
    "ignored": frozenset(),
}

PRIORITY_RANK = {"high": 0, "normal": 1, "low": 2}
PICKABLE_STATUSES = frozenset({"pending", "retrying"})


class InvalidCandidateTransitionError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Invalid candidate status transition: {current} -> {target}")
        self.current = current
        self.target = target


def validate_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidCandidateTransitionError(current, target)


def _merge_sources(existing: list[str] | None, source: str | None) -> list[str]:
    merged: list[str] = list(existing or [])
    if source and source not in merged:
        merged.append(source)
    return merged


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def enqueue_candidate(
    db: Session,
    *,
    url: str,
    org_id: int | None = None,
    account_id: int | None = None,
    title: str | None = None,
    source: str | None = None,
) -> tuple[ArticleCandidate, bool]:
    """入候选池。返回 (candidate, created)。同一 normalized_url 合并 sources。"""
    normalized = normalize_wechat_url(url)
    if not normalized:
        raise ValueError("Invalid wechat article URL")

    existing = db.scalar(
        select(ArticleCandidate).where(ArticleCandidate.normalized_url == normalized)
    )
    if existing:
        existing.sources = _merge_sources(existing.sources, source)
        if title and not existing.title:
            existing.title = title
        db.commit()
        db.refresh(existing)
        return existing, False

    candidate = ArticleCandidate(
        org_id=org_id,
        account_id=account_id,
        url=url.strip(),
        normalized_url=normalized,
        title=title,
        source=source,
        sources=_merge_sources([], source),
        status="pending",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate, True


def get_next_task(
    db: Session,
    *,
    priority: str | None = None,
) -> ArticleCandidate | None:
    """领取下一个 pending/retrying(已到期) 任务并置为 processing。"""
    now = _utcnow()
    rank_case = case(
        (Organization.priority == "high", PRIORITY_RANK["high"]),
        (Organization.priority == "normal", PRIORITY_RANK["normal"]),
        else_=PRIORITY_RANK["low"],
    )

    pickable = or_(
        ArticleCandidate.status == "pending",
        and_(
            ArticleCandidate.status == "retrying",
            or_(
                ArticleCandidate.next_retry_at.is_(None),
                ArticleCandidate.next_retry_at <= now,
            ),
        ),
    )

    stmt = (
        select(ArticleCandidate)
        .outerjoin(Organization, ArticleCandidate.org_id == Organization.id)
        .where(pickable)
        .order_by(rank_case, ArticleCandidate.discovered_at, ArticleCandidate.id)
        .limit(10)
        .with_for_update()
    )
    if priority is not None:
        stmt = stmt.where(Organization.priority == priority)

    candidates = db.scalars(stmt).all()
    for candidate in candidates:
        if not is_retry_due(candidate.next_retry_at, now=now):
            continue
        if account_recently_crawled(db, candidate.account_id, now=now):
            continue

        validate_transition(candidate.status, "processing")
        candidate.status = "processing"
        candidate.next_retry_at = None
        db.commit()
        db.refresh(candidate)
        return candidate

    return None


def transition_candidate(
    db: Session,
    candidate_id: int,
    target_status: CandidateStatus,
    *,
    fail_reason: str | None = None,
) -> ArticleCandidate:
    candidate = db.get(ArticleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate not found: {candidate_id}")

    validate_transition(candidate.status, target_status)
    candidate.status = target_status

    if target_status == "failed":
        candidate.retry_count += 1
        candidate.fail_reason = fail_reason
    elif target_status == "success":
        candidate.crawled_at = _utcnow()
        candidate.fail_reason = None
    elif target_status == "processing" and fail_reason is not None:
        candidate.fail_reason = fail_reason

    db.commit()
    db.refresh(candidate)
    return candidate


def mark_success(db: Session, candidate_id: int) -> ArticleCandidate:
    return transition_candidate(db, candidate_id, "success")


def mark_failed(
    db: Session, candidate_id: int, fail_reason: str | None = None
) -> ArticleCandidate:
    candidate = db.get(ArticleCandidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate not found: {candidate_id}")

    validate_transition(candidate.status, "failed")
    candidate.retry_count += 1
    candidate.fail_reason = fail_reason

    if should_escalate_to_manual(candidate.retry_count):
        validate_transition("failed", "manual")
        candidate.status = "manual"
        candidate.next_retry_at = None
    else:
        validate_transition("failed", "retrying")
        candidate.status = "retrying"
        candidate.next_retry_at = compute_next_retry_at(candidate.retry_count)

    db.commit()
    db.refresh(candidate)
    return candidate


def schedule_retry(db: Session, candidate_id: int) -> ArticleCandidate:
    return transition_candidate(db, candidate_id, "retrying")


def mark_manual(db: Session, candidate_id: int, reason: str | None = None) -> ArticleCandidate:
    return transition_candidate(db, candidate_id, "manual", fail_reason=reason)


def mark_ignored(db: Session, candidate_id: int) -> ArticleCandidate:
    return transition_candidate(db, candidate_id, "ignored")


def article_exists_by_content_hash(db: Session, content_hash: str) -> bool:
    existing = db.scalar(select(Article.id).where(Article.content_hash == content_hash).limit(1))
    return existing is not None


def article_exists_by_content_text(db: Session, content_text: str | None) -> bool:
    content_hash = compute_content_hash(content_text)
    if not content_hash:
        return False
    return article_exists_by_content_hash(db, content_hash)
