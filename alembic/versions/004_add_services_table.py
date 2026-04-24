"""Add services table

Revision ID: 004_add_services_table
Revises: 73cd2fbe5751
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_services_table'
down_revision = '73cd2fbe5751'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create services table
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_services_business_id'), 'services', ['business_id'], unique=False)
    op.create_index(op.f('ix_services_created_at'), 'services', ['created_at'], unique=False)
    op.create_index(op.f('ix_services_is_active'), 'services', ['is_active'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_services_is_active'), table_name='services')
    op.drop_index(op.f('ix_services_created_at'), table_name='services')
    op.drop_index(op.f('ix_services_business_id'), table_name='services')
    
    # Drop table
    op.drop_table('services')
