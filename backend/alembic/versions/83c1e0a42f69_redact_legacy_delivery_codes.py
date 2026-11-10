"""Redact delivery codes persisted by the demo notification workflow.

Revision ID: 83c1e0a42f69
Revises: 6fa3ac25c821
Create Date: 2026-11-08 18:52:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "83c1e0a42f69"
down_revision: str | Sequence[str] | None = "6fa3ac25c821"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE notifications "
            "SET title = :title, message = :message "
            "WHERE title = :legacy_title"
        ),
        {
            "title": "Delivery verification is ready",
            "message": (
                "Your order is in transit. Open its tracking page to request a "
                "short-lived delivery verification code."
            ),
            "legacy_title": "Delivery verification code",
        },
    )


def downgrade() -> None:
    pass
