# broiler-platform.github.io

The public website for [Broiler](https://github.com/Broiler-Platform/Broiler) â€” an open-source
browser, word processor, viewer, code editor, mail app and spreadsheet built on one platform
written from scratch in .NET.

Live at **<https://broiler-platform.github.io/>**.

## Browser app entry points

The website also hosts the independently published WebAssembly products:

| Entry | Intended short-domain forwarding |
| --- | --- |
| <https://broiler-platform.github.io/demo/> | `https://demo.broiler.app/` â†’ this URL |
| <https://broiler-platform.github.io/writer/> | `https://writer.broiler.app/` â†’ this URL |
| <https://broiler-platform.github.io/cell/> | `https://cell.broiler.app/` â†’ this URL |

These are real directories, so GitHub Pages normalizes `/demo`, `/writer` and
`/cell` to their trailing-slash forms. The home and applications pages link to
all three. Before a product has a published web release, its entry explains
that the preview is not available yet. The Office entry activates once all
three products exist; Writer and Cell can activate independently.

The **Site** workflow resolves current public WebAssembly releases on every
publication. It scans the public releases in `Broiler-Platform/Broiler`,
`Broiler-Platform/Broiler.Writer` and `Broiler-Platform/Broiler.Cells` for a
`.web-artifact.json` descriptor. Drafts and desktop-only releases are excluded;
prereleases are included because these browser editions are previews. The
newest `published_at` wins for each product, independently of native release
versions. Re-running **Site** with `workflow_dispatch` refreshes the products
without a website-source change. An external release integration may also send
the `web-release-published` repository-dispatch event; no cross-repository token
is required for the normal website publication path.

The workflow downloads original producer ZIPs, verifies source tag/commit,
repository/product identity, release eligibility, stable .NET 10 toolchain provenance,
archive size/SHA-256, full file inventory, generated entry/import map and SRI,
then extracts the complete `wwwroot` unchanged. It never compiles an application
or uses local NuGet packages. A malformed or damaged published web artifact
fails the build instead of silently using an older version. Normal network or
GitHub API errors also fail; they are not treated as absent releases.

Producer workflows select the latest stable `10.0.x` SDK and its compatible
`wasm-tools` workload. Descriptors record the resolved versions; validation accepts
stable .NET 10 versions without a patch-version lock. Early descriptors containing
a workload-set version plus blank output lines remain supported. Prerelease SDKs
and workloads, other .NET major versions and ambiguous provenance are rejected.

Files live under `/demo/releases/<version>/`, `/writer/releases/<version>/` and
`/cell/releases/<version>/`. All published web versions discovered in the
producer release history are retained, and duplicate component versions are
rejected. Keep those producer releases/assets published while historical URLs
are required. The build stops before a 900 MiB site storage budget rather than
silently pruning rollback versions.

`/office-web-site.json` records selected versions, producer release/asset IDs,
tags/commits, digests and retained file inventories. `/office-web.json` pins the
Launcher to the selected Writer and Cell version URLs on this website. The
complete marketing site, products and catalog are one Pages deployment; there
is no separate three-repository promotion step in this hosting configuration.
The Launcher and editors must include their website-path support before their
producer releases are published. Browser/Plate remain disabled.

The workflow runs extracted-product smoke tests plus website entry/navigation
tests in Chromium, Firefox and WebKit, checks website links and markup, and
rechecks every deployed product file. Evidence and the resolved release ledger
are uploaded as `website-web-product-evidence`. Pull requests perform the same
checks without deploying. Only `main` deploys. Use the manual `require_products`
option to fail until all three producer releases are available; its default
permits the honest availability pages while the first releases are prepared.

To reproduce locally (Python 3, authenticated GitHub CLI, Node 24):

```bash
python tools/build.py --out _site
python -m unittest discover -s tools/tests -v
python tools/web_products.py --out _site
python tools/verify.py _site
python tools/web_products.py --out _site --verify-only
npm ci --prefix tools/web
npx --prefix tools/web playwright install chromium firefox webkit
node tools/web/site-smoke.mjs _site evidence/website.json
```

`tools/web/artifact.py` and `smoke.mjs` are vendored from the Office repository's
`eng/web-producer`; keep those copies aligned. A plain offline `tools/build.py`
build produces marketing and availability pages without accessing GitHub.

### Short-domain forwarding

Configure **HTTP URL forwarding** at the domain provider or another redirect
service, with HTTPS certificates for all three source domains, to the table's
targets. Use ordinary redirects, not framed/masked forwarding. A DNS CNAME
cannot redirect to a path, and setting the website's single Pages custom domain
to one of these subdomains does not implement three path redirects. Keep this
Pages site at `broiler-platform.github.io`.

After a redirect the browser address and application origin are the website's.
Writer and Cell keep separate recovery database names, but share the website
origin and storage quota. Existing recovery drafts on the old subdomain origins
are not automatically migrated. Product return links go to `/demo/` on this
origin, so working website navigation does not depend on the forwarding service.
Check the three real HTTPS redirects after configuring the provider.

## Who the site is for

**End users first.** The top-level pages â€” the home page, the apps, About and Status â€” are
written for someone who has never heard of the project and wants to know what it is, whether
it is any good, and whether they can install it. They avoid jargon, and they lead with what
the apps do rather than how they are built.

**Developers second, but properly.** `/developers.html` is the entry point to the technical
material, and everything under it stays as detailed as it always was. Every developer page
carries a breadcrumb back to it. Keep the two audiences separated: if a paragraph would only
make sense to someone who already knows what a retained-mode UI toolkit is, it belongs on the
developer side.

The one thing both halves share is the honesty rule below â€” a friendlier tone must not turn
"no signed release exists" into "coming soon!".

## How it is built

A tiny static site with one build step and no dependencies beyond Python 3.

Every page shares a shell â€” the `<head>`, the sticky header with its nav, and the footer.
That shell lives in **`tools/shell.html`** and exists exactly once. `tools/build.py` wraps
each page body in it, writes the sitemap, copies the static files, and leaves a complete
site in `_site/`. GitHub Actions builds that directory and publishes it, so **nothing
generated is committed** and only the built site is served â€” `tools/` and the workflows
never reach it.

```bash
python tools/build.py                 # build the whole site into _site/
python tools/build.py --out dist      # somewhere else
python tools/build.py components/js   # rebuild just those pages, in place
python tools/verify.py                # links, anchors, markup and page metadata in _site/
```

`tools/build.py` is the definition of what the site consists of: the pages under
`tools/pages/`, the generated sitemap, and the `STATIC` list at the top of the script.
Anything else in the repository is not part of the site.

## Layout

```text
tools/shell.html          The shared shell â€” the only copy of the head, nav and footer
tools/build.py            Wraps each page body in the shell; writes the sitemap; copies
                          the static files; defines what the site consists of
tools/verify.py           Checks a built site: links, anchors, markup, metadata
tools/pages/              Page sources, mirroring their output paths:

  === for everyone ===
  index.html              What Broiler is, the apps, the honest status, FAQ
  applications.html       The apps, side by side, and what is planned
  applications/*.html     Browser, Writer, Plate, Code, Mail, Cells â€” what each one does for a user
  about.html              Why it exists, how it is made, where it came from
  status.html             What works, what doesn't, which previews can be downloaded and
                          what they are missing
  404.html                Not-found page (GitHub Pages serves this automatically)

  === for developers ===
  developers.html         The entry point: component map, rules, packages, evidence
  developers/*.html       Browser, Writer, Code â€” repository and build detail
  architecture.html       Layering, canonical owners, HtmlBridge, submodule topology
  components.html         Component catalogue â€” all nineteen, including those without a
                          page of their own (HtmlBridge, JSeal, Hosting, Net, Native,
                          Regex, DateTime, Unicode), which link to their repositories
  components/*.html       One page per component (DOM, CSS, Layout, Graphics, Media,
                          Input, HTML, JS, UI, Documents, VM)
  conformance.html        Every evidence suite: two WPT suites, test262, HTML 5.2,
                          real-world renders, the privacy corpus, Acid, unit-test status
  assurance.html          Human review records, per-file review, code assurance
  roadmap.html            Cross-repository work and its exit gates
  packages.html           Every published NuGet package, and what is not published
  get-started.html        Prerequisites, the solution map, build and tooling commands
  security.html           Preview limits, parser boundaries, what is absent
  docs.html               Index of every current document, linked to its owning repo

assets/css/site.css       The whole stylesheet â€” token-driven, light and dark
assets/js/site.js         Theme toggle, mobile nav, copy buttons, table of contents
assets/img/               Artwork â€” see below
robots.txt                Copied into the site verbatim
.github/workflows/        Build, check and publish
```

## Writing a page

A source is a JSON metadata object on the first line, a `---` line, then the body â€”
everything that belongs inside `<main>`:

```html
{"title": "Broiler.CSS â€” Broiler Platform", "desc": "â€¦", "nav": "components"}
---
<section class="page-head">â€¦</section>
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
a source file â€” nothing else is registered anywhere.

### The three page shapes

- **Landing** â€” `index.html`, alternating `.section` / `.section-alt` bands.
- **Catalogue** â€” `components.html`, `applications.html`: a `.page-head`, then one
  `.section`.
- **Document** â€” everything else: a `.page-head`, then a `.doc` grid holding `.doc-body`
  and an empty `<aside class="toc" data-toc>`. The table of contents is built at runtime
  from the `h2[id]` and `h3[id]` elements inside `.doc-body`, and heading anchor links are
  injected the same way â€” so **give every section heading an `id`**. A heading without one
  is simply left out of the contents, which is how card and column headings stay out of it.

### Content components

Shared: `.callout` (with `-warn`, `-danger`, `-info`, `-ember` variants), `.card` with
`.grid-2/3/4`, `.stat` tiles, `.table-wrap` around every `<table>`, `.code` blocks with a
copy button, `.pill` badges, `.checklist`, `.split`, and `.pager` for previous/next links.

User-facing: `.app-grid` / `.app-card` with `.app-icon` and `.platforms`, `.plat` chips,
`.app-head` for an app page header, `.features` / `.feature`, `.does` (a tick list; add
`.no` to an item for a dash instead), `.art-grid` / `.art-tile` for the component artwork,
`.status-band`, `.progress-row` / `.stage` (add `.now` or `.done`), `.faq`, and `.pullout`.

Developer-facing: `.stack` (the layer diagram), `.dev-strip` (the "are you a developer?"
band that ends most user pages), and `.crumb` (the breadcrumb every developer page carries).

Wide content must sit inside its own scrolling container â€” `.table-wrap` for tables,
`.code` for code â€” because the page body must never scroll horizontally.

## Artwork

`assets/img/` holds artwork taken from the Broiler repositories themselves:

| File | Source |
|---|---|
| `component-*.png` | The NuGet package icons from each component's `eng/icon.png` â€” the cartoon chickens. A broiler is a chicken; the project runs with the joke. |
| `broiler-mark.png` | The shared component package icon, the orange "B". |
| `app-browser.svg`, `app-writer.svg` | Converted from the Android app icons (`Resources/drawable/appicon.xml`) in the Browser and Writer repositories, path for path. |
| `app-code.svg` | **Not from the project.** Broiler Code has no icon of its own, so this one was drawn to match the other two â€” same blue, same flat style. Replace it if the project gains a real one. |
| `app-plate.svg`, `app-mail.svg`, `app-cells.svg` | **Not from the project** either. Broiler Plate, Broiler.Mail and Broiler Cells have no icons in their repositories, so these were drawn in the same style. Replace them if the projects gain real ones. |

All of it is Apache-2.0, from the same organisation as the site. The site's own header mark is
an inline SVG in `tools/shell.html` that matches `broiler-mark.png`.

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
python -m http.server 8777 --directory _site
```

Then open <http://127.0.0.1:8777/>. The site uses root-absolute paths (`/assets/â€¦`), so
serving `_site` is necessary â€” opening the files directly with `file://` will not load the
stylesheet.

## Publishing

`.github/workflows/pages.yml` builds the site and runs `tools/verify.py` on every push and
pull request, and deploys to GitHub Pages from `main` only. Pages is configured to publish
from the workflow rather than from the branch, so the served site contains exactly what
`tools/build.py` produced.

## Accuracy

The site quotes figures, statuses and warnings from the Broiler repositories' own
documentation â€” review records, roadmaps, conformance dashboards and status ledgers. Those
move. When a component's status changes, update the page that states it, and prefer
linking to the owning document over restating it.

In particular, keep the preview and human-review warnings intact. The component review
records require them to be preserved in any public preview notes, and several of the
numbers on this site â€” `PENDING` review records, 0 % assurance coverage, failing test
counts â€” are deliberately unflattering.

This matters more now that the site talks to end users. Plain language is not permission to
round anything up. "Emulator-tested" must not become "runs on Android"; "no signed release
exists" must not become "coming soon"; and the pages that say what the apps *cannot* do are
load-bearing, not filler.

The same goes for downloads now that some exist. A GitHub pre-release is not a reviewed or
signed release: say which files are unsigned, say which apps have no human-review record, and
keep the note that the previews went out ahead of the project's own release plan until that
stops being true. A draft release is not a download. Name formats the way the project does â€”
"DOCX", never "Word" (its decision DOCX-IP-006 forbids labels that name a vendor's product).

## License

Apache License 2.0 â€” see [LICENSE](LICENSE).
