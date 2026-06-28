"""多源发现编排与入池。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from wechat_collector.config import get_settings
from wechat_collector.db.models import DiscoverySourceStat, Organization
from wechat_collector.discovery.base import (
    DiscoveryProvider,
    build_search_queries,
    is_relevant_link,
)
from wechat_collector.discovery.providers.baidu import BaiduDiscoveryProvider
from wechat_collector.discovery.providers.bing import BingDiscoveryProvider
from wechat_collector.discovery.providers.official_site import OfficialSiteDiscoveryProvider
from wechat_collector.discovery.providers.sogou_wechat import SogouWechatDiscoveryProvider
from wechat_collector.discovery.search_html import FetchHtmlFn
from wechat_collector.services import candidate_service


@dataclass
class DiscoveryRunSummary:
    org_id: int
    org_name: str
    created: int = 0
    merged: int = 0
    skipped: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    disabled_sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def default_providers(fetch_html: FetchHtmlFn | None = None) -> list[DiscoveryProvider]:
    return [
        BingDiscoveryProvider(fetch_html=fetch_html),
        BaiduDiscoveryProvider(fetch_html=fetch_html),
        SogouWechatDiscoveryProvider(fetch_html=fetch_html),
        OfficialSiteDiscoveryProvider(fetch_html=fetch_html),
    ]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_or_create_source_stat(db: Session, source: str) -> DiscoverySourceStat:
    stat = db.get(DiscoverySourceStat, source)
    if stat is None:
        stat = DiscoverySourceStat(source=source)
        db.add(stat)
        db.flush()
    return stat


def _is_source_disabled(db: Session, source: str) -> bool:
    settings = get_settings()
    stat = db.get(DiscoverySourceStat, source)
    if stat is None:
        return False
    if stat.status == "disabled":
        return True
    return stat.consecutive_empty_runs >= settings.scheduler_empty_source_threshold


def _record_source_run(db: Session, source: str, hit_count: int, error: str | None = None) -> None:
    settings = get_settings()
    stat = _get_or_create_source_stat(db, source)
    stat.last_run_at = _utcnow()
    if hit_count > 0:
        stat.consecutive_empty_runs = 0
        stat.last_hit_at = _utcnow()
        stat.status = "normal"
        stat.warning_reason = None
    else:
        stat.consecutive_empty_runs += 1
        if stat.consecutive_empty_runs >= settings.scheduler_empty_source_threshold:
            stat.status = "warning"
            stat.warning_reason = "consecutive_empty_runs"
        if error:
            stat.warning_reason = error
    db.commit()


def discover_for_organization(
    db: Session,
    org: Organization,
    *,
    providers: list[DiscoveryProvider] | None = None,
) -> DiscoveryRunSummary:
    active_providers = providers or default_providers()
    summary = DiscoveryRunSummary(org_id=org.id, org_name=org.org_name)
    queries = build_search_queries(org)

    for provider in active_providers:
        if _is_source_disabled(db, provider.name):
            summary.disabled_sources.append(provider.name)
            continue

        result = provider.discover(org, queries)
        if result.error:
            summary.errors.append(f"{provider.name}: {result.error}")

        accepted = 0
        for link in result.links:
            if not is_relevant_link(link, org):
                summary.skipped += 1
                continue
            try:
                _, created = candidate_service.enqueue_candidate(
                    db,
                    url=link.url,
                    org_id=org.id,
                    title=link.title,
                    source=link.source,
                )
            except ValueError:
                summary.skipped += 1
                continue
            if created:
                summary.created += 1
            else:
                summary.merged += 1
            accepted += 1

        summary.by_source[provider.name] = accepted
        _record_source_run(db, provider.name, accepted, result.error)

    return summary


def discover_for_active_organizations(
    db: Session,
    *,
    limit: int = 20,
    providers: list[DiscoveryProvider] | None = None,
) -> list[DiscoveryRunSummary]:
    orgs = db.scalars(
        select(Organization)
        .options(joinedload(Organization.wechat_accounts))
        .where(Organization.status == "active")
        .order_by(Organization.id)
        .limit(limit)
    ).unique().all()

    return [discover_for_organization(db, org, providers=providers) for org in orgs]
