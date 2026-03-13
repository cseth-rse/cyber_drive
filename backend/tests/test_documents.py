# tests/test_documents.py
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from fastapi import HTTPException

from app.documents.service import DocumentsService
from app.models import Document, DocumentStatus, User, Role


def make_settings():
    s = MagicMock()
    s.upload_dir = "uploads"
    s.max_file_size_mb = 50
    s.max_file_size_bytes = 50 * 1024 * 1024
    return s


def make_svc(db=None):
    db = db or MagicMock()
    return DocumentsService(db, make_settings())


def make_upload_file(content: bytes = b"", filename: str = "test.pdf"):
    f = AsyncMock()
    f.read = AsyncMock(return_value=content)
    f.filename = filename
    return f


def make_uploader():
    u = MagicMock(spec=User)
    u.id = "admin-uuid"
    u.role = Role.ADMIN
    return u


# ── upload validation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_rejects_oversized_file():
    svc = make_svc()
    big = make_upload_file(content=b"x" * (51 * 1024 * 1024))

    with pytest.raises(HTTPException) as exc_info:
        await svc.upload(big, "Title", "course-id", 1, make_uploader())
    assert exc_info.value.status_code == 400
    assert "size" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf():
    svc = make_svc()
    # PNG magic bytes
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    fake_file = make_upload_file(content=png_bytes, filename="image.png")

    with pytest.raises(HTTPException) as exc_info:
        await svc.upload(fake_file, "Title", "course-id", 1, make_uploader())
    assert exc_info.value.status_code == 400
    assert "pdf" in str(exc_info.value.detail).lower()


# ── list_documents ────────────────────────────────────────────────────────────

def test_list_documents_returns_paginated():
    db = MagicMock()
    mock_query = MagicMock()
    db.query.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.count.return_value = 3
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [MagicMock(), MagicMock()]

    svc = make_svc(db=db)
    result = svc.list_documents(page=1, limit=20)

    assert result["total"] == 3
    assert result["page"] == 1
    assert len(result["items"]) == 2


def test_list_documents_caps_limit_at_50():
    db = MagicMock()
    mock_query = MagicMock()
    db.query.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.count.return_value = 0
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    svc = make_svc(db=db)
    result = svc.list_documents(page=1, limit=200)

    mock_query.limit.assert_called_with(50)


# ── get_document ──────────────────────────────────────────────────────────────

def test_get_document_not_found():
    db = MagicMock()
    mock_query = MagicMock()
    db.query.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None

    svc = make_svc(db=db)
    with pytest.raises(HTTPException) as exc_info:
        svc.get_document("bad-id")
    assert exc_info.value.status_code == 404


def test_get_document_found():
    doc = MagicMock(spec=Document)
    doc.id = "doc-1"

    db = MagicMock()
    mock_query = MagicMock()
    db.query.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = doc

    svc = make_svc(db=db)
    result = svc.get_document("doc-1")
    assert result.id == "doc-1"
