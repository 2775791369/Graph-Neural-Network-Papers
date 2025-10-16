"""Download papers listed in GNNPapers.md into organized directories.

This script parses the Markdown file, extracts paper titles and links,
and downloads the corresponding PDFs (when accessible). Files are stored
in the ``papers`` directory, grouped by their section headers.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_PATH = ROOT / "GNNPapers.md"
OUTPUT_ROOT = ROOT / "papers"


SECTION_PATTERN = re.compile(r"^(#{2,})\s*(.+?)\s*$")
PAPER_LINK_PATTERN = re.compile(r"\[(?:paper|book)\]\(([^)]+)\)")
TITLE_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def sanitize_name(name: str) -> str:
    """Return a filesystem-safe name derived from *name*."""

    sanitized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5]+", "_", name)
    sanitized = sanitized.strip("_")
    return sanitized or "unnamed"


def extract_sections(lines: Iterable[str]) -> List[Tuple[str, List[str]]]:
    """Split the Markdown file into (section_name, content_lines)."""

    sections: List[Tuple[str, List[str]]] = []
    current_section = "root"
    current_lines: List[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        match = SECTION_PATTERN.match(line)
        if match:
            level, heading = match.groups()
            if len(level) == 2:  # only consider top-level sections
                if current_lines:
                    sections.append((current_section, current_lines))
                current_section = heading.strip().strip("[]")
                current_lines = []
                continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_section, current_lines))

    return sections


def normalize_url(url: str) -> str:
    """Return a URL that points to a PDF when possible."""

    url = url.strip()
    if "arxiv.org/abs/" in url and not url.endswith(".pdf"):
        return url.replace("/abs/", "/pdf/") + ".pdf"
    return url


def unique_path(base: Path) -> Path:
    """Return a unique path by appending numeric suffixes when needed."""

    if not base.exists():
        return base

    index = 1
    while True:
        candidate = base.with_stem(f"{base.stem}_{index}")
        if not candidate.exists():
            return candidate
        index += 1


def download_file(url: str, destination: Path) -> Tuple[bool, str]:
    """Download ``url`` into ``destination``.

    Returns a tuple ``(success, message)``.
    """

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                return False, f"Non-PDF content-type: {content_type or 'unknown'}"

            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as file_obj:
                shutil.copyfileobj(response, file_obj)
    except urllib.error.URLError as exc:
        return False, str(exc)

    return True, ""


def collect_entries() -> List[Tuple[str, str, str]]:
    """Extract ``(section, title, url)`` tuples from the Markdown file."""

    lines = MARKDOWN_PATH.read_text(encoding="utf-8").splitlines()
    entries: List[Tuple[str, str, str]] = []

    for section, section_lines in extract_sections(lines):
        for index, line in enumerate(section_lines):
            link_match = PAPER_LINK_PATTERN.search(line)
            if not link_match:
                continue

            url = normalize_url(link_match.group(1))
            title_match = TITLE_PATTERN.search(line)

            if not title_match:
                for offset in range(index - 1, max(index - 6, -1), -1):
                    previous_match = TITLE_PATTERN.search(section_lines[offset])
                    if previous_match:
                        title_match = previous_match
                        break

            title = title_match.group(1).strip() if title_match else f"paper_{len(entries) + 1}"
            title = title.rstrip(".")

            entries.append((section, title, url))

    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download papers listed in GNNPapers.md")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N entries (useful for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned download paths without fetching files",
    )
    return parser.parse_args()


def main() -> int:
    if not MARKDOWN_PATH.exists():
        print(f"Markdown file not found: {MARKDOWN_PATH}", file=sys.stderr)
        return 1

    args = parse_args()
    entries = collect_entries()
    if args.limit is not None:
        entries = entries[: args.limit]
    print(f"Found {len(entries)} entries with downloadable links.")

    successes: List[Tuple[str, Path]] = []
    failures: List[Tuple[str, str, str]] = []

    for section, title, url in entries:
        section_dir = OUTPUT_ROOT / sanitize_name(section)
        filename = sanitize_name(title) + ".pdf"
        destination = unique_path(section_dir / filename)

        if destination.exists():
            print(f"Skipping existing file: {destination}")
            continue

        if args.dry_run:
            print(f"Planned: {title} -> {destination.relative_to(ROOT)} ({url})")
            continue

        success, message = download_file(url, destination)
        if success:
            successes.append((title, destination))
            print(f"Downloaded: {title} -> {destination.relative_to(ROOT)}")
        else:
            failures.append((title, url, message))
            print(f"Failed: {title} ({url}) - {message}")

    print("\nSummary:")
    print(f"  Successful downloads: {len(successes)}")
    print(f"  Failed downloads: {len(failures)}")
    if failures:
        print("\nFailures:")
        for title, url, message in failures:
            print(f"  - {title}: {url} ({message})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

