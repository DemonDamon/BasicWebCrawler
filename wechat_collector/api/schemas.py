"""Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
    biz: str | None = None  # 扩展上报的 __biz，用于自动回填账号

    @field_validator("publish_time", mode="before")
    @classmethod
    def _coerce_publish_time(cls, v: object) -> object:
        """宽松解析日期字符串，支持中文格式和 Unix 时间戳。"""
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            # Unix 时间戳（秒）
            return datetime.fromtimestamp(v)
        if isinstance(v, str):
            import re
            # 中文格式：2026年6月25日 或 2026年06月25日 10:30
            m = re.match(
                r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s+(\d{1,2}):(\d{2}))?",
                v.strip(),
            )
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                hh = int(m.group(4) or 0)
                mm = int(m.group(5) or 0)
                return datetime(y, mo, d, hh, mm)
        return v


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
