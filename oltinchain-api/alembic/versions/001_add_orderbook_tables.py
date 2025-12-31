"""Add limit_orders and trades tables for orderbook.

Revision ID: 001_orderbook
Revises: 
Create Date: 2025-12-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '001_orderbook'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create limit_orders table
    op.create_table(
        'limit_orders',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('user_id', UUID, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('price', sa.Numeric(20, 2), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('filled_quantity', sa.Numeric(20, 8), server_default='0'),
        sa.Column('status', sa.String(20), server_default='open'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('filled_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes for limit_orders
    op.create_index(
        'ix_limit_orders_side_status_price',
        'limit_orders',
        ['side', 'status', 'price']
    )
    op.create_index(
        'ix_limit_orders_user_status',
        'limit_orders',
        ['user_id', 'status']
    )
    
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('buy_order_id', UUID, sa.ForeignKey('limit_orders.id'), nullable=False),
        sa.Column('sell_order_id', UUID, sa.ForeignKey('limit_orders.id'), nullable=False),
        sa.Column('price', sa.Numeric(20, 2), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('taker_side', sa.String(4), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create index for trades
    op.create_index(
        'ix_trades_created_at',
        'trades',
        ['created_at']
    )


def downgrade() -> None:
    op.drop_table('trades')
    op.drop_table('limit_orders')
