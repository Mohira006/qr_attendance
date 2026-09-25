"""add explanation letter attachment path

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("explanation_letters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attachment_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("explanation_letters", schema=None) as batch_op:
        batch_op.drop_column("attachment_path")
