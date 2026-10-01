"""Fetch OCR text + metadata for Gallica documents listed in arks.txt.

Gallica's convenience ".texteBrut" endpoint is behind an ALTCHA CAPTCHA, so this
uses the ungated machine APIs instead:
  1. Pagination service   -> number of pages
  2. RequestDigitalElement -> per-page OCR as ALTO XML -> extract text
  3. OAIRecord            -> Dublin Core metadata (title, date)

Polite (rate-limited), cached, and resumable: a document whose raw text is already
on disk is skipped. The full-document text is concatenated from all pages and
written to data/raw/<ark>.txt; metadata is written to data/raw/<ark>.meta.json.
"""
from __future__ import annotations

import json
import re
import sys
import time
import random
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

import config


def read_arks(path: Path = config.ARKS_FILE) -> list[str]:
    """Read ark ids, ignoring blanks/# comments. Accepts bare id or full URL."""
    arks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "ark:/12148/" in line:
            line = line.split("ark:/12148/", 1)[1]
        line = line.split("/")[0].split(".")[0].split("?")[0]
        arks.append(line)
    return arks


def _get(session: requests.Session, url: str) -> requests.Response | None:
    """GET with retry/backoff. Returns the response or None after exhausting retries."""
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
            # Detect the ALTCHA gate: it redirects to .../altcha or returns the
            # "Vérification de sécurité" HTML page instead of real content.
            if "altcha" in resp.url.lower() or "Vérification de sécurité" in resp.text[:2000]:
                print(f"  ALTCHA gate hit on {url} (attempt {attempt})")
                time.sleep(min(2 ** attempt + random.random(), 30))
                continue
            if resp.status_code == 200:
                return resp
            if resp.status_code == 404:
                return resp  # caller decides
            time.sleep(min(2 ** attempt + random.random(), 30))
        except requests.RequestException as e:
            print(f"  {e.__class__.__name__} on {url} (attempt {attempt})")
            time.sleep(min(2 ** attempt + random.random(), 30))
    return None


def get_page_count(ark: str, session: requests.Session) -> int:
    """Number of page images in the document (from the Pagination service)."""
    resp = _get(session, config.PAGINATION_URL.format(ark=ark))
    if resp is None:
        return 0
    m = re.search(r"<nbVueImages>(\d+)</nbVueImages>", resp.text)
    return int(m.group(1)) if m else 0


# ALTO namespaces vary; match the String element regardless of namespace.
_STRING_TAG = re.compile(r"\}String$")


def _alto_page_text(xml_text: str) -> str:
    """Extract reading-order text from one ALTO page.

    Joins hyphenated words using SUBS_CONTENT (ALTO marks the two halves of a
    line-wrapped word; the full word lives on the HypPart1 element's SUBS_CONTENT).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    words: list[str] = []
    for el in root.iter():
        if not _STRING_TAG.search(el.tag):
            continue
        subs_type = el.get("SUBS_TYPE")
        if subs_type == "HypPart1":
            words.append(el.get("SUBS_CONTENT", el.get("CONTENT", "")))
        elif subs_type == "HypPart2":
            continue  # already emitted via the HypPart1 SUBS_CONTENT
        else:
            words.append(el.get("CONTENT", ""))
    return " ".join(w for w in words if w)


def fetch_ocr(ark: str, pages: int, session: requests.Session) -> str:
    """Concatenate OCR text across all pages via RequestDigitalElement (ALTO)."""
    parts: list[str] = []
    for p in range(1, pages + 1):
        resp = _get(session, config.ALTO_URL.format(ark=ark, page=p))
        if resp is None or resp.status_code != 200:
            print(f"  {ark} p{p}: no ALTO")
        else:
            resp.encoding = resp.apparent_encoding or "utf-8"
            txt = _alto_page_text(resp.text)
            if txt:
                parts.append(txt)
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return "\n\n".join(parts)


def fetch_metadata(ark: str, session: requests.Session) -> dict:
    """Dublin Core title/date/creator from the OAIRecord service."""
    resp = _get(session, config.OAI_RECORD_URL.format(ark=ark))
    meta = {"ark": ark, "title": "", "date": "", "creator": ""}
    if resp is None:
        return meta
    for field in ("title", "date", "creator"):
        m = re.search(rf"<dc:{field}>([^<]*)</dc:{field}>", resp.text, re.IGNORECASE)
        if m:
            meta[field] = m.group(1).strip()
    return meta


def fetch_all(force: bool = False) -> dict[str, bool]:
    arks = read_arks()
    if not arks:
        print("No arks found in arks.txt — add ids (one per line) and rerun.")
        return {}

    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})

    results: dict[str, bool] = {}
    print(f"Fetching {len(arks)} document(s) via ALTO OCR...")
    for i, ark in enumerate(arks, 1):
        out = config.RAW_DIR / f"{ark}.txt"
        if out.exists() and not force:
            print(f"[{i}/{len(arks)}] {ark}: cached, skipping")
            results[ark] = True
            continue

        print(f"[{i}/{len(arks)}] {ark}: metadata...")
        meta = fetch_metadata(ark, session)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        pages = get_page_count(ark, session)
        if pages == 0:
            print(f"  {ark}: FAILED (no page count — doc may not be text-indexed)")
            results[ark] = False
            continue
        print(f"  {ark}: '{meta['title'][:60]}' ({meta['date']}), {pages} pages")
        time.sleep(config.REQUEST_DELAY_SECONDS)

        text = fetch_ocr(ark, pages, session)
        if not text.strip():
            print(f"  {ark}: FAILED (no OCR text extracted)")
            results[ark] = False
            continue

        out.write_text(text, encoding="utf-8")
        (config.RAW_DIR / f"{ark}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {ark}: saved {len(text):,} chars from {pages} pages")
        results[ark] = True

    ok = sum(results.values())
    print(f"\nDone: {ok}/{len(arks)} succeeded.")
    return results


if __name__ == "__main__":
    fetch_all(force="--force" in sys.argv)
