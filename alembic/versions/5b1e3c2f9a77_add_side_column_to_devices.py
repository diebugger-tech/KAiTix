"""add_side_column_to_devices

Revision ID: 5b1e3c2f9a77
Revises: c2d4e6f8a012
Create Date: 2026-05-22

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "5b1e3c2f9a77"
down_revision: Union[str, Sequence[str], None] = "ae6739f9dde1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column(
            "side",
            sa.Enum("left", "right"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("devices", "side")
