from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .analysis import EventAnalyzer
from .clustering import cluster_articles
from .config import Settings
from .exporter import export_dashboard
from .models import Article
from .normalize import canonicalize_url, clean_text, deduplicate_articles, parse_datetime, stable_id
from .scoring import rank_events
from .sources import GDELTSource, RSSSource
from .storage import RadarStore


def load_fixture(path: str | Path) -> list[Article]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    articles = []
    for item in payload:
        canonical_url = canonicalize_url(item["url"])
        articles.append(
            Article(
                article_id=stable_id("art", canonical_url),
                url=item["url"],
                canonical_url=canonical_url,
                title=clean_text(item["title"]),
                summary=clean_text(item.get("summary")),
                source=item["source"],
                source_type=item.get("source_type", "fixture"),
                published_at=parse_datetime(item.get("published_at")),
                language=item.get("language", "en"),
                region=item.get("region", "Global"),
                source_weight=float(item.get("source_weight", 0.9)),
                image_url=item.get("image_url"),
            )
        )
    return articles


class RadarPipeline:
    def __init__(self, settings: Settings, fixture: str | None = None):
        self.settings = settings
        self.fixture = fixture

    def _fetch(self) -> tuple[list[Article], list[dict[str, str]]]:
        if self.fixture:
            return load_fixture(self.fixture), []

        articles: list[Article] = []
        errors: list[dict[str, str]] = []
        gdelt = GDELTSource(
            timeout=self.settings.request_timeout_seconds,
            max_records=self.settings.max_articles_per_source,
        )
        for query in self.settings.gdelt_queries:
            try:
                articles.extend(gdelt.fetch([query], self.settings.lookback_hours))
            except Exception as exc:  # A failed source must not stop the remaining radar.
                errors.append({"source": f"GDELT: {query[:45]}", "error": str(exc)[:240]})

        rss = RSSSource(
            timeout=self.settings.request_timeout_seconds,
            max_articles_per_source=self.settings.max_articles_per_source,
        )
        for source in self.settings.sources:
            try:
                articles.extend(rss.fetch([source]))
            except Exception as exc:
                errors.append({"source": source["name"], "error": str(exc)[:240]})
        return articles, errors

    def run(self) -> dict:
        started_at = datetime.now(timezone.utc)
        run_id = stable_id("run", started_at.isoformat())
        articles, errors = self._fetch()
        unique_articles = deduplicate_articles(articles)
        events = cluster_articles(
            unique_articles,
            similarity_threshold=self.settings.cluster_similarity_threshold,
            time_window_hours=self.settings.cluster_time_window_hours,
        )
        ranked_events = rank_events(events, top_n=len(events))
        top_events = ranked_events[: self.settings.top_n]
        analyzer = EventAnalyzer()
        for event in top_events:
            event.analysis = analyzer.analyze(event)

        finished_at = datetime.now(timezone.utc)
        status = (
            "failed" if not self.fixture and not unique_articles
            else "partial" if errors
            else "success"
        )
        run = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "articles_fetched": len(articles),
            "articles_unique": len(unique_articles),
            "events_built": len(ranked_events),
            "errors": errors,
        }
        with RadarStore(self.settings.database_path) as store:
            store.upsert_articles(unique_articles)
            store.upsert_events(ranked_events)
            store.record_run(run)
        output = Path(self.settings.docs_path) / "data" / "events.json"
        if status != "failed":
            output = export_dashboard(top_events, self.settings.docs_path, run)
        return {**run, "output": str(output), "events": top_events}
