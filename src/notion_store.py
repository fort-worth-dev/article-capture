from __future__ import annotations

from notion_client import AsyncClient
from notion_client.errors import (
    APIErrorCode,
    APIResponseError,
    HTTPResponseError,
    RequestTimeoutError,
)

from src.config import get_settings
from src.errors import StoreError
from src.models import Content, Summary

# Notion caps a single rich_text content string at 2000 chars; stay under it.
_MAX_TEXT = 1900


def _chunk(text: str, size: int = _MAX_TEXT) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _rich_text(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": c}} for c in _chunk(text)]


def _heading(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _notion_api_error(exc: APIResponseError) -> StoreError:
    if exc.code == APIErrorCode.Unauthorized:
        return StoreError(
            "Invalid Notion API key. Check NOTION_API_KEY in .env.",
            status_code=502,
        )
    if exc.code == APIErrorCode.ObjectNotFound:
        return StoreError(
            "Notion database not found or not shared with your integration. "
            "Check NOTION_DATABASE_ID and database connections.",
            status_code=502,
        )
    if exc.code == APIErrorCode.ValidationError:
        return StoreError(
            f"Notion rejected the page: {exc.message}",
            status_code=422,
        )
    if exc.code == APIErrorCode.RateLimited:
        return StoreError(
            "Notion rate limit reached. Wait a moment and try again.",
            status_code=503,
        )
    if exc.code in (APIErrorCode.ServiceUnavailable, APIErrorCode.GatewayTimeout):
        return StoreError(
            "Notion is temporarily unavailable. Try again shortly.",
            status_code=503,
        )
    if exc.code == APIErrorCode.InternalServerError:
        return StoreError("Notion server error. Try again.", status_code=502)
    return StoreError(f"Notion error: {exc.message}", status_code=502)


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:_MAX_TEXT]}}]
        },
    }


async def store(content: Content, summary: Summary) -> str:
    """Create a Notion page for this summary and return its URL.

    Expects a database whose properties match the names below (see README).
    """
    settings = get_settings()
    notion = AsyncClient(auth=settings.notion_api_key)

    children = [
        _heading("TL;DR"),
        _paragraph(summary.tldr),
        _heading("Key points"),
        *[_bullet(point) for point in summary.key_points],
    ]

    try:
        page = await notion.pages.create(
            parent={"database_id": settings.notion_database_id},
            properties={
                "Name": {"title": [{"text": {"content": content.title[:_MAX_TEXT]}}]},
                "URL": {"url": content.url},
                "Source": {"select": {"name": content.source_type.value}},
                "Tags": {"multi_select": [{"name": tag} for tag in summary.tags]},
            },
            children=children,
        )
    except APIResponseError as exc:
        raise _notion_api_error(exc) from exc
    except RequestTimeoutError as exc:
        raise StoreError(
            "Notion request timed out. Try again.",
            status_code=504,
        ) from exc
    except HTTPResponseError as exc:
        status_code = 503 if exc.status >= 500 else 502
        raise StoreError(
            f"Notion request failed ({exc.status}). Try again.",
            status_code=status_code,
        ) from exc

    return page["url"]
