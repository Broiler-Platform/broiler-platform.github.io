#!/usr/bin/env python3
"""Check the built site: internal links, anchors and markup.

    python tools/verify.py

Runs against the generated HTML at the site root — the files GitHub Pages
actually serves — rather than against the sources, so it catches a bad link
however it got there.

Checks:

  * every root-absolute link (`/…`) resolves to a page or an asset that exists;
  * every fragment (`#…`) resolves to an `id` on the page it points at;
  * tags are balanced and correctly nested;
  * every page has a non-empty <title> and meta description.

Exits non-zero and lists the problems if any check fails.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class Nesting(HTMLParser):
    """Reports unbalanced or badly nested tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, tuple[int, int]]] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"stray </{tag}> at line {self.getpos()[0]}")
            return
        if self.stack[-1][0] != tag:
            open_tag, (line, _) = self.stack[-1]
            self.problems.append(
                f"</{tag}> at line {self.getpos()[0]} closes <{open_tag}> opened at line {line}"
            )
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    return
            return
        self.stack.pop()

    def finish(self) -> list[str]:
        self.close()
        for tag, (line, _) in self.stack:
            self.problems.append(f"<{tag}> opened at line {line} is never closed")
        return self.problems


def pages() -> list[Path]:
    """Every built page: the site root and one level below it."""
    return sorted(
        p for p in list(ROOT.glob("*.html")) + list(ROOT.glob("*/*.html"))
        if ".github" not in p.parts and "tools" not in p.parts
    )


def main() -> int:
    found = pages()
    if not found:
        print("no built pages found — run `python tools/build.py` first", file=sys.stderr)
        return 1

    text = {p: p.read_text(encoding="utf-8") for p in found}
    url_of = {"/" + p.relative_to(ROOT).as_posix() for p in found} | {"/"}
    ids = {
        "/" + p.relative_to(ROOT).as_posix(): set(re.findall(r'id="([^"]+)"', s))
        for p, s in text.items()
    }
    problems: list[str] = []

    def note(page: Path, message: str) -> None:
        problems.append(f"{page.relative_to(ROOT).as_posix()}: {message}")

    for page, source in text.items():
        for target, fragment in re.findall(r'href="(/[^"#]*)(#[^"]*)?"', source):
            if target.startswith("/assets/"):
                if not (ROOT / target.lstrip("/")).exists():
                    note(page, f"link to missing asset {target}")
                continue
            if target not in url_of:
                note(page, f"link to missing page {target}")
            elif fragment:
                key = "/index.html" if target == "/" else target
                if fragment[1:] not in ids.get(key, set()):
                    note(page, f"link to missing anchor {target}{fragment}")

        own = ids["/" + page.relative_to(ROOT).as_posix()]
        for fragment in re.findall(r'href="#([^"]+)"', source):
            if fragment not in own:
                note(page, f"link to missing local anchor #{fragment}")

        parser = Nesting()
        parser.feed(source)
        for problem in parser.finish():
            note(page, problem)

        title = re.search(r"<title>(.*?)</title>", source, re.S)
        if not title or not title.group(1).strip():
            note(page, "empty or missing <title>")
        desc = re.search(r'<meta name="description" content="([^"]*)"', source)
        if not desc or not desc.group(1).strip():
            note(page, "empty or missing meta description")

    if problems:
        print(f"{len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(f"{len(found)} pages: links, anchors, markup and metadata all check out")
    return 0


if __name__ == "__main__":
    sys.exit(main())
