"""Clean cached Gallica OCR text: separate the bibliographic header, dehyphenate
line-wrapped words, normalize whitespace, and estimate OCR quality.

Reads data/raw/<ark>.txt, writes data/clean/<ark>.txt. Resumable.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import config

# A line-wrapped word in OCR looks like "révo-\nlution" — join across the break.
_HYPHEN_WRAP = re.compile(r"(\w+)[-\u00ad]\s*\n\s*(\w+)")
# Collapse runs of blank lines / whitespace.
_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
# A "word-ish" token for the quality heuristic (letters incl. French accents).
_WORDISH = re.compile(r"[A-Za-zÀ-ÿ]{2,}")


def split_header(raw: str) -> tuple[str, str]:
    """Split the .texteBrut response into (header, body).

    Gallica prepends bibliographic info, then the OCR body. They are typically
    separated by the first run of 2+ blank lines. Best-effort: if we can't find a
    clear split, treat the whole thing as body with an empty header.
    """
    parts = re.split(r"\n\s*\n\s*\n", raw, maxsplit=1)
    if len(parts) == 2 and len(parts[0]) < 2000:
        # Header is usually short; guard against splitting mid-body.
        return parts[0].strip(), parts[1]
    # Fallback: first blank-line gap.
    parts = re.split(r"\n\s*\n", raw, maxsplit=1)
    if len(parts) == 2 and len(parts[0]) < 2000:
        return parts[0].strip(), parts[1]
    return "", raw


def dehyphenate(text: str) -> str:
    """Join words split across line breaks by an end-of-line hyphen."""
    prev = None
    # Repeat until stable (handles rare double-wraps).
    while prev != text:
        prev = text
        text = _HYPHEN_WRAP.sub(r"\1\2", text)
    return text


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTISPACE.sub(" ", text)
    text = _MULTINEWLINE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def ocr_quality(text: str) -> float:
    """Rough 0..1 OCR-quality estimate.

    Heuristic: fraction of whitespace-separated tokens that look like real words
    (>=2 alphabetic chars, no digits/garbage mixed in). Clean prose scores high;
    garbled scans score low. This is a RELATIVE signal for filtering, not an
    absolute accuracy measure.
    """
    tokens = text.split()
    if not tokens:
        return 0.0
    good = sum(1 for t in tokens if _WORDISH.fullmatch(t.strip(".,;:!?()[]«»\"'")))
    return round(good / len(tokens), 3)


def clean_text(raw: str) -> tuple[str, float]:
    """Clean ALTO-sourced OCR body text. Returns (cleaned_body, ocr_quality).

    (ALTO text has no bibliographic header — metadata lives in the .meta.json
    sidecar — so there is nothing to split off here.)
    """
    body = dehyphenate(raw)
    body = normalize_whitespace(body)
    return body, ocr_quality(body)


def clean_all(force: bool = False) -> int:
    raw_files = sorted(config.RAW_DIR.glob("*.txt"))
    if not raw_files:
        print("No raw files in data/raw — run fetch.py first.")
        return 0
    n = 0
    for rf in raw_files:
        out = config.CLEAN_DIR / rf.name
        if out.exists() and not force:
            continue
        raw = rf.read_text(encoding="utf-8")
        body, q = clean_text(raw)
        out.write_text(body, encoding="utf-8")
        print(f"{rf.stem}: cleaned ({len(body):,} chars, ocr_quality={q})")
        n += 1
    print(f"\nCleaned {n} new file(s); {len(raw_files)} total.")
    return n


if __name__ == "__main__":
    clean_all(force="--force" in sys.argv)
