"""add_is_onboarded_to_business

Revision ID: 003
Revises: 002_add_lead_fields_to_contacts
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002_add_lead_fields_to_contacts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'businesses',
        sa.Column('is_onboarded', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column('businesses', 'is_onboarded')
