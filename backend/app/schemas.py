# app/schemas.py
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class TokenResponse(BaseModel):
    access_token: str
    role: str

class RefreshResponse(BaseModel):
    access_token: str

class MessageResponse(BaseModel):
    message: str


# ── Levels / Courses ──────────────────────────────────────────────────────────

class CourseOut(BaseModel):
    id: str
    code: str
    title: str
    description: str | None = None

    class Config:
        from_attributes = True

class LevelOut(BaseModel):
    id: int
    name: str
    order: int
    courses: list[CourseOut] = []

    class Config:
        from_attributes = True


# ── Documents ─────────────────────────────────────────────────────────────────

class UserBrief(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    id: str
    status: str
    title: str

class DocumentDetail(BaseModel):
    id: str
    title: str
    description: str | None = None
    file_name: str
    size: int
    mime_type: str
    status: str
    download_count: int
    scan_result: str | None = None
    scanned_at: datetime | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    course: CourseOut | None = None
    level: LevelOut | None = None
    uploaded_by: UserBrief | None = None
    approved_by: UserBrief | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaginatedDocuments(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: list[DocumentDetail]

    class Config:
        from_attributes = True
