import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import duckdb

from hotspot_radar.config import Settings
from hotspot_radar.pipeline import RadarPipeline


class PipelineTests(unittest.TestCase):
    def test_fixture_pipeline_writes_database_and_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = replace(
                Settings.load("config"),
                database_path=str(base / "radar.duckdb"),
                docs_path=str(base / "docs"),
            )
            result = RadarPipeline(settings, fixture="tests/fixtures/articles.json").run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["articles_fetched"], 12)
            self.assertEqual(result["articles_unique"], 11)
            self.assertGreaterEqual(result["events_built"], 4)

            payload = json.loads((base / "docs/data/events.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["event_count"], result["events_built"])
            required = {
                "what_happened", "why_important", "participants", "latest_progress",
                "china_impact", "market_impact", "watch_indicators",
            }
            self.assertTrue(required.issubset(payload["events"][0]["analysis"]))

            connection = duckdb.connect(str(base / "radar.duckdb"), read_only=True)
            self.assertEqual(connection.execute("SELECT count(*) FROM articles").fetchone()[0], 11)
            self.assertEqual(connection.execute("SELECT count(*) FROM run_history").fetchone()[0], 1)
            connection.close()

    def test_all_sources_can_fail_without_crashing_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = replace(
                Settings.load("config"),
                database_path=str(base / "empty.duckdb"),
                docs_path=str(base / "docs"),
            )
            empty_fixture = base / "empty.json"
            empty_fixture.write_text("[]", encoding="utf-8")
            result = RadarPipeline(settings, fixture=str(empty_fixture)).run()
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["events_built"], 0)
            payload = json.loads((base / "docs/data/events.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["events"], [])

    def test_live_source_failure_keeps_previous_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = replace(
                Settings.load("config"),
                database_path=str(base / "radar.duckdb"),
                docs_path=str(base / "docs"),
            )
            old_output = base / "docs/data/events.json"
            old_output.parent.mkdir(parents=True)
            old_output.write_text('{"events":[{"event_id":"previous"}]}', encoding="utf-8")
            with patch.object(
                RadarPipeline,
                "_fetch",
                return_value=([], [{"source": "GDELT", "error": "429"}]),
            ):
                result = RadarPipeline(settings).run()
            self.assertEqual(result["status"], "failed")
            self.assertIn("previous", old_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
