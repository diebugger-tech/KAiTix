"""add geaendert_von, geaendert_am to racks, devices, cables

Revision ID: 2d5e6a5b62b3
Revises: 5b1e3c2f9a77
Create Date: 2026-05-22 15:39:11.744020

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "2d5e6a5b62b3"
down_revision: Union[str, Sequence[str], None] = "5b1e3c2f9a77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("racks", sa.Column("geaendert_von", sa.String(100), nullable=True))
    op.add_column("racks", sa.Column("geaendert_am", sa.DateTime(), nullable=True))
    op.add_column("devices", sa.Column("geaendert_von", sa.String(100), nullable=True))
    op.add_column("devices", sa.Column("geaendert_am", sa.DateTime(), nullable=True))
    op.add_column("cables", sa.Column("geaendert_von", sa.String(100), nullable=True))
    op.add_column("cables", sa.Column("geaendert_am", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("racks", "geaendert_am")
    op.drop_column("racks", "geaendert_von")
    op.drop_column("devices", "geaendert_am")
    op.drop_column("devices", "geaendert_von")
    op.drop_column("cables", "geaendert_am")
    op.drop_column("cables", "geaendert_von")
