"""
schema.py — TradeInt standard schema v2.1 field definitions.

Single source of truth for FIELDNAMES used across all pull scripts.
All scripts import from here instead of defining their own list.

Usage in scripts:
    from schema import FIELDNAMES, FILING_FIELDS, PROFILE_FIELDS

Schema version: v2.1 (49 fields, 5 layers + Filing layer)
Last updated:   2026-05-25
"""

# ---------------------------------------------------------------------------
# Full field list — output order for all CSV files
# ---------------------------------------------------------------------------
FIELDNAMES: list[str] = [
    # Layer 1 — Source Metadata
    "source",           # 1  Data source identifier (SEC_EDGAR, GLEIF, etc.)
    "exchange",         # 2  Exchange code (NYSE, SGX, LSE, etc.)
    "jurisdiction",     # 3  ISO-2 country code (US, SG, GB, etc.)

    # Layer 2 — Company Identity
    "company_name",     # 4  Official registered company name
    "ticker",           # 5  Stock ticker symbol
    "source_id",        # 6  Source-specific entity ID (CIK, LEI, FIGI, QID…)
    "lei",              # 7  Legal Entity Identifier (GLEIF)
    "isin",             # 8  International Securities Identification Number
    "figi",             # 9  Financial Instrument Global Identifier (compositeFIGI)

    # Layer 3 — Company Profile
    "company_name_local",             # 10  Local-language company name
    "company_description",            # 11  Business description (100–300 words)
    "founded_year",                   # 12  Year of incorporation
    "industry_sector",                # 13  GICS Level 1 sector label
    "industry_code",                  # 14  Raw industry code (SIC, NACE, GICS)
    "industry_classification_scheme", # 15  Scheme: SIC / GICS / NACE / NAICS
    "country_of_incorporation",       # 16  ISO-2 country of legal registration
    "registered_address",             # 17  Official registered office address
    "hq_address",                     # 18  Physical headquarters address
    "employee_count",                 # 19  Total employees (most recent)
    "employee_count_date",            # 20  Reference date for employee_count
    "website",                        # 21  Official company website URL
    "primary_products_services",      # 22  Main products/services (comma-separated)
    "parent_company_name",            # 23  Parent company name (if subsidiary)
    "parent_lei",                     # 24  Parent company LEI (GLEIF Level 2)
    "is_listed_subsidiary",           # 25  True if subsidiary of listed parent
    "legal_form",                     # 26  Legal entity form (GLEIF ELF code)

    # Layer 4 — Financial Signals
    "market_cap_usd",       # 27  Market cap in USD (most recent trading day)
    "market_cap_date",      # 28  Reference date for market_cap_usd
    "revenue_usd",          # 29  Most recent annual revenue in USD
    "revenue_period",       # 30  Fiscal period for revenue_usd (e.g. FY2024)
    "net_income_usd",       # 31  Most recent annual net income in USD
    "net_income_period",    # 32  Fiscal period for net_income_usd
    "credit_rating",        # 33  Credit rating (e.g. AA+, BBB)
    "credit_rating_agency", # 34  Rating agency (S&P, Moody's, Fitch)
    "esg_report_url",       # 35  URL to most recent ESG/sustainability report
    "cdp_rating",           # 36  CDP climate disclosure rating (A/B/C/D/F)
    "cdp_disclosure_year",  # 37  Year of CDP rating

    # Layer 5 — Trust & Verification Signals
    "lei_status",             # 38  ACTIVE / INACTIVE / ANNULLED (GLEIF)
    "lei_last_updated",       # 39  Date GLEIF last updated this LEI record
    "lei_next_renewal_date",  # 40  LEI renewal deadline (past-due = risk signal)
    "exchange_verified",      # 41  True if listing confirmed via exchange source_id
    "latest_filing_date",     # 42  Date of most recent regulatory disclosure
    "filing_frequency_12m",   # 43  Count of filings in past 12 months
    "data_completeness_score",# 44  0–1 proportion of key fields populated (merge.py)

    # Filing / Announcement Record
    "filing_date",      # 45  Date filing was submitted
    "form_type",        # 46  Raw form type (8-K, 20-F, etc.) — do not normalise
    "category",         # 47  Standardised event category (M&A, Earnings, etc.)
    "accession_number", # 48  Source-specific unique filing ID
    "document_url",     # 49  Direct URL to primary filing document
]

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

# ---------------------------------------------------------------------------
# Controlled vocabularies (for validation and documentation)
# ---------------------------------------------------------------------------

# Allowed values for the `source` field
SOURCE_VOCAB: list[str] = [
    "SEC_EDGAR", "EDINET", "SGX", "LSE_RNS", "ASX", "BURSA",
    "NSE", "BSE", "EURONEXT", "KRX_DART", "TWSE_MOPS",
    "GLEIF", "OPENFIGI", "WIKIDATA", "OPENCORPORATES",
    "CDP", "GRI", "SP_RATINGS",
    "LSEG", "BLOOMBERG", "SP_CAPITAL_IQ",
]

# Allowed values for the `category` field (filing events)
CATEGORY_VOCAB: list[str] = [
    "M&A", "Officer Change", "Earnings", "Material Contract",
    "Financing", "Regulatory", "ESG", "Other",
]

# GICS Level 1 sectors — controlled vocabulary for `industry_sector`
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
