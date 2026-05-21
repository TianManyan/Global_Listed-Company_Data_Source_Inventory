# TradeInt Listed-Company Data Watchlist Tool

Pull regulatory filings and entity data from multiple global sources — currently **SEC EDGAR** (US 8-K filings) and **GLEIF** (global LEI records). All outputs follow the TradeInt cross-source standard schema (14 fields, see `schema.md`) and can be merged into a single CSV with `merge.py`.

**Sources implemented:**
- SEC EDGAR — free public REST API, no key required
- GLEIF LEI Registry — free public REST API, no key required

**Docs:** https://www.sec.gov/about/developer-resources · https://www.gleif.org/en/lei-data/gleif-api

---

## 5-Minute Quick-Start

### 1 — Prerequisites

- Python 3.10 or newer
- `requests` library

```bash
pip install requests
```

### 2 — Clone / copy the tool

Copy these four items into a working directory:

```
edgar_8k_pull.py   ← main script
watchlist.csv      ← your ticker list (edit this)
logs/              ← auto-created on first run
```

### 3 — Edit your watchlist

Open `watchlist.csv` and add or remove tickers (one per row). The `notes` column is optional and ignored by the script.

```csv
ticker,notes
AAPL,Apple Inc.
MSFT,Microsoft
TSLA,Tesla
```

### 4 — Run it

```bash
# Default: reads watchlist.csv, looks back 30 days, writes filings.csv
python edgar_8k_pull.py

# Custom look-back window
python edgar_8k_pull.py --days 7

# Pass tickers directly (overrides watchlist.csv)
python edgar_8k_pull.py --tickers AAPL,MSFT,NVDA

# Custom output path
python edgar_8k_pull.py --out results/week_of_2026-05-19.csv

# Combine options
python edgar_8k_pull.py --days 14 --out /tmp/q2_8k.csv
```

### 5 — Read the output

The output CSV follows the **TradeInt standard schema** (14 columns, same across all sources):

| Column | Description |
|---|---|
| `source` | Data source identifier (e.g. `SEC_EDGAR`, `GLEIF`) |
| `exchange` | Exchange where the company is listed |
| `jurisdiction` | ISO 2-letter country code (e.g. `US`, `SG`, `GB`) |
| `company_name` | Official company name from the source |
| `ticker` | Stock ticker symbol |
| `source_id` | Source-specific company identifier (e.g. CIK for EDGAR, LEI for GLEIF) |
| `lei` | Legal Entity Identifier (filled by GLEIF; empty for EDGAR) |
| `isin` | International Securities Identification Number (optional) |
| `figi` | Financial Instrument Global Identifier (optional) |
| `filing_date` | Date the filing was submitted (YYYY-MM-DD) |
| `form_type` | Raw form/document type as returned by the source (e.g. `8-K`) |
| `category` | Standardised event classification (see below) |
| `accession_number` | Source-specific unique filing ID |
| `document_url` | Direct URL to the primary filing document |

**Category labels** (keyword-rule based, accuracy ~60–70%):

| Label | Triggered by |
|---|---|
| M&A | merger, acquisition, takeover… |
| Officer Change | director, officer, CEO, resign… |
| Earnings | result, earnings, revenue, quarter… |
| Material Contract | agreement, contract, amendment… |
| Financing | offering, share, debt, bond… |
| Regulatory | regulation, investigation, settlement… |
| Other | anything that doesn't match the above |

---

## CLI Reference

```
python edgar_8k_pull.py [OPTIONS]

Options:
  --tickers  AAPL,MSFT,...   Comma-separated tickers. If omitted, reads watchlist.csv.
  --days     N               Look-back window in calendar days. Default: 30.
  --out      PATH            Output CSV path. Default: filings.csv.
  -h, --help                 Show this help message and exit.
```

---

## Run Log

Every run appends one line to `logs/run.log` (auto-created):

```
2026-05-19T08:42:01Z  tickers=AAPL,MSFT,TSLA  hits=12  elapsed_sec=4.3  error_code=OK  out=filings.csv
```

| Field | Meaning |
|---|---|
| Timestamp | UTC time the run finished |
| `tickers` | Tickers that were queried |
| `hits` | Number of 8-K rows written to CSV |
| `elapsed_sec` | Total wall-clock time |
| `error_code` | `OK`, `NO_RESULTS`, `NO_TICKERS`, `HTTP_429`, `EXCEPTION`, `INTERRUPTED` |
| `out` | Output path |

---

## File Structure

```
EDGAR-watchlist/
├── edgar_8k_pull.py      # SEC EDGAR 8-K pull script
├── gleif_pull.py         # GLEIF LEI registry pull script
├── merge.py              # Merge multiple source CSVs into one
├── watchlist.csv         # Ticker list for EDGAR (edit this)
├── gleif_watchlist.csv   # Company name list for GLEIF (edit this)
├── schema.md             # TradeInt cross-source standard schema (14 fields)
├── README.md             # This file
├── RUNBOOK.md            # Operational guide for all sources
├── filings.csv           # EDGAR output (auto-created each run)
├── gleif_results.csv     # GLEIF output (auto-created each run)
├── combined.csv          # Merged output from merge.py
├── .github/
│   └── workflows/
│       └── weekly.yml    # GitHub Actions automation
└── logs/
    └── run.log           # Append-only run log (auto-created)
```

---

## How It Works

1. **Ticker → CIK mapping** — fetches `https://www.sec.gov/files/company_tickers.json` (one request covering all ~10,000 SEC-registered tickers).
2. **Submissions JSON** — for each CIK, fetches `https://data.sec.gov/submissions/CIK{cik}.json`, which contains recent filings in reverse-chronological order.
3. **Filtering** — keeps only `form == "8-K"` rows with `filing_date ≥ today − days`.
4. **Rate limiting** — enforces ≥ 0.11 s between requests (≈ 9 req/sec), safely under the SEC's documented 10 req/sec ceiling.
5. **Output** — writes matching rows to CSV and logs the run summary.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Missing dependency: install requests` | `requests` not installed | `pip install requests` |
| `not found in SEC company_tickers.json` | Ticker not SEC-registered, or delisted | Check the ticker on EDGAR directly |
| `HTTP 429` logged | Too many requests in parallel | Don't run multiple instances simultaneously |
| `No 8-K filings found` | No 8-Ks filed in the look-back window | Increase `--days` or check the ticker on EDGAR |
| Empty `watchlist.csv` + no `--tickers` | Nothing to query | Add tickers to `watchlist.csv` |

---

## Licence & Data Terms

- Script code: internal TradeInt tooling — no external licence.
- **SEC EDGAR data**: free and public. Use must comply with SEC's fair-access policy. Do not exceed 10 req/sec. See https://www.sec.gov/about/developer-resources.
- Redistribution of raw EDGAR filing content is subject to SEC guidelines; consult TradeInt legal before redistributing.

---

*Maintained by TradeInt Product Team. Questions → amanda@tradebelong.com*
