"""
Export routes:
  GET /exports/{chapter_id}/markdown
  GET /exports/{chapter_id}/docx
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.chapter import Chapter

logger = get_logger(__name__)
router = APIRouter(prefix="/exports", tags=["exports"])


def _get_chapter_or_404(chapter_id: str, db: Session) -> Chapter:
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found")
    return chapter


@router.get("/{chapter_id}/markdown")
def export_chapter_markdown(chapter_id: str, db: Session = Depends(get_db)):
    """Export chapter as Markdown file. Generates if not yet created."""
    chapter = _get_chapter_or_404(chapter_id, db)

    if not chapter.markdown_content and not chapter.rewritten_markdown:
        raise HTTPException(status_code=400, detail="Chapter has no content to export")

    # Re-generate if path missing or file deleted
    if not chapter.export_markdown_path or not Path(chapter.export_markdown_path).exists():
        from app.services.export_service import export_markdown
        export_markdown(db, chapter)

    file_path = Path(chapter.export_markdown_path)
    return FileResponse(
        path=str(file_path),
        media_type="text/markdown",
        filename=file_path.name,
    )


@router.get("/{chapter_id}/docx")
def export_chapter_docx(chapter_id: str, db: Session = Depends(get_db)):
    """Export chapter as DOCX file. Generates if not yet created."""
    chapter = _get_chapter_or_404(chapter_id, db)

    if not chapter.markdown_content and not chapter.rewritten_markdown:
        raise HTTPException(status_code=400, detail="Chapter has no content to export")

    if not chapter.export_docx_path or not Path(chapter.export_docx_path).exists():
        from app.services.export_service import export_docx
        export_docx(db, chapter)

    file_path = Path(chapter.export_docx_path)
    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file_path.name,
    )
