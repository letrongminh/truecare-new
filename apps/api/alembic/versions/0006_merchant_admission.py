"""merchant admission go-live foundation

Revision ID: 0006_merchant_admission
Revises: 0005_profile_device_support
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_merchant_admission"
down_revision = "0005_profile_device_support"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _tenant_policy(table: str) -> None:
    predicate = "(tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)"
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
    op.execute(
        f"""
        create policy {table}_tenant_isolation on {table}
        using {predicate}
        with check {predicate}
        """
    )


def _drop_tenant_policy(table: str) -> None:
    op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def upgrade() -> None:
    op.add_column("merchants", sa.Column("application_status", sa.String(length=40), nullable=False, server_default="pending_review"))
    op.add_column("merchants", sa.Column("photo_status", sa.String(length=40), nullable=False, server_default="missing"))
    op.add_column("merchants", sa.Column("payment_recipient_status", sa.String(length=40), nullable=False, server_default="missing"))
    op.add_column("merchants", sa.Column("ekyc_status", sa.String(length=40), nullable=False, server_default="not_submitted"))
    op.add_column("merchants", sa.Column("go_live_blockers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("merchants", sa.Column("ops_rejection_reason", sa.Text(), nullable=True))
    op.add_column("merchants", sa.Column("ops_reviewed_by", UUID, sa.ForeignKey("users.id"), nullable=True))
    op.add_column("merchants", sa.Column("ops_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("merchants", sa.Column("photo_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("merchants", sa.Column("payment_recipient_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "merchant_ekyc_submissions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="submitted"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind in ('cmnd', 'selfie', 'bank')", name="merchant_ekyc_submissions_kind_valid"),
        sa.CheckConstraint("status in ('submitted', 'accepted', 'rejected')", name="merchant_ekyc_submissions_status_valid"),
        sa.UniqueConstraint("merchant_id", "kind", name="merchant_ekyc_submissions_merchant_kind_uidx"),
    )
    op.create_index("merchant_ekyc_submissions_merchant", "merchant_ekyc_submissions", ["merchant_id", "kind"])

    op.create_table(
        "merchant_payment_setups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("account_number", sa.String(length=80), nullable=False),
        sa.Column("account_holder_name", sa.String(length=200), nullable=False),
        sa.Column("qr_object_key", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending_review"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("status in ('pending_review', 'verified', 'rejected')", name="merchant_payment_setups_status_valid"),
        sa.UniqueConstraint("merchant_id", name="merchant_payment_setups_merchant_uidx"),
    )
    op.create_index("merchant_payment_setups_status", "merchant_payment_setups", ["tenant_id", "status"])

    _tenant_policy("merchant_ekyc_submissions")
    _tenant_policy("merchant_payment_setups")


def downgrade() -> None:
    _drop_tenant_policy("merchant_payment_setups")
    _drop_tenant_policy("merchant_ekyc_submissions")
    op.drop_index("merchant_payment_setups_status", table_name="merchant_payment_setups")
    op.drop_table("merchant_payment_setups")
    op.drop_index("merchant_ekyc_submissions_merchant", table_name="merchant_ekyc_submissions")
    op.drop_table("merchant_ekyc_submissions")
    op.drop_column("merchants", "payment_recipient_verified_at")
    op.drop_column("merchants", "photo_confirmed_at")
    op.drop_column("merchants", "ops_reviewed_at")
    op.drop_column("merchants", "ops_reviewed_by")
    op.drop_column("merchants", "ops_rejection_reason")
    op.drop_column("merchants", "go_live_blockers")
    op.drop_column("merchants", "ekyc_status")
    op.drop_column("merchants", "payment_recipient_status")
    op.drop_column("merchants", "photo_status")
    op.drop_column("merchants", "application_status")
