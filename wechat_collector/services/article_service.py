"""文章入库与去重。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from wechat_collector.db.models import Article, ArticleCandidate
from wechat_collector.services import candidate_service
from wechat_collector.utils.hashing import compute_content_hash
from wechat_collector.utils.url_normalize import normalize_wechat_url

logger = logging.getLogger(__name__)


@dataclass
class ClientContext:
    client_id: str | None = None
    plugin_version: str | None = None
    operator: str | None = None


@dataclass
class ArticleIngestInput:
    title: str
    url: str
    account_name: str | None = None
    org_id: int | None = None
    account_id: int | None = None
    candidate_id: int | None = None
    canonical_url: str | None = None
    publish_time: datetime | None = None
    cover_url: str | None = None
    summary: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    content_hash: str | None = None
    source: str | None = None


@dataclass
class ArticleIngestResult:
    article: Article
    created: bool
    duplicate_reason: str | None = None


def ingest_article(
    db: Session,
    payload: ArticleIngestInput,
    client: ClientContext | None = None,
) -> ArticleIngestResult:
    content_hash = payload.content_hash or compute_content_hash(payload.content_text)
    canonical_url = payload.canonical_url or normalize_wechat_url(payload.url)

    if content_hash and candidate_service.article_exists_by_content_hash(db, content_hash):
        existing = db.scalar(select(Article).where(Article.content_hash == content_hash))
        assert existing is not None
        _log_ingest(client, existing.id, created=False, reason="content_hash")
        return ArticleIngestResult(existing, False, "content_hash")

    if canonical_url:
        existing_canonical = db.scalar(
            select(Article).where(Article.canonical_url == canonical_url)
        )
        if existing_canonical:
            _log_ingest(client, existing_canonical.id, created=False, reason="canonical_url")
            return ArticleIngestResult(existing_canonical, False, "canonical_url")

    existing_url = db.scalar(select(Article).where(Article.url == payload.url))
    if existing_url:
        _log_ingest(client, existing_url.id, created=False, reason="url")
        return ArticleIngestResult(existing_url, False, "url")

    article = Article(
        org_id=payload.org_id,
        account_id=payload.account_id,
        title=payload.title,
        account_name=payload.account_name,
        url=payload.url,
        canonical_url=canonical_url,
        publish_time=payload.publish_time,
        cover_url=payload.cover_url,
        summary=payload.summary,
        content_html=payload.content_html,
        content_text=payload.content_text,
        content_hash=content_hash,
        source=payload.source or "extension",
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    if payload.candidate_id is not None:
        candidate = db.get(ArticleCandidate, payload.candidate_id)
        if candidate and candidate.status == "processing":
            candidate_service.mark_success(db, payload.candidate_id)

    _log_ingest(client, article.id, created=True, reason=None)
    return ArticleIngestResult(article, True, None)


def list_articles(db: Session, *, limit: int = 50, offset: int = 0) -> list[Article]:
    stmt = select(Article).order_by(Article.collected_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


def _log_ingest(
    client: ClientContext | None,
    article_id: int,
    *,
    created: bool,
    reason: str | None,
) -> None:
    logger.info(
        "article_ingest article_id=%s created=%s duplicate_reason=%s client_id=%s plugin_version=%s operator=%s",
        article_id,
        created,
        reason,
        client.client_id if client else None,
        client.plugin_version if client else None,
        client.operator if client else None,
    )
