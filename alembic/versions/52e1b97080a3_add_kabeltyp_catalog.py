"""add kabeltyp catalog

Revision ID: 52e1b97080a3
Revises: ca6d87134691
Create Date: 2026-11-17 20:25:30.178235

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "52e1b97080a3"
down_revision: Union[str, Sequence[str], None] = "ca6d87134691"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _catalog_rows() -> list[dict[str, object]]:
    rows = [
        ("Cat6", "kupfer", "RJ45", "RJ45", "Blau"),
        ("Cat6A", "kupfer", "RJ45", "RJ45", "Blau"),
        ("Cat7", "kupfer", "RJ45", "RJ45", "Blau"),
        ("DAC", "dac", "SFP+/QSFP", "SFP+/QSFP", "Grau"),
        ("LC-LC", "lwl", "LC-Duplex", "LC-Duplex", "Erika-Violett"),
        ("SC-SC", "lwl", "SC-Duplex", "SC-Duplex", "Erika-Violett"),
        ("SFP+", "dac", "SFP+", "SFP+", "Grau"),
        ("Strom-C13", "strom", "C13", "C14", "Rot"),
        ("Strom-C19", "strom", "C19", "C20", "Rot"),
        ("Strom-Schuko", "strom", "Schuko", "C13", "Rot"),
        (
            "Strom-CEE-16A-3P",
            "strom",
            "CEE-16A-3P",
            "CEE-16A-3P",
            None,
        ),
        (
            "Strom-CEE-32A-3P",
            "strom",
            "CEE-32A-3P",
            "CEE-32A-3P",
            None,
        ),
        (
            "Strom-CEE-63A-3P",
            "strom",
            "CEE-63A-3P",
            "CEE-63A-3P",
            None,
        ),
        ("sonstige", "sonstige", "sonstige", "sonstige", None),
    ]
    catalog = [
        {
            "name": name,
            "kategorie": kategorie,
            "stecker_a": stecker_a,
            "stecker_b": stecker_b,
            "enden_a": 1,
            "enden_b": 1,
            "standard_farbe": standard_farbe,
            "alt_typ": name,
            "aktiv": True,
        }
        for name, kategorie, stecker_a, stecker_b, standard_farbe in rows
    ]
    catalog.extend(
        [
            {
                "name": "Breakout QSFP+→4×SFP+",
                "kategorie": "breakout",
                "stecker_a": "QSFP+",
                "stecker_b": "SFP+",
                "enden_a": 1,
                "enden_b": 4,
                "standard_farbe": None,
                "alt_typ": "sonstige",
                "aktiv": True,
            },
            {
                "name": "Breakout QSFP28→4×SFP28",
                "kategorie": "breakout",
                "stecker_a": "QSFP28",
                "stecker_b": "SFP28",
                "enden_a": 1,
                "enden_b": 4,
                "standard_farbe": None,
                "alt_typ": "sonstige",
                "aktiv": True,
            },
            {
                "name": "Breakout QSFP-DD→8×SFP56",
                "kategorie": "breakout",
                "stecker_a": "QSFP-DD",
                "stecker_b": "SFP56",
                "enden_a": 1,
                "enden_b": 8,
                "standard_farbe": None,
                "alt_typ": "sonstige",
                "aktiv": True,
            },
        ]
    )
    return catalog


def upgrade() -> None:
    op.create_table(
        "kabeltypen",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "kategorie",
            sa.Enum(
                "kupfer",
                "lwl",
                "dac",
                "aoc",
                "breakout",
                "strom",
                "sonstige",
            ),
            nullable=False,
        ),
        sa.Column("stecker_a", sa.String(length=50), nullable=False),
        sa.Column("stecker_b", sa.String(length=50), nullable=False),
        sa.Column("enden_a", sa.Integer(), server_default="1", nullable=False),
        sa.Column("enden_b", sa.Integer(), server_default="1", nullable=False),
        sa.Column("standard_farbe", sa.String(length=30), nullable=True),
        sa.Column(
            "alt_typ",
            sa.String(length=50),
            server_default="sonstige",
            nullable=False,
        ),
        sa.Column("aktiv", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("cables", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kabeltyp_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_cables_kabeltyp_id_kabeltypen",
            "kabeltypen",
            ["kabeltyp_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    kabeltypen = sa.table(
        "kabeltypen",
        sa.column("name", sa.String),
        sa.column("kategorie", sa.String),
        sa.column("stecker_a", sa.String),
        sa.column("stecker_b", sa.String),
        sa.column("enden_a", sa.Integer),
        sa.column("enden_b", sa.Integer),
        sa.column("standard_farbe", sa.String),
        sa.column("alt_typ", sa.String),
        sa.column("aktiv", sa.Boolean),
    )
    op.bulk_insert(kabeltypen, _catalog_rows())
    op.execute(
        sa.text(
            """
            UPDATE cables
            SET kabeltyp_id = (
                SELECT kabeltypen.id
                FROM kabeltypen
                WHERE kabeltypen.name = cables.typ
            )
            WHERE EXISTS (
                SELECT 1
                FROM kabeltypen
                WHERE kabeltypen.name = cables.typ
            )
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("cables", schema=None) as batch_op:
        batch_op.drop_constraint("fk_cables_kabeltyp_id_kabeltypen", type_="foreignkey")
        batch_op.drop_column("kabeltyp_id")
    op.drop_table("kabeltypen")
