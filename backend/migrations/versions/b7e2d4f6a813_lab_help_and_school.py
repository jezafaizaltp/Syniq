"""school settings, raised hands, today's chapter

Revision ID: b7e2d4f6a813
Revises: a1f3c5e7b902
Create Date: 2026-11-10 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7e2d4f6a813'
down_revision: Union[str, Sequence[str], None] = 'a1f3c5e7b902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'school_settings',
        sa.Column('key', sa.String(length=40), primary_key=True),
        sa.Column('value', sa.String(length=500), nullable=False),
    )
    op.create_table(
        'help_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('class_group_id', sa.Integer(), sa.ForeignKey('class_groups.id'), nullable=False),
        sa.Column('concept_id', sa.Integer(), sa.ForeignKey('concepts.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_help_requests_student_id', 'help_requests', ['student_id'])
    op.create_index('ix_help_requests_class_group_id', 'help_requests', ['class_group_id'])
    op.add_column('class_groups', sa.Column('today_chapter_id', sa.Integer(), nullable=True))
    op.add_column('class_groups', sa.Column('today_set_on', sa.Date(), nullable=True))
    op.create_foreign_key('fk_class_groups_today_chapter', 'class_groups', 'chapters', ['today_chapter_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_class_groups_today_chapter', 'class_groups', type_='foreignkey')
    op.drop_column('class_groups', 'today_set_on')
    op.drop_column('class_groups', 'today_chapter_id')
    op.drop_index('ix_help_requests_class_group_id', 'help_requests')
    op.drop_index('ix_help_requests_student_id', 'help_requests')
    op.drop_table('help_requests')
    op.drop_table('school_settings')
