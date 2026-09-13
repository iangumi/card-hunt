# Card Hunt Local

Card Hunt Local is a local-first Streamlit app for turning Pokémon card store
screenshots into a reviewed hunt worksheet and purchase ledger.

Its goal is simple: reduce screenshot transcription and ranking work without
giving up human control over exact-card identity, market judgment, or purchase
decisions.

> screenshot → crop → AI identify → verify → rank → purchase ledger

## Project status

- **v2 complete:** local crop detection, Gemini identification, conservative
  identity gates, manual scoring, ranking, ledger, and audit trail.
- **v2.1 active:** workflow hardening, recovery, faster review, and usage
  summaries. See the [active milestone](docs/milestones/v2.1-workflow-hardening.md).

## Current capabilities

- Detect card regions locally or create manual crops.
- Preserve padded crop context for store price and request labels.
- Identify exact prints and visible store metadata with structured Gemini output.
- Retry temporary Gemini failures and use a configurable fallback model.
- Route ambiguous variants to review instead of silently ranking them.
- Correct results manually and apply an explicit `Verified` override.
- Calculate a weighted Hunt Score from user-entered market factors.
- Gate Active Ranking and purchases by identity, budget, request count, and status.
- Save hunt worksheets, maintain a purchase ledger, inspect audit events, and
  export CSV or Excel.
- Run the complete manual workflow without an API key.

Market research and sold-comparable collection are still manual. Card Hunt
Local does not currently automate purchase recommendations.

## Quick start

Python 3.11 or newer is recommended.

### macOS / Linux

```bash
git clone https://github.com/iangumi/card-hunt.git
cd card-hunt
cp .env.example .env
# Add GEMINI_API_KEY to .env only if you want AI identification.
./run.sh
```

### Windows PowerShell

```powershell
git clone https://github.com/iangumi/card-hunt.git
Set-Location card-hunt
Copy-Item .env.example .env
# Add GEMINI_API_KEY to .env only if you want AI identification.
.\run.ps1
```

The launch script creates `.venv`, installs the dependencies, and starts
Streamlit.

## Gemini configuration

```dotenv
GEMINI_API_KEY=your-key-here
CARD_HUNT_MODEL=gemini-3.8-flash
CARD_HUNT_FALLBACK_MODEL=gemini-3.5-flash
```

`GEMINI_API_KEY` is optional unless an AI Identify action is used. Never commit
your populated `.env` file.

The primary model retries temporary `503 UNAVAILABLE` responses four times with
backoff and jitter before the fallback model is tried.

## Privacy and local-first behavior

Screenshot processing, crop detection, scoring, hunt files, the ledger, and the
manual workflow stay on the local machine.

**Only a context crop explicitly submitted through an AI Identify action is
sent to the Gemini API.** The full screenshot is not automatically uploaded.

User records live beneath `data/`, which is ignored by Git. Back up that
directory; it contains the ledger, saved hunts, crops, and audit log.

## Screenshots

Project screenshots are not committed yet.

| View | Placeholder |
| --- | --- |
| Intake and detected crops | Screenshot to be added |
| AI review and verification | Screenshot to be added |
| Hunt worksheet and ranking | Screenshot to be added |
| Purchase ledger | Screenshot to be added |

## Roadmap

v2.1 is hardening the existing workflow. Planned releases then introduce a
market-snapshot foundation, evidence collection and history, decision/scoring
integration, hunt analytics, and portfolio lifecycle support before the v1.0
stable release. Identification-quality improvements continue alongside this
work and do not block the market roadmap.

See the full [project roadmap](docs/ROADMAP.md).

## Documentation

- [Documentation index](docs/README.md)
- [Product definition](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [v2.1 workflow-hardening milestone](docs/milestones/v2.1-workflow-hardening.md)
- [Decision log](docs/DECISIONS.md)
- [Development guide and Definition of Done](docs/DEVELOPMENT.md)

## Migrating v1 local data

If the v1 directory is beside this repository:

```bash
python migrate_v1.py ../card_hunt_local_app
```

The migration skips destination files that already exist. Back up both data
directories before migrating.
