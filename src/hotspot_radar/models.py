from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Article:
    article_id: str
    url: str
    canonical_url: str
    title: str
    summary: str
    source: str
    source_type: str
    published_at: datetime
    fetched_at: datetime = field(default_factory=utc_now)
    language: str = "en"
    region: str = "Global"
    source_weight: float = 0.8
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("raw", None)
        value["published_at"] = self.published_at.isoformat()
        value["fetched_at"] = self.fetched_at.isoformat()
        return value


@dataclass(slots=True)
class Event:
    event_id: str
    title: str
    category: str
    articles: list[Article]
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=utc_now)
    last_updated: datetime = field(default_factory=utc_now)
    analysis: dict[str, Any] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        return sorted({article.source for article in self.articles})

    @property
    def regions(self) -> list[str]:
        return sorted({article.region for article in self.articles})

    def to_dict(self, include_articles: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "event_id": self.event_id,
            "title": self.title,
            "category": self.category,
            "score": round(self.score, 1),
            "score_breakdown": self.score_breakdown,
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "source_count": len(self.sources),
            "article_count": len(self.articles),
            "sources": self.sources,
            "regions": self.regions,
            "keywords": self.keywords,
            "analysis": self.analysis,
        }
        if include_articles:
            value["articles"] = [article.to_dict() for article in self.articles]
        return value

