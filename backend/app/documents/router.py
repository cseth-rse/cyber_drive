# app/documents/router.py
from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, File
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.documents.service import DocumentsService
from app.models import Role, User
from app.schemas import DocumentDetail, DocumentUploadResponse, PaginatedDocuments

router = APIRouter(prefix="/documents", tags=["Documents"])


def _svc(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    return DocumentsService(db, settings)


def require_uploader(current_user: User = Depends(get_current_user)) -> User:
    from fastapi import HTTPException, status
    if current_user.role not in (Role.CONTRIBUTOR, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Contributors and Admins can upload documents")
    return current_user


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    course_id: str = Form(...),
    level_id: int = Form(...),
    description: str | None = Form(default=None),
    uploader: User = Depends(require_uploader),
    svc: DocumentsService = Depends(_svc),
):
    return await svc.upload(file, title, course_id, level_id, uploader, description, request)


@router.get("", response_model=PaginatedDocuments)
def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    level_id: int | None = Query(default=None),
    course_id: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    svc: DocumentsService = Depends(_svc),
):
    return svc.list_documents(page=page, limit=limit, level_id=level_id, course_id=course_id)


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, _: User = Depends(get_current_user), svc: DocumentsService = Depends(_svc)):
    return svc.get_document(doc_id)


@router.get("/{doc_id}/view")
def view_document(doc_id: str, request: Request,
                  current_user: User = Depends(get_current_user), svc: DocumentsService = Depends(_svc)):
    """Stream PDF inline (local) or redirect to presigned S3 URL. Logs VIEW."""
    return svc.serve_view(doc_id, current_user, request)


@router.get("/{doc_id}/download")
def download_document(doc_id: str, request: Request,
                      current_user: User = Depends(get_current_user), svc: DocumentsService = Depends(_svc)):
    """Force-download PDF (local) or redirect to presigned S3 URL. Logs DOWNLOAD."""
    return svc.serve_download(doc_id, current_user, request)


# Backwards compat alias
@router.get("/{doc_id}/file")
def file_compat(doc_id: str, request: Request,
                current_user: User = Depends(get_current_user), svc: DocumentsService = Depends(_svc)):
    return svc.serve_view(doc_id, current_user, request)
