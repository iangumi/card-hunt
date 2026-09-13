# Product definition

## Product statement

Card Hunt Local helps a collector turn a store screenshot into a reviewed,
ranked purchase worksheet and a local acquisition record. It reduces repetitive
transcription while keeping exact-card identity, market judgment, and the final
purchase decision under human control.

The primary workflow is:

> store screenshot → local crops → optional AI identification → identity review
> → manual Hunt Score → active ranking → purchase ledger

## Intended user

The current product is a single-user, local desktop workflow for a collector
who evaluates Pokémon cards shown in store screenshots. It assumes the user can
verify ambiguous prints and perform their own market research.

## v2 capabilities

- Upload one screenshot and detect likely card rectangles locally.
- Create card crops plus padded context crops that may retain store labels.
- Add manual crops when automatic detection is insufficient.
- Optionally send a context crop to Gemini for exact-card and store-metadata
  extraction.
- Review confidence, visible evidence, possible matches, and ambiguity reasons.
- Correct fields and mark an exact identity as manually verified.
- Score value, demand, liquidity, scarcity, history, artwork, and condition on a
  0–10 scale, producing a weighted Hunt Score from 0–100.
- Gate Active Ranking by budget, request count, status, and exact-ID confidence.
- Save hunt worksheets and record approved purchases in a local ledger.
- Inspect recent audit events and export the ledger as CSV or Excel.

## Product principles

### Exact identity before ranking

A correct species with the wrong print, set, promo, edition, or variant is not a
successful identification. If several prints are plausible, the candidate is
marked for review and does not silently enter Active Ranking.

### Human verification is authoritative

AI output is an editable starting point. A user can correct fields and use the
`Verified` override after personally confirming a difficult identity. Purchases
that do not pass the identity gate remain blocked unless verified.

### Local by default

Detection, cropping, scoring, hunt files, the purchase ledger, and the manual
workflow remain local. Only a crop submitted through an AI Identify action is
sent to Gemini. An API key is not required for the manual workflow.

### Missing data is better than invented data

Card number, set, year, variant, grade, store price, and request count must be
derived from visible evidence. Unknown values remain missing or low-confidence;
the system must not manufacture certainty.

### Decision support, not market automation

v2 does not collect sold comparables, estimate market value, or recommend a
purchase. The collector researches markets externally and enters the Hunt Score
factors manually.

## Eligibility rules

A candidate enters Active Ranking only when all of these conditions hold:

- its store price is present and no greater than the configured maximum;
- its request count is zero;
- its status is not sold, owned, bought, passed, skipped, or equivalent;
- its exact identity is manually verified, or its exact-ID confidence meets the
  configured threshold and it is not marked `needs_review`.

The default confidence threshold in the UI is 0.80. Automatic verification is a
separate, stricter implementation rule: the exact-ID confidence must be at
least 0.96, a card number must be present, and no ambiguity may be reported.

## Current non-goals

- Automated market or sold-comparable research.
- Automated purchase recommendations or transactions.
- Cloud synchronization, shared accounts, or multi-user collaboration.
- A promise that local rectangle detection will find every card.
- Treating Gemini output as authoritative without review.
- Uploading an entire screenshot during AI identification.

## Success criteria

v2 is successful when a user can complete the workflow without losing state,
ambiguous identities cannot bypass the ranking/purchase gate accidentally,
failed AI calls do not erase prior results, and saved hunts and purchases remain
recoverable from local files.

Operational quality should be evaluated with:

- end-to-end completion rate for representative store screenshots;
- percentage of crops needing manual correction, separated by detection and
  exact identification;
- false-positive rate at the identity gate;
- absence of candidate-state loss across Streamlit reruns and AI failures;
- ledger and audit integrity after repeated sessions.

No telemetry for these measures is currently claimed; they are validation
criteria for manual testing and future instrumentation decisions.
