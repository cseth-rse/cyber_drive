#!/usr/bin/env python3
"""
migrate_phase1_to_phase2.py

Run ONCE after deploying Phase 2 to migrate Phase 1 data:
  - Existing documents with status PENDING → AVAILABLE
    (they were admin-uploaded and passed the Phase 1 simulated scan)

Usage:
    python migrate_phase1_to_phase2.py
"""
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

MIGRATION_SQL = """
-- 1. Migrate old PENDING documents to AVAILABLE
UPDATE documents
SET status = 'AVAILABLE',
    scan_result = 'CLEAN (phase1 migration)',
    scanned_at = NOW()
WHERE status = 'PENDING';

-- 2. Report
SELECT status, COUNT(*) as count FROM documents GROUP BY status;
"""

def run():
    with engine.connect() as conn:
        result = conn.execute(text(
            "UPDATE documents SET status = 'AVAILABLE', scan_result = 'CLEAN (phase1 migration)', "
            "scanned_at = NOW() WHERE status = 'PENDING'"
        ))
        print(f"✓ Migrated {result.rowcount} document(s) from PENDING → AVAILABLE")

        rows = conn.execute(text("SELECT status, COUNT(*) as count FROM documents GROUP BY status")).fetchall()
        conn.commit()

    print("\nDocument status summary:")
    for row in rows:
        print(f"  {row[0]:20s} {row[1]}")

    print("\nMigration complete.")

if __name__ == "__main__":
    run()
