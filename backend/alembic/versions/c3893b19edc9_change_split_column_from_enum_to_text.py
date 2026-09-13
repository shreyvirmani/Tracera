"""Change split column from enum to text

Revision ID: c3893b19edc9
Revises: 3322cb2e541d
Create Date: 2026-09-13 12:25:17.971187

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3893b19edc9"
down_revision: str | None = "3322cb2e541d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Change split column from enum to text
    op.alter_column(
        "dataset_samples",
        "split",
        type_=sa.Text(),
        existing_type=sa.Enum("train", "validation", "test", name="splittype"),
        existing_nullable=True,
    )
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS splittype")


def downgrade() -> None:
    # Recreate the enum type
    op.execute("CREATE TYPE splittype AS ENUM ('train', 'validation', 'test')")
    # Change column back to enum
    op.alter_column(
        "dataset_samples",
        "split",
        type_=sa.Enum("train", "validation", "test", name="splittype"),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
