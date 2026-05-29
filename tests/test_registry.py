"""Routing tests for the extractor registry. No network required -- these only
exercise can_handle(), which is the kind of fast, deterministic test you want
lots of. (The actual fetching gets covered later with recorded fixtures.)"""

from src.extractors.article import ArticleExtractor
from src.extractors.registry import select_extractor
from src.extractors.youtube import YouTubeExtractor


def test_youtube_watch_url_selects_youtube():
    chosen = select_extractor("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert isinstance(chosen, YouTubeExtractor)


def test_youtu_be_short_url_selects_youtube():
    chosen = select_extractor("https://youtu.be/dQw4w9WgXcQ")
    assert isinstance(chosen, YouTubeExtractor)


def test_youtube_shorts_url_selects_youtube():
    chosen = select_extractor("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert isinstance(chosen, YouTubeExtractor)


def test_plain_article_falls_back_to_article():
    chosen = select_extractor("https://example.com/some/post")
    assert isinstance(chosen, ArticleExtractor)
