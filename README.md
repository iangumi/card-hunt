# Card Hunt Local App

A local, mobile-friendly-ish Streamlit app for your Pokémon card hunt workflow.

## What it does

- Drag/drop a store screenshot
- Experimental automatic card-region detection
- Manual crop fallback
- Shows crops as a reference strip
- Builds a Hunt worksheet
- Applies your current rules:
  - max ¥10,000 per card by default
  - `req_count > 0` goes to Watch if Released
  - sold / owned / bought / passed cards are removed from Active ranking
- Calculates the 100-point Hunt Score
- Saves hunt sessions
- Moves purchases into a permanent local ledger
- Exports CSV and Excel

## Important limitation

This app does **not** automatically identify cards or fetch sold comps from PSA/PriceCharting/eBay.

Use it as the local workspace:
`drop screenshot -> crop -> identify/research -> fill worksheet -> rank -> buy -> ledger`

Later you can add an AI/API layer.

## Install

Requires Python 3.11+.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Or:

```bash
chmod +x run.sh
./run.sh
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Or run:

```powershell
run.ps1
```

## One-command after first install

macOS / Linux:
```bash
./run.sh
```

Windows:
```powershell
./run.ps1
```

The browser should open automatically.

## Data

Everything stays local:

- `data/ledger.csv` — permanent ledger
- `data/hunts/` — saved hunt sessions
- `data/crops/` — card crops

Back up the `data/` folder periodically.
