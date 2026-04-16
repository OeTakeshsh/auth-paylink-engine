"""add_multi_session_columns

Revision ID: 481ba3181ab5
Revises: 7ac37fcb4067
Create Date: 2026-04-08 06:09:38.267816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '481ba3181ab5'
down_revision: Union[str, Sequence[str], None] = '7ac37fcb4067'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
