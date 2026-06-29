from fastapi import APIRouter

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.api.schemas import AccountHealthItem
from wechat_collector.services import report_service

router = APIRouter(prefix="/accounts", tags=["health"])


@router.get("/health", response_model=list[AccountHealthItem])
def get_accounts_health(
    _auth: AuthRequired,
    db: DbSession,
    limit: int = 100,
) -> list[AccountHealthItem]:
    rows = report_service.list_account_health(db, limit=limit)
    return [
        AccountHealthItem(
            account_id=row.account_id,
            account_name=row.account_name,
            org_id=row.org_id,
            org_name=row.org_name,
            status=row.status,
            consecutive_failures=row.consecutive_failures,
            article_count_7d=row.article_count_7d,
            warning_reason=row.warning_reason,
        )
        for row in rows
    ]
