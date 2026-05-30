from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Content, SourceType, Summary
from src.summarizer import summarize


def _sample_summary() -> Summary:
    return Summary(
        tldr="Core point.",
        key_points=["First takeaway", "Second takeaway"],
        tags=["ai", "agents"],
    )


@pytest.mark.asyncio
async def test_summarize_youtube_uses_gemini() -> None:
    content = Content(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type=SourceType.YOUTUBE,
        title="Test Video",
        text="",
    )
    expected = _sample_summary()

    with patch(
        "src.summarizer._gemini_summarize_youtube",
        new_callable=AsyncMock,
        return_value=expected,
    ) as gemini_mock, patch(
        "src.summarizer._anthropic_summarize",
        new_callable=AsyncMock,
    ) as anthropic_mock:
        result = await summarize(content)

    assert result == expected
    gemini_mock.assert_awaited_once_with(content)
    anthropic_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_summarize_article_uses_claude() -> None:
    content = Content(
        url="https://example.com/post",
        source_type=SourceType.ARTICLE,
        title="Test Article",
        text="Full article body.",
    )
    expected = _sample_summary()

    with patch(
        "src.summarizer._anthropic_summarize",
        new_callable=AsyncMock,
        return_value=expected,
    ) as anthropic_mock, patch(
        "src.summarizer._gemini_summarize_youtube",
        new_callable=AsyncMock,
    ) as gemini_mock:
        result = await summarize(content)

    assert result == expected
    anthropic_mock.assert_awaited_once_with(content)
    gemini_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_gemini_summarize_youtube_parses_structured_json() -> None:
    from src.summarizer import _gemini_summarize_youtube

    content = Content(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type=SourceType.YOUTUBE,
        title="Test Video",
        text="",
    )
    payload = _sample_summary().model_dump()
    mock_resp = MagicMock(text=json.dumps(payload))

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    with patch("google.genai.Client", return_value=mock_client), patch(
        "src.summarizer.get_settings",
        return_value=MagicMock(
            gemini_api_key="test-key",
            gemini_model="gemini-2.5-flash",
        ),
    ):
        result = await _gemini_summarize_youtube(content)

    assert result == _sample_summary()
    call_kwargs = mock_client.aio.models.generate_content.await_args.kwargs
    assert call_kwargs["config"].response_mime_type == "application/json"
