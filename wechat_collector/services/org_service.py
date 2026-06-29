"""组织主数据：CRUD、别名管理、公众号绑定。"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wechat_collector.db.models import Organization, WechatAccount


def normalize_text(value: str) -> str:
    """去首尾空白，全角转半角。"""
    text = unicodedata.normalize("NFKC", value.strip())
    return " ".join(text.split())


def normalize_aliases(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return _dedupe_alias_list([str(item) for item in parsed])
            except json.JSONDecodeError:
                pass
        parts = [part.strip() for part in stripped.replace("；", ";").split(";")]
        return _dedupe_alias_list(parts)
    return _dedupe_alias_list([str(item) for item in raw])


def _dedupe_alias_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_text(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def get_search_names(org: Organization) -> list[str]:
    names = [normalize_text(org.org_name)]
    if org.aliases:
        names.extend(normalize_aliases(org.aliases))
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def create_organization(
    db: Session,
    *,
    org_name: str,
    org_code: str | None = None,
    aliases: str | list[str] | None = None,
    region: str | None = None,
    org_level: str | None = None,
    official_website: str | None = None,
    priority: str = "normal",
    status: str = "active",
) -> Organization:
    org = Organization(
        org_code=org_code,
        org_name=normalize_text(org_name),
        aliases=normalize_aliases(aliases),
        region=region,
        org_level=org_level,
        official_website=official_website.strip() if official_website else None,
        priority=priority,
        status=status,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def upsert_organization_by_code(
    db: Session,
    *,
    org_code: str,
    org_name: str,
    aliases: str | list[str] | None = None,
    region: str | None = None,
    org_level: str | None = None,
    official_website: str | None = None,
    priority: str = "normal",
    status: str = "active",
) -> Organization:
    existing = db.scalar(select(Organization).where(Organization.org_code == org_code))
    normalized_aliases = normalize_aliases(aliases)
    website = official_website.strip() if official_website else None
    if existing:
        existing.org_name = normalize_text(org_name)
        existing.aliases = normalized_aliases
        existing.region = region
        existing.org_level = org_level
        existing.official_website = website
        existing.priority = priority
        existing.status = status
        db.commit()
        db.refresh(existing)
        return existing

    return create_organization(
        db,
        org_code=org_code,
        org_name=org_name,
        aliases=normalized_aliases,
        region=region,
        org_level=org_level,
        official_website=website,
        priority=priority,
        status=status,
    )


def get_organization(db: Session, org_id: int) -> Organization | None:
    return db.get(Organization, org_id)


def get_organization_by_code(db: Session, org_code: str) -> Organization | None:
    return db.scalar(select(Organization).where(Organization.org_code == org_code))


def list_organizations(db: Session, *, status: str | None = None) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.id)
    if status:
        stmt = stmt.where(Organization.status == status)
    return list(db.scalars(stmt))


def update_organization_aliases(
    db: Session, org_id: int, aliases: str | list[str] | None
) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise ValueError(f"Organization not found: {org_id}")
    org.aliases = normalize_aliases(aliases)
    db.commit()
    db.refresh(org)
    return org


def bind_wechat_account(
    db: Session,
    org_id: int,
    *,
    account_name: str,
    wechat_id: str | None = None,
    biz: str | None = None,
    alias_names: str | list[str] | None = None,
    status: str = "active",
) -> WechatAccount:
    org = db.get(Organization, org_id)
    if org is None:
        raise ValueError(f"Organization not found: {org_id}")

    account = WechatAccount(
        org_id=org_id,
        account_name=normalize_text(account_name),
        wechat_id=wechat_id,
        biz=biz,
        alias_names=normalize_aliases(alias_names),
        status=status,
        last_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def unbind_wechat_account(db: Session, account_id: int) -> WechatAccount:
    account = db.get(WechatAccount, account_id)
    if account is None:
        raise ValueError(f"Wechat account not found: {account_id}")
    account.org_id = None
    account.status = "inactive"
    db.commit()
    db.refresh(account)
    return account


def list_wechat_accounts_for_org(db: Session, org_id: int) -> list[WechatAccount]:
    stmt = (
        select(WechatAccount)
        .where(WechatAccount.org_id == org_id)
        .order_by(WechatAccount.id)
    )
    return list(db.scalars(stmt))


def list_pilot_accounts(db: Session, *, include_inactive: bool = False) -> list[dict[str, Any]]:
    """扁平列表：组织 + 绑定公众号（对齐 pilot_wechat_accounts.csv）。"""
    stmt = (
        select(WechatAccount, Organization)
        .join(Organization, WechatAccount.org_id == Organization.id)
        .order_by(Organization.org_code, WechatAccount.id)
    )
    if not include_inactive:
        stmt = stmt.where(
            Organization.status == "active",
            WechatAccount.status == "active",
        )
    rows: list[dict[str, Any]] = []
    for account, org in db.execute(stmt).all():
        aliases = org.aliases or []
        alias_str = ";".join(aliases) if isinstance(aliases, list) else str(aliases)
        rows.append(
            {
                "account_id": account.id,
                "org_id": org.id,
                "org_code": org.org_code,
                "org_name": org.org_name,
                "account_name": account.account_name,
                "aliases": alias_str,
                "priority": org.priority,
                "status": org.status if account.status == "active" else account.status,
                "biz": account.biz,
                "wechat_id": account.wechat_id,
            }
        )
    return rows


def _next_org_code(db: Session, prefix: str = "wc_") -> str:
    orgs = list(db.scalars(select(Organization.org_code).where(Organization.org_code.is_not(None))))
    max_num = 0
    for code in orgs:
        if code and code.startswith(prefix):
            suffix = code[len(prefix) :]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"


def create_pilot_account_row(
    db: Session,
    *,
    org_code: str | None,
    org_name: str,
    account_name: str,
    aliases: str | list[str] | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    code = org_code.strip() if org_code else _next_org_code(db)
    org = upsert_organization_by_code(
        db,
        org_code=code,
        org_name=org_name,
        aliases=aliases,
        priority=priority,
        status="active",
    )
    existing = db.scalar(
        select(WechatAccount).where(
            WechatAccount.org_id == org.id,
            WechatAccount.account_name == normalize_text(account_name),
        )
    )
    if existing:
        if existing.status != "active":
            existing.status = "active"
            db.commit()
            db.refresh(existing)
        account = existing
    else:
        account = bind_wechat_account(
            db,
            org.id,
            account_name=account_name,
            alias_names=aliases,
            status="active",
        )
    rows = list_pilot_accounts(db, include_inactive=True)
    match = next(r for r in rows if r["account_id"] == account.id)
    return match


def update_pilot_account_row(
    db: Session,
    account_id: int,
    *,
    org_code: str | None = None,
    org_name: str | None = None,
    account_name: str | None = None,
    aliases: str | list[str] | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    account = db.get(WechatAccount, account_id)
    if account is None or account.org_id is None:
        raise ValueError(f"Wechat account not found or unbound: {account_id}")
    org = db.get(Organization, account.org_id)
    if org is None:
        raise ValueError(f"Organization not found for account: {account_id}")

    if org_code is not None and org_code.strip() and org_code != org.org_code:
        conflict = db.scalar(select(Organization).where(Organization.org_code == org_code))
        if conflict and conflict.id != org.id:
            raise ValueError(f"org_code already exists: {org_code}")
        org.org_code = org_code.strip()

    if org_name is not None:
        org.org_name = normalize_text(org_name)
    if aliases is not None:
        org.aliases = normalize_aliases(aliases)
    if priority is not None:
        org.priority = priority
    if status is not None:
        org.status = status
        account.status = status

    if account_name is not None:
        account.account_name = normalize_text(account_name)

    db.commit()
    db.refresh(org)
    db.refresh(account)
    rows = list_pilot_accounts(db, include_inactive=True)
    return next(r for r in rows if r["account_id"] == account.id)


def delete_pilot_account_row(db: Session, account_id: int) -> None:
    account = db.get(WechatAccount, account_id)
    if account is None:
        raise ValueError(f"Wechat account not found: {account_id}")
    account.status = "inactive"
    org_id = account.org_id
    db.commit()
    if org_id is not None:
        active_count = db.scalar(
            select(func.count())
            .select_from(WechatAccount)
            .where(
                WechatAccount.org_id == org_id,
                WechatAccount.status == "active",
            )
        )
        if not active_count:
            org = db.get(Organization, org_id)
            if org:
                org.status = "inactive"
                db.commit()


def verify_wechat_account_mapping(db: Session, account_id: int) -> WechatAccount:
    account = db.get(WechatAccount, account_id)
    if account is None:
        raise ValueError(f"Wechat account not found: {account_id}")
    account.last_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
    account.status = "active"
    db.commit()
    db.refresh(account)
    return account
