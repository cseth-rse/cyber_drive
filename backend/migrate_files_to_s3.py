#!/usr/bin/env python3
"""
migrate_files_to_s3.py
──────────────────────
One-time script to migrate all local PDF files to S3/MinIO.

Run AFTER:
  1. MinIO (or AWS S3) is configured and running.
  2. S3_ENABLED=true in your .env file.
  3. alembic upgrade head has been run (to add storage_backend column).

Usage:
    python migrate_files_to_s3.py [--dry-run] [--delete-local]

Flags:
    --dry-run       Print what would happen without making any changes.
    --delete-local  Delete local files after successful S3 upload (default: keep them).
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)


def run(dry_run: bool, delete_local: bool) -> None:
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.models import Document
    from app.storage.s3 import S3Service

    settings = get_settings()

    if not settings.s3_enabled:
        logger.error("S3_ENABLED is not true in your .env — aborting.")
        sys.exit(1)

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    s3 = S3Service(settings)

    # Ensure bucket
    if not dry_run:
        s3.ensure_bucket()

    # Find all documents stored locally
    local_docs = db.query(Document).filter(
        Document.storage_backend == "local"
    ).all()

    logger.info("Found %d documents with local storage", len(local_docs))

    migrated = 0
    skipped = 0
    errors = 0

    for doc in local_docs:
        local_path = Path(doc.file_path)
        if not local_path.is_absolute():
            local_path = Path(settings.upload_dir) / doc.file_path.lstrip("/")

        if not local_path.exists():
            logger.warning("  [SKIP] %s — file not found: %s", doc.id, local_path)
            skipped += 1
            continue

        s3_key = f"documents/{doc.id}/{local_path.name}"

        logger.info("  [%s] %s → s3://%s/%s",
                    "DRY" if dry_run else "MIGRATING",
                    doc.title[:50], settings.s3_bucket_name, s3_key)

        if dry_run:
            migrated += 1
            continue

        try:
            file_bytes = local_path.read_bytes()
            s3.upload_file(file_bytes, s3_key, content_type=doc.mime_type)

            # Update DB record
            doc.file_path = s3_key
            doc.storage_backend = "s3"
            db.commit()

            logger.info("    ✓ Uploaded and DB updated")

            if delete_local:
                local_path.unlink(missing_ok=True)
                logger.info("    ✓ Local file deleted")

            migrated += 1

        except Exception as exc:
            db.rollback()
            logger.error("    ✗ Failed: %s", exc)
            errors += 1

    db.close()

    print("\n" + "─" * 50)
    print(f"  Migrated : {migrated}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")
    if dry_run:
        print("\n  (DRY RUN — no changes made)")
    print("─" * 50)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local files to S3/MinIO")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without making changes")
    parser.add_argument("--delete-local", action="store_true", help="Delete local files after upload")
    args = parser.parse_args()
    run(dry_run=args.dry_run, delete_local=args.delete_local)
