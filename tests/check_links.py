"""Check that every external link on the site responds. Run: python3 tests/check_links.py"""
import sys
import urllib.error
import urllib.request

from sitecheck import find_all, parse

UNVERIFIABLE = {"www.linkedin.com"}  # blocks scripted requests (999)
OWN_HOST = "koumisaki.com"  # canonical self-references; checked when the domain goes live


def external_links():
    links = set()
    for page in ["index.html", "404.html"]:
        for tag, attr in [("a", "href"), ("link", "href")]:
            for node in find_all(parse(page), tag):
                url = node.attrs.get(attr, "")
                if url.startswith("https://") and "fonts.g" not in url and url.split("/")[2] != OWN_HOST:
                    links.add(url)
    return sorted(links)


def status(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (link check)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)


def main():
    failed = False
    for url in external_links():
        code = status(url)
        host = url.split("/")[2]
        ok = isinstance(code, int) and code < 400
        label = "ok" if ok else ("unverifiable" if host in UNVERIFIABLE else "FAIL")
        failed |= label == "FAIL"
        print(f"{label:13} {code}  {url}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
