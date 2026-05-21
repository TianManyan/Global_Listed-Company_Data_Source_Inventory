# Schema — TradeInt Cross-Source Standard Fields

**Project:** Global Listed-Company Data Sources & APIs Inventory
**Version:** 1.0
**Date:** 2026-05-21

---

## Purpose

This document defines the standard field names and types used across all TradeInt data sources. Every source-specific script must map its raw fields to this schema before writing output. This ensures that CSV outputs from different sources are directly comparable and can be merged without transformation.

**All sources are peers under this schema.** SEC EDGAR is the first implemented source; other sources will follow the same field structure. No source is primary — the schema is the common standard that sits above all of them.

---

## Standard Schema

### Layer 1 — Source Metadata
*Where did this record come from?*

| Standard Field | Type | Description | Required |
|---|---|---|---|
| `source` | string | Data source identifier (see controlled vocabulary below) | ✅ |
| `exchange` | string | Exchange where the company is listed (e.g. `NYSE`, `SGX`, `LSE`) | ✅ |
| `jurisdiction` | string | ISO 2-letter country code of the exchange (e.g. `US`, `SG`, `GB`) | ✅ |

**Controlled vocabulary for `source`:**

| Value | Meaning |
|---|---|
| `SEC_EDGAR` | US SEC EDGAR public API |
| `EDINET` | Japan FSA EDINET API |
| `SGX` | Singapore Exchange web portal |
| `LSE_RNS` | London Stock Exchange RNS |
| `ASX` | Australian Securities Exchange |
| `BURSA` | Bursa Malaysia |
| `NSE` | National Stock Exchange of India |
| `BSE` | Bombay Stock Exchange |
| `EURONEXT` | Euronext (Paris / Amsterdam / Brussels / Milan / Oslo / Dublin) |
| `GLEIF` | GLEIF LEI Registry |
| `OPENFIGI` | Bloomberg OpenFIGI |
| `WIKIDATA` | Wikidata SPARQL endpoint |
| `OPENCORPORATES` | OpenCorporates company registry |

---

### Layer 2 — Company Identity
*Which company does this record refer to?*

| Standard Field | Type | Description | Required |
|---|---|---|---|
| `company_name` | string | Official registered company name as returned by the source | ✅ |
| `ticker` | string | Stock ticker symbol | ✅ where available |
| `source_id` | string | Source-specific company identifier (see mapping table below) | ✅ |
| `lei` | string | Legal Entity Identifier (20-char, from GLEIF) | ⬜ optional |
| `isin` | string | International Securities Identification Number | ⬜ optional |
| `figi` | string | Financial Instrument Global Identifier (from OpenFIGI) | ⬜ optional |

**`source_id` mapping by source:**

| Source | Raw field name | Example value |
|---|---|---|
| SEC EDGAR | `cik` | `0000789019` |
| EDINET | `edinetCode` | `E02144` |
| SGX | stock code | `D05` |
| LSE RNS | TIDM | `HSBA` |
| ASX | ASX code | `CBA` |
| Bursa Malaysia | stock code | `1155` |
| NSE | symbol | `RELIANCE` |
| BSE | security code | `500325` |
| GLEIF | `lei` | `HWUPKR0MPOU8FGXBT394` |
| OpenCorporates | `company_number` | `0902081` |

---

### Layer 3 — Filing / Announcement
*What is this record about?*

| Standard Field | Type | Description | Required |
|---|---|---|---|
| `filing_date` | string (YYYY-MM-DD) | Date the filing or announcement was submitted | ✅ |
| `form_type` | string | Raw form/document type as returned by the source (see examples below) | ✅ |
| `category` | string | Standardised event classification (see controlled vocabulary below) | ✅ |
| `document_url` | string | Direct URL to the primary filing document | ✅ where available |
| `accession_number` | string | Source-specific unique filing ID (for traceability) | ⬜ optional |

**`form_type` examples by source:**

| Source | Example `form_type` values |
|---|---|
| SEC EDGAR | `8-K`, `10-K`, `10-Q`, `DEF 14A` |
| EDINET | `有価証券報告書`、`四半期報告書`、`臨時報告書` |
| SGX | `General Announcement`, `Results`, `Circular` |
| LSE RNS | `RNS`, `TR-1`, `DREP` |
| ASX | `Appendix 4E`, `Change of Director's Interest`, `Market Sensitive` |

**Controlled vocabulary for `category`:**

| Value | Meaning | Triggered by (keywords in form_type / filename) |
|---|---|---|
| `M&A` | Merger, acquisition, or takeover | merger, acquisition, takeover… |
| `Officer Change` | Director or executive appointment / resignation | director, officer, CEO, resign… |
| `Earnings` | Quarterly or annual financial results | result, earnings, revenue, quarter… |
| `Material Contract` | Major agreement, contract, or amendment | agreement, contract, amendment… |
| `Financing` | Debt offering, equity issuance, or credit facility | offering, share, debt, bond… |
| `Regulatory` | Regulatory inquiry, lawsuit, or settlement | regulation, investigation, settlement… |
| `Other` | Does not match any of the above | — |

---

## Full Field Reference

Combined view of all standard fields in output order:

| # | Standard Field | Layer | Type | Required |
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
| 10 | `filing_date` | Filing | string | ✅ |
| 11 | `form_type` | Filing | string | ✅ |
| 12 | `category` | Filing | string | ✅ |
| 13 | `accession_number` | Filing | string | ⬜ |
| 14 | `document_url` | Filing | string | ✅ where available |

---

## SEC EDGAR Field Mapping (currently implemented)

This table shows how `edgar_8k_pull.py` maps EDGAR raw fields to the standard schema.

| Standard Field | EDGAR Raw Field | Notes |
|---|---|---|
| `source` | — | Hardcoded to `SEC_EDGAR` |
| `exchange` | — | Hardcoded to `NYSE/NASDAQ` |
| `jurisdiction` | — | Hardcoded to `US` |
| `company_name` | `name` | Direct mapping |
| `ticker` | CLI input / watchlist | Passed in by the caller |
| `source_id` | `cik` | Zero-padded 10-digit CIK |
| `lei` | — | Not available from EDGAR directly; resolve via GLEIF |
| `isin` | — | Not available from EDGAR directly; resolve via OpenFIGI |
| `figi` | — | Not available from EDGAR directly; resolve via OpenFIGI |
| `filing_date` | `filingDate` | Direct mapping |
| `form_type` | `form` | Direct mapping (e.g. `8-K`) |
| `category` | — | Derived via `classify_8k()` keyword rules |
| `accession_number` | `accessionNumber` | Direct mapping |
| `document_url` | constructed | Built from CIK + accession + primaryDocument |

---

## Source Mapping Examples

The following examples show how three representative sources map their raw fields to the standard schema. Use these as a reference when implementing a new source script.

The three sources were chosen to cover the full spectrum of access complexity, so that any new source can be matched to a known pattern:

| Source | Access type | What it represents |
|---|---|---|
| EDINET | Free API, key required | Automatable but with complexity — non-English docs, extra lookup steps, time parsing |
| LSE RNS | Paid commercial API | Automatable but behind a contract — free-text `form_type`, licensing cost |
| SGX | Web portal only, no API | Hardest case — no `accession_number`, PDF-only documents, scraping instability |

SEC EDGAR (already implemented) anchors the free-API-no-friction end of the spectrum. Together, the four sources cover every access tier in the inventory.

---

### EDINET (Japan — free API with subscription key)

Raw API response (`/api/v2/documents.json`):

```json
{
  "docID": "S100ABCD",
  "filerName": "トヨタ自動車株式会社",
  "edinetCode": "E02144",
  "submitDateTime": "2026-05-14T09:00:00",
  "docDescription": "四半期報告書",
  "docURL": "https://api.edinet-fsa.go.jp/api/v2/documents/S100ABCD"
}
```

| Standard Field | Value | Mapping notes |
|---|---|---|
| `source` | `EDINET` | Hardcoded |
| `exchange` | `TSE` | Hardcoded |
| `jurisdiction` | `JP` | Hardcoded |
| `company_name` | `トヨタ自動車株式会社` | `filerName` — direct mapping (Japanese) |
| `ticker` | `7203` | Not in API response; requires separate lookup via EDINET company list |
| `source_id` | `E02144` | `edinetCode` |
| `filing_date` | `2026-05-14` | `submitDateTime` — truncate to date only |
| `form_type` | `四半期報告書` | `docDescription` — Japanese document type code |
| `category` | `Earnings` | Keyword match: `四半期` → Earnings |
| `accession_number` | `S100ABCD` | `docID` |
| `document_url` | `https://api.edinet-fsa.go.jp/...` | `docURL` |

**Implementation notes:** `filerName` is in Japanese; `submitDateTime` includes time and must be truncated to date only; `ticker` is not returned directly and requires a separate lookup via the EDINET company list.

---

### LSE RNS (United Kingdom — commercial API, contract required)

Raw API response (per RNS Data Feed Technical Specification v1.3):

```json
{
  "sequenceNo": "1234567",
  "issuerName": "HSBC Holdings plc",
  "tidm": "HSBA",
  "publishedDate": "2026-05-14T08:30:00Z",
  "headlineText": "Director/PDMR Shareholding",
  "documentUrl": "https://www.londonstockexchange.com/..."
}
```

| Standard Field | Value | Mapping notes |
|---|---|---|
| `source` | `LSE_RNS` | Hardcoded |
| `exchange` | `LSE` | Hardcoded |
| `jurisdiction` | `GB` | Hardcoded |
| `company_name` | `HSBC Holdings plc` | `issuerName` — direct mapping |
| `ticker` | `HSBA` | `tidm` |
| `source_id` | `HSBA` | `tidm` — LSE uses TIDM as the company identifier |
| `filing_date` | `2026-05-14` | `publishedDate` — truncate to date only |
| `form_type` | `Director/PDMR Shareholding` | `headlineText` — free-text headline, not a code |
| `category` | `Officer Change` | Keyword match: `Director` → Officer Change |
| `accession_number` | `1234567` | `sequenceNo` |
| `document_url` | `https://...` | `documentUrl` — direct mapping |

**Implementation notes:** `tidm` serves as both `ticker` and `source_id`; `form_type` comes from a free-text headline rather than a standardised code; requires a paid commercial contract (2026 fee: £6,500/yr for data feed access).

---

### SGX (Singapore — web portal only, no public API)

Fields parsed from web page HTML:

```json
{
  "company": "DBS Group Holdings Ltd",
  "stockCode": "D05",
  "announcementDate": "2026-05-14",
  "announcementType": "General Announcement",
  "title": "Change of CEO",
  "pdfUrl": "https://links.sgx.com/..."
}
```

| Standard Field | Value | Mapping notes |
|---|---|---|
| `source` | `SGX` | Hardcoded |
| `exchange` | `SGX` | Hardcoded |
| `jurisdiction` | `SG` | Hardcoded |
| `company_name` | `DBS Group Holdings Ltd` | `company` — direct mapping |
| `ticker` | `D05` | `stockCode` |
| `source_id` | `D05` | `stockCode` — SGX uses stock code as company identifier |
| `filing_date` | `2026-05-14` | `announcementDate` — direct mapping |
| `form_type` | `General Announcement` | `announcementType` — fixed category name |
| `category` | `Officer Change` | Keyword match: `CEO` in title → Officer Change |
| `accession_number` | — | Not available — SGX web portal has no unique filing ID |
| `document_url` | `https://links.sgx.com/...` | `pdfUrl` — PDF is the only document format |

**Implementation notes:** No official API; fields are parsed from HTML and may break if SGX changes the page structure; `accession_number` cannot be populated; document is always a PDF.

---

### Cross-source comparison

| | SEC EDGAR | EDINET | LSE RNS | SGX |
|---|---|---|---|---|
| `source_id` raw field | `cik` | `edinetCode` | `tidm` | `stockCode` |
| `form_type` raw field | `form` (code) | `docDescription` (JP code) | `headlineText` (free text) | `announcementType` (category) |
| `ticker` availability | Via watchlist | Requires extra lookup | Direct (`tidm`) | Direct (`stockCode`) |
| `accession_number` | ✅ `accessionNumber` | ✅ `docID` | ✅ `sequenceNo` | ❌ Not available |
| Automation feasibility | ✅ Free API | ✅ Free API (key required) | ✅ Paid contract | ⚠️ Web scraping only |

---

## How to Add a New Source

When implementing a new source script, follow these steps:

1. **Read this document** and identify which standard fields the source can populate.
2. **Map raw fields** to standard fields using the mapping table above as a reference.
3. **Hardcode** `source`, `exchange`, and `jurisdiction` for that source.
4. **Implement `classify()`** using the standard `category` vocabulary.
5. **Output columns in the standard field order** (columns 1–14 above).
6. **Add a mapping table** for the new source to the SEC EDGAR section above.

---

*Schema maintained by Tian Manyan (Product Intern, TradeInt). Last reviewed May 2026.*
