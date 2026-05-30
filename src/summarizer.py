from __future__ import annotations

import json
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from pydantic import ValidationError

from src.config import get_settings
from src.errors import SummarizeError
from src.models import Content, Summary

_SYSTEM = (
    "You are a precise research summarizer. You distill articles and video "
    "transcripts about software, AI, and agentic systems into structured notes. "
    "Be faithful to the source and concise; never invent details."
)

# Output budget for the tool call — 1024 was truncating key_points/tags on longer articles.
_MAX_SUMMARY_TOKENS = 2048


def _summary_tool_schema() -> dict[str, Any]:
    """Anthropic-friendly schema: properties + required only (no model title/description)."""
    schema = Summary.model_json_schema()
    return {
        "type": "object",
        "properties": schema["properties"],
        "required": schema["required"],
        "additionalProperties": False,
    }


def _format_validation_error(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or "invalid structure"


def _normalize_summary_data(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce common LLM shape mistakes before Pydantic validation."""
    data = dict(raw)

    tldr = data.get("tldr")
    if tldr is not None and not isinstance(tldr, str):
        data["tldr"] = str(tldr)

    key_points = data.get("key_points")
    if isinstance(key_points, str):
        data["key_points"] = [key_points]
    elif isinstance(key_points, list):
        data["key_points"] = [str(p) for p in key_points if p is not None and str(p).strip()]

    tags = data.get("tags")
    if isinstance(tags, str):
        data["tags"] = [t.strip().lower() for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        data["tags"] = [str(t).strip().lower() for t in tags if t is not None and str(t).strip()]

    return data


def _parse_summary(raw: object) -> Summary:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SummarizeError(
                "Claude returned malformed summary JSON.",
                status_code=502,
            ) from exc

    if not isinstance(raw, dict):
        raise SummarizeError(
            "Claude returned an invalid summary structure.",
            status_code=502,
        )

    try:
        return Summary.model_validate(_normalize_summary_data(raw))
    except ValidationError as exc:
        raise SummarizeError(
            f"Claude returned an invalid summary structure: {_format_validation_error(exc)}",
            status_code=502,
        ) from exc


def _tool_block(message: object) -> object | None:
    for block in message.content:
        if block.type == "tool_use" and block.name == "save_summary":
            return block
    return None


async def summarize(content: Content) -> Summary:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Claude's context is large, but there's no need to pay for an entire
    # three-hour transcript on v1. Trim defensively; revisit with map-reduce later.
    body = content.text[:50_000]

    tool = {
        "name": "save_summary",
        "description": "Record the structured summary of the provided content.",
        "input_schema": _summary_tool_schema(),
    }

    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=_MAX_SUMMARY_TOKENS,
            system=_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": "save_summary"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Title: {content.title}\n"
                        f"Source: {content.source_type.value}\n"
                        f"URL: {content.url}\n\n"
                        f"Content:\n{body}"
                    ),
                }
            ],
        )
    except AuthenticationError as exc:
        raise SummarizeError(
            "Invalid Anthropic API key. Check ANTHROPIC_API_KEY in .env.",
            status_code=502,
        ) from exc
    except RateLimitError as exc:
        raise SummarizeError(
            "Claude rate limit reached. Wait a moment and try again.",
            status_code=503,
        ) from exc
    except APITimeoutError as exc:
        raise SummarizeError(
            "Claude request timed out. Try again with shorter content.",
            status_code=504,
        ) from exc
    except APIConnectionError as exc:
        raise SummarizeError(
            "Could not reach Anthropic. Check your network connection.",
            status_code=503,
        ) from exc
    except APIStatusError as exc:
        if exc.status_code in (503, 529):
            raise SummarizeError(
                "Claude is temporarily unavailable. Try again shortly.",
                status_code=503,
            ) from exc
        status_code = 503 if exc.status_code >= 500 else 502
        raise SummarizeError(
            f"Claude rejected the request: {exc.message}",
            status_code=status_code,
        ) from exc

    block = _tool_block(message)
    if block is None:
        raise SummarizeError(
            "Claude did not return a structured summary.",
            status_code=502,
        )

    if message.stop_reason == "max_tokens":
        raise SummarizeError(
            "Claude ran out of space while summarizing. Try a shorter article.",
            status_code=502,
        )

    return _parse_summary(block.input)
