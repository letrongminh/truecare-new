"""phase 2 and 3 domain tables

Revision ID: 0003_phase2_phase3_domains
Revises: 0002_core_marketplace
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_phase2_phase3_domains"
down_revision = "0002_core_marketplace"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _tenant_policy(table: str) -> None:
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(
        f"""
        create policy {table}_tenant_isolation on {table}
        using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        with check (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.add_column("merchant_services", sa.Column("ops_reviewed_by", UUID, nullable=True))
    op.add_column("merchant_services", sa.Column("ops_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("merchant_services", sa.Column("ops_rejection_reason", sa.Text(), nullable=True))
    op.add_column("merchant_services", sa.Column("resubmit_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "price_change_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_service_id", UUID, sa.ForeignKey("merchant_services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_price", sa.BigInteger(), nullable=False),
        sa.Column("new_price", sa.BigInteger(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("price_change_log_service", "price_change_log", ["merchant_service_id", "changed_at"])
    _tenant_policy("price_change_log")

    op.create_table(
        "evidence",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("quality", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("gps_accuracy_meters", sa.Float(), nullable=True),
        sa.Column("perceptual_hash", sa.String(length=128), nullable=True),
        sa.Column("watermarked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exif_stripped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type in ('before', 'after')", name="evidence_type_valid"),
        sa.CheckConstraint("status in ('pending_upload', 'uploaded', 'processed', 'weak_evidence', 'expired')", name="evidence_status_valid"),
    )
    op.create_index("evidence_booking", "evidence", ["booking_id", "type"])
    _tenant_policy("evidence")

    op.create_table(
        "payments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("merchant_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merchant_denied_reason", sa.String(length=80), nullable=True),
        sa.Column("commission_amount", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("commission_status", sa.String(length=40), nullable=False, server_default="not_applicable"),
        sa.Column("invoice_id", sa.Text(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_reason", sa.Text(), nullable=True),
        sa.Column("dispute_status", sa.String(length=40), nullable=False, server_default="none"),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("ops_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("method in ('qr_transfer', 'cash', 'vetc_wallet')", name="payments_method_valid"),
        sa.CheckConstraint("status in ('initiated_qr', 'user_claimed', 'cash_offered', 'verified', 'merchant_denied', 'failed', 'disputed', 'cancelled')", name="payments_status_valid"),
        sa.CheckConstraint("commission_status in ('not_applicable', 'accrued', 'exported', 'invoiced', 'settled', 'waived', 'disputed')", name="payments_commission_status_valid"),
    )
    op.create_index("payments_booking", "payments", ["booking_id"])
    op.create_unique_constraint("payments_tenant_booking_idempotency_uidx", "payments", ["tenant_id", "booking_id", "idempotency_key"])
    _tenant_policy("payments")

    op.create_table(
        "ratings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("rating", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("tip", sa.BigInteger(), nullable=True),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rating in ('positive', 'negative')", name="ratings_value_valid"),
    )
    op.create_unique_constraint("ratings_booking_unique", "ratings", ["booking_id"])
    op.create_index("ratings_merchant", "ratings", ["merchant_id"])
    _tenant_policy("ratings")

    op.create_table(
        "promo_codes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.BigInteger(), nullable=False),
        sa.Column("max_discount_amount", sa.BigInteger(), nullable=True),
        sa.Column("min_order_amount", sa.BigInteger(), nullable=True),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), nullable=True),
        sa.Column("service_template_id", UUID, sa.ForeignKey("service_templates.id"), nullable=True),
        sa.Column("usage_limit_total", sa.Integer(), nullable=False),
        sa.Column("usage_limit_per_user", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_funded", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_ops", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("discount_type in ('percent', 'fixed')", name="promo_codes_discount_type_valid"),
    )
    op.create_unique_constraint("promo_codes_tenant_code_uidx", "promo_codes", ["tenant_id", "code"])
    _tenant_policy("promo_codes")

    op.create_table(
        "promo_code_usages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("promo_code_id", UUID, sa.ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("promo_code_usages_promo", "promo_code_usages", ["promo_code_id"])
    op.create_unique_constraint("promo_code_usages_user_promo", "promo_code_usages", ["user_id", "promo_code_id"])
    _tenant_policy("promo_code_usages")

    op.create_table(
        "reward_stamps",
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('pending', 'finalized', 'frozen')", name="reward_stamps_status_valid"),
    )
    op.create_index("reward_stamps_user", "reward_stamps", ["user_id", "status"])
    _tenant_policy("reward_stamps")

    op.create_table(
        "reward_vouchers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("service_template_id", UUID, sa.ForeignKey("service_templates.id"), nullable=True),
        sa.Column("stamp_threshold_reached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_booking_id", UUID, sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_booking_id", UUID, sa.ForeignKey("bookings.id"), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="issued"),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('issued', 'reserved', 'redeemed', 'released', 'expired', 'frozen', 'restored', 'invalidated')", name="reward_vouchers_status_valid"),
    )
    op.create_index("reward_vouchers_user_status", "reward_vouchers", ["user_id", "status"])
    _tenant_policy("reward_vouchers")

    op.create_table(
        "referrals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("referrer_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("referee_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("reward_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reward_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("referrals_referrer", "referrals", ["referrer_id"])
    _tenant_policy("referrals")

    op.create_table(
        "complaints",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="created"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("refund_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("voucher_action", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("complaints_user", "complaints", ["user_id", "status"])
    op.create_index("complaints_merchant", "complaints", ["merchant_id", "status"])
    _tenant_policy("complaints")


def downgrade() -> None:
    op.drop_table("complaints")
    op.drop_table("referrals")
    op.drop_index("reward_vouchers_user_status", table_name="reward_vouchers")
    op.drop_table("reward_vouchers")
    op.drop_index("reward_stamps_user", table_name="reward_stamps")
    op.drop_table("reward_stamps")
    op.drop_constraint("promo_code_usages_user_promo", "promo_code_usages", type_="unique")
    op.drop_index("promo_code_usages_promo", table_name="promo_code_usages")
    op.drop_table("promo_code_usages")
    op.drop_constraint("promo_codes_tenant_code_uidx", "promo_codes", type_="unique")
    op.drop_table("promo_codes")
    op.drop_index("ratings_merchant", table_name="ratings")
    op.drop_constraint("ratings_booking_unique", "ratings", type_="unique")
    op.drop_table("ratings")
    op.drop_constraint("payments_tenant_booking_idempotency_uidx", "payments", type_="unique")
    op.drop_index("payments_booking", table_name="payments")
    op.drop_table("payments")
    op.drop_index("evidence_booking", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("price_change_log_service", table_name="price_change_log")
    op.drop_table("price_change_log")
    op.drop_column("merchant_services", "resubmit_count")
    op.drop_column("merchant_services", "ops_rejection_reason")
    op.drop_column("merchant_services", "ops_reviewed_at")
    op.drop_column("merchant_services", "ops_reviewed_by")
