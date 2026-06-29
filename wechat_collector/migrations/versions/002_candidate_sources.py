"""add candidate sources and unique normalized_url

Revision ID: 002_candidate_sources
Revises: 001_initial
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_candidate_sources"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("article_candidates") as batch_op:
        batch_op.add_column(sa.Column("sources", sa.JSON(), nullable=True))
        batch_op.drop_index("ix_article_candidates_normalized_url")
        batch_op.create_index(
            "ix_article_candidates_normalized_url",
            ["normalized_url"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("article_candidates") as batch_op:
        batch_op.drop_index("ix_article_candidates_normalized_url")
        batch_op.create_index(
            "ix_article_candidates_normalized_url",
            ["normalized_url"],
            unique=False,
        )
        batch_op.drop_column("sources")
