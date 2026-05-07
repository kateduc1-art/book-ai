"""
Chapter routes:
  POST /chapters/build
  POST /chapters/{chapter_id}/summarize
  POST /chapters/{chapter_id}/rewrite
  GET  /chapters/{chapter_id}
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.chapter import Chapter
from app.models.job import Job, JobStatus, JobType
from app.schemas.chapter_schema import (
    BuildChapterRequest,
    BuildChapterResponse,
    ChapterRead,
    ChapterSource,
    ChapterSourceMap,
    RewriteRequest,
    RewriteResponse,
    SummarizeResponse,
)
from app.schemas.export_schema import JobCreateResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/chapters", tags=["chapters"])


def _get_chapter_or_404(chapter_id: str, db: Session) -> Chapter:
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found")
    return chapter


# ─── Build chapter ────────────────────────────────────────────────────────────

@router.post("/build", response_model=BuildChapterResponse, status_code=201)
def build_chapter(request: BuildChapterRequest, db: Session = Depends(get_db)):
    """
    Assemble a new chapter from validated chunk IDs.
    Chunks are ordered by page and organized into sections.
    """
    from app.services.chapter_builder import create_chapter

    try:
        chapter = create_chapter(
            db=db,
            document_id=request.document_id,
            title=request.title,
            topics=request.topics,
            chunk_ids=request.validated_chunk_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sources = [ChapterSource(**s) for s in (chapter.sources or [])]

    return BuildChapterResponse(
        chapter_id=chapter.id,
        title=chapter.title,
        markdown=chapter.markdown_content or "",
        sources=sources,
    )


# ─── Summarize ────────────────────────────────────────────────────────────────

def _run_summarize_job(job_id: str, chapter_id: str) -> None:
    from app.core.database import SessionLocal
    from app.agents.summarizer_agent import SummarizerAgent

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

        if not job or not chapter:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        agent = SummarizerAgent()
        data = agent.summarize(chapter.title, chapter.markdown_content or "")

        chapter.summary_short = data.get("summary_short", "")
        chapter.summary_detailed = data.get("summary_detailed", "")
        chapter.key_points = data.get("key_points", [])
        chapter.concepts = data.get("concepts", [])

        job.status = JobStatus.completed
        job.progress = 100
        job.result = {
            "chapter_id": chapter_id,
            "summary_short": chapter.summary_short,
            "summary_detailed": chapter.summary_detailed,
            "key_points": chapter.key_points,
            "concepts": chapter.concepts,
        }
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Summarize job {job_id} failed: {e}", exc_info=True)
        if job:
            job.status = JobStatus.failed
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/{chapter_id}/summarize", response_model=JobCreateResponse, status_code=202)
def summarize_chapter(
    chapter_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate a structured summary for the chapter (async job)."""
    chapter = _get_chapter_or_404(chapter_id, db)

    if not chapter.markdown_content:
        raise HTTPException(status_code=400, detail="Chapter has no content to summarize")

    job = Job(
        document_id=chapter.document_id,
        job_type=JobType.summarize,
        status=JobStatus.pending,
        input_data={"chapter_id": chapter_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_summarize_job, job.id, chapter_id)

    return JobCreateResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        message=(
            "Summarization started. Poll "
            f"/documents/{chapter.document_id}/jobs/{job.id} for results."
        ),
    )


# ─── Rewrite ──────────────────────────────────────────────────────────────────

def _run_rewrite_job(job_id: str, chapter_id: str, style: str, audience: str) -> None:
    from app.core.database import SessionLocal
    from app.agents.rewriter_agent import RewriterAgent

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()

        if not job or not chapter:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        agent = RewriterAgent()
        rewritten, source_map = agent.rewrite(
            chapter.title,
            chapter.markdown_content or "",
            style,
            audience,
            chapter.sources or [],
        )
        chapter.rewritten_markdown = rewritten
        chapter.source_map = source_map

        job.status = JobStatus.completed
        job.progress = 100
        job.result = {
            "chapter_id": chapter_id,
            "rewritten_markdown": rewritten,
            "source_map": source_map,
        }
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Rewrite job {job_id} failed: {e}", exc_info=True)
        if job:
            job.status = JobStatus.failed
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/{chapter_id}/rewrite", response_model=JobCreateResponse, status_code=202)
def rewrite_chapter(
    chapter_id: str,
    request: RewriteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Rewrite the chapter in a more fluid, didactic style (async job)."""
    chapter = _get_chapter_or_404(chapter_id, db)

    if not chapter.markdown_content:
        raise HTTPException(status_code=400, detail="Chapter has no content to rewrite")

    job = Job(
        document_id=chapter.document_id,
        job_type=JobType.rewrite,
        status=JobStatus.pending,
        input_data={
            "chapter_id": chapter_id,
            "style": request.style,
            "audience": request.audience,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_rewrite_job, job.id, chapter_id, request.style, request.audience)

    return JobCreateResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        message=(
            "Rewriting started. Poll "
            f"/documents/{chapter.document_id}/jobs/{job.id} for results."
        ),
    )


# ─── Get chapter ──────────────────────────────────────────────────────────────

@router.get("/{chapter_id}", response_model=ChapterRead)
def get_chapter(chapter_id: str, db: Session = Depends(get_db)):
    """Get chapter metadata."""
    return _get_chapter_or_404(chapter_id, db)
