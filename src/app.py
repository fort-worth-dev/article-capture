from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.pipeline import (
    CaptureHttpError,
    CaptureRequest,
    CaptureResponse,
    format_validation_error,
    run_capture,
)

app = FastAPI(title="Knowledge Pipeline")

# Netlify UI calls Render directly for /capture (YouTube can exceed Netlify's ~26s proxy limit).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    _request: object, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": format_validation_error(exc)},
    )

_STATIC = Path(__file__).resolve().parent.parent / "static"


@app.post("/capture", response_model=CaptureResponse)
async def capture(req: CaptureRequest) -> CaptureResponse:
    """The whole pipeline, in three honest steps: extract -> summarize -> store.

    Each step is an independent, typed function. In the agentic phase, these same
    three functions become tools the agent can call in whatever order it decides.
    """
    try:
        return await run_capture(str(req.url))
    except CaptureHttpError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
