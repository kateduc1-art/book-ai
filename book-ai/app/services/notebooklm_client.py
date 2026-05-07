"""
NotebookLM Enterprise client — OPTIONAL integration.

This module is disabled by default (USE_NOTEBOOKLM=false in .env).
It provides stub/partial implementations for NotebookLM Enterprise API.

⚠️  IMPORTANT:
    - NotebookLM Enterprise API is in limited preview as of 2024.
    - Access must be requested through Google Cloud.
    - Do NOT use browser automation or scraping of the NotebookLM interface.
    - Set USE_NOTEBOOKLM=true and configure the required env vars to enable.

Required env vars (when enabled):
    NOTEBOOKLM_PROJECT_ID  — your Google Cloud project ID
    NOTEBOOKLM_LOCATION    — API region (e.g., us-central1)
    NOTEBOOKLM_API_KEY     — your API key or use ADC
"""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotebookLMClient:
    """
    Client for NotebookLM Enterprise API.
    When USE_NOTEBOOKLM is false, all methods raise NotImplementedError
    with a helpful message.
    """

    def __init__(self) -> None:
        self._enabled = settings.use_notebooklm
        if self._enabled:
            self._validate_config()
            logger.info("NotebookLM client initialized (enabled)")
        else:
            logger.info("NotebookLM client is disabled (USE_NOTEBOOKLM=false)")

    def _validate_config(self) -> None:
        missing = []
        if not settings.notebooklm_project_id:
            missing.append("NOTEBOOKLM_PROJECT_ID")
        if not settings.notebooklm_location:
            missing.append("NOTEBOOKLM_LOCATION")
        if not settings.notebooklm_api_key:
            missing.append("NOTEBOOKLM_API_KEY")
        if missing:
            raise ValueError(
                f"NotebookLM is enabled but missing env vars: {', '.join(missing)}"
            )

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise NotImplementedError(
                "NotebookLM integration is disabled. "
                "Set USE_NOTEBOOKLM=true and configure the required env vars."
            )

    # ── Stub implementations ─────────────────────────────────────────────────

    def create_notebook(self, title: str, description: str = "") -> dict:
        """Create a new notebook in NotebookLM Enterprise."""
        self._require_enabled()
        # TODO: implement actual API call once preview access is available
        # POST https://{location}-aiplatform.googleapis.com/v1/projects/{project}/notebooks
        raise NotImplementedError("create_notebook: API endpoint pending preview access.")

    def add_source_text(self, notebook_id: str, text: str, title: str = "") -> dict:
        """Add a text source to a notebook."""
        self._require_enabled()
        # TODO: implement POST to sources endpoint
        raise NotImplementedError("add_source_text: API endpoint pending preview access.")

    def add_source_file(self, notebook_id: str, file_path: str) -> dict:
        """Upload a file as a source to a notebook."""
        self._require_enabled()
        # TODO: implement multipart upload
        raise NotImplementedError("add_source_file: API endpoint pending preview access.")

    def request_summary(self, notebook_id: str) -> dict:
        """Request a summary from NotebookLM for a given notebook."""
        self._require_enabled()
        # TODO: implement summary generation call
        raise NotImplementedError("request_summary: API endpoint pending preview access.")

    def get_notebook(self, notebook_id: str) -> dict:
        """Retrieve notebook metadata."""
        self._require_enabled()
        raise NotImplementedError("get_notebook: API endpoint pending preview access.")


# Singleton
_client: NotebookLMClient | None = None


def get_notebooklm_client() -> NotebookLMClient:
    global _client
    if _client is None:
        _client = NotebookLMClient()
    return _client
