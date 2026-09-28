import unittest

from hotspot_radar.normalize import canonicalize_url, clean_text


class NormalizeTests(unittest.TestCase):
    def test_tracking_parameters_and_fragment_are_removed(self):
        value = canonicalize_url(
            "http://Example.COM/story/?b=2&utm_source=newsletter&a=1#section"
        )
        self.assertEqual(value, "https://example.com/story?a=1&b=2")

    def test_html_and_whitespace_are_cleaned(self):
        self.assertEqual(clean_text("<p>Hello&nbsp;  world</p>"), "Hello world")


if __name__ == "__main__":
    unittest.main()

