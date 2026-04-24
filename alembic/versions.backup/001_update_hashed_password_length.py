"""Update hashed_password column length

Revision ID: 001
Revises: 
Create Date: 2026-02-14 17:56:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Alter hashed_password column from VARCHAR(255) to VARCHAR(60).
    
    Bcrypt hashes are always 60 characters in length.
    """
    # Alter column length
    op.alter_column(
        'users',
        'hashed_password',
        type_=sa.String(60),
        existing_type=sa.String(255),
        existing_nullable=False
    )


def downgrade() -> None:
    """
    Revert hashed_password column back to VARCHAR(255).
    """
    op.alter_column(
        'users',
        'hashed_password',
        type_=sa.String(255),
        existing_type=sa.String(60),
        existing_nullable=False
    )
