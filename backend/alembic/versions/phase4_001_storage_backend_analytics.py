"""phase4_storage_backend_analytics_indexes

Revision ID: phase4_001
Revises: phase2_001
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "phase4_001"
down_revision = "phase2_001"   # unchanged — still depends on phase2_001
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add storage_backend column to documents
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column("storage_backend", sa.String(), nullable=False, server_default="local")
        )

    # 2. Add composite index for analytics queries
    op.create_index("ix_doc_status_created", "documents", ["status", "created_at"])

    # 3. Partial indexes (PostgreSQL only)
    bind = op.get_context().bind
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_audit_download_ts "
            "ON audit_logs (timestamp) WHERE action = 'DOWNLOAD'"
        ))
        op.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_audit_upload_ts "
            "ON audit_logs (timestamp) WHERE action = 'UPLOAD'"
        ))


def downgrade() -> None:
    bind = op.get_context().bind
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS ix_audit_upload_ts"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_audit_download_ts"))

    op.drop_index("ix_doc_status_created", "documents")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("storage_backend")