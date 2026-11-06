"""tutor questions

Revision ID: c7e2a9d41f03
Revises: b3c1d2e4f5a6
Create Date: 2026-11-06 06:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7e2a9d41f03'
down_revision: Union[str, Sequence[str], None] = 'b3c1d2e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Questions Ask SYNiq couldn't answer from the content, with no student details."""
    op.create_table(
        'tutor_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.String(length=600), nullable=False),
        sa.Column('answered_by', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tutor_questions_concept_id'), 'tutor_questions', ['concept_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tutor_questions_concept_id'), table_name='tutor_questions')
    op.drop_table('tutor_questions')
