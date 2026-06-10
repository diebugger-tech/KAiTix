"""add usv to device typ enum

Revision ID: 47148cf138dd
Revises: 1f7296a624f3
Create Date: 2026-05-28 11:30:04.589464

"""

from typing import Sequence, Union
from alembic import op

revision: str = "47148cf138dd"
down_revision: Union[str, Sequence[str], None] = "1f7296a624f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TYPES = (
    "'server','switch','pdu','storage','firewall',"
    "'kentix_raconode','kentix_doormaster',"
    "'kentix_multisensor','sonstige'"
)
NEW_TYPES = (
    "'server','switch','pdu','storage','firewall',"
    "'kentix_raconode','kentix_doormaster',"
    "'kentix_multisensor','usv','sonstige'"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE devices MODIFY COLUMN typ ENUM({NEW_TYPES}) NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE devices MODIFY COLUMN typ ENUM({OLD_TYPES}) NOT NULL")
