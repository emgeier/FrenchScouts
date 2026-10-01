"""Build a single self-contained HTML report from the pipeline outputs.

Embeds the plots (as inline base64 PNGs) and the results table into ONE file,
docs/index.html, with no external assets. That one file works three ways:
  - email it as an attachment (opens offline in any browser)
  - host it on GitHub Pages (the docs/ folder is a Pages source)
  - upload it to an S3 static site

Usage:
    python report.py
    python report.py --min-quality 0.6   # note the filter in the report
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import sys
from pathlib import Path

import pandas as pd

import config

PLOTS_DIR = config.DATA / "plots"
DOCS_DIR = config.ROOT / "docs"           # GitHub Pages source folder
OUT_HTML = DOCS_DIR / "index.html"

# Plots in display order with captions.
PLOTS = [
    ("sentiment_over_time.png", "Sentiment over time (yearly mean + per-document scatter)."),
    ("wordcount_over_time.png", "Average word count per document, by year."),
    ("docs_per_year.png", "Document coverage: how many issues per year."),
    ("sentiment_vs_quality.png",
     "Sanity check: sentiment vs OCR quality. A flat cloud means sentiment is not merely OCR noise."),
]


def _img_tag(path: Path, caption: str) -> str:
    if not path.exists():
        return f'<p class="missing">[missing plot: {html.escape(path.name)}]</p>'
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'<figure><img alt="{html.escape(caption)}" '
        f'src="data:image/png;base64,{b64}"/>'
        f'<figcaption>{html.escape(caption)}</figcaption></figure>'
    )


def _table_html(df: pd.DataFrame) -> str:
    """Sortable HTML table (sorting handled by a tiny inline script)."""
    headers = "".join(
        f'<th onclick="sortTable({i})">{html.escape(c)}</th>'
        for i, c in enumerate(df.columns)
    )
    rows = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        rows.append(f"<tr>{cells}</tr>")
    return (
        f'<table id="results"><thead><tr>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def build(min_quality: float) -> None:
    if not config.RESULTS_CSV.exists():
        sys.exit("No data/results.csv — run the pipeline first: python main.py")
    df = pd.read_csv(config.RESULTS_CSV)
    if df.empty:
        sys.exit("results.csv is empty — nothing to report.")

    note = ""
    if min_quality > 0:
        before = len(df)
        df = df[df["ocr_quality"] >= min_quality].copy()
        note = f"OCR-quality filter applied: ocr_quality ≥ {min_quality} ({len(df)}/{before} documents shown)."

    # Headline numbers.
    n_docs = len(df)
    years = pd.to_numeric(df.get("date"), errors="coerce").dropna()
    year_range = f"{int(years.min())}–{int(years.max())}" if not years.empty else "n/a"
    mean_sent = round(df["sentiment_score"].mean(), 3) if "sentiment_score" in df else "n/a"
    total_words = int(df["total_words"].sum()) if "total_words" in df else 0
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    plots_html = "\n".join(_img_tag(PLOTS_DIR / name, cap) for name, cap in PLOTS)
    table_html = _table_html(df)

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>French Scouting Journals — Text Analysis</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 960px;
         margin: 2rem auto; padding: 0 1rem; color: #222; line-height: 1.5; }}
  h1 {{ margin-bottom: .2rem; }}
  .sub {{ color: #666; margin-top: 0; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 1.5rem 0; }}
  .card {{ flex: 1 1 160px; background: #f5f7fa; border-radius: 8px; padding: 1rem; }}
  .card .n {{ font-size: 1.6rem; font-weight: 700; }}
  .card .l {{ color: #666; font-size: .85rem; }}
  figure {{ margin: 1.5rem 0; }}
  figure img {{ max-width: 100%; border: 1px solid #e3e3e3; border-radius: 6px; }}
  figcaption {{ color: #666; font-size: .9rem; margin-top: .4rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .85rem; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ddd; padding: 4px 8px; text-align: left; }}
  th {{ background: #333; color: #fff; cursor: pointer; position: sticky; top: 0; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  .note {{ background: #fff8e1; border-left: 4px solid #ffb300; padding: .6rem 1rem; }}
  .caveats {{ background: #f0f4ff; border-left: 4px solid #5c7cfa; padding: .6rem 1rem; }}
  .missing {{ color: #b00; }}
  footer {{ color: #888; font-size: .8rem; margin-top: 2rem; }}
</style></head><body>

<h1>French Scouting Journals — Text Analysis</h1>
<p class="sub">Word counts and sentiment over {year_range}, from digitized Gallica (BnF) issues.</p>

<div class="cards">
  <div class="card"><div class="n">{n_docs}</div><div class="l">documents</div></div>
  <div class="card"><div class="n">{year_range}</div><div class="l">year range</div></div>
  <div class="card"><div class="n">{mean_sent}</div><div class="l">mean sentiment</div></div>
  <div class="card"><div class="n">{total_words:,}</div><div class="l">total words</div></div>
</div>

{f'<p class="note">{html.escape(note)}</p>' if note else ''}

<h2>Figures</h2>
{plots_html}

<h2>Methodology</h2>
<p>Full-document OCR text was retrieved from Gallica's machine APIs (per-page ALTO
via <code>RequestDigitalElement</code>, metadata via <code>OAIRecord</code>), cleaned
(dehyphenation + whitespace normalization), tokenized with the French spaCy model
(<code>fr_core_news_md</code>) for word counts, and scored for sentiment with a
transparent French sentiment lexicon.</p>

<div class="caveats">
  <strong>Read before interpreting:</strong>
  <ul>
    <li>Sentiment uses a small, transparent <em>lexicon</em> method — explainable, but a
        starting point, not ground truth. Validate against documents read by hand.</li>
    <li>These are historical OCR scans; the <code>ocr_quality</code> column flags noisy
        documents. See the sentiment-vs-quality figure before drawing conclusions.</li>
    <li>Source material is public-domain Gallica content; no sensitive data is included.</li>
  </ul>
</div>

<h2>Results ({n_docs} documents)</h2>
<p>Click a column header to sort.</p>
{table_html}

<footer>Generated {generated} · FrenchScouts PoC · data from gallica.bnf.fr</footer>

<script>
function sortTable(col) {{
  var t = document.getElementById("results");
  var rows = Array.prototype.slice.call(t.tBodies[0].rows);
  var asc = t.getAttribute("data-sort-col") != col || t.getAttribute("data-sort-dir") != "asc";
  rows.sort(function(a, b) {{
    var x = a.cells[col].innerText, y = b.cells[col].innerText;
    var nx = parseFloat(x), ny = parseFloat(y);
    if (!isNaN(nx) && !isNaN(ny)) {{ return asc ? nx - ny : ny - nx; }}
    return asc ? x.localeCompare(y) : y.localeCompare(x);
  }});
  rows.forEach(function(r) {{ t.tBodies[0].appendChild(r); }});
  t.setAttribute("data-sort-col", col);
  t.setAttribute("data-sort-dir", asc ? "asc" : "desc");
}}
</script>
</body></html>"""

    OUT_HTML.write_text(page, encoding="utf-8")
    size_kb = OUT_HTML.stat().st_size / 1024
    print(f"Wrote {OUT_HTML} ({size_kb:.0f} KB, self-contained).")
    print("Open it locally, email it, or publish docs/ via GitHub Pages (see README).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-quality", type=float, default=0.0,
                    help="Only include documents with ocr_quality >= this value.")
    args = ap.parse_args()
    build(args.min_quality)
