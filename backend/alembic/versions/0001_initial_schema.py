"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(*values: str, name: str) -> sa.Enum:
    # Stored as VARCHAR(32); see app/models/base.py:str_enum for the rationale.
    return sa.Enum(*values, name=name, native_enum=False, length=32)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("active", "inactive", name="department_status"), nullable=False),
        sa.Column("work_start_time", sa.Time(), nullable=True),
        sa.Column("work_end_time", sa.Time(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_departments_status", "departments", ["status"], unique=False)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("face_recognition_id", sa.String(length=128), nullable=True),
        sa.Column("profile_photo", sa.String(length=512), nullable=True),
        sa.Column("work_start_time", sa.Time(), nullable=True),
        sa.Column("work_end_time", sa.Time(), nullable=True),
        sa.Column("status", _enum("active", "inactive", name="employment_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"], unique=False)
    op.create_index("ix_employees_employee_id", "employees", ["employee_id"], unique=True)
    op.create_index("ix_employees_face_recognition_id", "employees", ["face_recognition_id"], unique=True)
    op.create_index("ix_employees_status", "employees", ["status"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", _enum("hr", "employee", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("work_start_time", sa.Time(), nullable=False),
        sa.Column("work_end_time", sa.Time(), nullable=False),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False),
        sa.Column("explanation_letter_threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("duplicate_event_window_seconds", sa.Integer(), nullable=False),
        sa.Column("working_days", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _enum("on_time", "late", name="attendance_status"), nullable=False),
        sa.Column("checkout_status", _enum("pending", "completed", "missing", name="checkout_status"), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("total_working_minutes", sa.Integer(), nullable=True),
        sa.Column("expected_check_in", sa.Time(), nullable=False),
        sa.Column("expected_check_out", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
    )
    op.create_index("ix_attendance_checkout_status", "attendance", ["checkout_status"], unique=False)
    op.create_index("ix_attendance_date", "attendance", ["date"], unique=False)
    op.create_index("ix_attendance_date_status", "attendance", ["date", "status"], unique=False)
    op.create_index("ix_attendance_employee_id", "attendance", ["employee_id"], unique=False)
    op.create_index("ix_attendance_status", "attendance", ["status"], unique=False)

    op.create_table(
        "face_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("identifier", sa.String(length=128), nullable=True),
        sa.Column(
            "requested_type",
            _enum("auto", "check_in", "check_out", name="face_event_request_type"),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            _enum("check_in", "check_out", "duplicate", "unknown_employee", "rejected", name="face_event_outcome"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("attendance_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attendance_id"], ["attendance.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_face_events_device_id", "face_events", ["device_id"], unique=False)
    op.create_index("ix_face_events_employee_timestamp", "face_events", ["employee_id", "timestamp"], unique=False)
    op.create_index("ix_face_events_outcome", "face_events", ["outcome"], unique=False)
    op.create_index("ix_face_events_timestamp", "face_events", ["timestamp"], unique=False)

    op.create_table(
        "explanation_letters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("attendance_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("pdf_path", sa.String(length=512), nullable=True),
        sa.Column("employee_explanation", sa.Text(), nullable=True),
        sa.Column("hr_comment", sa.Text(), nullable=True),
        sa.Column("status", _enum("pending", "submitted", "reviewed", name="letter_status"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attendance_id"], ["attendance.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attendance_id"),
    )
    op.create_index("ix_explanation_letters_date", "explanation_letters", ["date"], unique=False)
    op.create_index("ix_explanation_letters_employee_id", "explanation_letters", ["employee_id"], unique=False)
    op.create_index("ix_explanation_letters_status", "explanation_letters", ["status"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            _enum("check_in", "check_out", "late", "explanation_letter", "system", name="notification_type"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("attendance_id", sa.Integer(), nullable=True),
        sa.Column("explanation_letter_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attendance_id"], ["attendance.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["explanation_letter_id"], ["explanation_letters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_notifications_user_read_created", "notifications", ["user_id", "is_read", "created_at"], unique=False
    )

    op.create_table(
        "leaves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("leave_type", _enum("vacation", "sick", "unpaid", "other", name="leave_type"), nullable=False),
        sa.Column("status", _enum("pending", "approved", "rejected", name="leave_status"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_leaves_date_order"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaves_employee_dates", "leaves", ["employee_id", "start_date", "end_date"], unique=False)
    op.create_index("ix_leaves_employee_id", "leaves", ["employee_id"], unique=False)
    op.create_index("ix_leaves_status", "leaves", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("leaves")
    op.drop_table("notifications")
    op.drop_table("explanation_letters")
    op.drop_table("face_events")
    op.drop_table("attendance")
    op.drop_table("company_settings")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("employees")
    op.drop_table("departments")
