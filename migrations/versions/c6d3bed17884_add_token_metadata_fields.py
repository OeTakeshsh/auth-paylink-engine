"""add token metadata fields

Revision ID: c6d3bed17884
Revises: cb371441a096
Create Date: 2026-04-10 09:16:21.241549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d3bed17884'
down_revision: Union[str, Sequence[str], None] = 'cb371441a096'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
