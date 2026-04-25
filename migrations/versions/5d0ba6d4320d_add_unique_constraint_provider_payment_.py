"""add unique constraint provider_payment_id

Revision ID: 5d0ba6d4320d
Revises: 5cc44992c2b3
Create Date: 2026-04-25 14:15:30.714939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d0ba6d4320d'
down_revision: Union[str, Sequence[str], None] = '5cc44992c2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
