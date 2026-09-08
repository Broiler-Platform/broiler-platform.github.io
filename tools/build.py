#!/usr/bin/env python3
"""Build the Broiler Platform site into a directory.

Every page shares one shell — the <head>, the sticky header with its nav, and
the footer. That shell lives in `tools/shell.html` and exists exactly once;
this script wraps each page's body in it, writes the sitemap, copies the static
files, and leaves a complete site in the output directory. GitHub Pages
publishes that directory; nothing generated is committed.

    python tools/build.py                 # build the whole site into _site/
    python tools/build.py --out dist      # somewhere else
    python tools/build.py components/js   # rebuild just those pages, in place

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

This file is the definition of what the site consists of: the pages under
`tools/pages/`, the generated sitemap, and STATIC below. Anything else in the
repository — this directory, the README, the workflows — is not part of it and
is never published.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "tools" / "pages"
SHELL = ROOT / "tools" / "shell.html"
DEFAULT_OUT = ROOT / "_site"
BASE_URL = "https://broiler-platform.github.io/"

# Copied into the output verbatim, relative to the repository root.
STATIC = ["assets", "robots.txt"]

# Pages that exist for the server rather than for a reader, and so stay out of
# the sitemap.
SITEMAP_SKIP = {"404.html"}

# Written into an output directory so a later run knows it made it, and will
# not empty a directory that holds something else.
MARKER = ".build-output"


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


def mark_current(shell: str, key: str) -> str:
    """Mark one nav link as the current page and drop the data-nav attributes.

    The nav markup lives in shell.html so there is one copy of it; the only
    thing that varies per page is which link is current.
    """
    seen: list[str] = []

    def repl(match: re.Match[str]) -> str:
        value = match.group(1)
        seen.append(value)
        return ' aria-current="page"' if value == key else ""

    out = re.sub(r'\s+data-nav="([^"]*)"', repl, shell)
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
    page = page.replace("%%OG_TITLE%%", esc(meta.get("og_title", meta["title"])))
    page = page.replace("%%OG_DESC%%", esc(meta.get("og_desc", meta["desc"])))
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


def rel_of(source: Path) -> str:
    return source.relative_to(PAGES).as_posix()


def build_sitemap(relatives: list[str]) -> str:
    """A deterministic sitemap: no lastmod, so it never drifts on a rebuild."""
    entries = []
    for rel in sorted(relatives):
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


def prepare(out: Path) -> None:
    """Empty the output directory, refusing anything this script did not make.

    --out takes a path from the caller, so `--out .` has to be a refusal rather
    than a recursive delete of the repository.
    """
    if out.exists():
        if not (out / MARKER).exists():
            raise BuildError(
                f"{out} exists and was not produced by this script "
                f"(no {MARKER} in it) — refusing to empty it"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text(
        "Generated by tools/build.py. Everything here is rebuilt from scratch.\n",
        encoding="utf-8",
    )


def copy_static(out: Path) -> list[str]:
    copied = []
    for name in STATIC:
        source = ROOT / name
        if not source.exists():
            raise BuildError(f"static path {name!r} does not exist")
        if source.is_dir():
            shutil.copytree(source, out / name)
            copied.append(f"{name}/")
        else:
            shutil.copy2(source, out / name)
            copied.append(name)
    return copied


def main(argv: list[str]) -> int:
    out = DEFAULT_OUT
    names: list[str] = []
    it = iter(range(len(argv)))
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--out":
            i += 1
            if i >= len(argv):
                print("--out needs a directory", file=sys.stderr)
                return 2
            out = Path(argv[i]).resolve()
        elif arg.startswith("--out="):
            out = Path(arg.split("=", 1)[1]).resolve()
        elif arg.startswith("-"):
            print(f"unknown option: {arg}\n\n{__doc__}", file=sys.stderr)
            return 2
        else:
            names.append(arg)
        i += 1

    shell = SHELL.read_text(encoding="utf-8")
    all_sources = sources()
    if not all_sources:
        print(f"no page sources found under {PAGES}", file=sys.stderr)
        return 1

    selected = all_sources
    if names:
        wanted = {n.removesuffix(".html") for n in names}
        by_stem = {Path(rel_of(s)).with_suffix("").as_posix(): s for s in all_sources}
        missing = wanted - by_stem.keys()
        if missing:
            print(f"no such page(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
        selected = [by_stem[w] for w in sorted(wanted)]

    # Render everything before writing anything, so a broken source fails the
    # run without leaving a half-built site.
    rendered = [(rel_of(s), render(shell, *read_source(s))) for s in selected]

    if names:
        # A partial rebuild updates an existing build in place.
        if not (out / MARKER).exists():
            print(
                f"{out} holds no build yet — run `python tools/build.py` first",
                file=sys.stderr,
            )
            return 1
    else:
        prepare(out)

    for rel, page in rendered:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        print(f"{rel:<32} {len(page):>7,} bytes")

    if not names:
        sitemap = build_sitemap([rel_of(s) for s in all_sources])
        (out / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        print(f"{'sitemap.xml':<32} {len(sitemap):>7,} bytes")
        for name in copy_static(out):
            print(f"{name:<32} {'copied':>13}")
        print(f"\n{len(rendered)} pages -> {out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
