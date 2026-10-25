"""add scan response metadata and timestamps indexes

Revision ID: a7f3c1d92b04
Revises: 1cfc1e25a058
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f3c1d92b04"
down_revision: str | None = "1cfc1e25a058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Persist the collector's observed response metadata so the API and
    # reports never fabricate values for completed scans.
    op.add_column("scans", sa.Column("status_code", sa.Integer(), nullable=True))
    op.add_column("scans", sa.Column("content_type", sa.String(length=255), nullable=True))
    op.add_column("scans", sa.Column("response_time_ms", sa.Integer(), nullable=True))
    op.add_column("scans", sa.Column("redirect_count", sa.Integer(), nullable=True))
    op.add_column("scans", sa.Column("final_url", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("content_length", sa.Integer(), nullable=True))

    # Existing timestamps are stored as UTC-naive; reinterpret them as UTC
    # when converting to timestamptz.
    op.execute(
        "ALTER TABLE scans ALTER COLUMN created_at TYPE timestamptz "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE scans ALTER COLUMN completed_at TYPE timestamptz "
        "USING completed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE findings ALTER COLUMN created_at TYPE timestamptz "
        "USING created_at AT TIME ZONE 'UTC'"
    )

    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_index("ix_findings_created_at", "findings", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_findings_created_at", table_name="findings")
    op.drop_index("ix_scans_created_at", table_name="scans")

    op.execute("ALTER TABLE scans ALTER COLUMN created_at TYPE timestamp")
    op.execute("ALTER TABLE scans ALTER COLUMN completed_at TYPE timestamp")
    op.execute("ALTER TABLE findings ALTER COLUMN created_at TYPE timestamp")

    op.drop_column("scans", "content_length")
    op.drop_column("scans", "final_url")
    op.drop_column("scans", "redirect_count")
    op.drop_column("scans", "response_time_ms")
    op.drop_column("scans", "content_type")
    op.drop_column("scans", "status_code")
