# broiler-platform.github.io

The public website for the [Broiler](https://github.com/MaiRat/Broiler) platform — an
experimental managed-code browser, word processor and IDE stack for .NET 10.

Live at **<https://broiler-platform.github.io/>**.

## How it is built

A tiny static site with one build step and no dependencies beyond Python 3.

Every page shares a shell — the `<head>`, the sticky header with its nav, and the footer.
That shell lives in **`tools/shell.html`** and exists exactly once. `tools/build.py` wraps
each page body in it and writes the finished HTML to the site root, which is the branch
GitHub Pages serves (`.nojekyll` is present, so the files are copied through untouched).

```bash
python tools/build.py                 # rebuild every page and the sitemap
python tools/build.py components/js   # rebuild just those pages
python tools/build.py --check         # fail if any output is stale, write nothing
python tools/verify.py                # links, anchors, markup and page metadata
```

> **Edit `tools/pages/…`, not the HTML at the root.** The root files are build output.
> A change made there is discarded by the next build — which is what
> `tools/build.py --check` is for, and why CI runs it on every push and pull request.

## Layout

```text
tools/shell.html          The shared shell — the only copy of the head, nav and footer
tools/build.py            Wraps each page body in the shell; also writes sitemap.xml
tools/verify.py           Checks the built site: links, anchors, markup, metadata
tools/pages/              Page sources, mirroring their output paths

index.html                ── build output from here down ──
architecture.html         Layering, canonical owners, HtmlBridge, submodule topology
components.html           Component catalogue
components/*.html         One page per component (DOM, CSS, Layout, Graphics, Media,
                          Input, HTML, JS, UI, Documents, VM)
applications.html         Application catalogue
applications/*.html       Browser, Writer, Code
conformance.html          Every evidence suite: two WPT suites, test262, HTML 5.2,
                          real-world renders, the privacy corpus, Acid, unit-test status
assurance.html            Human review records, per-file review, code assurance
roadmap.html              Cross-repository work and its exit gates
packages.html             Every published NuGet package, and what is not published
get-started.html          Prerequisites, the solution map, build and tooling commands
security.html             Preview limits, parser boundaries, what is absent
docs.html                 Index of every current document, linked to its owning repo
404.html                  Not-found page (GitHub Pages serves this automatically)
sitemap.xml               Generated

assets/css/site.css       The whole stylesheet — token-driven, light and dark
assets/js/site.js         Theme toggle, mobile nav, copy buttons, table of contents
```

## Writing a page

A source is a JSON metadata object on the first line, a `---` line, then the body —
everything that belongs inside `<main>`:

```html
{"title": "Broiler.CSS — Broiler Platform", "desc": "…", "nav": "components"}
---
<section class="page-head">…</section>
```

| Key | | |
|---|---|---|
| `title` | required | `<title>`, and the default `og:title` |
| `desc` | required | Meta description, and the default `og:description` |
| `nav` | optional | `data-nav` value of the nav link to mark as current. A key that matches no link fails the build. |
| `og_title`, `og_desc` | optional | Override the defaults |
| `og_url` | optional | Emits `og:url`. Set on the home page only. |

The output path is the source path relative to `tools/pages/`, so
`tools/pages/components/js.html` builds `components/js.html`. Adding a page means adding
a source file — nothing else is registered anywhere.

### The three page shapes

- **Landing** — `index.html`, alternating `.section` / `.section-alt` bands.
- **Catalogue** — `components.html`, `applications.html`: a `.page-head`, then one
  `.section`.
- **Document** — everything else: a `.page-head`, then a `.doc` grid holding `.doc-body`
  and an empty `<aside class="toc" data-toc>`. The table of contents is built at runtime
  from the `h2[id]` and `h3[id]` elements inside `.doc-body`, and heading anchor links are
  injected the same way — so **give every section heading an `id`**. A heading without one
  is simply left out of the contents, which is how card and column headings stay out of it.

### Content components

`.callout` (with `-warn`, `-danger`, `-info`, `-ember` variants), `.card` with
`.grid-2/3/4`, `.stat` tiles, `.table-wrap` around every `<table>`, `.code` blocks with a
copy button, `.pill` badges, `.stack` (the layer diagram on the home page), `.checklist`,
`.split`, and `.pager` for previous/next links.

Wide content must sit inside its own scrolling container — `.table-wrap` for tables,
`.code` for code — because the page body must never scroll horizontally.

## Colour and theme

`assets/css/site.css` defines the complete light palette on `:root` and redefines only the
tokens under `@media (prefers-color-scheme: dark)` and `:root[data-theme="dark"]`, so the
toggle wins in both directions. Every foreground/background pair in the palette meets
WCAG AA (4.5:1) in both themes; if you change a colour, check it still does.

The theme toggle stores its choice in `localStorage` under `broiler-theme`. With nothing
stored, the site follows the operating system.

## Checking a change locally

```bash
python tools/build.py && python tools/verify.py
python -m http.server 8777
```

Then open <http://127.0.0.1:8777/>. The site uses root-absolute paths (`/assets/…`), so
opening the files directly with `file://` will not load the stylesheet.

## Accuracy

The site quotes figures, statuses and warnings from the Broiler repositories' own
documentation — review records, roadmaps, conformance dashboards and status ledgers. Those
move. When a component's status changes, update the page that states it, and prefer
linking to the owning document over restating it.

In particular, keep the preview and human-review warnings intact. The component review
records require them to be preserved in any public preview notes, and several of the
numbers on this site — `PENDING` review records, 0 % assurance coverage, failing test
counts — are deliberately unflattering.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
