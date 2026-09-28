from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dateutil import parser as date_parser


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme in {"http", "https"} else parts.scheme
    host = (parts.hostname or "").lower()
    port = f":{parts.port}" if parts.port and parts.port not in {80, 443} else ""
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=False)
            if key.lower() not in TRACKING_PARAMETERS and not key.lower().startswith("utm_")
        )
    )
    return urlunsplit((scheme, f"{host}{port}", path, query, ""))


def stable_id(prefix: str, value: str, length: int = 20) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def parse_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError, OverflowError):
            parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def deduplicate_articles(articles):
    """Keep the richest/newest representation for each canonical URL."""
    selected = {}
    for article in articles:
        current = selected.get(article.canonical_url)
        if current is None:
            selected[article.canonical_url] = article
            continue
        current_quality = len(current.title) + len(current.summary)
        candidate_quality = len(article.title) + len(article.summary)
        if candidate_quality > current_quality or article.published_at > current.published_at:
            selected[article.canonical_url] = article
    return sorted(selected.values(), key=lambda item: item.published_at, reverse=True)

