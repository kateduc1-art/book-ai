from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://bookai:bookai@localhost:5432/book_ai"

    # ── OpenAI ───────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    # ── Storage ───────────────────────────────────────────────
    upload_dir: str = "storage/uploads"
    export_dir: str = "storage/exports"

    # ── Processing ────────────────────────────────────────────
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_score: float = 0.75
    max_results: int = 100

    # ── NotebookLM (optional) ─────────────────────────────────
    use_notebooklm: bool = False
    notebooklm_project_id: str = ""
    notebooklm_location: str = ""
    notebooklm_api_key: str = ""

    # ── App metadata ──────────────────────────────────────────
    app_name: str = "Book AI"
    app_version: str = "0.1.0"
    debug: bool = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
