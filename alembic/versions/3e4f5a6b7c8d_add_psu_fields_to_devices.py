"""add psu_count, psu_nennwatt to devices

Revision ID: 3e4f5a6b7c8d
Revises: 2d5e6a5b62b3
Create Date: 2026-05-22 15:58:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "3e4f5a6b7c8d"
down_revision: Union[str, Sequence[str], None] = "2d5e6a5b62b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("psu_count", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("psu_nennwatt", sa.DECIMAL(8, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "psu_nennwatt")
    op.drop_column("devices", "psu_count")
