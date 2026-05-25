"""
edgar_8k_pull.py v2.0 — Pull 8-K filings for a list of tickers from SEC EDGAR.

Output follows TradeInt standard schema v2.1 (49 fields).
Compatible with merge_v2.py directly — no field name translation needed.

New in v2.0 vs v1.0
--------------------
- Output fields aligned to schema v2.1 (filing_date, form_type, source_id, etc.)
- Populates Layer 3 fields available from submissions JSON:
    industry_sector (sicDescription), industry_code (sic),
    industry_classification_scheme (hardcoded SIC),
    country_of_incorporation (stateOfIncorporation)
- Populates Layer 5 fields:
    latest_filing_date, filing_frequency_12m, exchange_verified
- source field set to SEC_EDGAR (was missing in v1.0)

Dependencies: requests (pip install requests)
Rate limit:   ≤ 10 requests/second (SEC documented limit)
Usage:        python edgar_8k_pull.py --tickers AAPL,MSFT,TSLA [--max-filings 20] [--out results.csv]
"""

import argparse
import csv
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

HEADERS = {"User-Agent": "TradeInt research@tradeint.com"}
MIN_REQUEST_INTERVAL = 0.11  # 1/10 req/sec + small buffer

_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# Schema v2.1 output fields — imported from schema.py (single source of truth)
# ---------------------------------------------------------------------------
from schema import FIELDNAMES, CATEGORY_VOCAB  # noqa: E402

# ---------------------------------------------------------------------------
# 8-K category classifier
# ---------------------------------------------------------------------------
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("M&A",              ["merger", "acquisition", "takeover", "scheme of arrangement"]),
    ("Officer Change",   ["director", "officer", "ceo", "cfo", "resign", "appoint"]),
    ("Earnings",         ["result", "earnings", "revenue", "quarter", "annual report"]),
    ("Material Contract",["agreement", "contract", "amendment", "mou", "loi"]),
    ("Financing",        ["offering", "placement", "rights", "bond", "debt", "share issu"]),
    ("Regulatory",       ["regulation", "investigation", "settlement", "fine", "penalty"]),
    ("ESG",              ["sustainability", "esg", "climate", "carbon"]),
]

def classify_8k(description: str) -> str:
    """Return a category label for a filing based on its description."""
    desc_lower = (description or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other"


def _get(url: str) -> dict:
    """Rate-limited GET that returns parsed JSON or raises on error."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp.json()


def load_ticker_to_cik() -> dict[str, str]:
    """Return {TICKER_UPPER: zero-padded-10-digit-CIK} from SEC's company_tickers.json."""
    data = _get("https://www.sec.gov/files/company_tickers.json")
    mapping: dict[str, str] = {}
    for entry in data.values():
        ticker = entry["ticker"].upper()
        cik = str(entry["cik_str"]).zfill(10)
        mapping[ticker] = cik
    return mapping


def fetch_8k_filings(cik: str, ticker: str, max_filings: int) -> list[dict]:
    """Return up to max_filings 8-K filing records for the given CIK, schema v2.1."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = _get(url)

    company_name = data.get("name", "")
    sic          = data.get("sic", "")
    sic_desc     = data.get("sicDescription", "")
    state_of_inc = data.get("stateOfIncorporation", "")
    exchanges    = data.get("exchanges", [])
    # Map EDGAR exchange names to standard codes
    # EDGAR returns full names like "NYSE", "Nasdaq", "NYSE MKT" etc.
    _EXCH_MAP = {
        "NYSE": "NYSE", "Nasdaq": "NASDAQ", "NASDAQ": "NASDAQ",
        "NYSE MKT": "NYSE MKT", "NYSE Arca": "NYSE ARCA",
        "CBOE": "CBOE", "OTC": "OTC",
    }
    exchange_str = "/".join(
        _EXCH_MAP.get(e, e) for e in exchanges
    ) if exchanges else ""  # empty if not listed on a named exchange

    filings      = data.get("filings", {}).get("recent", {})
    forms        = filings.get("form", [])
    filed_dates  = filings.get("filingDate", [])
    accessions   = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    descriptions = filings.get("primaryDocDescription", [])

    # Layer 5 — compute latest_filing_date and filing_frequency_12m
    from datetime import date, datetime
    today = date.today()
    all_dates = []
    for d in filed_dates:
        try:
            all_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
        except ValueError:
            pass
    latest_filing_date  = max(all_dates).strftime("%Y-%m-%d") if all_dates else ""
    filing_freq_12m     = str(sum(1 for d in all_dates if (today - d).days <= 365))

    rows = []
    for form, filed_date, accession, doc, desc in zip(
        forms, filed_dates, accessions, primary_docs, descriptions
    ):
        if form != "8-K":
            continue
        acc_clean = accession.replace("-", "")
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{acc_clean}/{doc}"
        )
        rows.append({
            # Layer 1
            "source":           "SEC_EDGAR",
            "exchange":         exchange_str,
            "jurisdiction":     "US",
            # Layer 2
            "company_name":     company_name,
            "ticker":           ticker,
            "source_id":        cik,
            "lei":              "",
            "isin":             "",
            "figi":             "",
            # Layer 3 — fields available from submissions JSON
            "company_name_local":              "",
            "company_description":             "",
            "founded_year":                    "",
            "industry_sector":                 sic_desc,
            "industry_code":                   sic,
            "industry_classification_scheme":  "SIC" if sic else "",
            "country_of_incorporation":        state_of_inc,
            "registered_address":              "",
            "hq_address":                      "",
            "employee_count":                  "",
            "employee_count_date":             "",
            "website":                         "",
            "primary_products_services":       "",
            "parent_company_name":             "",
            "parent_lei":                      "",
            "is_listed_subsidiary":            "",
            "legal_form":                      "",
            # Layer 4 — not available from this endpoint
            "market_cap_usd": "", "market_cap_date": "",
            "revenue_usd": "", "revenue_period": "",
            "net_income_usd": "", "net_income_period": "",
            "credit_rating": "", "credit_rating_agency": "",
            "esg_report_url": "", "cdp_rating": "", "cdp_disclosure_year": "",
            # Layer 5
            "lei_status":             "",
            "lei_last_updated":       "",
            "lei_next_renewal_date":  "",
            "exchange_verified":      "True",
            "latest_filing_date":     latest_filing_date,
            "filing_frequency_12m":   filing_freq_12m,
            "data_completeness_score": "",
            # Filing
            "filing_date":      filed_date,
            "form_type":        form,
            "category":         classify_8k(desc),
            "accession_number": accession,
            "document_url":     doc_url,
        })
        if len(rows) >= max_filings:
            break

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch 8-K filings from SEC EDGAR (schema v2.1).")
    parser.add_argument("--tickers", required=True, help="Comma-separated tickers, e.g. AAPL,MSFT")
    parser.add_argument("--max-filings", type=int, default=20, help="Max 8-K rows per ticker (default 20)")
    parser.add_argument("--out", default="edgar_8k_results.csv", help="Output CSV path")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    print("Loading ticker→CIK map from SEC …")
    ticker_map = load_ticker_to_cik()

    all_rows: list[dict] = []
    for ticker in tickers:
        cik = ticker_map.get(ticker)
        if not cik:
            print(f"  [WARN] {ticker}: not found in SEC company_tickers.json — skipping")
            continue
        print(f"  Fetching 8-Ks for {ticker} (CIK {cik}) …", end="", flush=True)
        rows = fetch_8k_filings(cik, ticker, args.max_filings)
        all_rows.extend(rows)
        print(f" {len(rows)} filing(s)")

    if not all_rows:
        print("No filings retrieved. Exiting without writing CSV.")
        return

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows → {args.out}")

    # Preview
    col_widths = [8, 12, 26, 10, 12, 16]
    headers_p  = ["ticker", "source_id", "company_name", "category", "filing_date", "accession_number"]
    sep = "  ".join("-" * w for w in col_widths)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print()
    print(fmt.format(*headers_p))
    print(sep)
    for row in all_rows[:20]:
        print(fmt.format(
            row["ticker"][:8],
            row["source_id"][:12],
            row["company_name"][:26],
            row["category"][:10],
            row["filing_date"][:12],
            row["accession_number"][:16],
        ))
    if len(all_rows) > 20:
        print(f"  … {len(all_rows) - 20} more rows in {args.out}")


if __name__ == "__main__":
    main()
