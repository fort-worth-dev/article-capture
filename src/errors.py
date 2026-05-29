from __future__ import annotations


class PipelineError(Exception):
    """User-facing pipeline failure with a suggested HTTP status code."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class SummarizeError(PipelineError):
    """Raised when Claude summarization fails."""


class StoreError(PipelineError):
    """Raised when Notion storage fails."""
