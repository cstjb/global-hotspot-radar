from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .models import Article, Event


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    article_id VARCHAR PRIMARY KEY,
    canonical_url VARCHAR UNIQUE NOT NULL,
    url VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    summary VARCHAR,
    source VARCHAR,
    source_type VARCHAR,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ,
    language VARCHAR,
    region VARCHAR,
    source_weight DOUBLE,
    image_url VARCHAR
);

CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    score DOUBLE,
    score_breakdown JSON,
    first_seen TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    analysis JSON,
    keywords JSON,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_articles (
    event_id VARCHAR NOT NULL,
    article_id VARCHAR NOT NULL,
    linked_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (event_id, article_id)
);

CREATE TABLE IF NOT EXISTS run_history (
    run_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR,
    articles_fetched INTEGER,
    articles_unique INTEGER,
    events_built INTEGER,
    errors JSON
);
"""


class RadarStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(self.path))
        self.connection.execute(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "RadarStore":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def upsert_articles(self, articles: list[Article]) -> None:
        values = [
            (
                item.article_id, item.canonical_url, item.url, item.title, item.summary,
                item.source, item.source_type, item.published_at, item.fetched_at,
                item.language, item.region, item.source_weight, item.image_url,
            )
            for item in articles
        ]
        if not values:
            return
        self.connection.executemany(
            """
            INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (article_id) DO UPDATE SET
                canonical_url = excluded.canonical_url,
                url = excluded.url,
                title = excluded.title,
                summary = excluded.summary,
                source = excluded.source,
                source_type = excluded.source_type,
                published_at = excluded.published_at,
                fetched_at = excluded.fetched_at,
                language = excluded.language,
                region = excluded.region,
                source_weight = excluded.source_weight,
                image_url = excluded.image_url
            """,
            values,
        )

    def upsert_events(self, events: list[Event]) -> None:
        event_values = [
            (
                event.event_id, event.title, event.category, event.score,
                json.dumps(event.score_breakdown, ensure_ascii=False), event.first_seen,
                event.last_updated, json.dumps(event.analysis, ensure_ascii=False),
                json.dumps(event.keywords, ensure_ascii=False),
            )
            for event in events
        ]
        if not event_values:
            return
        self.connection.executemany(
            """
            INSERT INTO events (
                event_id, title, category, score, score_breakdown, first_seen,
                last_updated, analysis, keywords
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO UPDATE SET
                title = excluded.title, category = excluded.category, score = excluded.score,
                score_breakdown = excluded.score_breakdown, first_seen = excluded.first_seen,
                last_updated = excluded.last_updated,
                analysis = CASE
                    WHEN excluded.analysis::VARCHAR = '{}' THEN events.analysis
                    ELSE excluded.analysis
                END,
                keywords = excluded.keywords, updated_at = now()
            """,
            event_values,
        )
        links = [(event.event_id, item.article_id) for event in events for item in event.articles]
        self.connection.executemany(
            "INSERT OR IGNORE INTO event_articles (event_id, article_id) VALUES (?, ?)", links
        )

    def record_run(self, run: dict) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO run_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run["run_id"], run["started_at"], run["finished_at"], run["status"],
                run["articles_fetched"], run["articles_unique"], run["events_built"],
                json.dumps(run.get("errors", []), ensure_ascii=False),
            ],
        )
