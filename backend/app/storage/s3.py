# app/storage/s3.py
"""
S3-compatible object storage service.

Works with:
  - MinIO (self-hosted, default)     → S3_ENABLED=true, S3_ENDPOINT=http://localhost:9000
  - AWS S3                            → S3_ENABLED=true, S3_ENDPOINT=https://s3.amazonaws.com, S3_FORCE_PATH_STYLE=false

When S3_ENABLED=false (default), all operations gracefully fall back to
returning the local file path unchanged — so Phase 1/2 code still works.

Install SDK:
    pip install boto3

MinIO Quick Start:
    wget https://dl.min.io/server/minio/release/linux-amd64/minio
    chmod +x minio && sudo mv minio /usr/local/bin/
    mkdir ~/minio-data
    minio server ~/minio-data --console-address ":9001"
    # Console: http://localhost:9001  user: minioadmin  pass: minioadmin
"""
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_client = None
_bucket: str = ""


def _get_client(settings):
    global _client, _bucket
    if _client is not None:
        return _client
    try:
        import boto3
        from botocore.config import Config as BotoConfig

        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path" if settings.s3_force_path_style else "virtual"},
            ),
        )
        _bucket = settings.s3_bucket_name
        logger.info("S3 client initialised (endpoint=%s, bucket=%s)", settings.s3_endpoint, _bucket)
        return _client
    except ImportError:
        raise RuntimeError("boto3 is not installed. Run: pip install boto3")
    except Exception as exc:
        logger.error("Failed to initialise S3 client: %s", exc)
        raise


class S3Service:
    def __init__(self, settings):
        self.settings = settings
        self.enabled = settings.s3_enabled

    # ── Upload ────────────────────────────────────────────────────────────────

    def upload_file(self, file_bytes: bytes, s3_key: str, content_type: str = "application/pdf") -> str:
        """
        Upload bytes to S3. Returns the S3 key.
        If S3 is disabled, raises RuntimeError (should not be called).
        """
        if not self.enabled:
            raise RuntimeError("S3 is not enabled")
        client = _get_client(self.settings)
        client.put_object(
            Bucket=self.settings.s3_bucket_name,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={"uploaded-by": "cyber-drive"},
        )
        logger.info("Uploaded %s to S3 (%d bytes)", s3_key, len(file_bytes))
        return s3_key

    # ── Presigned URL ─────────────────────────────────────────────────────────

    def presigned_url(self, s3_key: str, disposition: str = "inline", filename: str = "") -> str:
        """
        Generate a presigned GET URL that expires in s3_presigned_url_expires seconds.
        disposition: 'inline' (view) or 'attachment' (download)
        """
        if not self.enabled:
            raise RuntimeError("S3 is not enabled")
        client = _get_client(self.settings)
        params = {
            "Bucket": self.settings.s3_bucket_name,
            "Key": s3_key,
            "ResponseContentType": "application/pdf",
        }
        if filename:
            from urllib.parse import quote
            params["ResponseContentDisposition"] = f"{disposition}; filename*=UTF-8''{quote(filename)}"

        url = client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=self.settings.s3_presigned_url_expires,
        )
        return url

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_file(self, s3_key: str) -> None:
        if not self.enabled:
            return
        try:
            client = _get_client(self.settings)
            client.delete_object(Bucket=self.settings.s3_bucket_name, Key=s3_key)
            logger.info("Deleted S3 object: %s", s3_key)
        except Exception as exc:
            logger.warning("Failed to delete S3 object %s: %s", s3_key, exc)

    # ── Bucket health ─────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Returns True if bucket is reachable."""
        if not self.enabled:
            return True  # local mode is always OK
        try:
            client = _get_client(self.settings)
            client.head_bucket(Bucket=self.settings.s3_bucket_name)
            return True
        except Exception as exc:
            logger.warning("S3 health check failed: %s", exc)
            return False

    # ── Ensure bucket exists ──────────────────────────────────────────────────

    def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist (idempotent)."""
        if not self.enabled:
            return
        try:
            client = _get_client(self.settings)
            try:
                client.head_bucket(Bucket=self.settings.s3_bucket_name)
                logger.info("S3 bucket '%s' already exists", self.settings.s3_bucket_name)
            except Exception:
                client.create_bucket(Bucket=self.settings.s3_bucket_name)
                logger.info("Created S3 bucket '%s'", self.settings.s3_bucket_name)
        except Exception as exc:
            logger.error("Could not ensure S3 bucket: %s", exc)
            raise
