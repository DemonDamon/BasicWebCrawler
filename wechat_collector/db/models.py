from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from wechat_collector.db.base import Base

PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")
ForeignKeyType = BigInteger().with_variant(Integer, "sqlite")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    org_code: Mapped[str | None] = mapped_column(String(64), unique=True)
    org_name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[Any] | None] = mapped_column(JSON)
    region: Mapped[str | None] = mapped_column(String(128))
    org_level: Mapped[str | None] = mapped_column(String(64))
    official_website: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), default="normal", server_default="normal")
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    wechat_accounts: Mapped[list["WechatAccount"]] = relationship(back_populates="organization")
    article_candidates: Mapped[list["ArticleCandidate"]] = relationship(
        back_populates="organization"
    )
    articles: Mapped[list["Article"]] = relationship(back_populates="organization")


class WechatAccount(Base):
    __tablename__ = "wechat_accounts"
    __table_args__ = (Index("ix_wechat_accounts_org_id", "org_id"),)

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKeyType, ForeignKey("organizations.id"), nullable=True
    )
    account_name: Mapped[str] = mapped_column(Text, nullable=False)
    wechat_id: Mapped[str | None] = mapped_column(String(128))
    biz: Mapped[str | None] = mapped_column(String(256))
    alias_names: Mapped[list[Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization: Mapped[Organization | None] = relationship(back_populates="wechat_accounts")
    article_candidates: Mapped[list["ArticleCandidate"]] = relationship(
        back_populates="wechat_account"
    )
    articles: Mapped[list["Article"]] = relationship(back_populates="wechat_account")
    health: Mapped["AccountHealth | None"] = relationship(
        back_populates="wechat_account", uselist=False
    )


class ArticleCandidate(Base):
    __tablename__ = "article_candidates"
    __table_args__ = (
        Index("ix_article_candidates_normalized_url", "normalized_url", unique=True),
        Index("ix_article_candidates_org_id", "org_id"),
        Index("ix_article_candidates_account_id", "account_id"),
        Index("ix_article_candidates_status", "status"),
    )

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKeyType, ForeignKey("organizations.id"), nullable=True
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKeyType, ForeignKey("wechat_accounts.id"), nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    normalized_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(64))
    sources: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fail_reason: Mapped[str | None] = mapped_column(Text)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime)

    organization: Mapped[Organization | None] = relationship(back_populates="article_candidates")
    wechat_account: Mapped[WechatAccount | None] = relationship(
        back_populates="article_candidates"
    )


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_content_hash", "content_hash"),
        Index("ix_articles_org_id", "org_id"),
        Index("ix_articles_account_id", "account_id"),
        Index("ix_articles_canonical_url", "canonical_url"),
    )

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKeyType, ForeignKey("organizations.id"), nullable=True
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKeyType, ForeignKey("wechat_accounts.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    account_name: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime)
    cover_url: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    content_html: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(64))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    organization: Mapped[Organization | None] = relationship(back_populates="articles")
    wechat_account: Mapped[WechatAccount | None] = relationship(back_populates="articles")


class AccountHealth(Base):
    __tablename__ = "account_health"
    __table_args__ = (
        Index("ix_account_health_account_id", "account_id", unique=True),
    )

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKeyType, ForeignKey("wechat_accounts.id"), nullable=False, unique=True
    )
    last_discovered_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
    article_count_1d: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    article_count_7d: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    article_count_30d: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(32), default="normal", server_default="normal")
    warning_reason: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    wechat_account: Mapped[WechatAccount] = relationship(back_populates="health")


class DiscoverySourceStat(Base):
    __tablename__ = "discovery_source_stats"

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    consecutive_empty_runs: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="normal", server_default="normal")
    warning_reason: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
