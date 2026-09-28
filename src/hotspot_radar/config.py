from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Settings:
    lookback_hours: int = 48
    max_articles_per_source: int = 50
    request_timeout_seconds: int = 20
    cluster_similarity_threshold: float = 0.34
    cluster_time_window_hours: int = 36
    top_n: int = 10
    database_path: str = "data/hotspots.duckdb"
    docs_path: str = "docs"
    language: str = "zh-CN"
    gdelt_queries: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, config_dir: str | Path = "config") -> "Settings":
        config_dir = Path(config_dir)
        settings_data = json.loads((config_dir / "settings.json").read_text(encoding="utf-8"))
        settings_data["sources"] = json.loads(
            (config_dir / "sources.json").read_text(encoding="utf-8")
        )
        settings_data["database_path"] = os.getenv(
            "RADAR_DATABASE", settings_data["database_path"]
        )
        settings_data["top_n"] = int(os.getenv("RADAR_TOP_N", settings_data["top_n"]))
        settings_data["lookback_hours"] = int(
            os.getenv("RADAR_LOOKBACK_HOURS", settings_data["lookback_hours"])
        )
        return cls(**settings_data)

