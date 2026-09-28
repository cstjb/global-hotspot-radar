from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Event


def export_dashboard(events: list[Event], docs_path: str, run: dict) -> Path:
    data_path = Path(docs_path) / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "run": {
            "status": run["status"],
            "articles_fetched": run["articles_fetched"],
            "articles_unique": run["articles_unique"],
            "errors": run.get("errors", []),
        },
        "events": [event.to_dict() for event in events],
    }
    output = data_path / "events.json"
    temporary = data_path / "events.json.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return output

