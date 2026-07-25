"""add composite index to signal snapshots

Revision ID: a1b2c3d4e5f6
Revises: 9d9c2f5c1b7a
Create Date: 2026-07-24 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9d9c2f5c1b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_market_signal_snapshots_market_id_created_at",
        "market_signal_snapshots",
        ["market_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_signal_snapshots_market_id_created_at",
        table_name="market_signal_snapshots",
    )
