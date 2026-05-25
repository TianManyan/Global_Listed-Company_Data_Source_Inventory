"""
openfigi_pull.py v1.0 — Map tickers/ISINs to FIGI via OpenFIGI API.

Resolves company identifiers (ticker, ISIN) to:
  - compositeFIGI  → company-level global identifier
  - isin           → International Securities Identification Number
  - exchange code  → which exchange the security trades on

Output follows TradeInt schema v2.1 (49 fields).
Compatible with merge_v2.py directly.

Fields populated
----------------
Layer 2:  figi (#9), isin (#8)
Layer 1:  exchange (#2) — from OpenFIGI exchCode

Role in the pipeline
--------------------
OpenFIGI is the first step in the identity resolution chain:
  ticker → OpenFIGI → FIGI + ISIN → GLEIF (LEI) → EDGAR / EDINET

⚠️  V2 API sunset: 2026-07-01 — this script uses V3 only (/v3/mapping).

Dependencies: requests  (pip install requests)
API docs:     https://www.openfigi.com/api/documentation

Rate limits (V3)
----------------
Without API key : 25 req/min, max 10 jobs/request
With API key    : 25 req/6s,  max 100 jobs/request
HTTP 429 returned when limit exceeded.

Usage
-----
  # No API key (slower rate limit)
  python openfigi_pull.py --tickers AAPL,MSFT,D05

  # With API key (recommended)
  python openfigi_pull.py --tickers AAPL,MSFT --apikey YOUR_KEY

  # From .env file
  python openfigi_pull.py --tickers AAPL,MSFT --env

  # Map by ISIN instead of ticker
  python openfigi_pull.py --isins US0378331005,US5949181045

  # Custom output
  python openfigi_pull.py --tickers AAPL,MSFT --out results/figi_2026-05-25.csv
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
HEADERS_BASE = {"Content-Type": "application/json"}

# Rate limit: without key = 25/min → 1 req per 2.5s to be safe
# With key = 25/6s → 1 req per 0.25s to be safe
INTERVAL_NO_KEY  = 2.5
INTERVAL_WITH_KEY = 0.3

_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# Schema v2.1 output fields (all 49 — only figi, isin, exchange populated)
# ---------------------------------------------------------------------------
from schema import FIELDNAMES  # single source of truth — schema.py

# ---------------------------------------------------------------------------
# Exchange code → jurisdiction mapping
# Covers major exchanges in TradeInt's scope
# ---------------------------------------------------------------------------
EXCH_TO_JURISDICTION = {
    "US": "US", "UN": "US", "UW": "US", "UA": "US",  # NYSE / NASDAQ variants
    "LN": "GB",   # London Stock Exchange
    "JP": "JP", "JT": "JP",  # Tokyo Stock Exchange
    "SP": "SG",   # Singapore Exchange
    "AU": "AU",   # ASX
    "MK": "MY",   # Bursa Malaysia
    "IS": "IN",   # NSE India
    "IB": "IN",   # BSE India
    "KS": "KR",   # Korea Exchange
    "TT": "TW",   # Taiwan Stock Exchange
    "FP": "FR",   # Euronext Paris
    "NA": "NL",   # Euronext Amsterdam
    "BB": "BE",   # Euronext Brussels
    "HK": "HK",   # Hong Kong Exchange
    "SS": "CN", "SZ": "CN",  # Shanghai / Shenzhen
    "GY": "DE",   # Deutsche Börse
}

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _post(payload: list[dict], api_key: str) -> dict:
    """POST to OpenFIGI mapping endpoint with rate limiting."""
    global _last_request_time
    interval = INTERVAL_WITH_KEY if api_key else INTERVAL_NO_KEY
    elapsed = time.monotonic() - _last_request_time
    if elapsed < interval:
        time.sleep(interval - elapsed)

    headers = dict(HEADERS_BASE)
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key

    resp = requests.post(OPENFIGI_URL, json=payload, headers=headers, timeout=15)
    _last_request_time = time.monotonic()

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 10))
        print(f"  [WARN] Rate limited — waiting {retry_after}s …")
        time.sleep(retry_after)
        return _post(payload, api_key)   # one retry

    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Core mapping function
# ---------------------------------------------------------------------------
def map_ticker(ticker: str, exch_code: str, api_key: str) -> dict | None:
    """
    Map a ticker + exchange to FIGI and ISIN via OpenFIGI.

    Returns the best match (Common Stock, primary exchange) or None.
    """
    payload = [{"idType": "TICKER", "idValue": ticker, "exchCode": exch_code}]
    try:
        results = _post(payload, api_key)
    except requests.HTTPError as e:
        print(f"  [ERROR] {ticker}: HTTP {e.response.status_code}")
        return None

    # results is a list with one element per job
    job_result = results[0] if results else {}
    if "error" in job_result:
        return None

    hits = job_result.get("data", [])
    if not hits:
        return None

    # Prefer Common Stock in marketSector = Equity
    def _score(h):
        return (
            (1 if h.get("securityType") == "Common Stock" else 0) +
            (1 if h.get("marketSector") == "Equity" else 0)
        )
    best = sorted(hits, key=_score, reverse=True)[0]
    return best


def map_isin(isin: str, api_key: str) -> dict | None:
    """Map an ISIN to FIGI via OpenFIGI."""
    payload = [{"idType": "ID_ISIN", "idValue": isin}]
    try:
        results = _post(payload, api_key)
    except requests.HTTPError as e:
        print(f"  [ERROR] {isin}: HTTP {e.response.status_code}")
        return None

    job_result = results[0] if results else {}
    if "error" in job_result:
        return None

    hits = job_result.get("data", [])
    if not hits:
        return None

    def _score(h):
        return (
            (1 if h.get("securityType") == "Common Stock" else 0) +
            (1 if h.get("marketSector") == "Equity" else 0)
        )
    return sorted(hits, key=_score, reverse=True)[0]


def build_row(hit: dict, input_ticker: str = "", input_isin: str = "") -> dict:
    """Convert an OpenFIGI hit to a schema v2.1 row."""
    row = {f: "" for f in FIELDNAMES}

    exch_code  = hit.get("exchCode", "")
    figi       = hit.get("compositeFIGI", hit.get("figi", ""))
    isin       = hit.get("isin", input_isin)
    name       = hit.get("name", "")
    ticker_out = hit.get("ticker", input_ticker)
    jurisdiction = EXCH_TO_JURISDICTION.get(exch_code, "")

    row["source"]       = "OPENFIGI"
    row["exchange"]     = exch_code
    row["jurisdiction"] = jurisdiction
    row["company_name"] = name
    row["ticker"]       = ticker_out
    row["source_id"]    = figi          # use compositeFIGI as source_id for OpenFIGI
    row["figi"]         = figi
    row["isin"]         = isin
    row["document_url"] = f"https://www.openfigi.com/id/{figi}" if figi else ""

    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map tickers/ISINs to FIGI via OpenFIGI API (schema v2.1).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tickers",
        help='Comma-separated tickers, e.g. "AAPL,MSFT,D05". '
             'Uses US exchange by default; prefix with EXCH: to specify, e.g. SP:D05',
    )
    group.add_argument(
        "--isins",
        help="Comma-separated ISINs, e.g. US0378331005,US5949181045",
    )
    parser.add_argument(
        "--apikey", default="",
        help="OpenFIGI API key (optional but recommended for higher rate limits). "
             "Or use --env to load from OPENFIGI_API_KEY in .env file.",
    )
    parser.add_argument(
        "--env", action="store_true",
        help="Load API key from OPENFIGI_API_KEY environment variable / .env file.",
    )
    parser.add_argument(
        "--out", default="openfigi_results.csv",
        help="Output CSV path (default: openfigi_results.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve API key
    api_key = args.apikey
    if args.env or not api_key:
        # Try loading from environment / .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        api_key = api_key or os.getenv("OPENFIGI_API_KEY", "")

    key_status = "with API key" if api_key else "without API key (slower rate limit)"
    print(f"openfigi_pull.py v1.0 — {key_status}")
    print(f"Endpoint: {OPENFIGI_URL}")
    print()

    out = Path(args.out)
    all_rows: list[dict] = []

    if args.tickers:
        entries = [t.strip() for t in args.tickers.split(",") if t.strip()]
        for entry in entries:
            # Support EXCH:TICKER format, e.g. SP:D05 for SGX
            if ":" in entry:
                exch_code, ticker = entry.split(":", 1)
            else:
                exch_code, ticker = "US", entry   # default to US exchange

            print(f"  {ticker} ({exch_code}) …", end="", flush=True)
            hit = map_ticker(ticker, exch_code, api_key)
            if hit:
                row = build_row(hit, input_ticker=ticker)
                all_rows.append(row)
                print(f" figi={row['figi']}  isin={row['isin'] or '—'}  exch={row['exchange']}")
            else:
                print(" not found")

    elif args.isins:
        isins = [i.strip() for i in args.isins.split(",") if i.strip()]
        for isin in isins:
            print(f"  {isin} …", end="", flush=True)
            hit = map_isin(isin, api_key)
            if hit:
                row = build_row(hit, input_isin=isin)
                all_rows.append(row)
                print(f" figi={row['figi']}  ticker={row['ticker']}  exch={row['exchange']}")
            else:
                print(" not found")

    if not all_rows:
        print("\nNo results found. CSV not written.")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ Wrote {len(all_rows)} row(s) → {out}")
    print()

    # Preview
    col_widths = [6, 8, 4, 24, 20, 12]
    headers_p  = ["exch", "jurisd.", "isin?", "company_name", "figi", "ticker"]
    sep = "  ".join("-" * w for w in col_widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers_p))
    print(sep)
    for row in all_rows:
        print(fmt.format(
            row["exchange"][:col_widths[0]],
            row["jurisdiction"][:col_widths[1]],
            "✓" if row["isin"] else "—",
            row["company_name"][:col_widths[3]],
            row["figi"][:col_widths[4]],
            row["ticker"][:col_widths[5]],
        ))


if __name__ == "__main__":
    main()
