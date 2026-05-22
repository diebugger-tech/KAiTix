"""add storage and firewall to device typ enum

Revision ID: ae6739f9dde1
Revises: 76ba1eb27e61
Create Date: 2026-05-22 13:46:22.001308

"""

from typing import Sequence, Union
from alembic import op

revision: str = "ae6739f9dde1"
down_revision: Union[str, Sequence[str], None] = "76ba1eb27e61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TYPES = (
    "'server','switch','pdu','kentix_raconode',"
    "'kentix_doormaster','kentix_multisensor','sonstige'"
)
NEW_TYPES = (
    "'server','switch','pdu','storage','firewall',"
    "'kentix_raconode','kentix_doormaster',"
    "'kentix_multisensor','sonstige'"
)


def upgrade() -> None:
    op.execute(f"ALTER TABLE devices MODIFY COLUMN typ ENUM({NEW_TYPES}) NOT NULL")


def downgrade() -> None:
    op.execute(f"ALTER TABLE devices MODIFY COLUMN typ ENUM({OLD_TYPES}) NOT NULL")
