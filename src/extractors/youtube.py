from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx

from src.extractors.base import ContentExtractor, ExtractionError
from src.models import Content, SourceType

_YT_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}


def _video_id(url: str) -> str | None:
    """Pull the video id out of the common YouTube URL shapes."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "youtu.be":
        return parsed.path.lstrip("/").split("/")[0] or None
    if host in _YT_HOSTS:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        for prefix in ("/shorts/", "/embed/", "/v/"):
            if parsed.path.startswith(prefix):
                return parsed.path[len(prefix):].split("/")[0]
    return None


def _watch_url(url: str) -> str:
    """Canonical watch URL — Gemini expects https://www.youtube.com/watch?v=ID."""
    video_id = _video_id(url)
    if not video_id:
        raise ExtractionError(f"Not a recognizable YouTube URL: {url}")
    return f"https://www.youtube.com/watch?v={video_id}"


class YouTubeExtractor(ContentExtractor):
    """Fetch YouTube metadata via oEmbed.

    Summarization happens downstream: Gemini ingests the YouTube URL directly
    in one call (see summarizer.py), so this extractor never touches transcripts.

    (If the YouTube-URL preview ever gets restricted, the fallback is the old
    youtube-transcript-api path behind a Webshare residential proxy.)
    """

    def can_handle(self, url: str) -> bool:
        return _video_id(url) is not None

    async def extract(self, url: str) -> Content:
        if not self.can_handle(url):
            raise ExtractionError(f"Not a recognizable YouTube URL: {url}")

        title, author = await self._fetch_metadata(url)

        return Content(
            url=url,
            source_type=SourceType.YOUTUBE,
            title=title,
            text="",
            author=author,
        )

    @staticmethod
    async def _fetch_metadata(url: str) -> tuple[str, str | None]:
        # oEmbed is a lightweight public endpoint (not the blocked transcript
        # path); best-effort, falls back to the URL as the title.
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://www.youtube.com/oembed",
                    params={"url": url, "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("title", url), data.get("author_name")
        except Exception:
            return url, None
