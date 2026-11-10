"""Scope location history to assignments and constrain active rider capacity.

Revision ID: 6fa3ac25c821
Revises: 4e31c9bd72a1
Create Date: 2026-11-08 18:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6fa3ac25c821"
down_revision: str | Sequence[str] | None = "4e31c9bd72a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rider_locations",
        sa.Column("assignment_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_rider_locations_assignment_id_assignments",
        "rider_locations",
        "assignments",
        ["assignment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_rider_locations_assignment_id"),
        "rider_locations",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        "uq_assignments_one_active_per_rider",
        "assignments",
        ["rider_id"],
        unique=True,
        postgresql_where=sa.text(
            "assignment_status IN ('pending', 'accepted')"
        ),
        sqlite_where=sa.text(
            "assignment_status IN ('pending', 'accepted')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_assignments_one_active_per_rider", table_name="assignments"
    )
    op.drop_index(
        op.f("ix_rider_locations_assignment_id"), table_name="rider_locations"
    )
    op.drop_constraint(
        "fk_rider_locations_assignment_id_assignments",
        "rider_locations",
        type_="foreignkey",
    )
    op.drop_column("rider_locations", "assignment_id")
