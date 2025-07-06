"""Empty script template for Alembic migrations."""
revision = '${up_revision}'
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

from alembic import op
import sqlalchemy as sa

def upgrade():
    pass

def downgrade():
    pass