"""add notional columns to tracked markets

Revision ID: 9d9c2f5c1b7a
Revises: 3cbc9bc65943
Create Date: 2026-04-29 05:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d9c2f5c1b7a"
down_revision: Union[str, Sequence[str], None] = "3cbc9bc65943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET statement_timeout = 0")
    op.add_column("tracked_markets", sa.Column("buy_notional", sa.Float(), nullable=True))
    op.add_column("tracked_markets", sa.Column("sell_notional", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("tracked_markets", "sell_notional")
    op.drop_column("tracked_markets", "buy_notional")
