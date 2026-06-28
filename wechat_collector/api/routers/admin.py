from pathlib import Path
import csv
import io
import re

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import (
    AdminSettingItem,
    AdminSettingsUpdateBody,
    ArticleDetail,
    ArticleListItem,
    PilotAccountCreateBody,
    PilotAccountRow,
    PilotAccountUpdateBody,
)
from wechat_collector.services import article_service, org_service, settings_service

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


@router.get("/manage")
def admin_manage_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "admin-manage.html")


@router.get("/health-page")
def health_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "health.html")


@router.get("/pilot-accounts", response_model=list[PilotAccountRow])
def list_pilot_accounts_admin(
    _auth: AuthRequired,
    db: DbSession,
    include_inactive: bool = False,
) -> list[PilotAccountRow]:
    rows = org_service.list_pilot_accounts(db, include_inactive=include_inactive)
    return [PilotAccountRow(**row) for row in rows]


@router.post("/pilot-accounts", response_model=PilotAccountRow, status_code=status.HTTP_201_CREATED)
def create_pilot_account_admin(
    body: PilotAccountCreateBody,
    _auth: AuthRequired,
    db: DbSession,
) -> PilotAccountRow:
    try:
        row = org_service.create_pilot_account_row(
            db,
            org_code=body.org_code,
            org_name=body.org_name,
            account_name=body.account_name,
            aliases=body.aliases,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PilotAccountRow(**row)


@router.put("/pilot-accounts/{account_id}", response_model=PilotAccountRow)
def update_pilot_account_admin(
    account_id: int,
    body: PilotAccountUpdateBody,
    _auth: AuthRequired,
    db: DbSession,
) -> PilotAccountRow:
    try:
        row = org_service.update_pilot_account_row(
            db,
            account_id,
            org_code=body.org_code,
            org_name=body.org_name,
            account_name=body.account_name,
            aliases=body.aliases,
            priority=body.priority,
            status=body.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PilotAccountRow(**row)


@router.delete("/pilot-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pilot_account_admin(
    account_id: int,
    _auth: AuthRequired,
    db: DbSession,
) -> None:
    try:
        org_service.delete_pilot_account_row(db, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/pilot-accounts/export.csv")
def export_pilot_accounts_csv(
    _auth: AuthRequired,
    db: DbSession,
) -> StreamingResponse:
    rows = org_service.list_pilot_accounts(db, include_inactive=False)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["org_code", "org_name", "account_name", "aliases", "priority"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "org_code": row.get("org_code") or "",
                "org_name": row.get("org_name") or "",
                "account_name": row.get("account_name") or "",
                "aliases": row.get("aliases") or "",
                "priority": row.get("priority") or "normal",
            }
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pilot_wechat_accounts.csv"'},
    )


@router.get("/settings", response_model=list[AdminSettingItem])
def list_settings_admin(_auth: AuthRequired) -> list[AdminSettingItem]:
    return [AdminSettingItem(**item) for item in settings_service.list_settings_for_admin()]


@router.put("/settings", response_model=list[AdminSettingItem])
def update_settings_admin(
    body: AdminSettingsUpdateBody,
    _auth: AuthRequired,
) -> list[AdminSettingItem]:
    try:
        settings_service.update_env_settings(body.values)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [AdminSettingItem(**item) for item in settings_service.list_settings_for_admin()]
