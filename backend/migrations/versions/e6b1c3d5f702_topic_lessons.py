"""topic lessons: each topic can carry a step-by-step lesson taught before practice

Revision ID: e6b1c3d5f702
Revises: d2f5a8c1e734
Create Date: 2026-11-11 13:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6b1c3d5f702'
down_revision: Union[str, Sequence[str], None] = 'd2f5a8c1e734'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('concepts', sa.Column('lesson', sa.JSON(none_as_null=True), nullable=True))


def downgrade() -> None:
    op.drop_column('concepts', 'lesson')
