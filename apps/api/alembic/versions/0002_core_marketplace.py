"""core marketplace foundation

Revision ID: 0002_core_marketplace
Revises: 0001_backend_foundation
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_core_marketplace"
down_revision = "0001_backend_foundation"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _tenant_policy(table: str, policy: str | None = None) -> None:
    policy_name = policy or f"{table}_tenant_isolation"
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(
        f"""
        create policy {policy_name} on {table}
        using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        with check (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "service_templates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("floor_price", sa.BigInteger(), nullable=False),
        sa.Column("ceiling_price", sa.BigInteger(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("duration_max", sa.Integer(), nullable=False),
        sa.Column("evidence_required", sa.Text(), nullable=False),
        sa.Column("sop_checklist_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    service_templates = sa.table(
        "service_templates",
        sa.column("id", UUID),
        sa.column("name", sa.Text()),
        sa.column("floor_price", sa.BigInteger()),
        sa.column("ceiling_price", sa.BigInteger()),
        sa.column("duration_min", sa.Integer()),
        sa.column("duration_max", sa.Integer()),
        sa.column("evidence_required", sa.Text()),
    )
    op.bulk_insert(
        service_templates,
        [
            {
                "id": "00000000-0000-0000-0001-000000000001",
                "name": "Rua ngoai co ban",
                "floor_price": 70_000,
                "ceiling_price": 200_000,
                "duration_min": 20,
                "duration_max": 30,
                "evidence_required": "before_after_exterior",
            },
            {
                "id": "00000000-0000-0000-0001-000000000002",
                "name": "Rua trong ngoai",
                "floor_price": 120_000,
                "ceiling_price": 300_000,
                "duration_min": 35,
                "duration_max": 45,
                "evidence_required": "before_after_interior",
            },
            {
                "id": "00000000-0000-0000-0001-000000000003",
                "name": "Hut bui noi that",
                "floor_price": 30_000,
                "ceiling_price": 100_000,
                "duration_min": 15,
                "duration_max": 20,
                "evidence_required": "interior_after",
            },
            {
                "id": "00000000-0000-0000-0001-000000000004",
                "name": "Ve sinh kinh guong",
                "floor_price": 15_000,
                "ceiling_price": 60_000,
                "duration_min": 10,
                "duration_max": 15,
                "evidence_required": "after_only",
            },
            {
                "id": "00000000-0000-0000-0001-000000000005",
                "name": "Rua gam co ban",
                "floor_price": 80_000,
                "ceiling_price": 200_000,
                "duration_min": 20,
                "duration_max": 30,
                "evidence_required": "before_after_lower_body",
            },
            {
                "id": "00000000-0000-0000-0001-000000000006",
                "name": "Combo Gio Vang",
                "floor_price": 70_000,
                "ceiling_price": 300_000,
                "duration_min": 30,
                "duration_max": 50,
                "evidence_required": "before_after_exterior",
            },
        ],
    )

    op.create_table(
        "merchants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("bay_count", sa.Integer(), nullable=False),
        sa.Column("operating_hours_start", sa.String(length=16), nullable=False),
        sa.Column("operating_hours_end", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("pipeline_status", sa.String(length=40), nullable=False, server_default="longlist"),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rating_average", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commission_rate", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("max_bookings_per_day", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("storefront_photo_url", sa.Text(), nullable=True),
        sa.Column("bay_photo_url", sa.Text(), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('pending_info', 'pending_review', 'rejected', 'approved', 'live', 'suspended')", name="merchants_status_valid"),
        sa.CheckConstraint(
            "pipeline_status in ('longlist', 'visited', 'qualified', 'pending_setup', 'test_booking_passed', 'live_limited', 'live_full', 'watchlist', 'suspended')",
            name="merchants_pipeline_status_valid",
        ),
    )
    op.create_index("merchants_tenant_status", "merchants", ["tenant_id", "status"])
    _tenant_policy("merchants")

    op.create_table(
        "merchant_services",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", UUID, sa.ForeignKey("service_templates.id"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("duration_max", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'disabled', 'pending_review', 'rejected')", name="merchant_services_status_valid"),
    )
    op.create_index("merchant_services_merchant", "merchant_services", ["merchant_id"])
    _tenant_policy("merchant_services")

    op.create_table(
        "slot_capacity",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bay_number", sa.Integer(), nullable=False),
        sa.Column("time_slot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("held_by_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('available', 'held', 'in_progress', 'closed')", name="slot_capacity_status_valid"),
    )
    op.create_index("slot_capacity_merchant_status", "slot_capacity", ["merchant_id", "status"])
    op.create_index("slot_capacity_held_by_user", "slot_capacity", ["held_by_user_id"], postgresql_where=sa.text("status = 'held'"))
    op.create_unique_constraint("slot_capacity_merchant_bay_time", "slot_capacity", ["merchant_id", "bay_number", "time_slot"])
    _tenant_policy("slot_capacity")

    op.create_table(
        "bookings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("merchant_service_id", UUID, sa.ForeignKey("merchant_services.id"), nullable=False),
        sa.Column("slot_capacity_id", UUID, sa.ForeignKey("slot_capacity.id"), nullable=False),
        sa.Column("bay_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("deposit_amount", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("check_in_token", sa.String(length=64), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("service_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_method", sa.String(length=40), nullable=True),
        sa.Column("payment_status", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('held', 'checked_in', 'in_progress', 'awaiting_payment', 'completed', 'rated', 'expired', 'no_show', 'cancelled', 'cancelled_by_ops', 'payment_disputed')",
            name="bookings_status_valid",
        ),
    )
    op.create_index("bookings_user_status", "bookings", ["user_id", "status", "expires_at"])
    op.create_index("bookings_merchant_status", "bookings", ["merchant_id", "status", "held_at"])
    op.create_unique_constraint("bookings_user_idempotency_uidx", "bookings", ["user_id", "idempotency_key"])
    _tenant_policy("bookings")


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_constraint("slot_capacity_merchant_bay_time", "slot_capacity", type_="unique")
    op.drop_index("slot_capacity_held_by_user", table_name="slot_capacity")
    op.drop_index("slot_capacity_merchant_status", table_name="slot_capacity")
    op.drop_table("slot_capacity")
    op.drop_index("merchant_services_merchant", table_name="merchant_services")
    op.drop_table("merchant_services")
    op.drop_index("merchants_tenant_status", table_name="merchants")
    op.drop_table("merchants")
    op.drop_table("service_templates")
