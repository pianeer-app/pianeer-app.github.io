#!/usr/bin/env python3
"""Pre-flight checks for the Pianeer site.

The site is hand-written HTML with no build step, so nothing catches a typo for
us at compile time. This does instead. Standard library only — no Node, no npm,
no virtualenv: `python3 tools/check.py` from the repo root, or `make check`.

Checked, in order:

  1. Tag balance and nesting, via a real HTML5-aware parser.
  2. Every <link>/<img>/<script> asset referenced actually exists on disk.
  3. Every internal href resolves to a file that exists.
  4. Every #anchor resolves — both same-page links and cross-page ones like
     `./#pricing`, which is the pair that breaks when a section is renamed.
  5. Every <img> carries alt text and explicit width/height (no layout shift).
  6. Each page has exactly one <h1>, a <title> and a meta description.
  7. The nav and footer are byte-identical across pages apart from the
     documented per-page differences — they are duplicated by hand, so this is
     what stops the three copies drifting apart.
  8. Every class used in the HTML has a rule in the stylesheet, and every rule
     in the stylesheet is used by some page. Trimming a page is the moment a
     still-needed rule gets deleted, or a dead one gets left behind.

Exit status is 0 when everything passes, 1 otherwise, so it works in CI.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "support.html", "privacy.html"]

# Elements that never have a closing tag.
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

problems: list[str] = []


def fail(page: str, msg: str) -> None:
    problems.append(f"{page}: {msg}")


class PageParser(HTMLParser):
    """Collects structure, ids, links and images in one pass."""

    def __init__(self, page: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page = page
        self.stack: list[tuple[str, int]] = []
        self.ids: set[str] = set()
        self.hrefs: list[tuple[str, int]] = []
        self.assets: list[tuple[str, int]] = []
        self.images: list[tuple[dict[str, str], int]] = []
        self.counts: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]

        self.counts[tag] = self.counts.get(tag, 0) + 1
        if "id" in a:
            self.ids.add(a["id"])
        if "href" in a:
            self.hrefs.append((a["href"], line))
        if tag == "img":
            self.images.append((a, line))
            if a.get("src"):
                self.assets.append((a["src"], line))
        if tag == "link" and a.get("href"):
            self.assets.append((a["href"], line))
        if tag == "script" and a.get("src"):
            self.assets.append((a["src"], line))

        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID:
            return
        line = self.getpos()[0]
        if not self.stack:
            fail(self.page, f"line {line}: stray </{tag}>")
            return
        top, opened = self.stack[-1]
        if top != tag:
            fail(self.page, f"line {line}: </{tag}> while <{top}> from line {opened} is still open")
        else:
            self.stack.pop()


def block(src: str, start: str, end: str) -> str | None:
    """The text between the first `start` and the following `end`, inclusive."""
    i = src.find(start)
    if i < 0:
        return None
    j = src.find(end, i)
    return src[i : j + len(end)] if j >= 0 else None


def main() -> int:
    chrome: dict[str, dict[str, str]] = {"nav": {}, "footer": {}}
    ids_by_page: dict[str, set[str]] = {}
    anchor_links: list[tuple[str, str, str, int]] = []  # page, target page, anchor, line

    for page in PAGES:
        path = ROOT / page
        if not path.exists():
            fail(page, "file is missing")
            continue
        src = path.read_text(encoding="utf-8")

        parser = PageParser(page)
        parser.feed(src)
        parser.close()

        # 1. anything left open at EOF
        for tag, line in parser.stack:
            fail(page, f"<{tag}> opened on line {line} is never closed")

        # 2. + 3. every referenced path exists
        for ref, line in parser.assets + [(h, l) for h, l in parser.hrefs]:
            if ref.startswith(("http://", "https://", "mailto:", "data:", "#")) or not ref:
                continue
            target = ref.split("#", 1)[0].split("?", 1)[0]
            if not target or target == "./":
                continue
            if not (ROOT / target).exists():
                fail(page, f"line {line}: reference to missing file {target!r}")

        # 4. record every anchor; they are checked once all pages are parsed,
        # because a cross-page one names an id that lives in another file.
        ids_by_page[page] = parser.ids
        for href, line in parser.hrefs:
            if href.startswith(("http://", "https://", "mailto:")) or "#" not in href:
                continue
            target, _, anchor = href.partition("#")
            if not anchor:
                fail(page, f'line {line}: empty href="#" — point it somewhere real')
                continue
            # "" means this page; "./" and "index.html" both mean the landing
            # page; anything else names the file it points at.
            if target == "":
                dest = page
            elif target in ("./", ".", "index.html", "./index.html"):
                dest = "index.html"
            else:
                dest = target.removeprefix("./")
            anchor_links.append((page, dest, anchor, line))

        # 5. images are accessible and reserve their space
        for attrs, line in parser.images:
            if "alt" not in attrs:
                fail(page, f"line {line}: <img> without an alt attribute")
            if not (attrs.get("width") and attrs.get("height")):
                fail(page, f"line {line}: <img src={attrs.get('src','?')!r}> needs width and height")

        # 6. one h1, a title, a description
        if parser.counts.get("h1", 0) != 1:
            fail(page, f"expected exactly one <h1>, found {parser.counts.get('h1', 0)}")
        if "<title>" not in src:
            fail(page, "no <title>")
        if 'name="description"' not in src:
            fail(page, "no meta description")

        # 7. remember the shared chrome for the cross-page comparison
        nav = block(src, '<header class="nav">', "</header>")
        foot = block(src, "<footer>", "</footer>")
        if nav is None:
            fail(page, "no <header class=\"nav\"> block")
        else:
            chrome["nav"][page] = nav
        if foot is None:
            fail(page, "no <footer> block")
        else:
            chrome["footer"][page] = foot

    # 7 (continued). The three copies of the nav and footer are maintained by
    # hand. They legitimately differ in which links they carry and whether paths
    # are relative to the root, so compare only the parts that must not drift:
    # the brand lockup and the footer's legal line.
    def brand_and_legal(kind: str, text: str) -> str:
        if kind == "nav":
            return block(text, '<a class="nav-brand"', "</a>") or ""
        return re.sub(r"\s+", " ", block(text, '<p class="footer-legal">', "</p>") or "")

    for kind, copies in chrome.items():
        seen: dict[str, list[str]] = {}
        for page, text in copies.items():
            seen.setdefault(brand_and_legal(kind, text), []).append(page)
        if kind == "footer" and len(seen) > 1:
            groups = " vs ".join("+".join(v) for v in seen.values())
            fail("(all pages)", f"footer legal line has drifted apart: {groups}")
        if kind == "nav" and len(seen) > 1:
            groups = " vs ".join("+".join(v) for v in seen.values())
            fail("(all pages)", f"nav brand lockup has drifted apart: {groups}")

    # 4 (continued). Now that every page's ids are known, resolve the anchors.
    for page, target, anchor, line in anchor_links:
        if target not in ids_by_page:
            fail(page, f"line {line}: anchor points into {target!r}, which is not one of the pages")
        elif anchor not in ids_by_page[target]:
            where = "this page" if target == page else target
            fail(page, f'line {line}: href="#{anchor}" has no matching id in {where}')

    # 8. The stylesheet and the markup agree about which classes exist.
    css = (ROOT / "assets/css/style.css").read_text(encoding="utf-8")
    markup = "".join((ROOT / p).read_text(encoding="utf-8") for p in PAGES if (ROOT / p).exists())

    used: set[str] = set()
    for m in re.finditer(r'class="([^"]+)"', markup):
        used.update(m.group(1).split())
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))

    for cls in sorted(used - defined):
        fail("(stylesheet)", f"class {cls!r} is used in the HTML but has no CSS rule")
    for cls in sorted(defined - used):
        fail("(stylesheet)", f"CSS rule .{cls} is not used by any page")

    if problems:
        print(f"FAILED — {len(problems)} problem(s):\n")
        for p in problems:
            print(f"  • {p}")
        return 1

    print(f"OK — {len(PAGES)} pages: structure, links, anchors, assets, images, chrome.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
