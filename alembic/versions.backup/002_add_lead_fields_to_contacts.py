"""Add lead fields to contacts table

Revision ID: 002_add_lead_fields_to_contacts
Revises: 001_update_hashed_password_length
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_lead_fields_to_contacts'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add lead pipeline fields to contacts table."""
    # Add columns — all nullable so existing rows are unaffected
    op.add_column('contacts', sa.Column('status', sa.String(50), nullable=True, server_default='New'))
    op.add_column('contacts', sa.Column('service_interest', sa.String(255), nullable=True))
    op.add_column('contacts', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('contacts', sa.Column('tags', sa.String(500), nullable=True))
    op.add_column('contacts', sa.Column('source', sa.String(100), nullable=True, server_default='manual'))

    # Create index on status for fast filtering
    op.create_index('ix_contacts_status', 'contacts', ['status'])


def downgrade():
    """Remove lead pipeline fields from contacts table."""
    op.drop_index('ix_contacts_status', table_name='contacts')
    op.drop_column('contacts', 'source')
    op.drop_column('contacts', 'tags')
    op.drop_column('contacts', 'notes')
    op.drop_column('contacts', 'service_interest')
    op.drop_column('contacts', 'status')
