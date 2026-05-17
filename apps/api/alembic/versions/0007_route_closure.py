"""route closure golden hour support

Revision ID: 0007_route_closure
Revises: 0006_merchant_admission
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_route_closure"
down_revision = "0006_merchant_admission"
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
    op.create_table(
        "merchant_golden_hours",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(length=16), nullable=False),
        sa.Column("end_time", sa.String(length=16), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("day_of_week between 0 and 6", name="merchant_golden_hours_day_valid"),
        sa.CheckConstraint("discount_percent between 0 and 30", name="merchant_golden_hours_discount_valid"),
        sa.CheckConstraint("start_time ~ '^[0-2][0-9]:[0-5][0-9]$'", name="merchant_golden_hours_start_time_valid"),
        sa.CheckConstraint("end_time ~ '^[0-2][0-9]:[0-5][0-9]$'", name="merchant_golden_hours_end_time_valid"),
        sa.UniqueConstraint("merchant_id", "day_of_week", name="merchant_golden_hours_merchant_day_uidx"),
    )
    op.create_index("merchant_golden_hours_merchant", "merchant_golden_hours", ["merchant_id"])
    _tenant_policy("merchant_golden_hours")


def downgrade() -> None:
    _drop_tenant_policy("merchant_golden_hours")
    op.drop_index("merchant_golden_hours_merchant", table_name="merchant_golden_hours")
    op.drop_table("merchant_golden_hours")
