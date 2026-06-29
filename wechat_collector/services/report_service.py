"""健康度与覆盖率报表（P9 扩展）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from wechat_collector.db.models import Article, ArticleCandidate, DiscoverySourceStat, Organization, WechatAccount
from wechat_collector.monitoring import metrics


@dataclass
class AccountHealthRow:
    account_id: int
    account_name: str
    org_id: int | None
    org_name: str | None
    status: str
    consecutive_failures: int
    article_count_7d: int
    warning_reason: str | None


@dataclass
class CoverageReport:
    organization_total: int
    organization_active: int
    wechat_account_total: int
    wechat_account_with_org: int
    candidate_total: int
    candidate_pending: int
    candidate_success: int
    candidate_failed: int
    article_total: int
    crawl_success_rate: float | None
    account_coverage_rate: float | None
    manual_queue_count: int
    retry_queue_count: int
    avg_collect_delay_hours: float | None
    discovery_sources_warning: int


def list_account_health(db: Session, *, limit: int = 100) -> list[AccountHealthRow]:
    accounts = db.scalars(
        select(WechatAccount)
        .options(joinedload(WechatAccount.organization), joinedload(WechatAccount.health))
        .order_by(WechatAccount.id)
        .limit(limit)
    ).all()

    rows: list[AccountHealthRow] = []
    for account in accounts:
        health = account.health
        rows.append(
            AccountHealthRow(
                account_id=account.id,
                account_name=account.account_name,
                org_id=account.org_id,
                org_name=account.organization.org_name if account.organization else None,
                status=health.status if health else "unknown",
                consecutive_failures=health.consecutive_failures if health else 0,
                article_count_7d=health.article_count_7d if health else 0,
                warning_reason=health.warning_reason if health else None,
            )
        )
    return rows


def build_coverage_report(db: Session) -> CoverageReport:
    org_total = db.scalar(select(func.count()).select_from(Organization)) or 0
    org_active = (
        db.scalar(
            select(func.count()).select_from(Organization).where(Organization.status == "active")
        )
        or 0
    )
    account_total = db.scalar(select(func.count()).select_from(WechatAccount)) or 0
    account_with_org = (
        db.scalar(
            select(func.count())
            .select_from(WechatAccount)
            .where(WechatAccount.org_id.is_not(None))
        )
        or 0
    )
    candidate_total = db.scalar(select(func.count()).select_from(ArticleCandidate)) or 0
    candidate_pending = (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(ArticleCandidate.status == "pending")
        )
        or 0
    )
    candidate_success = (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(ArticleCandidate.status == "success")
        )
        or 0
    )
    candidate_failed = (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(ArticleCandidate.status.in_(("failed", "manual", "retrying")))
        )
        or 0
    )
    retry_queue_count = (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(ArticleCandidate.status == "retrying")
        )
        or 0
    )
    article_total = db.scalar(select(func.count()).select_from(Article)) or 0
    discovery_sources_warning = (
        db.scalar(
            select(func.count())
            .select_from(DiscoverySourceStat)
            .where(DiscoverySourceStat.status == "warning")
        )
        or 0
    )

    finished = candidate_success + candidate_failed
    crawl_success_rate = (candidate_success / finished) if finished else None

    return CoverageReport(
        organization_total=org_total,
        organization_active=org_active,
        wechat_account_total=account_total,
        wechat_account_with_org=account_with_org,
        candidate_total=candidate_total,
        candidate_pending=candidate_pending,
        candidate_success=candidate_success,
        candidate_failed=candidate_failed,
        article_total=article_total,
        crawl_success_rate=crawl_success_rate,
        account_coverage_rate=metrics.compute_account_coverage(db),
        manual_queue_count=metrics.count_manual_queue(db),
        retry_queue_count=retry_queue_count,
        avg_collect_delay_hours=metrics.average_collect_delay_hours(db),
        discovery_sources_warning=discovery_sources_warning,
    )
