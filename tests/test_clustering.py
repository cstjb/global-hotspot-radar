import unittest
from datetime import datetime, timezone

from hotspot_radar.clustering import cluster_articles
from hotspot_radar.models import Article
from hotspot_radar.normalize import stable_id


def make_article(url, title, summary, source):
    return Article(
        article_id=stable_id("art", url),
        url=url,
        canonical_url=url,
        title=title,
        summary=summary,
        source=source,
        source_type="test",
        published_at=datetime.now(timezone.utc),
        region="Test",
    )


class ClusteringTests(unittest.TestCase):
    def test_similar_stories_form_one_event(self):
        articles = [
            make_article(
                "https://a.test/1",
                "Federal Reserve holds interest rates steady",
                "The central bank held interest rates steady after inflation cooled",
                "A",
            ),
            make_article(
                "https://b.test/2",
                "Fed keeps rates steady as inflation cools",
                "Federal Reserve officials kept interest rates unchanged",
                "B",
            ),
            make_article(
                "https://c.test/3",
                "Powerful earthquake triggers major rescue operation",
                "Emergency teams searched damaged buildings after the earthquake",
                "C",
            ),
        ]
        events = cluster_articles(articles, similarity_threshold=0.28)
        sizes = sorted(len(event.articles) for event in events)
        self.assertEqual(sizes, [1, 2])
        financial = max(events, key=lambda event: len(event.articles))
        self.assertEqual(financial.category, "经济金融")

    def test_substrings_do_not_create_false_military_category(self):
        articles = [
            make_article(
                "https://culture.test/awards",
                "Stars arrive for the music awards red carpet",
                "Actors and musicians celebrated the annual awards ceremony",
                "Culture",
            )
        ]
        self.assertEqual(cluster_articles(articles), [])


if __name__ == "__main__":
    unittest.main()
