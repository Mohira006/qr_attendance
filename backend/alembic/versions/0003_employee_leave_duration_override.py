"""per-employee leave duration override

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable with no default and no backfill needed - NULL correctly means
    # "use the company default", which is exactly the desired behavior for every
    # existing employee row untouched by this migration.
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("annual_leave_duration_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_column("annual_leave_duration_days")
