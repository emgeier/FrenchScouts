"""Analyze cleaned Gallica text: French word counts + lexicon sentiment.

Reads data/clean/<ark>.txt (and the raw header for title/date), writes one row
per document to data/results.csv.

Word counts use spaCy's French model for proper tokenization. Sentiment uses the
transparent lexicon in sentiment_lexicon.py (polarity in [-1, 1]). See README for
why a lexicon method is the right starting point for historical/humanities text.
"""
from __future__ import annotations

import json
import re
import sys

import pandas as pd

import config
from sentiment_lexicon import POSITIVE, NEGATIVE

_YEAR_RE = re.compile(r"\b(18|19|20)\d{2}\b")


def load_spacy():
    """Load the French spaCy model with a clear error if it's missing."""
    try:
        import spacy
    except ImportError:
        sys.exit("spaCy not installed. Run: pip install -r requirements.txt")
    try:
        nlp = spacy.load(config.SPACY_MODEL, disable=["ner", "parser"])
    except OSError:
        sys.exit(
            f"spaCy model '{config.SPACY_MODEL}' not found.\n"
            f"Install it with: python -m spacy download {config.SPACY_MODEL}"
        )
    # Long OCR documents can exceed the default max_length; raise it generously.
    nlp.max_length = 5_000_000
    return nlp


def load_metadata(ark: str) -> tuple[str, str]:
    """Title + year from the <ark>.meta.json sidecar written by fetch.py."""
    meta_file = config.RAW_DIR / f"{ark}.meta.json"
    if not meta_file.exists():
        return "", ""
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    title = meta.get("title", "")[:200]
    date = meta.get("date", "")
    m = _YEAR_RE.search(date)
    year = m.group(0) if m else date
    return title, year


def analyze_doc(nlp, text: str) -> dict:
    """Word counts + lexicon sentiment for one document."""
    doc = nlp(text)
    total_words = 0
    content_words = 0
    pos_hits = 0
    neg_hits = 0

    for tok in doc:
        if not tok.is_alpha:
            continue
        total_words += 1
        lemma = tok.lemma_.lower()
        if not tok.is_stop:
            content_words += 1
        if lemma in POSITIVE:
            pos_hits += 1
        elif lemma in NEGATIVE:
            neg_hits += 1

    hits = pos_hits + neg_hits
    sentiment = round((pos_hits - neg_hits) / hits, 4) if hits else 0.0

    return {
        "total_words": total_words,
        "content_words": content_words,
        "pos_hits": pos_hits,
        "neg_hits": neg_hits,
        "sentiment_score": sentiment,
    }


def ocr_quality_of(ark: str) -> float:
    """Recompute OCR quality from the cleaned text (cheap, keeps CSV self-contained)."""
    from clean import ocr_quality
    cf = config.CLEAN_DIR / f"{ark}.txt"
    return ocr_quality(cf.read_text(encoding="utf-8")) if cf.exists() else 0.0


def analyze_all() -> pd.DataFrame:
    clean_files = sorted(config.CLEAN_DIR.glob("*.txt"))
    if not clean_files:
        sys.exit("No cleaned files in data/clean — run fetch.py then clean.py first.")

    nlp = load_spacy()
    rows = []
    for i, cf in enumerate(clean_files, 1):
        ark = cf.stem
        print(f"[{i}/{len(clean_files)}] analyzing {ark}...")
        text = cf.read_text(encoding="utf-8")
        title, year = load_metadata(ark)
        metrics = analyze_doc(nlp, text)
        rows.append({
            "ark": ark,
            "title": title,
            "date": year,
            **metrics,
            "ocr_quality": ocr_quality_of(ark),
        })

    df = pd.DataFrame(rows, columns=[
        "ark", "title", "date", "total_words", "content_words",
        "pos_hits", "neg_hits", "sentiment_score", "ocr_quality",
    ])
    df.to_csv(config.RESULTS_CSV, index=False)
    print(f"\nWrote {len(df)} rows -> {config.RESULTS_CSV}")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    analyze_all()
