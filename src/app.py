from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

from src.errors import StoreError, SummarizeError
from src.extractors.base import ExtractionError
from src.extractors.registry import extract
from src.notion_store import store
from src.summarizer import summarize

app = FastAPI(title="Knowledge Pipeline")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    _request: object, exc: RequestValidationError
) -> JSONResponse:
    messages: list[str] = []
    for err in exc.errors():
        msg = err.get("msg", "Invalid value")
        loc = [str(part) for part in err.get("loc", ()) if part != "body"]
        if loc:
            messages.append(f"{' → '.join(loc)}: {msg}")
        else:
            messages.append(msg)
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(messages) or "Invalid request."},
    )

_STATIC = Path(__file__).resolve().parent.parent / "static"


class CaptureRequest(BaseModel):
    url: HttpUrl


class CaptureResponse(BaseModel):
    title: str
    source: str
    tldr: str
    key_points: list[str]
    tags: list[str]
    notion_url: str


@app.post("/capture", response_model=CaptureResponse)
async def capture(req: CaptureRequest) -> CaptureResponse:
    """The whole pipeline, in three honest steps: extract -> summarize -> store.

    Each step is an independent, typed function. In the agentic phase, these same
    three functions become tools the agent can call in whatever order it decides.
    """
    try:
        content = await extract(str(req.url))
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        summary = await summarize(content)
    except SummarizeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        notion_url = await store(content, summary)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return CaptureResponse(
        title=content.title,
        source=content.source_type.value,
        tldr=summary.tldr,
        key_points=summary.key_points,
        tags=summary.tags,
        notion_url=notion_url,
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
