from __future__ import annotations

import math
import re
from collections import Counter
from datetime import timedelta

from .classifier import classify_articles
from .models import Article, Event
from .normalize import stable_id


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "has", "have", "he", "her", "his", "how", "in", "into", "is", "it",
    "its", "new", "news", "of", "on", "or", "says", "she", "that", "the", "their",
    "this", "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "world", "after", "over", "amid", "latest", "live", "update",
}


def tokenize(text: str) -> list[str]:
    latin = [
        token for token in re.findall(r"[a-z][a-z0-9'-]{2,}", text.lower())
        if token not in STOP_WORDS
    ]
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    cjk = []
    for chunk in cjk_chunks:
        cjk.extend(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return latin + cjk


def _term_vector(article: Article) -> Counter[str]:
    title_terms = tokenize(article.title)
    summary_terms = tokenize(article.summary)
    vector = Counter(summary_terms)
    vector.update({term: count * 2.5 for term, count in Counter(title_terms).items()})
    return vector


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    shared = left.keys() & right.keys()
    numerator = sum(left[key] * right[key] for key in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _cluster_vector(articles: list[Article]) -> Counter[str]:
    combined: Counter[str] = Counter()
    for article in articles:
        combined.update(_term_vector(article))
    scale = max(len(articles), 1)
    return Counter({key: value / scale for key, value in combined.items()})


def cluster_articles(
    articles: list[Article], similarity_threshold: float = 0.34, time_window_hours: int = 36
) -> list[Event]:
    clusters: list[list[Article]] = []
    vectors: list[Counter[str]] = []
    window = timedelta(hours=time_window_hours)

    for article in sorted(articles, key=lambda item: item.published_at):
        article_vector = _term_vector(article)
        best_index = -1
        best_similarity = 0.0
        for index, cluster in enumerate(clusters):
            if article.published_at - max(item.published_at for item in cluster) > window:
                continue
            similarity = cosine_similarity(article_vector, vectors[index])
            # Shared named terms protect short breaking-news headlines from under-clustering.
            named_overlap = set(tokenize(article.title)) & {
                term for item in cluster for term in tokenize(item.title)
            }
            adjusted = similarity + min(len(named_overlap), 3) * 0.025
            if adjusted > best_similarity:
                best_similarity = adjusted
                best_index = index
        if best_index >= 0 and best_similarity >= similarity_threshold:
            clusters[best_index].append(article)
            vectors[best_index] = _cluster_vector(clusters[best_index])
        else:
            clusters.append([article])
            vectors.append(article_vector)

    events: list[Event] = []
    for cluster in clusters:
        category, category_scores = classify_articles(cluster)
        # RSS feeds contain culture, sport and lifestyle items. Keep the radar focused
        # on the seven explicitly supported global-impact categories.
        if max(category_scores.values(), default=0) == 0:
            continue
        representative = max(
            cluster,
            key=lambda item: (item.source_weight, len(item.title), item.published_at),
        )
        frequencies = Counter(
            term for item in cluster for term in tokenize(f"{item.title} {item.summary}")
        )
        keywords = [term for term, _ in frequencies.most_common(8)]
        # The oldest article is a stable anchor as a developing event gains newer coverage.
        identity = min(cluster, key=lambda item: item.published_at).article_id
        events.append(
            Event(
                event_id=stable_id("evt", identity),
                title=representative.title,
                category=category,
                articles=sorted(cluster, key=lambda item: item.published_at, reverse=True),
                first_seen=min(item.published_at for item in cluster),
                last_updated=max(item.published_at for item in cluster),
                keywords=keywords,
            )
        )
    return events
