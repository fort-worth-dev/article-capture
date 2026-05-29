from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import Content


class ExtractionError(Exception):
    """Raised when an extractor cannot retrieve usable content."""


class ContentExtractor(ABC):
    """Strategy interface: turn a URL into normalized Content.

    Adding a new source = implement this + register it in registry.py. Nothing
    else in the pipeline changes. Your .NET instinct is exactly right here: this
    is an interface plus a registry doing dependency injection by hand.

    extract() is async because every real implementation does I/O. Sync libraries
    (trafilatura, youtube-transcript-api) get wrapped with asyncio.to_thread so
    they don't block the event loop.
    """

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this extractor knows how to handle the URL."""

    @abstractmethod
    async def extract(self, url: str) -> Content:
        """Fetch and normalize. Raise ExtractionError on any failure."""
