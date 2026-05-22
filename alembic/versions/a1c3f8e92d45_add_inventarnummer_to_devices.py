"""add_inventarnummer_to_devices

Revision ID: a1c3f8e92d45
Revises: b346b3c9139b
Create Date: 2026-05-21

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1c3f8e92d45"
down_revision: Union[str, Sequence[str], None] = "b346b3c9139b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("inventarnummer", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "inventarnummer")
