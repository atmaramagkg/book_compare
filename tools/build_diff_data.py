#!/usr/bin/env python3
"""Build the app's bundled diff datasets from published source texts.

Most books are built from ExamDiff reports: each report is an HTML table with
two line-aligned panes, whose inline spans map to highlight kinds. Srimad
Bhagavatam is built directly from verse text: the original side comes from
vedabase.cc's clean Markdown files and the revised side from a supplied
Bhaktivedanta VedaBase DOCX. Only changed passages are written to compact JSON
files.

Usage:
    python tools/build_diff_data.py
    python tools/build_diff_data.py --books bg kb
    python tools/build_diff_data.py --books sb
    python tools/build_diff_data.py --books sb --sb-docx /path/to/sb.docx
    python tools/build_diff_data.py --offline   # reuse cached files only
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import random
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "tools" / ".cache"
DATA_DIR = ROOT / "assets" / "data"

BG_URL = "https://bookchanges.com/wp-content/uploads/2009/09/Bg-Chapter-{chapter}-diff.htm"
KB_INDEX_URL = "https://bookchanges.com/krsna-book-complete-list-of-changes/"
CC_INDEX_URL = "https://bookchanges.com/caitanya-caritamrta-changes-%E2%80%94-full-list"

SB_SITEMAP_URL = "https://vedabase.cc/sitemap-en-books.xml"
SB_ORIGINAL_BASE = "https://vedabase.cc"
SB_REVISED_BASE = "https://vedabase.io/en/library"
SB_DOCX_PATH = Path(r"C:\Users\austr\OneDrive\Documents\sb.docx")

# The VedaBase DOCX uses Michael Best's legacy diacritic font encoding.
VEDABASE_UNICODE = {
    ord("Ï"): "Ñ", ord("ï"): "ñ",
    ord("Ä"): "Ā", ord("ä"): "ā",
    ord("É"): "Ī", ord("é"): "ī",
    ord("Ç"): "Ś", ord("ç"): "ś",
    ord("Ü"): "Ū", ord("ü"): "ū",
    ord("Ò"): "Ḍ", ord("ò"): "ḍ",
    ord("Ù"): "Ḥ", ord("ù"): "ḥ",
    ord("ß"): "Ḷ", ord("ÿ"): "ḷ",
    ord("À"): "Ṁ", ord("à"): "ṁ",
    ord("Ì"): "Ṅ", ord("ì"): "ṅ",
    ord("Ë"): "Ṇ", ord("ë"): "ṇ",
    ord("Å"): "Ṛ", ord("å"): "ṛ",
    ord("È"): "Ṝ", ord("è"): "ṝ",
    ord("Ñ"): "Ṣ", ord("ñ"): "ṣ",
    ord("Ö"): "Ṭ", ord("ö"): "ṭ",
    ord("û"): "l̐",
}

BG_CHAPTER_TITLES = {
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

# ExamDiff inline class -> our highlight kind. Older reports use long names,
# newer reports use the short names shown in their legends.
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
    "si": "same",           # identical / ignored line part
    "sc": "same",           # unchanged words inside a changed line
    "sc2": "chg",           # changed in changed
    "sd": "del",            # deleted words
    "sa": "add",            # added words
}

OLD_DIFF_ROW_CLASSES = {"linespan_c", "linespan_a", "linespan_d", "linespan_n", "linespan_o"}
NEW_DIFF_ROW_CLASSES = {"lc", "la", "ld", "ln", "lo"}

BG_REFERENCE_RE = re.compile(r"Bg\.?\s*(\d+)\.(\d+(?:\s*-\s*\d+)?)", re.IGNORECASE)
CC_REFERENCE_RE = re.compile(
    r"^(Adi|Madhya|Antya)\s+(\d+)\.(\d+(?:[\u2013-]\d+)?)", re.IGNORECASE
)
TEXT_RE = re.compile(r"^TEXTS?\s+\d", re.IGNORECASE)


@dataclass(frozen=True)
class BookConfig:
    id: str
    title: str
    short_title: str
    asset: str
    original_edition: str
    revised_edition: str
    original_label: str
    revised_label: str
    reference_prefix: str
    unit_label: str
    unit_label_plural: str
    source_name: str
    source_url: str
    source_note: str
    section_labels: tuple[str, ...]
    default_section: str
    default_reference: str
    reference_style: str


BOOKS: dict[str, BookConfig] = {
    "bg": BookConfig(
        id="bg",
        title="Bhagavad-gita As It Is",
        short_title="Bhagavad-gita",
        asset="bg_diffs.json",
        original_edition="1972 Macmillan Complete Edition",
        revised_edition="Revised and Enlarged Edition (post-1977)",
        original_label="1972 ORIGINAL",
        revised_label="REVISED EDITION",
        reference_prefix="BG",
        unit_label="verse",
        unit_label_plural="verses",
        source_name="ISKCON & BBT Prabhupada Book Changes - Bhagavad Gita Changes: Complete List",
        source_url="https://bookchanges.com/bhagavad-gita-changes-complete-list/",
        source_note=(
            "Diff reports generated from Bhaktivedanta Vedabase 2003 (original) "
            "and Vedabase 3.1 (revised). Word-for-word synonyms were not compared "
            "in the source reports. Scanning artefacts may remain in the original text."
        ),
        section_labels=("TRANSLATION", "PURPORT", "TEXT"),
        default_section="INTRO",
        default_reference="intro",
        reference_style="bg",
    ),
    "kb": BookConfig(
        id="kb",
        title="Krsna: The Supreme Personality of Godhead",
        short_title="Krsna Book",
        asset="kb_diffs.json",
        original_edition="1970 original edition",
        revised_edition="Vedabase 2013 revised edition",
        original_label="1970 ORIGINAL",
        revised_label="REVISED EDITION",
        reference_prefix="",
        unit_label="passage",
        unit_label_plural="passages",
        source_name="ISKCON & BBT Prabhupada Book Changes - Krsna Book: Complete List of Changes",
        source_url=KB_INDEX_URL,
        source_note=(
            "Diff reports compare the 1970 original text with the Vedabase 2013 "
            "text. Krsna Book is continuous prose, so changes are grouped as one "
            "passage per chapter. The original side is not a facsimile of the "
            "printed edition and may contain scanning artefacts."
        ),
        section_labels=(),
        default_section="Passage",
        default_reference="Chapter text",
        reference_style="none",
    ),
    "cc": BookConfig(
        id="cc",
        title="Sri Caitanya-caritamrta",
        short_title="Caitanya-caritamrta",
        asset="cc_diffs.json",
        original_edition="1975 original edition",
        revised_edition="Vedabase 2003 revised edition",
        original_label="1975 ORIGINAL",
        revised_label="REVISED EDITION",
        reference_prefix="",
        unit_label="verse",
        unit_label_plural="verses",
        source_name="ISKCON & BBT Prabhupada Book Changes - Caitanya-caritamrta Changes: Full List",
        source_url=CC_INDEX_URL,
        source_note=(
            "These reports compare the 1975 original edition with the 2003 "
            "revised edition. Word-for-word synonyms were not compared in the "
            "source reports. The original side is not a facsimile of the printed "
            "edition and may contain scanning artefacts."
        ),
        section_labels=("SYNONYMS", "TRANSLATION", "PURPORT", "TEXT"),
        default_section="TEXT",
        default_reference="intro",
        reference_style="cc",
    ),
    "sb": BookConfig(
        id="sb",
        title="Srimad-Bhagavatam",
        short_title="Srimad-Bhagavatam",
        asset="sb_diffs.json",
        original_edition="Original pre-revision edition printed during Prabhupada's lifetime",
        revised_edition="Bhaktivedanta VedaBase 2025 revised edition",
        original_label="ORIGINAL EDITION",
        revised_label="REVISED EDITION",
        reference_prefix="SB",
        unit_label="verse",
        unit_label_plural="verses",
        source_name=(
            "vedabase.cc original edition compared with Bhaktivedanta "
            "VedaBase 2025"
        ),
        source_url="https://vedabase.io/en/library/",
        source_note=(
            "The original side is vedabase.cc's text of the editions printed "
            "during Srila Prabhupada's lifetime, verified against scans of the "
            "printed books. The revised side is exported from the supplied "
            "Bhaktivedanta VedaBase 2025 DOCX. Devanagari, transliteration and "
            "word-for-word synonyms are not compared. Coverage ends at SB 10.13 "
            "because no original lifetime edition was printed for the later "
            "chapters of Canto 10 or for Cantos 11-12."
        ),
        section_labels=("TRANSLATION", "PURPORT"),
        default_section="TRANSLATION",
        default_reference="",
        reference_style="sb",
    ),
}


@dataclass(frozen=True)
class ChapterSpec:
    number: int
    number_label: str
    title: str
    url: str


@dataclass(frozen=True)
class VerseSpec:
    canto: int
    chapter: int
    verse: str
    original_url: str
    revised_url: str

    @property
    def key(self) -> str:
        return f"{self.canto}-{self.chapter}-{self.verse}"

    @property
    def reference(self) -> str:
        return f"{self.canto}.{self.chapter}.{self.verse}"

    @property
    def chapter_number(self) -> int:
        return self.canto * 100 + self.chapter

    @property
    def chapter_label(self) -> str:
        return f"{self.canto}.{self.chapter}"


def fetch_url(url: str, cache_name: str, offline: bool, min_bytes: int = 1000) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / cache_name
    if path.exists() and path.stat().st_size > min_bytes:
        return path.read_text(encoding="utf-8", errors="replace")
    if offline:
        raise FileNotFoundError(f"No cached HTML for {url}: {path}")

    print(f"  downloading {cache_name} ...", flush=True)
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


def fetch_files_parallel(
    jobs: list[tuple[str, str, int]], offline: bool
) -> dict[str, str]:
    """Fetch many small source files, reusing cached copies when possible."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    pending: list[tuple[str, str, int]] = []
    unavailable: list[tuple[str, str]] = []

    for url, cache_name, min_bytes in jobs:
        path = CACHE_DIR / cache_name
        if path.exists() and path.stat().st_size > min_bytes:
            results[cache_name] = path.read_text(encoding="utf-8", errors="replace")
        elif offline:
            raise FileNotFoundError(f"No cached source for {url}: {path}")
        else:
            pending.append((url, cache_name, min_bytes))

    if pending:
        print(
            f"  downloading {len(pending)} source files with 3 workers ...",
            flush=True,
        )

        def download(job: tuple[str, str, int]) -> tuple[str, str | None]:
            url, cache_name, min_bytes = job
            path = CACHE_DIR / cache_name
            temp_path = CACHE_DIR / f"{cache_name}.part"
            status = "000"

            for attempt in range(8):
                if temp_path.exists():
                    temp_path.unlink()
                process = subprocess.run(
                    [
                        "curl.exe", "-L", "-sS", "--compressed",
                        "--connect-timeout", "20", "--max-time", "90",
                        "--retry", "2", "--retry-delay", "2",
                        "--retry-connrefused",
                        "-A", "Mozilla/5.0",
                        "-o", str(temp_path), "-w", "%{http_code}", url,
                    ],
                    capture_output=True,
                    text=True,
                )
                output = process.stdout.strip()
                status = output.splitlines()[-1] if output else "000"
                if (
                    status == "200"
                    and temp_path.exists()
                    and temp_path.stat().st_size > min_bytes
                ):
                    temp_path.replace(path)
                    return cache_name, path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                if status.startswith("4"):
                    if temp_path.exists():
                        temp_path.unlink()
                    unavailable.append((url, status))
                    return cache_name, None
                if temp_path.exists():
                    temp_path.unlink()
                time.sleep(min(2 ** attempt, 20) + random.uniform(0, 1))

            unavailable.append((url, status))
            return cache_name, None

        done = 0
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(download, job): job for job in pending}
            for future in as_completed(futures):
                cache_name, text = future.result()
                if text is not None:
                    results[cache_name] = text
                done += 1
                if done % 1000 == 0:
                    print(f"  downloaded {done}/{len(pending)}", flush=True)

    if unavailable:
        print(
            f"  warning: {len(unavailable)} source files unavailable; "
            "affected verses will be skipped",
            flush=True,
        )
    return results


def sb_verse_specs(offline: bool) -> list[VerseSpec]:
    """List every lifetime-published Srimad-Bhagavatam verse in the sitemap."""
    xml = fetch_url(SB_SITEMAP_URL, "sb-sitemap.xml", offline, min_bytes=100000)
    pattern = re.compile(
        r"<loc>https://vedabase\.cc/sb/(\d+)/(\d+)/(\d+)/</loc>"
    )
    specs: list[VerseSpec] = []
    seen: set[str] = set()
    for canto_s, chapter_s, verse in pattern.findall(xml):
        canto, chapter = int(canto_s), int(chapter_s)
        if canto > 10 or (canto == 10 and chapter > 13):
            continue  # no original lifetime edition was printed for these
        key = f"{canto}-{chapter}-{verse}"
        if key in seen:
            continue
        seen.add(key)
        specs.append(
            VerseSpec(
                canto=canto,
                chapter=chapter,
                verse=verse,
                original_url=f"{SB_ORIGINAL_BASE}/sb/{canto}/{chapter}/{verse}.md",
                revised_url=f"{SB_REVISED_BASE}/sb/{canto}/{chapter}/{verse}/",
            )
        )
    return sorted(specs, key=lambda s: (s.canto, s.chapter, int(s.verse)))


def normalize_text(text: str) -> str:
    text = html_module.unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def vedabase_unicode(text: str) -> str:
    """Convert VedaBase's legacy diacritic font encoding to Unicode."""
    return text.translate(VEDABASE_UNICODE)


def load_sb_docx(
    path: Path,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, str]]:
    """Read revised Translation/Purport paragraphs and chapter titles from a DOCX."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))

    paragraphs = []
    for para in root.findall(".//w:p", ns):
        text = "".join(
            node.text or "" for node in para.findall(".//w:t", ns)
        ).strip()
        if text:
            paragraphs.append(vedabase_unicode(text))

    verse_re = re.compile(r"^SB (\d+)\.(\d+)\.(\d+)$")
    chapter_re = re.compile(r"^SB (\d+)\.(\d+): (.+)$")
    verses: dict[str, dict[str, list[str]]] = {}
    titles: dict[str, str] = {}
    current: str | None = None
    section: str | None = None

    for text in paragraphs:
        chapter_match = chapter_re.match(text)
        if chapter_match:
            canto, chapter, title = chapter_match.groups()
            titles[f"{int(canto)}-{int(chapter)}"] = normalize_text(title)
            section = None
            continue
        match = verse_re.match(text)
        if match:
            canto, chapter, verse = match.groups()
            key = f"{int(canto)}-{int(chapter)}-{verse}"
            verses[key] = {"TRANSLATION": [], "PURPORT": []}
            current = key
            section = None
            continue
        if current is None:
            continue

        upper = text.strip().upper()
        if upper == "TRANSLATION":
            section = "TRANSLATION"
            continue
        if upper == "PURPORT":
            section = "PURPORT"
            continue
        if upper in {"TEXT", "SYNONYMS", "DEVANAGARI"}:
            section = None
            continue
        if section is None:
            continue

        clean = normalize_text(text)
        if clean and clean not in verses[current][section]:
            verses[current][section].append(clean)

    return verses, titles


def markdown_sections(markdown: str, heading: str) -> list[str]:
    """Return paragraphs under one '## Heading' block in a vedabase.cc .md file."""
    lines = markdown.splitlines()
    start = None
    wanted = f"## {heading.lower()}"
    for index, line in enumerate(lines):
        if line.strip().lower() == wanted:
            start = index + 1
            break
    if start is None:
        return []

    block: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        cleaned = line.strip()
        if cleaned.startswith(">"):
            cleaned = cleaned[1:].strip()
        cleaned = cleaned.replace("**", "").replace("*", "")
        block.append(cleaned)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in block + [""]:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(normalize_text(" ".join(current)))
            current = []
    return [p for p in paragraphs if p]


def append_segment(segments: list[dict], kind: str, text: str) -> None:
    if not text:
        return
    if segments and segments[-1]["k"] == kind:
        segments[-1]["t"] += text
    else:
        segments.append({"t": text, "k": kind})


THUS_END_RE = re.compile(r"^Thus end the Bhaktivedanta purports", re.IGNORECASE)


def normalize_sections(
    translation: list[str], purport: list[str]
) -> tuple[list[str], list[str]]:
    """Keep the 'Thus end...' note in the same section on both sites."""
    moved = [p for p in translation if THUS_END_RE.match(p)]
    if moved:
        translation = [p for p in translation if not THUS_END_RE.match(p)]
        for paragraph in moved:
            if paragraph not in purport:
                purport.append(paragraph)
    return translation, purport


def diff_passages(original_paragraphs: list[str], revised_paragraphs: list[str]) -> list[dict]:
    """Produce one or more hunks for a changed Translation or Purport section."""
    original = " ".join(original_paragraphs)
    revised = " ".join(revised_paragraphs)
    if not original and not revised:
        return []
    if original == revised:
        return []

    if not original:
        return [{"original": [], "revised": [{"t": revised, "k": "add"}]}]
    if not revised:
        return [{"original": [{"t": original, "k": "del"}], "revised": []}]

    left_tokens = re.findall(r"\S+\s*", original)
    right_tokens = re.findall(r"\S+\s*", revised)
    matcher = SequenceMatcher(None, left_tokens, right_tokens, autojunk=False)
    left: list[dict] = []
    right: list[dict] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for index in range(i1, i2):
                append_segment(left, "same", left_tokens[index])
            for index in range(j1, j2):
                append_segment(right, "same", right_tokens[index])
        elif tag == "replace":
            paired = min(i2 - i1, j2 - j1)
            for offset in range(paired):
                append_segment(left, "chg", left_tokens[i1 + offset])
                append_segment(right, "chg", right_tokens[j1 + offset])
            for index in range(i1 + paired, i2):
                append_segment(left, "del", left_tokens[index])
            for index in range(j1 + paired, j2):
                append_segment(right, "add", right_tokens[index])
        elif tag == "delete":
            for index in range(i1, i2):
                append_segment(left, "del", left_tokens[index])
        elif tag == "insert":
            for index in range(j1, j2):
                append_segment(right, "add", right_tokens[index])

    return [{"original": left, "revised": right}]


def build_sb_dataset(offline: bool) -> tuple[dict, dict]:
    config = BOOKS["sb"]
    specs = sb_verse_specs(offline)
    print(f"  {len(specs)} lifetime-published verses", flush=True)

    revised_verses, chapter_titles = load_sb_docx(SB_DOCX_PATH)
    print(f"  {len(revised_verses)} revised verses in VedaBase DOCX", flush=True)

    jobs: list[tuple[str, str, int]] = [
        (spec.original_url, f"sb-orig-{spec.key}.md", 200) for spec in specs
    ]
    files = fetch_files_parallel(jobs, offline)

    chapters: dict[int, dict] = {}
    skipped = 0
    for index, spec in enumerate(specs, start=1):
        original_md = files.get(f"sb-orig-{spec.key}.md")
        revised_sections = revised_verses.get(spec.key)
        if original_md is None or revised_sections is None:
            skipped += 1
            if skipped <= 20:
                print(f"  skipping SB {spec.reference}: source unavailable", flush=True)
            continue
        chapter_number = spec.chapter_number

        if chapter_number not in chapters:
            chapter_key = f"{spec.canto}-{spec.chapter}"
            chapters[chapter_number] = {
                "chapter": chapter_number,
                "numberLabel": spec.chapter_label,
                "title": chapter_titles.get(
                    chapter_key, f"Canto {spec.canto}, Chapter {spec.chapter}"
                ),
                "sectionCount": 0,
                "hunkCount": 0,
                "sections": [],
            }

        original_translation = markdown_sections(original_md, "TRANSLATION")
        original_purport = markdown_sections(original_md, "PURPORT")
        revised_translation = revised_sections["TRANSLATION"]
        revised_purport = revised_sections["PURPORT"]
        original_translation, original_purport = normalize_sections(
            original_translation, original_purport
        )
        revised_translation, revised_purport = normalize_sections(
            revised_translation, revised_purport
        )
        section_paragraphs = {
            "TRANSLATION": (original_translation, revised_translation),
            "PURPORT": (original_purport, revised_purport),
        }

        sections: dict[str, dict] = {}
        for heading in config.section_labels:
            original_paragraphs, revised_paragraphs = section_paragraphs[heading]
            hunks = diff_passages(original_paragraphs, revised_paragraphs)
            if not hunks:
                continue
            section = sections.setdefault(
                spec.reference, {"reference": spec.reference, "hunks": []}
            )
            for hunk in hunks:
                section["hunks"].append(
                    {
                        "id": f"sb-{spec.key}-{heading.lower()}-{len(section['hunks']) + 1}",
                        "section": heading,
                        "original": hunk["original"],
                        "revised": hunk["revised"],
                    }
                )

        if sections:
            chapter = chapters[chapter_number]
            chapter["sections"].extend(sections.values())
            chapter["sectionCount"] += len(sections)
            chapter["hunkCount"] += sum(len(s["hunks"]) for s in sections.values())

        if index % 500 == 0:
            print(f"  processed {index}/{len(specs)} verses", flush=True)

    if skipped:
        print(f"  skipped {skipped} verses with unavailable sources", flush=True)
    ordered_chapters = [chapters[key] for key in sorted(chapters)]
    total_hunks = sum(c["hunkCount"] for c in ordered_chapters)
    dataset = {
        "schema": 2,
        "id": config.id,
        "book": config.title,
        "shortTitle": config.short_title,
        "originalEdition": config.original_edition,
        "revisedEdition": config.revised_edition,
        "originalLabel": config.original_label,
        "revisedLabel": config.revised_label,
        "referencePrefix": config.reference_prefix,
        "unitLabel": config.unit_label,
        "unitLabelPlural": config.unit_label_plural,
        "source": {
            "name": config.source_name,
            "url": config.source_url,
            "note": config.source_note,
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chapterCount": len(ordered_chapters),
        "sectionCount": sum(c["sectionCount"] for c in ordered_chapters),
        "hunkCount": total_hunks,
        "chapters": ordered_chapters,
    }
    manifest = {
        "id": config.id,
        "title": config.title,
        "shortTitle": config.short_title,
        "asset": config.asset,
        "originalEdition": config.original_edition,
        "revisedEdition": config.revised_edition,
        "chapterCount": len(ordered_chapters),
        "hunkCount": total_hunks,
    }
    return dataset, manifest


def bg_chapters(offline: bool) -> list[ChapterSpec]:
    del offline
    return [
        ChapterSpec(
            number=chapter,
            number_label=str(chapter),
            title=BG_CHAPTER_TITLES[chapter],
            url=BG_URL.format(chapter=chapter),
        )
        for chapter in range(1, 19)
    ]


def kb_chapters(offline: bool) -> list[ChapterSpec]:
    html = fetch_url(KB_INDEX_URL, "kb-index.html", offline, min_bytes=5000)
    soup = BeautifulSoup(html, "html.parser")
    specs: list[ChapterSpec] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(KB_INDEX_URL, anchor["href"])
        if "/KrsnaBook/diff_" not in href:
            continue
        label = anchor.get_text(" ", strip=True)
        match = re.search(r"Chapter\s+(\d+)", label, re.IGNORECASE)
        if not match:
            continue
        number = int(match.group(1))
        specs.append(
            ChapterSpec(
                number=number,
                number_label=str(number),
                title=f"Krsna Book chapter {number}",
                url=href,
            )
        )
    return sorted(specs, key=lambda spec: spec.number)


def cc_chapters(offline: bool) -> list[ChapterSpec]:
    html = fetch_url(CC_INDEX_URL, "cc-index.html", offline, min_bytes=5000)
    soup = BeautifulSoup(html, "html.parser")
    specs: list[ChapterSpec] = []
    division_order = {"Intro": 0, "Adi": 1, "Madhya": 2, "Antya": 3}
    for anchor in soup.find_all("a", href=True):
        href = urljoin(CC_INDEX_URL, anchor["href"])
        if "/cc/CC_" not in href or "2014" in href.lower() or not href.lower().endswith(".htm"):
            continue
        label = anchor.get_text(" ", strip=True).rstrip(":")
        if label.lower().startswith("introduction"):
            division, number, number_label, title = "Intro", 0, "Intro", "Introduction"
        else:
            match = re.match(r"(Adi|Madhya|Antya)\s+(\d+)", label, re.IGNORECASE)
            if not match:
                continue
            division = match.group(1).capitalize()
            number = int(match.group(2))
            short = {"Adi": "A", "Madhya": "M", "Antya": "An"}[division]
            number_label = f"{short}{number}"
            title = label
        specs.append(
            ChapterSpec(
                number=division_order[division] * 1000 + number,
                number_label=number_label,
                title=title,
                url=href,
            )
        )
    return sorted(specs, key=lambda spec: spec.number)


def chapter_specs(book_id: str, offline: bool) -> list[ChapterSpec]:
    if book_id == "bg":
        return bg_chapters(offline)
    if book_id == "kb":
        return kb_chapters(offline)
    if book_id == "cc":
        return cc_chapters(offline)
    raise ValueError(f"Unknown book: {book_id}")


def pane_node(soup: BeautifulSoup, side: str):
    """Locate one side of an ExamDiff report, old or new markup."""
    if side == "left":
        node = soup.find(id="d21") or soup.find(id="file1")
    else:
        node = soup.find(id="d22") or soup.find(id="file2")
    if node is None:
        raise ValueError(f"Could not find the {side} diff pane")
    content = node if node.name == "div" and node.get("id", "").startswith("d2") else None
    if content is None:
        content = node.find("td", class_="content")
    if content is None:
        raise ValueError(f"Could not find content for the {side} pane")
    return content


def parse_row(div) -> dict:
    """Turn one diff row into structured spans."""
    classes = div.get("class") or []
    is_diff = any(c in OLD_DIFF_ROW_CLASSES or c in NEW_DIFF_ROW_CLASSES for c in classes)
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
    return {"diff": is_diff, "spans": spans}


def parse_panes(html: str) -> tuple[list[dict], list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    left_node = pane_node(soup, "left")
    right_node = pane_node(soup, "right")
    left = [parse_row(d) for d in left_node.find_all("div", recursive=False)]
    right = [parse_row(d) for d in right_node.find_all("div", recursive=False)]

    # A few source reports have a stray trailing blank row in one pane. Drop
    # trailing blanks from the longer side, then pad if a real line is unmatched.
    while len(left) > len(right) and not left[-1]["spans"]:
        left.pop()
    while len(right) > len(left) and not right[-1]["spans"]:
        right.pop()
    if len(left) < len(right):
        left.extend({"diff": False, "spans": []} for _ in range(len(right) - len(left)))
    elif len(right) < len(left):
        right.extend({"diff": False, "spans": []} for _ in range(len(left) - len(right)))
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
    """ExamDiff omits spaces between adjacent inline word spans.

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


def build_side(panes: list[dict], start: int, end: int) -> list[dict]:
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


def detect_reference(text: str, config: BookConfig) -> str | None:
    if config.reference_style == "bg":
        match = BG_REFERENCE_RE.search(text)
        if match:
            return f"{match.group(1)}.{re.sub(' ', '', match.group(2))}"
    elif config.reference_style == "cc":
        match = CC_REFERENCE_RE.match(text.strip())
        if match:
            verse = match.group(3).replace("\u2013", "-")
            return f"{match.group(1).capitalize()} {match.group(2)}.{verse}"
    return None


def detect_section(text: str, config: BookConfig, fallback: str) -> str:
    upper = text.strip().upper()
    if upper in config.section_labels:
        return upper
    if TEXT_RE.match(upper):
        return "TEXT"
    return fallback


def context_before(
    left: list[dict], right: list[dict], start: int, config: BookConfig
) -> tuple[str, str]:
    """Find the current reference and section label before a hunk."""
    reference = config.default_reference
    section = config.default_section
    for i in range(start - 1, max(-1, start - 220), -1):
        text = row_text(left[i]).strip() or row_text(right[i]).strip()
        if not text:
            continue
        found = detect_reference(text, config)
        if found is not None:
            reference = found
            if config.reference_style in ("bg", "cc"):
                section = "TEXT"
        section = detect_section(text, config, section)
        if found is not None and section != config.default_section:
            break
    return reference, section


def derive_title(spec: ChapterSpec, panes: tuple[list[dict], list[dict]], book_id: str) -> str:
    if book_id == "bg":
        return spec.title
    left, right = panes
    # The revised pane usually has the cleanest heading; fall back to original.
    for row in right[:12] + left[:12]:
        text = row_text(row).strip()
        if not text or text.startswith("Generated"):
            continue
        if book_id == "kb":
            if ":" in text:
                text = text.split(":", 1)[1].strip()
            if "/" in text:
                text = text.split("/", 1)[-1].strip()
            return text or spec.title
        if book_id == "cc":
            if "-" in text.split(":", 1)[0]:
                head, _, tail = text.partition("-")
                text = (head + tail).strip()
            if ":" in text:
                text = text.split(":", 1)[1].strip()
            if text.lower().startswith("the "):
                text = text[4:].strip()
            return f"{spec.title} — {text}" if text else spec.title
    return spec.title


def build_chapter(spec: ChapterSpec, html: str, config: BookConfig) -> dict:
    left, right = parse_panes(html)
    runs = merge_runs(left, right)
    section_map: dict[str, dict] = {}
    hunk_count = 0

    for start, end in runs:
        reference, section = context_before(left, right, start, config)
        original = build_side(left, start, end)
        revised = build_side(right, start, end)
        if not original and not revised:
            continue
        hunk_count += 1
        sdata = section_map.setdefault(
            reference, {"reference": reference, "hunks": []}
        )
        sdata["hunks"].append(
            {
                "id": f"{config.id}-{spec.number}-{reference}-{hunk_count}",
                "section": section,
                "original": original,
                "revised": revised,
            }
        )

    return {
        "chapter": spec.number,
        "numberLabel": spec.number_label,
        "title": derive_title(spec, (left, right), config.id),
        "sectionCount": len(section_map),
        "hunkCount": hunk_count,
        "sections": list(section_map.values()),
    }


def build_dataset(book_id: str, offline: bool) -> tuple[dict, dict]:
    if book_id == "sb":
        return build_sb_dataset(offline)
    config = BOOKS[book_id]
    specs = chapter_specs(book_id, offline)
    chapters: list[dict] = []
    for spec in specs:
        html = fetch_url(
            spec.url,
            f"{book_id}-{spec.number:04d}.html",
            offline,
            min_bytes=10000,
        )
        data = build_chapter(spec, html, config)
        chapters.append(data)
        print(
            f"  {config.short_title:22s} {spec.number_label:>5s}: "
            f"{data['hunkCount']:4d} changes",
            flush=True,
        )

    total_hunks = sum(c["hunkCount"] for c in chapters)
    dataset = {
        "schema": 2,
        "id": config.id,
        "book": config.title,
        "shortTitle": config.short_title,
        "originalEdition": config.original_edition,
        "revisedEdition": config.revised_edition,
        "originalLabel": config.original_label,
        "revisedLabel": config.revised_label,
        "referencePrefix": config.reference_prefix,
        "unitLabel": config.unit_label,
        "unitLabelPlural": config.unit_label_plural,
        "source": {
            "name": config.source_name,
            "url": config.source_url,
            "note": config.source_note,
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chapterCount": len(chapters),
        "sectionCount": sum(c["sectionCount"] for c in chapters),
        "hunkCount": total_hunks,
        "chapters": chapters,
    }
    manifest = {
        "id": config.id,
        "title": config.title,
        "shortTitle": config.short_title,
        "asset": config.asset,
        "originalEdition": config.original_edition,
        "revisedEdition": config.revised_edition,
        "chapterCount": len(chapters),
        "hunkCount": total_hunks,
    }
    return dataset, manifest


def main() -> int:
    global SB_DOCX_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline", action="store_true", help="only use cached source files"
    )
    parser.add_argument(
        "--books",
        nargs="+",
        choices=sorted(BOOKS),
        default=sorted(BOOKS),
        help="books to rebuild (default: all)",
    )
    parser.add_argument(
        "--sb-docx",
        type=Path,
        default=SB_DOCX_PATH,
        help=f"VedaBase DOCX for the revised SB text (default: {SB_DOCX_PATH})",
    )
    args = parser.parse_args()
    SB_DOCX_PATH = args.sb_docx
    if "sb" in args.books and not SB_DOCX_PATH.exists():
        raise FileNotFoundError(f"VedaBase DOCX not found: {SB_DOCX_PATH}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifests: list[dict] = []
    for book_id in args.books:
        print(f"\nBuilding {BOOKS[book_id].title}", flush=True)
        dataset, manifest = build_dataset(book_id, args.offline)
        out_file = DATA_DIR / BOOKS[book_id].asset
        out_file.write_text(
            json.dumps(dataset, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        manifests.append(manifest)
        size_mb = out_file.stat().st_size / 1024 / 1024
        print(
            f"Wrote {out_file} ({dataset['hunkCount']} changes, {size_mb:.2f} MB)",
            flush=True,
        )

    manifest_path = DATA_DIR / "books.json"
    existing = []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            existing = []
    by_id = {entry["id"]: entry for entry in existing if isinstance(entry, dict) and "id" in entry}
    by_id.update({entry["id"]: entry for entry in manifests})
    ordered = [by_id[key] for key in sorted(BOOKS) if key in by_id]
    ordered += [entry for key, entry in by_id.items() if key not in BOOKS]
    manifest_path.write_text(
        json.dumps(ordered, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"\nWrote {manifest_path} ({len(ordered)} books)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
