# LinkedIn Network Analyzer 🔍

A powerful, local, privacy-first Python utility that parses your exported LinkedIn `Connections.csv`, intelligently detects column variations, classifies senior professional roles, calculates seniority and data quality scores, eliminates duplicate contacts, and generates formatted CSV and multi-sheet Excel reports.

---

## 📋 Features

- **Zero Web Scraping & 100% Offline**: Operates strictly on the CSV file exported directly by you from LinkedIn. No browser automation, no Selenium/Playwright, and no third-party APIs or telemetry.
- **Intelligent Header Detection**: Automatically identifies column names (e.g. `First Name`, `Position`, `Company`, `URL`, `Email Address`, `Connected On`), even with alternate casings or synonyms, and gracefully handles LinkedIn's standard preamble notes.
- **Sophisticated Role Classifier**: Uses word-boundary regex patterns to detect Founders, C-Suite (CEO, CTO, CFO, COO, CMO, CIO, CPO), Directors (Managing, Executive, Board), Senior Leadership (VP, SVP, Head of, Partner, President), and Entrepreneurs—preventing false substring matches (e.g., "receptionist" will never match "CEO").
- **Multi-Category Extraction**: Accurately classifies multi-role titles such as `"Founder & CTO"` into a primary category (`Founder`) and secondary categories (`["CTO"]`).
- **Seniority & Lead Scoring (0–100)**: Ranks contacts based on executive hierarchy and selects the highest score when multi-role titles are present.
- **Multi-Priority Deduplication**: Intelligently merges duplicates using the hierarchy:
  1. Canonical LinkedIn URL
  2. Verified Email
  3. Full Name + Company
  *(Ensures two distinct people with the same name at different companies are never conflated).*
- **Data Quality Scoring (0–100)**: Measures the completeness of each contact record (Name, Company, Position, URL, and Email).
- **Multi-Tab Excel Workbook**: Outputs a professionally styled `.xlsx` file with frozen headers, auto-filters, auto-fitted columns, and an Executive KPI Summary sheet.

---

## 🛠️ Tech Stack & Requirements

- **Python**: 3.11+ (Tested on Python 3.12)
- **pandas**: High-performance data manipulation
- **openpyxl**: Formatted Excel generation
- **pytest**: Test runner and validation framework

---

## 📁 Project Structure

```
linkedin-network-analyzer/
│
├── input/
│   ├── .gitkeep
│   └── sample_connections.csv       # Synthetic dataset for testing
│
├── output/
│   └── .gitkeep                     # Output directory for CSV & XLSX exports
│
├── logs/
│   ├── .gitkeep
│   └── app.log                      # Execution logs
│
├── src/
│   ├── __init__.py
│   ├── main.py                      # CLI parser and pipeline orchestrator
│   ├── csv_loader.py                # Preamble detection and multi-encoding CSV loader
│   ├── column_mapper.py             # Synonym and column mapping engine
│   ├── role_classifier.py           # Regex-based role categorization
│   ├── seniority_scorer.py          # 0-100 scoring, seniority level & lead type
│   ├── deduplicator.py              # Priority deduplication & safe merging
│   ├── exporter.py                  # CSV & styled openpyxl Excel generator
│   └── utils.py                     # URL normalizer, quality scorer, logger
│
├── tests/
│   ├── __init__.py
│   ├── test_column_mapper.py
│   ├── test_role_classifier.py
│   ├── test_seniority_scorer.py
│   └── test_deduplicator.py
│
├── requirements.txt
├── README.md
├── .gitignore
└── run.py
```

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
Ensure Python 3.11 or later is installed:
```powershell
python --version
```

### 2. Set Up Virtual Environment (Windows)

Open PowerShell in the project directory:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

*(On macOS/Linux, replace `.venv\Scripts\activate` with `source .venv/bin/activate`)*

---

## 📥 How to Obtain Your LinkedIn Data Export

1. Log into your LinkedIn account.
2. Click your profile picture at the top right $\rightarrow$ **Settings & Privacy**.
3. In the left navigation, select **Data Privacy**.
4. Under the "How LinkedIn uses your data" section, click **Get a copy of your data**.
5. Select **Want something in particular?** and check **Connections**.
6. Click **Request archive** (LinkedIn will email you a download link within 10–30 minutes).
7. Download the `.zip` archive, extract `Connections.csv`, and place it in the `input/` folder:
   ```
   linkedin-network-analyzer/input/Connections.csv
   ```

---

## 💻 Running the Tool

### Standard Run (All Senior Contacts)
```powershell
python run.py --input input/Connections.csv
```

### Filter by Role
```powershell
# Filter by Founders only
python run.py --input input/Connections.csv --role founder

# Filter by CTOs
python run.py --input input/Connections.csv --role cto

# Filter by CEOs
python run.py --input input/Connections.csv --role ceo

# Filter by C-Suite executives (CEO, CTO, CFO, COO, CMO, CIO, CPO)
python run.py --input input/Connections.csv --role c-suite

# Filter by Directors
python run.py --input input/Connections.csv --role director

# Filter by Entrepreneurs
python run.py --input input/Connections.csv --role entrepreneur
```

### Filter by Company
```powershell
# Exact company match (case-insensitive)
python run.py --input input/Connections.csv --company "Google"

# Substring company match
python run.py --input input/Connections.csv --company-contains "tech"
```

### Keyword Search
Search across Name, Company, and Position:
```powershell
python run.py --input input/Connections.csv --search "AI"
```

### Filter by Location (if present in export)
```powershell
python run.py --input input/Connections.csv --location "India"
```

---

## 📊 Command-Line Options Reference

| Argument | Short | Description |
| :--- | :--- | :--- |
| `--input` | `-i` | Path to input CSV file *(default: `input/Connections.csv`)* |
| `--output-dir` | `-o` | Output directory *(default: `output`)* |
| `--role` | `-r` | Filter by role: `founder`, `cto`, `ceo`, `director`, `entrepreneur`, `c-suite`, `senior` |
| `--company` | `-c` | Exact company name filter *(case-insensitive)* |
| `--company-contains` | | Company name substring filter |
| `--search` | `-s` | Search string across name, company, and title |
| `--location` | `-l` | Filter by geographic location if available in CSV |
| `--export` | | Specific export target subset: `founders`, `c_suite`, `directors`, `entrepreneurs`, `senior` |
| `--log-dir` | | Directory for log files *(default: `logs`)* |
| `--log-level` | | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 📈 Role Classification & Scoring Rules

### Seniority Score Hierarchy (0–100)
When a contact holds multiple titles (e.g. *"Founder & CEO"*), the **highest** score is awarded:

| Role Title | Score | Seniority Level | Lead Type |
| :--- | :---: | :--- | :--- |
| Founder / Co-Founder | **100** | Founder | Founder |
| CEO / Chief Executive Officer | **98** | C-Suite | C-Suite |
| CTO / Chief Technology Officer | **98** | C-Suite | C-Suite |
| CFO / Chief Financial Officer | **95** | C-Suite | C-Suite |
| COO / Chief Operating Officer | **95** | C-Suite | C-Suite |
| CMO / Chief Marketing Officer | **93** | C-Suite | C-Suite |
| CIO / Chief Information Officer | **93** | C-Suite | C-Suite |
| Managing Director | **92** | Executive | Director |
| CPO / CRO / CSO / Other CXO | **92** | C-Suite | C-Suite |
| Executive Director | **90** | Executive | Director |
| Director / Board Director | **85** | Executive | Director |
| Partner / General Partner | **85** | Executive | Senior Leadership |
| President / Co-President | **85** | Executive | Senior Leadership |
| Senior Vice President (SVP / EVP) | **82** | Senior Leadership | Senior Leadership |
| Vice President (VP) | **80** | Senior Leadership | Senior Leadership |
| Head of Department | **75** | Senior Leadership | Senior Leadership |
| General Manager (GM) | **75** | Senior Leadership | Senior Leadership |
| Entrepreneur / Business Owner | **70** | Entrepreneur | Entrepreneur |
| Other / Non-Senior | **0** | Other | Other |

---

## 📤 Output Structure

All outputs are saved to the `output/` directory:

1. **`senior_connections.xlsx`**: Professional multi-sheet Excel workbook:
   - **Summary Tab**: High-level KPI card table with aggregate connection metrics.
   - **All Senior Tab**: All contacts with `seniority_score > 0`.
   - **Founders Tab**: Founders, Co-Founders, and Founding Partners.
   - **C-Suite Tab**: C-level executives.
   - **Directors Tab**: Managing, Executive, and Board Directors.
   - **Entrepreneurs Tab**: Business owners and entrepreneurs.
2. **`senior_connections.csv`**: Master CSV of all senior contacts.
3. **`founders.csv`**: CSV of founders and co-founders.
4. **`c_suite.csv`**: CSV of C-suite executives.
5. **`directors.csv`**: CSV of directors.
6. **`entrepreneurs.csv`**: CSV of entrepreneurs.
7. **`filtered_connections.csv`**: Generated whenever an active filter (`--role`, `--company`, etc.) is applied.

---

## 🔒 Privacy & Security

- **100% Local**: No internet connection is used or required.
- **No Scraping / Telemetry**: No external calls, tracking pixels, or remote APIs.
- **Git Protection**: `.gitignore` is configured to ignore all `*.csv`, `*.xlsx`, `logs/`, and virtual environments to ensure your personal contact data is never accidentally committed.
- **Strict Email Handling**: Only reads email addresses already present in your exported CSV. Never attempts to infer, guess, generate, or scrape email addresses.

---

## 🧪 Running Unit Tests

Run the complete test suite with `pytest`:

```powershell
pytest -v tests/
```

Or using standard `unittest`:

```powershell
python -m unittest discover -s tests -v
```
