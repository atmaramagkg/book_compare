#!/usr/bin/env python3
"""Build the app's diff dataset from the published chapter-by-chapter
ExamDiff reports on bookchanges.com.

The reports compare the 1972 Macmillan text of Bhagavad-gita As It Is with
the post-1977 "Revised and Enlarged" text (both as published in Vedabase).
Each report is an XHTML table with two line-aligned panes:

  #d21 - original (1972)      #d22 - revised (post-1977)

Inline spans are marked: identical / changed / changed2 / deleted / added.
We keep only the changed regions (plus light context), grouped by verse and
section, and write a compact JSON file bundled with the Flutter app.

Usage:
    python tools/build_diff_data.py
    python tools/build_diff_data.py --offline   # reuse cached HTML only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

BASE_URL = "https://bookchanges.com/wp-content/uploads/2009/09/Bg-Chapter-{chapter}-diff.htm"
ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "tools" / ".cache"
OUT_FILE = ROOT / "assets" / "data" / "bg_diffs.json"

CHAPTER_TITLES = {
    1: "Observing the Armies on the Battlefield of Kuruksetra",
    2: "Contents of the Gita Summarized",
    3: "Karma-yoga",
    4: "Transcendental Knowledge",
    5: "Karma-yoga - Action in Krsna Consciousness",
    6: "Sankhya-yoga",
    7: "Knowledge of the Absolute",
    8: "Attaining the Supreme",
    9: "The Most Confidential Knowledge",
    10: "The Opulence of the Absolute",
    11: "The Universal Form",
    12: "Devotional Service",
    13: "Nature, the Enjoyer, and Consciousness",
    14: "The Three Modes of Material Nature",
    15: "The Yoga of the Supreme Person",
    16: "The Divine and Demoniac Natures",
    17: "The Divisions of Faith",
    18: "Conclusion - The Perfection of Renunciation",
}

# ExamDiff inline class -> our highlight kind.
KIND_MAP = {
    "identical": "same",
    "changed": "same",      # unchanged words inside a changed line
    "changed2": "chg",      # substituted words (shown highlighted on both sides)
    "deleted": "del",       # original-only words
    "added": "add",         # revised-only words
    "inserted": "add",
    "newer": "chg",
    "older": "chg",
    "ignored": "same",
}

DIFF_ROW_CLASSES = {"linespan_c", "linespan_a", "linespan_d", "linespan_n", "linespan_o"}
VERSE_RE = re.compile(r"Bg\.?\s*(\d+)\.(\d+(?:\s*-\s*\d+)?)", re.IGNORECASE)
TEXT_RE = re.compile(r"^TEXT\s+\d+", re.IGNORECASE)


def fetch_html(chapter: int, offline: bool) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"bg-chapter-{chapter:02d}.html"
    if path.exists() and path.stat().st_size > 10_000:
        return path.read_text(encoding="utf-8", errors="replace")
    if offline:
        raise FileNotFoundError(f"No cached HTML for chapter {chapter}: {path}")

    url = BASE_URL.format(chapter=chapter)
    print(f"  downloading chapter {chapter:2d} ...", flush=True)
    subprocess.run(
        [
            "curl.exe", "-L", "-sS", "--fail", "--max-time", "240",
            "--retry", "3", "--retry-delay", "2",
            "-A", "Mozilla/5.0",
            "-o", str(path), url,
        ],
        check=True,
    )
    return path.read_text(encoding="utf-8", errors="replace")


def parse_row(div) -> dict:
    """Turn one <div class=linespan_*> into structured spans."""
    classes = div.get("class") or []
    spans = []
    for span in div.find_all("span", recursive=False):
        span_classes = span.get("class") or []
        if not span_classes:
            continue  # line-number gutter
        text = span.get_text().replace("\xa0", " ")
        text = re.sub(r"[ \t]{2,}", " ", text)
        kind = KIND_MAP.get(span_classes[0], "same")
        if text.strip():
            spans.append({"t": text, "k": kind})
    return {
        "diff": bool(classes) and classes[0] in DIFF_ROW_CLASSES,
        "spans": spans,
    }


def parse_panes(html: str) -> tuple[list[dict], list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    left_div = soup.find(id="d21")
    right_div = soup.find(id="d22")
    if left_div is None or right_div is None:
        raise ValueError("Could not find the two diff panes (#d21 / #d22)")
    left = [parse_row(d) for d in left_div.find_all("div", recursive=False)]
    right = [parse_row(d) for d in right_div.find_all("div", recursive=False)]
    if len(left) != len(right):
        raise ValueError(f"Pane line counts differ: {len(left)} vs {len(right)}")
    return left, right


def row_text(row: dict) -> str:
    return "".join(s["t"] for s in row["spans"])


def merge_runs(left: list[dict], right: list[dict], gap: int = 2) -> list[tuple[int, int]]:
    """Group contiguous changed rows; merge runs separated by little context."""
    flags = [l["diff"] or r["diff"] for l, r in zip(left, right)]
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        start = i
        while i < len(flags) and flags[i]:
            i += 1
        end = i  # exclusive
        if runs and start - runs[-1][1] <= gap:
            runs[-1] = (runs[-1][0], end)
        else:
            runs.append((start, end))
    return runs


def needs_space(before: str, after: str) -> bool:
    """ExamDiff omits the spaces between adjacent inline word spans.

    Restore them only when both sides look like words, so hyphenated forms
    such as 'commander-in-chief' are not broken apart.
    """
    if not before or not after:
        return False
    if before[-1].isspace() or after[0].isspace():
        return False
    if re.fullmatch(r"[^\w]+", before) or re.fullmatch(r"[^\w]+", after):
        return False
    if before[-1] in "\"'([{" or after[0] in "\"')]},.;:?!-":
        return False
    if before[-1] == "." and after[0].isdigit():  # e.g. 6.3.19
        return False
    return True


def build_side(panes: list[dict], start: int, end: int, side: str) -> list[dict]:
    """Build a compact list of highlighted text runs for one side of a hunk.

    In an ExamDiff report each pane already contains exactly the text of that
    edition: 'deleted' spans only occur on the original side and 'added' spans
    only on the revised side. Both must be kept so words stay intact.
    """
    out: list[dict] = []
    for i in range(start, end):
        spans = panes[i]["spans"]
        if not spans:
            if out and out[-1]["t"] != "\n":
                out.append({"t": "\n", "k": "same"})
            continue
        for span in spans:
            text = span["t"]
            if out and needs_space(out[-1]["t"], text):
                out[-1]["t"] += " "
            if out and out[-1]["k"] == span["k"] and out[-1]["t"] != "\n":
                out[-1]["t"] += text
            else:
                out.append({"t": text, "k": span["k"]})
    # Normalise: a newline directly after a space/word is fine, but drop
    # duplicate newlines and leading/trailing whitespace on each paragraph.
    cleaned: list[dict] = []
    for seg in out:
        text = seg["t"]
        if text == "\n":
            if cleaned and cleaned[-1]["t"] == "\n":
                continue
            cleaned.append({"t": "\n", "k": "same"})
            continue
        if text.startswith(" ") and cleaned and cleaned[-1]["t"] in ("\n", ""):
            text = text.lstrip()
        if not text:
            continue
        if cleaned and cleaned[-1]["t"] != "\n" and cleaned[-1]["k"] == seg["k"]:
            cleaned[-1]["t"] += text
        else:
            cleaned.append({"t": text, "k": seg["k"]})
    while cleaned and cleaned[0]["t"] == "\n":
        cleaned.pop(0)
    while cleaned and cleaned[-1]["t"] == "\n":
        cleaned.pop()
    return cleaned


def context_before(left: list[dict], right: list[dict], start: int) -> tuple[str, str]:
    """Find the current verse reference and section label before a hunk."""
    verse = "intro"
    section = "INTRO"
    for i in range(start - 1, max(-1, start - 220), -1):
        text = row_text(left[i]).strip() or row_text(right[i]).strip()
        if verse == "intro":
            match = VERSE_RE.search(text)
            if match:
                verse = f"{match.group(1)}.{re.sub(chr(32), '', match.group(2))}"
                if section == "INTRO":
                    section = "TEXT"
        if section == "INTRO" or section == "TEXT":
            upper = text.strip().upper()
            if upper == "TRANSLATION":
                section = "TRANSLATION"
            elif upper == "PURPORT":
                section = "PURPORT"
            elif TEXT_RE.match(text.strip()):
                section = "TEXT"
        if verse != "intro" and section not in ("INTRO", "TEXT"):
            break
    return verse, section


def build_chapter(chapter: int, html: str) -> dict:
    left, right = parse_panes(html)
    runs = merge_runs(left, right)
    verse_map: dict[str, dict] = {}
    hunk_count = 0

    for start, end in runs:
        verse, section = context_before(left, right, start)
        original = build_side(left, start, end, "left")
        revised = build_side(right, start, end, "right")
        if not original and not revised:
            continue
        hunk_count += 1
        vdata = verse_map.setdefault(verse, {"reference": verse, "hunks": []})
        vdata["hunks"].append(
            {
                "id": f"{chapter}-{verse}-{hunk_count}",
                "section": section,
                "original": original,
                "revised": revised,
            }
        )

    return {
        "chapter": chapter,
        "title": CHAPTER_TITLES[chapter],
        "verseCount": len(verse_map),
        "hunkCount": hunk_count,
        "verses": list(verse_map.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="only use cached HTML")
    args = parser.parse_args()

    chapters = []
    for chapter in range(1, 19):
        html = fetch_html(chapter, args.offline)
        data = build_chapter(chapter, html)
        chapters.append(data)
        print(
            f"  chapter {chapter:2d}: {data['hunkCount']:4d} changes "
            f"across {data['verseCount']:3d} verses",
            flush=True,
        )

    total_hunks = sum(c["hunkCount"] for c in chapters)
    dataset = {
        "schema": 1,
        "book": "Bhagavad-gita As It Is",
        "originalEdition": "1972 Macmillan Complete Edition",
        "revisedEdition": "Revised and Enlarged Edition (post-1977)",
        "source": {
            "name": "ISKCON & BBT Prabhupada Book Changes - Bhagavad Gita Changes: Complete List",
            "url": "https://bookchanges.com/bhagavad-gita-changes-complete-list/",
            "note": (
                "Diff reports generated from Bhaktivedanta Vedabase 2003 (original) "
                "and Vedabase 3.1 (revised). Word-for-word synonyms were not compared "
                "in the source reports. Scanning artefacts may remain in the original text."
            ),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chapterCount": len(chapters),
        "hunkCount": total_hunks,
        "chapters": chapters,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_mb = OUT_FILE.stat().st_size / 1024 / 1024
    print(f"\nWrote {OUT_FILE} ({total_hunks} changes, {size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
