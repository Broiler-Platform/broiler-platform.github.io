#!/usr/bin/env python3
"""Add independently released WebAssembly products to the built marketing site.

Only downloads producer release assets; never builds applications. All published
web versions are retained, and the newest published version becomes each entry.
"""
import argparse
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import build

spec = importlib.util.spec_from_file_location("web_artifact", Path(__file__).parent / "web/artifact.py")
artifact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifact)
PRODUCTS = {"launcher": ("Broiler-Platform/Broiler", "demo", "Broiler Office"),
            "writer": ("Broiler-Platform/Broiler.Writer", "writer", "Broiler Writer"),
            "cell": ("Broiler-Platform/Broiler.Cells", "cell", "Broiler Cell")}
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?\Z")


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path]))


def asset_bytes(repo, asset):
    # gh owns authentication and redirect handling; tokens never enter a URL.
    data = subprocess.check_output(["gh", "api", "-H", "Accept: application/octet-stream",
                                    f'repos/{repo}/releases/assets/{asset["id"]}'])
    if len(data) != asset["size"]:
        raise ValueError("GitHub asset size differs: " + asset["name"])
    return data


def releases(repo):
    result = []
    for page in range(1, 21):
        batch = api(f"repos/{repo}/releases?per_page=100&page={page}")
        result.extend(r for r in batch if not r["draft"] and r.get("published_at"))
        if len(batch) < 100:
            return sorted(result, key=lambda r: (r["published_at"], r["id"]), reverse=True)
    raise ValueError("Release history exceeds the bounded scan; review retention")


def source_commit(repo, tag):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", tag):
        raise ValueError("Unsupported release tag")
    target = api(f"repos/{repo}/git/ref/tags/{tag}")["object"]
    for _ in range(8):
        if target["type"] == "commit":
            return target["sha"]
        if target["type"] != "tag":
            break
        target = api(f'repos/{repo}/git/tags/{target["sha"]}')["object"]
    raise ValueError("Release tag does not resolve to a commit")


def install(repo, product, release, out, cache):
    matches = [a for a in release["assets"] if a["name"].endswith(".web-artifact.json")]
    if len(matches) != 1:
        raise ValueError("Exactly one descriptor required per web producer release")
    descriptor = matches[0]
    if descriptor["size"] > 8 * 1024 * 1024:
        raise ValueError("Producer descriptor exceeds limit")
    data = asset_bytes(repo, descriptor)
    meta = json.loads(data)
    if not VERSION.fullmatch(meta.get("version", "")) or len(meta["version"]) > 80:
        raise ValueError("Invalid producer version")
    archives = [a for a in release["assets"] if a["name"] == meta["archive"]]
    if len(archives) != 1 or archives[0]["size"] > 512 * 1024 * 1024:
        raise ValueError("Exactly one bounded producer ZIP is required")
    archive_asset = archives[0]
    for name in (descriptor["name"], archive_asset["name"]):
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", name):
            raise ValueError("Unsafe asset filename")
    downloaded = cache / str(release["id"])
    downloaded.mkdir(parents=True, exist_ok=True)
    metadata_path = downloaded / descriptor["name"]
    metadata_path.write_bytes(data)
    archive = downloaded / archive_asset["name"]
    archive.write_bytes(asset_bytes(repo, archive_asset))
    commit = source_commit(repo, release["tag_name"])
    manifest = artifact.verify(archive, metadata_path, require_release=True,
        expected={"product": product, "repository": repo, "tag": release["tag_name"], "commit": commit})
    if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) + sum(r["size"] for r in manifest["files"]) >= 900 * 1024 * 1024:
        raise ValueError("Retaining this release exceeds the website storage budget")
    prefix = PRODUCTS[product][1]
    destination = out / prefix / "releases" / manifest["version"]
    if destination.exists():
        raise ValueError("Duplicate immutable component version: " + manifest["version"])
    extracted = downloaded / "extracted"
    artifact.verify(archive, metadata_path, extract=extracted, require_release=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extracted / "wwwroot", destination)
    (out / "web-artifacts" / product).mkdir(parents=True, exist_ok=True)
    (out / "web-artifacts" / product / descriptor["name"]).write_bytes(data)
    return {"product": product, "version": manifest["version"], "repository": repo,
            "tag": release["tag_name"], "commit": commit, "releaseId": release["id"],
            "publishedAt": release["published_at"], "entryUrl": f'https://broiler-platform.github.io/{prefix}/releases/{manifest["version"]}/',
            "archive": {"id": archive_asset["id"], "name": archive.name, "size": manifest["archiveSize"], "sha256": manifest["archiveSha256"]},
            "metadata": {"id": descriptor["id"], "name": descriptor["name"], "size": len(data), "sha256": artifact.digest(data)},
            "runtimeMode": manifest["runtimeMode"], "files": manifest["files"]}


def resolve(out, required=False):
    if not (out / build.MARKER).is_file():
        raise ValueError("Run the website build first; output must have its build marker")
    if (out / "office-web-site.json").exists():
        raise ValueError("Rebuild the site before resolving new release identities")
    selected, history = {}, []
    with tempfile.TemporaryDirectory() as temporary:
        for product, (repo, prefix, title) in PRODUCTS.items():
            for release in releases(repo):
                if not any(a["name"].endswith(".web-artifact.json") for a in release["assets"]):
                    # Desktop-only releases are not web candidates.
                    continue
                row = install(repo, product, release, out, Path(temporary) / product)
                history.append(row)
                selected.setdefault(product, row)
            if product not in selected:
                if required:
                    raise ValueError("No published WebAssembly producer release for " + product)
                print(title + ": no published web release; availability page retained")
                continue
        for product, row in selected.items():
            repo, prefix, title = PRODUCTS[product]
            row["entryAvailable"] = product != "launcher" or len(selected) == 3
            if not row["entryAvailable"]:
                print("Office entry awaits all three published web products")
                continue
            target = f'./releases/{row["version"]}/'
            body = f'<section class="section"><div class="wrap"><h1>{title}</h1><p>Opening browser preview {html.escape(row["version"])}…</p><p><a class="btn btn-primary" href="{target}">Open {title}</a></p></div></section>'
            body += '<script>location.replace(new URL(' + json.dumps(target) + ',location.href).href);</script>'
            page = build.render(build.SHELL.read_text(encoding="utf-8"), {"title": title + " browser preview", "desc": "Open the current published browser preview of " + title + ".", "nav": "apps"}, body)
            (out / prefix / "index.html").write_text(page, encoding="utf-8")
            print(title + ": " + row["version"] + " (" + row["tag"] + ")")
    ledger = {"schemaVersion": 1, "artifactKind": "broiler-website-web-products", "selectionPolicy": "newest-published-web-release-including-prereleases",
              "products": list(selected.values()), "history": history, "unavailable": sorted(set(PRODUCTS) - set(selected)), "disabledProducts": ["browser", "plate"]}
    catalog = {"schemaVersion": 1, "status": "approved" if len(selected) == 3 else "unavailable", "channel": "preview",
               "catalogVersion": "website-" + "-".join(str(selected[p]["releaseId"]) for p in sorted(selected)),
               "products": [{"id": p, "version": selected[p]["version"], "url": selected[p]["entryUrl"]} for p in ("writer", "cell") if p in selected]}
    # C# catalog labels are bounded; numeric GitHub IDs keep this label compact.
    for name, value in (("office-web-site.json", ledger), ("office-web.json", catalog)):
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    (out / ".nojekyll").touch()
    if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) >= 900 * 1024 * 1024:
        raise ValueError("Site approaches Pages size limit; review retained web release storage")
    return ledger


def verify(out):
    ledger = json.loads((out / "office-web-site.json").read_text())
    for row in ledger["history"]:
        root = out / PRODUCTS[row["product"]][1] / "releases" / row["version"]
        expected = {r["path"]: r for r in row["files"]}
        files = artifact.tree(root)
        if set(expected) != set(files):
            raise ValueError("Deployed inventory differs")
        for name, data in files.items():
            if len(data) != expected[name]["size"] or artifact.digest(data) != expected[name]["sha256"]:
                raise ValueError("Deployed bytes differ: " + name)
        artifact.graph(files)
    print(f'Web products: {len(ledger["products"])} current, {len(ledger["history"])} retained versions; inventories verified')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=build.DEFAULT_OUT)
    parser.add_argument("--require-products", action="store_true", help="Fail until all three published web producers exist")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        resolve(args.out.resolve(), args.require_products)
    verify(args.out.resolve())
