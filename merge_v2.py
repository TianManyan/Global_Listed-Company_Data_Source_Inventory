"""
merge.py v2.0 — Entity-centric merge for TradeInt cross-source data.

Reads multiple standard-schema CSVs (schema v2.1, 49 fields), resolves
which rows refer to the same company, merges them into one profile per
company, and separates filing events into a linked filing table.

Outputs
-------
  merged_profiles.csv  — one row per company (Layer 1–5 fields + metadata)
  merged_filings.csv   — one row per filing event, linked by source_id + lei

Entity resolution priority (first match wins)
----------------------------------------------
  Level 1: lei              — most reliable cross-source identifier
  Level 2: isin             — reliable for securities
  Level 3: ticker + exchange — same symbol on same exchange
  Level 4: company_name     — fuzzy fallback; flagged as LOW confidence

Field merge rules
-----------------
  AUTHORITATIVE  — always use the named source's value (e.g. GLEIF for lei_status)
  LATEST         — use value with the most recent _date / _period companion
  FIRST_TRUSTED  — use first non-empty value from sources ranked by trust order
  APPEND         — filing fields: keep all rows, don't merge

completeness_score
------------------
  Denominator = 23 scoreable fields only (excludes B-class structural gaps).
  See SCORE_FIELDS below. Score = weighted_filled / weighted_total.
  Thresholds: >= 0.7 green, >= 0.4 amber, < 0.4 red.

Dependencies: none (standard library only)
Python: 3.10+

Usage
-----
  # Merge all *_results.csv in current directory
  python merge.py

  # Specify files explicitly
  python merge.py --inputs edgar_results.csv gleif_results.csv openfigi_results.csv

  # Custom output paths
  python merge.py --inputs *.csv --profiles out/profiles.csv --filings out/filings.csv
"""

import argparse
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema — imported from schema.py (single source of truth)
# ---------------------------------------------------------------------------
from schema import (  # noqa: E402
    FIELDNAMES as _ALL_FIELDS,
    FILING_FIELDS,
    FILING_EVENT_FIELDS,
    SOURCE_TRUST_ORDER,
)

# merge_v2.py adds three metadata columns to the profile output
PROFILE_FIELDS: list[str] = _ALL_FIELDS + ["source_list", "match_confidence", "merge_date"]

def _trust_rank(source: str) -> int:
    """Lower = more trusted. Unknown sources get rank 99."""
    try:
        return SOURCE_TRUST_ORDER.index(source.upper())
    except ValueError:
        return 99


# ---------------------------------------------------------------------------
# Field merge rules
# ---------------------------------------------------------------------------

# AUTHORITATIVE: always use this source's value when present, ignore others
AUTHORITATIVE: dict[str, str] = {
    "lei":                  "GLEIF",
    "lei_status":           "GLEIF",
    "lei_last_updated":     "GLEIF",
    "lei_next_renewal_date": "GLEIF",
    "legal_form":           "GLEIF",
    "figi":                 "OPENFIGI",
    "isin":                 "OPENFIGI",
    "credit_rating":        "SP_RATINGS",
    "credit_rating_agency": "SP_RATINGS",
    "cdp_rating":           "CDP",
    "cdp_disclosure_year":  "CDP",
}

# LATEST: take the value whose companion _date / _period field is most recent
LATEST_PAIRS: list[tuple[str, str]] = [
    ("employee_count",  "employee_count_date"),
    ("market_cap_usd",  "market_cap_date"),
    ("revenue_usd",     "revenue_period"),
    ("net_income_usd",  "net_income_period"),
]

# All other non-filing fields use FIRST_TRUSTED rule (first non-empty by trust rank)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# completeness_score — weights imported from schema.py (single source of truth)
# ---------------------------------------------------------------------------
from schema import SCORE_WEIGHT_1, SCORE_WEIGHT_HALF, SCORE_MAX  # noqa: E402


def compute_completeness(profile: dict) -> float:
    """Return completeness_score in [0, 1] rounded to 3 decimal places."""
    score = 0.0
    for f in SCORE_WEIGHT_1:
        if profile.get(f, "").strip():
            score += 1.0
    for f in SCORE_WEIGHT_HALF:
        if profile.get(f, "").strip():
            score += 0.5
    return round(score / SCORE_MAX, 3)


# ---------------------------------------------------------------------------
# Date parsing helpers (for LATEST rule)
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date | None:
    """Parse YYYY-MM-DD or fiscal period strings like FY2025. Returns None on failure."""
    if not s:
        return None
    s = s.strip()
    # ISO date
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    # Fiscal period FY2025 → treat as 2025-12-31
    m = re.match(r"FY(\d{4})", s, re.IGNORECASE)
    if m:
        return date(int(m.group(1)), 12, 31)
    # YYYYMMDD
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        pass
    return None


# ---------------------------------------------------------------------------
# Legacy field name adapter
# Maps old field names from v1.0 scripts to schema v2.1 field names.
# Add new mappings here whenever a source script is updated.
# ---------------------------------------------------------------------------
LEGACY_FIELD_MAP: dict[str, str] = {
    # edgar_8k_pull.py v1.0 → schema v2.1
    "cik":        "source_id",
    "filed_date": "filing_date",
    "form":       "form_type",
}

# Legacy source name normalisation (e.g. filename stem → standard source value)
LEGACY_SOURCE_MAP: dict[str, str] = {
    "edgar_8k_filings": "SEC_EDGAR",
    "filings":          "SEC_EDGAR",
    "gleif_results":    "GLEIF",
    "openfigi_results": "OPENFIGI",
}


def _adapt_row(row: dict, source_hint: str) -> dict:
    """Rename legacy field names and fill missing `source` field."""
    adapted = {}
    for k, v in row.items():
        new_k = LEGACY_FIELD_MAP.get(k, k)
        adapted[new_k] = v

    # Fill source if missing or empty
    if not adapted.get("source", "").strip():
        adapted["source"] = LEGACY_SOURCE_MAP.get(source_hint, source_hint.upper())

    # edgar_8k_pull.py stores date as YYYY/MM/DD — normalise to YYYY-MM-DD
    fd = adapted.get("filing_date", "")
    if fd and "/" in fd:
        adapted["filing_date"] = fd.replace("/", "-")

    # If ticker is present but exchange is empty, default SEC_EDGAR exchange
    if adapted.get("source") == "SEC_EDGAR" and not adapted.get("exchange", "").strip():
        adapted["exchange"] = "NYSE/NASDAQ"  # still a known issue — see schema Known Issues #3

    return adapted




def read_csv(path: Path) -> list[dict]:
    """Read a standard-schema CSV; applies legacy field name adapter."""
    if not path.exists():
        print(f"  [SKIP] {path} not found")
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw = list(reader)
    if not raw:
        print(f"  [SKIP] {path} is empty")
        return []

    source_hint = path.stem  # e.g. "edgar_8k_filings"
    adapted = [_adapt_row(row, source_hint) for row in raw]

    all_known = set(PROFILE_FIELDS) | set(FILING_FIELDS)
    # Check for still-unknown columns after adaptation
    remaining_extra = set(adapted[0].keys()) - all_known - {"_match_confidence"}
    if remaining_extra:
        print(f"  [WARN] {path.name}: columns not in schema (dropped): {sorted(remaining_extra)}")

    return adapted


def write_csv(rows: list[dict], fieldnames: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Entity resolution — assign a canonical key to each raw row
# ---------------------------------------------------------------------------

_STRIP_SUFFIXES = re.compile(
    r"(corporation|corp|incorporated|inc|limited|ltd|llc|plc|"
    r"holdings|holding|group|sa|ag|nv|bv|gmbh|co)\Z",
    re.IGNORECASE,
)

def _normalise(s: str) -> str:
    """
    Lowercase, strip punctuation/whitespace, then strip common legal suffixes.
    'Microsoft Corporation' → 'microsoft'
    'Microsoft'             → 'microsoft'
    'Apple Inc.'            → 'apple'
    """
    # Remove all non-alphanumeric characters
    base = re.sub(r"[^a-z0-9]", "", s.lower())
    # Iteratively strip legal suffixes (e.g. 'appleinc' → 'apple')
    while True:
        stripped = _STRIP_SUFFIXES.sub("", base).strip()
        if stripped == base or not stripped:
            break
        base = stripped
    return base


def resolve_key(row: dict, existing_keys: dict[str, str]) -> tuple[str, str]:
    """
    Return (canonical_key, match_confidence) for this row.

    Resolution priority:
      Level 1: lei              — most reliable cross-source identifier
      Level 2: isin             — reliable for securities
      Level 2.5: ticker + exchange — same symbol on same exchange
      Level 3: exact company name — normalised, space/punct stripped
      Level 4: fuzzy fallback   — flagged LOW
    """
    lei = row.get("lei", "").strip().upper()
    if lei:
        return lei, "HIGH"

    isin = row.get("isin", "").strip().upper()
    if isin:
        return isin, "HIGH"

    ticker  = row.get("ticker", "").strip().upper()
    exchange = row.get("exchange", "").strip().upper()
    if ticker and exchange:
        return f"{ticker}|{exchange}", "MEDIUM"

    # Level 3: exact normalised company name — MEDIUM confidence
    # This allows GLEIF (no ticker) to merge with exchange sources (no lei)
    # when the legal name is identical after normalisation.
    name_exact = _normalise(row.get("company_name", ""))
    if name_exact:
        # Check if this exact key already exists — if so, use it as MEDIUM
        exact_key = f"EXACT:{name_exact}"
        if exact_key in existing_keys or not existing_keys:
            return exact_key, "MEDIUM"
        return exact_key, "MEDIUM"

    # Last resort: source + source_id
    return f"{row.get('source','')}:{row.get('source_id','')}", "LOW"


# ---------------------------------------------------------------------------
# Field merge logic
# ---------------------------------------------------------------------------

def _is_filing_row(row: dict) -> bool:
    """True if this row is primarily a filing event (has filing_date or form_type)."""
    return bool(row.get("filing_date", "").strip() or
                row.get("form_type", "").strip())


def merge_rows(rows: list[dict]) -> dict:
    """
    Merge a list of rows that all refer to the same company into one profile.

    rows must all share the same canonical_key (already resolved).
    Filing event fields are excluded here; they are handled separately.
    """
    profile: dict = {f: "" for f in PROFILE_FIELDS}

    # ── 1. AUTHORITATIVE fields — use the designated source ─────────────────
    for field, auth_source in AUTHORITATIVE.items():
        for row in rows:
            if row.get("source", "").upper() == auth_source and row.get(field, "").strip():
                profile[field] = row[field].strip()
                break

    # ── 2. LATEST fields — use value with most recent date companion ─────────
    for value_field, date_field in LATEST_PAIRS:
        best_value = ""
        best_date: date | None = None
        for row in rows:
            v = row.get(value_field, "").strip()
            d = _parse_date(row.get(date_field, ""))
            if v and d and (best_date is None or d > best_date):
                best_value = v
                best_date = d
                best_date_str = row.get(date_field, "").strip()
        if best_value:
            profile[value_field] = best_value
            profile[date_field]  = best_date_str  # type: ignore[possibly-undefined]

    # ── 3. FIRST_TRUSTED — all remaining profile fields ──────────────────────
    already_handled = set(AUTHORITATIVE) | {v for v, _ in LATEST_PAIRS} | \
                      {d for _, d in LATEST_PAIRS} | FILING_EVENT_FIELDS | \
                      {"source_list", "match_confidence", "merge_date",
                       "data_completeness_score", "filing_frequency_12m",
                       "latest_filing_date"}

    sorted_rows = sorted(rows, key=lambda r: _trust_rank(r.get("source", "")))

    for field in PROFILE_FIELDS:
        if field in already_handled or profile.get(field, ""):
            continue
        for row in sorted_rows:
            v = row.get(field, "").strip()
            if v:
                profile[field] = v
                break

    # ── 4. Trust & Verification — computed / aggregated fields ───────────────

    # latest_filing_date: max across all filing rows
    filing_dates = [
        _parse_date(r.get("filing_date", ""))
        for r in rows
        if r.get("filing_date", "").strip()
    ]
    filing_dates_clean = [d for d in filing_dates if d is not None]
    if filing_dates_clean:
        profile["latest_filing_date"] = max(filing_dates_clean).strftime("%Y-%m-%d")

    # filing_frequency_12m: count filings in past 12 months
    today = date.today()
    freq = sum(
        1 for d in filing_dates_clean
        if (today - d).days <= 365
    )
    if filing_dates_clean:
        profile["filing_frequency_12m"] = str(freq)

    # exchange_verified: true if source_id was confirmed via exchange lookup
    # For now: true if any row has source in exchange-class sources AND source_id is populated
    exchange_sources = {
        "SEC_EDGAR", "SGX", "LSE_RNS", "ASX", "BURSA", "NSE", "BSE",
        "EURONEXT", "EDINET", "KRX_DART", "TWSE_MOPS",
    }
    for row in rows:
        if row.get("source", "").upper() in exchange_sources and \
           row.get("source_id", "").strip():
            profile["exchange_verified"] = "True"
            break
    else:
        profile["exchange_verified"] = "False"

    # ── 5. Merge metadata ─────────────────────────────────────────────────────
    sources_seen = sorted({r.get("source", "").strip() for r in rows if r.get("source")})
    profile["source_list"]   = ",".join(sources_seen)
    profile["merge_date"]    = date.today().strftime("%Y-%m-%d")

    # match_confidence: lowest level seen across all rows
    # (set by caller — passed in via rows[0]["_match_confidence"])
    profile["match_confidence"] = rows[0].get("_match_confidence", "HIGH")

    # ── 6. completeness_score ─────────────────────────────────────────────────
    profile["data_completeness_score"] = str(compute_completeness(profile))

    return profile


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_merge(
    input_paths: list[Path],
    profiles_out: Path,
    filings_out: Path,
) -> tuple[int, int]:
    """
    Full merge pipeline.

    Returns (n_profiles, n_filings).
    """
    # ── Load all rows ─────────────────────────────────────────────────────────
    all_rows: list[dict] = []
    print()
    for path in input_paths:
        rows = read_csv(path)
        if rows:
            source_label = rows[0].get("source", str(path.stem))
            print(f"  ✓ {path.name:<35} {len(rows):>4} rows  (source={source_label})")
            all_rows.extend(rows)
        else:
            print(f"  — {path.name:<35}    0 rows  (skipped)")

    print()
    if not all_rows:
        print("[ERROR] No rows loaded. Exiting.")
        sys.exit(1)

    # ── Pre-pass: propagate LEI across rows with identical company_name ────
    # GLEIF rows carry LEI; XBRL / Wikidata rows for the same company don't.
    # Build a name → LEI map from GLEIF rows, then fill blanks in other rows.
    name_to_lei: dict[str, str] = {}
    for row in all_rows:
        lei_val = row.get("lei", "").strip()
        name_key = _normalise(row.get("company_name", ""))
        if lei_val and name_key:
            name_to_lei[name_key] = lei_val

    propagated = 0
    for row in all_rows:
        if not row.get("lei", "").strip():
            name_key = _normalise(row.get("company_name", ""))
            if name_key in name_to_lei:
                row["lei"] = name_to_lei[name_key]
                propagated += 1

    if propagated:
        print(f"  LEI propagation: filled {propagated} row(s) via company name match")

    # ── Entity resolution — group rows by canonical key ───────────────────────
    # key → list of rows
    entity_groups: dict[str, list[dict]] = {}
    # key → match_confidence
    key_confidence: dict[str, str] = {}
    existing_keys: dict[str, str] = {}

    CONFIDENCE_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    for row in all_rows:
        key, confidence = resolve_key(row, existing_keys)
        # Downgrade confidence for an existing key if new match is lower
        if key in key_confidence:
            existing_rank = CONFIDENCE_RANK[key_confidence[key]]
            new_rank = CONFIDENCE_RANK[confidence]
            if new_rank > existing_rank:
                key_confidence[key] = confidence
        else:
            key_confidence[key] = confidence
            existing_keys[key] = confidence

        row["_match_confidence"] = key_confidence[key]
        entity_groups.setdefault(key, []).append(row)

    print(f"  Entity resolution: {len(all_rows)} rows → {len(entity_groups)} distinct entities")
    low_conf = sum(1 for c in key_confidence.values() if c == "LOW")
    if low_conf:
        print(f"  [WARN] {low_conf} entities matched on company name only (LOW confidence) "
              f"— review merged_profiles.csv 'match_confidence' column")
    print()

    # ── Merge profiles + extract filing rows ─────────────────────────────────
    profiles: list[dict] = []
    filings:  list[dict] = []

    for key, rows in entity_groups.items():
        # Attach match confidence to all rows in this group
        for r in rows:
            r["_match_confidence"] = key_confidence[key]

        # Extract filing event rows (keep all, don't merge)
        for row in rows:
            if _is_filing_row(row):
                filing = {
                    "source_id":    row.get("source_id", ""),
                    "lei":          row.get("lei", ""),
                    "company_name": row.get("company_name", ""),
                    "filing_date":  row.get("filing_date", ""),
                    "form_type":    row.get("form_type", ""),
                    "category":     row.get("category", ""),
                    "accession_number": row.get("accession_number", ""),
                    "document_url": row.get("document_url", ""),
                    "source":       row.get("source", ""),
                }
                filings.append(filing)

        # Merge into one company profile
        profile = merge_rows(rows)
        profiles.append(profile)

    # ── Write outputs ─────────────────────────────────────────────────────────
    write_csv(profiles, PROFILE_FIELDS, profiles_out)
    write_csv(filings,  FILING_FIELDS,  filings_out)

    return len(profiles), len(filings)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge TradeInt source CSVs into entity-centric profiles + filing table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=None,
        help="Input CSV files. If omitted, uses all *_results.csv in the current directory.",
    )
    parser.add_argument(
        "--profiles",
        default="merged_profiles.csv",
        help="Output path for company profiles (default: merged_profiles.csv).",
    )
    parser.add_argument(
        "--filings",
        default="merged_filings.csv",
        help="Output path for filing events (default: merged_filings.csv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve input files
    if args.inputs:
        input_paths = [Path(p) for p in args.inputs]
    else:
        input_paths = sorted(Path(".").glob("*_results.csv"))
        if not input_paths:
            # Also accept the default output names from each script
            candidates = ["filings.csv", "gleif_results.csv", "edgar_8k_filings.csv"]
            input_paths = [Path(p) for p in candidates if Path(p).exists()]
        if not input_paths:
            sys.exit(
                "[ERROR] No input files found. "
                "Pass --inputs explicitly or ensure *_results.csv files exist."
            )

    profiles_out = Path(args.profiles)
    filings_out  = Path(args.filings)

    print(f"merge.py v2.0 — TradeInt entity-centric merge")
    print(f"  Input files : {len(input_paths)}")
    print(f"  Profiles out: {profiles_out}")
    print(f"  Filings out : {filings_out}")

    n_profiles, n_filings = run_merge(input_paths, profiles_out, filings_out)

    print(f"✓ merged_profiles.csv : {n_profiles} company profiles")
    print(f"✓ merged_filings.csv  : {n_filings} filing events")
    print()

    # Completeness summary
    with open(profiles_out, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        scores = [float(r.get("data_completeness_score", 0)) for r in reader]

    if scores:
        avg   = sum(scores) / len(scores)
        green = sum(1 for s in scores if s >= 0.7)
        amber = sum(1 for s in scores if 0.4 <= s < 0.7)
        red   = sum(1 for s in scores if s < 0.4)
        print("Completeness summary:")
        print(f"  Average score : {avg:.2f}")
        print(f"  Green  (≥0.70): {green:>4} profiles")
        print(f"  Amber  (≥0.40): {amber:>4} profiles")
        print(f"  Red    (<0.40): {red:>4} profiles")


if __name__ == "__main__":
    main()
