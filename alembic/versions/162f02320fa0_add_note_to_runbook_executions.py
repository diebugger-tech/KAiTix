"""add_note_to_runbook_executions

Revision ID: 162f02320fa0
Revises: 151e01210e99
Create Date: 2026-05-25 14:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "162f02320fa0"
down_revision: Union[str, None] = "151e01210e99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runbook_executions", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("runbook_executions", "note")
