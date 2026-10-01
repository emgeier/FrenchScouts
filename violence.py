"""Track violence-related vocabulary per issue, over time.

For each cleaned document, counts violence-lexicon lemmas (total and by theme),
and — critically — normalizes by document length as a RATE per 1,000 words, so a
long issue isn't flagged as "more violent" simply for being long.

Outputs:
  data/violence_by_issue.csv   one row per issue (date, counts, rate, themes)
  prints a per-year summary

Usage:
    python violence.py
    python violence.py --min-quality 0.6
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import pandas as pd

import config
from violence_lexicon import THEMES, ALL

_YEAR_RE = re.compile(r"\b(18|19|20)\d{2}\b")


def load_metadata(ark: str) -> tuple[str, str]:
    """Title + full date string from the <ark>.meta.json sidecar."""
    mf = config.RAW_DIR / f"{ark}.meta.json"
    if not mf.exists():
        return "", ""
    meta = json.loads(mf.read_text(encoding="utf-8"))
    return meta.get("title", "")[:120], meta.get("date", "")


def analyze_doc(nlp, text: str) -> dict:
    """Total words + violence counts (overall and per theme) for one document."""
    total_words = 0
    overall = 0
    theme_counts = {name: 0 for name in THEMES}

    for tok in nlp(text):
        if not tok.is_alpha:
            continue
        total_words += 1
        lemma = tok.lemma_.lower()
        if lemma in ALL:
            overall += 1
            for name, words in THEMES.items():
                if lemma in words:
                    theme_counts[name] += 1
                    break

    rate = round(1000 * overall / total_words, 3) if total_words else 0.0
    return {"total_words": total_words, "violence_count": overall,
            "violence_rate_per_1k": rate, **theme_counts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-quality", type=float, default=0.0,
                    help="Skip documents with ocr_quality below this.")
    args = ap.parse_args()

    try:
        import spacy
    except ImportError:
        sys.exit("spaCy not installed. Run: pip install -r requirements.txt")
    try:
        nlp = spacy.load(config.SPACY_MODEL, disable=["ner", "parser"])
    except OSError:
        sys.exit(f"Model missing. Run: python -m spacy download {config.SPACY_MODEL}")
    nlp.max_length = 5_000_000

    from clean import ocr_quality
    files = sorted(config.CLEAN_DIR.glob("*.txt"))
    if not files:
        sys.exit("No cleaned files in data/clean — run fetch.py then clean.py first.")

    rows = []
    for i, f in enumerate(files, 1):
        ark = f.stem
        text = f.read_text(encoding="utf-8")
        if args.min_quality > 0 and ocr_quality(text) < args.min_quality:
            continue
        print(f"  [{i}/{len(files)}] {ark}...", file=sys.stderr)
        title, date = load_metadata(ark)
        m = _YEAR_RE.search(date)
        year = int(m.group(0)) if m else None
        metrics = analyze_doc(nlp, text)
        rows.append({"ark": ark, "title": title, "date": date, "year": year, **metrics})

    if not rows:
        sys.exit("No documents analyzed.")

    df = pd.DataFrame(rows).sort_values(["date", "ark"]).reset_index(drop=True)
    out = config.DATA / "violence_by_issue.csv"
    df.to_csv(out, index=False)
    print(f"\nWrote {len(df)} issue rows -> {out}")

    # Per-year summary (mean rate is the headline metric).
    if df["year"].notna().any():
        summary = (df.dropna(subset=["year"])
                     .groupby("year")
                     .agg(issues=("ark", "size"),
                          mean_rate_per_1k=("violence_rate_per_1k", "mean"),
                          total_violence_words=("violence_count", "sum"))
                     .round(3))
        print("\nViolence vocabulary by year (rate = words per 1,000):")
        print(summary.to_string())


if __name__ == "__main__":
    main()
