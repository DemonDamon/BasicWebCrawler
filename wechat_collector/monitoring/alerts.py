"""异常规则引擎（方案 §4.7）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wechat_collector.config import get_settings
from wechat_collector.db.models import AccountHealth, ArticleCandidate, DiscoverySourceStat, WechatAccount


@dataclass
class Alert:
    code: str
    severity: str
    message: str
    account_id: int | None = None
    source: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def evaluate_alerts(db: Session) -> list[Alert]:
    alerts: list[Alert] = []
    settings = get_settings()
    now = _utcnow()
    stale_before = now - timedelta(days=3)

    high_activity_accounts = db.scalars(
        select(WechatAccount).join(AccountHealth, isouter=True).order_by(WechatAccount.id)
    ).all()
    for account in high_activity_accounts:
        health = account.health
        if health and health.article_count_7d >= 3:
            last_crawled = health.last_crawled_at
            if last_crawled is None or last_crawled < stale_before:
                alerts.append(
                    Alert(
                        code="stale_high_activity_account",
                        severity="warning",
                        message=f"高频账号 {account.account_name} 超过 3 天无新采集",
                        account_id=account.id,
                    )
                )
                health.status = "warning"
                health.warning_reason = "stale_high_activity_account"
            elif health.consecutive_failures >= 3:
                alerts.append(
                    Alert(
                        code="consecutive_failures",
                        severity="warning",
                        message=f"账号 {account.account_name} 连续失败 {health.consecutive_failures} 次",
                        account_id=account.id,
                    )
                )
                health.status = "warning"
                health.warning_reason = "consecutive_failures"

    parse_failures = (
        db.scalar(
            select(func.count())
            .select_from(ArticleCandidate)
            .where(
                ArticleCandidate.status.in_(("failed", "manual", "retrying")),
                ArticleCandidate.fail_reason.ilike("%parse%"),
            )
        )
        or 0
    )
    if parse_failures >= 5:
        alerts.append(
            Alert(
                code="parser_failure_spike",
                severity="critical",
                message=f"解析失败候选过多: {parse_failures}",
            )
        )

    source_stats = db.scalars(select(DiscoverySourceStat)).all()
    for stat in source_stats:
        if stat.consecutive_empty_runs >= settings.scheduler_empty_source_threshold:
            alerts.append(
                Alert(
                    code="discovery_source_empty",
                    severity="warning",
                    message=f"发现源 {stat.source} 连续 {stat.consecutive_empty_runs} 次无结果",
                    source=stat.source,
                )
            )

    db.commit()
    return alerts
