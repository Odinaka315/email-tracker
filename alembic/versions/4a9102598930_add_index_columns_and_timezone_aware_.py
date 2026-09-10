"""add_index_columns_and_timezone_aware_timestamps

Revision ID: 4a9102598930
Revises: fcc8fca860ca
Create Date: 2026-09-10 11:46:46.031132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4a9102598930'
down_revision: Union[str, Sequence[str], None] = 'fcc8fca860ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- click_events ---
    op.execute("CREATE SEQUENCE IF NOT EXISTS click_events_index_seq")
    op.add_column('click_events', sa.Column('index', sa.Integer(), server_default=sa.text("nextval('click_events_index_seq')"), nullable=False))
    op.execute("ALTER SEQUENCE click_events_index_seq OWNED BY click_events.index")
    op.alter_column('click_events', 'clicked_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_unique_constraint('uq_click_events_index', 'click_events', ['index'])

    # --- open_events ---
    op.execute("CREATE SEQUENCE IF NOT EXISTS open_events_index_seq")
    op.add_column('open_events', sa.Column('index', sa.Integer(), server_default=sa.text("nextval('open_events_index_seq')"), nullable=False))
    op.execute("ALTER SEQUENCE open_events_index_seq OWNED BY open_events.index")
    op.alter_column('open_events', 'opened_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_unique_constraint('uq_open_events_index', 'open_events', ['index'])

    # --- tracked_emails ---
    op.execute("CREATE SEQUENCE IF NOT EXISTS tracked_emails_index_seq")
    op.add_column('tracked_emails', sa.Column('index', sa.Integer(), server_default=sa.text("nextval('tracked_emails_index_seq')"), nullable=False))
    op.execute("ALTER SEQUENCE tracked_emails_index_seq OWNED BY tracked_emails.index")
    op.alter_column('tracked_emails', 'first_opened_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tracked_emails', 'last_opened_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)
    op.alter_column('tracked_emails', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('tracked_emails', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_unique_constraint('uq_tracked_emails_index', 'tracked_emails', ['index'])


def downgrade() -> None:
    """Downgrade schema."""
    # --- tracked_emails ---
    op.drop_constraint('uq_tracked_emails_index', 'tracked_emails', type_='unique')
    op.alter_column('tracked_emails', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('tracked_emails', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('tracked_emails', 'last_opened_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('tracked_emails', 'first_opened_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.drop_column('tracked_emails', 'index')
    op.execute("DROP SEQUENCE IF EXISTS tracked_emails_index_seq")

    # --- open_events ---
    op.drop_constraint('uq_open_events_index', 'open_events', type_='unique')
    op.alter_column('open_events', 'opened_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.drop_column('open_events', 'index')
    op.execute("DROP SEQUENCE IF EXISTS open_events_index_seq")

    # --- click_events ---
    op.drop_constraint('uq_click_events_index', 'click_events', type_='unique')
    op.alter_column('click_events', 'clicked_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.drop_column('click_events', 'index')
    op.execute("DROP SEQUENCE IF EXISTS click_events_index_seq")

