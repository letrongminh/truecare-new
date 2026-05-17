"""backend foundation

Revision ID: 0001_backend_foundation
Revises:
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_backend_foundation"
down_revision = None
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False, server_default="consumer"),
        sa.Column("auth_provider", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("referral_code", sa.String(length=32), nullable=True),
        sa.Column("referred_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("users_tenant_email_active", "users", ["tenant_id", "email"], unique=True, postgresql_where=sa.text("deleted_at is null and email is not null"))
    op.create_index("users_tenant_phone_active", "users", ["tenant_id", "phone"], unique=True, postgresql_where=sa.text("deleted_at is null and phone is not null"))
    op.create_unique_constraint("users_referral_code_uidx", "users", ["referral_code"])

    op.create_table(
        "tenant_memberships",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "profiles",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="vi"),
        sa.Column("no_show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_no_show_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("token_hash", sa.String(length=128), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("family_id", UUID, nullable=False),
        sa.Column("parent_hash", sa.String(length=128), nullable=True),
        sa.Column("superseded_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reused_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("refresh_tokens_user", "refresh_tokens", ["user_id"])
    op.create_index("refresh_tokens_family", "refresh_tokens", ["family_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", UUID, primary_key=True),
        sa.Column("subject", sa.String(length=200), primary_key=True),
        sa.Column("key", sa.String(length=200), primary_key=True),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "domain_events",
        sa.Column("event_id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", UUID, nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_letter_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("domain_events_available", "domain_events", ["available_at", "processed_at"])
    op.create_index("domain_events_aggregate", "domain_events", ["tenant_id", "aggregate_type", "aggregate_id", "aggregate_version"])

    op.create_table(
        "processed_domain_events",
        sa.Column("consumer_name", sa.String(length=120), primary_key=True),
        sa.Column("event_id", UUID, primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("result_hash", sa.String(length=128), nullable=True),
        sa.Column("error_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "worker_jobs",
        sa.Column("name", sa.String(length=120), primary_key=True),
        sa.Column("schedule_kind", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_lag_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("catch_up_from", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "worker_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_name", sa.String(length=120), sa.ForeignKey("worker_jobs.name"), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("high_watermark", sa.String(length=200), nullable=True),
        sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "rls_probe_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "value", name="rls_probe_records_tenant_value_uidx"),
    )
    op.execute("alter table rls_probe_records enable row level security")
    op.execute("alter table rls_probe_records force row level security")
    op.execute(
        """
        create policy rls_probe_tenant_isolation on rls_probe_records
        using (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        with check (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.drop_table("rls_probe_records")
    op.drop_table("worker_runs")
    op.drop_table("worker_jobs")
    op.drop_table("processed_domain_events")
    op.drop_index("domain_events_aggregate", table_name="domain_events")
    op.drop_index("domain_events_available", table_name="domain_events")
    op.drop_table("domain_events")
    op.drop_table("idempotency_keys")
    op.drop_index("refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("refresh_tokens_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("profiles")
    op.drop_table("tenant_memberships")
    op.drop_constraint("users_referral_code_uidx", "users", type_="unique")
    op.drop_index("users_tenant_phone_active", table_name="users")
    op.drop_index("users_tenant_email_active", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
