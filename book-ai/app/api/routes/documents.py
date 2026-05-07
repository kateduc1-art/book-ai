"""
Document routes:
  POST /documents/upload
  POST /documents/{document_id}/index
  GET  /documents/{document_id}
  GET  /documents/{document_id}/jobs
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.models.job import Job, JobStatus, JobType
from app.schemas.document_schema import DocumentIndexResponse, DocumentRead, DocumentUploadResponse
from app.schemas.export_schema import JobCreateResponse, JobStatusResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf"}


def _get_document_or_404(document_id: str, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return doc


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF file and register it in the database."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{suffix}"
    dest_path = upload_dir / safe_filename

    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
        id=doc_id,
        filename=file.filename or safe_filename,
        original_path=str(dest_path),
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    logger.info(f"Document uploaded: id={doc_id}, file={file.filename}")
    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
    )


# ─── Index (async) ────────────────────────────────────────────────────────────

def _run_index_job(job_id: str, document_id: str) -> None:
    """Background task: run the indexing pipeline and update job status."""
    from app.core.database import SessionLocal
    from app.services.document_indexer import index_document

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()

        if not job or not document:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        def update_progress(pct: int, msg: str) -> None:
            job.progress = pct
            job.current_step = msg
            db.commit()

        result = index_document(db=db, document=document, progress_callback=update_progress)

        job.status = JobStatus.completed
        job.progress = 100
        job.current_step = "Indexing complete"
        job.result = result
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Index job {job_id} failed: {e}", exc_info=True)
        if job:
            job.status = JobStatus.failed
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.failed
            db.commit()
    finally:
        db.close()


@router.post("/{document_id}/index", response_model=JobCreateResponse, status_code=202)
def index_document_endpoint(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger async indexing for a document. Returns a job ID to track progress."""
    document = _get_document_or_404(document_id, db)

    if document.status == DocumentStatus.indexing:
        raise HTTPException(status_code=409, detail="Document is already being indexed")

    job = Job(
        document_id=document_id,
        job_type=JobType.index,
        status=JobStatus.pending,
        input_data={"document_id": document_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_index_job, job.id, document_id)

    return JobCreateResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        message="Indexing started. Poll /documents/{document_id}/jobs/{job_id} for status.",
    )


# ─── Document details ─────────────────────────────────────────────────────────

@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document metadata."""
    return _get_document_or_404(document_id, db)


# ─── Job status ───────────────────────────────────────────────────────────────

@router.get("/{document_id}/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(document_id: str, job_id: str, db: Session = Depends(get_db)):
    """Get status and progress of an async job."""
    _get_document_or_404(document_id, db)
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.document_id == document_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        result=job.result,
    )
