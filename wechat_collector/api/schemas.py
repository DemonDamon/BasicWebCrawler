"""Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CandidateCreateBody(BaseModel):
    url: str
    org_id: int | None = None
    account_id: int | None = None
    title: str | None = None
    source: str | None = None


class CandidateImportBody(BaseModel):
    urls: list[str] = Field(min_length=1)
    org_id: int | None = None
    account_id: int | None = None
    source: str = "manual"


class CandidateResponse(BaseModel):
    id: int
    url: str
    normalized_url: str | None
    status: str
    created: bool
    sources: list[str] | None = None


class CandidateImportResponse(BaseModel):
    created: int
    merged: int
    skipped: int


class ArticleIngestBody(BaseModel):
    title: str
    account_name: str | None = None
    wechat_id: str | None = None
    biz: str | None = None
    url: str
    canonical_url: str | None = None
    publish_time: datetime | None = None
    cover_url: str | None = None
    summary: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    org_id: int | None = None
    account_id: int | None = None
    candidate_id: int | None = None
    source: str | None = None


class ArticleIngestResponse(BaseModel):
    id: int
    title: str
    url: str
    created: bool
    duplicate_reason: str | None = None


class ArticleListItem(BaseModel):
    id: int
    title: str
    account_name: str | None
    url: str
    publish_time: datetime | None
    collected_at: datetime
    source: str | None


class TaskResponse(BaseModel):
    id: int
    url: str
    normalized_url: str | None
    title: str | None
    org_id: int | None
    account_id: int | None
    status: str


class TaskFailedBody(BaseModel):
    fail_reason: str | None = None


class TaskActionResponse(BaseModel):
    id: int
    status: str


class AccountHealthItem(BaseModel):
    account_id: int
    account_name: str
    org_id: int | None
    org_name: str | None
    status: str
    consecutive_failures: int
    article_count_7d: int
    warning_reason: str | None


class CoverageReportResponse(BaseModel):
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
    account_coverage_rate: float | None = None
    manual_queue_count: int = 0
    retry_queue_count: int = 0
    avg_collect_delay_hours: float | None = None
    discovery_sources_warning: int = 0


class DiscoveryRunRequest(BaseModel):
    org_id: int | None = None
    limit: int = Field(default=20, ge=1, le=500)


class DiscoveryRunResponse(BaseModel):
    organizations_scanned: int
    created: int
    merged: int
    skipped: int
    details: list[dict[str, object]]


class AlertItem(BaseModel):
    code: str
    severity: str
    message: str
    account_id: int | None = None
    source: str | None = None


class MonitoringRefreshResponse(BaseModel):
    accounts_updated: int
    alerts: list[AlertItem]
