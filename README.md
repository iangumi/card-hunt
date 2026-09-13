# Card Hunt Local v2

v2 adds the first AI-assisted stage to the working v1 flow:

**store screenshot → local crops → AI exact card identification + price/req extraction → confidence gate → manual market scoring → ranking → purchase ledger**

## What is new

- Gemini vision identification for each card crop
- Structured output for:
  - card name
  - card number
  - set / promo
  - year
  - language
  - variant
  - raw / slab and visible grade
  - store price in JPY
  - req count
  - confidence values
  - possible alternative matches
  - visible evidence
- Conservative variant gate:
  - ambiguous cards are routed to **Needs Review**
  - cards below the confidence threshold do not enter Active Ranking
  - you can manually set `Verified=True` after checking
- Padded context crops to retain price / req stickers
- Re-analyze a hard card one crop at a time
- Audit trail for AI results and purchases
- Token-usage table for the current session
- Existing local/manual mode still works without an API key

## Privacy / network behavior

Cropping, ledger, scoring, and session files remain local.

**Only crops sent through an AI Identify button leave the local machine; those crops are sent to the Gemini API.**
No API call occurs in normal/manual mode, which remains fully local.

## Install

Python 3.11+ recommended.

### macOS / Linux

```bash
unzip card_hunt_local_app_v2.zip
cd card_hunt_local_app_v2

cp .env.example .env
# Edit .env and add GEMINI_API_KEY

./run.sh
```

### Windows PowerShell

```powershell
Expand-Archive card_hunt_local_app_v2.zip
cd card_hunt_local_app_v2

Copy-Item .env.example .env
# Edit .env and add GEMINI_API_KEY

.\run.ps1
```

The first run creates `.venv`, installs dependencies and starts Streamlit.

## API model

Default:

```text
GEMINI_API_KEY=...
CARD_HUNT_MODEL=gemini-3.8-flash
CARD_HUNT_FALLBACK_MODEL=gemini-3.5-flash
```

The model selection applies to both the full hunt and one-crop retry workflow.
Temporary `503 UNAVAILABLE` responses are retried four times with backoff before
the optional fallback model is used.

## Migrate your v1 ledger/data

If v1 is next to v2:

```bash
python migrate_v1.py ../card_hunt_local_app
```

The migration script does not overwrite files that already exist in v2.

You can also manually copy the v1 `data/` folder.

## Recommended workflow

1. Upload screenshot.
2. Auto-detect or manually crop.
3. AI Identify All.
4. Check **Needs Review**.
5. For difficult cards, retry only that crop.
6. Correct exact variant manually when required.
7. Mark `Verified=True`.
8. Research recent sold comps externally.
9. Fill the 0–10 market/Hunt Score factors.
10. Purchase only after the exact-ID gate passes.
11. Move purchased cards to Ledger.

## Why market research is still manual

v2 intentionally automates **identification + store metadata first**.

This keeps the most error-prone step auditable before we add web/market automation.
A future v3 can add sold-comp snapshots and research sources after v2 proves reliable.

## Files

```text
data/ledger.csv
data/hunts/
data/crops/
data/audit.jsonl
```

Back up the `data/` directory.
