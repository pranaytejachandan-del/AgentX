"""Add payment fields to orders table

Revision ID: 003_add_payment_fields_to_orders
Revises: 002_add_deal_snapshot_to_orders
Create Date: 2026-09-04 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_payment_fields_to_orders'
down_revision: Union[str, None] = '002_add_deal_snapshot_to_orders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('razorpay_payment_id', sa.String(length=255), nullable=True))
    op.add_column('orders', sa.Column('payment_link_created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('payment_failure_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'payment_failure_reason')
    op.drop_column('orders', 'payment_link_created_at')
    op.drop_column('orders', 'razorpay_payment_id')
