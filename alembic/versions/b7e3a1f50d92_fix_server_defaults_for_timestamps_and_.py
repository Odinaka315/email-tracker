"""fix_server_defaults_for_timestamps_and_index

Revision ID: b7e3a1f50d92
Revises: 4a9102598930
Create Date: 2026-09-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e3a1f50d92'
down_revision: Union[str, Sequence[str], None] = '4a9102598930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing server defaults for timestamp columns and fix index column defaults."""
    # The previous migration changed column types but didn't add DEFAULT clauses.
    # The original columns used Python-side defaults (datetime.utcnow) which never
    # created a database-level DEFAULT. We need them now because the models use server_default.

    # --- tracked_emails: add DEFAULT now() to created_at and updated_at ---
    op.alter_column('tracked_emails', 'created_at',
                    server_default=sa.text('now()'))
    op.alter_column('tracked_emails', 'updated_at',
                    server_default=sa.text('now()'))

    # --- open_events: add DEFAULT now() to opened_at ---
    op.alter_column('open_events', 'opened_at',
                    server_default=sa.text('now()'))

    # --- click_events: add DEFAULT now() to clicked_at ---
    op.alter_column('click_events', 'clicked_at',
                    server_default=sa.text('now()'))

    # --- Fix index column defaults to use sequences ---
    op.alter_column('tracked_emails', 'index',
                    server_default=sa.text("nextval('tracked_emails_index_seq')"))
    op.alter_column('open_events', 'index',
                    server_default=sa.text("nextval('open_events_index_seq')"))
    op.alter_column('click_events', 'index',
                    server_default=sa.text("nextval('click_events_index_seq')"))


def downgrade() -> None:
    """Remove server defaults."""
    op.alter_column('click_events', 'index', server_default=None)
    op.alter_column('open_events', 'index', server_default=None)
    op.alter_column('tracked_emails', 'index', server_default=None)
    op.alter_column('click_events', 'clicked_at', server_default=None)
    op.alter_column('open_events', 'opened_at', server_default=None)
    op.alter_column('tracked_emails', 'updated_at', server_default=None)
    op.alter_column('tracked_emails', 'created_at', server_default=None)
