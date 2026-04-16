"""add_payment_tables_fixed

Revision ID: 5cc44992c2b3
Revises: c6d3bed17884
Create Date: 2026-04-11 10:26:19.128177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cc44992c2b3'
down_revision: Union[str, Sequence[str], None] = 'c6d3bed17884'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
