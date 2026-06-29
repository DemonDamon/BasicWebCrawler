"""账号管理 API：查看/配置账号的 RSSHub 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from wechat_collector.api.deps import AuthRequired, DbSession
from wechat_collector.db.models import WechatAccount

router = APIRouter(tags=["accounts"])


class RSSHubRoute(BaseModel):
    provider: str
    route: str


class RSSHubRoutesBody(BaseModel):
    routes: list[RSSHubRoute]


class AccountRSSHubRoutesResponse(BaseModel):
    account_id: int
    account_name: str
    biz: str | None
    routes: list[RSSHubRoute]


@router.get("/accounts/{account_id}/rsshub_routes", response_model=AccountRSSHubRoutesResponse)
def get_rsshub_routes(
    account_id: int,
    _auth: AuthRequired,
    db: DbSession,
) -> AccountRSSHubRoutesResponse:
    account = db.get(WechatAccount, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    return AccountRSSHubRoutesResponse(
        account_id=account.id,
        account_name=account.account_name,
        biz=account.biz,
        routes=[RSSHubRoute(**r) for r in (account.rsshub_routes or [])],
    )


@router.put("/accounts/{account_id}/rsshub_routes", response_model=AccountRSSHubRoutesResponse)
def set_rsshub_routes(
    account_id: int,
    body: RSSHubRoutesBody,
    _auth: AuthRequired,
    db: DbSession,
) -> AccountRSSHubRoutesResponse:
    account = db.get(WechatAccount, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    account.rsshub_routes = [r.model_dump() for r in body.routes]
    db.commit()
    db.refresh(account)
    return AccountRSSHubRoutesResponse(
        account_id=account.id,
        account_name=account.account_name,
        biz=account.biz,
        routes=[RSSHubRoute(**r) for r in (account.rsshub_routes or [])],
    )


@router.get("/accounts", response_model=list[AccountRSSHubRoutesResponse])
def list_accounts(
    _auth: AuthRequired,
    db: DbSession,
) -> list[AccountRSSHubRoutesResponse]:
    accounts = list(db.scalars(select(WechatAccount).order_by(WechatAccount.id)))
    return [
        AccountRSSHubRoutesResponse(
            account_id=a.id,
            account_name=a.account_name,
            biz=a.biz,
            routes=[RSSHubRoute(**r) for r in (a.rsshub_routes or [])],
        )
        for a in accounts
    ]
