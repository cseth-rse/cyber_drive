"""phase2_contributor_role_audit_log_document_approval

Revision ID: phase2_001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "phase2_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # RENAME VALUE runs safely inside a transaction — no autocommit tricks needed.
        # It renames the enum label AND updates every row using it atomically.
        # No separate UPDATE required.
        conn.execute(sa.text("ALTER TYPE role ADD VALUE IF NOT EXISTS 'CONTRIBUTOR'"))
        conn.execute(sa.text("ALTER TYPE documentstatus RENAME VALUE 'PENDING' TO 'PENDING_SCAN'"))
        conn.execute(sa.text("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'PENDING_APPROVAL'"))
        conn.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE auditaction AS ENUM (
                    'LOGIN','LOGOUT','REFRESH','UPLOAD','VIEW',
                    'DOWNLOAD','DELETE','APPROVE','REJECT','ROLE_CHANGE'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
    else:
        # SQLite uses VARCHAR — just update the value directly
        conn.execute(sa.text(
            "UPDATE documents SET status = 'PENDING_SCAN' WHERE status = 'PENDING'"
        ))

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("scanned_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("scan_result", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("approved_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=True)
        )
        batch_op.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_user_ts", "audit_logs", ["user_id", "timestamp"])
    op.create_index("ix_audit_doc_ts", "audit_logs", ["document_id", "timestamp"])
    op.create_index("ix_audit_action_ts", "audit_logs", ["action", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_audit_action_ts", "audit_logs")
    op.drop_index("ix_audit_doc_ts", "audit_logs")
    op.drop_index("ix_audit_user_ts", "audit_logs")
    op.drop_table("audit_logs")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("approved_by_id")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("scan_result")
        batch_op.drop_column("scanned_at")

    if op.get_bind().dialect.name == "postgresql":
        # Reverse the rename
        op.get_bind().execute(
            sa.text("ALTER TYPE documentstatus RENAME VALUE 'PENDING_SCAN' TO 'PENDING'")
        )