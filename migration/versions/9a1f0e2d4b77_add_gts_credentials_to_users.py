"""add_gts_credentials_to_users

Revision ID: 9a1f0e2d4b77
Revises: 7d3a2e7f1c11
Create Date: 2026-04-02 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1f0e2d4b77"
down_revision: Union[str, Sequence[str], None] = "7d3a2e7f1c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("gts_email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("gts_password", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "gts_password")
    op.drop_column("users", "gts_email")
