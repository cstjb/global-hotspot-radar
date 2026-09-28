from __future__ import annotations

import math
from datetime import datetime, timezone

from .models import Event


CATEGORY_IMPACT = {
    "军事安全": 1.0,
    "国际政治": 0.85,
    "经济金融": 0.9,
    "科技AI": 0.75,
    "能源资源": 0.85,
    "产业供应链": 0.8,
    "社会突发": 0.9,
}


def score_event(event: Event, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    age_hours = max((now - event.last_updated).total_seconds() / 3600, 0)

    coverage = min(math.log2(len(event.articles) + 1) / math.log2(9), 1.0)
    source_diversity = min(len(event.sources) / 5, 1.0)
    region_diversity = min(len(event.regions) / 4, 1.0)
    recency = math.exp(-age_hours / 24)
    credibility = sum(article.source_weight for article in event.articles) / len(event.articles)
    impact = CATEGORY_IMPACT.get(event.category, 0.7)
    span_hours = max((event.last_updated - event.first_seen).total_seconds() / 3600, 1)
    velocity = min(len(event.articles) / max(span_hours, 3) * 3, 1.0)

    components = {
        "coverage": coverage * 22,
        "source_diversity": source_diversity * 18,
        "region_diversity": region_diversity * 10,
        "recency": recency * 22,
        "credibility": credibility * 10,
        "impact": impact * 13,
        "velocity": velocity * 5,
    }
    event.score_breakdown = {key: round(value, 1) for key, value in components.items()}
    event.score = round(min(sum(components.values()), 100.0), 1)
    return event.score


def rank_events(events: list[Event], top_n: int = 10) -> list[Event]:
    for event in events:
        score_event(event)
    return sorted(events, key=lambda item: (item.score, item.last_updated), reverse=True)[:top_n]

