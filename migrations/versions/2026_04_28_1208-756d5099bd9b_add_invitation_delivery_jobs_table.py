from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '756d5099bd9b'
down_revision: Union[str, Sequence[str], None] = '0922b47e72d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


invitation_delivery_status = postgresql.ENUM(
    'pending',
    'queued',
    'processing',
    'sent',
    'failed',
    name='invitation_delivery_status',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    invitation_delivery_status.create(bind, checkfirst=True)

    op.create_table(
        'invitation_delivery_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invitation_id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('status', invitation_delivery_status, nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['invitation_id'], ['invitations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invitation_id', name='uq_invitation_delivery_jobs_invitation_id'),
    )
    op.create_index(
        'ix_invitation_delivery_jobs_status',
        'invitation_delivery_jobs',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index('ix_invitation_delivery_jobs_status', table_name='invitation_delivery_jobs')
    op.drop_table('invitation_delivery_jobs')
    invitation_delivery_status.drop(bind, checkfirst=True)