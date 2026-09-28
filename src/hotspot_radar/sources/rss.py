from __future__ import annotations

from typing import Any

import feedparser

from ..http import resilient_session
from ..models import Article
from ..normalize import canonicalize_url, clean_text, parse_datetime, stable_id


class RSSSource:
    def __init__(self, timeout: int = 20, max_articles_per_source: int = 50):
        self.timeout = timeout
        self.max_articles_per_source = max_articles_per_source
        self.session = resilient_session()

    def fetch(self, sources: list[dict[str, Any]]) -> list[Article]:
        articles: list[Article] = []
        for source in sources:
            response = self.session.get(
                source["url"],
                timeout=self.timeout,
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, "bozo", False) and not feed.entries:
                raise ValueError(f"Invalid RSS response from {source['name']}")
            for entry in feed.entries[: self.max_articles_per_source]:
                article = self._parse(entry, source)
                if article:
                    articles.append(article)
        return articles

    @staticmethod
    def _parse(entry: Any, source: dict[str, Any]) -> Article | None:
        url = clean_text(entry.get("link"))
        title = clean_text(entry.get("title"))
        if not url or not title:
            return None
        canonical_url = canonicalize_url(url)
        published = entry.get("published") or entry.get("updated")
        image_url = None
        media = entry.get("media_content") or entry.get("media_thumbnail") or []
        if media and isinstance(media, list):
            image_url = media[0].get("url")
        return Article(
            article_id=stable_id("art", canonical_url),
            url=url,
            canonical_url=canonical_url,
            title=title,
            summary=clean_text(entry.get("summary") or entry.get("description")),
            source=source["name"],
            source_type="rss",
            published_at=parse_datetime(published),
            language=source.get("language", "unknown"),
            region=source.get("region", "Global"),
            source_weight=float(source.get("weight", 0.9)),
            image_url=image_url,
            raw=dict(entry),
        )
