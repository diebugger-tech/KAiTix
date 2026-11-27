"""add umbau nachtrag, position und laenge

Revision ID: d4ed62bc8ae1
Revises: a6f7bab2f1b2
Create Date: 2026-11-27 23:30:00.000000

umbau_enden bekommt:
- nachtrag_nr: verbindet die Enden eines im Rückbau nachgetragenen Kabels (cable_id NULL)
- soll_position: Einbauort des Geräts als Text (z. B. "HE 12–13"), Teil der Soll-Kopie
- laenge_m: Länge des Kabels, Teil der Soll-Kopie

Bestehende Enden behalten NULL in allen drei Spalten.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4ed62bc8ae1"
down_revision: Union[str, Sequence[str], None] = "a6f7bab2f1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("umbau_enden", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nachtrag_nr", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("soll_position", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("laenge_m", sa.DECIMAL(precision=6, scale=2), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_umbau_enden_umbau_nachtrag_seite_nr",
            ["umbau_id", "nachtrag_nr", "seite", "ende_nr"],
        )


def downgrade() -> None:
    with op.batch_alter_table("umbau_enden", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_umbau_enden_umbau_nachtrag_seite_nr", type_="unique"
        )
        batch_op.drop_column("laenge_m")
        batch_op.drop_column("soll_position")
        batch_op.drop_column("nachtrag_nr")
