"""puzzle answers

Revision ID: d8f3b6a2c915
Revises: c7e2a9d41f03
Create Date: 2026-11-06 09:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8f3b6a2c915'
down_revision: Union[str, Sequence[str], None] = 'c7e2a9d41f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Thinking puzzles answered inside lessons, kept only with the parent's consent."""
    op.create_table(
        'puzzle_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=20), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_puzzle_answers_student_id'), 'puzzle_answers', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_puzzle_answers_student_id'), table_name='puzzle_answers')
    op.drop_table('puzzle_answers')
