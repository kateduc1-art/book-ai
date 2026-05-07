from pydantic import BaseModel, Field
from datetime import datetime


class ChapterSource(BaseModel):
    page: int
    paragraph: int


class ChapterSourceMap(BaseModel):
    paragraph: int
    based_on_pages: list[int]


class BuildChapterRequest(BaseModel):
    document_id: str
    title: str = Field(..., min_length=3)
    topics: list[str] = Field(..., min_length=1)
    validated_chunk_ids: list[str] = Field(..., min_length=1)


class BuildChapterResponse(BaseModel):
    chapter_id: str
    title: str
    markdown: str
    sources: list[ChapterSource]

    model_config = {"from_attributes": True}


class SummarizeResponse(BaseModel):
    chapter_id: str
    summary_short: str
    summary_detailed: str
    key_points: list[str]
    concepts: list[str]

    model_config = {"from_attributes": True}


class RewriteRequest(BaseModel):
    style: str = "didático, claro, profissional e agradável"
    audience: str = "professores e gestores educacionais"
    preserve_sources: bool = True


class RewriteResponse(BaseModel):
    chapter_id: str
    rewritten_markdown: str
    source_map: list[ChapterSourceMap]

    model_config = {"from_attributes": True}


class ChapterRead(BaseModel):
    id: str
    document_id: str
    title: str
    topics: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
