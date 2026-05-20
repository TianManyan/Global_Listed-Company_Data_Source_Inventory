# Runbook — EDGAR 8-K Watchlist Tool

**Repo:** https://github.com/TianManyan/EDGAR-watchlist  
**Last updated:** May 2026  
**Questions?** Ping the owner listed in Section 1, or paste any error message into Claude and ask for help.

---

## 1. Project Purpose and Owner

### What this tool does

Every week, this tool automatically pulls **8-K filings** from the SEC EDGAR public API for a list of US-listed companies (the "watchlist"). An 8-K is a mandatory report that a US-listed company must file whenever a material event occurs — for example, a merger, a CEO resignation, or a major contract signing.

The tool fetches the filings, classifies each one by event type, saves the results to a CSV file, and stores it on GitHub for the owner to review.

**In plain terms:** instead of manually checking each company's SEC page every week, this tool does it automatically and delivers a tidy spreadsheet.

### What this tool does NOT do

- It does not store data in any database or external system.
- It does not send emails or push notifications (yet).
- It does not cover non-US exchanges (SGX, LSE, etc.) — US only, via SEC EDGAR.

### Owner

| Field | Detail |
|---|---|
| Owner | Tian Manyan |
| Role | Product Intern, TradeInt |
| Contact | amanda@tradebelong.com |
| Repo | https://github.com/TianManyan/EDGAR-watchlist |
| Automation | GitHub Actions — runs every Monday at 09:00 UTC (17:00 Singapore time) |

---

## 2. Install and Dependencies

### Prerequisites

| Requirement | Version | How to check |
|---|---|---|
| Python | 3.10 or newer | `python --version` |
| Git | Any recent version | `git --version` |
| GitHub account | — | https://github.com |
| `requests` library | Any recent | `pip show requests` |

### Step-by-step setup (first time only)

**Step 1 — Clone the repo**

Open Terminal and run:

```bash
git clone https://github.com/TianManyan/EDGAR-watchlist.git
cd EDGAR-watchlist
```

**Step 2 — Install the only dependency**

```bash
pip install requests
```

**Step 3 — Verify the install**

```bash
python edgar_8k_pull.py --help
```

Expected output:

```
usage: edgar_8k_pull.py [-h] [--tickers TICKERS] [--days DAYS] [--out OUT]
...
```

If you see this, setup is complete.

### Environment variables / .env

This tool requires **no API keys and no .env file**. SEC EDGAR is a free public API with no authentication required.

If you ever add a paid data source in the future (e.g. a classification API), create a `.env` file in the project root using this template:

```
# .env — never commit this file to GitHub
# Add API keys here if new data sources are integrated

# Example (not currently used):
# ANTHROPIC_API_KEY=sk-ant-...
# SOME_OTHER_API_KEY=...
```

The `.gitignore` already excludes `.env` from being committed.

### File structure

```
EDGAR-watchlist/
├── edgar_8k_pull.py         # Main script — do not rename
├── watchlist.csv            # Ticker list — edit this to change coverage
├── README.md                # Quick-start guide for developers
├── RUNBOOK.md               # This file
├── .gitignore               # Excludes outputs and secrets from Git
├── .github/
│   └── workflows/
│       └── weekly.yml       # GitHub Actions automation config
└── logs/
    └── run.log              # Append-only run log (auto-created on first run)
```

---

## 3. Day-to-Day Run Commands

### Option A — Let GitHub Actions run it automatically (recommended)

No action needed. The workflow triggers every Monday at 09:00 UTC automatically.

To retrieve results:
1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click the latest **Weekly 8-K Watchlist Pull** run
3. Scroll to **Artifacts** at the bottom
4. Download the ZIP → extract → open `filings.csv`

Results are retained for **30 days** per run.

### Option B — Trigger manually on GitHub (no Terminal needed)

Use this when you want a fresh pull without waiting for Monday.

1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click **Weekly 8-K Watchlist Pull** in the left sidebar
3. Click **Run workflow** → **Run workflow** (green button)
4. Wait ~1–2 minutes → refresh the page → download Artifact as above

### Option C — Run locally in Terminal

Use this when testing changes or running a custom query.

```bash
# Default: read watchlist.csv, look back 30 days
python edgar_8k_pull.py

# Look back 7 days only
python edgar_8k_pull.py --days 7

# Override tickers without editing watchlist.csv
python edgar_8k_pull.py --tickers AAPL,MSFT,NVDA

# Custom output path
python edgar_8k_pull.py --out results/2026-05-20.csv

# Combine options
python edgar_8k_pull.py --days 14 --out results/2026-05-20.csv
```

### Sample output

Terminal will print:

```
Tickers from watchlist.csv: AAPL, MSFT, TSLA, NVDA, AMZN, GOOGL, META, JPM
Look-back window: 7 days (since 2026-05-13)

Loading ticker → CIK map from SEC …

  Fetching 8-Ks for AAPL (CIK 0000320193) … 0 filing(s)
  Fetching 8-Ks for MSFT (CIK 0000789019) … 1 filing(s)
  Fetching 8-Ks for TSLA (CIK 0001318605) … 0 filing(s)
  ...

✓ Wrote 1 row(s) to filings.csv

ticker    cik           company_name               form    filed_date    accession_number
--------  ------------  -------------------------  ------  ------------  -------------------------
MSFT      0000789019    MICROSOFT CORP             8-K     2026-05-14    0001193125-26-224155

Run log → logs/run.log  (OK, 3.1s, 1 hits)
```

The output CSV (`filings.csv`) contains these columns:

| Column | Description |
|---|---|
| `ticker` | Ticker symbol |
| `cik` | SEC company ID |
| `company_name` | Official SEC-registered name |
| `form` | Always `8-K` |
| `filed_date` | Date the filing was submitted to SEC |
| `accession_number` | Unique filing ID — use this to look up the original document |
| `category` | Auto-classified event type (see below) |
| `document_url` | Direct link to the filing document on SEC.gov |

**Category labels:**

| Label | Meaning |
|---|---|
| M&A | Merger, acquisition, or takeover |
| Officer Change | Director/executive appointment or resignation |
| Earnings | Quarterly or annual financial results |
| Material Contract | Major agreement, contract, or amendment |
| Financing | Debt offering, equity issuance, or credit facility |
| Regulatory | SEC inquiry, lawsuit, investigation, or settlement |
| Other | Does not match any of the above (~60–70% classification accuracy) |

### Updating the watchlist

Open `watchlist.csv` and add or remove tickers. The `notes` column is optional.

```csv
ticker,notes
AAPL,Apple Inc.
MSFT,Microsoft
TSLA,Tesla
```

After editing, commit and push:

```bash
git add watchlist.csv
git commit -m "Update watchlist: add TSLA, remove JPM"
git push
```

The next Actions run will use the updated list automatically.

---

## 4. Known Failures and Remediation Paths

### Error → Fix table

| What you see | What it means | What to do |
|---|---|---|
| `Missing dependency: install requests` | `requests` library not installed | Run `pip install requests` then retry |
| `not found in SEC company_tickers.json` | Ticker is not SEC-registered, delisted, or mistyped | Search the company at https://www.sec.gov/cgi-bin/browse-edgar and confirm the correct ticker |
| `HTTP 403` on push | GitHub PAT missing `workflow` scope | Generate a new PAT at https://github.com/settings/tokens/new — tick both `repo` and `workflow` |
| `HTTP 429` in run log | Too many requests sent to SEC | Do not run multiple script instances at the same time; wait a few minutes and retry |
| `No 8-K filings found` | No 8-Ks filed in the look-back window | Normal — not every company files every week. Try `--days 30` to widen the window |
| `error_code=NO_TICKERS` in run log | `watchlist.csv` is empty and no `--tickers` flag passed | Add at least one ticker to `watchlist.csv` |
| `category` column missing from CSV | Actions ran an old cached version of the script | Trigger a brand-new run via **Run workflow** button (not Re-run) |
| Actions run shows yellow warning about Node.js 20 | GitHub deprecation notice for an internal action — does not affect functionality | Ignore for now; will resolve itself when GitHub updates the runner |
| `refusing to allow a PAT to create workflow` on push | PAT lacks `workflow` scope | Regenerate PAT with `repo` + `workflow` scopes; update remote URL: `git remote set-url origin https://YOUR_NEW_PAT@github.com/TianManyan/EDGAR-watchlist.git` |

### How to read the run log

Every run appends one line to `logs/run.log`:

```
2026-05-19T08:42:01Z  tickers=AAPL,MSFT  hits=1  elapsed_sec=3.1  error_code=OK  out=filings.csv
```

If `error_code` is not `OK`, cross-reference with the table above.

---

## 5. Upgrade / Rollback / Emergency Stop

### Upgrading the script

When you make changes to `edgar_8k_pull.py` or `watchlist.csv`:

```bash
git add edgar_8k_pull.py       # or watchlist.csv, or both
git commit -m "Describe what you changed"
git push
```

The next Actions run will automatically use the new version. To verify the update took effect, check the commit hash shown in the Actions run log — it should match your latest commit on GitHub.

### Rolling back to a previous version

If a change breaks something and you need to revert:

**Step 1 — Find the last working commit hash:**

Go to https://github.com/TianManyan/EDGAR-watchlist/commits/main and copy the 7-character hash of the last good commit (e.g. `3a9499c`).

**Step 2 — Revert locally:**

```bash
git revert HEAD
git push
```

This creates a new commit that undoes the last change — safer than deleting history.

If you need to go back further:

```bash
git checkout 3a9499c -- edgar_8k_pull.py   # restore one file to a specific commit
git commit -m "Revert edgar_8k_pull.py to 3a9499c"
git push
```

### Emergency stop — disable the weekly automation

If you need to immediately stop the weekly auto-run (e.g. the script is hitting SEC too hard, or producing bad data):

**On GitHub (no Terminal needed):**

1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click **Weekly 8-K Watchlist Pull** in the left sidebar
3. Click the **...** menu (top right) → **Disable workflow**

The schedule is now paused. No runs will trigger until you re-enable it.

**To re-enable:**

Same path → **Enable workflow**.

### Deleting a bad Artifact

If a specific CSV output contains bad data and you want to remove it:

1. Go to https://github.com/TianManyan/EDGAR-watchlist/actions
2. Click the specific run that produced the bad file
3. Scroll to **Artifacts** → click the **bin icon** next to the artifact

Note: Artifacts expire automatically after 30 days regardless.

---

*Runbook maintained by Tian Manyan (Product Intern, TradeInt). Last reviewed May 2026.*
