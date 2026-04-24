from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004_remove_staff_role'
down_revision = '003_add_is_onboarded_to_business'
branch_labels = None
depends_on = None


def upgrade():

    op.execute("UPDATE users SET role = 'admin' WHERE role = 'staff'")
    
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'admin'")
    op.execute("DROP TYPE userrole_old")


def downgrade():
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'admin'")
    op.execute("DROP TYPE userrole_old")
