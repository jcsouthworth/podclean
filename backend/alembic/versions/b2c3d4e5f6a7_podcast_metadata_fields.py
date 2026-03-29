"""add podcast metadata fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("podcasts", sa.Column("artwork_url", sa.String(), nullable=True))
    op.add_column("podcasts", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("podcasts", sa.Column("author", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("podcasts", "author")
    op.drop_column("podcasts", "description")
    op.drop_column("podcasts", "artwork_url")
