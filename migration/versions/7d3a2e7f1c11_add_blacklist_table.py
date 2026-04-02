"""add_blacklist_table

Revision ID: 7d3a2e7f1c11
Revises: 165c9fab873a
Create Date: 2026-04-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7d3a2e7f1c11"
down_revision: Union[str, Sequence[str], None] = "165c9fab873a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure enum type exists once even if it was left behind in dev DB.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE blacklisttriptype AS ENUM ('OW', 'RT', 'ANY');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )

    op.create_table(
        "black_list",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column(
            "trip_type",
            postgresql.ENUM("OW", "RT", "ANY", name="blacklisttriptype", create_type=False),
            nullable=False,
        ),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_black_list_user_id"), "black_list", ["user_id"], unique=False)
    op.create_index(
        "ux_black_list_rule",
        "black_list",
        ["user_id", "origin", "destination", "trip_type", "departure_date", "return_date"],
        unique=True,
    )
    op.create_index(
        "idx_black_list_lookup",
        "black_list",
        ["user_id", "origin", "destination", "trip_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_black_list_lookup", table_name="black_list")
    op.drop_index("ux_black_list_rule", table_name="black_list")
    op.drop_index(op.f("ix_black_list_user_id"), table_name="black_list")
    op.drop_table("black_list")
    op.execute("DROP TYPE IF EXISTS blacklisttriptype")
