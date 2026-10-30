# koumisaki.com

Kou Misaki's homepage, served by GitHub Pages at https://koumisaki.com/. No build step.

## Updating

- Add a paper: in `index.html`, papers you led go under Selected Publications and the rest under Other Publications, newest first in each. Put the venue in `<span class="badge">` and an award such as Spotlight in `<span class="badge award">`. Selected entries also get keywords, a one-line `tldr` and a thumbnail: save the main figure from the paper's blog with `cwebp -q 85 -resize 720 0 figure.png -o images/papers/<name>.webp`. If the blog has an animation, record it instead as a short muted H.264 loop under 200 KB, save its last frame as the WebP still, and embed it like the existing ones (`<video ... poster="still" muted loop playsinline preload="none">`); the page plays it only while it is on screen and never for visitors who ask for reduced motion. Update `FIRST_AUTHOR` or `OTHER` (and `KEYWORDS`, `THUMBNAILS` and `VIDEOS`) in `tests/test_site.py`.
- `images/share.png` (1200×630) is the preview image shown when the link is pasted into LinkedIn, Slack or X. Remake it when the role or research areas change.
- Change the footer date in `index.html` and `<lastmod>` in `sitemap.xml` whenever the content changes.
- Check before pushing: `python3 -m unittest discover -s tests -v` and `python3 tests/check_links.py`.

Visits are counted with Cloudflare Web Analytics (no cookies); the dashboard is under Web Analytics in the Cloudflare account.

Brand icons come from [Simple Icons](https://simpleicons.org/) (CC0); the envelope icon was drawn for this site.
