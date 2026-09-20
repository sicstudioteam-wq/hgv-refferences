from __future__ import annotations

import mimetypes
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path.cwd()
PRESERVE = {".git", ".github"}

BASES = [
    "https://hgvprint.com.my",
    "https://hgvprints.com",
    "https://hgvprint.com",
]

IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg"}


def acceptable(path: str, content_type: str) -> bool:
    ext = Path(path).suffix.lower()
    ct = (content_type or "").lower()

    if ext in IMAGE_EXTS:
        return ct.startswith("image/")
    if ext == ".html":
        return "text/html" in ct or "application/xhtml" in ct
    if ext == ".css":
        return "text/css" in ct or "text/plain" in ct
    if ext == ".json":
        return "json" in ct or "text/plain" in ct
    if ext == ".xml":
        return "xml" in ct or "text/plain" in ct
    if ext == ".txt":
        return "text/" in ct or not ct

    guessed, _ = mimetypes.guess_type(path)
    return not guessed or not ct or guessed.split("/")[0] == ct.split("/")[0]


def download_one(rel: str) -> tuple[str, str | None, bytes | None, str | None]:
    encoded = quote(rel, safe="/")

    for base in BASES:
        url = f"{base}/{encoded}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 HGV-Reference-Importer/3.0",
                "Accept": "*/*",
            },
        )

        try:
            with urlopen(request, timeout=25) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")
                if response.status == 200 and data and acceptable(rel, content_type):
                    return rel, base, data, None
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

    return rel, None, None, locals().get("last_error", "not found")


def clean_root() -> None:
    for child in ROOT.iterdir():
        if child.name in PRESERVE:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: import_hgv.py <manifest>")
        return 2

    manifest_path = Path(sys.argv[1])
    paths = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    clean_root()

    success: list[tuple[str, str, int]] = []
    missing: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(download_one, rel): rel for rel in paths}

        completed = 0
        for future in as_completed(futures):
            rel, base, data, error = future.result()
            completed += 1

            if data is not None and base is not None:
                out = ROOT / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                success.append((rel, base, len(data)))
            else:
                missing.append((rel, error or "not found"))

            if completed % 50 == 0 or completed == len(paths):
                print(
                    f"Processed {completed}/{len(paths)} | "
                    f"downloaded={len(success)} missing={len(missing)}",
                    flush=True,
                )

    success.sort()
    missing.sort()

    report_lines = [
        "# HGV Reference Import Report",
        "",
        f"- Manifest files: **{len(paths)}**",
        f"- Downloaded: **{len(success)}**",
        f"- Missing: **{len(missing)}**",
        f"- Downloaded bytes: **{sum(item[2] for item in success):,}**",
        "",
        "## Missing files",
        "",
    ]

    if missing:
        report_lines.extend(f"- `{path}` — {error}" for path, error in missing)
    else:
        report_lines.append("- None")

    report_lines += [
        "",
        "## Source endpoints tried",
        "",
        *[f"- {base}" for base in BASES],
        "",
        "The requested path list was generated from the sanitized customer-facing files in the uploaded HGV `public_html` backup.",
        "",
    ]

    (ROOT / "IMPORT_REPORT.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    notes = """# HGV Reference Site

This repository contains the customer-facing HGV website reference set derived from the uploaded cPanel backup's `public_html` structure.

## Intentionally excluded

The uploaded backup was inspected before import. These were excluded because they are hosting/runtime, sensitive, duplicate, backup, internal, or unnecessary for static deployment:

- cPanel / CageFS runtime data
- SSL certificates and private keys
- mail data and server logs
- .ftpquota
- .well-known certificate validation files
- .htaccess / PHP runtime configuration
- source ZIP backups
- admin.html / internal admin artifacts
- backup HTML files
- XLSX / CSV internal working files
- README/change-log text files

The exact customer-facing manifest contains HTML, CSS, JSON, robots/sitemap and product/media assets.
"""
    (ROOT / "IMPORT_NOTES.md").write_text(notes, encoding="utf-8")

    print(
        f"FINAL manifest={len(paths)} downloaded={len(success)} "
        f"missing={len(missing)} bytes={sum(item[2] for item in success)}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
