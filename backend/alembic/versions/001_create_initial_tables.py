"""create initial tables

Revision ID: 001
Revises: 
Create Date: 2026-09-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', name='scanstatus'), nullable=False),
        sa.Column('feature_schema_version', sa.String(32), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_tier', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='risktier'), nullable=True),
        sa.Column('score_source', sa.Enum('fixed_baseline', 'ml_model', 'fallback_baseline', name='scoresource'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
    )
    op.create_index('ix_scans_created_at', 'scans', ['created_at'])
    op.create_index('ix_scans_status', 'scans', ['status'])

    op.create_table(
        'findings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scan_id', UUID(as_uuid=True), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(64), nullable=False),
        sa.Column('category', sa.Enum('security', 'configuration', 'performance', 'privacy', name='findingcategory'), nullable=False),
        sa.Column('severity', sa.Enum('critical', 'high', 'medium', 'low', 'info', name='findingseverity'), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('source', sa.Enum('rule_engine', 'ml_model', 'cve_lookup', name='findingsource'), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_findings_scan_id', 'findings', ['scan_id'])
    op.create_index('ix_findings_rule_id', 'findings', ['rule_id'])
    op.create_index('ix_findings_severity', 'findings', ['severity'])


def downgrade() -> None:
    op.drop_index('ix_findings_severity', table_name='findings')
    op.drop_index('ix_findings_rule_id', table_name='findings')
    op.drop_index('ix_findings_scan_id', table_name='findings')
    op.drop_table('findings')

    op.drop_index('ix_scans_status', table_name='scans')
    op.drop_index('ix_scans_created_at', table_name='scans')
    op.drop_table('scans')

    op.execute('DROP TYPE IF EXISTS scanstatus')
    op.execute('DROP TYPE IF EXISTS risktier')
    op.execute('DROP TYPE IF EXISTS scoresource')
    op.execute('DROP TYPE IF EXISTS findingcategory')
    op.execute('DROP TYPE IF EXISTS findingseverity')
    op.execute('DROP TYPE IF EXISTS findingsource')