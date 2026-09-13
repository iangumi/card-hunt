# Development guide

## Scope and safety

Card Hunt Local contains application code and user-owned local state. Before
editing, inspect both tracked changes and untracked non-ignored files:

```bash
git status --short
git diff
git diff --cached
git ls-files --others --exclude-standard
```

Do not reset, clean, overwrite, migrate, or delete local work unless the owner
explicitly requests it. Do not broadly inspect ignored files. In particular,
never read or expose `.env`, credentials, tokens, API keys, local Streamlit
secrets, crops, ledger rows, hunts, or audit contents merely to understand the
repository.

## Local setup

Python 3.11 or newer is recommended. The launch scripts create `.venv`, install
`requirements.txt`, and run `app.py`:

```bash
cp .env.example .env
# Add GEMINI_API_KEY only if AI Identify will be used.
./run.sh
```

On Windows PowerShell, use `Copy-Item` and `./run.ps1` as shown in the root
[README](../README.md). Never commit the populated `.env` file.

## Code responsibilities

- Keep Streamlit orchestration and presentation in `app.py`.
- Keep provider-independent crop, candidate, scoring, ledger, and audit helpers
  in `card_hunt_core.py` so they can be tested without launching Streamlit.
- Keep Gemini transport, schema, retries, and usage adaptation in
  `ai_identify.py`.
- Preserve candidate and ledger columns unless a compatibility plan is
  documented first.
- Preserve manual verification as an explicit user action.

## Verification

Run these checks before handing off a code change:

```bash
pytest
python -c "import ai_identify; import card_hunt_core"
git diff --check
```

Tests must not call the live Gemini API. Use mocked clients, errors, responses,
sleep, and jitter as the current Gemini tests do. A missing API key should not
prevent imports or provider-independent unit tests.

For documentation-only changes, `git diff --check` plus link and content review
is sufficient unless the documentation change reveals a code concern.

## Manual release checks

Use disposable data or a backed-up copy; never repurpose the user's active
ledger or audit log as test fixtures.

1. Upload a screenshot, detect crops, and add a manual crop if needed.
2. Confirm selected-crop and all-crop AI actions preserve state across reruns.
3. Confirm partial AI failures keep previous results and expose per-crop retry.
4. Confirm ambiguous or low-confidence IDs appear in review and stay out of
   Active Ranking.
5. Confirm manual correction plus `Verified` enables the intended override.
6. Confirm budget, request-count, and status gates affect ranking.
7. Save a hunt, add an eligible purchase, edit/save the ledger, and test both
   exports.
8. Upload different bytes and confirm a new screenshot-specific session starts.

Live Gemini checks are manual integration tests. They require explicit use of a
real key and may incur quota or cost; never run them as part of unit tests.

## Documentation maintenance

- Update [PRODUCT.md](PRODUCT.md) for scope, principles, eligibility, or
  non-goal changes.
- Update [ARCHITECTURE.md](ARCHITECTURE.md) for component, data flow, state,
  persistence, provider, or configuration changes.
- Update [ROADMAP.md](ROADMAP.md) when work is proposed, reprioritized, or
  completed.
- Add an entry to [DECISIONS.md](DECISIONS.md) for durable choices and
  supersessions.
- Keep the root README concise and runnable.
