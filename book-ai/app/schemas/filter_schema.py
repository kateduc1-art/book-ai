from pydantic import BaseModel, Field
from typing import Literal


class FilterRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1, description="List of topics to search for")
    granularity: Literal["paragraph", "page"] = "paragraph"
    min_score: float = Field(default=0.75, ge=0.0, le=1.0)
    max_results: int = Field(default=100, ge=1, le=500)


class FilteredChunk(BaseModel):
    chunk_id: str
    page: int
    paragraph: int
    text: str
    score: float
    matched_topic: str


class FilterResponse(BaseModel):
    document_id: str
    topics: list[str]
    results: list[FilteredChunk]


class ValidateRelevanceRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1)
    candidate_chunk_ids: list[str] = Field(..., min_length=1)


class ChunkValidationResult(BaseModel):
    chunk_id: str
    is_relevant: bool
    confidence: float = 0.0
    matched_topics: list[str] = []
    reason: str = ""


class ValidateRelevanceResponse(BaseModel):
    document_id: str
    results: list[ChunkValidationResult]
