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


def elements(node):
    return [c for c in node.children if not isinstance(c, str)]


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


FIRST_AUTHOR = [
    ("2602.04344", ["ICML 2026"], [("Blog", "https://pub.sakana.ai/umf/")]),
    ("2510.21150", ["ICLR 2026"], [("Blog", "https://pub.sakana.ai/ssot/")]),
    ("2503.04412", ["NeurIPS 2025", "Spotlight"],
     [("TreeQuest", "https://github.com/SakanaAI/treequest"), ("Blog", "https://sakana.ai/ab-mcts/")]),
]

OTHER = [
    ("2509.21862", ["ALIFE 2026"], [("Code", "https://github.com/SakanaAI/shachi")]),
    ("2501.16937", ["ICLR 2025", "Spotlight"],
     [("Code", "https://github.com/SakanaAI/TAID"), ("Blog", "https://sakana.ai/taid/")]),
]

KEYWORDS = {
    "2602.04344": ["inference-time scaling", "diffusion language models", "MCTS"],
    "2510.21150": ["prompting", "output diversity", "probabilistic instruction following"],
    "2503.04412": ["inference-time scaling", "MCTS", "Bayesian modeling"],
}

THUMBNAILS = {
    "2602.04344": ("/images/papers/unmaskfork.webp", "https://pub.sakana.ai/umf/"),
    "2510.21150": ("/images/papers/ssot.webp", "https://pub.sakana.ai/ssot/"),
    "2503.04412": ("/images/papers/ab-mcts-schematic.webp", "https://sakana.ai/ab-mcts/"),
}

LINKS = [
    ("Email", "#"),
    ("Google Scholar", "https://scholar.google.com/citations?user=8kL-3m4AAAAJ"),
    ("GitHub", "https://github.com/takkyu2"),
    ("LinkedIn", "https://www.linkedin.com/in/kou-misaki/"),
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


class TestProfile(unittest.TestCase):
    def setUp(self):
        self.doc = parse("index.html")
        self.profile = find(self.doc, "header", cls="profile")
        self.intro = find(self.profile, "div", cls="intro")

    def test_photo_sits_right_of_name(self):
        beside, photo = elements(self.intro)
        self.assertEqual((photo.tag, photo.classes), ("img", ["portrait"]))
        self.assertIsNotNone(find(beside, "h1"))

    def test_only_name_role_and_links_beside_photo(self):
        beside = find(self.intro, "div", cls="intro-text")
        self.assertEqual([(n.tag, n.classes) for n in elements(beside)],
                         [("h1", []), ("p", ["role"]), ("ul", ["links"])])

    def test_role(self):
        self.assertEqual(text(find(self.intro, "p", cls="role")), "Machine learning researcher at Sakana AI, Tokyo")

    def test_lead_sentence(self):
        self.assertEqual(text(find(self.profile, "p", cls="lead")),
                         "I research methods that make large language models perform better by spending more "
                         "compute at inference time, an approach known as inference-time scaling.")

    def test_key_facts(self):
        facts = find(self.profile, "dl", cls="facts")
        self.assertEqual([text(n) for n in find_all(facts, "dt")], ["First-author papers", "Before Sakana AI", "PhD"])
        self.assertEqual([text(n) for n in find_all(facts, "dd")],
                         ["ICML 2026, ICLR 2026, NeurIPS 2025 (Spotlight)",
                          "Apple (Japanese Siri), Recruit",
                          "Theoretical Physics, The University of Tokyo"])

    def test_venue_names_do_not_break_across_lines(self):
        dd = find_all(find(self.profile, "dl", cls="facts"), "dd")[0]
        raw = "".join(c for c in dd.children if isinstance(c, str))
        for venue in ["ICML\xa02026", "ICLR\xa02026", "NeurIPS\xa02025\xa0(Spotlight)"]:
            self.assertIn(venue, raw)

    def test_no_x_account(self):
        self.assertNotIn("x.com", (ROOT / "index.html").read_text(encoding="utf-8"))

    def test_no_bio_paragraph(self):
        self.assertIsNone(find(self.doc, "p", cls="bio"))

    def test_icon_links(self):
        links = find(self.intro, "ul", cls="links")
        self.assertEqual(links.attrs.get("role"), "list")
        anchors = find_all(links, "a")
        self.assertEqual([(a.attrs.get("aria-label"), a.attrs.get("href")) for a in anchors], LINKS)
        for a in anchors:
            with self.subTest(link=a.attrs.get("aria-label")):
                self.assertEqual(a.attrs.get("title"), a.attrs.get("aria-label"))
                self.assertEqual(text(a), "")
                self.assertEqual(find(a, "svg").attrs.get("aria-hidden"), "true")

    def test_email_icon_is_assembled_by_script(self):
        a = find(self.intro, "a", cls="email")
        self.assertEqual((a.attrs.get("data-user"), a.attrs.get("data-domain")), ("mk940se", "gmail.com"))
        script = " ".join(text_of_scripts(self.doc))
        self.assertIn("mailto:", script)
        self.assertIn("data-user", script)

    def test_footer_shows_email_address(self):
        footer = find(self.doc, "footer", cls="footer")
        a = find(footer, "a", cls="email-address")
        self.assertEqual((a.attrs.get("data-user"), a.attrs.get("data-domain")), ("mk940se", "gmail.com"))
        self.assertIn("mk940se [at] gmail.com", text(find(footer, "noscript")))
        self.assertRegex(" ".join(text_of_scripts(self.doc)), r"email-address[\s\S]*textContent")

    def test_no_plaintext_email_anywhere(self):
        address = ("mk940se" + "@" + "gmail.com").encode()
        for path in site_files():
            self.assertNotIn(address, path.read_bytes(), path)

    def test_portrait_markup(self):
        img = find(self.intro, "img", cls="portrait")
        self.assertEqual(img.attrs.get("src"), "/images/portrait.jpg")
        self.assertEqual((img.attrs.get("width"), img.attrs.get("height")), ("112", "112"))
        self.assertTrue(img.attrs.get("alt"))

    def test_portrait_file_is_small_square_and_clean(self):
        path = ROOT / "images" / "portrait.jpg"
        width, height, has_exif = jpeg_info(path)
        self.assertEqual((width, height), (400, 400))
        self.assertFalse(has_exif)
        self.assertLess(path.stat().st_size, 60_000)


class TestPublications(unittest.TestCase):
    def setUp(self):
        self.doc = parse("index.html")
        self.first = find(self.doc, "section", attr=("id", "selected-publications"))
        self.other = find(self.doc, "section", attr=("id", "other-publications"))
        self.papers = find_all(self.doc, "li", cls="paper")

    def paper(self, arxiv):
        return find(self.doc, "li", attr=("data-arxiv", arxiv))

    def groups(self):
        return [(self.first, FIRST_AUTHOR, True), (self.other, OTHER, False)]

    def test_own_papers_come_before_the_rest(self):
        self.assertEqual([s.attrs.get("id") for s in find_all(self.doc, "section")], ["selected-publications", "other-publications"])
        self.assertEqual(text(find(self.first, "h2")), "Selected Publications")
        self.assertEqual(text(find(self.other, "h2")), "Other Publications")

    def test_order(self):
        for section, papers, _ in self.groups():
            with self.subTest(section=section.attrs.get("id")):
                found = [li.attrs.get("data-arxiv") for li in find_all(section, "li", cls="paper")]
                self.assertEqual(found, [p[0] for p in papers])

    def test_lists_keep_their_semantics(self):
        for section, _, _ in self.groups():
            self.assertEqual(find(section, "ol", cls="papers").attrs.get("role"), "list")

    def test_each_paper(self):
        for section, papers, first in self.groups():
            for li, (arxiv, badges, links) in zip(find_all(section, "li", cls="paper"), papers):
                with self.subTest(arxiv=arxiv):
                    abs_url = f"https://arxiv.org/abs/{arxiv}"
                    self.assertEqual(find(li, "a", cls="paper-title").attrs.get("href"), abs_url)
                    self.assertEqual([text(s) for s in find_all(find(li, "p", cls="authors"), "strong")], ["Kou Misaki"])
                    self.assertEqual([text(s) for s in find_all(find(li, "p", cls="venue"), "span", cls="badge")], badges)
                    tldr = find(li, "p", cls="tldr")
                    self.assertEqual(tldr is not None and bool(text(tldr)), first)
                    found = [(text(a), a.attrs.get("href")) for a in find_all(find(li, "p", cls="paper-links"), "a")]
                    self.assertEqual(found, [("arXiv", abs_url)] + links)

    def test_venue_badge_comes_first(self):
        for li in self.papers:
            with self.subTest(arxiv=li.attrs.get("data-arxiv")):
                head = elements(li)[0]
                self.assertEqual(head.classes, ["paper-head"])
                meta = elements(head)[0]
                self.assertEqual(meta.classes, ["paper-meta"])
                self.assertEqual(elements(meta)[0].classes, ["venue"])

    def test_summary_spans_the_full_width_below_the_head(self):
        for section, _, first in self.groups():
            for li in find_all(section, "li", cls="paper"):
                with self.subTest(arxiv=li.attrs.get("data-arxiv")):
                    expected = [["paper-head"], ["tldr"], ["paper-links"]] if first else [["paper-head"], ["paper-links"]]
                    self.assertEqual([n.classes for n in elements(li)], expected)

    def test_spotlights_are_award_badges(self):
        self.assertEqual([text(s) for s in find_all(self.doc, "span", cls="award")], ["Spotlight", "Spotlight"])

    def test_research_papers_have_keywords(self):
        for li in find_all(self.first, "li", cls="paper"):
            arxiv = li.attrs["data-arxiv"]
            with self.subTest(arxiv=arxiv):
                keywords = find(li, "ul", cls="keywords")
                self.assertEqual(keywords.attrs.get("role"), "list")
                self.assertEqual([text(k) for k in find_all(keywords, "li")], KEYWORDS[arxiv])
        self.assertIsNone(find(self.other, "ul", cls="keywords"))

    def test_research_papers_show_their_blog_figure(self):
        for li in find_all(self.first, "li", cls="paper"):
            arxiv = li.attrs["data-arxiv"]
            src, href = THUMBNAILS[arxiv]
            with self.subTest(arxiv=arxiv):
                link = elements(elements(li)[0])[1]
                self.assertEqual((link.tag, link.classes, link.attrs.get("href")), ("a", ["thumb"], href))
                self.assertEqual((link.attrs.get("tabindex"), link.attrs.get("aria-hidden")), ("-1", "true"))
                img = find(link, "img")
                self.assertEqual((img.attrs.get("src"), img.attrs.get("loading")), (src, "lazy"))
                self.assertTrue(img.attrs.get("width") and img.attrs.get("height"))
                path = ROOT / src.lstrip("/")
                self.assertTrue(path.exists(), path)
                self.assertLess(path.stat().st_size, 80_000)
        self.assertIsNone(find(self.other, "a", cls="thumb"))

    def test_summaries_state_each_contribution(self):
        expected = {
            "2602.04344": ["masked diffusion language models", "multiple models collaborate",
                           "Monte Carlo tree search", "coding benchmarks", "math"],
            "2510.21150": ["make choices according to given probabilities", "fair coin", "prompting alone", "random string", "more diverse"],
            "2503.04412": ["We propose AB-MCTS", "Bayesian", "refine an existing one",
                           "As part of this work, I developed TreeQuest"],
        }
        for arxiv, phrases in expected.items():
            tldr = text(find(self.paper(arxiv), "p", cls="tldr"))
            for phrase in phrases:
                with self.subTest(arxiv=arxiv, phrase=phrase):
                    self.assertIn(phrase, tldr)

    def test_equal_contribution(self):
        authors = text(find(self.paper("2503.04412"), "p", cls="authors"))
        self.assertIn("Yuichi Inoue*", authors)
        self.assertIn("Kou Misaki*", authors)
        legend = text(find(self.other, "p", cls="legend"))
        self.assertIn("* Equal contribution", legend)

    def test_scholar_full_list_link(self):
        legend = find(self.other, "p", cls="legend")
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
        pairs = [("--text", "--bg"), ("--text-secondary", "--bg"), ("--accent", "--bg"),
                 ("--badge-text", "--badge-bg"), ("--award-text", "--award-bg"), ("--text-secondary", "--tag-bg")]
        for name, tokens in [("light", light), ("dark", dark)]:
            for fg, bg in pairs:
                with self.subTest(mode=name, pair=(fg, bg)):
                    self.assertGreaterEqual(contrast(tokens[fg], tokens[bg]), 4.5)

    def test_font_fallbacks(self):
        self.assertRegex(self.css, r"--font-serif:[^;]*Newsreader[^;]*,\s*serif;")
        self.assertRegex(self.css, r"--font-sans:[^;]*Inter[^;]*,\s*sans-serif;")

    def test_layout_width(self):
        self.assertIn("max-width: 760px", self.css)

    def test_long_titles_wrap(self):
        self.assertRegex(self.css, r"\.paper-title\s*\{[^}]*overflow-wrap:\s*anywhere")

    def test_name_fills_the_row_and_photo_is_centred_beside_it(self):
        self.assertRegex(self.css, r"\.intro\s*\{[^}]*align-items:\s*center")
        self.assertRegex(self.css, r"\.intro-text\s*\{[^}]*flex:\s*1")
        self.assertRegex(self.css, r"\.portrait\s*\{[^}]*width:\s*112px")

    def test_mobile_keeps_photo_beside_name(self):
        self.assertNotIn("column-reverse", self.css)
        mobile = self.css[self.css.index("@media (max-width: 600px)"):]
        self.assertRegex(mobile, r"\.portrait\s*\{[^}]*width:\s*84px")

    def test_icons_fit_on_small_phones(self):
        small = self.css[self.css.index("@media (max-width: 360px)"):]
        self.assertRegex(small, r"\.links a\s*\{[^}]*width:\s*36px")

    def test_icons_follow_text_colour(self):
        self.assertRegex(self.css, r"\.links svg\s*\{[^}]*fill:\s*currentColor")

    def test_thumbnails_are_centred_beside_their_paper(self):
        self.assertRegex(self.css, r"\.paper-head\s*\{[^}]*align-items:\s*center")

    def test_thumbnails_show_the_whole_figure_and_lead_on_phones(self):
        self.assertRegex(self.css, r"\.thumb\s*\{[^}]*aspect-ratio:\s*2\s*/\s*1")
        self.assertRegex(self.css, r"\.thumb img\s*\{[^}]*object-fit:\s*contain")
        self.assertRegex(self.css, r"\.thumb img\s*\{[^}]*position:\s*absolute")
        mobile = self.css[self.css.index("@media (max-width: 600px)"):]
        self.assertRegex(mobile, r"\.thumb\s*\{[^}]*order:\s*-1")

    def test_links_in_running_text_are_underlined(self):
        self.assertRegex(self.css, r"\.legend a\s*\{[^}]*text-decoration:\s*underline")

    def test_404_uses_only_defined_classes(self):
        for node in find_all(parse("404.html"), attr=("class", None)):
            for cls in node.classes:
                with self.subTest(cls=cls):
                    self.assertRegex(self.css, rf"\.{cls}\b")

    def test_fonts_loaded_and_footer(self):
        doc = parse("index.html")
        hrefs = [l.attrs.get("href", "") for l in find_all(doc, "link")]
        self.assertTrue(any("fonts.googleapis.com/css2" in h and "Newsreader" in h and "Inter" in h for h in hrefs))
        footer = find(doc, "footer", cls="footer")
        self.assertIn("Last updated: October 2026", [text(p) for p in find_all(footer, "p")])


SAME_AS = [
    "https://scholar.google.com/citations?user=8kL-3m4AAAAJ",
    "https://github.com/takkyu2",
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
