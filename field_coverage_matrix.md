# Field Coverage Matrix — TradeInt Cross-Source Schema v2.2

**Project:** Global Listed-Company Data Sources & APIs Inventory
**Version:** 2.0
**Date:** 2026-05-26
**Schema version:** v2.2 (56 fields)
**Sources:** 21 (matching pitch deck source inventory)

---

## How to read this matrix

| Symbol | Meaning |
|---|---|
| ✅ | Source reliably provides this field; high coverage; directly mappable |
| △ | Source partially provides this field; low coverage, indirect derivation, or requires extra processing |
| — | Source does not provide this field |

**Basis for each cell:** ① Live-validated scripts; ② `api.md` documented response fields; ③ `sources_6questions_v5.md`; ④ `13_candidate_source_materials.md`. Commercial vendor cells based on published product documentation.

---

## Matrix A — Layer 1: Source Metadata + Layer 2: Company Identity + Layer 3: Company Profile
*Fields #1–32*

| Source | #1 source | #2 exchange | #3 jurisdiction | #4 company_name | #5 ticker | #6 source_id | #7 lei | #8 isin | #9 figi | #10 cusip | #11 name_local | #12 description | #13 founded_year | #14 ipo_date | #15 fiscal_yr_end | #16 industry_sector | #17 industry_code | #18 industry_scheme | #19 country_of_incorp | #20 registered_address | #21 hq_address | #22 employee_count | #23 employee_date | #24 website | #25 products_services | #26 phone | #27 officers | #28 cross_listings | #29 parent_name | #30 parent_lei | #31 is_subsidiary | #32 legal_form |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **EODHD** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ PrimaryTicker | △ cross-val | ✅ cross-val | △ cross-val | ✅ US only | — | ✅ | — | ✅ | ✅ | ✅ GICS | ✅ GICS | ✅ GICS | ✅ | — | ✅ | ✅ | ✅ UpdatedAt | ✅ | △ extract | ✅ | ✅ | ✅ | — | — | — | — |
| **SEC EDGAR** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ CIK | — | — | — | — | — | — | — | — | — | △ SIC text | ✅ SIC | ✅ SIC | △ state only | — | — | △ XBRL | △ XBRL | — | — | — | — | — | — | — | — | — |
| **GLEIF** | ✅ | — | ✅ | ✅ | — | ✅ LEI | ✅ | — | — | — | △ local | — | — | — | — | — | — | — | ✅ | ✅ | △ hq | — | — | — | — | — | — | — | △ L2 | △ L2 | △ L2 | ✅ ELF |
| **OpenCorporates** | ✅ | — | ✅ | ✅ | — | ✅ company_no | — | — | — | — | — | — | ✅ | — | — | △ | — | — | ✅ | ✅ | — | — | — | — | — | — | — | — | — | — | — | — |
| **Wikidata** | ✅ | △ P414 | ✅ P17 | ✅ | ✅ P249 | ✅ QID | △ P1278 | △ P946 | — | — | △ label | △ desc | △ P571 | — | — | △ P452 | — | — | ✅ P17 | — | △ P159 | — | — | ✅ P856 | — | — | — | — | △ P749 | — | △ P749 | — |
| **OpenFIGI** | ✅ | ✅ exchCode | ✅ | ✅ | ✅ | ✅ compositeFIGI | — | ✅ input | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **EDINET** | ✅ | ✅ | ✅ | ✅ | — | ✅ edinetCode | — | — | — | — | ✅ JP | — | — | — | — | — | — | — | ✅ JP | — | — | △ XBRL | △ XBRL | — | — | — | — | — | — | — | — | — |
| **SGX** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ stock code | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **LSE RNS** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ TIDM | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Euronext** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ ISIN | — | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **ASX** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ ASX code | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Bursa Malaysia** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ stock code | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **NSE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ symbol | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **BSE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ security code | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **KRX / DART** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ corp code | — | — | — | — | ✅ KR | — | — | — | — | △ DART | △ DART | — | ✅ | — | — | △ XBRL | △ XBRL | — | — | — | — | — | — | — | — | — |
| **TWSE / MOPS** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ stock no | — | — | — | — | ✅ ZH | — | — | — | — | △ | — | — | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **CDP** | ✅ | — | ✅ | ✅ | — | — | — | — | — | — | — | — | — | — | — | △ sector | — | — | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **GRI** ⚠️ frozen 2020 | ✅ | — | ✅ | ✅ | — | — | — | — | — | — | — | — | — | — | — | △ | — | — | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **S&P Ratings** | ✅ | — | ✅ | ✅ | △ | — | — | — | — | — | — | — | — | — | — | △ | — | — | ✅ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **LSEG / Refinitiv** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ RIC | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ GICS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Bloomberg** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ BBGID | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ GICS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **S&P Capital IQ** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ SPGID | ✅ | ✅ | — | ✅ | △ | ✅ | ✅ | ✅ | ✅ | ✅ GICS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | △ |

---

## Matrix B — Layer 4: Financial Signals + Layer 5: Trust & Verification + Filing / Announcement
*Fields #33–56*

| Source | #33 mktcap_usd | #34 mktcap_date | #35 revenue_usd | #36 revenue_period | #37 netincome_usd | #38 netincome_period | #39 credit_rating | #40 rating_agency | #41 esg_report_url | #42 cdp_rating | #43 cdp_year | #44 lei_status | #45 lei_last_updated | #46 lei_renewal | #47 exch_verified | #48 is_delisted | #49 latest_filing_date | #50 filing_freq_12m | #51 completeness | #52 filing_date | #53 form_type | #54 category | #55 accession_no | #56 doc_url |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **EODHD** | ✅ | ✅ UpdatedAt | ✅ global | ✅ | ✅ global | ✅ | — | — | — | — | — | — | — | — | — | ✅ IsDelisted | △ UpdatedAt | — | — | — | — | — | — | — |
| **SEC EDGAR** | — | — | △ XBRL US | △ XBRL | △ XBRL US | △ XBRL | — | — | — | — | — | — | — | — | ✅ | — | ✅ | ✅ | ✅ computed | ✅ | ✅ | ✅ | ✅ | ✅ |
| **GLEIF** | — | — | — | — | — | — | — | — | — | — | — | ✅ | ✅ | ✅ | — | — | — | — | — | — | — | — | — | — |
| **OpenCorporates** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | △ | — | △ | — | — | — | — | — | — | — |
| **Wikidata** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **OpenFIGI** | △ partial | △ | — | — | — | — | — | — | — | — | — | — | — | — | ✅ exchCode | — | — | — | — | — | — | — | — | — |
| **EDINET** | — | — | △ XBRL JP | △ XBRL | △ XBRL JP | △ XBRL | — | — | — | — | — | — | — | — | ✅ | — | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ docID | ✅ |
| **SGX** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **LSE RNS** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **Euronext** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **ASX** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **Bursa Malaysia** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **NSE** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | △ | △ | — | △ | △ | △ | — | △ |
| **BSE** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | △ | △ | — | △ | △ | △ | — | △ |
| **KRX / DART** | — | — | △ XBRL KR | △ | △ XBRL KR | △ | — | — | — | — | — | — | — | — | ✅ | — | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TWSE / MOPS** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | ✅ | — | ✅ | △ | — | ✅ | ✅ | ✅ | — | ✅ |
| **CDP** | — | — | — | — | — | — | — | — | △ report link | ✅ | ✅ | — | — | — | — | — | — | — | — | ✅ | ✅ | ✅ ESG | — | ✅ |
| **GRI** ⚠️ frozen 2020 | — | — | — | — | — | — | — | — | △ pre-2020 | — | — | — | — | — | — | — | — | — | — | △ | △ | △ ESG | — | △ |
| **S&P Ratings** | — | — | — | — | — | — | ✅ | ✅ | — | — | — | — | — | — | — | — | △ | — | — | — | — | — | — | ✅ |
| **LSEG / Refinitiv** | ✅ RT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | △ | △ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ computed | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Bloomberg** | ✅ RT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | △ | △ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ computed | ✅ | ✅ | ✅ | ✅ | ✅ |
| **S&P Capital IQ** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | △ | △ | — | ✅ | ✅ | ✅ | ✅ | ✅ computed | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Source Priority by Layer

### Layer 1–2: Source Metadata + Company Identity

| Field | Primary (free) | Secondary (free) | Fallback (paid) |
|---|---|---|---|
| `source_id` | Exchange-specific | — | — |
| `lei` | GLEIF ✅ | EODHD (cross-val) | LSEG |
| `isin` | OpenFIGI ✅ | EODHD (cross-val) | LSEG |
| `figi` | OpenFIGI ✅ | EODHD (cross-val) | Bloomberg |
| `cusip` | EODHD (US only) | — | LSEG |
| `ticker` | Exchange API / EDGAR | Wikidata P249 | — |

### Layer 3: Company Profile

| Field | Primary | Secondary (free) | Notes |
|---|---|---|---|
| `company_description` | EODHD ✅ | — | Only structured source globally |
| `ipo_date` | EODHD ✅ | — | Only structured source globally |
| `fiscal_year_end` | EODHD ✅ | — | Only structured source globally |
| `phone` | EODHD ✅ | — | |
| `officers` | EODHD ✅ | — | JSON string |
| `cross_listings` | EODHD ✅ | — | |
| `founded_year` | Wikidata P571 | OpenCorporates | EODHD does not provide this |
| `industry_sector` | EODHD GICS ✅ | EDGAR SIC→map (US) | EODHD is globally consistent |
| `country_of_incorporation` | GLEIF ✅ | EODHD | |
| `registered_address` | GLEIF ✅ | OpenCorporates | |
| `hq_address` | EODHD ✅ | GLEIF (fallback) | |
| `employee_count` | EODHD ✅ | EDGAR XBRL (US cross-check) | |
| `website` | EODHD ✅ | Wikidata P856 (fallback) | |
| `parent_company_name` / `parent_lei` | GLEIF Level 2 ✅ | Wikidata P749 | |
| `legal_form` | GLEIF ✅ | — | ~100% LEI-registered entities |

### Layer 4: Financial Signals

| Field | Primary | Secondary (free) | Fallback (paid) |
|---|---|---|---|
| `market_cap_usd` | EODHD ✅ global | OpenFIGI (partial) | LSEG RT |
| `revenue_usd` / `net_income_usd` | EODHD ✅ global | EDGAR XBRL (US cross-check) | LSEG |
| `credit_rating` | S&P Ratings (single-lookup) | — | S&P RatingsXpress |
| `esg_report_url` | CDP | Company IR page | — |
| `cdp_rating` | CDP bulk CSV | — | — |
| `is_delisted` | EODHD ✅ | — | Only reliable direct source |

### Layer 5: Trust & Verification

| Field | Primary | Notes |
|---|---|---|
| `lei_status` / `lei_last_updated` / `lei_next_renewal_date` | GLEIF ✅ | ~100% LEI-registered |
| `is_delisted` | EODHD ✅ | More reliable than inferring from exchange_verified |
| `exchange_verified` | Exchange lookup via source_id | Computed by script |
| `latest_filing_date` / `filing_frequency_12m` | EDGAR ✅ (US) | Other markets: EODHD UpdatedAt as proxy |
| `data_completeness_score` | Computed by merge.py | Not from any external source |

---

## Notable Gaps (schema v2.2)

| Gap | Affected fields | Explanation |
|---|---|---|
| EODHD non-US market coverage | #12–28, #33–38, #48 | Known Issue #4 — awaiting sample data from EODHD support for SGX, LSE, ASX, Bursa, NSE, BSE, Euronext, TWSE |
| Financial data for non-US/JP/KR (free tier) | #35–38 | No free XBRL endpoint outside US/JP/KR; EODHD paid key covers globally |
| Credit ratings (bulk) | #39–40 | S&P public tier is single-lookup only; no free bulk API |
| ESG structured data | #41–43 | CDP provides free bulk CSV annually; no real-time API; GRI frozen 2020 |
| Ownership / beneficial shareholders | — | Not in schema v2.2; deferred to v3 (Design Decision 5) |
| `founded_year` for non-major companies | #13 | Wikidata coverage drops sharply for small/mid-cap and emerging market companies |

---

*Matrix compiled: 2026-05-26. Based on schema v2.2 (56 fields) and sources_6questions_v5.md (18 documented sources + 3 commercial vendors). All ✅ cells reflect documented API response fields or validated script output. △ cells reflect partial coverage or require additional processing.*
