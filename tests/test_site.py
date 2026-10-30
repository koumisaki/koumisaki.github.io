import unittest

from sitecheck import ROOT, find, find_all, parse, site_files, text


class TestSkeleton(unittest.TestCase):
    def setUp(self):
        self.doc = parse("index.html")

    def test_language_is_english(self):
        self.assertEqual(find(self.doc, "html").attrs.get("lang"), "en")

    def test_title(self):
        self.assertEqual(text(find(self.doc, "title")), "Kou Misaki — Machine learning researcher")

    def test_single_h1_is_name(self):
        h1s = find_all(self.doc, "h1")
        self.assertEqual(len(h1s), 1)
        self.assertEqual(text(h1s[0]), "Kou Misaki")

    def test_viewport_and_charset(self):
        self.assertIsNotNone(find(self.doc, "meta", attr=("charset", "utf-8")))
        self.assertIsNotNone(find(self.doc, "meta", attr=("name", "viewport")))

    def test_stylesheet_linked(self):
        self.assertIsNotNone(find(self.doc, "link", attr=("href", "/style.css")))

    def test_nojekyll_present(self):
        self.assertTrue((ROOT / ".nojekyll").exists())


if __name__ == "__main__":
    unittest.main()
