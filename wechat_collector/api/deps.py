"""FastAPI 依赖：数据库会话、鉴权、客户端上下文。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from wechat_collector.config import Settings, get_settings
from wechat_collector.db.base import get_db
from wechat_collector.services.article_service import ClientContext

DbSession = Annotated[Session, Depends(get_db)]


def get_client_context(
    x_client_id: Annotated[str | None, Header()] = None,
    x_plugin_version: Annotated[str | None, Header()] = None,
    x_operator: Annotated[str | None, Header()] = None,
) -> ClientContext:
    return ClientContext(
        client_id=x_client_id,
        plugin_version=x_plugin_version,
        operator=x_operator,
    )


ClientCtx = Annotated[ClientContext, Depends(get_client_context)]


def verify_api_token(
    x_api_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_api_token or x_api_token != settings.collector_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )


AuthRequired = Annotated[None, Depends(verify_api_token)]
