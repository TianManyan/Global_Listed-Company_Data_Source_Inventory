"""
edgar_xbrl_pull.py v1.0 — Pull financial data from SEC EDGAR XBRL endpoint.

Fetches revenue, net income, and employee count for US-listed companies
using the SEC EDGAR companyfacts API. Output follows TradeInt schema v2.1.
Compatible with merge_v2.py directly.

Fields populated
----------------
Layer 3:  employee_count (#19), employee_count_date (#20)
Layer 4:  revenue_usd (#29), revenue_period (#30),
          net_income_usd (#31), net_income_period (#32)

Fields NOT populated by this script (use other sources):
  market_cap_usd  → OpenFIGI
  credit_rating   → S&P Ratings

Coverage: US companies only (SEC filers).
          Japan equivalent: EDINET XBRL (edinet_pull.py, Week 2).
          Korea equivalent: KRX DART XBRL (Week 4).

Dependencies: requests  (pip install requests)
Rate limit:   10 req/s (same as other SEC EDGAR endpoints)
API docs:     https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json

Usage
-----
  python edgar_xbrl_pull.py --tickers AAPL,MSFT,TSLA
  python edgar_xbrl_pull.py --tickers AAPL --out results/xbrl_2026-05-25.csv
"""

import argparse
import csv
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
EDGAR_BASE    = "https://data.sec.gov"
TICKERS_URL   = "https://www.sec.gov/files/company_tickers.json"
HEADERS       = {"User-Agent": "TradeInt research@tradeint.com"}
MIN_INTERVAL  = 0.11   # 10 req/s SEC limit + buffer

_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# Schema v2.1 output fields (subset — only fields this script populates)
# All 49 fields present; unpopulated fields are empty string.
# ---------------------------------------------------------------------------
from schema import FIELDNAMES  # single source of truth — schema.py

# ---------------------------------------------------------------------------
# Revenue concept priority order
# Different companies use different XBRL concept names for revenue.
# Try in this order; take first non-null 10-K result.
# ---------------------------------------------------------------------------
REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",  # Post-2018 ASC 606 standard
    "Revenues",
    "Revenue",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _get(url: str) -> dict:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------------------------
# Ticker → CIK map
# ---------------------------------------------------------------------------
def load_ticker_to_cik() -> dict[str, str]:
    """Return {TICKER_UPPER: zero-padded-10-digit-CIK}."""
    data = _get(TICKERS_URL)
    mapping: dict[str, str] = {}
    for entry in data.values():
        ticker = entry["ticker"].upper()
        cik    = str(entry["cik_str"]).zfill(10)
        mapping[ticker] = cik
    return mapping

# ---------------------------------------------------------------------------
# XBRL parser
# ---------------------------------------------------------------------------
def _extract_latest_annual(facts: dict, namespace: str, concept: str) -> dict | None:
    """
    Return the most recent annual (10-K or 20-F) filing value
    for a given XBRL concept, or None if not found.
    """
    ns_data = facts.get(namespace, {})
    concept_data = ns_data.get(concept)
    if not concept_data:
        return None

    units = concept_data.get("units", {})
    # Prefer USD for financial values; fall back to first unit (e.g. 'pure' for headcount)
    unit_key = "USD" if "USD" in units else (list(units.keys())[0] if units else None)
    if not unit_key:
        return None

    entries = units[unit_key]
    # Keep only annual filings (10-K for US; 20-F for foreign private issuers)
    annual = [e for e in entries if e.get("form") in ("10-K", "20-F")]
    if not annual:
        return None

    # Most recent by period end date
    latest = sorted(annual, key=lambda x: x.get("end", ""))[-1]
    return {
        "value":       latest["val"],
        "period_end":  latest["end"],
        "fiscal_year": latest.get("fy"),
        "unit":        unit_key,
        "form":        latest.get("form"),
        "filed":       latest.get("filed", ""),
    }


def fetch_xbrl_fields(cik: str, ticker: str) -> dict:
    """
    Fetch XBRL companyfacts for one CIK and return a schema v2.1 row
    with Layer 3 and Layer 4 financial fields populated.
    """
    url  = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    data = _get(url)
    facts        = data.get("facts", {})
    company_name = data.get("entityName", "")

    row: dict = {f: "" for f in FIELDNAMES}

    # ── Layer 1–2 identity ───────────────────────────────────────────────────
    row["source"]      = "SEC_EDGAR"
    row["exchange"]    = ""   # XBRL endpoint doesn't return exchange — resolved by edgar_8k_pull.py
    row["jurisdiction"] = "US"
    row["company_name"] = company_name
    row["ticker"]       = ticker
    row["source_id"]    = cik

    # ── Layer 3: employee count ───────────────────────────────────────────────
    emp = _extract_latest_annual(facts, "dei", "EntityNumberOfEmployees")
    if emp:
        row["employee_count"]      = str(emp["value"])
        row["employee_count_date"] = emp["period_end"]

    # ── Layer 4: revenue ─────────────────────────────────────────────────────
    for concept in REVENUE_CONCEPTS:
        rev = _extract_latest_annual(facts, "us-gaap", concept)
        if rev:
            row["revenue_usd"]    = str(rev["value"])
            row["revenue_period"] = f"FY{rev['fiscal_year']}" if rev.get("fiscal_year") else rev["period_end"]
            break

    # ── Layer 4: net income ───────────────────────────────────────────────────
    ni = _extract_latest_annual(facts, "us-gaap", "NetIncomeLoss")
    if ni:
        row["net_income_usd"]    = str(ni["value"])
        row["net_income_period"] = f"FY{ni['fiscal_year']}" if ni.get("fiscal_year") else ni["period_end"]

    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch XBRL financial data from SEC EDGAR (schema v2.1).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tickers", required=True,
        help="Comma-separated tickers, e.g. AAPL,MSFT,TSLA",
    )
    parser.add_argument(
        "--out", default="edgar_xbrl_results.csv",
        help="Output CSV path (default: edgar_xbrl_results.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args    = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    out     = Path(args.out)

    print("Loading ticker→CIK map from SEC …")
    ticker_map = load_ticker_to_cik()

    all_rows: list[dict] = []
    for ticker in tickers:
        cik = ticker_map.get(ticker)
        if not cik:
            print(f"  [WARN] {ticker}: not found in SEC company_tickers.json — skipping")
            continue
        print(f"  Fetching XBRL for {ticker} (CIK {cik}) …", end="", flush=True)
        try:
            row = fetch_xbrl_fields(cik, ticker)
            all_rows.append(row)
            rev = row.get("revenue_usd", "")
            ni  = row.get("net_income_usd", "")
            emp = row.get("employee_count", "")
            print(f" revenue={int(float(rev)):,} | net_income={int(float(ni)):,} | employees={emp}"
                  if rev and ni else " (some fields missing)")
        except requests.HTTPError as e:
            print(f" [ERROR] HTTP {e.response.status_code} — skipping")

    if not all_rows:
        print("No XBRL data retrieved.")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ Wrote {len(all_rows)} row(s) → {out}")
    print()

    # Preview table
    col_widths = [8, 12, 20, 16, 16, 10]
    headers_p  = ["ticker", "source_id", "company_name", "revenue_usd", "net_income_usd", "employees"]
    sep = "  ".join("-" * w for w in col_widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers_p))
    print(sep)
    for row in all_rows:
        rev = f"{int(float(row['revenue_usd'])):,}" if row.get("revenue_usd") else "—"
        ni  = f"{int(float(row['net_income_usd'])):,}" if row.get("net_income_usd") else "—"
        print(fmt.format(
            row["ticker"][:8],
            row["source_id"][:12],
            row["company_name"][:20],
            rev[:16],
            ni[:16],
            row.get("employee_count", "—")[:10],
        ))


if __name__ == "__main__":
    main()
