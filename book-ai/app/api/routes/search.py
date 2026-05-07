"""
Search routes:
  POST /documents/{document_id}/filter
  POST /documents/{document_id}/validate-relevance
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.models.job import Job, JobStatus, JobType
from app.schemas.export_schema import JobCreateResponse, JobStatusResponse
from app.schemas.filter_schema import (
    FilterRequest,
    FilterResponse,
    ValidateRelevanceRequest,
    ValidateRelevanceResponse,
)

logger = get_logger(__name__)
router = APIRouter(tags=["search"])


def _get_indexed_document_or_404(document_id: str, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    if doc.status != DocumentStatus.indexed:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not indexed yet (status={doc.status}). Run /index first.",
        )
    return doc


# ─── Topic filter ─────────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/filter", response_model=FilterResponse)
def filter_by_topics(
    document_id: str,
    request: FilterRequest,
    db: Session = Depends(get_db),
):
    """
    Search for chunks in the document that match the given topics.
    Returns page, paragraph, text, score, and matched_topic.
    """
    _get_indexed_document_or_404(document_id, db)

    from app.services.topic_search_service import search_by_topics

    results = search_by_topics(
        db=db,
        document_id=document_id,
        topics=request.topics,
        min_score=request.min_score,
        max_results=request.max_results,
    )

    return FilterResponse(
        document_id=document_id,
        topics=request.topics,
        results=results,
    )


# ─── Relevance validation ────────────────────────────────────────────────────

def _run_validate_job(job_id: str, document_id: str, chunk_ids: list[str], topics: list[str]) -> None:
    """Background task: run relevance validation."""
    from datetime import datetime, timezone
    from app.core.database import SessionLocal
    from app.agents.relevance_validator_agent import RelevanceValidatorAgent
    from app.services.topic_search_service import get_chunks_by_ids

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        chunks = get_chunks_by_ids(db, chunk_ids)
        agent = RelevanceValidatorAgent()
        items = [
            {"chunk_id": c.id, "text": c.text, "page": c.page_number, "paragraph": c.paragraph_number}
            for c in chunks
        ]
        results = agent.validate_batch(items, topics)

        job.status = JobStatus.completed
        job.progress = 100
        job.result = {
            "document_id": document_id,
            "results": [r.model_dump() for r in results],
        }
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Validate job {job_id} failed: {e}", exc_info=True)
        if job:
            job.status = JobStatus.failed
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/documents/{document_id}/validate-relevance", response_model=JobCreateResponse, status_code=202)
def validate_relevance(
    document_id: str,
    request: ValidateRelevanceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Validate whether candidate chunks are truly relevant to the given topics.
    Returns a job_id — poll /documents/{document_id}/jobs/{job_id} for results.
    """
    _get_indexed_document_or_404(document_id, db)

    job = Job(
        document_id=document_id,
        job_type=JobType.validate_relevance,
        status=JobStatus.pending,
        input_data={
            "chunk_ids": request.candidate_chunk_ids,
            "topics": request.topics,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_validate_job, job.id, document_id, request.candidate_chunk_ids, request.topics
    )

    return JobCreateResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        message="Relevance validation started. Poll /documents/{document_id}/jobs/{job_id} for results.",
    )
