from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..http import resilient_session
from ..models import Article
from ..normalize import canonicalize_url, clean_text, parse_datetime, stable_id


class GDELTSource:
    """Fetch recent global coverage from the GDELT DOC 2.0 API."""

    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout: int = 20, max_records: int = 100):
        self.timeout = timeout
        self.max_records = min(max(max_records, 1), 250)
        self.session = resilient_session()

    def fetch(self, queries: list[str], lookback_hours: int = 48) -> list[Article]:
        articles: list[Article] = []
        for query in queries:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": self.max_records,
                "format": "json",
                "sort": "HybridRel",
                "startdatetime": (
                    datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
                ).strftime("%Y%m%d%H%M%S"),
                "enddatetime": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            }
            response = self.session.get(
                self.endpoint,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            for item in payload.get("articles", []):
                article = self._parse(item)
                if article:
                    articles.append(article)
        return articles

    @staticmethod
    def _parse(item: dict[str, Any]) -> Article | None:
        url = clean_text(item.get("url"))
        title = clean_text(item.get("title"))
        if not url or not title:
            return None
        canonical_url = canonicalize_url(url)
        domain = clean_text(item.get("domain")) or "GDELT source"
        published = parse_datetime(item.get("seendate"))
        return Article(
            article_id=stable_id("art", canonical_url),
            url=url,
            canonical_url=canonical_url,
            title=title,
            summary=clean_text(item.get("socialimage_alt") or item.get("description")),
            source=domain,
            source_type="gdelt",
            published_at=published,
            language=clean_text(item.get("language")) or "unknown",
            region=clean_text(item.get("sourcecountry")) or "Global",
            source_weight=0.75,
            image_url=item.get("socialimage") or None,
            raw=item,
        )
