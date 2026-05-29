# Schema — TradeInt Cross-Source Standard Fields

**Project:** Global Listed-Company Data Sources & APIs Inventory
**Version:** 2.2
**Date:** 2026-05-26
**Supersedes:** v2.1 (2026-05-25)

---

## Changelog v2.1 → v2.2

| Change | Detail |
|---|---|
| Field count | 49 → 56 fields |
| New source added | EODHD (EOD Historical Data) — commercial Fundamentals API; fills non-US financial data gaps and provides fields unavailable from any free source |
| New fields (Layer 2) | `cusip` (#10, new) — US securities identifier, directly available from EODHD `General.CUSIP` |
| New fields (Layer 3) | `ipo_date` (#14, new) — exchange listing date, replaces use of `founded_year` as listing proxy; `fiscal_year_end` (#15, new); `phone` (#24, new); `officers` (#25, new); `cross_listings` (#26, new) |
| New fields (Layer 5) | `is_delisted` (#48, new) — direct boolean from EODHD `General.IsDelisted`, more reliable than inferring from `exchange_verified` |
| Source suggestion updates | Layer 3 and Layer 4 source suggestions updated to reflect EODHD as primary for non-US markets |
| Source-to-Layer matrix | EODHD row added |
| EODHD field mapping table | New section added |
| Design Decision 6 | `officers` field stored as JSON string; not a relational table |
| Design Decision 7 | `ipo_date` vs `founded_year` distinction clarified |
| Known Issues | Issue #4 added: EODHD non-US market coverage unverified pending sample data response |

---

## Changelog v2.0 → v2.1

| Change | Detail |
|---|---|
| Field count | 43 → 49 fields |
| New fields (Layer 3) | `industry_classification_scheme` (#15, inserted; fields #15–26 renumbered) |
| New fields (Layer 3) | `legal_form` (#26, new) |
| New fields (Layer 4) | `esg_report_url` (#33), `cdp_rating` (#34), `cdp_disclosure_year` (#35); financial fields renumbered to #36–43 |
| New fields (Layer 5) | `lei_next_renewal_date` (#45); trust fields renumbered to #44–49 |
| Field clarification | `figi` (#9) description updated to specify compositeFIGI |
| New Design Decisions | Decision 4 (`source_id` entity-level semantics), Decision 5 (Ownership data known limitation) |

---

## Changelog v1.0 → v2.0

| Change | Detail |
|---|---|
| Field count | 14 → 43 fields |
| Layer count | 3 → 5 layers |
| New layers | Layer 3 (Company Profile), Layer 4 (Financial Signals), Layer 5 (Trust & Verification Signals) |
| Filing fields renumbered | Former Layer 3 (Filing/Announcement) moves to fields #39–43 |
| Design intent | Schema now supports both **event records** (filings) and **entity profiles** (company portraits). A single company record can carry profile fields (#10–38) alongside zero or more filing records (#39–43). |

---

## Purpose

This document defines the standard field names and types used across all TradeInt data sources. Every source-specific script must map its raw fields to this schema before writing output. This ensures that CSV outputs from different sources are directly comparable and can be merged without transformation.

**All sources are peers under this schema.** No source is primary — the schema is the common standard that sits above all of them.

**Schema design principle:** fields that change over time (market cap, employee count, credit rating) are always paired with a `_date` companion field. A value without a date cannot be verified as current and is harmful in trust-signal contexts.

---

## Layer Overview

| Layer | Name | Fields | Purpose |
|---|---|---|---|
| Layer 1 | Source Metadata | #1–3 | Where did this record come from? |
| Layer 2 | Company Identity | #4–10 | Which company does this record refer to? |
| Layer 3 | Company Profile | #11–32 | Static portrait — who is this company? |
| Layer 4 | Financial Signals | #33–43 | Dynamic financials — what is the company's financial state? |
| Layer 5 | Trust & Verification Signals | #44–50 | Can this company record be trusted? |
| Filing / Announcement | Filing Record | #51–56 | What event or disclosure does this record describe? |

---

## Layer 1 — Source Metadata
*Where did this record come from?*

| # | Field | Type | Required | Description |
|---|---|---|---|---|
| 1 | `source` | string | ✅ | Data source identifier — see controlled vocabulary below |
| 2 | `exchange` | string | ✅ | Exchange where the company is listed (e.g. `NYSE`, `SGX`, `LSE`) |
| 3 | `jurisdiction` | string | ✅ | ISO 2-letter country code of the exchange (e.g. `US`, `SG`, `GB`) |

**Controlled vocabulary for `source`:**

| Value | Meaning |
|---|---|
| `SEC_EDGAR` | US SEC EDGAR public API |
| `EODHD` | EOD Historical Data — Fundamentals API (commercial) |
| `EDINET` | Japan FSA EDINET API |
| `SGX` | Singapore Exchange web portal |
| `LSE_RNS` | London Stock Exchange RNS |
| `ASX` | Australian Securities Exchange |
| `BURSA` | Bursa Malaysia |
| `NSE` | National Stock Exchange of India |
| `BSE` | Bombay Stock Exchange |
| `EURONEXT` | Euronext (Paris / Amsterdam / Brussels / Milan / Oslo / Dublin) |
| `KRX_DART` | Korea Exchange / DART |
| `TWSE_MOPS` | Taiwan Stock Exchange / MOPS |
| `GLEIF` | GLEIF LEI Registry |
| `OPENFIGI` | Bloomberg OpenFIGI |
| `WIKIDATA` | Wikidata SPARQL endpoint |
| `OPENCORPORATES` | OpenCorporates company registry |
| `SP_RATINGS` | S&P Global Ratings (public disclosure tier) |
| `CDP` | CDP (formerly Carbon Disclosure Project) |
| `GRI` | GRI Sustainability Disclosure Database |

---

## Layer 2 — Company Identity
*Which company does this record refer to?*

| # | Field | Type | Required | Description |
|---|---|---|---|---|
| 4 | `company_name` | string | ✅ | Official registered company name as returned by the source |
| 5 | `ticker` | string | ✅ where available | Stock ticker symbol |
| 6 | `source_id` | string | ✅ | Source-specific company identifier — see mapping table below |
| 7 | `lei` | string | ⬜ | Legal Entity Identifier (20-char), from GLEIF. EODHD also returns this field as `General.LEI` — use for cross-validation. |
| 8 | `isin` | string | ⬜ | International Securities Identification Number. OpenFIGI is authoritative; EODHD `General.ISIN` can be used for cross-validation. |
| 9 | `figi` | string | ⬜ | Financial Instrument Global Identifier — specifically the **compositeFIGI** (company level). OpenFIGI is authoritative; EODHD `General.OpenFigi` can be used for cross-validation. ⚠️ **OpenFIGI v2 API sunsets 2026-07-01 — all scripts must use v3 endpoint (`/v3/mapping`).** |
| 10 | `cusip` | string | ⬜ | CUSIP identifier (9-char), primarily for US-listed securities. Source: EODHD `General.CUSIP`. Leave blank for non-US companies. |

**`source_id` mapping by source:**

| Source | Raw field name | Example value |
|---|---|---|
| SEC EDGAR | `cik` | `0000789019` |
| EODHD | `PrimaryTicker` | `AAPL.US` |
| EDINET | `edinetCode` | `E02144` |
| SGX | stock code | `D05` |
| LSE RNS | TIDM | `HSBA` |
| ASX | ASX code | `CBA` |
| Bursa Malaysia | stock code | `1155` |
| NSE | symbol | `RELIANCE` |
| BSE | security code | `500325` |
| KRX/DART | corp code | `00126380` |
| TWSE/MOPS | stock no | `2330` |
| GLEIF | `lei` | `HWUPKR0MPOU8FGXBT394` |
| OpenCorporates | `company_number` | `0902081` |

---

## Layer 3 — Company Profile
*Who is this company? — Static portrait, updated when source data changes.*

| # | Field | Type | Required | Source Suggestion | Description |
|---|---|---|---|---|---|
| 11 | `company_name_local` | string | ⬜ | EDINET, exchange portals | Local-language company name (e.g. Japanese, Chinese). Populate when the primary source is non-English. |
| 12 | `company_description` | string | ⬜ | **EODHD `General.Description`** (primary); company IR page (fallback) | Business description, 100–300 words. EODHD is the only low-cost source providing this field across global markets. |
| 13 | `founded_year` | integer | ⬜ | OpenCorporates, Wikidata | Year of legal incorporation. Distinct from `ipo_date` — see Design Decision 7. |
| 14 | `ipo_date` | string (YYYY-MM-DD) | ⬜ | **EODHD `General.IPODate`** | Date the company's shares began trading on the primary exchange. Distinct from `founded_year`. For companies that listed via re-IPO or transfer, use the most recent listing date. |
| 15 | `fiscal_year_end` | string | ⬜ | **EODHD `General.FiscalYearEnd`** | Month in which the company's fiscal year ends, e.g. `September`, `December`. Required for correctly interpreting `revenue_period` and `net_income_period`. |
| 16 | `industry_sector` | string | ⬜ | **EODHD `General.GicSector`** (primary, global GICS); EDGAR SIC → mapped (US fallback) | High-level sector label. Must use the GICS Level 1 controlled vocabulary: `Energy`, `Materials`, `Industrials`, `Consumer Discretionary`, `Consumer Staples`, `Health Care`, `Financials`, `Information Technology`, `Communication Services`, `Utilities`, `Real Estate`. EODHD provides GICS natively and is the preferred source for cross-market consistency. |
| 17 | `industry_code` | string | ⬜ | **EODHD `General.GicIndustry`** (primary); SEC SIC (US fallback) | Standardised industry code in raw form. Always pair with `industry_classification_scheme`. |
| 18 | `industry_classification_scheme` | string | ⬜ | Same as `industry_code` | Classification scheme for `industry_code`. Controlled vocabulary: `SIC`, `GICS`, `NACE`, `NAICS`. When sourced from EODHD, set to `GICS`. |
| 19 | `country_of_incorporation` | string | ⬜ | GLEIF (authoritative); EODHD `General.CountryISO` (supplementary) | Country where the legal entity is registered, ISO 2-letter code. |
| 20 | `registered_address` | string | ⬜ | GLEIF | Official registered office address. |
| 21 | `hq_address` | string | ⬜ | **EODHD `General.Address` / `General.AddressData`** (primary); GLEIF (fallback) | Physical headquarters address. EODHD returns a structured `AddressData` object with Street, City, State, Country, ZIP. |
| 22 | `employee_count` | integer | ⬜ | **EODHD `General.FullTimeEmployees`** (primary, global); SEC EDGAR XBRL (US cross-check) | Total full-time employee headcount. Always pair with `employee_count_date`. |
| 23 | `employee_count_date` | string (YYYY-MM-DD) | ⬜ | EODHD `General.UpdatedAt` | Reference date for `employee_count`. Use `General.UpdatedAt` from EODHD as proxy. |
| 24 | `website` | string | ⬜ | **EODHD `General.WebURL`** (primary); Wikidata P856 (fallback) | Official company website URL. |
| 25 | `primary_products_services` | string | ⬜ | EODHD `General.Description` (text extraction); company IR page | Main products or services. When sourced from EODHD, extract from `Description` field — not a structured field in the API response. |
| 26 | `phone` | string | ⬜ | **EODHD `General.Phone`** | Company main telephone number as returned by EODHD. Format varies by country. Use as a contact discovery signal, not for programmatic dialling. |
| 27 | `officers` | string | ⬜ | **EODHD `General.Officers`** | Key executive officers as a JSON string. Each entry contains `Name`, `Title`, and `YearBorn`. Example: `[{"Name": "Mr. Timothy D. Cook", "Title": "CEO & Director", "YearBorn": "1961"}]`. Store the full array serialised as a string. See Design Decision 6. |
| 28 | `cross_listings` | string | ⬜ | **EODHD `General.Listings`** | Other exchanges where the company's shares are traded, as a comma-separated string of exchange codes. Example: `LSE,SA`. Source: EODHD `General.Listings` array. |
| 29 | `parent_company_name` | string | ⬜ | GLEIF Level 2, Wikidata | Parent company name, if the entity is a subsidiary. |
| 30 | `parent_lei` | string | ⬜ | GLEIF Level 2 | LEI of the parent company. Use to resolve ownership chains. |
| 31 | `is_listed_subsidiary` | boolean | ⬜ | GLEIF Level 2, Wikidata | `true` if this entity is a listed subsidiary of a publicly traded parent. |
| 32 | `legal_form` | string | ⬜ | GLEIF (`entity.legalForm.id`) | Legal entity form using the GLEIF ELF code, e.g. `PUBLIC LIMITED COMPANY`, `KABUSHIKI KAISHA`. |

**Regional notes for Layer 3:**

| Field | Regional difference |
|---|---|
| `company_name_local` | Required for EDINET (Japan) and TWSE/MOPS (Taiwan); optional but recommended for KRX/DART (Korea) |
| `founded_year` | Often unavailable from exchange APIs; OpenCorporates or Wikidata is the most reliable free source. Not the same as `ipo_date`. |
| `ipo_date` | Available from EODHD globally. For US companies, cross-check against SEC EDGAR `ipoDate` in submissions JSON. |
| `fiscal_year_end` | Available from EODHD globally. Required for interpreting `revenue_period` and `net_income_period` correctly. |
| `industry_sector` | Use EODHD GICS as primary for all markets. Map EDGAR SIC to GICS for US-only fallback. |
| `officers` | Available from EODHD globally. Contains C-suite level only (typically 8–12 officers). Not a substitute for operational contact directories. |
| `cross_listings` | Available from EODHD. Useful for companies listed on multiple exchanges; helps resolve duplicate entity records during merge. |

---

## Layer 4 — Financial Signals
*What is the company's financial state? — Dynamic, updated periodically.*

| # | Field | Type | Required | Source Suggestion | Description |
|---|---|---|---|---|---|
| 33 | `market_cap_usd` | float | ⬜ | **EODHD `Highlights.MarketCapitalization`** (primary, global); OpenFIGI (partial fallback) | Market capitalisation in USD at most recent trading day. Always pair with `market_cap_date`. |
| 34 | `market_cap_date` | string (YYYY-MM-DD) | ⬜ | EODHD `General.UpdatedAt` | Reference date for `market_cap_usd`. |
| 35 | `revenue_usd` | float | ⬜ | **EODHD `Financials.Income_Statement.yearly[latest].totalRevenue`** (primary, global); SEC EDGAR XBRL (US cross-check) | Most recent annual revenue in USD. Always pair with `revenue_period`. |
| 36 | `revenue_period` | string | ⬜ | EODHD `Financials.Income_Statement.yearly[latest].date` | Fiscal period for `revenue_usd`, e.g. `FY2025`. Derive from the `date` field in the yearly Income Statement. |
| 37 | `net_income_usd` | float | ⬜ | **EODHD `Financials.Income_Statement.yearly[latest].netIncome`** (primary, global); SEC EDGAR XBRL (US cross-check) | Most recent annual net income (profit/loss) in USD. Always pair with `net_income_period`. |
| 38 | `net_income_period` | string | ⬜ | EODHD `Financials.Income_Statement.yearly[latest].date` | Fiscal period for `net_income_usd`. |
| 39 | `credit_rating` | string | ⬜ | S&P Ratings (public tier, single-lookup only) | Credit rating, e.g. `AA+`, `BBB`, `BB-`. No bulk API available from free sources. |
| 40 | `credit_rating_agency` | string | ⬜ | Same as `credit_rating` | Rating agency name: `S&P`, `Moody's`, or `Fitch`. Always populate when `credit_rating` is present. |
| 41 | `esg_report_url` | string | ⬜ | CDP; company IR page | URL to the most recent ESG / sustainability report. **Do not use GRI database — frozen December 2020.** |
| 42 | `cdp_rating` | string | ⬜ | CDP public bulk download | CDP climate disclosure rating. Controlled vocabulary: `A`, `A-`, `B`, `B-`, `C`, `C-`, `D`, `D-`, `F`. |
| 43 | `cdp_disclosure_year` | integer | ⬜ | CDP public bulk download | Year of the CDP rating in `cdp_rating`. Required whenever `cdp_rating` is populated. |

**Design decision — date pairing:** Every numeric field that can change over time (`market_cap_usd`, `revenue_usd`, `net_income_usd`, `employee_count`) is paired with a `_date` or `_period` companion. A financial value without a reference date cannot be validated and is a trust liability in anti-fraud contexts.

**Currency note:** All financial values are stored in USD. Scripts pulling non-USD figures must convert at the spot rate on the `_date` / `_period` end date.

---

## Layer 5 — Trust & Verification Signals
*Can this company record be trusted? — Core anti-fraud fields.*

| # | Field | Type | Required | Source Suggestion | Description |
|---|---|---|---|---|---|
| 44 | `lei_status` | string | ⬜ | GLEIF | LEI registration status: `ACTIVE`, `INACTIVE`, or `ANNULLED`. An `INACTIVE` or `ANNULLED` LEI is a significant trust flag. |
| 45 | `lei_last_updated` | string (YYYY-MM-DD) | ⬜ | GLEIF | Date GLEIF last updated this LEI record. |
| 46 | `lei_next_renewal_date` | string (YYYY-MM-DD) | ⬜ | GLEIF `registration.nextRenewalDate` | Date by which the LEI must be renewed. A past-due renewal date is a trust risk signal. |
| 47 | `exchange_verified` | boolean | ⬜ | Exchange portal / `source_id` lookup | `true` if the company's listing has been confirmed via a live lookup against the exchange's own data. |
| 48 | `is_delisted` | boolean | ⬜ | **EODHD `General.IsDelisted`** | `true` if the company has been delisted from its primary exchange. Sourced directly from EODHD — more reliable than inferring delisting status from `exchange_verified` alone. An `is_delisted: true` record should trigger a warning in the UI and be excluded from active counterparty searches. |
| 49 | `latest_filing_date` | string (YYYY-MM-DD) | ⬜ | Exchange APIs / EDGAR | Date of the most recent regulatory disclosure. |
| 50 | `filing_frequency_12m` | integer | ⬜ | Exchange APIs | Count of regulatory disclosures in the past 12 months. |
| 51 | `data_completeness_score` | float (0–1) | ⬜ | Computed by `merge.py` | Proportion of key fields that are populated. Computed at merge time — not pulled from any external API. See note below. |

**Interpretation guide for trust fields:**

| Signal | Threshold | Interpretation |
|---|---|---|
| `lei_status` | `INACTIVE` or `ANNULLED` | Investigate before use; entity may have ceased operations |
| `is_delisted` | `true` | Company no longer actively traded; treat as inactive counterparty |
| `lei_last_updated` | > 12 months ago | LEI maintenance may be lapsed |
| `lei_next_renewal_date` | Past due | Entity has not renewed its LEI |
| `latest_filing_date` | > 12 months ago | No recent disclosure activity; possible shell company |
| `filing_frequency_12m` | < 2 | Unusually low filing activity |
| `data_completeness_score` | < 0.5 | Display warning in UI |

**Note on `data_completeness_score`:** Computed by `merge.py` at merge time. Not pulled from any external API. Score = weighted_filled / 20.0, rounded to 3 decimal places.

**Weight 1.0 fields (17 fields × 1.0 = 17 pts):**
`source`, `exchange`, `jurisdiction`, `company_name`, `ticker`, `source_id`, `lei`, `isin`, `industry_sector`, `country_of_incorporation`, `lei_status`, `exchange_verified`, `latest_filing_date`, `legal_form`, `filing_date`, `form_type`, `category`

**Weight 0.5 fields (6 fields × 0.5 = 3 pts):**
`company_description`, `founded_year`, `revenue_usd`, `market_cap_usd`, `employee_count`, `website`

**Total denominator = 20.0.** Fields not listed above (e.g. `credit_rating`, `cdp_rating`, `officers`, `ipo_date`, `cusip`, `parent_*`) are B-class structural gaps — structurally absent for some companies and excluded from the denominator to avoid penalising records that are genuinely complete for their company type. The authoritative definition lives in `schema.py` (`SCORE_WEIGHT_1`, `SCORE_WEIGHT_HALF`, `SCORE_MAX`). If these two sources ever conflict, `schema.py` takes precedence.

---

## Filing / Announcement Record
*What event or disclosure does this record describe? — Dynamic, one row per filing.*

| # | Field | Type | Required | Description |
|---|---|---|---|---|
| 52 | `filing_date` | string (YYYY-MM-DD) | ✅ | Date the filing or announcement was submitted to the exchange or regulator |
| 53 | `form_type` | string | ✅ | Raw form or document type exactly as returned by the source — do not normalise |
| 54 | `category` | string | ✅ | Standardised event classification — see controlled vocabulary below |
| 55 | `accession_number` | string | ⬜ | Source-specific unique filing ID for traceability |
| 56 | `document_url` | string | ✅ where available | Direct URL to the primary filing document |

**Controlled vocabulary for `category`:**

| Value | Meaning | Triggered by |
|---|---|---|
| `M&A` | Merger, acquisition, or takeover | merger, acquisition, takeover, scheme of arrangement |
| `Officer Change` | Director or executive appointment / resignation | director, officer, CEO, CFO, resign, appoint |
| `Earnings` | Quarterly or annual financial results | result, earnings, revenue, quarter, annual report, 四半期, 有価証券 |
| `Material Contract` | Major agreement, contract, or amendment | agreement, contract, amendment, MOU, LOI |
| `Financing` | Debt offering, equity issuance, or credit facility | offering, share, debt, bond, placement, rights |
| `Regulatory` | Regulatory inquiry, lawsuit, or settlement | regulation, investigation, settlement, fine, penalty |
| `ESG` | Environmental, social, or governance disclosure | sustainability, ESG, climate, CDP, GRI |
| `Other` | Does not match any of the above | — |

---

## Full Field Reference

Complete field list in output order — use this as the column order for all CSV outputs.

| # | Field | Layer | Type | Required |
|---|---|---|---|---|
| 1 | `source` | Source Metadata | string | ✅ |
| 2 | `exchange` | Source Metadata | string | ✅ |
| 3 | `jurisdiction` | Source Metadata | string | ✅ |
| 4 | `company_name` | Company Identity | string | ✅ |
| 5 | `ticker` | Company Identity | string | ✅ where available |
| 6 | `source_id` | Company Identity | string | ✅ |
| 7 | `lei` | Company Identity | string | ⬜ |
| 8 | `isin` | Company Identity | string | ⬜ |
| 9 | `figi` | Company Identity | string | ⬜ |
| 10 | `cusip` | Company Identity | string | ⬜ |
| 11 | `company_name_local` | Company Profile | string | ⬜ |
| 12 | `company_description` | Company Profile | string | ⬜ |
| 13 | `founded_year` | Company Profile | integer | ⬜ |
| 14 | `ipo_date` | Company Profile | string (YYYY-MM-DD) | ⬜ |
| 15 | `fiscal_year_end` | Company Profile | string | ⬜ |
| 16 | `industry_sector` | Company Profile | string | ⬜ |
| 17 | `industry_code` | Company Profile | string | ⬜ |
| 18 | `industry_classification_scheme` | Company Profile | string | ⬜ |
| 19 | `country_of_incorporation` | Company Profile | string | ⬜ |
| 20 | `registered_address` | Company Profile | string | ⬜ |
| 21 | `hq_address` | Company Profile | string | ⬜ |
| 22 | `employee_count` | Company Profile | integer | ⬜ |
| 23 | `employee_count_date` | Company Profile | string (YYYY-MM-DD) | ⬜ |
| 24 | `website` | Company Profile | string | ⬜ |
| 25 | `primary_products_services` | Company Profile | string | ⬜ |
| 26 | `phone` | Company Profile | string | ⬜ |
| 27 | `officers` | Company Profile | string (JSON) | ⬜ |
| 28 | `cross_listings` | Company Profile | string | ⬜ |
| 29 | `parent_company_name` | Company Profile | string | ⬜ |
| 30 | `parent_lei` | Company Profile | string | ⬜ |
| 31 | `is_listed_subsidiary` | Company Profile | boolean | ⬜ |
| 32 | `legal_form` | Company Profile | string | ⬜ |
| 33 | `market_cap_usd` | Financial Signals | float | ⬜ |
| 34 | `market_cap_date` | Financial Signals | string (YYYY-MM-DD) | ⬜ |
| 35 | `revenue_usd` | Financial Signals | float | ⬜ |
| 36 | `revenue_period` | Financial Signals | string | ⬜ |
| 37 | `net_income_usd` | Financial Signals | float | ⬜ |
| 38 | `net_income_period` | Financial Signals | string | ⬜ |
| 39 | `credit_rating` | Financial Signals | string | ⬜ |
| 40 | `credit_rating_agency` | Financial Signals | string | ⬜ |
| 41 | `esg_report_url` | Financial Signals | string | ⬜ |
| 42 | `cdp_rating` | Financial Signals | string | ⬜ |
| 43 | `cdp_disclosure_year` | Financial Signals | integer | ⬜ |
| 44 | `lei_status` | Trust Signals | string | ⬜ |
| 45 | `lei_last_updated` | Trust Signals | string (YYYY-MM-DD) | ⬜ |
| 46 | `lei_next_renewal_date` | Trust Signals | string (YYYY-MM-DD) | ⬜ |
| 47 | `exchange_verified` | Trust Signals | boolean | ⬜ |
| 48 | `is_delisted` | Trust Signals | boolean | ⬜ |
| 49 | `latest_filing_date` | Trust Signals | string (YYYY-MM-DD) | ⬜ |
| 50 | `filing_frequency_12m` | Trust Signals | integer | ⬜ |
| 51 | `data_completeness_score` | Trust Signals | float (0–1) | ⬜ |
| 52 | `filing_date` | Filing / Announcement | string (YYYY-MM-DD) | ✅ |
| 53 | `form_type` | Filing / Announcement | string | ✅ |
| 54 | `category` | Filing / Announcement | string | ✅ |
| 55 | `accession_number` | Filing / Announcement | string | ⬜ |
| 56 | `document_url` | Filing / Announcement | string | ✅ where available |

---

## Source-to-Layer Coverage Matrix

| Source | L1 Metadata | L2 Identity | L3 Profile | L4 Financial | L5 Trust | Filing |
|---|---|---|---|---|---|---|
| **EODHD** | ✅ | ✅ (ticker, ISIN, LEI, FIGI, CUSIP) | ✅ primary (description, GICS, address, employees, website, phone, officers, cross_listings, ipo_date, fiscal_year_end) | ✅ primary global (market_cap, revenue, net_income) | ✅ (is_delisted) | — |
| SEC EDGAR | ✅ | ✅ partial | ✅ partial (SIC→industry_code) | ✅ XBRL US only | ✅ partial | ✅ primary US |
| GLEIF | ✅ | ✅ partial (LEI) | ✅ partial (address, country, legal_form, parent) | — | ✅ primary (LEI status, renewal) | — |
| OpenFIGI | ✅ | ✅ (FIGI, ISIN) | — | △ market_cap partial | — | — |
| EDINET | ✅ | ✅ | ✅ partial (local name) | ✅ XBRL JP only | ✅ partial | ✅ primary JP |
| CDP | ✅ | ✅ partial | — | ✅ (cdp_rating, cdp_disclosure_year) | — | ✅ ESG |
| S&P Ratings | — | — | — | ✅ credit_rating (single-lookup) | — | — |
| Wikidata | ✅ | ✅ partial | ✅ partial (sector, parent, founded_year) | — | — | — |
| SGX / LSE / ASX / Bursa / NSE / BSE / KRX / TWSE | ✅ | ✅ | — | — | ✅ partial (filing dates) | ✅ primary |

---

## EODHD Field Mapping

EODHD Fundamentals API endpoint: `GET https://eodhd.com/api/fundamentals/{TICKER}.{EXCHANGE}?api_token={KEY}&fmt=json`

| Standard Field | EODHD JSON Path | Notes |
|---|---|---|
| `source` | — | Hardcode to `EODHD` |
| `exchange` | `General.Exchange` | Direct mapping |
| `jurisdiction` | `General.CountryISO` | ISO 2-letter code |
| `company_name` | `General.Name` | Direct mapping |
| `ticker` | `General.Code` | Exchange-local ticker |
| `source_id` | `General.PrimaryTicker` | e.g. `AAPL.US` |
| `lei` | `General.LEI` | Use for cross-validation with GLEIF |
| `isin` | `General.ISIN` | Use for cross-validation with OpenFIGI |
| `figi` | `General.OpenFigi` | Use for cross-validation |
| `cusip` | `General.CUSIP` | US securities only |
| `company_description` | `General.Description` | Direct mapping |
| `ipo_date` | `General.IPODate` | Direct mapping (YYYY-MM-DD) |
| `fiscal_year_end` | `General.FiscalYearEnd` | e.g. `September` |
| `industry_sector` | `General.GicSector` | Already GICS Level 1 |
| `industry_code` | `General.GicIndustry` | GICS Level 3 |
| `industry_classification_scheme` | — | Hardcode to `GICS` |
| `country_of_incorporation` | `General.CountryISO` | Supplement with GLEIF for precision |
| `hq_address` | `General.Address` | Flat string; `General.AddressData` for structured |
| `employee_count` | `General.FullTimeEmployees` | Direct mapping |
| `employee_count_date` | `General.UpdatedAt` | Proxy date |
| `website` | `General.WebURL` | Direct mapping |
| `phone` | `General.Phone` | Direct mapping |
| `officers` | `General.Officers` | Serialise full array as JSON string |
| `cross_listings` | `General.Listings` | Extract `Exchange` values, join with comma |
| `market_cap_usd` | `Highlights.MarketCapitalization` | In USD |
| `market_cap_date` | `General.UpdatedAt` | Proxy date |
| `revenue_usd` | `Financials.Income_Statement.yearly[latest].totalRevenue` | Take most recent year key |
| `revenue_period` | `Financials.Income_Statement.yearly[latest].date` | Convert to `FY{YYYY}` format |
| `net_income_usd` | `Financials.Income_Statement.yearly[latest].netIncome` | Direct mapping |
| `net_income_period` | `Financials.Income_Statement.yearly[latest].date` | Same as `revenue_period` |
| `is_delisted` | `General.IsDelisted` | Boolean string `"True"`/`"False"` → convert to bool |

⚠️ **Non-US market coverage unverified as of 2026-05-26.** Demo key returns `Forbidden` for all non-US tickers. Sample data request sent to EODHD support. Do not assume non-US fields are populated until verified — see Known Issues #4.

---

## SEC EDGAR Field Mapping (currently implemented)

| Standard Field | EDGAR Raw Field | Notes |
|---|---|---|
| `source` | — | Hardcode to `SEC_EDGAR` |
| `exchange` | — | Resolve per-company from `exchanges` array in submissions JSON ⚠️ currently hardcoded |
| `jurisdiction` | — | Hardcode to `US` |
| `company_name` | `name` | Direct mapping |
| `ticker` | CLI input / watchlist | Passed in by caller |
| `source_id` | `cik` | Zero-padded 10-digit CIK |
| `industry_sector` | `sicDescription` | Map SIC text to GICS Level 1 |
| `industry_code` | `sic` | SIC code |
| `industry_classification_scheme` | — | Hardcode to `SIC` |
| `country_of_incorporation` | `stateOfIncorporation` | 2-letter state code for US |
| `employee_count` | XBRL `dei:EntityNumberOfEmployees` | Requires XBRL endpoint |
| `revenue_usd` | XBRL `us-gaap:Revenues` | Requires XBRL endpoint |
| `net_income_usd` | XBRL `us-gaap:NetIncomeLoss` | Requires XBRL endpoint |
| `latest_filing_date` | Most recent `filingDate` | From submissions JSON |
| `filing_frequency_12m` | Count of filings in past 12m | Computed from submissions JSON |
| `filing_date` | `filingDate` | Direct mapping |
| `form_type` | `form` | Direct mapping |
| `accession_number` | `accessionNumber` | Direct mapping |
| `document_url` | constructed | Built from CIK + accession + primaryDocument |

---

## Design Decisions

### Decision 1 — Date pairing for time-varying fields
`employee_count` / `employee_count_date`, `market_cap_usd` / `market_cap_date`, `revenue_usd` / `revenue_period`, `net_income_usd` / `net_income_period` always appear as pairs. A numeric value without a reference date cannot be validated as current, which is actively harmful in trust-signal contexts. Any future time-varying field added to the schema must include a paired `_date` or `_period` field.

### Decision 2 — `data_completeness_score` is a computed field
This field is not sourced from any external API. It is calculated by `merge.py` at merge time. It drives the completeness progress bar in the HTML prototype: scores below 0.5 trigger a warning banner on the company card.

### Decision 3 — Filing layer is optional per record
Not every record needs to carry filing data. A record pulled from GLEIF to populate LEI status will have Layers 1–5 populated but filing fields blank. `merge.py` is responsible for combining partial records into a single company profile.

### Decision 4 — `source_id` is an entity-level identifier, not a filing-level identifier
`source_id` uniquely identifies a **company** within a given source. It is **not** a filing-level identifier — `accession_number` (#55) is the unique ID for a single filing event. Confusing the two will cause `merge.py` to incorrectly treat multiple filings as separate entities.

### Decision 5 — Ownership data is a known limitation, deferred to v3
Major shareholder and beneficial ownership data is not included in v2.x due to: irregular update frequency, severe cross-market format divergence, and the need for a dedicated parsing layer. Recommended approach for v3: implement a separate `ownership` table linked via `source_id` + `lei`.

### Decision 6 — `officers` is stored as a JSON string, not a relational table
The `officers` field contains an array of officer records serialised as a JSON string. This is intentional: a relational `officers` table would require a separate schema and join logic in `merge.py`. For v2.x, storing as a string preserves the data while keeping the schema flat. Scripts should serialise using `json.dumps(officers_array)`. Consumers should deserialise with `json.loads()`. A dedicated officers table is recommended for v3.

### Decision 7 — `ipo_date` vs `founded_year` are distinct fields
`ipo_date` (when shares began trading) and `founded_year` (when the legal entity was incorporated) are different dates and should never be used interchangeably. EODHD `General.IPODate` reflects the listing date, not incorporation. For companies that listed via re-IPO, SPAC, or exchange transfer, `ipo_date` reflects the most recent listing event. `founded_year` must be sourced separately from OpenCorporates or Wikidata.

---

## Known Issues & Time-Sensitive Warnings

| # | Issue | Affected Field / Source | Deadline | Action Required |
|---|---|---|---|---|
| 1 | OpenFIGI v2 API sunsets (RESOLVED) | `figi` (#9) | **2026-07-01** | Migrate all scripts to `/v3/mapping` endpoint before this date |
| 2 | GRI database frozen since December 2020 | `esg_report_url` (#41) | Already past | Do not use GRI as live source; use CDP or company IR page |
| 3 | `exchange` field hardcoded to `NYSE/NASDAQ` in `edgar_8k_pull.py` (RESOLVED) | `exchange` (#2) | Week 2 fix | Resolve per-company using `exchanges` array in submissions JSON |
| 4 | EODHD non-US market coverage unverified | All EODHD-sourced fields for non-US markets | Pending | Awaiting sample data from EODHD support for SGX, LSE, ASX, Bursa, NSE, BSE, Euronext, TWSE. Do not mark EODHD as verified primary source for non-US markets until confirmed. |

---

## How to Add a New Source

1. Read this document and identify which standard fields the source can populate.
2. Map raw fields to standard fields using the EDGAR and EODHD mapping tables as reference.
3. Hardcode `source`, `exchange`, and `jurisdiction` for that source.
4. Implement `classify()` using the standard `category` vocabulary if the source produces filing records.
5. Output columns in the standard field order (#1–56 above).
6. Add a mapping table for the new source to this document.
7. Update the Source-to-Layer Coverage Matrix above.

---

*Schema maintained by Tian Manyan (Product Intern, TradeInt). Last reviewed 2026-05-26.*
