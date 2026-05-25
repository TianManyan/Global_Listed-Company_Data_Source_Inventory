"""
gleif_pull.py v2.0 — Query the GLEIF LEI Registry for a list of company names.

Output follows TradeInt standard schema v2.1 (49 fields).
Compatible with merge_v2.py directly.

New in v2.0 vs v1.0
--------------------
- Populates all schema v2.1 Layer 3 fields available from GLEIF:
    legal_form, country_of_incorporation, registered_address, hq_address,
    parent_company_name, parent_lei, is_listed_subsidiary
- Populates all Layer 5 LEI trust fields:
    lei_status, lei_last_updated, lei_next_renewal_date
- Now includes INACTIVE entities (marked in lei_status); v1.0 silently dropped them

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
    python gleif_pull.py --max-results 3 --out results/gleif_2026-05-25.csv
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
# Schema v2.1 output fields — imported from schema.py (single source of truth)
# ---------------------------------------------------------------------------
from schema import FIELDNAMES  # noqa: E402


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
# GLEIF Level 2 — parent relationship lookup
# ---------------------------------------------------------------------------
def _fetch_parent(lei: str) -> tuple[str, str, str]:
    """
    Look up the ultimate parent of *lei* via GLEIF Level 2 API.

    Returns (parent_company_name, parent_lei, is_listed_subsidiary).
    Returns ("", "", "") when:
      - Entity has no parent (independent company)
      - Parent has no LEI (reporting exception)
      - API returns 404 or any error

    Coverage: ~93% of LEI-registered entities have verified parent data
    (GLEIF Q4 2025 Business Report). When parent itself has no LEI, the
    relationship is filed as a reporting exception and this function
    returns empty strings.
    """
    url = f"{GLEIF_API_BASE}/lei-records/{lei}/ultimate-parent"
    try:
        data   = _get(url)
        parent = data.get("data", {})
        if not parent:
            return "", "", ""
        attrs       = parent.get("attributes", {})
        entity      = attrs.get("entity", {})
        parent_lei  = parent.get("id", "")
        parent_name = entity.get("legalName", {}).get("name", "")
        # is_listed_subsidiary: true if we found a parent record
        is_subsidiary = "True" if parent_lei else ""
        return parent_name, parent_lei, is_subsidiary
    except Exception:
        # 404 = no parent / reporting exception; other errors = treat as unknown
        return "", "", ""



def fetch_lei_records(company_name: str, max_results: int) -> list[dict]:
    """
    Search GLEIF for *company_name* and return up to *max_results* rows
    mapped to the TradeInt standard schema v2.1.

    Unlike v1.0, this version:
    - Includes INACTIVE/ANNULLED entities (marked in lei_status)
    - Populates all available Layer 3 and Layer 5 fields
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
        attrs  = record.get("attributes", {})
        entity = attrs.get("entity", {})
        reg    = attrs.get("registration", {})

        lei        = attrs.get("lei", "")
        legal_name = entity.get("legalName", {}).get("name", "")
        status     = entity.get("status", "")  # ACTIVE / INACTIVE / ANNULLED

        # Addresses
        legal_addr = entity.get("legalAddress", {})
        hq_addr    = entity.get("headquartersAddress", {})

        def _format_address(a: dict) -> str:
            parts = [
                " ".join(a.get("addressLines", [])),
                a.get("city", ""),
                a.get("region", ""),
                a.get("postalCode", ""),
                a.get("country", ""),
            ]
            return ", ".join(p for p in parts if p)

        registered_address = _format_address(legal_addr)
        hq_address         = _format_address(hq_addr)
        country            = legal_addr.get("country", "")

        # Legal form (ELF code → plain text name)
        legal_form_obj = entity.get("legalForm", {})
        legal_form     = legal_form_obj.get("other", "") or legal_form_obj.get("id", "")

        # Parent / ownership via GLEIF Level 2
        parent_name, parent_lei_val, is_subsidiary = _fetch_parent(lei)

        # Trust signals
        lei_status          = status
        lei_last_updated    = reg.get("lastUpdateDate", "")[:10]  # trim to YYYY-MM-DD
        lei_next_renewal    = reg.get("nextRenewalDate", "")[:10]

        rows.append({
            # Layer 1
            "source":      "GLEIF",
            "exchange":    "",   # GLEIF covers legal entities, not exchange listings
            "jurisdiction": country,
            # Layer 2
            "company_name": legal_name,
            "ticker":       "",
            "source_id":    lei,
            "lei":          lei,
            "isin":         "",
            "figi":         "",
            # Layer 3
            "company_name_local":             "",
            "company_description":            "",
            "founded_year":                   "",
            "industry_sector":                "",
            "industry_code":                  "",
            "industry_classification_scheme": "",
            "country_of_incorporation":       country,
            "registered_address":             registered_address,
            "hq_address":                     hq_address if hq_address != registered_address else "",
            "employee_count":                 "",
            "employee_count_date":            "",
            "website":                        "",
            "primary_products_services":      "",
            "parent_company_name":            parent_name,
            "parent_lei":                     parent_lei_val,
            "is_listed_subsidiary":           is_subsidiary,
            "legal_form":                     legal_form,
            # Layer 4 — not available from GLEIF
            "market_cap_usd": "", "market_cap_date": "",
            "revenue_usd": "", "revenue_period": "",
            "net_income_usd": "", "net_income_period": "",
            "credit_rating": "", "credit_rating_agency": "",
            "esg_report_url": "", "cdp_rating": "", "cdp_disclosure_year": "",
            # Layer 5
            "lei_status":             lei_status,
            "lei_last_updated":       lei_last_updated,
            "lei_next_renewal_date":  lei_next_renewal,
            "exchange_verified":      "",
            "latest_filing_date":     "",
            "filing_frequency_12m":   "",
            "data_completeness_score": "",
            # Filing — not applicable for GLEIF
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
            col_widths = [6, 8, 28, 22, 8, 12]
            headers_p  = ["source", "jurisd.", "company_name", "lei", "status", "renewal"]
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
                    row["lei_status"][:col_widths[4]],
                    row["lei_next_renewal_date"][:col_widths[5]],
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
