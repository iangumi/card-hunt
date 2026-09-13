# Roadmap

This roadmap is a planning aid, not a release promise. Items move to the current
baseline only after implementation, automated verification where practical,
and the listed manual checks.

## Current baseline: v2

The repository currently provides:

- local screenshot intake, automatic detection, and manual crops;
- stable upload fingerprints across ordinary Streamlit reruns;
- tight crops and padded context crops;
- optional Gemini structured identification with per-crop retry;
- transient retry/backoff and configurable fallback behavior;
- conservative exact-variant confidence and manual-verification gates;
- nullable candidate numeric dtypes and failed-update isolation;
- manual Hunt Score factors, Active Ranking, hunt saves, ledger, audit, and
  exports;
- mocked AI tests that do not make live network calls.

## Milestone 1: v2 operational validation

Goal: establish a repeatable manual release check over representative real
screenshots without expanding product scope.

Proposed work:

- Maintain a non-secret manual test matrix for varied screenshot layouts,
  languages, raw cards, slabs, labels, and ambiguous prints.
- Verify navigation and rerun persistence across all five tabs.
- Verify a different upload starts fresh screenshot-specific state while a
  normal rerun does not.
- Verify one-crop success/failure, all-crop partial failure, retry messaging,
  fallback messaging, and preservation of previous identifications.
- Verify saved hunt, purchase gate, ledger edit/save, CSV export, and Excel
  export with disposable test data.
- Record observed detection misses and identification ambiguity categories
  without storing private screenshots in Git.

Exit criteria:

- The manual checklist is documented and has been completed on macOS/Linux; a
  Windows result is recorded when a Windows environment is available.
- No state-loss, identity-gate bypass, or user-data overwrite defect remains
  open for the tested flows.
- Any known limitations have a reproducible description and priority.

## Milestone 2: regression coverage and persistence hardening

Goal: reduce risk in the local workflow while preserving the current user
experience and file formats.

Candidate work, to be specified before implementation:

- Add tests around review filtering, ledger schema compatibility, inventory ID
  generation, append-only audit records, and hunt-save paths.
- Add representative synthetic-image tests for crop ordering, padding bounds,
  and overlap suppression where deterministic enough to be useful.
- Add headless Streamlit tests for upload-state initialization and critical
  gate behavior.
- Define compatibility expectations for future candidate and ledger columns.
- Evaluate atomic local writes and recovery behavior for interrupted saves.

Exit criteria:

- Critical identity and purchase gates have automated coverage at both helper
  and UI-orchestration levels.
- Existing user data remains readable, and migration/recovery behavior is
  documented before any persistence-format change.
- Unit tests remain offline and require no Gemini credentials.

## Milestone 3: identification quality improvements

Goal: improve exact-print review efficiency without weakening conservative
behavior.

Candidate work:

- Categorize false matches and low-confidence results using sanitized notes.
- Evaluate crop/context presentation and prompt/schema refinements against a
  controlled local test set.
- Make evidence and alternative matches easier to compare during manual review.
- Define explicit quality thresholds before changing auto-verification rules.
- Evaluate model changes only with compatibility, cost, latency, and failure
  behavior documented.

Exit criteria:

- Exact-print accuracy is measured separately from species accuracy.
- Ambiguous results continue to set `needs_review=true` and remain blocked.
- Provider or model changes preserve the structured contract and offline tests.

## Later discovery: market-research assistance

Automated market research is not part of v2 and has no committed implementation
milestone. Before any v3 work, discovery must define:

- permitted and reliable data sources;
- provenance and timestamp requirements for every comparable sale;
- region, currency, condition, grading, fees, and outlier rules;
- privacy, terms-of-service, rate-limit, and cost constraints;
- how uncertainty is presented and how manual judgment remains authoritative.

No market estimate or purchase recommendation should ship until those decisions
and validation criteria are accepted in [DECISIONS.md](DECISIONS.md).

## Cross-cutting release gates

Every milestone must preserve these invariants:

- User-owned `data/` content is never silently replaced or deleted.
- Manual operation works without an API key.
- Only explicitly AI-submitted crops leave the local machine.
- API keys never enter source control or audit records.
- One malformed or failed AI result cannot erase prior candidate/session state.
- Exact-card ambiguity cannot silently enter Active Ranking or the ledger.
