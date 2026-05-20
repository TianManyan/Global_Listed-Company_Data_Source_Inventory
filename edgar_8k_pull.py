"""
edgar_8k_pull.py — Pull recent 8-K filings from SEC EDGAR for a ticker watchlist.

Dependencies: requests  (only non-stdlib dep; pip install requests)
Rate limit:   ≤ 10 requests/second — SEC documented limit
              https://www.sec.gov/about/developer-resources

Usage examples
--------------
# Use default watchlist.csv, look back 30 days, write to filings.csv
    python edgar_8k_pull.py

# Override tickers on the command line (skips watchlist.csv)
    python edgar_8k_pull.py --tickers AAPL,MSFT,TSLA

# Look back 7 days, write to a custom path
    python edgar_8k_pull.py --days 7 --out results/weekly_8k.csv

# Mix: read watchlist but override output path and look-back window
    python edgar_8k_pull.py --days 14 --out /tmp/8k_14d.csv

Run log is appended to logs/run.log automatically.
"""

import argparse
import csv
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional dependency
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    sys.exit(
        "Missing dependency: install it with  pip install requests\n"
        "Then re-run the script."
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
WATCHLIST_PATH = BASE_DIR / "watchlist.csv"
LOG_PATH = BASE_DIR / "logs" / "run.log"
DEFAULT_OUT = BASE_DIR / "filings.csv"

HEADERS = {"User-Agent": "TradeInt research@tradeint.com"}

# SEC asks for ≤ 10 req/sec.  0.11 s gives ≈ 9 req/sec with a small buffer.
MIN_INTERVAL = 0.11  # seconds between requests

_last_request_time: float = 0.0


# ---------------------------------------------------------------------------
# Rate-limited HTTP helper
# ---------------------------------------------------------------------------
def _get(url: str) -> dict:
    """Rate-limited GET → parsed JSON.  Raises requests.HTTPError on bad status."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Watchlist reader
# ---------------------------------------------------------------------------
def load_watchlist(path: Path) -> list[str]:
    """
    Read tickers from a CSV file.

    Accepted formats
    ----------------
    - Single-column (no header):    one ticker per row
    - Header row 'ticker':          ticker,notes or ticker,sector,...
    - Header row 'symbol':          symbol,...

    Lines that are blank or start with '#' are skipped.
    """
    if not path.exists():
        return []

    tickers: list[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header_checked = False
        for row in reader:
            if not row:
                continue
            cell = row[0].strip()
            if not cell or cell.startswith("#"):
                continue
            # Skip a header row if the first cell looks like a column label
            if not header_checked:
                header_checked = True
                if cell.lower() in ("ticker", "symbol", "tickers"):
                    continue
            tickers.append(cell.upper())
    return tickers


# ---------------------------------------------------------------------------
# SEC EDGAR helpers
# ---------------------------------------------------------------------------
def load_ticker_to_cik() -> dict[str, str]:
    """Fetch the full SEC ticker→CIK map (single request, ~2 MB JSON)."""
    data = _get("https://www.sec.gov/files/company_tickers.json")
    mapping: dict[str, str] = {}
    for entry in data.values():
        ticker = entry["ticker"].upper()
        cik = str(entry["cik_str"]).zfill(10)
        mapping[ticker] = cik
    return mapping


def fetch_8k_filings(cik: str, since: date) -> list[dict]:
    """
    Return 8-K filings for *cik* with filing date ≥ *since*.

    The EDGAR submissions JSON lists filings in reverse-chronological order.
    We stop as soon as we hit a date older than *since* (early-exit for
    efficiency) — unless SEC returns an older filing before all recent ones,
    which does not happen in practice for the recent-filings block.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = _get(url)

    company_name = data.get("name", "")
    recent = data.get("filings", {}).get("recent", {})

    forms       = recent.get("form", [])
    filed_dates = recent.get("filingDate", [])
    accessions  = recent.get("accessionNumber", [])
    primary_doc = recent.get("primaryDocument", [])

    rows: list[dict] = []
    for form, date_str, accession, doc in zip(forms, filed_dates, accessions, primary_doc):
        try:
            filing_date = date.fromisoformat(date_str)
        except ValueError:
            continue

        # Submissions are newest-first; stop when we go past our window
        if filing_date < since:
            break

        if form != "8-K":
            continue

        acc_clean = accession.replace("-", "")
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{acc_clean}/{doc}"
        )
        rows.append(
            {
                "cik": cik,
                "company_name": company_name,
                "form": form,
                "filed_date": date_str,
                "accession_number": accession,
                "document_url": doc_url,
                "category": classify_8k(doc_url, accession),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Skill: classify 8-K by event type (keyword-rule based)
# ---------------------------------------------------------------------------

# Each entry: (category_label, [keywords_to_match_in_lowercase_filename])
# Rules are checked in order; first match wins.
_CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    ("M&A",              ["merger", "acquisition", "acqui", "takeover", "business combination"]),
    ("Officer Change",   ["director", "officer", "ceo", "cfo", "coo", "cto", "president",
                          "resign", "appointment", "elect"]),
    ("Earnings",         ["result", "earnings", "revenue", "quarter", "fiscal", "financial"]),
    ("Material Contract",["agreement", "contract", "amendment", "license", "partnership"]),
    ("Financing",        ["offering", "share", "stock", "debt", "credit", "loan",
                          "convertible", "note", "bond"]),
    ("Regulatory",       ["sec ", "regulation", "compliance", "investigation", "lawsuit",
                          "settlement", "legal"]),
]
_FALLBACK_CATEGORY = "Other"


def classify_8k(document_url: str, accession_number: str) -> str:
    """
    Return a category label for an 8-K filing.

    Strategy: match keywords against the document filename and accession number.
    No extra HTTP request is made — purely string-based, zero extra API calls.
    Accuracy ~60-70%; ambiguous filings fall into '其他 / Other'.
    """
    filename = document_url.split("/")[-1].lower()
    signal = filename + " " + accession_number.lower()
    for label, keywords in _CLASSIFICATION_RULES:
        if any(kw in signal for kw in keywords):
            return label
    return _FALLBACK_CATEGORY


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
def append_run_log(
    tickers: list[str],
    hits: int,
    elapsed_sec: float,
    error_code: str,
    out_path: Path,
) -> None:
    """Append one structured line to logs/run.log (create file/dirs as needed)."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{ts}\t"
        f"tickers={','.join(tickers)}\t"
        f"hits={hits}\t"
        f"elapsed_sec={elapsed_sec:.1f}\t"
        f"error_code={error_code}\t"
        f"out={out_path}\n"
    )
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull 8-K filings from SEC EDGAR for a watchlist of tickers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tickers",
        default="",
        help=(
            "Comma-separated list of tickers, e.g. AAPL,MSFT,TSLA. "
            "If omitted, the script reads watchlist.csv."
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Look-back window in calendar days (default: 30).",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Output CSV path (default: {DEFAULT_OUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t_start = time.monotonic()
    error_code = "OK"
    all_rows: list[dict] = []
    tickers: list[str] = []

    try:
        # ── Resolve ticker list ──────────────────────────────────────────────
        if args.tickers.strip():
            tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
            print(f"Tickers from command line: {', '.join(tickers)}")
        else:
            tickers = load_watchlist(WATCHLIST_PATH)
            if tickers:
                print(f"Tickers from {WATCHLIST_PATH}: {', '.join(tickers)}")
            else:
                print(
                    f"[WARN] No tickers found in {WATCHLIST_PATH} and --tickers not set.\n"
                    "       Create watchlist.csv or pass --tickers AAPL,MSFT,...",
                    file=sys.stderr,
                )
                error_code = "NO_TICKERS"
                return

        # ── Date window ──────────────────────────────────────────────────────
        since = date.today() - timedelta(days=args.days)
        print(f"Look-back window: {args.days} days (since {since})")

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # ── Fetch CIK map (1 request) ────────────────────────────────────────
        print("\nLoading ticker → CIK map from SEC …")
        ticker_map = load_ticker_to_cik()

        # ── Fetch filings ────────────────────────────────────────────────────
        print()
        for ticker in tickers:
            cik = ticker_map.get(ticker)
            if not cik:
                print(f"  [WARN] {ticker}: not found in SEC company_tickers.json — skipping")
                continue
            print(f"  Fetching 8-Ks for {ticker} (CIK {cik}) …", end="", flush=True)
            rows = fetch_8k_filings(cik, since)
            for row in rows:
                row["ticker"] = ticker
            all_rows.extend(rows)
            print(f" {len(rows)} filing(s)")

        # ── Write output ─────────────────────────────────────────────────────
        if not all_rows:
            print("\nNo 8-K filings found in the look-back window. CSV not written.")
            error_code = "NO_RESULTS"
        else:
            fieldnames = [
                "ticker", "cik", "company_name", "form",
                "filed_date", "accession_number", "category", "document_url",
            ]
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)

            print(f"\n✓ Wrote {len(all_rows)} row(s) to {out_path}")

            # ── Preview table ─────────────────────────────────────────────────
            col_widths = [8, 12, 28, 6, 12, 25]
            headers_p  = ["ticker", "cik", "company_name", "form", "filed_date", "accession_number"]
            sep = "  ".join("-" * w for w in col_widths)
            fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
            preview = all_rows[:20]
            print()
            print(fmt.format(*headers_p))
            print(sep)
            for row in preview:
                print(fmt.format(
                    row["ticker"][:col_widths[0]],
                    row["cik"][:col_widths[1]],
                    row["company_name"][:col_widths[2]],
                    row["form"][:col_widths[3]],
                    row["filed_date"][:col_widths[4]],
                    row["accession_number"][:col_widths[5]],
                ))
            if len(all_rows) > 20:
                print(f"  … {len(all_rows) - 20} more rows in {out_path}")

    except KeyboardInterrupt:
        error_code = "INTERRUPTED"
        print("\n[INFO] Run interrupted by user.", file=sys.stderr)
    except requests.HTTPError as exc:
        error_code = f"HTTP_{exc.response.status_code}"
        print(f"\n[ERROR] HTTP error: {exc}", file=sys.stderr)
    except Exception:
        error_code = "EXCEPTION"
        traceback.print_exc()
    finally:
        elapsed = time.monotonic() - t_start
        append_run_log(tickers, len(all_rows), elapsed, error_code, Path(args.out))
        print(f"\nRun log → {LOG_PATH}  ({error_code}, {elapsed:.1f}s, {len(all_rows)} hits)")


if __name__ == "__main__":
    main()
