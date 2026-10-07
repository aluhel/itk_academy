"""change event status to varchar

Revision ID: 7a1b57d71af1
Revises: 5257f44228f7
Create Date: 2026-10-05 11:52:23.098525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1b57d71af1'
down_revision: Union[str, Sequence[str], None] = '5257f44228f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "events",
        "status",
        existing_type=sa.Enum("NEW", "PUBLISHED", name="event_status"),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="lower(status::text)",
    )
    op.execute("DROP TYPE IF EXISTS event_status")


def downgrade() -> None:
    # В старом enum event_status только два значения: NEW и PUBLISHED.
    # Всё, что не влезает, маппим в 'new' — иначе теряем данные.
    op.execute(
        "UPDATE events SET status = 'new' "
        "WHERE lower(status) NOT IN ('new', 'published')"
    )
    op.execute("CREATE TYPE event_status AS ENUM ('NEW', 'PUBLISHED')")
    op.alter_column(
        "events",
        "status",
        existing_type=sa.String(length=50),
        type_=sa.Enum("NEW", "PUBLISHED", name="event_status"),
        existing_nullable=False,
        postgresql_using="upper(status)::event_status",
    )
