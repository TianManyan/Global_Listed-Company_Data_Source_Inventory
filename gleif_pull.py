"""
gleif_pull.py — Query the GLEIF LEI Registry for a list of company names.

Outputs follow the TradeInt cross-source standard schema (see schema.md).
Results can be merged directly with edgar_8k_pull.py output — same columns.

Dependencies: requests  (pip install requests)
Rate limit:   No hard limit published; fair-use basis.
              Script enforces 0.5s between requests to be safe.
API docs:     https://www.gleif.org/en/lei-data/gleif-api

Usage examples
--------------
# Query by company names listed in gleif_watchlist.csv
    python gleif_pull.py

# Query specific companies from the command line
    python gleif_pull.py --companies "Apple Inc,Microsoft Corporation"

# Limit results per company, custom output path
    python gleif_pull.py --max-results 3 --out results/gleif_2026-05-21.csv

Run log is appended to logs/run.log automatically.
"""

import argparse
import csv
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: install it with  pip install requests")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR       = Path(__file__).parent
WATCHLIST_PATH = BASE_DIR / "gleif_watchlist.csv"
LOG_PATH       = BASE_DIR / "logs" / "run.log"
DEFAULT_OUT    = BASE_DIR / "gleif_results.csv"

GLEIF_API_BASE = "https://api.gleif.org/api/v1"
HEADERS        = {"Accept": "application/vnd.api+json",
                  "User-Agent": "TradeInt research@tradeint.com"}

MIN_INTERVAL = 0.5   # seconds between requests (fair-use, no published limit)
_last_request_time: float = 0.0

# ---------------------------------------------------------------------------
# Standard output fields — matches TradeInt cross-source schema (schema.md)
# Layer 1: Source Metadata | Layer 2: Company Identity | Layer 3: Filing
# ---------------------------------------------------------------------------
FIELDNAMES = [
    # Layer 1 — Source Metadata
    "source",
    "exchange",
    "jurisdiction",
    # Layer 2 — Company Identity
    "company_name",
    "ticker",
    "source_id",
    "lei",
    "isin",
    "figi",
    # Layer 3 — Filing (not applicable for GLEIF; fields left empty)
    "filing_date",
    "form_type",
    "category",
    "accession_number",
    "document_url",
]


# ---------------------------------------------------------------------------
# Rate-limited HTTP helper
# ---------------------------------------------------------------------------
def _get(url: str, params: dict | None = None) -> dict:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Watchlist reader (reuses same format as edgar watchlist)
# ---------------------------------------------------------------------------
def load_watchlist(path: Path) -> list[str]:
    """Read company names from gleif_watchlist.csv."""
    if not path.exists():
        return []
    companies: list[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header_checked = False
        for row in reader:
            if not row:
                continue
            cell = row[0].strip()
            if not cell or cell.startswith("#"):
                continue
            if not header_checked:
                header_checked = True
                if cell.lower() in ("company", "name", "company_name"):
                    continue
            companies.append(cell)
    return companies


# ---------------------------------------------------------------------------
# GLEIF query
# ---------------------------------------------------------------------------
def fetch_lei_records(company_name: str, max_results: int) -> list[dict]:
    """
    Search GLEIF for *company_name* and return up to *max_results* rows
    mapped to the TradeInt standard schema.
    """
    url = f"{GLEIF_API_BASE}/lei-records"
    params = {
        "filter[entity.legalName]": company_name,
        "page[size]": max_results,
    }
    data = _get(url, params=params)
    records = data.get("data", [])

    rows: list[dict] = []
    for record in records:
        attrs      = record.get("attributes", {})
        entity     = attrs.get("entity", {})
        reg        = attrs.get("registration", {})
        lei        = attrs.get("lei", "")
        legal_name = entity.get("legalName", {}).get("name", "")
        country    = entity.get("legalAddress", {}).get("country", "")
        status     = entity.get("status", "")

        # Only include active entities
        if status != "ACTIVE":
            continue

        rows.append({
            # Layer 1 — Source Metadata
            "source":           "GLEIF",
            "exchange":         "",      # GLEIF covers legal entities, not exchange listings
            "jurisdiction":     country, # ISO 2-letter country code
            # Layer 2 — Company Identity
            "company_name":     legal_name,
            "ticker":           "",      # not available from GLEIF
            "source_id":        lei,     # GLEIF-specific identifier: LEI
            "lei":              lei,     # filled directly from GLEIF
            "isin":             "",      # not available from GLEIF
            "figi":             "",      # not available from GLEIF
            # Layer 3 — Filing (not applicable for GLEIF)
            "filing_date":      "",
            "form_type":        "",
            "category":         "",
            "accession_number": "",
            "document_url":     f"https://search.gleif.org/#/record/{lei}",
        })

    return rows


# ---------------------------------------------------------------------------
# Logging helper (shared format with edgar_8k_pull.py)
# ---------------------------------------------------------------------------
def append_run_log(
    companies: list[str],
    hits: int,
    elapsed_sec: float,
    error_code: str,
    out_path: Path,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{ts}\t"
        f"companies={','.join(companies)}\t"
        f"hits={hits}\t"
        f"elapsed_sec={elapsed_sec:.1f}\t"
        f"error_code={error_code}\t"
        f"out={out_path}\n"
    )
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query GLEIF LEI Registry and output to TradeInt standard schema CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--companies",
        default="",
        help='Comma-separated company names, e.g. "Apple Inc,HSBC Holdings". '
             "If omitted, reads gleif_watchlist.csv.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=1,
        help="Max LEI records to return per company (default: 1).",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Output CSV path (default: {DEFAULT_OUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t_start    = time.monotonic()
    error_code = "OK"
    all_rows: list[dict] = []
    companies: list[str] = []

    try:
        # ── Resolve company list ─────────────────────────────────────────────
        if args.companies.strip():
            companies = [c.strip() for c in args.companies.split(",") if c.strip()]
            print(f"Companies from command line: {', '.join(companies)}")
        else:
            companies = load_watchlist(WATCHLIST_PATH)
            if companies:
                print(f"Companies from {WATCHLIST_PATH}: {', '.join(companies)}")
            else:
                print(
                    f"[WARN] No companies found in {WATCHLIST_PATH} and --companies not set.\n"
                    "       Create gleif_watchlist.csv or pass --companies 'Apple Inc,...'",
                    file=sys.stderr,
                )
                error_code = "NO_COMPANIES"
                return

        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # ── Query GLEIF ──────────────────────────────────────────────────────
        print()
        for company in companies:
            print(f"  Querying GLEIF for '{company}' …", end="", flush=True)
            rows = fetch_lei_records(company, args.max_results)
            all_rows.extend(rows)
            print(f" {len(rows)} record(s)")

        # ── Write output ─────────────────────────────────────────────────────
        if not all_rows:
            print("\nNo active LEI records found. CSV not written.")
            error_code = "NO_RESULTS"
        else:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(all_rows)

            print(f"\n✓ Wrote {len(all_rows)} row(s) to {out_path}")

            # ── Preview ───────────────────────────────────────────────────────
            col_widths = [6, 12, 28, 22]
            headers_p  = ["source", "jurisdiction", "company_name", "lei"]
            sep = "  ".join("-" * w for w in col_widths)
            fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
            print()
            print(fmt.format(*headers_p))
            print(sep)
            for row in all_rows[:20]:
                print(fmt.format(
                    row["source"][:col_widths[0]],
                    row["jurisdiction"][:col_widths[1]],
                    row["company_name"][:col_widths[2]],
                    row["lei"][:col_widths[3]],
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
        append_run_log(companies, len(all_rows), elapsed, error_code, Path(args.out))
        print(f"\nRun log → {LOG_PATH}  ({error_code}, {elapsed:.1f}s, {len(all_rows)} hits)")


if __name__ == "__main__":
    main()
