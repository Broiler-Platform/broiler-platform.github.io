#!/usr/bin/env python3
"""Build the Broiler Platform site.

Every page shares one shell — the <head>, the sticky header with its nav, and
the footer. That shell lives in `tools/shell.html` and exists exactly once;
this script wraps each page's body in it and writes the result to the site
root, which is what GitHub Pages serves.

    python tools/build.py                 # rebuild every page and the sitemap
    python tools/build.py components/js   # rebuild just those pages
    python tools/build.py --check         # fail if any output is stale

`--check` is the form to run in CI or a pre-commit hook: it writes nothing and
exits non-zero when a committed page no longer matches its source, which is how
an edit made to a generated file instead of its source gets caught.

A page source lives at `tools/pages/<output path>` and is a JSON metadata
object on the first line, a `---` line, then the body — everything that belongs
inside <main>:

    {"title": "…", "desc": "…", "nav": "components"}
    ---
    <section class="page-head">…</section>

Metadata keys:

    title      required   <title> and the default og:title
    desc       required   meta description and the default og:description
    nav        optional   data-nav value of the nav link to mark as current
    og_title   optional   overrides og:title
    og_desc    optional   overrides og:description
    og_url     optional   emits og:url (set on the home page only)

The output path is the source path relative to `tools/pages/`, so
`tools/pages/components/js.html` builds `components/js.html`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "tools" / "pages"
SHELL = ROOT / "tools" / "shell.html"
SITEMAP = ROOT / "sitemap.xml"
BASE_URL = "https://broiler-platform.github.io/"

# Pages that exist for the server rather than for a reader, and so stay out of
# the sitemap.
SITEMAP_SKIP = {"404.html"}


class BuildError(Exception):
    pass


def esc(text: str) -> str:
    """Escape for an HTML attribute or element text.

    Deliberately leaves apostrophes alone: attributes here are double-quoted,
    so `&#x27;` would only make the prose in a <title> harder to read.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def read_source(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    head, sep, body = raw.partition("\n---\n")
    if not sep:
        raise BuildError(f"{path}: missing the '---' line after the metadata")
    try:
        meta = json.loads(head)
    except json.JSONDecodeError as exc:
        raise BuildError(f"{path}: metadata is not valid JSON — {exc}") from exc
    for key in ("title", "desc"):
        if not meta.get(key):
            raise BuildError(f"{path}: metadata is missing '{key}'")
    return meta, body.strip("\n")


def mark_current(nav_html: str, key: str) -> str:
    """Mark one nav link as the current page and drop the data-nav attributes.

    The nav markup lives in shell.html so there is one copy of it; the only
    thing that varies per page is which link is current.
    """
    seen: list[str] = []

    def repl(match: re.Match[str]) -> str:
        value = match.group(1)
        seen.append(value)
        return ' aria-current="page"' if value == key else ""

    out = re.sub(r'\s+data-nav="([^"]*)"', repl, nav_html)
    if key and key not in seen:
        raise BuildError(
            f"nav key {key!r} matches no link in shell.html (have: {', '.join(seen)})"
        )
    return out


def render(shell: str, meta: dict, body: str) -> str:
    """Fill the shell, then drop the body in last.

    The order matters: everything that could look like a placeholder or a nav
    attribute is resolved against the shell alone, so a page body is inserted
    verbatim and can contain whatever it likes.
    """
    og_url = meta.get("og_url")
    page = mark_current(shell, meta.get("nav", ""))
    page = page.replace("%%TITLE%%", esc(meta["title"]))
    page = page.replace("%%DESC%%", esc(meta["desc"]))
    page = page.replace(
        "%%OG_TITLE%%", esc(meta.get("og_title", meta["title"]))
    )
    page = page.replace(
        "%%OG_DESC%%", esc(meta.get("og_desc", meta["desc"]))
    )
    page = page.replace(
        "%%OG_URL%%",
        f'<meta property="og:url" content="{esc(og_url)}">\n' if og_url else "",
    )
    left = re.findall(r"%%(?!CONTENT%%)[A-Z_]+%%", page)
    if left:
        raise BuildError(f"unsubstituted placeholder(s) in shell.html: {sorted(set(left))}")
    return page.replace("%%CONTENT%%", body)


def sources() -> list[Path]:
    return sorted(PAGES.rglob("*.html"))


def out_path(source: Path) -> Path:
    return ROOT / source.relative_to(PAGES)


def build_sitemap(outputs: list[Path]) -> str:
    """A deterministic sitemap: no lastmod, so it never drifts on a rebuild."""
    entries = []
    for out in sorted(outputs, key=lambda p: p.relative_to(ROOT).as_posix()):
        rel = out.relative_to(ROOT).as_posix()
        if rel in SITEMAP_SKIP:
            continue
        loc = BASE_URL if rel == "index.html" else BASE_URL + rel
        priority = "1.0" if rel == "index.html" else ("0.8" if "/" not in rel else "0.6")
        entries.append(
            f"  <url>\n    <loc>{loc}</loc>\n    <priority>{priority}</priority>\n  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def main(argv: list[str]) -> int:
    check = "--check" in argv
    names = [a for a in argv if not a.startswith("-")]
    unknown = [a for a in argv if a.startswith("-") and a != "--check"]
    if unknown:
        print(f"unknown option(s): {' '.join(unknown)}\n\n{__doc__}", file=sys.stderr)
        return 2

    shell = SHELL.read_text(encoding="utf-8")
    all_sources = sources()
    if not all_sources:
        print(f"no page sources found under {PAGES}", file=sys.stderr)
        return 1

    selected = all_sources
    if names:
        wanted = {n.removesuffix(".html") for n in names}
        selected = [
            s for s in all_sources
            if s.relative_to(PAGES).with_suffix("").as_posix() in wanted
        ]
        missing = wanted - {
            s.relative_to(PAGES).with_suffix("").as_posix() for s in selected
        }
        if missing:
            print(f"no such page(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    # Render everything before writing anything, so a broken source fails the
    # run without leaving the site half-rebuilt.
    rendered = [(out_path(s), render(shell, *read_source(s))) for s in selected]

    stale: list[str] = []
    for out, page in rendered:
        rel = out.relative_to(ROOT).as_posix()
        if check:
            current = out.read_text(encoding="utf-8") if out.exists() else None
            if current != page:
                stale.append(rel)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print(f"{rel:<32} {len(page):>7,} bytes")

    # The sitemap is derived from the full page set, so it is only rebuilt (or
    # checked) when the whole site is.
    if not names:
        sitemap = build_sitemap([out_path(s) for s in all_sources])
        if check:
            current = SITEMAP.read_text(encoding="utf-8") if SITEMAP.exists() else None
            if current != sitemap:
                stale.append("sitemap.xml")
        else:
            SITEMAP.write_text(sitemap, encoding="utf-8")
            print(f"{'sitemap.xml':<32} {len(sitemap):>7,} bytes")

    if check:
        if stale:
            print("out of date — run `python tools/build.py`:", file=sys.stderr)
            for rel in stale:
                print(f"  {rel}", file=sys.stderr)
            return 1
        print(f"up to date ({len(selected)} pages)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
