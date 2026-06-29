"""initial schema: organizations, wechat_accounts, article_candidates, articles, account_health

Revision ID: 001_initial
Revises:
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_code", sa.String(length=64), nullable=True),
        sa.Column("org_name", sa.Text(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("org_level", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=32), server_default="normal", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_code"),
    )

    op.create_table(
        "wechat_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("account_name", sa.Text(), nullable=False),
        sa.Column("wechat_id", sa.String(length=128), nullable=True),
        sa.Column("biz", sa.String(length=256), nullable=True),
        sa.Column("alias_names", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wechat_accounts_org_id", "wechat_accounts", ["org_id"], unique=False)

    op.create_table(
        "article_candidates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fail_reason", sa.Text(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("crawled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["wechat_accounts.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_article_candidates_account_id", "article_candidates", ["account_id"], unique=False)
    op.create_index("ix_article_candidates_normalized_url", "article_candidates", ["normalized_url"], unique=False)
    op.create_index("ix_article_candidates_org_id", "article_candidates", ["org_id"], unique=False)
    op.create_index("ix_article_candidates_status", "article_candidates", ["status"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("account_name", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("publish_time", sa.DateTime(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("collected_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["wechat_accounts.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_articles_account_id", "articles", ["account_id"], unique=False)
    op.create_index("ix_articles_canonical_url", "articles", ["canonical_url"], unique=False)
    op.create_index("ix_articles_content_hash", "articles", ["content_hash"], unique=False)
    op.create_index("ix_articles_org_id", "articles", ["org_id"], unique=False)

    op.create_table(
        "account_health",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("last_discovered_at", sa.DateTime(), nullable=True),
        sa.Column("last_crawled_at", sa.DateTime(), nullable=True),
        sa.Column("article_count_1d", sa.Integer(), server_default="0", nullable=False),
        sa.Column("article_count_7d", sa.Integer(), server_default="0", nullable=False),
        sa.Column("article_count_30d", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="normal", nullable=False),
        sa.Column("warning_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["wechat_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )
    op.create_index("ix_account_health_account_id", "account_health", ["account_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_account_health_account_id", table_name="account_health")
    op.drop_table("account_health")
    op.drop_index("ix_articles_org_id", table_name="articles")
    op.drop_index("ix_articles_content_hash", table_name="articles")
    op.drop_index("ix_articles_canonical_url", table_name="articles")
    op.drop_index("ix_articles_account_id", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_article_candidates_status", table_name="article_candidates")
    op.drop_index("ix_article_candidates_org_id", table_name="article_candidates")
    op.drop_index("ix_article_candidates_normalized_url", table_name="article_candidates")
    op.drop_index("ix_article_candidates_account_id", table_name="article_candidates")
    op.drop_table("article_candidates")
    op.drop_index("ix_wechat_accounts_org_id", table_name="wechat_accounts")
    op.drop_table("wechat_accounts")
    op.drop_table("organizations")
