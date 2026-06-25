"""指标计算与 account_health 刷新。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from wechat_collector.db.models import AccountHealth, Article, ArticleCandidate, Organization, WechatAccount


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def refresh_account_health(db: Session) -> int:
    now = _utcnow()
    since_1d = now - timedelta(days=1)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    accounts = db.scalars(select(WechatAccount).order_by(WechatAccount.id)).all()
    updated = 0

    for account in accounts:
        health = account.health
        if health is None:
            health = AccountHealth(account_id=account.id)
            db.add(health)

        count_1d = db.scalar(
            select(func.count())
            .select_from(Article)
            .where(Article.account_id == account.id, Article.collected_at >= since_1d)
        ) or 0
        count_7d = db.scalar(
            select(func.count())
            .select_from(Article)
            .where(Article.account_id == account.id, Article.collected_at >= since_7d)
        ) or 0
        count_30d = db.scalar(
            select(func.count())
            .select_from(Article)
            .where(Article.account_id == account.id, Article.collected_at >= since_30d)
        ) or 0

        last_discovered = db.scalar(
            select(func.max(ArticleCandidate.discovered_at)).where(
                ArticleCandidate.account_id == account.id
            )
        )
        last_crawled = db.scalar(
            select(func.max(ArticleCandidate.crawled_at)).where(
                ArticleCandidate.account_id == account.id,
                ArticleCandidate.status == "success",
            )
        )

        consecutive_failures = db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(
                ArticleCandidate.account_id == account.id,
                ArticleCandidate.status.in_(("failed", "manual", "retrying")),
            )
        ) or 0

        health.article_count_1d = count_1d
        health.article_count_7d = count_7d
        health.article_count_30d = count_30d
        health.last_discovered_at = last_discovered
        health.last_crawled_at = last_crawled
        health.consecutive_failures = consecutive_failures
        health.updated_at = now
        updated += 1

    db.commit()
    return updated


def compute_account_coverage(db: Session) -> float | None:
    active_orgs = db.scalar(
        select(func.count()).select_from(Organization).where(Organization.status == "active")
    ) or 0
    if active_orgs == 0:
        return None

    orgs_with_accounts = db.scalar(
        select(func.count(func.distinct(WechatAccount.org_id))).where(
            WechatAccount.org_id.is_not(None)
        )
    ) or 0
    return orgs_with_accounts / active_orgs


def count_manual_queue(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(ArticleCandidate.status == "manual")
        )
        or 0
    )


def average_collect_delay_hours(db: Session) -> float | None:
    rows = db.execute(
        select(Article.publish_time, Article.collected_at).where(
            Article.publish_time.is_not(None)
        )
    ).all()
    if not rows:
        return None

    total_seconds = 0.0
    count = 0
    for publish_time, collected_at in rows:
        if publish_time and collected_at and collected_at >= publish_time:
            total_seconds += (collected_at - publish_time).total_seconds()
            count += 1
    if count == 0:
        return None
    return total_seconds / count / 3600
