"""concept activities

Revision ID: e4a7c2f91b38
Revises: d8f3b6a2c915
Create Date: 2026-11-07 06:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4a7c2f91b38'
down_revision: Union[str, Sequence[str], None] = 'd8f3b6a2c915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A hands-on activity per topic (see app/activities.py)."""
    op.add_column('concepts', sa.Column('activity', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('concepts', 'activity')
