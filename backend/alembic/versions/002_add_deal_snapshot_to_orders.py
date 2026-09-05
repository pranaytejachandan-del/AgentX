"""Add deal_snapshot to orders table

Revision ID: 002_add_deal_snapshot_to_orders
Revises: 001_initial_schema
Create Date: 2026-09-04 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_deal_snapshot_to_orders'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('deal_snapshot', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('orders', 'deal_snapshot')
