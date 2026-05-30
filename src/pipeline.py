from __future__ import annotations

from pydantic import BaseModel, HttpUrl, ValidationError

from src.errors import StoreError, SummarizeError
from src.extractors.base import ExtractionError
from src.extractors.registry import extract
from src.notion_store import store
from src.summarizer import summarize


class CaptureRequest(BaseModel):
    url: HttpUrl


class CaptureResponse(BaseModel):
    title: str
    source: str
    tldr: str
    key_points: list[str]
    tags: list[str]
    notion_url: str


class CaptureHttpError(Exception):
    """Pipeline failure with an HTTP status code for API handlers."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def format_validation_error(exc: ValidationError) -> str:
    messages: list[str] = []
    for err in exc.errors():
        msg = err.get("msg", "Invalid value")
        loc = [str(part) for part in err.get("loc", ()) if part != "body"]
        if loc:
            messages.append(f"{' → '.join(loc)}: {msg}")
        else:
            messages.append(msg)
    return "; ".join(messages) or "Invalid request."


async def run_capture(url: str) -> CaptureResponse:
    """Extract, summarize, and store a URL. Raises CaptureHttpError on failure."""
    try:
        req = CaptureRequest(url=url)
    except ValidationError as exc:
        raise CaptureHttpError(422, format_validation_error(exc)) from exc

    try:
        content = await extract(str(req.url))
    except ExtractionError as exc:
        raise CaptureHttpError(422, str(exc)) from exc

    try:
        summary = await summarize(content)
    except SummarizeError as exc:
        raise CaptureHttpError(exc.status_code, str(exc)) from exc

    try:
        notion_url = await store(content, summary)
    except StoreError as exc:
        raise CaptureHttpError(exc.status_code, str(exc)) from exc

    return CaptureResponse(
        title=content.title,
        source=content.source_type.value,
        tldr=summary.tldr,
        key_points=summary.key_points,
        tags=summary.tags,
        notion_url=notion_url,
    )
