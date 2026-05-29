"""
openfigi_pull.py v1.0 — Map identifiers to FIGI using the OpenFIGI v3 API.

Resolves ISIN (or ticker) to compositeFIGI and ISIN for the TradeInt
standard schema (Layer 2 fields: figi #9, isin #8).

Output follows TradeInt standard schema v2.2 (56 fields).
Compatible with merge_v2.py directly.

Why OpenFIGI?
-------------
OpenFIGI is the authoritative free source for compositeFIGI and cross-
validated ISIN. Both are AUTHORITATIVE fields in merge_v2.py — OpenFIGI
values overwrite other sources for figi and isin.

API version
-----------
Uses OpenFIGI v3 only (/v3/mapping). V2 was sunset 2026-07-01.

Rate limits (per API docs)
--------------------------
  Without API key : 25 requests/minute, 10 jobs/request
  With API key    : 25 requests/6 seconds, 100 jobs/request
  Script enforces conservative delay; set OPENFIGI_API_KEY in .env for
  higher throughput.

Identifier types supported (-t / --id-type)
-------------------------------------------
  ID_ISIN    — International Securities Identification Number (default)
  TICKER     — Exchange ticker + exchange code (requires --exch-code)
  ID_CUSIP   — CUSIP (US only)
  ID_SEDOL   — SEDOL (UK / Ireland)

Output
------
One row per FIGI returned per input identifier. If an ISIN maps to
multiple FIGIs (e.g. the same security on multiple exchanges), each
FIGI is a separate row. merge_v2.py deduplicates by compositeFIGI.

Usage
-----
  # Map ISINs (most common)
  python openfigi_pull.py --ids US0378331005,US5949181045

  # Map ISINs from a file (one per line)
  python openfigi_pull.py --file isins.txt

  # Map tickers (requires --exch-code)
  python openfigi_pull.py --ids AAPL --id-type TICKER --exch-code US

  # Use API key from .env for higher rate limit
  python openfigi_pull.py --ids US0378331005 --env

  # Custom output path
  python openfigi_pull.py --ids US0378331005 --out results/figi_2026-06-01.csv

Dependencies: requests  (pip install requests)
              python-dotenv  (pip install python-dotenv)  — optional
API docs:     https://www.openfigi.com/api/documentation
"""

import argparse
import csv
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

from schema import FIELDNAMES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR     = Path(__file__).parent
LOG_PATH     = BASE_DIR / "logs" / "run.log"
DEFAULT_OUT  = BASE_DIR / "openfigi_results.csv"

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"

# Rate limit: 25 req/min without key  →  1 req per 2.4s (conservative)
#             25 req/6s  with key     →  1 req per 0.24s (conservative)
DELAY_NO_KEY  = 2.5   # seconds between batch requests (no key)
DELAY_WITH_KEY = 0.30  # seconds between batch requests (with key)

# Batch size: max jobs per request (10 without key, 100 with key)
BATCH_NO_KEY  = 10
BATCH_WITH_KEY = 100

_last_request_time: float = 0.0


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _post_batch(jobs: list[dict], api_key: str) -> list[dict]:
    """
    POST one batch of mapping jobs to OpenFIGI v3 /mapping.

    Each job is a dict like {"idType": "ID_ISIN", "idValue": "US0378331005"}.
    Returns the list of result objects (one per job; may be {"error": "..."}).
    """
    global _last_request_time

    delay = DELAY_WITH_KEY if api_key else DELAY_NO_KEY
    elapsed = time.monotonic() - _last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key

    resp = requests.post(OPENFIGI_URL, headers=headers, json=jobs, timeout=20)
    _last_request_time = time.monotonic()

    if resp.status_code == 429:
        # Rate limited — wait 60s and retry once
        print("  [WARN] Rate limited (HTTP 429). Waiting 60s …", flush=True)
        time.sleep(60)
        resp = requests.post(OPENFIGI_URL, headers=headers, json=jobs, timeout=20)
        _last_request_time = time.monotonic()

    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# FIGI result → schema row mapper
# ---------------------------------------------------------------------------
def _figi_to_row(figi_obj: dict, input_id: str, id_type: str) -> dict:
    """
    Map one FIGI result object to a TradeInt schema v2.2 row.

    OpenFIGI returns data per instrument (share class / exchange listing).
    We store the compositeFIGI in figi (#9) and populate what we can.
    All other fields are empty — merge_v2.py fills them from other sources.
    """
    # compositeFIGI is the company-level identifier we want
    composite_figi = figi_obj.get("compositeFIGI", "")
    share_class    = figi_obj.get("shareClassFIGI", "")
    ticker         = figi_obj.get("ticker", "")
    exch_code      = figi_obj.get("exchCode", "")
    name           = figi_obj.get("name", "")
    security_type  = figi_obj.get("securityType", "")
    security_type2 = figi_obj.get("securityType2", "")

    # isin: only available when input was an ISIN
    isin = input_id if id_type == "ID_ISIN" else ""

    # exchCode → jurisdiction (best effort; not authoritative — use GLEIF)
    jurisdiction_map = {
        "US": "US", "LN": "GB", "AU": "AU", "JP": "JP",
        "HK": "HK", "SG": "SG", "KS": "KR", "TT": "TW",
        "IN": "IN", "FP": "FR", "GY": "DE", "SM": "ES",
        "IM": "IT", "NA": "NL", "BB": "BE", "ID": "ID",
        "MK": "MY", "VN": "VN", "CN": "CN",
    }
    jurisdiction = jurisdiction_map.get(exch_code, "")

    row = {f: "" for f in FIELDNAMES}
    row.update({
        # Layer 1
        "source":       "OPENFIGI",
        "exchange":     exch_code,
        "jurisdiction": jurisdiction,
        # Layer 2
        "company_name": name,
        "ticker":       ticker,
        "source_id":    composite_figi,   # compositeFIGI is the entity-level ID
        "isin":         isin,
        "figi":         composite_figi,
    })
    return row


# ---------------------------------------------------------------------------
# Main mapping function
# ---------------------------------------------------------------------------
def map_identifiers(
    identifiers: list[str],
    id_type: str,
    exch_code: str,
    api_key: str,
) -> list[dict]:
    """
    Map a list of identifiers to FIGI rows using OpenFIGI v3 /mapping.

    Returns a flat list of schema v2.2 rows (one per FIGI result).
    Errors are logged to stderr; the identifier is skipped.
    """
    batch_size = BATCH_WITH_KEY if api_key else BATCH_NO_KEY
    all_rows: list[dict] = []

    for i in range(0, len(identifiers), batch_size):
        batch_ids  = identifiers[i : i + batch_size]
        batch_jobs = []
        for id_val in batch_ids:
            job: dict = {"idType": id_type, "idValue": id_val}
            if exch_code:
                job["exchCode"] = exch_code
            # Restrict to Common Stock to avoid ETF / bond / warrant noise
            job["securityType"] = "Common Stock"
            batch_jobs.append(job)

        print(
            f"  Batch {i // batch_size + 1}: "
            f"{len(batch_jobs)} job(s) … ",
            end="",
            flush=True,
        )

        try:
            results = _post_batch(batch_jobs, api_key)
        except requests.HTTPError as exc:
            print(f"HTTP error: {exc}", file=sys.stderr)
            continue

        batch_hits = 0
        for id_val, result in zip(batch_ids, results):
            if "error" in result:
                # Identifier not found or invalid — not a script error
                print(f"\n    [WARN] {id_val}: {result['error']}", file=sys.stderr)
                continue
            figi_list = result.get("data", [])
            for figi_obj in figi_list:
                row = _figi_to_row(figi_obj, id_val, id_type)
                all_rows.append(row)
                batch_hits += 1

        print(f"{batch_hits} FIGI record(s)")

    return all_rows


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
def append_run_log(
    n_inputs: int,
    n_hits: int,
    elapsed_sec: float,
    error_code: str,
    out_path: Path,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{ts}\t"
        f"n_inputs={n_inputs}\t"
        f"hits={n_hits}\t"
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
        description="Map identifiers to FIGI using OpenFIGI v3 API (schema v2.2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument(
        "--ids",
        default="",
        help='Comma-separated identifier values, e.g. "US0378331005,US5949181045".',
    )
    id_group.add_argument(
        "--file",
        default="",
        metavar="PATH",
        help="Path to a file with one identifier per line.",
    )
    parser.add_argument(
        "--id-type",
        default="ID_ISIN",
        choices=["ID_ISIN", "TICKER", "ID_CUSIP", "ID_SEDOL"],
        help="Identifier type to map (default: ID_ISIN).",
    )
    parser.add_argument(
        "--exch-code",
        default="",
        metavar="CODE",
        help='Exchange code filter, e.g. "US", "LN", "AU". Required for TICKER id-type.',
    )
    parser.add_argument(
        "--apikey",
        default="",
        metavar="KEY",
        help="OpenFIGI API key (optional; increases rate limit to 25 req/6s).",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Load OPENFIGI_API_KEY from .env file (requires python-dotenv).",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Output CSV path (default: {DEFAULT_OUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args     = parse_args()
    t_start  = time.monotonic()
    error_code = "OK"
    all_rows: list[dict] = []

    try:
        # ── Resolve API key ───────────────────────────────────────────────────
        api_key = args.apikey.strip()
        if not api_key and args.env:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                print("[WARN] python-dotenv not installed; ignoring --env.", file=sys.stderr)
            api_key = os.getenv("OPENFIGI_API_KEY", "")

        if api_key:
            print(f"API key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
            print(f"Rate limit: 25 req/6s, {BATCH_WITH_KEY} jobs/request")
        else:
            print("No API key — rate limit: 25 req/min, 10 jobs/request")
            print("Register free at https://www.openfigi.com/user/register")

        # ── Validate TICKER requires exch-code ───────────────────────────────
        if args.id_type == "TICKER" and not args.exch_code:
            sys.exit("[ERROR] --id-type TICKER requires --exch-code (e.g. --exch-code US)")

        # ── Resolve identifier list ───────────────────────────────────────────
        if args.ids.strip():
            identifiers = [x.strip() for x in args.ids.split(",") if x.strip()]
        else:
            file_path = Path(args.file)
            if not file_path.exists():
                sys.exit(f"[ERROR] File not found: {file_path}")
            with open(file_path, encoding="utf-8") as f:
                identifiers = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        if not identifiers:
            sys.exit("[ERROR] No identifiers to process.")

        print(f"\n{len(identifiers)} identifier(s) to map ({args.id_type})")
        print()

        # ── Map ───────────────────────────────────────────────────────────────
        all_rows = map_identifiers(
            identifiers=identifiers,
            id_type=args.id_type,
            exch_code=args.exch_code,
            api_key=api_key,
        )

        # ── Write output ──────────────────────────────────────────────────────
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not all_rows:
            print("\nNo FIGI records found. CSV not written.")
            error_code = "NO_RESULTS"
        else:
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(all_rows)
            print(f"\n✓ Wrote {len(all_rows)} row(s) to {out_path}")

            # Preview
            col_widths = [22, 10, 8, 8, 24]
            headers_p  = ["figi (compositeFIGI)", "ticker", "exchange", "jurisd.", "company_name"]
            sep = "  ".join("-" * w for w in col_widths)
            fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
            print()
            print(fmt.format(*headers_p))
            print(sep)
            for row in all_rows[:20]:
                print(fmt.format(
                    row["figi"][:col_widths[0]],
                    row["ticker"][:col_widths[1]],
                    row["exchange"][:col_widths[2]],
                    row["jurisdiction"][:col_widths[3]],
                    row["company_name"][:col_widths[4]],
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
        append_run_log(
            n_inputs=len(identifiers) if "identifiers" in dir() else 0,
            n_hits=len(all_rows),
            elapsed_sec=elapsed,
            error_code=error_code,
            out_path=Path(args.out),
        )
        print(f"\nRun log → {LOG_PATH}  ({error_code}, {elapsed:.1f}s, {len(all_rows)} hits)")


if __name__ == "__main__":
    main()
