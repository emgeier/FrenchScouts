"""Most frequent CONTENT words across the whole scouting-journal corpus.

Content words = nouns, verbs, adjectives, adverbs (words that carry meaning).
Excluded: stopwords, pronouns, prepositions, articles, conjunctions, auxiliaries,
determiners, numbers, punctuation, and OCR-garbage tokens.

Method:
  - read every cleaned document (data/clean/*.txt; falls back to cleaning raw/)
  - tag part-of-speech with the French spaCy model and keep only NOUN/PROPN?/
    VERB/ADJ/ADV content words (PROPN excluded by default — see --keep-propn)
  - lemmatize so plurals/inflections collapse (scouts->scout, chefs->chef)
  - drop OCR junk (no vowel, <3 chars, non-alphabetic)
  - aggregate corpus-wide frequency AND document frequency (how many docs use it)

Outputs:
  data/top_words.csv   full ranked table
  prints the top N (default 100) to the console

Usage:
    python top_words.py                 # top 100
    python top_words.py --top 50
    python top_words.py --keep-propn     # include proper nouns (names, places)
    python top_words.py --min-quality 0.6
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

import pandas as pd

import config

# Content-word POS tags (Universal POS). Pronouns/adpositions/determiners/
# conjunctions/auxiliaries/numerals are deliberately excluded.
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV"}

_HAS_VOWEL = re.compile(r"[aeiouyàâäéèêëïîôöùûüœæ]", re.IGNORECASE)

# A few high-frequency, low-connotation lemmas spaCy tags as content words but
# that are structurally empty in practice (common in periodicals). Editable.
EXTRA_STOP = {
    "être", "avoir", "faire", "plus", "tout", "aussi", "très", "bien", "cet",
    "cette", "an", "année", "numéro", "page", "revue", "etc", "mois", "jour",
}


def iter_clean_texts(min_quality: float):
    """Yield (ark, text) for every cleaned document, optionally quality-filtered."""
    from clean import ocr_quality
    files = sorted(config.CLEAN_DIR.glob("*.txt"))
    if not files:
        sys.exit("No cleaned files in data/clean — run: python clean.py (after fetch).")
    for f in files:
        text = f.read_text(encoding="utf-8")
        if min_quality > 0 and ocr_quality(text) < min_quality:
            continue
        yield f.stem, text


def is_real_word(lemma: str) -> bool:
    """Reject OCR garbage: must be alphabetic, >=3 chars, and contain a vowel."""
    return lemma.isalpha() and len(lemma) >= 3 and bool(_HAS_VOWEL.search(lemma))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100, help="How many words to show.")
    ap.add_argument("--keep-propn", action="store_true",
                    help="Also count proper nouns (names, places).")
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

    pos_keep = set(CONTENT_POS)
    if args.keep_propn:
        pos_keep.add("PROPN")

    total = Counter()      # corpus-wide token frequency
    doc_freq = Counter()   # number of documents each lemma appears in
    n_docs = 0

    for ark, text in iter_clean_texts(args.min_quality):
        n_docs += 1
        print(f"  [{n_docs}] {ark}...", file=sys.stderr)
        seen_here = set()
        for tok in nlp(text):
            if tok.pos_ not in pos_keep or tok.is_stop:
                continue
            lemma = tok.lemma_.lower().strip()
            if lemma in EXTRA_STOP or not is_real_word(lemma):
                continue
            total[lemma] += 1
            seen_here.add(lemma)
        for lemma in seen_here:
            doc_freq[lemma] += 1

    if not total:
        sys.exit("No content words found — check that cleaned text exists.")

    rows = [
        {"rank": i, "word": w, "frequency": c, "doc_count": doc_freq[w]}
        for i, (w, c) in enumerate(total.most_common(), start=1)
    ]
    df = pd.DataFrame(rows)
    out = config.DATA / "top_words.csv"
    df.to_csv(out, index=False)

    topn = df.head(args.top)
    print(f"\nAnalyzed {n_docs} document(s). "
          f"{len(total):,} distinct content lemmas; full table -> {out}\n")
    print(f"Top {args.top} content words (lemma, total frequency, # docs):")
    print(topn.to_string(index=False))


if __name__ == "__main__":
    main()
