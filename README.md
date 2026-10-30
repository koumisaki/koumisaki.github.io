# koumisaki.com

Kou Misaki's homepage, served by GitHub Pages at https://koumisaki.com/. No build step.

## Updating

- Add a paper: copy an `<li class="paper">` block in `index.html` and keep newest first. Put the venue in `<span class="badge">` and an award such as Spotlight in `<span class="badge award">`. Add `first-author` plus a `tldr` line only for first-author papers. Update `PAPERS` in `tests/test_site.py`.
- Change the footer date in `index.html` and `<lastmod>` in `sitemap.xml` whenever the content changes.
- Check before pushing: `python3 -m unittest discover -s tests -v` and `python3 tests/check_links.py`.

Brand icons come from [Simple Icons](https://simpleicons.org/) (CC0); the envelope icon was drawn for this site.
