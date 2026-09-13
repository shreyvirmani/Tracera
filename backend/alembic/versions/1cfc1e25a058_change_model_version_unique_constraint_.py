"""Change model_version unique constraint to composite with dataset_version

Revision ID: 1cfc1e25a058
Revises: c3893b19edc9
Create Date: 2026-09-13 15:14:23.090334

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1cfc1e25a058"
down_revision: str | None = "c3893b19edc9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the existing unique constraint on model_version
    op.drop_constraint("uq_model_versions_model_version", "model_versions", type_="unique")
    # Create composite unique constraint on (model_version, dataset_version)
    op.create_unique_constraint(
        "uq_model_versions_model_version_dataset",
        "model_versions",
        ["model_version", "dataset_version"],
    )


def downgrade() -> None:
    # Drop the composite unique constraint
    op.drop_constraint("uq_model_versions_model_version_dataset", "model_versions", type_="unique")
    # Recreate the original unique constraint on model_version
    op.create_unique_constraint(
        "uq_model_versions_model_version", "model_versions", ["model_version"]
    )
