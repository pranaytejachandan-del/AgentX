"""Initial Database Schema with pgvector support

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-03 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension (if PostgreSQL)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='procurement_manager', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Create vendors table
    op.create_table(
        'vendors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), server_default='5.0', nullable=False),
        sa.Column('gstin', sa.String(length=15), nullable=False),
        sa.Column('gst_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendors_id', 'vendors', ['id'], unique=False)
    op.create_index('ix_vendors_gstin', 'vendors', ['gstin'], unique=True)

    # 4. Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('specifications', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('base_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('min_allowable_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False),
        sa.Column('certifications', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('embedding', Vector(dim=1536).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('min_allowable_price <= base_price', name='check_min_price_le_base_price'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_id', 'products', ['id'], unique=False)
    op.create_index('ix_products_vendor_id', 'products', ['vendor_id'], unique=False)
    op.create_index('ix_products_sku', 'products', ['sku'], unique=True)
    op.create_index('ix_products_category', 'products', ['category'], unique=False)

    # 5. Create procurement_requests table
    op.create_table(
        'procurement_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('raw_prompt', sa.Text(), nullable=False),
        sa.Column('extracted_constraints', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('execution_status', sa.String(length=50), server_default='CREATED', nullable=False),
        sa.Column('max_budget', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_procurement_requests_id', 'procurement_requests', ['id'], unique=False)
    op.create_index('ix_procurement_requests_user_id', 'procurement_requests', ['user_id'], unique=False)
    op.create_index('ix_procurement_requests_execution_status', 'procurement_requests', ['execution_status'], unique=False)

    # 6. Create negotiation_traces table
    op.create_table(
        'negotiation_traces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('buyer_agent_message', sa.Text(), nullable=True),
        sa.Column('supplier_agent_message', sa.Text(), nullable=True),
        sa.Column('proposed_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('counter_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('negotiation_status', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('decision_summary', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['procurement_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_negotiation_traces_id', 'negotiation_traces', ['id'], unique=False)
    op.create_index('ix_negotiation_traces_request_id', 'negotiation_traces', ['request_id'], unique=False)

    # 7. Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('negotiated_unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('approval_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('payment_status', sa.String(length=50), server_default='NOT_STARTED', nullable=False),
        sa.Column('razorpay_order_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_payment_link_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_payment_link_url', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['request_id'], ['procurement_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_orders_id', 'orders', ['id'], unique=False)
    op.create_index('ix_orders_request_id', 'orders', ['request_id'], unique=False)
    op.create_index('ix_orders_payment_status', 'orders', ['payment_status'], unique=False)

    # 8. Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.String(length=50), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['procurement_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_events_id', 'audit_events', ['id'], unique=False)
    op.create_index('ix_audit_events_request_id', 'audit_events', ['request_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_events_request_id', table_name='audit_events')
    op.drop_index('ix_audit_events_id', table_name='audit_events')
    op.drop_table('audit_events')

    op.drop_index('ix_orders_payment_status', table_name='orders')
    op.drop_index('ix_orders_request_id', table_name='orders')
    op.drop_index('ix_orders_id', table_name='orders')
    op.drop_table('orders')

    op.drop_index('ix_negotiation_traces_request_id', table_name='negotiation_traces')
    op.drop_index('ix_negotiation_traces_id', table_name='negotiation_traces')
    op.drop_table('negotiation_traces')

    op.drop_index('ix_procurement_requests_execution_status', table_name='procurement_requests')
    op.drop_index('ix_procurement_requests_user_id', table_name='procurement_requests')
    op.drop_index('ix_procurement_requests_id', table_name='procurement_requests')
    op.drop_table('procurement_requests')

    op.drop_index('ix_products_category', table_name='products')
    op.drop_index('ix_products_sku', table_name='products')
    op.drop_index('ix_products_vendor_id', table_name='products')
    op.drop_index('ix_products_id', table_name='products')
    op.drop_table('products')

    op.drop_index('ix_vendors_gstin', table_name='vendors')
    op.drop_index('ix_vendors_id', table_name='vendors')
    op.drop_table('vendors')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
