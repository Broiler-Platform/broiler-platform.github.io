# broiler-platform.github.io

The public website for the [Broiler](https://github.com/MaiRat/Broiler) platform — an
experimental managed-code browser, word processor and IDE stack for .NET 10.

Live at **<https://broiler-platform.github.io/>**.

## What this is

A hand-written static site. No build step, no generator, no dependencies: the HTML files
in this repository are exactly what GitHub Pages serves. `.nojekyll` is present so Pages
copies the files through untouched.

```text
index.html            Overview — the stack, the applications, the honest preview position
architecture.html     Layering, canonical owners, HtmlBridge, submodule topology
components.html       Component catalogue
components/*.html     One page per component (DOM, CSS, Layout, Graphics, Media, Input,
                      HTML, JS, UI, Documents, VM)
applications.html     Application catalogue
applications/*.html   Browser, Writer, Code
conformance.html      Every evidence suite: two WPT suites, test262, HTML 5.2, real-world
                      renders, the privacy corpus, Acid, unit-test status
assurance.html        Human review records, per-file review, the code assurance system
roadmap.html          Cross-repository work and its exit gates
packages.html         Every published NuGet package, and what is deliberately not published
get-started.html      Prerequisites, the solution map, build and tooling commands
security.html         Preview limits, parser boundaries, what is absent
docs.html             Index of every current document, linked to its source repository
404.html              Not-found page (GitHub Pages serves this automatically)
assets/css/site.css   The whole stylesheet — token-driven, light and dark
assets/js/site.js     Theme toggle, mobile nav, copy buttons, table-of-contents
```

## Editing

Every page shares the same shell: the `<head>`, the sticky header with its nav, and the
footer are duplicated verbatim in each file. **If you change one of them, change all of
them** — `grep` for a distinctive string first.

The three page shapes are:

- **Landing** — `index.html`, alternating `.section` / `.section-alt` bands.
- **Catalogue** — `components.html`, `applications.html`: a `.page-head` then one
  `.section`.
- **Document** — everything else: a `.page-head`, then a `.doc` grid holding
  `.doc-body` and an empty `<aside class="toc" data-toc>`. The table of contents is built
  at runtime from the `h2[id]` and `h3[id]` elements in `.doc-body`, and heading anchor
  links are injected the same way — so **give every `h2` and `h3` an `id`**.

Content components available in the stylesheet: `.callout` (with `-warn`, `-danger`,
`-info`, `-ember` variants), `.card` and `.grid-2/3/4`, `.stat` tiles, `.table-wrap`
around every `<table>`, `.code` blocks with a copy button, `.pill` badges, `.stack`
(the layer diagram on the home page), `.checklist`, and `.pager` for previous/next links.

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
