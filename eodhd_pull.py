"""
eodhd_pull.py v1.0 — Pull company fundamentals from EODHD Fundamentals API.

Fills the 7 new fields introduced in schema v2.2 that have no free-source
equivalent, plus supplements existing Layer 3 and Layer 4 fields globally.

Fields populated (schema v2.2)
-------------------------------
Layer 2:  cusip (#10)
Layer 3:  company_description (#12), ipo_date (#14), fiscal_year_end (#15),
          industry_sector (#16), industry_code (#17),
          industry_classification_scheme (#18),
          hq_address (#21), employee_count (#22), employee_count_date (#23),
          website (#24), phone (#26), officers (#27), cross_listings (#28)
Layer 4:  market_cap_usd (#33), market_cap_date (#34),
          revenue_usd (#35), revenue_period (#36),
          net_income_usd (#37), net_income_period (#38)
Layer 5:  is_delisted (#48)

Demo key limitation
-------------------
The demo key (api_token=demo) only returns data for AAPL.US.
All other tickers return HTTP 403. Replace with a paid key for production use.

Known Issue #4 (schema v2.2)
-----------------------------
Non-US market coverage unverified as of 2026-05-26.
Demo key returns Forbidden for all non-US tickers.
Sample data request sent to EODHD support.
Do not assume non-US fields are populated until verified.

Dependencies: requests  (pip install requests)
Rate limits:  Free plan: 20 API calls/day
              Paid plans: 100,000 calls/day
              Script enforces 0.5s between requests.
API docs:     https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds

Usage
-----
  # Using demo key (AAPL.US only)
  python eodhd_pull.py --tickers AAPL.US --apikey demo

  # Using your paid key
  python eodhd_pull.py --tickers AAPL.US,MSFT.US,D05.SG --apikey YOUR_KEY

  # Load key from .env file (EODHD_API_KEY=...)
  python eodhd_pull.py --tickers AAPL.US,MSFT.US --env

  # Custom output path
  python eodhd_pull.py --tickers AAPL.US --apikey demo --out results/eodhd_2026-05-26.csv

Ticker format: {SYMBOL}.{EXCHANGE_CODE}
  US:    AAPL.US, MSFT.US, TSLA.US
  SG:    D05.SG  (DBS Group)
  GB:    HSBA.LSE (HSBC)
  JP:    7203.TSE (Toyota)
  MY:    1155.KLSE (Maybank)
  KR:    005930.KO (Samsung)
  TW:    2330.TW (TSMC)
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

from schema import FIELDNAMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EODHD_BASE   = "https://eodhd.com/api/v1.1/fundamentals"
MIN_INTERVAL = 0.5   # seconds between requests
_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _get(ticker_exchange: str, api_key: str) -> dict:
    """Fetch EODHD Fundamentals JSON for one ticker."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)

    url = f"{EODHD_BASE}/{ticker_exchange}"
    params = {"api_token": api_key, "fmt": "json"}
    resp = requests.get(url, params=params, timeout=20)
    _last_request_time = time.monotonic()

    if resp.status_code == 403:
        raise PermissionError(
            f"HTTP 403 — API key may lack access to '{ticker_exchange}'. "
            "Demo key only works for AAPL.US. "
            "Non-US tickers require a paid key (Known Issue #4)."
        )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Financial data parser helpers
# ---------------------------------------------------------------------------
def _latest_annual(income_stmt: dict) -> tuple[str, dict]:
    """
    Return (period_key, row_dict) for the most recent annual entry
    in EODHD's Income_Statement.yearly dict.
    Keys are date strings like '2024-09-28'.
    """
    yearly = income_stmt.get("yearly", {})
    if not yearly:
        return "", {}
    latest_key = sorted(yearly.keys())[-1]
    return latest_key, yearly[latest_key]


def _to_fy(date_str: str) -> str:
    """Convert '2024-09-28' → 'FY2024'."""
    if not date_str:
        return ""
    return f"FY{date_str[:4]}"


def _format_officers(officers_dict: dict) -> str:
    """
    Serialise EODHD General.Officers dict to JSON string.
    Input: {'0': {'Name': '...', 'Title': '...', 'YearBorn': '...'}, ...}
    Output: '[{"Name": "...", "Title": "...", "YearBorn": "..."}]'
    """
    if not officers_dict:
        return ""
    officers_list = [v for v in officers_dict.values() if isinstance(v, dict)]
    return json.dumps(officers_list, ensure_ascii=False)


def _format_cross_listings(listings_dict: dict) -> str:
    """
    Extract exchange codes from EODHD General.Listings dict.
    Input: {'0': {'Code': 'AAPL', 'Exchange': 'NASDAQ', ...}, ...}
    Output: 'NASDAQ,LSE'
    """
    if not listings_dict:
        return ""
    exchanges = [
        v.get("Exchange", "")
        for v in listings_dict.values()
        if isinstance(v, dict) and v.get("Exchange")
    ]
    return ",".join(exchanges)


# ---------------------------------------------------------------------------
# Main mapping function
# ---------------------------------------------------------------------------
def fetch_eodhd_fields(ticker_exchange: str, api_key: str) -> dict:
    """
    Fetch EODHD Fundamentals for one ticker and return a schema v2.2 row.

    ticker_exchange format: 'AAPL.US', 'D05.SG', '7203.TSE', etc.
    """
    data = _get(ticker_exchange, api_key)

    general    = data.get("General", {})
    highlights = data.get("Highlights", {})
    financials = data.get("Financials", {})
    income_stmt = financials.get("Income_Statement", {})

    # ── Layer 1 ──────────────────────────────────────────────────────────────
    exchange    = general.get("Exchange", "")
    jurisdiction = general.get("CountryISO", "")

    # ── Layer 2 ──────────────────────────────────────────────────────────────
    company_name = general.get("Name", "")
    ticker       = general.get("Code", ticker_exchange.split(".")[0])
    source_id    = general.get("PrimaryTicker", ticker_exchange)
    lei          = general.get("LEI", "")
    isin         = general.get("ISIN", "")
    figi         = general.get("OpenFigi", "")
    cusip        = general.get("CUSIP", "")

    # ── Layer 3 ──────────────────────────────────────────────────────────────
    company_description = general.get("Description", "")
    ipo_date            = general.get("IPODate", "")
    fiscal_year_end     = general.get("FiscalYearEnd", "")
    industry_sector     = general.get("GicSector", "")
    industry_code       = general.get("GicIndustry", "")
    industry_scheme     = "GICS" if industry_sector else ""
    country_of_inc      = general.get("CountryISO", "")

    # HQ address — try structured first, fall back to flat string
    addr_data = general.get("AddressData", {})
    if addr_data:
        parts = [
            addr_data.get("Street", ""),
            addr_data.get("City", ""),
            addr_data.get("State", ""),
            addr_data.get("ZIP", ""),
            addr_data.get("Country", ""),
        ]
        hq_address = ", ".join(p for p in parts if p)
    else:
        hq_address = general.get("Address", "")

    employee_count      = str(general.get("FullTimeEmployees", "") or "")
    employee_count_date = general.get("UpdatedAt", "")[:10] if general.get("UpdatedAt") else ""
    website             = general.get("WebURL", "")
    phone               = general.get("Phone", "")
    officers            = _format_officers(general.get("Officers", {}))
    cross_listings      = _format_cross_listings(general.get("Listings", {}))

    # ── Layer 4 ──────────────────────────────────────────────────────────────
    market_cap_usd  = str(highlights.get("MarketCapitalization", "") or "")
    market_cap_date = general.get("UpdatedAt", "")[:10] if general.get("UpdatedAt") else ""

    period_key, income_row = _latest_annual(income_stmt)
    revenue_usd    = str(income_row.get("totalRevenue", "") or "")
    revenue_period = _to_fy(period_key)
    net_income_usd    = str(income_row.get("netIncome", "") or "")
    net_income_period = revenue_period

    # ── Layer 5 ──────────────────────────────────────────────────────────────
    is_delisted = str(general.get("IsDelisted", "") or "")
    # Normalise to True/False string
    if is_delisted.lower() in ("true", "1", "yes"):
        is_delisted = "True"
    elif is_delisted.lower() in ("false", "0", "no", ""):
        is_delisted = "False"

    # ── Build full schema v2.2 row ───────────────────────────────────────────
    row: dict = {f: "" for f in FIELDNAMES}
    row.update({
        # Layer 1
        "source":       "EODHD",
        "exchange":     exchange,
        "jurisdiction": jurisdiction,
        # Layer 2
        "company_name": company_name,
        "ticker":       ticker,
        "source_id":    source_id,
        "lei":          lei,
        "isin":         isin,
        "figi":         figi,
        "cusip":        cusip,
        # Layer 3
        "company_description":            company_description,
        "ipo_date":                       ipo_date,
        "fiscal_year_end":                fiscal_year_end,
        "industry_sector":                industry_sector,
        "industry_code":                  industry_code,
        "industry_classification_scheme": industry_scheme,
        "country_of_incorporation":       country_of_inc,
        "hq_address":                     hq_address,
        "employee_count":                 employee_count,
        "employee_count_date":            employee_count_date,
        "website":                        website,
        "phone":                          phone,
        "officers":                       officers,
        "cross_listings":                 cross_listings,
        # Layer 4
        "market_cap_usd":    market_cap_usd,
        "market_cap_date":   market_cap_date,
        "revenue_usd":       revenue_usd,
        "revenue_period":    revenue_period,
        "net_income_usd":    net_income_usd,
        "net_income_period": net_income_period,
        # Layer 5
        "is_delisted": is_delisted,
    })
    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch company fundamentals from EODHD API (schema v2.2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tickers", required=True,
        help='Comma-separated tickers in SYMBOL.EXCHANGE format, e.g. "AAPL.US,D05.SG"',
    )
    parser.add_argument(
        "--apikey", default="",
        help='EODHD API key. Use "demo" to test with AAPL.US only.',
    )
    parser.add_argument(
        "--env", action="store_true",
        help="Load API key from EODHD_API_KEY environment variable / .env file.",
    )
    parser.add_argument(
        "--out", default="eodhd_results.csv",
        help="Output CSV path (default: eodhd_results.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve API key
    api_key = args.apikey
    if args.env or not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        api_key = api_key or os.getenv("EODHD_API_KEY", "")

    if not api_key:
        sys.exit("[ERROR] No API key provided. Use --apikey demo or --apikey YOUR_KEY or --env")

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    out     = Path(args.out)

    key_label = "demo key (AAPL.US only)" if api_key == "demo" else "paid key"
    print(f"eodhd_pull.py v1.0 — {key_label}")
    print(f"Tickers: {', '.join(tickers)}")
    print()

    all_rows: list[dict] = []
    for ticker in tickers:
        print(f"  {ticker} …", end="", flush=True)
        try:
            row = fetch_eodhd_fields(ticker, api_key)
            all_rows.append(row)
            # Preview key fields
            rev  = f"${int(float(row['revenue_usd'])):,}" if row.get("revenue_usd") else "—"
            mcap = f"${int(float(row['market_cap_usd'])):,}" if row.get("market_cap_usd") else "—"
            emp  = row.get("employee_count", "—") or "—"
            print(f" revenue={rev}  mktcap={mcap}  employees={emp}")
        except PermissionError as e:
            print(f"\n  [SKIP] {e}")
        except requests.HTTPError as e:
            print(f"\n  [ERROR] HTTP {e.response.status_code} — skipping")
        except Exception as e:
            print(f"\n  [ERROR] {e} — skipping")

    if not all_rows:
        print("\nNo data retrieved. CSV not written.")
        print("Tip: demo key only works for AAPL.US")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ Wrote {len(all_rows)} row(s) → {out}")
    print()

    # Preview table
    col_widths = [8, 4, 26, 16, 12, 10]
    headers_p  = ["ticker", "exch", "company_name", "revenue_usd", "ipo_date", "employees"]
    sep = "  ".join("-" * w for w in col_widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers_p))
    print(sep)
    for row in all_rows:
        rev = f"{int(float(row['revenue_usd'])):,}" if row.get("revenue_usd") else "—"
        print(fmt.format(
            row["ticker"][:col_widths[0]],
            row["exchange"][:col_widths[1]],
            row["company_name"][:col_widths[2]],
            rev[:col_widths[3]],
            row.get("ipo_date", "—")[:col_widths[4]],
            (row.get("employee_count", "—") or "—")[:col_widths[5]],
        ))


if __name__ == "__main__":
    main()
