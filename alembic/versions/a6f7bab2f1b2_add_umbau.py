"""add umbau

Revision ID: a6f7bab2f1b2
Revises: 27f768e65156
Create Date: 2026-11-17 22:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6f7bab2f1b2"
down_revision: Union[str, Sequence[str], None] = "27f768e65156"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "umbauten",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("beschreibung", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "erfassung",
                "rueckbau",
                "umbau",
                "wiederaufbau",
                "abgeschlossen",
                "verworfen",
            ),
            nullable=False,
        ),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
        sa.Column("erstellt_von", sa.String(length=100), nullable=True),
        sa.Column("eingefroren_am", sa.DateTime(), nullable=True),
        sa.Column("eingefroren_von", sa.String(length=100), nullable=True),
        sa.Column("abgeschlossen_am", sa.DateTime(), nullable=True),
        sa.Column("abgeschlossen_von", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "umbau_racks",
        sa.Column("umbau_id", sa.Integer(), nullable=False),
        sa.Column("rack_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["rack_id"], ["racks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["umbau_id"], ["umbauten.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("umbau_id", "rack_id"),
    )
    op.create_table(
        "umbau_geraetepruefungen",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("umbau_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("device_name", sa.String(length=100), nullable=False),
        sa.Column("bestaetigt_am", sa.DateTime(), nullable=False),
        sa.Column("bestaetigt_von", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["umbau_id"], ["umbauten.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "umbau_id", "device_id", name="uq_umbau_geraetepruefungen_umbau_device"
        ),
    )
    op.create_index(
        "ix_umbau_geraetepruefungen_umbau_id",
        "umbau_geraetepruefungen",
        ["umbau_id"],
        unique=False,
    )
    op.create_table(
        "umbau_enden",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("umbau_id", sa.Integer(), nullable=False),
        sa.Column("cable_id", sa.Integer(), nullable=True),
        sa.Column("strand_number", sa.Integer(), nullable=True),
        sa.Column("seite", sa.Enum("A", "B"), nullable=False),
        sa.Column("ende_nr", sa.Integer(), nullable=False),
        sa.Column("soll_device_id", sa.Integer(), nullable=True),
        sa.Column("soll_device_name", sa.String(length=100), nullable=False),
        sa.Column("soll_rack_name", sa.String(length=100), nullable=True),
        sa.Column("soll_port", sa.String(length=50), nullable=False),
        sa.Column("kabel_nr", sa.String(length=50), nullable=True),
        sa.Column("kabeltyp_name", sa.String(length=100), nullable=False),
        sa.Column("kategorie", sa.String(length=20), nullable=False),
        sa.Column("farbe", sa.String(length=30), nullable=True),
        sa.Column(
            "status",
            sa.Enum("gesteckt", "abgeklemmt", "angeklemmt", "angeklemmt_abweichend"),
            nullable=False,
        ),
        sa.Column("abgeklemmt_am", sa.DateTime(), nullable=True),
        sa.Column("abgeklemmt_von", sa.String(length=100), nullable=True),
        sa.Column("angeklemmt_am", sa.DateTime(), nullable=True),
        sa.Column("angeklemmt_von", sa.String(length=100), nullable=True),
        sa.Column("ist_device_id", sa.Integer(), nullable=True),
        sa.Column("ist_device_name", sa.String(length=100), nullable=True),
        sa.Column("ist_port", sa.String(length=50), nullable=True),
        sa.Column("abweichung_grund", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["cable_id"], ["cables.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ist_device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["soll_device_id"], ["devices.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["umbau_id"], ["umbauten.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "umbau_id",
            "cable_id",
            "seite",
            "ende_nr",
            name="uq_umbau_enden_umbau_cable_seite_nr",
        ),
    )
    op.create_index(
        "ix_umbau_enden_umbau_id", "umbau_enden", ["umbau_id"], unique=False
    )
    op.create_table(
        "umbau_ereignisse",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("umbau_id", sa.Integer(), nullable=False),
        sa.Column("ende_id", sa.Integer(), nullable=True),
        sa.Column("von_status", sa.String(length=30), nullable=True),
        sa.Column("nach_status", sa.String(length=30), nullable=False),
        sa.Column("grund", sa.String(length=255), nullable=True),
        sa.Column("benutzer", sa.String(length=100), nullable=True),
        sa.Column("zeitpunkt", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ende_id"], ["umbau_enden.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["umbau_id"], ["umbauten.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_umbau_ereignisse_umbau_id", "umbau_ereignisse", ["umbau_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_umbau_ereignisse_umbau_id", table_name="umbau_ereignisse")
    op.drop_table("umbau_ereignisse")
    op.drop_index("ix_umbau_enden_umbau_id", table_name="umbau_enden")
    op.drop_table("umbau_enden")
    op.drop_index(
        "ix_umbau_geraetepruefungen_umbau_id", table_name="umbau_geraetepruefungen"
    )
    op.drop_table("umbau_geraetepruefungen")
    op.drop_table("umbau_racks")
    op.drop_table("umbauten")
