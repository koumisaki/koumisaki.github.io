import json
import re
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


def css_tokens(css, block_start):
    start = css.index(block_start)
    block = css[start:css.index("}", start)]
    return dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-fA-F]{6})", block))


def contrast(a, b):
    def lum(h):
        cs = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        cs = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in cs]
        return 0.2126 * cs[0] + 0.7152 * cs[1] + 0.0722 * cs[2]
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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

    def test_email_address_shown_as_link_text(self):
        script = " ".join(text_of_scripts(self.doc))
        self.assertIn("textContent", script)

    def test_email_noscript_fallback(self):
        self.assertIn("mk940se [at] gmail.com", text(find(self.intro, "noscript")))

    def test_no_plaintext_email_anywhere(self):
        address = ("mk940se" + "@" + "gmail.com").encode()
        for path in site_files():
            self.assertNotIn(address, path.read_bytes(), path)

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


class TestStyle(unittest.TestCase):
    def setUp(self):
        self.css = (ROOT / "style.css").read_text(encoding="utf-8")

    def test_contrast_ratios(self):
        light = css_tokens(self.css, ":root {")
        dark = css_tokens(self.css, "@media (prefers-color-scheme: dark)")
        for name, tokens in [("light", light), ("dark", dark)]:
            for key in ["--text", "--text-secondary", "--accent"]:
                with self.subTest(mode=name, token=key):
                    self.assertGreaterEqual(contrast(tokens[key], tokens["--bg"]), 4.5)

    def test_font_fallbacks(self):
        self.assertRegex(self.css, r"--font-serif:[^;]*Newsreader[^;]*,\s*serif;")
        self.assertRegex(self.css, r"--font-sans:[^;]*Inter[^;]*,\s*sans-serif;")

    def test_layout_width(self):
        self.assertIn("max-width: 720px", self.css)

    def test_long_titles_wrap(self):
        self.assertRegex(self.css, r"\.paper-title\s*\{[^}]*overflow-wrap:\s*anywhere")

    def test_mobile_layout_puts_photo_on_top(self):
        self.assertRegex(self.css, r"@media \(max-width: 600px\)[\s\S]*\.intro\s*\{[^}]*flex-direction:\s*column-reverse")

    def test_fonts_loaded_and_footer(self):
        doc = parse("index.html")
        hrefs = [l.attrs.get("href", "") for l in find_all(doc, "link")]
        self.assertTrue(any("fonts.googleapis.com/css2" in h and "Newsreader" in h and "Inter" in h for h in hrefs))
        self.assertEqual(text(find(doc, "footer", cls="footer")), "Last updated: October 2026")


SAME_AS = [
    "https://scholar.google.com/citations?user=8kL-3m4AAAAJ",
    "https://github.com/takkyu2",
    "https://x.com/takkyuO2",
    "https://www.linkedin.com/in/kou-misaki/",
]


class TestSeo(unittest.TestCase):
    def setUp(self):
        self.doc = parse("index.html")

    def meta(self, attr, value):
        node = find(self.doc, "meta", attr=(attr, value))
        return node.attrs.get("content") if node else None

    def test_description_and_canonical(self):
        desc = self.meta("name", "description")
        self.assertTrue(desc and 50 <= len(desc) <= 160, desc)
        self.assertIsNotNone(find(self.doc, "link", attr=("rel", "canonical")))
        self.assertEqual(find(self.doc, "link", attr=("rel", "canonical")).attrs["href"], "https://koumisaki.com/")

    def test_open_graph_and_card(self):
        self.assertEqual(self.meta("property", "og:type"), "profile")
        self.assertEqual(self.meta("property", "og:url"), "https://koumisaki.com/")
        self.assertEqual(self.meta("property", "og:image"), "https://koumisaki.com/images/portrait.jpg")
        self.assertTrue(self.meta("property", "og:title"))
        self.assertTrue(self.meta("property", "og:description"))
        self.assertEqual(self.meta("name", "twitter:card"), "summary")

    def test_json_ld(self):
        blocks = [s for s in find_all(self.doc, "script", attr=("type", "application/ld+json"))]
        self.assertEqual(len(blocks), 1)
        data = json.loads("".join(c for c in blocks[0].children if isinstance(c, str)))
        self.assertEqual(data["@type"], "ProfilePage")
        person = data["mainEntity"]
        self.assertEqual(person["@type"], "Person")
        self.assertEqual(person["name"], "Kou Misaki")
        self.assertEqual(person["alternateName"], "三崎 航")
        self.assertEqual(person["url"], "https://koumisaki.com/")
        self.assertEqual(person["worksFor"]["name"], "Sakana AI")
        self.assertEqual(person["alumniOf"]["name"], "The University of Tokyo")
        self.assertEqual(person["sameAs"], SAME_AS)
        self.assertNotIn("email", person)

    def test_favicon(self):
        self.assertIsNotNone(find(self.doc, "link", attr=("href", "/favicon.svg")))
        self.assertTrue((ROOT / "favicon.svg").exists())

    def test_robots_and_sitemap(self):
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://koumisaki.com/sitemap.xml", robots)
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://koumisaki.com/</loc>", sitemap)
        self.assertIn("<lastmod>2026-10-31</lastmod>", sitemap)

    def test_404_links_home(self):
        page = parse("404.html")
        self.assertIn("/", [a.attrs.get("href") for a in find_all(page, "a")])
        self.assertEqual(find(page, "meta", attr=("name", "robots")).attrs.get("content"), "noindex")
        self.assertIsNotNone(find(page, "link", attr=("href", "/style.css")))
        self.assertEqual(find(page, "html").attrs.get("lang"), "en")


if __name__ == "__main__":
    unittest.main()
