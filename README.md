# koumisaki.com

Kou Misaki's homepage, served by GitHub Pages at https://koumisaki.com/. No build step.

## Updating

- Add a paper: in `index.html`, papers you led go under Selected Publications and the rest under Other Publications, newest first in each. Put the venue in `<span class="badge">` and an award such as Spotlight in `<span class="badge award">`. Selected entries also get keywords, a one-line `tldr` and a thumbnail: save the main figure from the paper's blog with `cwebp -q 85 -resize 720 0 figure.png -o images/papers/<name>.webp`. Update `FIRST_AUTHOR` or `OTHER` (and `KEYWORDS` and `THUMBNAILS`) in `tests/test_site.py`.
- Change the footer date in `index.html` and `<lastmod>` in `sitemap.xml` whenever the content changes.
- Check before pushing: `python3 -m unittest discover -s tests -v` and `python3 tests/check_links.py`.

Brand icons come from [Simple Icons](https://simpleicons.org/) (CC0); the envelope icon was drawn for this site.
