import unittest

from sitecheck import ROOT, find, find_all, parse, site_files, text


def jpeg_info(path):
    """Return (width, height, has_exif) by walking JPEG segments."""
    data = path.read_bytes()
    i, width, height, has_exif = 2, None, None, False
    while i < len(data) - 4:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
            has_exif = True
        if marker in (0xC0, 0xC2):
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
        if marker == 0xDA:
            break
        i += 2 + length
    return width, height, has_exif


def text_of_scripts(doc):
    return ["".join(c for c in s.children if isinstance(c, str)) for s in find_all(doc, "script")]


PAPERS = [
    ("2602.04344", True, "ICML 2026", [], ["https://pub.sakana.ai/umf/"]),
    ("2510.21150", True, "ICLR 2026", [], ["https://pub.sakana.ai/ssot/"]),
    ("2509.21862", False, "ALIFE 2026", ["https://github.com/SakanaAI/shachi"], []),
    ("2503.04412", True, "NeurIPS 2025 · Spotlight", ["https://github.com/SakanaAI/treequest"], ["https://sakana.ai/ab-mcts/"]),
    ("2501.16937", False, "ICLR 2025 · Spotlight", ["https://github.com/SakanaAI/TAID"], ["https://sakana.ai/taid/"]),
]


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


class TestIntro(unittest.TestCase):
    def setUp(self):
        self.doc = parse("index.html")
        self.intro = find(self.doc, "header", cls="intro")

    def test_tagline(self):
        self.assertEqual(text(find(self.intro, "p", cls="tagline")),
                         "Machine learning researcher · inference-time scaling for LLMs")

    def test_bio_covers_career(self):
        bio = text(find(self.intro, "p", cls="bio"))
        for phrase in ["I'm a Research Engineer at Sakana AI", "UnMaskFork (ICML 2026)",
                       "String Seed of Thought (ICLR 2026)", "AB-MCTS (NeurIPS 2025 Spotlight)",
                       "TAID (ICLR 2025 Spotlight)", "Japanese Siri at Apple", "Recruit",
                       "theoretical condensed-matter physics from the University of Tokyo"]:
            self.assertIn(phrase, bio)

    def test_profile_links(self):
        hrefs = [a.attrs.get("href") for a in find_all(find(self.intro, "ul", cls="links"), "a")]
        for url in ["https://scholar.google.com/citations?user=8kL-3m4AAAAJ",
                    "https://github.com/takkyu2", "https://x.com/takkyuO2",
                    "https://www.linkedin.com/in/kou-misaki/"]:
            self.assertIn(url, hrefs)

    def test_email_is_assembled_by_script(self):
        a = find(self.intro, "a", cls="email")
        self.assertEqual(a.attrs.get("data-user"), "mk940se")
        self.assertEqual(a.attrs.get("data-domain"), "gmail.com")
        script = " ".join(text_of_scripts(self.doc))
        self.assertIn("mailto:", script)
        self.assertIn("data-user", script)

    def test_email_noscript_fallback(self):
        self.assertIn("mk940se [at] gmail.com", text(find(self.intro, "noscript")))

    def test_no_plaintext_email_anywhere(self):
        for path in site_files():
            if path.suffix in {".html", ".css", ".xml", ".txt", ".md"}:
                self.assertNotIn("mk940se" + "@" + "gmail.com", path.read_text(encoding="utf-8"), path)

    def test_portrait_markup(self):
        img = find(self.intro, "img", cls="portrait")
        self.assertEqual(img.attrs.get("src"), "/images/portrait.jpg")
        self.assertEqual((img.attrs.get("width"), img.attrs.get("height")), ("160", "160"))
        self.assertTrue(img.attrs.get("alt"))

    def test_portrait_file_is_small_square_and_clean(self):
        path = ROOT / "images" / "portrait.jpg"
        width, height, has_exif = jpeg_info(path)
        self.assertEqual((width, height), (400, 400))
        self.assertFalse(has_exif)
        self.assertLess(path.stat().st_size, 60_000)


class TestResearch(unittest.TestCase):
    def test_research_paragraph(self):
        section = find(parse("index.html"), "section", attr=("id", "research"))
        self.assertEqual(text(find(section, "h2")), "Research")
        body = text(find(section, "p"))
        for phrase in ["inference-time compute", "search", "diverse", "reasoning"]:
            self.assertIn(phrase, body)


class TestPublications(unittest.TestCase):
    def setUp(self):
        self.section = find(parse("index.html"), "section", attr=("id", "publications"))
        self.papers = find_all(self.section, "li", cls="paper")

    def test_order(self):
        self.assertEqual([p.attrs.get("data-arxiv") for p in self.papers], [p[0] for p in PAPERS])

    def test_each_paper(self):
        for li, (arxiv, first, venue, code, blog) in zip(self.papers, PAPERS):
            with self.subTest(arxiv=arxiv):
                abs_url = f"https://arxiv.org/abs/{arxiv}"
                self.assertEqual(find(li, "a", cls="paper-title").attrs.get("href"), abs_url)
                self.assertEqual([text(s) for s in find_all(find(li, "p", cls="authors"), "strong")], ["Kou Misaki"])
                self.assertEqual(text(find(li, "p", cls="venue")), venue)
                self.assertEqual("first-author" in li.classes, first)
                tldr = find(li, "p", cls="tldr")
                self.assertEqual(tldr is not None and bool(text(tldr)), first)
                links = [a.attrs.get("href") for a in find_all(find(li, "p", cls="paper-links"), "a")]
                self.assertEqual(links, [abs_url] + code + blog)

    def test_equal_contribution(self):
        authors = text(find(self.papers[3], "p", cls="authors"))
        self.assertIn("Yuichi Inoue*", authors)
        self.assertIn("Kou Misaki*", authors)
        legend = text(find(self.section, "p", cls="legend"))
        self.assertIn("* Equal contribution", legend)

    def test_scholar_full_list_link(self):
        legend = find(self.section, "p", cls="legend")
        self.assertIn("https://scholar.google.com/citations?user=8kL-3m4AAAAJ",
                      [a.attrs.get("href") for a in find_all(legend, "a")])

    def test_no_openreview_links(self):
        self.assertNotIn("openreview.net", (ROOT / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
