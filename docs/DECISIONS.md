# Decision log

This file records durable decisions already reflected in the current
implementation. Add a new numbered entry when a change affects product scope,
privacy, trust boundaries, persistence, provider behavior, or ranking rules.
Do not rewrite an accepted entry to hide history; mark it superseded and link to
the replacement.

## D-001 — Keep the workflow local-first

**Status:** Accepted; documenting current behavior.

**Decision:** Detection, cropping, scoring, hunt files, ledger operations, and
manual review run locally. Network access is optional and occurs only when the
user invokes AI Identify for a crop.

**Consequences:** The manual workflow remains useful without credentials.
Documentation and UI must clearly disclose when crop data crosses the local
boundary. Cloud sync and collaboration are outside the current architecture.

## D-002 — Gate on exact print identity, not species recognition

**Status:** Accepted; documenting current behavior.

**Decision:** Exact number, set/promo, edition, and variant matter more than
recognizing the Pokémon. Multiple plausible prints set `needs_review=true`.
Ranking and purchase eligibility require either a non-ambiguous result above the
configured threshold or a manual `Verified` override.

**Consequences:** The system prefers missing data and review work over false
certainty. The user remains responsible for difficult variant verification.

## D-003 — Keep market research manual in v2

**Status:** Accepted; documenting current behavior.

**Decision:** AI identification extracts visible card and store metadata only.
It does not estimate market value, collect sold comparables, or recommend a
purchase. Hunt Score inputs remain user-entered.

**Consequences:** v2 avoids presenting unsupported market certainty. Any future
research feature needs a separate source/provenance design and acceptance
decision.

## D-004 — Use schema-constrained Gemini identification

**Status:** Accepted; documenting current behavior.

**Decision:** The runtime AI provider is Google Gemini through `google-genai`
(`from google import genai`). The request uses `client.models.generate_content`
with an image part, conservative system instruction, `application/json`, and a
JSON schema matching the candidate identification contract.

**Consequences:** Provider output is normalized into a provider-independent
dictionary before it reaches candidate logic. Model changes must preserve the
same contract and conservative prompt semantics.

## D-005 — Retry only transient Gemini unavailability

**Status:** Accepted; documenting current behavior.

**Decision:** Retry only `503` / `UNAVAILABLE`, with four primary attempts and
backoff plus jitter. After primary exhaustion, try the configurable fallback
once. Do not retry invalid requests, auth/permission errors, schema errors, or
programming errors.

**Consequences:** Temporary demand spikes are handled without multiplying bad
requests. Retry/fallback events are auditable, and failures stay isolated to the
affected crop.

## D-006 — Separate upload identity from hunt-session identity

**Status:** Accepted; documenting current behavior.

**Decision:** Compare deterministic file fingerprints across Streamlit reruns.
Create a timestamped hunt session ID and reset screenshot-specific state only
when uploaded bytes change.

**Consequences:** AI buttons and navigation may rerun Streamlit without erasing
the current intake. Re-selecting content after a distinct upload may create a
new active hunt; the fingerprint is not a global hunt registry.

## D-007 — Use inspectable local persistence

**Status:** Accepted; documenting current behavior.

**Decision:** Persist hunt snapshots and the ledger as CSV, record audit events
as JSONL, and store crops as image files under `data/`. Treat that directory as
user-owned and Git-ignored.

**Consequences:** Users can inspect and back up their records without a
database. The format does not currently provide transactions, concurrency
control, or automatic schema migration, so future changes must prioritize
compatibility and recovery.

## Entry template

```markdown
## D-NNN — Short decision title

**Status:** Proposed | Accepted | Superseded by D-NNN

**Context:** What constraint or problem requires a decision?

**Decision:** What are we choosing?

**Consequences:** What becomes easier, harder, required, or explicitly out of
scope?
```
