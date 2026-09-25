"""remove explanation letter threshold setting

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("company_settings", schema=None) as batch_op:
        batch_op.drop_column("explanation_letter_threshold_minutes")


def downgrade() -> None:
    with op.batch_alter_table("company_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("explanation_letter_threshold_minutes", sa.Integer(), nullable=False, server_default="15")
        )
