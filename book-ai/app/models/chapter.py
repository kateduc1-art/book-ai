import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewritten_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_short: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_detailed: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    # [{page, paragraph}]
    sources: Mapped[list] = mapped_column(JSON, default=list)
    # [{paragraph, based_on_pages}]
    source_map: Mapped[list] = mapped_column(JSON, default=list)
    # list of chunk IDs used
    chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    export_markdown_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    export_docx_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="chapters"
    )
