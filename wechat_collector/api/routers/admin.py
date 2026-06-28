from pathlib import Path
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import ArticleDetail, ArticleListItem
from wechat_collector.services import article_service

router = APIRouter(prefix="/admin", tags=["admin"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_IMG_TAG_RE = re.compile(r"<img\b", re.IGNORECASE)


def _article_content_stats(article) -> tuple[bool, int, int, int]:
    text = article.content_text or ""
    html = article.content_html or ""
    text_length = len(text)
    html_length = len(html)
    image_count = len(_IMG_TAG_RE.findall(html))
    has_content = bool(text.strip() or html.strip())
    return has_content, text_length, html_length, image_count


@router.get("/articles", response_model=list[ArticleListItem])
def list_articles_admin(
    _auth: AuthRequired,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[ArticleListItem]:
    articles = article_service.list_articles(db, limit=limit, offset=offset)
    items: list[ArticleListItem] = []
    for article in articles:
        has_content, text_length, _, _ = _article_content_stats(article)
        items.append(
            ArticleListItem(
                id=article.id,
                title=article.title,
                account_name=article.account_name,
                url=article.url,
                publish_time=article.publish_time,
                collected_at=article.collected_at,
                source=article.source,
                has_content=has_content,
                text_length=text_length,
            )
        )
    return items


@router.get("/articles/{article_id}", response_model=ArticleDetail)
def get_article_admin(
    article_id: int,
    _auth: AuthRequired,
    db: DbSession,
) -> ArticleDetail:
    article = article_service.get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    _, text_length, html_length, image_count = _article_content_stats(article)
    return ArticleDetail(
        id=article.id,
        title=article.title,
        account_name=article.account_name,
        url=article.url,
        canonical_url=article.canonical_url,
        publish_time=article.publish_time,
        collected_at=article.collected_at,
        source=article.source,
        org_id=article.org_id,
        cover_url=article.cover_url,
        summary=article.summary,
        content_html=article.content_html,
        content_text=article.content_text,
        text_length=text_length,
        html_length=html_length,
        image_count=image_count,
    )


@router.get("")
def admin_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "admin.html")


@router.get("/health-page")
def health_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "health.html")
