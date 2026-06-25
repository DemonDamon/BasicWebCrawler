"""Phase 2: discovery, scheduler, monitoring fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_phase2"
down_revision: Union[str, Sequence[str], None] = "002_candidate_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(sa.Column("official_website", sa.Text(), nullable=True))

    with op.batch_alter_table("article_candidates") as batch_op:
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_article_candidates_next_retry_at", ["next_retry_at"], unique=False)

    op.create_table(
        "discovery_source_stats",
        sa.Column("source", sa.String(length=64), primary_key=True),
        sa.Column("consecutive_empty_runs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_hit_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="normal", nullable=False),
        sa.Column("warning_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("discovery_source_stats")
    with op.batch_alter_table("article_candidates") as batch_op:
        batch_op.drop_index("ix_article_candidates_next_retry_at")
        batch_op.drop_column("next_retry_at")
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_column("official_website")
