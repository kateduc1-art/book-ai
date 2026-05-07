"""
BookProcessingWorkflow — orchestrates the full document processing pipeline.
Can be invoked directly by API endpoints or run as a background job.

Steps:
  1. extract_pdf
  2. chunk_text
  3. generate_embeddings
  4. store_vectors
  5. search_topics
  6. validate_relevance
  7. assemble_chapter
  8. summarize_chapter
  9. rewrite_chapter
  10. export_files
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.chapter import Chapter
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.filter_schema import ChunkValidationResult

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


class WorkflowStep(str, Enum):
    extract_pdf = "extract_pdf"
    chunk_text = "chunk_text"
    generate_embeddings = "generate_embeddings"
    store_vectors = "store_vectors"
    search_topics = "search_topics"
    validate_relevance = "validate_relevance"
    assemble_chapter = "assemble_chapter"
    summarize_chapter = "summarize_chapter"
    rewrite_chapter = "rewrite_chapter"
    export_files = "export_files"


@dataclass
class WorkflowResult:
    success: bool
    document_id: str
    chapter_id: str | None = None
    pages_processed: int = 0
    chunks_created: int = 0
    relevant_chunks: int = 0
    export_markdown_path: str | None = None
    export_docx_path: str | None = None
    errors: list[str] = field(default_factory=list)


class BookProcessingWorkflow:
    """
    Full pipeline workflow from PDF indexing to chapter export.
    Each step is independent and can be called individually.
    """

    def __init__(self, db: Session, progress_callback: ProgressCallback | None = None) -> None:
        self._db = db
        self._progress = progress_callback or (lambda pct, msg: logger.info(f"[{pct}%] {msg}"))

    # ─── Individual steps ────────────────────────────────────────────────────

    def step_index(self, document: Document) -> dict:
        """Steps 1-4: extract, chunk, embed, store."""
        from app.services.document_indexer import index_document

        return index_document(
            db=self._db,
            document=document,
            progress_callback=self._progress,
        )

    def step_search_topics(
        self,
        document_id: str,
        topics: list[str],
        min_score: float = 0.75,
        max_results: int = 100,
    ) -> list:
        """Step 5: semantic search by topics."""
        from app.services.topic_search_service import search_by_topics

        return search_by_topics(
            db=self._db,
            document_id=document_id,
            topics=topics,
            min_score=min_score,
            max_results=max_results,
        )

    def step_validate_relevance(
        self,
        chunk_ids: list[str],
        topics: list[str],
    ) -> list[ChunkValidationResult]:
        """Step 6: AI-powered relevance validation."""
        from app.agents.relevance_validator_agent import RelevanceValidatorAgent
        from app.services.topic_search_service import get_chunks_by_ids

        chunks = get_chunks_by_ids(self._db, chunk_ids)
        agent = RelevanceValidatorAgent()

        items = [
            {
                "chunk_id": c.id,
                "text": c.text,
                "page": c.page_number,
                "paragraph": c.paragraph_number,
            }
            for c in chunks
        ]
        return agent.validate_batch(items, topics)

    def step_assemble_chapter(
        self,
        document_id: str,
        title: str,
        topics: list[str],
        validated_chunk_ids: list[str],
    ) -> Chapter:
        """Step 7: assemble a chapter from validated chunks."""
        from app.services.chapter_builder import create_chapter

        return create_chapter(
            db=self._db,
            document_id=document_id,
            title=title,
            topics=topics,
            chunk_ids=validated_chunk_ids,
        )

    def step_summarize(self, chapter: Chapter) -> Chapter:
        """Step 8: summarize the chapter."""
        from app.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        content = chapter.markdown_content or ""
        summary_data = agent.summarize(chapter.title, content)

        chapter.summary_short = summary_data.get("summary_short", "")
        chapter.summary_detailed = summary_data.get("summary_detailed", "")
        chapter.key_points = summary_data.get("key_points", [])
        chapter.concepts = summary_data.get("concepts", [])
        self._db.commit()
        return chapter

    def step_rewrite(
        self,
        chapter: Chapter,
        style: str = "didático, claro, profissional e agradável",
        audience: str = "professores e gestores educacionais",
    ) -> Chapter:
        """Step 9: rewrite chapter in a better style."""
        from app.agents.rewriter_agent import RewriterAgent

        agent = RewriterAgent()
        content = chapter.markdown_content or ""
        sources = chapter.sources or []

        rewritten, source_map = agent.rewrite(chapter.title, content, style, audience, sources)
        chapter.rewritten_markdown = rewritten
        chapter.source_map = source_map
        self._db.commit()
        return chapter

    def step_export(self, chapter: Chapter) -> tuple[str, str]:
        """Step 10: export to Markdown and DOCX."""
        from app.services.export_service import export_docx, export_markdown

        md_path = export_markdown(self._db, chapter)
        docx_path = export_docx(self._db, chapter)
        return md_path, docx_path

    # ─── Full pipeline ───────────────────────────────────────────────────────

    def run_full_pipeline(
        self,
        document: Document,
        title: str,
        topics: list[str],
        min_score: float = 0.75,
        max_results: int = 100,
        style: str = "didático, claro, profissional e agradável",
        audience: str = "professores e gestores educacionais",
    ) -> WorkflowResult:
        """
        Run the complete pipeline from index to export.
        Returns a WorkflowResult with all outcomes.
        """
        result = WorkflowResult(success=False, document_id=document.id)

        try:
            # Steps 1-4: Index
            self._progress(5, "Starting indexing pipeline")
            index_result = self.step_index(document)
            result.pages_processed = index_result["pages_processed"]
            result.chunks_created = index_result["chunks_created"]

            # Step 5: Search topics
            self._progress(40, "Searching by topics")
            search_results = self.step_search_topics(document.id, topics, min_score, max_results)
            chunk_ids = [r.chunk_id for r in search_results]

            if not chunk_ids:
                result.errors.append("No chunks found matching the given topics")
                result.success = False
                return result

            # Step 6: Validate relevance
            self._progress(55, "Validating relevance with AI")
            validations = self.step_validate_relevance(chunk_ids, topics)
            valid_ids = [v.chunk_id for v in validations if v.is_relevant]
            result.relevant_chunks = len(valid_ids)

            if not valid_ids:
                result.errors.append("No chunks passed AI relevance validation")
                result.success = False
                return result

            # Step 7: Assemble chapter
            self._progress(70, "Assembling chapter")
            chapter = self.step_assemble_chapter(document.id, title, topics, valid_ids)
            result.chapter_id = chapter.id

            # Step 8: Summarize
            self._progress(80, "Generating summary")
            chapter = self.step_summarize(chapter)

            # Step 9: Rewrite
            self._progress(90, "Rewriting chapter")
            chapter = self.step_rewrite(chapter, style, audience)

            # Step 10: Export
            self._progress(95, "Exporting files")
            md_path, docx_path = self.step_export(chapter)
            result.export_markdown_path = md_path
            result.export_docx_path = docx_path

            self._progress(100, "Pipeline complete")
            result.success = True
            return result

        except Exception as e:
            logger.error(f"BookProcessingWorkflow error: {e}", exc_info=True)
            result.errors.append(str(e))
            result.success = False
            return result
