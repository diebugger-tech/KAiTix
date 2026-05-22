"""add_hardware_fields_to_racks

Revision ID: 76ba1eb27e61
Revises: c2d4e6f8a012
Create Date: 2026-05-22 11:54:35.439962

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "76ba1eb27e61"
down_revision: Union[str, Sequence[str], None] = "c2d4e6f8a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "racks", sa.Column("hersteller", sa.String(length=100), nullable=True)
    )
    op.add_column("racks", sa.Column("modell", sa.String(length=100), nullable=True))
    op.add_column("racks", sa.Column("hardware_type_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("racks", "hardware_type_id")
    op.drop_column("racks", "modell")
    op.drop_column("racks", "hersteller")
