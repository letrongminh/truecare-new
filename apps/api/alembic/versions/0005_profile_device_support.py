"""profile device support

Revision ID: 0005_profile_device_support
Revises: 0004_correctness_closure
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_profile_device_support"
down_revision = "0004_correctness_closure"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


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
    op.execute(
        f"""
        insert into tenants (id, name)
        values ('{DEFAULT_TENANT_ID}'::uuid, 'TrueCare Pilot')
        on conflict (id) do nothing
        """
    )

    op.create_table(
        "invite_codes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="direct_ops"),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("referred_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="invite_codes_code_uidx"),
    )
    op.create_index("invite_codes_tenant", "invite_codes", ["tenant_id", "expires_at"])

    op.create_table(
        "device_registrations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("device_id", "user_id", name="device_registrations_device_user_uidx"),
    )
    op.create_index("device_registrations_device", "device_registrations", ["device_id"])
    op.create_index("device_registrations_user", "device_registrations", ["user_id"])

    op.create_table(
        "vehicles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="sedan"),
        sa.Column("license_plate", sa.String(length=40), nullable=True),
        sa.Column("make", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(length=80), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("vehicles_user_active", "vehicles", ["user_id"], postgresql_where=sa.text("deleted_at is null"))
    op.create_index("vehicles_tenant_user", "vehicles", ["tenant_id", "user_id"])

    op.create_table(
        "device_tokens",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("device_id", sa.String(length=200), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("device_tokens_user", "device_tokens", ["user_id", "registered_at"])
    op.create_index("device_tokens_device", "device_tokens", ["device_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("booking_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("golden_hour", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("referral_reward", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("wash_reminder", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("quiet_hours_start", sa.String(length=16), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=16), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "support_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("subject_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("owner_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("identifier", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("support_requests_tenant_status", "support_requests", ["tenant_id", "status", "created_at"])
    op.create_index("support_requests_subject", "support_requests", ["subject_user_id", "created_at"])

    op.create_table(
        "data_export_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("bundle_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("data_export_jobs_user", "data_export_jobs", ["user_id", "created_at"])

    op.create_table(
        "account_deletion_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="waiting"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancel_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("account_deletion_requests_user", "account_deletion_requests", ["user_id", "requested_at"])

    for table in (
        "invite_codes",
        "device_registrations",
        "vehicles",
        "device_tokens",
        "notification_preferences",
        "support_requests",
        "data_export_jobs",
        "account_deletion_requests",
    ):
        _tenant_policy(table)

    op.execute(
        f"""
        insert into invite_codes (id, tenant_id, code, source, max_uses, used_count)
        values ('00000000-0000-0000-0000-000000000004'::uuid, '{DEFAULT_TENANT_ID}'::uuid, 'PILOT-HA01', 'direct_ops', 1000000, 0)
        on conflict (code) do nothing
        """
    )


def downgrade() -> None:
    for table in (
        "account_deletion_requests",
        "data_export_jobs",
        "support_requests",
        "notification_preferences",
        "device_tokens",
        "vehicles",
        "device_registrations",
        "invite_codes",
    ):
        _drop_tenant_policy(table)

    op.drop_index("account_deletion_requests_user", table_name="account_deletion_requests")
    op.drop_table("account_deletion_requests")
    op.drop_index("data_export_jobs_user", table_name="data_export_jobs")
    op.drop_table("data_export_jobs")
    op.drop_index("support_requests_subject", table_name="support_requests")
    op.drop_index("support_requests_tenant_status", table_name="support_requests")
    op.drop_table("support_requests")
    op.drop_table("notification_preferences")
    op.drop_index("device_tokens_device", table_name="device_tokens")
    op.drop_index("device_tokens_user", table_name="device_tokens")
    op.drop_table("device_tokens")
    op.drop_index("vehicles_tenant_user", table_name="vehicles")
    op.drop_index("vehicles_user_active", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("device_registrations_user", table_name="device_registrations")
    op.drop_index("device_registrations_device", table_name="device_registrations")
    op.drop_table("device_registrations")
    op.drop_index("invite_codes_tenant", table_name="invite_codes")
    op.drop_table("invite_codes")
