from pydantic import BaseModel, Field
from datetime import datetime
from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus

    model_config = {"from_attributes": True}


class DocumentIndexResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    pages_processed: int
    chunks_created: int

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    total_pages: int
    total_chunks: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
