from pydantic import BaseModel


class ExportResponse(BaseModel):
    chapter_id: str
    format: str
    path: str
    filename: str


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    result: dict | None = None


class JobCreateResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    message: str
