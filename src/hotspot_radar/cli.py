from __future__ import annotations

import argparse
import json
from dataclasses import replace

from .config import Settings
from .pipeline import RadarPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Global Hotspot Radar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Fetch, cluster, score, store and export events")
    run.add_argument("--config-dir", default="config")
    run.add_argument("--fixture", help="Use a local JSON fixture instead of the network")
    run.add_argument("--database", help="Override the DuckDB path")
    run.add_argument("--docs", help="Override the static dashboard directory")
    run.add_argument("--top-n", type=int, help="Override number of ranked events")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.load(args.config_dir)
    if args.database:
        settings = replace(settings, database_path=args.database)
    if args.docs:
        settings = replace(settings, docs_path=args.docs)
    if args.top_n:
        settings = replace(settings, top_n=args.top_n)
    result = RadarPipeline(settings, fixture=args.fixture).run()
    print(
        json.dumps(
            {
                "status": result["status"],
                "articles_fetched": result["articles_fetched"],
                "articles_unique": result["articles_unique"],
                "events_built": result["events_built"],
                "output": result["output"],
                "errors": result["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
