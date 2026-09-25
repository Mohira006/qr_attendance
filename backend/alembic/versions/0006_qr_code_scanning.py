"""replace face id with qr code scanning

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index("ix_employees_face_recognition_id")
        batch_op.drop_column("face_recognition_id")
        batch_op.add_column(sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True))

    # The raw event-log table is no longer needed: its only real consumer was
    # duplicate-scan detection (now a single column on employees, see above) and
    # the Face ID simulator (removed). Attendance records themselves already
    # capture what actually happened for every successful scan.
    op.drop_table("face_events")


def downgrade() -> None:
    op.create_table(
        "face_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("attendance_id", sa.Integer(), sa.ForeignKey("attendance.id"), nullable=True),
        sa.Column("identifier", sa.String(length=128), nullable=False),
        sa.Column("requested_type", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_column("last_scan_at")
        batch_op.add_column(sa.Column("face_recognition_id", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_employees_face_recognition_id", ["face_recognition_id"], unique=True)
