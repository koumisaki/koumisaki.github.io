# koumisaki.com

Kou Misaki's homepage, served by GitHub Pages at https://koumisaki.com/. No build step.

## Updating

- Add a paper: copy an `<li class="paper">` block in `index.html`, keep newest first, and add `first-author` plus a `tldr` line only for first-author papers. Update `PAPERS` in `tests/test_site.py`.
- Change the footer date in `index.html` and `<lastmod>` in `sitemap.xml` whenever the content changes.
- Check before pushing: `python3 -m unittest discover -s tests -v` and `python3 tests/check_links.py`.
