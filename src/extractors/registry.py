from __future__ import annotations

from src.extractors.article import ArticleExtractor
from src.extractors.base import ContentExtractor, ExtractionError
from src.extractors.youtube import YouTubeExtractor
from src.models import Content

# Order matters: specific extractors first; ArticleExtractor is the catch-all.
# To add a source (e.g. a podcast or PDF extractor later), implement
# ContentExtractor and drop it into this list above ArticleExtractor.
_EXTRACTORS: list[ContentExtractor] = [
    YouTubeExtractor(),
    ArticleExtractor(),
]


def select_extractor(url: str) -> ContentExtractor:
    for extractor in _EXTRACTORS:
        if extractor.can_handle(url):
            return extractor
    raise ExtractionError(f"No extractor can handle: {url}")


async def extract(url: str) -> Content:
    return await select_extractor(url).extract(url)
