"""backend correctness closure

Revision ID: 0004_correctness_closure
Revises: 0003_phase2_phase3_domains
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_correctness_closure"
down_revision = "0003_phase2_phase3_domains"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _tenant_policy(table: str, *, nullable_tenant: bool = False) -> None:
    if nullable_tenant:
        predicate = "(tenant_id is null or tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)"
    else:
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
    op.add_column("evidence", sa.Column("retry_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("evidence", sa.Column("retry_exhausted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("evidence", sa.Column("ops_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("evidence", sa.Column("last_retry_error", sa.Text(), nullable=True))

    op.add_column("processed_domain_events", sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=True))
    op.create_index("processed_domain_events_tenant", "processed_domain_events", ["tenant_id", "processed_at"])
    op.add_column("worker_jobs", sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=True))
    op.create_index("worker_jobs_tenant", "worker_jobs", ["tenant_id", "enabled"])
    op.add_column("worker_runs", sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=True))
    op.create_index("worker_runs_tenant", "worker_runs", ["tenant_id", "started_at"])

    for table in (
        "users",
        "tenant_memberships",
        "profiles",
        "idempotency_keys",
        "domain_events",
    ):
        _tenant_policy(table)
    for table in ("processed_domain_events", "worker_jobs", "worker_runs"):
        _tenant_policy(table, nullable_tenant=True)

    op.create_table(
        "audit_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_kind", sa.String(length=80), nullable=False),
        sa.Column("target_id", UUID, nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=True),
    )
    op.create_index("audit_log_tenant_recorded", "audit_log", ["tenant_id", "recorded_at"])
    op.create_index("audit_log_actor", "audit_log", ["actor_user_id", "recorded_at"])
    op.create_index("audit_log_target", "audit_log", ["target_kind", "target_id"])
    _tenant_policy("audit_log")


def downgrade() -> None:
    _drop_tenant_policy("audit_log")
    op.drop_index("audit_log_target", table_name="audit_log")
    op.drop_index("audit_log_actor", table_name="audit_log")
    op.drop_index("audit_log_tenant_recorded", table_name="audit_log")
    op.drop_table("audit_log")

    for table in ("worker_runs", "worker_jobs", "processed_domain_events", "domain_events", "idempotency_keys", "profiles", "tenant_memberships", "users"):
        _drop_tenant_policy(table)

    op.drop_index("worker_runs_tenant", table_name="worker_runs")
    op.drop_column("worker_runs", "tenant_id")
    op.drop_index("worker_jobs_tenant", table_name="worker_jobs")
    op.drop_column("worker_jobs", "tenant_id")
    op.drop_index("processed_domain_events_tenant", table_name="processed_domain_events")
    op.drop_column("processed_domain_events", "tenant_id")

    op.drop_column("evidence", "last_retry_error")
    op.drop_column("evidence", "ops_review_required")
    op.drop_column("evidence", "retry_exhausted_at")
    op.drop_column("evidence", "retry_attempts")
