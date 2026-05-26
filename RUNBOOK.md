# Runbook — Global Listed-Company Data Sources

**Project:** TradeInt Listed-Company Data Sources & APIs Inventory
**Last updated:** 2026-05-26
**Schema version:** v2.2 (56 fields)
**Questions?** Ping the owner listed in Section 1, or paste any error message into Claude and ask for help.

---

## 1. Project Purpose and Owner

### What this runbook covers

This runbook is an operational guide for accessing TradeInt's inventory of global listed-company data sources. It covers:

- **Tier 1 — Free / public API sources** (SEC EDGAR, GLEIF, Wikidata, OpenFIGI): full operational detail — setup, authentication, sample queries, refresh cadence, and known issues
- **Tier 2 — Commercial sources** (EODHD): full operational detail — setup, authentication, field mapping, and known limitations
- **Tier 3 — No-public-API sources** (SGX, LSE RNS, Euronext, ASX, JPX TDnet, Bursa Malaysia, NSE, BSE, LSEG, Bloomberg, S&P Capital IQ): one-paragraph summary per source covering what it is, how to get access, and cost range

For API endpoint details and cross-source field mapping, see `api.md`. For field coverage by source, see `field_coverage_matrix.md`.

### Owner

| Field | Detail |
|---|---|
| Owner | Tian Manyan |
| Role | Product Intern, TradeInt |
| Contact | amanda@tradebelong.com |
| Repo | https://github.com/TianManyan/EDGAR-watchlist |
| Automation | GitHub Actions — runs every Monday at 09:00 UTC (17:00 Singapore time) |

---

## 2. Environment Setup

### Prerequisites

| Requirement | Version | How to check |
|---|---|---|
| Python | 3.10 or newer | `python --version` |
| Git | Any recent version | `git --version` |
| `requests` library | Any recent | `pip show requests` |
| `python-dotenv` | Any recent | `pip show python-dotenv` |

### Installation

```bash
git clone https://github.com/TianManyan/EDGAR-watchlist.git
cd EDGAR-watchlist
pip install requests python-dotenv
```

### API key management

SEC EDGAR, GLEIF, and Wikidata require no API keys. For other sources, create a `.env` file in the project root:

```bash
# .env — never commit this file to GitHub
OPENFIGI_API_KEY=your_key_here
EDINET_API_KEY=your_key_here
EODHD_API_KEY=your_key_here        # demo key: 6a1422a45b7334.07835825 (AAPL.US only)
```

The `.gitignore` already excludes `.env` from being committed. Load keys in Python with:

```python
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("EODHD_API_KEY")
```

### File structure

```
EDGAR-watchlist/
├── schema.py                     # ★ Single source of truth — 56 field definitions
├── edgar_8k_pull.py              # SEC EDGAR 8-K filing events
├── edgar_xbrl_pull.py            # SEC EDGAR XBRL financial data (US only)
├── eodhd_pull.py                 # EODHD Fundamentals API (global, paid)
├── gleif_pull.py                 # GLEIF LEI registry + Level 2 parent data
├── openfigi_pull.py              # OpenFIGI ticker → FIGI/ISIN mapping
├── wikidata_pull.py              # Wikidata — founded_year, website (auxiliary)
├── merge_v2.py                   # Entity-centric merge — all sources → profiles
├── schema_v2_2.md                # Human-readable schema documentation
├── field_coverage_matrix.md      # 21 sources × 56 fields coverage matrix
├── api.md                        # API endpoint reference
├── sources_6questions_v5.md      # 18 sources × 6 questions documentation
├── .env                          # API keys — never commit
├── .gitignore
└── .github/workflows/weekly.yml  # GitHub Actions — runs every Monday 09:00 UTC
```

---

## 3. Tier 1 — Free / Public API Sources

### SEC EDGAR (United States)

**What it covers:** All US-listed companies. Two scripts:
- `edgar_8k_pull.py` — 8-K filing events (material announcements)
- `edgar_xbrl_pull.py` — XBRL financial data (revenue, net income, employee count)

**Run the 8-K pull script:**

```bash
python edgar_8k_pull.py --tickers AAPL,MSFT,TSLA
python edgar_8k_pull.py --tickers AAPL,MSFT --max-filings 10
python edgar_8k_pull.py --tickers AAPL --out results/edgar_8k_2026-05-26.csv
```

**Run the XBRL financial data script:**

```bash
python edgar_xbrl_pull.py --tickers AAPL,MSFT
python edgar_xbrl_pull.py --tickers AAPL --out results/edgar_xbrl_2026-05-26.csv
```

**Fields populated by EDGAR scripts:**

| Script | Fields populated |
|---|---|
| `edgar_8k_pull.py` | source, exchange, jurisdiction, company_name, ticker, source_id, industry_sector, industry_code, industry_classification_scheme, country_of_incorporation, exchange_verified, latest_filing_date, filing_frequency_12m, filing_date, form_type, category, accession_number, document_url |
| `edgar_xbrl_pull.py` | source, company_name, ticker, source_id, revenue_usd, revenue_period, net_income_usd, net_income_period, employee_count, employee_count_date |

**Sample output (8-K):**

```
Loading ticker → CIK map from SEC …
  Fetching 8-Ks for AAPL (CIK 0000320193) … 20 filing(s)
  Fetching 8-Ks for MSFT (CIK 0000789019) … 20 filing(s)

✓ Wrote 40 rows → edgar_8k_results.csv

ticker    source_id     company_name    category    filing_date   accession_number
--------  ------------  --------------  ----------  ------------  ----------------
AAPL      0000320193    Apple Inc.      Earnings    2026-04-30    0000320193-26-...
```

**Refresh cadence:** Real-time — filings visible within minutes of submission.
**Rate limit:** 10 req/s (SEC hard limit). Script enforces 110 ms interval.

---

### GLEIF LEI Registry (Global)

**What it covers:** Legal Entity Identifier records worldwide. `gleif_pull.py` queries both Level 1 (entity data) and Level 2 (parent-subsidiary relationships).

**Fields populated:**

Layer 2: `lei`, `source_id`
Layer 3: `company_name_local` (partial), `country_of_incorporation`, `registered_address`, `hq_address` (if different), `parent_company_name`, `parent_lei`, `is_listed_subsidiary`, `legal_form`
Layer 5: `lei_status`, `lei_last_updated`, `lei_next_renewal_date`

**Run the script:**

```bash
python gleif_pull.py --companies "Apple Inc,Microsoft Corporation,DBS Group Holdings"
python gleif_pull.py --companies "Apple Inc" --max-results 3 --out gleif_results.csv
```

**Sample output:**

```
  Querying 'Apple Inc' … lei=HWUPKR0MPOU8FGXBT394  status=ACTIVE  renewal=2027-03-08
  Querying 'Microsoft Corporation' … lei=INR2EJN1ERAN0W5ZP974  status=ACTIVE  renewal=2027-05-04

✓ Wrote 2 row(s) → gleif_results.csv
```

**Tips for better matching:**
- Use the official registered legal name (e.g. `DBS Group Holdings Ltd`, not `DBS`)
- For subsidiaries, GLEIF Level 2 only returns parent data if the parent also has a registered LEI

**Refresh cadence:** Rolling updates as entities renew LEIs (annual). Bulk CSV available at gleif.org.
**Rate limit:** No hard limit; fair-use basis. Script enforces 0.5s between requests.

---

### OpenFIGI (Global Identifier Mapping)

**What it covers:** Maps tickers and ISINs to compositeFIGI. Essential for cross-source entity resolution.

⚠️ **V2 API sunset: 2026-07-01 — script already uses V3 only.**

**Setup:** Register free API key at openfigi.com. Add to `.env`: `OPENFIGI_API_KEY=your_key_here`

**Fields populated:** `figi`, `isin`, `exchange`, `jurisdiction`, `company_name`, `ticker`

**Run the script:**

```bash
# US tickers (default exchange: US)
python openfigi_pull.py --tickers AAPL,MSFT

# Non-US tickers — prefix with exchange code
python openfigi_pull.py --tickers AAPL,MSFT,SP:D05,LN:HSBA,JP:7203

# Map by ISIN
python openfigi_pull.py --isins US0378331005,SG1L01001701
```

**Exchange code reference:**

| Code | Exchange |
|---|---|
| US | NYSE / NASDAQ |
| SP | SGX (Singapore) |
| LN | LSE (London) |
| JP | Tokyo Stock Exchange |
| AU | ASX (Australia) |
| MK | Bursa Malaysia |

**Rate limit:** With key: 25 req/6s. Without key: 25 req/min.

---

### Wikidata (Global Knowledge Graph — Auxiliary)

**Role in pipeline:** Auxiliary source only. Used exclusively for `founded_year` (the only free structured source for this field). `website` and `ticker` are now sourced from EODHD.

**Fields populated:** `founded_year`, `website` (fallback only), `ticker` (fallback only)

**Run the script:**

```bash
python wikidata_pull.py --companies "Apple Inc,Microsoft Corporation,Toyota Motor"
```

**Known issues:**
- Occasional HTTP 502/503 (Wikidata infrastructure) — script handles gracefully with warning
- Coverage drops for small/mid-cap companies
- `founded_year` may lag for recently incorporated entities

**Refresh cadence:** Community-maintained; no guaranteed schedule.
**Rate limit:** 60-second processing window. Script enforces 2s between requests.

---

## 4. Tier 2 — Commercial API Sources

### EODHD (EOD Historical Data — Global Fundamentals)

**What it covers:** Company fundamentals globally — profile data, financials, officers, ESG signals. Primary source for 15 schema v2.2 fields that have no free equivalent.

**Setup:** Add API key to `.env`: `EODHD_API_KEY=your_key_here`
Demo key (AAPL.US only): `6a1422a45b7334.07835825`

**Fields populated:**

| Layer | Fields |
|---|---|
| Layer 2 | `cusip` (US only) |
| Layer 3 | `company_description`, `ipo_date`, `fiscal_year_end`, `industry_sector` (GICS), `industry_code`, `industry_classification_scheme`, `hq_address`, `employee_count`, `employee_count_date`, `website`, `phone`, `officers`, `cross_listings` |
| Layer 4 | `market_cap_usd`, `market_cap_date`, `revenue_usd`, `revenue_period`, `net_income_usd`, `net_income_period` |
| Layer 5 | `is_delisted` |

**Ticker format:** `SYMBOL.EXCHANGE` — e.g. `AAPL.US`, `D05.SG`, `HSBA.LSE`, `7203.TSE`

**Run the script:**

```bash
# With demo key (AAPL.US only)
python eodhd_pull.py --tickers AAPL.US --apikey demo

# With paid key (all markets)
python eodhd_pull.py --tickers AAPL.US,MSFT.US,D05.SG,HSBA.LSE --env

# Custom output
python eodhd_pull.py --tickers AAPL.US,MSFT.US --env --out eodhd_results.csv
```

**Sample output:**

```
eodhd_pull.py v1.0 — paid key
  AAPL.US … revenue=$416,161,000,000  mktcap=$4,535,749,181,440  employees=166000
  MSFT.US … revenue=$281,724,000,000  mktcap=$...  employees=...

✓ Wrote 2 row(s) → eodhd_results.csv
```

**Known limitations:**

| Issue | Detail |
|---|---|
| Demo key limited to AAPL.US | All other tickers return HTTP 403 with demo key |
| Non-US market coverage unverified | Known Issue #4 — awaiting sample data from EODHD support |
| `founded_year` not available | EODHD provides `ipo_date` (listing date) but not incorporation year — use Wikidata for `founded_year` |

**Pricing:** Free plan: 20 calls/day. Paid plans from ~€50/month. See eodhd.com/pricing.
**Rate limit:** Free: 20 req/day. Paid: up to 100,000 req/day. Script enforces 0.5s between requests.

### SGX Company Announcements (Singapore)

SGX is Singapore's primary exchange (~776 listed companies). Announcements are browsable at [sgx.com](https://www.sgx.com/securities/company-announcements) but there is no official public announcement API. For programmatic access, announcement and corporate action data is available via LSEG/Refinitiv commercial feeds. Contact LSEG directly; pricing is not publicly listed.

### LSE RNS / News Explorer (United Kingdom)

RNS processes ~350,000 announcements per year from LSE-listed companies. Free web browsing at [londonstockexchange.com](https://www.londonstockexchange.com/help/whats-news-explorer) with a private investor declaration. Commercial API access requires a contract; 2026 fee schedule: Data Feed £6,500/yr, Real-Time Distribution £26,000/yr, Non-Display/LLM Application £26,000/yr. Note: the 2026 policy explicitly requires Exchange consent for use of RNS content within a Large Language Model. Contact LSEG at lseg.com.

### Euronext Regulated Markets (Pan-European)

Euronext covers Paris, Amsterdam, Brussels, Milan, Oslo, and Dublin. Regulatory rules are browsable at [euronext.com](https://www.euronext.com/en/regulation); company-level disclosure and market data require a commercial agreement. No unified public disclosure API. Contact Euronext data services or a vendor such as LSEG.

### ASX Announcements (Australia)

ASX announcements are browsable at [asx.com.au](https://www.asx.com.au/markets/trade-our-cash-market/announcements) but there is no official public announcement API. Commercial data is available via ASX ComNews® feed or LSEG/Refinitiv under direct contract. See the [ASX Information Services Product & Services Guide v2.30](https://www.asxonline.com/content/dam/asxonline/public/documents/market-information-product-and-services-guide.pdf) for the licensing framework; pricing requires direct negotiation.

### JPX TDnet / EDINET (Japan)

TDnet covers real-time timely disclosure for all TSE-listed companies (all tiers paid: Database Service ¥33,400/month; API Service ¥70,000/month + usage). EDINET covers FSA statutory filings and has a free API with a subscription key — apply at [edinet-fsa.go.jp](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WEEK0060.html). Note: community-reported implicit rate limit of ~12–20 req/min for EDINET batch processing (requests faster than 3–5 s intervals cause connection drops).

### Bursa Malaysia (Malaysia)

Announcements are browsable at [bursamalaysia.com](https://www.bursamalaysia.com/market_information/announcements/company_announcement) but there is no official public announcement API. The 2024 CDS API Gateway is for broker account management only. Commercial market data is available via ICE Consolidated Feed. Contact ICE or Bursa Malaysia directly; pricing is not publicly listed.

### NSE Corporate Filings (India)

NSE filings are browsable at [nseindia.com](https://www.nseindia.com/companies-listing/corporate-filings-financial-results) but there is no stable public API; the site employs strong anti-scraping protections and internal endpoints change frequently. Contact NSE directly for data licensing, or use commercial vendors such as Tickerplant.

### BSE Corporate Announcements (India)

BSE announcements are browsable at [bseindia.com](https://www.bseindia.com/corporates/ann.html) but there is no official public API. The only known commercial API path is Tickerplant at approximately ₹3 lakh/year (~USD 3,600). An unofficial open-source library (BseIndiaApi) wraps undocumented internal endpoints but carries no official support or stability guarantee.

### LSEG / Refinitiv (Global Vendor)

LSEG is the commercial distribution channel for SGX and ASX announcement feeds, and operates the RNS data feed for UK regulatory announcements. Access via enterprise contract. Contact LSEG at [lseg.com](https://www.lseg.com). Not suitable for ad-hoc or low-volume use.

### Bloomberg Data License (Global Vendor)

Bloomberg Data License provides bulk delivery of pricing, reference data, and corporate actions globally via scheduled file delivery or API. Requires an existing Bloomberg enterprise relationship. Contact your Bloomberg representative or [bloomberg.com/professional](https://www.bloomberg.com/professional).

### S&P Capital IQ Pro (Global Vendor)

S&P Capital IQ Pro covers global listed and private company fundamentals, filings, and ownership data. Access via enterprise subscription. Contact S&P Global Market Intelligence at [spglobal.com/marketintelligence](https://www.spglobal.com/marketintelligence).

---

## 6. Merging All Sources — merge_v2.py

`merge_v2.py` reads all source CSVs and combines them into two output files:
- `merged_profiles.csv` — one row per company (entity-centric, 56 + 3 metadata fields)
- `merged_filings.csv` — one row per filing event, linked to profiles via `source_id` + `lei`

**Full pipeline run:**

```bash
python edgar_8k_pull.py --tickers AAPL,MSFT --out edgar_8k_results.csv
python edgar_xbrl_pull.py --tickers AAPL,MSFT --out edgar_xbrl_results.csv
python eodhd_pull.py --tickers AAPL.US,MSFT.US --env --out eodhd_results.csv
python gleif_pull.py --companies "Apple Inc,Microsoft Corporation" --out gleif_results.csv
python openfigi_pull.py --tickers AAPL,MSFT --out openfigi_results.csv
python wikidata_pull.py --companies "Apple Inc,Microsoft Corporation" --out wikidata_results.csv

python merge_v2.py \
  --inputs edgar_8k_results.csv edgar_xbrl_results.csv eodhd_results.csv \
           gleif_results.csv openfigi_results.csv wikidata_results.csv
```

**Entity resolution priority:**

| Level | Match key | Confidence |
|---|---|---|
| 1 | `lei` exact match | HIGH |
| 2 | `isin` exact match | HIGH |
| 3 | `ticker` + `exchange` | MEDIUM |
| 4 | Normalised company name (suffix-stripped) | MEDIUM |

**LEI propagation:** Before entity resolution, `merge_v2.py` builds a `name → lei` map from GLEIF rows and propagates LEI to matching rows from other sources. This ensures EODHD / EDGAR rows merge correctly with GLEIF rows even when they have no LEI.

**Field merge rules:**

| Rule | Applied to |
|---|---|
| AUTHORITATIVE | `lei`, `lei_status`, `legal_form` → GLEIF; `figi`, `isin` → OpenFIGI; `credit_rating` → S&P |
| LATEST (most recent `_date`) | `market_cap_usd`, `revenue_usd`, `net_income_usd`, `employee_count` |
| FIRST_TRUSTED | All other fields; trust order: GLEIF > EDGAR > EODHD > EDINET > Wikidata > OpenFIGI > exchanges |

---

## 7. Known Failures and Remediation

| What you see | What it means | What to do |
|---|---|---|
| `Missing dependency: install requests` | `requests` not installed | `pip install requests` |
| `not found in SEC company_tickers.json` | Ticker not SEC-registered, delisted, or mistyped | Search at https://www.sec.gov/cgi-bin/browse-edgar |
| `HTTP 429` from SEC | Too many requests | Do not run multiple script instances; wait and retry |
| `HTTP 429` from Wikidata | Query processing limit exceeded | Simplify query, add LIMIT, wait for `Retry-After` |
| `HTTP 403` from EODHD | API key lacks access to this ticker | Demo key only works for AAPL.US; paid key required for other tickers |
| `HTTP 403` on GitHub push | PAT missing `workflow` scope | Regenerate PAT at github.com/settings/tokens/new with `repo` + `workflow` scopes |
| `No active LEI records found` | Company name not matched in GLEIF | Use the official registered legal name; try a shorter version |
| `Wikidata 502 Bad Gateway` | Wikidata infrastructure issue | Transient — script handles gracefully and skips; retry later |
| `No data retrieved. CSV not written` from eodhd_pull.py | All tickers returned 403 or 404 | Check ticker format (must be SYMBOL.EXCHANGE); verify API key |
| Same company appears as multiple profiles in merge | Entity resolution failed — names differ across sources | Check `match_confidence` column; ensure GLEIF has been run so LEI can propagate |
| `company_description` empty in merged_profiles | EODHD step failed or only demo key used | Run `eodhd_pull.py` with paid key; verify `eodhd_results.csv` exists before merge |
| `data_completeness_score` unexpectedly low | Key fields missing | Check which source CSVs were included in merge; re-run missing sources |
| `category` column all `Other` | 8-K descriptions not matching classification rules | Review `CATEGORY_RULES` in `edgar_8k_pull.py`; add keywords for your sector |

---

## 8. Upgrade / Rollback / Emergency Stop

### Upgrading

```bash
git add edgar_8k_pull.py
git commit -m "Describe what changed"
git push
```

### Rolling back

```bash
git revert HEAD
git push
```

To restore a specific file to an earlier commit:

```bash
git checkout <commit-hash> -- edgar_8k_pull.py
git commit -m "Revert to <commit-hash>"
git push
```

### Emergency stop — disable weekly automation

1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click **Weekly 8-K Watchlist Pull** → **...** menu → **Disable workflow**

Re-enable via the same path → **Enable workflow**.

---

*Runbook maintained by Tian Manyan (Product Intern, TradeInt). Last reviewed 2026-05-26.*
