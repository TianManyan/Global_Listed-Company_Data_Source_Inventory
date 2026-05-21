# Runbook — Global Listed-Company Data Sources

**Project:** TradeInt Listed-Company Data Sources & APIs Inventory
**Last updated:** May 2026
**Questions?** Ping the owner listed in Section 1, or paste any error message into Claude and ask for help.

---

## 1. Project Purpose and Owner

### What this runbook covers

This runbook is an operational guide for accessing TradeInt's inventory of global listed-company data sources. It covers:

- **Tier 1 — Free / public API sources** (SEC EDGAR, GLEIF, Wikidata, OpenFIGI): full operational detail — setup, authentication, sample queries, refresh cadence, and known issues
- **Tier 2 — Commercial / no-public-API sources** (SGX, LSE RNS, Euronext, ASX, JPX TDnet, Bursa Malaysia, NSE, BSE, LSEG, Bloomberg, S&P Capital IQ): one-paragraph summary per source covering what it is, how to get access, and cost range

For API endpoint details and cross-source field mapping, see `api.md`. For source architecture and access tiers, see `arch.md`.

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
OPENCORPORATES_API_KEY=your_key_here
EDINET_API_KEY=your_key_here
```

The `.gitignore` already excludes `.env` from being committed. Load keys in Python with:

```python
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("OPENFIGI_API_KEY")
```

### File structure

```
EDGAR-watchlist/
├── edgar_8k_pull.py              # SEC EDGAR 8-K pull script
├── gleif_pull.py                 # GLEIF LEI registry pull script
├── watchlist.csv                 # Ticker list for EDGAR automated runs
├── gleif_watchlist.csv           # Company name list for GLEIF queries
├── schema.md                     # TradeInt cross-source standard schema (14 fields)
├── docs/
│   ├── prd.md                    # Project Spec
│   ├── arch.md                   # Architecture overview
│   ├── api.md                    # API reference
│   ├── changelog.md              # Iteration log
│   └── runbook.md                # This file
├── .env                          # API keys — never commit
├── .gitignore
└── .github/workflows/weekly.yml  # GitHub Actions automation
```

---

## 3. Tier 1 — Free / Public API Sources

### SEC EDGAR (United States)

**What it covers:** All US-listed companies and Exchange Act reporting entities. 8-K (material events), 10-K (annual reports), 10-Q (quarterly reports), and all other SEC form types.

**Run the 8-K pull script:**

```bash
# Fetch recent 8-K filings for specific tickers
python edgar_8k_pull.py --tickers AAPL,MSFT,TSLA

# Limit rows per ticker
python edgar_8k_pull.py --tickers AAPL,MSFT --max-filings 10

# Custom output path
python edgar_8k_pull.py --tickers AAPL --out results/2026-05-20.csv
```

**Run via GitHub Actions (automated, recommended):**

1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click **Weekly 8-K Watchlist Pull** → **Run workflow**
3. Download the CSV artifact when complete (retained 30 days)

**Sample output:**

```
Loading ticker → CIK map from SEC …
  Fetching 8-Ks for AAPL (CIK 0000320193) … 0 filing(s)
  Fetching 8-Ks for MSFT (CIK 0000789019) … 1 filing(s)

✓ Wrote 1 row(s) to filings.csv

ticker    cik           company_name     form    filed_date
--------  ------------  ---------------  ------  ----------
MSFT      0000789019    MICROSOFT CORP   8-K     2026-05-14
```

**Refresh cadence:** Real-time on filing submission. Filings are visible via the API within minutes of submission.

**Rate limit:** 10 req/s (SEC hard limit). Script enforces 110 ms interval. Empirical (2026-05-19): mean latency 386.7 ms, 0 × HTTP 429.

---

### GLEIF LEI Registry (Global)

**What it covers:** Legal Entity Identifier (LEI) records for legal entities worldwide. Useful for cross-border identity resolution, finding parent-subsidiary relationships, and populating the `lei` field in the TradeInt standard schema. Covers US, SG, GB, JP, and 200+ other jurisdictions.

**Run the GLEIF pull script:**

```bash
# Query companies from gleif_watchlist.csv (default)
python gleif_pull.py

# Query specific companies from the command line
python gleif_pull.py --companies "Apple Inc,HSBC Holdings plc"

# Limit results per company, custom output path
python gleif_pull.py --max-results 3 --out results/gleif_2026-05-21.csv
```

**Update gleif_watchlist.csv:**

Open `gleif_watchlist.csv` and add or remove company names. Use official registered legal names for best match accuracy.

```csv
company
Apple Inc
Microsoft Corporation
DBS Group Holdings Ltd
```

**Sample output:**

```
Companies from gleif_watchlist.csv: Apple Inc, Microsoft Corporation, ...

  Querying GLEIF for 'Apple Inc' … 1 record(s)
  Querying GLEIF for 'Microsoft Corporation' … 1 record(s)

✓ Wrote 5 row(s) to gleif_results.csv

source  jurisdiction  company_name               lei
------  ------------  -------------------------  ----------------------
GLEIF   US            Apple Inc.                 HWUPKR0MPOU8FGXBT394
GLEIF   US            MICROSOFT CORPORATION      INR2EJN1ERAN0W5ZP974
GLEIF   SG            DBS GROUP HOLDINGS LTD     5493007FKT78NKPM5V55
```

**Merging with EDGAR output:**

Both scripts output the same 14-column standard schema. To merge:

```bash
python -c "
import csv
from edgar_8k_pull import FIELDNAMES

edgar = list(csv.DictReader(open('filings.csv')))
gleif = list(csv.DictReader(open('gleif_results.csv')))
all_rows = edgar + gleif

with open('combined.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(all_rows)
print(f'{len(edgar)} EDGAR + {len(gleif)} GLEIF = {len(all_rows)} rows → combined.csv')
"
```

**Refresh cadence:** Rolling updates as entities renew LEIs. Bulk CSV files published daily at gleif.org for high-volume use.

**Rate limit:** No hard limit published; fair-use basis. Script enforces 0.5s between requests. Use bulk downloads for thousands of lookups.

---

### Wikidata (Global Knowledge Graph)

**What it covers:** Cross-jurisdiction entity metadata, identifier cross-references (LEI, ISIN, ticker), stock exchange memberships, and ownership relationships. Quality is community-maintained.

**Sample query (SPARQL):**

```sparql
SELECT ?company ?companyLabel ?ticker ?lei WHERE {
  ?company wdt:P31  wd:Q4830453 ;
           wdt:P414 wd:Q13677    ;
           wdt:P249 ?ticker .
  OPTIONAL { ?company wdt:P1278 ?lei . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
LIMIT 10
```

Run interactively at https://query.wikidata.org or via curl:

```bash
curl -G "https://query.wikidata.org/sparql" \
  --data-urlencode 'query=SELECT ?item ?itemLabel WHERE { ?item wdt:P31 wd:Q4830453 . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } } LIMIT 5' \
  -H "Accept: application/json" \
  -H "User-Agent: TradeInt research@tradeint.com"
```

**Refresh cadence:** Community-maintained; no guaranteed schedule. Use weekly bulk dumps for high-volume use.

**Rate limit:** 60 sec processing/60-sec window; max 5 parallel queries per IP. As of May 2026, significantly slower than prior years — keep queries narrow, always set LIMIT.

---

### OpenFIGI (Global Identifier Mapping)

**What it covers:** Maps ISIN, CUSIP, SEDOL, ticker, and 20+ identifier types to FIGI (Financial Instrument Global Identifier). Essential for resolving the same security across different data sources.

**Setup:** Register for a free API key at openfigi.com. Add to `.env`: `OPENFIGI_API_KEY=your_key_here`

⚠️ V2 API sunset: 1 July 2026 — use V3 only.

**Sample query:**

```bash
# Map ISIN to FIGI (Apple Inc.)
curl -X POST "https://api.openfigi.com/v3/mapping" \
  -H "Content-Type: application/json" \
  -H "X-OPENFIGI-APIKEY: $OPENFIGI_API_KEY" \
  -d '[{"idType": "ID_ISIN", "idValue": "US0378331005"}]'
```

**Rate limit:** With key: 25 req/6s, 100 jobs/request. Without key: 25 req/min, 10 jobs/request.

---

## 4. Tier 2 — Commercial / No-Public-API Sources

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

## 5. Known Failures and Remediation

| What you see | What it means | What to do |
|---|---|---|
| `Missing dependency: install requests` | `requests` not installed | `pip install requests` |
| `not found in SEC company_tickers.json` | Ticker not SEC-registered, delisted, or mistyped | Search at https://www.sec.gov/cgi-bin/browse-edgar |
| `HTTP 429` from SEC | Too many requests | Do not run multiple script instances; wait and retry |
| `HTTP 429` from Wikidata | Query processing limit exceeded | Simplify query, add LIMIT, wait for `Retry-After` |
| `HTTP 403` on GitHub push | PAT missing `workflow` scope | Regenerate PAT at github.com/settings/tokens/new with `repo` + `workflow` scopes |
| `No 8-K filings found` | No 8-Ks in the look-back window | Normal — try `--days 30` to widen coverage |
| `No active LEI records found` | Company name not matched in GLEIF | Use the official registered legal name; try a shorter version of the name |
| `category` column missing from CSV | Actions ran an old cached version of the script | Trigger a brand-new run via **Run workflow** button (not Re-run) |
| Wikidata query times out | Graph too large / query too broad | Add more filters, reduce LIMIT, or use bulk dumps |
| OpenFIGI returns empty | Identifier not found or wrong `idType` | Check idType spelling; try `ID_TICKER` with `exchCode` instead of ISIN |
| `ValueError: dict contains fields not in fieldnames` on merge | `filings.csv` was generated by an old version of the script | Re-run `edgar_8k_pull.py` locally to regenerate with standard field names |

---

## 6. Upgrade / Rollback / Emergency Stop

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

*Runbook maintained by Tian Manyan (Product Intern, TradeInt). Last reviewed May 2026.*
