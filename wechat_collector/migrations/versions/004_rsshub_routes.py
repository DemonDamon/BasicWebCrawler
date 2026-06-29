"""004: Add rsshub_routes to wechat_accounts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_rsshub_routes"
down_revision: Union[str, Sequence[str], None] = "003_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("wechat_accounts") as batch_op:
        batch_op.add_column(sa.Column("rsshub_routes", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("wechat_accounts") as batch_op:
        batch_op.drop_column("rsshub_routes")
