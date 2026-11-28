"""add strand b ends

Revision ID: 27f768e65156
Revises: 52e1b97080a3
Create Date: 2026-11-17 21:36:02.302234

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "27f768e65156"
down_revision: Union[str, Sequence[str], None] = "52e1b97080a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_NAME = "fk_cable_strands_nach_device_id_devices"


def upgrade() -> None:
    # B-Ende eines Breakout-Strangs: Gerät + Port als Text.
    # von_port_id/nach_port_id bleiben unverändert.
    with op.batch_alter_table("cable_strands", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nach_device_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("nach_port", sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            FK_NAME,
            "devices",
            ["nach_device_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("cable_strands", schema=None) as batch_op:
        batch_op.drop_constraint(FK_NAME, type_="foreignkey")
        batch_op.drop_column("nach_port")
        batch_op.drop_column("nach_device_id")
