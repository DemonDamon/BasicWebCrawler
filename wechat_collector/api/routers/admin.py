from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import ArticleListItem
from wechat_collector.services import article_service

router = APIRouter(prefix="/admin", tags=["admin"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/articles", response_model=list[ArticleListItem])
def list_articles_admin(
    _auth: AuthRequired,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[ArticleListItem]:
    articles = article_service.list_articles(db, limit=limit, offset=offset)
    return [
        ArticleListItem(
            id=article.id,
            title=article.title,
            account_name=article.account_name,
            url=article.url,
            publish_time=article.publish_time,
            collected_at=article.collected_at,
            source=article.source,
        )
        for article in articles
    ]


@router.get("")
def admin_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "admin.html")


@router.get("/health-page")
def health_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "health.html")
