"""add_telemetry_geofence_pools_sla_and_hash_chain

Revision ID: a070aed128a7
Revises: 83c1e0a42f69
Create Date: 2026-11-24 00:17:25.780482

"""
import hashlib
import json
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a070aed128a7'
down_revision: Union[str, Sequence[str], None] = '83c1e0a42f69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('delivery_pools',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('zone_name', sa.String(length=200), nullable=False),
    sa.Column('dropoff_lat', sa.Float(), nullable=False),
    sa.Column('dropoff_lng', sa.Float(), nullable=False),
    sa.Column('total_base_fee', sa.Float(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'DISPATCHED', 'CLOSED', name='delivery_pool_status_enum'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_pools_id'), 'delivery_pools', ['id'], unique=False)
    op.create_index(op.f('ix_delivery_pools_status'), 'delivery_pools', ['status'], unique=False)

    with op.batch_alter_table("order_status_history") as batch:
        batch.add_column(sa.Column("sequence_num", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("prev_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("record_hash", sa.String(length=64), nullable=True))
        batch.create_unique_constraint(
            "uq_order_history_sequence", ["order_id", "sequence_num"]
        )

    bind = op.get_bind()
    histories = bind.execute(
        sa.text(
            "SELECT id, order_id, updated_by, previous_status, new_status, updated_at "
            "FROM order_status_history ORDER BY order_id, updated_at, id"
        )
    ).mappings()
    sequences: dict[int, int] = {}
    hashes: dict[int, str] = {}
    for history in histories:
        order_id = history["order_id"]
        sequence_num = sequences.get(order_id, 0) + 1
        previous_hash = hashes.get(order_id, "0" * 64)
        timestamp = history["updated_at"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        payload = {
            "order_id": order_id,
            "sequence_num": sequence_num,
            "old_status": history["previous_status"],
            "new_status": history["new_status"],
            "actor_id": history["updated_by"],
            "timestamp_iso": timestamp.astimezone(UTC).isoformat(),
            "prev_hash": previous_hash,
        }
        record_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        bind.execute(
            sa.text(
                "UPDATE order_status_history SET sequence_num = :sequence_num, "
                "prev_hash = :prev_hash, record_hash = :record_hash WHERE id = :id"
            ),
            {
                "sequence_num": sequence_num,
                "prev_hash": previous_hash,
                "record_hash": record_hash,
                "id": history["id"],
            },
        )
        sequences[order_id] = sequence_num
        hashes[order_id] = record_hash

    with op.batch_alter_table("order_status_history") as batch:
        batch.alter_column("sequence_num", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("prev_hash", existing_type=sa.String(length=64), nullable=False)
        batch.alter_column("record_hash", existing_type=sa.String(length=64), nullable=False)

    cargo_tier = sa.Enum("STANDARD", "COLD_CHAIN", "FRAGILE", name="cargo_tier_enum")
    cargo_tier.create(bind, checkfirst=True)
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("cargo_tier", cargo_tier, nullable=True))
        batch.add_column(sa.Column("max_temp_c", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column("is_compromised", sa.Boolean(), server_default="false", nullable=False)
        )
        batch.add_column(sa.Column("pool_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("split_fee_ghs", sa.Float(), nullable=True))
        batch.add_column(sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("sla_breached", sa.Boolean(), server_default="false", nullable=False)
        )
        batch.add_column(
            sa.Column("rebate_credited_ghs", sa.Float(), server_default="0", nullable=False)
        )
        batch.create_foreign_key(
            "fk_orders_pool_id_delivery_pools", "delivery_pools", ["pool_id"], ["id"]
        )
    bind.execute(
        sa.text("UPDATE orders SET cargo_tier = 'STANDARD' WHERE cargo_tier IS NULL")
    )
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("cargo_tier", existing_type=cargo_tier, nullable=False)

    with op.batch_alter_table("rider_locations") as batch:
        batch.add_column(sa.Column("temperature_c", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column("deviation_meters", sa.Float(), server_default="0", nullable=False)
        )
        batch.add_column(
            sa.Column("is_off_route", sa.Boolean(), server_default="false", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("rider_locations") as batch:
        batch.drop_column("is_off_route")
        batch.drop_column("deviation_meters")
        batch.drop_column("temperature_c")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_pool_id_delivery_pools", type_="foreignkey")
        batch.drop_column("rebate_credited_ghs")
        batch.drop_column("sla_breached")
        batch.drop_column("sla_deadline")
        batch.drop_column("split_fee_ghs")
        batch.drop_column("pool_id")
        batch.drop_column("is_compromised")
        batch.drop_column("max_temp_c")
        batch.drop_column("cargo_tier")
    with op.batch_alter_table("order_status_history") as batch:
        batch.drop_constraint("uq_order_history_sequence", type_="unique")
        batch.drop_column("record_hash")
        batch.drop_column("prev_hash")
        batch.drop_column("sequence_num")
    sa.Enum(
        "STANDARD", "COLD_CHAIN", "FRAGILE", name="cargo_tier_enum"
    ).drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f("ix_delivery_pools_status"), table_name="delivery_pools")
    op.drop_index(op.f("ix_delivery_pools_id"), table_name="delivery_pools")
    op.drop_table("delivery_pools")
