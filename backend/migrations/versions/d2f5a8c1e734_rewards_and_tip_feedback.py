"""rewards and tip feedback: learning events carry the question and tip tag; indexes for daily counts

Revision ID: d2f5a8c1e734
Revises: c9d4e6f8a215
Create Date: 2026-11-11 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2f5a8c1e734'
down_revision: Union[str, Sequence[str], None] = 'c9d4e6f8a215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('learning_events', sa.Column('item_id', sa.Integer(), nullable=True))
    op.add_column('learning_events', sa.Column('detail', sa.String(length=60), nullable=True))
    op.create_index('ix_learning_events_daily', 'learning_events', ['student_id', 'kind', 'created_at'])
    op.create_index('ix_attempts_student_time', 'attempts', ['student_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_attempts_student_time', table_name='attempts')
    op.drop_index('ix_learning_events_daily', table_name='learning_events')
    op.drop_column('learning_events', 'detail')
    op.drop_column('learning_events', 'item_id')
