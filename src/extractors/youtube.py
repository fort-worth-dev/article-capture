from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx

from src.extractors.base import ContentExtractor, ExtractionError
from src.models import Content, SourceType

_YT_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}


def _video_id(url: str) -> str | None:
    """Pull the 11-char video id out of the common YouTube URL shapes."""
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


class YouTubeExtractor(ContentExtractor):
    """Pull the transcript (not the page HTML) for a YouTube video.

    Transcript comes from youtube-transcript-api's 1.x instance API; title/author
    come from YouTube's lightweight oEmbed endpoint. Videos without captions raise
    ExtractionError -- that's expected and handled gracefully upstream.
    """

    def can_handle(self, url: str) -> bool:
        return _video_id(url) is not None

    async def extract(self, url: str) -> Content:
        vid = _video_id(url)
        if not vid:
            raise ExtractionError(f"Not a recognizable YouTube URL: {url}")

        transcript = await asyncio.to_thread(self._fetch_transcript, vid)
        title, author = await self._fetch_metadata(url)

        return Content(
            url=url,
            source_type=SourceType.YOUTUBE,
            title=title,
            text=transcript,
            author=author,
        )

    @staticmethod
    def _fetch_transcript(video_id: str) -> str:
        # Imported lazily so the module stays import-safe even if the dep shifts.
        from youtube_transcript_api import YouTubeTranscriptApi

        try:
            fetched = YouTubeTranscriptApi().fetch(video_id)
        except Exception as exc:
            # Most common cause: captions disabled or none available.
            raise ExtractionError(
                f"Could not get a transcript for video {video_id} "
                f"(captions may be disabled): {exc}"
            ) from exc

        text = " ".join(snippet.text for snippet in fetched).strip()
        if not text:
            raise ExtractionError(f"Empty transcript for video {video_id}")
        return text

    @staticmethod
    async def _fetch_metadata(url: str) -> tuple[str, str | None]:
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
            return url, None  # metadata is best-effort
