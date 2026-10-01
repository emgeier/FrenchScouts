"""Shared configuration and paths for the FrenchScouts Gallica PoC."""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"          # cached OCR text, one file per ark
CLEAN_DIR = DATA / "clean"      # cleaned text, one file per ark
ARKS_FILE = ROOT / "arks.txt"   # input: one ark id per line
RESULTS_CSV = DATA / "results.csv"

for _d in (DATA, RAW_DIR, CLEAN_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Gallica API ────────────────────────────────────────────────────────────
GALLICA_BASE = "https://gallica.bnf.fr"
#
# IMPORTANT: the convenience ".texteBrut" full-text endpoint is behind an ALTCHA
# anti-bot CAPTCHA (it 302-redirects automated clients to a challenge page). The
# documented MACHINE endpoints below are NOT gated, so we use those instead:
#   - Pagination service   -> page count
#   - RequestDigitalElement -> per-page OCR as ALTO XML (the real OCR text)
#   - OAIRecord            -> Dublin Core metadata (title, date, creator)
PAGINATION_URL = GALLICA_BASE + "/services/Pagination?ark={ark}"
ALTO_URL = GALLICA_BASE + "/RequestDigitalElement?O={ark}&E=ALTO&Deb={page}"
OAI_RECORD_URL = GALLICA_BASE + "/services/OAIRecord?ark={ark}"

# ── Politeness / rate limiting ───────────────────────────────────────────────
# Gallica is a shared public service. Keep this conservative; the whole PoC is
# only ~100 documents so there is no reason to hammer it.
REQUEST_DELAY_SECONDS = 2.0     # min delay between requests
REQUEST_TIMEOUT = 60            # per-request timeout (large OCR docs)
MAX_RETRIES = 4
# A realistic browser UA. Gallica varies behavior by User-Agent; a generic
# library UA is more likely to be challenged. Keep requests polite via the delay.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 FrenchScouts-PoC/0.1 (research)"
)

# ── spaCy ────────────────────────────────────────────────────────────────────
SPACY_MODEL = "fr_core_news_md"
