# FrenchScouts — Gallica word count + sentiment PoC

A small, local, resumable pipeline that pulls OCR full text for Gallica (BnF)
documents, counts words, and runs French sentiment analysis. Built for a set of
~100 French scouting journals from 1920–1940.

## Pipeline

```
arks.txt  →  fetch   →  data/raw/<ark>.txt     (cached OCR text)
          →  clean   →  data/clean/<ark>.txt   (dehyphenated, normalized)
          →  analyze →  data/results.csv       (word counts + sentiment per doc)
```

Each stage is **idempotent and resumable**: already-fetched text is not
re-downloaded, so you can stop and restart safely.

## How documents are retrieved

Gallica exposes full-document OCR text by appending `.texteBrut` to the ark URL:

```
https://gallica.bnf.fr/ark:/12148/<id>.texteBrut
```

No scraping and no local OCR needed — the text layer already exists. These are
digitized scans, though, so the OCR has errors; the `clean` step dehyphenates and
normalizes, and `analyze` records a rough OCR-quality estimate per document so you
can filter low-quality scans.

## Setup

```bash
cd ~/FrenchScouts
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_md
```

## Usage

1. Put your ark ids in `arks.txt` (one per line, just the id after `ark:/12148/`).
2. Run the whole pipeline:

```bash
python main.py
```

Or run stages individually:

```bash
python fetch.py     # download OCR text (polite, cached, resumable)
python clean.py     # dehyphenate + normalize cached text
python analyze.py   # word counts + sentiment -> data/results.csv
python visualize.py # plots over time -> data/plots/*.png
```

### Visualizing

`visualize.py` reads `data/results.csv` and writes PNGs to `data/plots/`:

- `sentiment_over_time.png` — yearly-mean sentiment with a per-document scatter
- `wordcount_over_time.png` — mean total/content words per year
- `docs_per_year.png` — how many documents you have per year (coverage)
- `sentiment_vs_quality.png` — sanity check that sentiment isn't just OCR noise

```bash
python visualize.py                   # plot everything
python visualize.py --min-quality 0.6 # drop low-OCR-quality docs first
```

### Sharing a report

`report.py` bundles the plots and the results table into a single self-contained
`docs/index.html` (plots embedded as inline base64 — no external files). The same
file works three ways: email it, host it on GitHub Pages, or put it on S3.

```bash
python report.py                      # -> docs/index.html
python report.py --min-quality 0.6    # note the quality filter in the report
```

**Email:** just attach `docs/index.html` — it opens offline in any browser.

**Publish on GitHub Pages** (the source material is public-domain Gallica content,
so a public page is fine). From the project root, with the repo already on GitHub:

```bash
# one-time: make sure the report is committed on your default branch
git add docs/index.html data/results.csv
git commit -m "Add French scouting journals analysis report"
git push

# one-time: enable Pages from the docs/ folder (requires the GitHub CLI `gh`)
gh api -X POST repos/:owner/:repo/pages \
  -f "source[branch]=main" -f "source[path]=/docs"
# (or in the browser: repo Settings -> Pages -> Source: branch "main", folder "/docs")
```

Your report will be live at `https://<owner>.github.io/<repo>/` within a minute or
two. To update it later, re-run `python report.py`, then
`git commit -am "Update report" && git push` — Pages redeploys automatically.

## Output

`data/results.csv` — one row per document:

| column | meaning |
|--------|---------|
| `ark` | Gallica ark id |
| `title`, `date` | from the bibliographic header in the OCR text (best-effort) |
| `total_words` | all word tokens (spaCy, French) |
| `content_words` | excluding stopwords + punctuation |
| `sentiment_score` | lexicon-based polarity (−1 … +1), see caveats |
| `pos_hits`, `neg_hits` | raw positive/negative lexicon matches |
| `ocr_quality` | 0–1 estimate; higher = cleaner OCR |

## Sentiment caveats (read before trusting the numbers)

- Interwar French (1920–1940) is close to modern French, so models work better
  here than on older text — but it is still **historical** and domain-specific
  (scouting). Validate scores against documents you read yourself.
- The default sentiment is a **transparent lexicon method**, chosen so the result
  is explainable in a humanities context. It is a starting point, not ground truth.
- OCR noise degrades everything. Use `ocr_quality` to filter or weight.

## Notes

- Rate limiting and a descriptive User-Agent are set in `config.py`. Please keep
  requests polite — Gallica is a shared public service. Update the contact email
  in `USER_AGENT`.
