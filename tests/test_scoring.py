import unittest
from datetime import datetime, timezone

from hotspot_radar.models import Article, Event
from hotspot_radar.scoring import score_event


class ScoringTests(unittest.TestCase):
    def test_score_is_bounded_and_has_explainable_components(self):
        now = datetime.now(timezone.utc)
        articles = [
            Article(
                article_id=f"a{index}", url=f"https://example.com/{index}",
                canonical_url=f"https://example.com/{index}", title="Conflict update",
                summary="Security conflict ceasefire update", source=f"Source {index}",
                source_type="test", published_at=now, region=f"Region {index}",
                source_weight=0.9,
            )
            for index in range(4)
        ]
        event = Event(
            event_id="event", title="Conflict update", category="军事安全",
            articles=articles, first_seen=now, last_updated=now,
        )
        score = score_event(event, now=now)
        self.assertGreater(score, 70)
        self.assertLessEqual(score, 100)
        self.assertEqual(
            set(event.score_breakdown),
            {"coverage", "source_diversity", "region_diversity", "recency", "credibility", "impact", "velocity"},
        )


if __name__ == "__main__":
    unittest.main()

