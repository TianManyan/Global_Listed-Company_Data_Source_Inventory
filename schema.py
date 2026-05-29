"""
schema.py — TradeInt standard schema v2.3 field definitions.

Single source of truth for FIELDNAMES used across all pull scripts.
All scripts import from here instead of defining their own list.

Usage in scripts:
    from schema import FIELDNAMES, FILING_FIELDS, PROFILE_FIELDS

Schema version: v2.3 (57 fields, 5 layers + Filing layer)
Supersedes:     v2.2 (56 fields, 2026-05-26)
Last updated:   2026-05-29

Changelog v2.2 → v2.3
----------------------
Field count: 56 → 57
Primary Key:  trade_int_id (#0) added — internal auto-increment integer.
              Format: internal integer; external API uses "TI-{id:06d}" prefix.
              Assigned by merge_v2.py at merge time; never sourced from external APIs.
              Pull scripts leave this field blank — merge.py fills it.
Design:       Supervisor decision 2026-05-29: Plan C (internal ID + LEI/ISIN dual index).

Changelog v2.1 → v2.2
----------------------
Field count: 49 → 56
New source:  EODHD (EOD Historical Data) — commercial Fundamentals API
New Layer 2: cusip (#10)
New Layer 3: ipo_date (#14), fiscal_year_end (#15), phone (#26),
             officers (#27), cross_listings (#28)
             [fields #14–32 renumbered from v2.1]
New Layer 5: is_delisted (#48)
             [fields #44–56 renumbered from v2.1]
"""

# ---------------------------------------------------------------------------
# Full field list — output order for all CSV files (schema v2.3, 57 fields)
# ---------------------------------------------------------------------------
FIELDNAMES: list[str] = [
    # Internal Primary Key (#0)
    "trade_int_id",     # 0  Internal auto-increment integer PK. Assigned by merge_v2.py.
                        #    External format: "TI-{id:06d}" (e.g. TI-000001).
                        #    Pull scripts leave blank; never sourced from external APIs.

    # Layer 1 — Source Metadata (#1–3)
    "source",           # 1  Data source identifier (SEC_EDGAR, EODHD, GLEIF, etc.)           # 1  Data source identifier (SEC_EDGAR, EODHD, GLEIF, etc.)
    "exchange",         # 2  Exchange code (NYSE, SGX, LSE, etc.)
    "jurisdiction",     # 3  ISO-2 country code (US, SG, GB, etc.)

    # Layer 2 — Company Identity (#4–10)
    "company_name",     # 4  Official registered company name
    "ticker",           # 5  Stock ticker symbol
    "source_id",        # 6  Source-specific entity ID (CIK, LEI, FIGI, QID…)
    "lei",              # 7  Legal Entity Identifier (GLEIF)
    "isin",             # 8  International Securities Identification Number
    "figi",             # 9  Financial Instrument Global Identifier (compositeFIGI) ⚠️ v2 sunsets 2026-07-01
    "cusip",            # 10 CUSIP identifier (9-char, US securities) — EODHD General.CUSIP

    # Layer 3 — Company Profile (#11–32)
    "company_name_local",             # 11 Local-language company name
    "company_description",            # 12 Business description (EODHD primary)
    "founded_year",                   # 13 Year of legal incorporation (≠ ipo_date)
    "ipo_date",                       # 14 Date shares began trading — EODHD General.IPODate
    "fiscal_year_end",                # 15 Month fiscal year ends — EODHD General.FiscalYearEnd
    "industry_sector",                # 16 GICS Level 1 sector label
    "industry_code",                  # 17 Raw industry code (SIC, NACE, GICS)
    "industry_classification_scheme", # 18 Scheme: SIC / GICS / NACE / NAICS
    "country_of_incorporation",       # 19 ISO-2 country of legal registration
    "registered_address",             # 20 Official registered office address
    "hq_address",                     # 21 Physical headquarters address
    "employee_count",                 # 22 Total full-time employees (most recent)
    "employee_count_date",            # 23 Reference date for employee_count
    "website",                        # 24 Official company website URL
    "primary_products_services",      # 25 Main products/services (comma-separated)
    "phone",                          # 26 Company main telephone — EODHD General.Phone
    "officers",                       # 27 Key executives as JSON string — EODHD General.Officers
    "cross_listings",                 # 28 Other exchanges, comma-separated — EODHD General.Listings
    "parent_company_name",            # 29 Parent company name (if subsidiary)
    "parent_lei",                     # 30 Parent company LEI (GLEIF Level 2)
    "is_listed_subsidiary",           # 31 True if subsidiary of listed parent
    "legal_form",                     # 32 Legal entity form (GLEIF ELF code)

    # Layer 4 — Financial Signals (#33–43)
    "market_cap_usd",       # 33 Market cap in USD — EODHD Highlights.MarketCapitalization
    "market_cap_date",      # 34 Reference date for market_cap_usd
    "revenue_usd",          # 35 Most recent annual revenue in USD
    "revenue_period",       # 36 Fiscal period for revenue_usd (e.g. FY2024)
    "net_income_usd",       # 37 Most recent annual net income in USD
    "net_income_period",    # 38 Fiscal period for net_income_usd
    "credit_rating",        # 39 Credit rating (e.g. AA+, BBB)
    "credit_rating_agency", # 40 Rating agency (S&P, Moody's, Fitch)
    "esg_report_url",       # 41 URL to most recent ESG/sustainability report
    "cdp_rating",           # 42 CDP climate disclosure rating (A/B/C/D/F)
    "cdp_disclosure_year",  # 43 Year of CDP rating

    # Layer 5 — Trust & Verification Signals (#44–51)
    "lei_status",             # 44 ACTIVE / INACTIVE / ANNULLED (GLEIF)
    "lei_last_updated",       # 45 Date GLEIF last updated this LEI record
    "lei_next_renewal_date",  # 46 LEI renewal deadline (past-due = risk signal)
    "exchange_verified",      # 47 True if listing confirmed via exchange source_id
    "is_delisted",            # 48 True if delisted — EODHD General.IsDelisted
    "latest_filing_date",     # 49 Date of most recent regulatory disclosure
    "filing_frequency_12m",   # 50 Count of filings in past 12 months
    "data_completeness_score",# 51 0–1 proportion of key fields populated (merge.py)

    # Filing / Announcement Record (#52–56)
    "filing_date",      # 52 Date filing was submitted
    "form_type",        # 53 Raw form type (8-K, 20-F, etc.) — do not normalise
    "category",         # 54 Standardised event category (M&A, Earnings, etc.)
    "accession_number", # 55 Source-specific unique filing ID
    "document_url",     # 56 Direct URL to primary filing document
]

# ---------------------------------------------------------------------------
# Verify count
# ---------------------------------------------------------------------------
assert len(FIELDNAMES) == 57, f"Expected 57 fields, got {len(FIELDNAMES)}"
assert len(set(FIELDNAMES)) == 57, "Duplicate field names detected"

# ---------------------------------------------------------------------------
# Subsets used by merge_v2.py
# ---------------------------------------------------------------------------

# Fields that are filing events — kept as separate rows, not merged into profile
FILING_EVENT_FIELDS: set[str] = {
    "filing_date", "form_type", "category", "accession_number", "document_url"
}

# Fields output in merged_filings.csv
FILING_FIELDS: list[str] = [
    "source_id", "lei", "company_name",
    "filing_date", "form_type", "category", "accession_number", "document_url",
    "source",
]

# Profile fields = all FIELDNAMES + merge metadata (added by merge_v2.py)
PROFILE_FIELDS: list[str] = FIELDNAMES + ["source_list", "match_confidence", "merge_date"]
# Note: trade_int_id is already in FIELDNAMES (#0); merge_v2.py populates it at merge time.

# ---------------------------------------------------------------------------
# completeness_score weighted fields (used by merge_v2.py)
# B-class structural gaps excluded from denominator
# ---------------------------------------------------------------------------

# weight 1.0 — required + high-value fields (denominator = 17 × 1.0)
SCORE_WEIGHT_1: list[str] = [
    "source", "exchange", "jurisdiction",
    "company_name", "ticker", "source_id",
    "lei", "isin",
    "industry_sector", "country_of_incorporation",
    "lei_status", "exchange_verified",
    "latest_filing_date", "legal_form",
    "filing_date", "form_type", "category",
]

# weight 0.5 — medium-value optional fields (denominator += 6 × 0.5 = 3.0)
SCORE_WEIGHT_HALF: list[str] = [
    "company_description", "founded_year",
    "revenue_usd", "market_cap_usd",
    "employee_count", "website",
]

# B-class fields — structurally absent for some companies; excluded from denominator
# credit_rating, cdp_rating, cdp_disclosure_year, esg_report_url,
# parent_company_name, parent_lei, is_listed_subsidiary,
# officers, cusip, ipo_date, fiscal_year_end, phone, cross_listings

SCORE_MAX: float = len(SCORE_WEIGHT_1) * 1.0 + len(SCORE_WEIGHT_HALF) * 0.5  # = 20.0

# ---------------------------------------------------------------------------
# trade_int_id helpers
# ---------------------------------------------------------------------------

def format_trade_int_id(internal_id: int) -> str:
    """
    Convert internal integer ID to external TI-prefixed string.

    Internal (DB / CSV): 1, 2, 3, …
    External (API / UI): "TI-000001", "TI-000002", "TI-000003", …

    Usage:
        format_trade_int_id(1)       → "TI-000001"
        format_trade_int_id(42)      → "TI-000042"
        format_trade_int_id(999999)  → "TI-999999"
        format_trade_int_id(1000000) → "TI-1000000"  # no truncation
    """
    return f"TI-{internal_id:06d}"


def parse_trade_int_id(external_id: str) -> int:
    """
    Convert external TI-prefixed string back to internal integer.

    Raises ValueError if the string is not a valid TI-XXXXXX identifier.

    Usage:
        parse_trade_int_id("TI-000001") → 1
        parse_trade_int_id("TI-000042") → 42
    """
    if not external_id.upper().startswith("TI-"):
        raise ValueError(f"Not a valid trade_int_id: {external_id!r}")
    return int(external_id[3:])


# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

SOURCE_VOCAB: list[str] = [
    "SEC_EDGAR", "EODHD", "EDINET",
    "SGX", "LSE_RNS", "ASX", "BURSA", "NSE", "BSE", "EURONEXT",
    "KRX_DART", "TWSE_MOPS",
    "GLEIF", "OPENFIGI", "WIKIDATA", "OPENCORPORATES",
    "CDP", "GRI", "SP_RATINGS",
    "LSEG", "BLOOMBERG", "SP_CAPITAL_IQ",
]

CATEGORY_VOCAB: list[str] = [
    "M&A", "Officer Change", "Earnings", "Material Contract",
    "Financing", "Regulatory", "ESG", "Other",
]

GICS_SECTORS: list[str] = [
    "Energy", "Materials", "Industrials", "Consumer Discretionary",
    "Consumer Staples", "Health Care", "Financials", "Information Technology",
    "Communication Services", "Utilities", "Real Estate",
]

# ---------------------------------------------------------------------------
# Source trust order — used by merge_v2.py FIRST_TRUSTED rule
# Lower index = higher trust
# ---------------------------------------------------------------------------
SOURCE_TRUST_ORDER: list[str] = [
    "GLEIF",
    "OPENCORPORATES",
    "SEC_EDGAR",
    "EODHD",
    "EDINET",
    "KRX_DART",
    "TWSE_MOPS",
    "WIKIDATA",
    "OPENFIGI",
    "SGX", "LSE_RNS", "ASX", "BURSA", "NSE", "BSE", "EURONEXT",
    "CDP",
    "GRI",
    "SP_RATINGS",
]
