"""add_breite_mm_to_racks

Revision ID: c2d4e6f8a012
Revises: a1c3f8e92d45
Create Date: 2026-05-22

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c2d4e6f8a012"
down_revision: Union[str, Sequence[str], None] = "a1c3f8e92d45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "racks",
        sa.Column("breite_mm", sa.Integer(), nullable=False, server_default="600"),
    )


def downgrade() -> None:
    op.drop_column("racks", "breite_mm")
