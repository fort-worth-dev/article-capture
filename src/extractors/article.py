from __future__ import annotations

import asyncio

import trafilatura
from trafilatura.metadata import extract_metadata

from src.extractors.base import ContentExtractor, ExtractionError
from src.models import Content, SourceType


class ArticleExtractor(ContentExtractor):
    """Default extractor: fetch a page and pull clean readable text via trafilatura.

    Also acts as the catch-all fallback for any http(s) URL no other extractor
    claims, so keep it last in the registry.
    """

    def can_handle(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    async def extract(self, url: str) -> Content:
        # trafilatura is synchronous and network-bound; keep it off the event loop.
        return await asyncio.to_thread(self._extract_sync, url)

    def _extract_sync(self, url: str) -> Content:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ExtractionError(f"Could not fetch {url}")

        text = trafilatura.extract(
            downloaded, include_comments=False, include_tables=True
        )
        if not text:
            raise ExtractionError(f"No readable article content found at {url}")

        title, author = url, None
        try:
            meta = extract_metadata(downloaded)
            if meta:
                title = meta.title or title
                author = meta.author
        except Exception:
            pass  # metadata is best-effort; the text is what matters

        return Content(
            url=url,
            source_type=SourceType.ARTICLE,
            title=title,
            text=text,
            author=author,
        )
