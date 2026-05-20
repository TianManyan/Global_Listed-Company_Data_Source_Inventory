# edgar_8k_pull — SEC EDGAR 8-K Watchlist Tool

Pull recent **8-K (material event) filings** from SEC EDGAR for any list of US-listed tickers. Results are saved to a CSV and every run is logged automatically.

**Source:** SEC EDGAR free public REST API — no API key required.  
**Rate limit:** ≤ 10 req/sec (SEC documented); the script enforces this automatically.  
**Docs:** https://www.sec.gov/about/developer-resources

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

The output CSV has these columns:

| Column | Description |
|---|---|
| `ticker` | Ticker symbol as entered |
| `cik` | SEC CIK (10-digit, zero-padded) |
| `company_name` | Official company name from SEC |
| `form` | Always `8-K` |
| `filed_date` | Filing date (YYYY-MM-DD) |
| `accession_number` | SEC accession number (unique filing ID) |
| `document_url` | Direct URL to the primary filing document |

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
edgar_tool/
├── edgar_8k_pull.py   # Main script
├── watchlist.csv      # Ticker list (edit this)
├── filings.csv        # Output (auto-created / overwritten each run)
├── README.md          # This file
└── logs/
    └── run.log        # Append-only run log (auto-created)
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

*Maintained by TradeInt Product Team. Questions → research@tradeint.com*
