"""leave management module

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.types import UTCDateTime

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=32)


def upgrade() -> None:
    op.create_table(
        "leave_cycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("cycle_start_date", sa.Date(), nullable=False),
        sa.Column("cycle_end_date", sa.Date(), nullable=False),
        sa.Column("eligibility_date", sa.Date(), nullable=False),
        sa.Column("status", _enum("available", "requested", "consumed", name="leave_cycle_status"), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "cycle_number", name="uq_leave_cycles_employee_number"),
    )
    op.create_index("ix_leave_cycles_employee_id", "leave_cycles", ["employee_id"], unique=False)
    op.create_index("ix_leave_cycles_employee_status", "leave_cycles", ["employee_id", "status"], unique=False)
    op.create_index("ix_leave_cycles_status", "leave_cycles", ["status"], unique=False)

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("leave_cycle_id", sa.Integer(), nullable=False),
        sa.Column("requested_start_date", sa.Date(), nullable=False),
        sa.Column("requested_end_date", sa.Date(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("request_type", _enum("normal", "force_majeure", name="leave_request_type"), nullable=False),
        sa.Column(
            "status",
            _enum("pending", "approved", "rejected", "cancelled", "completed", name="leave_request_status"),
            nullable=False,
        ),
        sa.Column("employee_comment", sa.Text(), nullable=True),
        sa.Column("hr_comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("approved_at", UTCDateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", UTCDateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", UTCDateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_hr_override", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("leave_id", sa.Integer(), nullable=True),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint("requested_end_date >= requested_start_date", name="ck_leave_requests_date_order"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_cycle_id"], ["leave_cycles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["leave_id"], ["leaves.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leave_requests_employee_id", "leave_requests", ["employee_id"], unique=False)
    op.create_index("ix_leave_requests_employee_status", "leave_requests", ["employee_id", "status"], unique=False)
    op.create_index("ix_leave_requests_leave_cycle_id", "leave_requests", ["leave_cycle_id"], unique=False)
    op.create_index("ix_leave_requests_status", "leave_requests", ["status"], unique=False)

    # New settings columns get a server_default so the existing single settings row
    # (and any other pre-existing rows) are backfilled automatically by the ALTER
    # itself - unlike employment_start_date below, every one of these has one
    # sensible default value that applies to every row, new or old.
    with op.batch_alter_table("company_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("annual_leave_duration_days", sa.Integer(), nullable=False, server_default="24"))
        batch_op.add_column(sa.Column("leave_normal_notice_days", sa.Integer(), nullable=False, server_default="14"))
        batch_op.add_column(sa.Column("leave_force_majeure_notice_days", sa.Integer(), nullable=False, server_default="3"))
        batch_op.add_column(sa.Column("leave_eligibility_after_months", sa.Integer(), nullable=False, server_default="6"))
        batch_op.add_column(sa.Column("leave_next_cycle_after_months", sa.Integer(), nullable=False, server_default="11"))
        batch_op.add_column(sa.Column("leave_reminder_30_days_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("leave_reminder_14_days_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("leave_reminder_7_days_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("preferred_language", _enum("uz", "ru", "en", name="language"), nullable=False, server_default="uz")
        )

    # employment_start_date has no single sensible default across all rows - added
    # nullable, backfilled per-row, then locked to NOT NULL, so this is safe to run
    # against a database that already has employees in it.
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("employment_start_date", sa.Date(), nullable=True))

    employees_table = sa.table(
        "employees", sa.column("id"), sa.column("employment_start_date"), sa.column("created_at")
    )
    op.execute(
        employees_table.update().values(employment_start_date=sa.func.date(employees_table.c.created_at))
    )

    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.alter_column("employment_start_date", existing_type=sa.Date(), nullable=False)
        batch_op.create_index("ix_employees_employment_start_date", ["employment_start_date"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index("ix_employees_employment_start_date")
        batch_op.drop_column("employment_start_date")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("preferred_language")

    with op.batch_alter_table("company_settings", schema=None) as batch_op:
        batch_op.drop_column("leave_reminder_7_days_enabled")
        batch_op.drop_column("leave_reminder_14_days_enabled")
        batch_op.drop_column("leave_reminder_30_days_enabled")
        batch_op.drop_column("leave_next_cycle_after_months")
        batch_op.drop_column("leave_eligibility_after_months")
        batch_op.drop_column("leave_force_majeure_notice_days")
        batch_op.drop_column("leave_normal_notice_days")
        batch_op.drop_column("annual_leave_duration_days")

    op.drop_index("ix_leave_requests_status", table_name="leave_requests")
    op.drop_index("ix_leave_requests_leave_cycle_id", table_name="leave_requests")
    op.drop_index("ix_leave_requests_employee_status", table_name="leave_requests")
    op.drop_index("ix_leave_requests_employee_id", table_name="leave_requests")
    op.drop_table("leave_requests")

    op.drop_index("ix_leave_cycles_status", table_name="leave_cycles")
    op.drop_index("ix_leave_cycles_employee_status", table_name="leave_cycles")
    op.drop_index("ix_leave_cycles_employee_id", table_name="leave_cycles")
    op.drop_table("leave_cycles")
