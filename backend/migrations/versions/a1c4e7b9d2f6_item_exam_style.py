"""item exam style: marks questions written in a board-exam format (case-based, assertion-reason...)

Revision ID: a1c4e7b9d2f6
Revises: e6b1c3d5f702
Create Date: 2026-11-16 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c4e7b9d2f6'
down_revision: Union[str, Sequence[str], None] = 'e6b1c3d5f702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('exam', sa.String(length=20), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('items', 'exam')
