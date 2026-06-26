from fastapi import APIRouter, HTTPException, status

from wechat_collector.api.deps import AuthRequired, ClientCtx, DbSession
from wechat_collector.api.schemas import ArticleIngestBody, ArticleIngestResponse
from wechat_collector.services.article_service import ArticleIngestInput, ingest_article

router = APIRouter(tags=["articles"])


@router.post("/articles", response_model=ArticleIngestResponse)
def create_article(
    _auth: AuthRequired,
    body: ArticleIngestBody,
    db: DbSession,
    client: ClientCtx,
) -> ArticleIngestResponse:
    result = ingest_article(
        db,
        ArticleIngestInput(
            title=body.title,
            url=body.url,
            account_name=body.account_name,
            org_id=body.org_id,
            account_id=body.account_id,
            candidate_id=body.candidate_id,
            canonical_url=body.canonical_url,
            publish_time=body.publish_time,
            cover_url=body.cover_url,
            summary=body.summary,
            content_html=body.content_html,
            content_text=body.content_text,
            source=body.source,
            biz=body.biz,
        ),
        client,
    )
    return ArticleIngestResponse(
        id=result.article.id,
        title=result.article.title,
        url=result.article.url,
        created=result.created,
        duplicate_reason=result.duplicate_reason,
    )
