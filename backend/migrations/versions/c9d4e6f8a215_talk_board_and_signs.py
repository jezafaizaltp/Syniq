"""talk board needs on raised hands, sign-language video links per topic

Revision ID: c9d4e6f8a215
Revises: b7e2d4f6a813
Create Date: 2026-11-10 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d4e6f8a215'
down_revision: Union[str, Sequence[str], None] = 'b7e2d4f6a813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('help_requests', sa.Column('need', sa.String(length=20), nullable=True))
    op.add_column('concepts', sa.Column('sign_videos', sa.JSON(none_as_null=True), nullable=True))


def downgrade() -> None:
    op.drop_column('concepts', 'sign_videos')
    op.drop_column('help_requests', 'need')
