"""Add user verification approval state.

Revision ID: 4e31c9bd72a1
Revises: 97efcca21231
Create Date: 2026-11-08 13:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e31c9bd72a1"
down_revision: str | Sequence[str] | None = "97efcca21231"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.execute(sa.text("UPDATE users SET is_verified = true"))


def downgrade() -> None:
    op.drop_column("users", "is_verified")
