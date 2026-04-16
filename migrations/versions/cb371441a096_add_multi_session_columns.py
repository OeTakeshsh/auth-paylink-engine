"""add_multi_session_columns

Revision ID: cb371441a096
Revises: 481ba3181ab5
Create Date: 2026-04-08 06:57:00.779947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb371441a096'
down_revision: Union[str, Sequence[str], None] = '481ba3181ab5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
