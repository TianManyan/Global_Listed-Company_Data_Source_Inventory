"""
wikidata_pull.py v1.0 — Enrich company profiles with Wikidata SPARQL data.

Queries the Wikidata SPARQL endpoint for three high-quality, low-risk fields:
  - founded_year   (P571 inception date)  — ~70% coverage, accurate
  - website        (P856 official website) — ~75% coverage, reliable
  - ticker         (P249 stock ticker)     — ~70% major exchanges, reliable

Fields deliberately NOT queried (poor quality in Wikidata):
  - industry_sector    → inconsistent taxonomy, use EDGAR SIC instead
  - parent_company_name → lags M&A, use GLEIF Level 2 instead
  - lei                → only 30% coverage, use GLEIF directly instead

Input:  comma-separated company names (CLI) or wikidata_watchlist.csv
Output: edgar_xbrl_results.csv-style CSV following schema v2.1 (49 fields)

Dependencies: requests  (pip install requests)
Rate limit:   60-second processing window per client; max 5 parallel queries.
              Script enforces 2s between requests and LIMIT 5 per SPARQL query.
API docs:     https://query.wikidata.org/

Usage
-----
  python wikidata_pull.py --companies "Apple Inc,DBS Group,Toyota Motor"
  python wikidata_pull.py --companies "HSBC Holdings" --out results/wiki_2026-05-25.csv
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept":     "application/sparql-results+json",
    "User-Agent": "TradeInt research@tradeint.com (https://tradeint.com)",
}
MIN_INTERVAL = 2.0   # seconds between requests — conservative for fair use
_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# Schema v2.1 output fields
# ---------------------------------------------------------------------------
from schema import FIELDNAMES  # single source of truth — schema.py

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _sparql(query: str) -> list[dict]:
    """Execute a SPARQL query and return the bindings list."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    resp = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=60,   # increased from 30s — Wikidata can be slow (~16B triples)
    )
    _last_request_time = time.monotonic()

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 10))
        print(f"  [WARN] Rate limited (429) — waiting {retry_after}s …")
        time.sleep(retry_after)
        return _sparql(query)   # one retry

    # Wikidata infrastructure errors — don't crash, return empty
    if resp.status_code in (502, 503, 504):
        print(f"  [WARN] Wikidata server error ({resp.status_code}) — skipping this query")
        return []

    resp.raise_for_status()
    return resp.json().get("results", {}).get("bindings", [])

# ---------------------------------------------------------------------------
# SPARQL query builder
# ---------------------------------------------------------------------------
def _build_query(company_name: str) -> str:
    """
    Build a SPARQL query that searches for a company by label and returns
    only the three high-quality fields: founded_year, website, ticker.

    Uses LIMIT 5 to stay well within rate limits and avoid timeout.
    Searches both exact and case-insensitive label match.
    """
    # Escape single quotes in company name
    safe_name = company_name.replace("'", "\\'")
    return f"""
SELECT DISTINCT ?company ?companyLabel ?ticker ?website ?founded WHERE {{
  ?company wdt:P31 wd:Q4830453 .
  ?company rdfs:label "{safe_name}"@en .
  OPTIONAL {{ ?company wdt:P249 ?ticker . }}
  OPTIONAL {{ ?company wdt:P856 ?website . }}
  OPTIONAL {{ ?company wdt:P571 ?founded . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 5
"""


def _build_query_fuzzy(company_name: str) -> str:
    """
    Fallback query using case-insensitive string search.
    Used when exact label match returns no results.

    Deliberately avoids wdt:P31/wdt:P279* (recursive subclass traversal)
    which is expensive on Wikidata's ~16B triple graph and causes timeouts.
    Uses direct wdt:P31 wd:Q4830453 instead — faster, covers most listed companies.
    """
    safe_name = company_name.replace("'", "\\'").lower()
    return f"""
SELECT DISTINCT ?company ?companyLabel ?ticker ?website ?founded WHERE {{
  ?company wdt:P31 wd:Q4830453 .
  ?company rdfs:label ?label .
  FILTER(LCASE(STR(?label)) = "{safe_name}")
  OPTIONAL {{ ?company wdt:P249 ?ticker . }}
  OPTIONAL {{ ?company wdt:P856 ?website . }}
  OPTIONAL {{ ?company wdt:P571 ?founded . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 5
"""


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------
def _parse_year(founded_str: str) -> str:
    """Extract 4-digit year from a Wikidata date string like '1976-04-01T00:00:00Z'."""
    if not founded_str:
        return ""
    return founded_str[:4] if len(founded_str) >= 4 else ""


def _best_value(bindings: list[dict], field: str) -> str:
    """Return the first non-empty value for *field* across all result rows."""
    for row in bindings:
        val = row.get(field, {}).get("value", "").strip()
        if val:
            return val
    return ""


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------
def fetch_wikidata_fields(company_name: str) -> dict | None:
    """
    Query Wikidata for *company_name* and return a schema v2.1 row
    with founded_year, website, and ticker populated.

    Returns None if no matching company found.
    Strategy: try exact label match first; fall back to case-insensitive.
    """
    row: dict = {f: "" for f in FIELDNAMES}

    try:
        # Try exact match first
        bindings = _sparql(_build_query(company_name))

        # Fallback: case-insensitive match
        if not bindings:
            bindings = _sparql(_build_query_fuzzy(company_name))

    except requests.exceptions.ReadTimeout:
        print(f"\n  [WARN] Wikidata timeout for '{company_name}' — skipping. "
              "Try again later or query during off-peak hours.", flush=True)
        return None

    if not bindings:
        return None

    # Extract the three trusted fields
    founded_raw  = _best_value(bindings, "founded")
    website      = _best_value(bindings, "website")
    ticker       = _best_value(bindings, "ticker")
    company_uri  = _best_value(bindings, "company")   # e.g. http://www.wikidata.org/entity/Q312965
    label        = _best_value(bindings, "companyLabel")

    founded_year = _parse_year(founded_raw)

    # Only return a row if at least one target field was found
    if not any([founded_year, website, ticker]):
        return None

    # Derive Wikidata QID for source_id
    qid = company_uri.split("/")[-1] if company_uri else ""

    row["source"]        = "WIKIDATA"
    row["company_name"]  = label or company_name
    row["source_id"]     = qid
    row["ticker"]        = ticker
    row["founded_year"]  = founded_year
    row["website"]       = website
    row["document_url"]  = company_uri   # link back to Wikidata entity

    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich company profiles with Wikidata (founded_year, website, ticker).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--companies", required=True,
        help='Comma-separated company names, e.g. "Apple Inc,DBS Group,Toyota Motor"',
    )
    parser.add_argument(
        "--out", default="wikidata_results.csv",
        help="Output CSV path (default: wikidata_results.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args      = parse_args()
    companies = [c.strip() for c in args.companies.split(",") if c.strip()]
    out       = Path(args.out)

    print(f"wikidata_pull.py v1.0 — querying {len(companies)} company/companies")
    print(f"Fields: founded_year · website · ticker (3 high-quality fields only)")
    print()

    all_rows: list[dict] = []
    for company in companies:
        print(f"  Querying '{company}' …", end="", flush=True)
        row = fetch_wikidata_fields(company)
        if row:
            all_rows.append(row)
            parts = []
            if row.get("founded_year"): parts.append(f"founded={row['founded_year']}")
            if row.get("website"):      parts.append(f"website=✓")
            if row.get("ticker"):       parts.append(f"ticker={row['ticker']}")
            print(f" {' | '.join(parts) if parts else 'no fields found'}")
        else:
            print(" not found in Wikidata")

    if not all_rows:
        print("\nNo results found. CSV not written.")
        print("Tips: try the full legal name (e.g. 'Apple Inc' not 'Apple')")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ Wrote {len(all_rows)} row(s) → {out}")
    print()

    # Preview
    col_widths = [28, 6, 4, 40]
    headers_p  = ["company_name", "founded", "ticker", "website"]
    sep = "  ".join("-" * w for w in col_widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers_p))
    print(sep)
    for row in all_rows:
        print(fmt.format(
            row["company_name"][:col_widths[0]],
            row.get("founded_year", "—")[:col_widths[1]],
            row.get("ticker", "—")[:col_widths[2]],
            row.get("website", "—")[:col_widths[3]],
        ))


if __name__ == "__main__":
    main()
