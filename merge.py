"""
merge.py — Merge CSV outputs from multiple TradeInt data source scripts
          into a single combined CSV following the standard schema (schema.md).

All input CSVs must follow the TradeInt standard schema (14 columns).
Outputs from edgar_8k_pull.py and gleif_pull.py are compatible by default.

Dependencies: none (standard library only)

Usage examples
--------------
# Merge default files: filings.csv + gleif_results.csv → combined.csv
    python merge.py

# Specify input files explicitly
    python merge.py --inputs filings.csv gleif_results.csv

# Custom output path
    python merge.py --out results/combined_2026-05-21.csv

# Add a third source when available
    python merge.py --inputs filings.csv gleif_results.csv edinet_results.csv
"""

import argparse
import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Standard field order — must match schema.md
# ---------------------------------------------------------------------------
FIELDNAMES = [
    "source", "exchange", "jurisdiction",
    "company_name", "ticker", "source_id", "lei", "isin", "figi",
    "filing_date", "form_type", "category", "accession_number", "document_url",
]

# Default input files (one per source script)
DEFAULT_INPUTS = ["filings.csv", "gleif_results.csv"]
DEFAULT_OUT    = "combined.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict]:
    """Read a standard-schema CSV. Validates columns on load."""
    if not path.exists():
        print(f"  [SKIP] {path} not found — skipping")
        return []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"  [SKIP] {path} is empty — skipping")
        return []

    # Warn if columns don't match the standard schema
    actual   = set(reader.fieldnames or [])
    expected = set(FIELDNAMES)
    missing  = expected - actual
    extra    = actual - expected
    if missing:
        print(f"  [WARN] {path} is missing standard columns: {sorted(missing)}")
    if extra:
        print(f"  [WARN] {path} has unexpected columns (will be dropped): {sorted(extra)}")

    # Normalise: keep only standard fields, fill missing with empty string
    normalised = []
    for row in rows:
        normalised.append({f: row.get(f, "") for f in FIELDNAMES})

    return normalised


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge TradeInt source CSVs into one standard-schema output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=DEFAULT_INPUTS,
        help=f"Input CSV files to merge (default: {' '.join(DEFAULT_INPUTS)}).",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output CSV path (default: {DEFAULT_OUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args   = parse_args()
    inputs = [Path(p) for p in args.inputs]
    out    = Path(args.out)

    print(f"Merging {len(inputs)} source file(s) → {out}")
    print()

    all_rows: list[dict] = []
    counts:   dict[str, int] = {}

    for path in inputs:
        rows = read_csv(path)
        if rows:
            source_label = rows[0].get("source", str(path))
            counts[source_label] = len(rows)
            all_rows.extend(rows)
            print(f"  ✓ {path.name:30s} {len(rows):>4} rows  (source={source_label})")
        else:
            print(f"  — {path.name:30s}    0 rows  (skipped)")

    print()

    if not all_rows:
        print("No rows to merge. Output file not written.")
        sys.exit(1)

    write_csv(all_rows, out)

    # Summary
    total = len(all_rows)
    print(f"✓ Wrote {total} rows to {out}")
    print()
    print("Breakdown by source:")
    for source, count in counts.items():
        pct = count / total * 100
        print(f"  {source:<20s} {count:>4} rows  ({pct:.0f}%)")


if __name__ == "__main__":
    main()
