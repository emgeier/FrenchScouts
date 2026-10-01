"""Plot word counts and sentiment over time from data/results.csv.

Produces PNGs in data/plots/:
  - sentiment_over_time.png   mean sentiment per year (+ per-doc scatter)
  - wordcount_over_time.png   mean total/content words per year
  - docs_per_year.png         number of documents per year (coverage)
  - sentiment_vs_quality.png  sanity check: is sentiment driven by OCR noise?

Usage:
    python visualize.py
    python visualize.py --min-quality 0.6   # drop low-OCR-quality docs first
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

import config

PLOTS_DIR = config.DATA / "plots"


def load_results(min_quality: float) -> pd.DataFrame:
    if not config.RESULTS_CSV.exists():
        sys.exit("No data/results.csv — run the pipeline first: python main.py")
    df = pd.read_csv(config.RESULTS_CSV)
    if df.empty:
        sys.exit("results.csv is empty — nothing to plot.")

    # Coerce year to a nullable integer; drop rows with no usable date.
    df["year"] = pd.to_numeric(df["date"], errors="coerce")
    missing = df["year"].isna().sum()
    if missing:
        print(f"Note: {missing} document(s) have no parseable year and are excluded from time plots.")
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)

    if min_quality > 0:
        before = len(df)
        df = df[df["ocr_quality"] >= min_quality].copy()
        print(f"OCR-quality filter >= {min_quality}: kept {len(df)}/{before} documents.")

    if df.empty:
        sys.exit("No documents left to plot after filtering.")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-quality", type=float, default=0.0,
                    help="Drop documents with ocr_quality below this (0..1).")
    args = ap.parse_args()

    try:
        import matplotlib
        matplotlib.use("Agg")  # headless: write files, don't open a window
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit("matplotlib not installed. Run: pip install -r requirements.txt")

    df = load_results(args.min_quality)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    by_year = df.groupby("year")
    years_sorted = sorted(df["year"].unique())
    single_year = len(years_sorted) < 2  # avoid a degenerate line with one point

    # ── 1. Sentiment over time ────────────────────────────────────────────
    mean_sent = by_year["sentiment_score"].mean()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(df["year"], df["sentiment_score"], alpha=0.4, s=25,
               color="steelblue", label="per document")
    if not single_year:
        ax.plot(mean_sent.index, mean_sent.values, "-o", color="darkred",
                linewidth=2, label="yearly mean")
    else:
        ax.scatter(mean_sent.index, mean_sent.values, color="darkred", s=120,
                   marker="D", label="yearly mean")
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Year")
    ax.set_ylabel("Lexicon sentiment  (−1 … +1)")
    ax.set_title("Sentiment over time — French scouting journals")
    ax.set_ylim(-1, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "sentiment_over_time.png", dpi=150)
    plt.close(fig)

    # ── 2. Word counts over time ──────────────────────────────────────────
    mean_total = by_year["total_words"].mean()
    mean_content = by_year["content_words"].mean()
    fig, ax = plt.subplots(figsize=(10, 5))
    style = "-o" if not single_year else "D"
    if single_year:
        ax.scatter(mean_total.index, mean_total.values, s=120, label="total words (mean)")
        ax.scatter(mean_content.index, mean_content.values, s=120, label="content words (mean)")
    else:
        ax.plot(mean_total.index, mean_total.values, "-o", label="total words (mean)")
        ax.plot(mean_content.index, mean_content.values, "-s", label="content words (mean)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Words per document")
    ax.set_title("Average word count over time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "wordcount_over_time.png", dpi=150)
    plt.close(fig)

    # ── 3. Documents per year (coverage) ──────────────────────────────────
    counts = by_year.size()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(counts.index, counts.values, color="seagreen")
    ax.set_xlabel("Year")
    ax.set_ylabel("Documents")
    ax.set_title("Document coverage by year")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "docs_per_year.png", dpi=150)
    plt.close(fig)

    # ── 4. Sentiment vs OCR quality (noise sanity check) ──────────────────
    fig, ax = plt.subplots(figsize=(7, 6))
    sc = ax.scatter(df["ocr_quality"], df["sentiment_score"],
                    c=df["year"], cmap="viridis", alpha=0.7, s=35)
    ax.set_xlabel("OCR quality (0 … 1)")
    ax.set_ylabel("Sentiment score")
    ax.set_title("Sentiment vs OCR quality\n(flat cloud = sentiment not just OCR noise)")
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    if df["year"].nunique() > 1:
        fig.colorbar(sc, ax=ax, label="Year")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "sentiment_vs_quality.png", dpi=150)
    plt.close(fig)

    print(f"\nWrote 4 plot(s) to {PLOTS_DIR}/")
    for p in sorted(PLOTS_DIR.glob("*.png")):
        print(f"  {p.name}")

    # Quick textual summary too.
    print("\nSummary by year:")
    summary = by_year.agg(
        docs=("ark", "size"),
        mean_sentiment=("sentiment_score", "mean"),
        mean_words=("total_words", "mean"),
    ).round(2)
    print(summary.to_string())


if __name__ == "__main__":
    main()
