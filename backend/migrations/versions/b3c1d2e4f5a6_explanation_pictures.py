"""explanation pictures

Revision ID: b3c1d2e4f5a6
Revises: 59711441e707
Create Date: 2026-11-02 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c1d2e4f5a6'
down_revision: Union[str, Sequence[str], None] = '59711441e707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A drawing for the visual explanation style (see app/pictures.py)."""
    op.add_column('explanations', sa.Column('picture', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('explanations', 'picture')
