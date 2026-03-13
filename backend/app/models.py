# app/models.py
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text,
    Enum as SAEnum, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


def _uuid() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    STUDENT = "STUDENT"
    CONTRIBUTOR = "CONTRIBUTOR"
    ADMIN = "ADMIN"


class DocumentStatus(str, enum.Enum):
    PENDING_SCAN = "PENDING_SCAN"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AVAILABLE = "AVAILABLE"
    REJECTED = "REJECTED"


class AuditAction(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REFRESH = "REFRESH"
    UPLOAD = "UPLOAD"
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ROLE_CHANGE = "ROLE_CHANGE"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(SAEnum(Role, name="role"), nullable=False, default=Role.STUDENT)
    otp = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    refresh_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    uploaded_docs = relationship("Document", back_populates="uploaded_by", foreign_keys="Document.uploaded_by_id")
    approved_docs = relationship("Document", back_populates="approved_by", foreign_keys="Document.approved_by_id")
    audit_logs = relationship("AuditLog", back_populates="user")


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    order = Column(Integer, unique=True, nullable=False)

    courses = relationship("Course", back_populates="level")
    documents = relationship("Document", back_populates="level")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("code", "level_id", name="uq_course_code_level"),)

    id = Column(String, primary_key=True, default=_uuid)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)

    level = relationship("Level", back_populates="courses")
    documents = relationship("Document", back_populates="course")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_doc_level_course_status", "level_id", "course_id", "status"),
        Index("ix_doc_uploader", "uploaded_by_id"),
        Index("ix_doc_status_created", "status", "created_at"),   # Phase 4: analytics
    )

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, unique=True, nullable=False)   # local path OR S3 key
    storage_backend = Column(String, nullable=False, default="local")  # "local" | "s3"
    checksum = Column(String, unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(SAEnum(DocumentStatus, name="documentstatus"), nullable=False, default=DocumentStatus.PENDING_SCAN)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    download_count = Column(Integer, default=0, nullable=False)

    # Phase 2: scan + approval
    scanned_at = Column(DateTime, nullable=True)
    scan_result = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    uploaded_by = relationship("User", back_populates="uploaded_docs", foreign_keys=[uploaded_by_id])
    approved_by = relationship("User", back_populates="approved_docs", foreign_keys=[approved_by_id])
    course = relationship("Course", back_populates="documents")
    level = relationship("Level", back_populates="documents")
    audit_logs = relationship("AuditLog", back_populates="document")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_ts", "user_id", "timestamp"),
        Index("ix_audit_doc_ts", "document_id", "timestamp"),
        Index("ix_audit_action_ts", "action", "timestamp"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(SAEnum(AuditAction, name="auditaction"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    extra = Column("metadata", Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")
    document = relationship("Document", back_populates="audit_logs")
