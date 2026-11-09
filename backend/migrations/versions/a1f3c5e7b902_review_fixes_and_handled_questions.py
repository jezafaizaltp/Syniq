"""review fixes and handled questions

Revision ID: a1f3c5e7b902
Revises: e4a7c2f91b38
Create Date: 2026-11-09 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1f3c5e7b902'
down_revision: Union[str, Sequence[str], None] = 'e4a7c2f91b38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Teacher fix notes from the uploaded review sheet, and a 'handled' mark on asked questions."""
    op.add_column('items', sa.Column('fix_note', sa.Text(), server_default='', nullable=False))
    op.add_column('tutor_questions', sa.Column('handled', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column('tutor_questions', 'handled')
    op.drop_column('items', 'fix_note')
