"""update_runbook_execution_status_enum

Revision ID: 151e01210e99
Revises: e123456789ab
Create Date: 2026-05-25 14:24:56.094380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '151e01210e99'
down_revision: Union[str, Sequence[str], None] = 'e123456789ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Change to String temporarily to allow updating values
    op.alter_column('runbook_executions', 'status',
               existing_type=mysql.ENUM('aktiv', 'abgeschlossen', 'abgebrochen', collation='utf8mb4_unicode_ci'),
               type_=sa.String(50),
               existing_nullable=False)
    
    # 2. Update existing rows
    op.execute("UPDATE runbook_executions SET status = 'offen' WHERE status = 'aktiv'")
    op.execute("UPDATE runbook_executions SET status = 'verworfen' WHERE status = 'abgebrochen'")
    
    # 3. Change to new ENUM
    op.alter_column('runbook_executions', 'status',
               existing_type=sa.String(50),
               type_=sa.Enum('offen', 'abgeschlossen', 'verworfen'),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Change to String temporarily
    op.alter_column('runbook_executions', 'status',
               existing_type=sa.Enum('offen', 'abgeschlossen', 'verworfen'),
               type_=sa.String(50),
               existing_nullable=False)
    
    # 2. Update values back
    op.execute("UPDATE runbook_executions SET status = 'aktiv' WHERE status = 'offen'")
    op.execute("UPDATE runbook_executions SET status = 'abgebrochen' WHERE status = 'verworfen'")
    
    # 3. Change to old ENUM
    op.alter_column('runbook_executions', 'status',
               existing_type=sa.String(50),
               type_=mysql.ENUM('aktiv', 'abgeschlossen', 'abgebrochen', collation='utf8mb4_unicode_ci'),
               existing_nullable=False)
