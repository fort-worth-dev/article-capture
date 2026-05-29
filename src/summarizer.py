from __future__ import annotations

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

# Deriving the tool schema straight from the Pydantic model and forcing the model
# to call it is the reliable way to get structured output. It is also the exact
# pattern you will reuse when these functions become real agent tools later --
# a tool is just a JSON schema plus a handler.
_TOOL = {
    "name": "save_summary",
    "description": "Record the structured summary of the provided content.",
    "input_schema": Summary.model_json_schema(),
}


async def summarize(content: Content) -> Summary:
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Claude's context is large, but there's no need to pay for an entire
    # three-hour transcript on v1. Trim defensively; revisit with map-reduce later.
    body = content.text[:50_000]

    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=_SYSTEM,
            tools=[_TOOL],
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

    for block in message.content:
        if block.type == "tool_use" and block.name == "save_summary":
            try:
                return Summary.model_validate(block.input)
            except ValidationError as exc:
                raise SummarizeError(
                    "Claude returned an invalid summary structure.",
                    status_code=502,
                ) from exc

    raise SummarizeError(
        "Claude did not return a structured summary.",
        status_code=502,
    )
