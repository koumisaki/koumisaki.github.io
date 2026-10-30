"""Tiny HTML tree builder and helpers for the site tests (stdlib only)."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NOT_PUBLISHED = {".git", ".superpowers", "tests"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = {k: (v if v is not None else "") for k, v in attrs}
        self.parent = parent
        self.children = []

    @property
    def classes(self):
        return self.attrs.get("class", "").split()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(name):
    builder = _Builder()
    builder.feed((ROOT / name).read_text(encoding="utf-8"))
    return builder.root


def _walk(node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from _walk(child)


def find_all(node, tag=None, cls=None, attr=None):
    """attr is a (name, value) pair; value None means 'attribute present'."""
    found = []
    for n in _walk(node):
        if tag and n.tag != tag:
            continue
        if cls and cls not in n.classes:
            continue
        if attr:
            name, value = attr
            if name not in n.attrs or (value is not None and n.attrs[name] != value):
                continue
        found.append(n)
    return found


def find(node, tag=None, cls=None, attr=None):
    found = find_all(node, tag, cls, attr)
    return found[0] if found else None


def text(node):
    parts = []

    def collect(n):
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in ("script", "style"):
                collect(child)

    collect(node)
    return " ".join("".join(parts).split())


def site_files():
    return [p for p in ROOT.rglob("*") if p.is_file() and not NOT_PUBLISHED & set(p.relative_to(ROOT).parts)]
