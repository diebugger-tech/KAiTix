"""add_runbooks_and_vms

Revision ID: e123456789ab
Revises: d02c996b4cfd
Create Date: 2026-05-25 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e123456789ab'
down_revision: Union[str, None] = 'd02c996b4cfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. virtual_machines
    op.create_table('virtual_machines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('host_device_id', sa.Integer(), nullable=False),
        sa.Column('hypervisor_typ', sa.Enum('vmware', 'hyper-v', 'kvm', 'xcpng', 'sonstige'), nullable=False),
        sa.Column('vm_id_extern', sa.String(length=50), nullable=True),
        sa.Column('betriebssystem', sa.String(length=100), nullable=True),
        sa.Column('dienst', sa.String(length=255), nullable=True),
        sa.Column('ip_adresse', sa.String(length=45), nullable=True),
        sa.Column('depends_on_vm_id', sa.Integer(), nullable=True),
        sa.Column('shutdown_priority', sa.Integer(), server_default='5', nullable=True),
        sa.Column('responsible', sa.String(length=100), nullable=True),
        sa.Column('bemerkung', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['depends_on_vm_id'], ['virtual_machines.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['host_device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. runbooks
    op.create_table('runbooks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('typ', sa.Enum('shutdown', 'startup', 'wartung', 'notfall', 'custom'), nullable=False),
        sa.Column('beschreibung', sa.Text(), nullable=True),
        sa.Column('generated_from_id', sa.Integer(), nullable=True),
        sa.Column('erstellt_am', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('erstellt_von', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['generated_from_id'], ['runbooks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. runbook_layers
    op.create_table('runbook_layers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('runbook_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('markdown_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['runbook_id'], ['runbooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. runbook_devices
    op.create_table('runbook_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('runbook_id', sa.Integer(), nullable=False),
        sa.Column('layer_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('vm_id', sa.Integer(), nullable=True),
        sa.Column('freitext', sa.String(length=255), nullable=True),
        sa.Column('delay_seconds', sa.Integer(), server_default='30', nullable=True),
        sa.Column('responsible', sa.String(length=100), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['layer_id'], ['runbook_layers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['runbook_id'], ['runbooks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vm_id'], ['virtual_machines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. runbook_executions
    op.create_table('runbook_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('runbook_id', sa.Integer(), nullable=False),
        sa.Column('modus', sa.Enum('shutdown', 'startup'), nullable=False),
        sa.Column('gestartet_am', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('gestartet_von', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('aktiv', 'abgeschlossen', 'abgebrochen'), server_default='aktiv', nullable=True),
        sa.ForeignKeyConstraint(['runbook_id'], ['runbooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. runbook_execution_steps
    op.create_table('runbook_execution_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),
        sa.Column('runbook_device_id', sa.Integer(), nullable=False),
        sa.Column('abgehakt_am', sa.DateTime(), nullable=True),
        sa.Column('abgehakt_von', sa.String(length=100), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['runbook_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['runbook_device_id'], ['runbook_devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('runbook_execution_steps')
    op.drop_table('runbook_executions')
    op.drop_table('runbook_devices')
    op.drop_table('runbook_layers')
    op.drop_table('runbooks')
    op.drop_table('virtual_machines')
