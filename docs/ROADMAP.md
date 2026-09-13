# Product roadmap

This roadmap describes intended sequencing, not release dates. Current behavior
is documented in [PRODUCT.md](PRODUCT.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
Future milestones remain proposals until their scope is implemented and their
exit criteria are met.

| Status | Milestone |
| --- | --- |
| Completed | v1 Foundation |
| Completed | v2 AI Identification |
| Active | [v2.1 Workflow Hardening](milestones/v2.1-workflow-hardening.md) |
| Planned | v3 Market Snapshot foundation |
| Planned | v3.1 Automatic market evidence collection |
| Planned | v3.2 Market summarization/history |
| Planned | v3.3 Decision/scoring integration |
| Planned | v4 Hunt UX / analytics |
| Planned | v5 Portfolio lifecycle / repricing |
| Planned | v1.0 Stable |

## Completed: v1 Foundation

**Outcome:** Established the local screenshot-to-worksheet workflow, local crop
detection, manual scoring and ranking, saved hunts, purchase ledger, audit trail,
and local file persistence.

## Completed: v2 AI Identification

**Outcome:** Added opt-in Gemini identification with a structured exact-card
contract, padded context crops, confidence/manual-review gates, manual Verified
override, and audit visibility for AI-assisted results.

## Active: v2.1 Workflow Hardening

**Goal:** Make the existing hunt workflow resilient, recoverable, and efficient
enough for repeated real-world use.

**Major scope:** Complete transient-rate-limit handling, unresolved-only batch
identification, inline review actions, improved crop selection and preview,
session summaries, resumable hunts, duplicate purchase protection, persistent
workflow navigation, and aggregated API usage summaries. The detailed shipped
and remaining scope is in the
[v2.1 milestone spec](milestones/v2.1-workflow-hardening.md).

**Exit criteria:** The remaining v2.1 workflow features are implemented and
verified; reruns and per-crop failures preserve state; saved hunts can resume;
duplicate ledger additions are prevented; critical gates have offline automated
coverage; and the manual end-to-end release checklist passes without modifying
or losing existing user data.

## Planned: v3 Market Snapshot foundation

**Goal:** Add a trustworthy local structure for recording point-in-time market
evidence before automating its collection.

**Major scope:** Define snapshot and evidence schemas, source/provenance fields,
timestamps, currency and region, raw/slab and condition context, manual evidence
entry, and compatibility with existing candidates and ledger records.

**Exit criteria:** Users can create, inspect, edit, and retain a timestamped
market snapshot locally; every value has explicit source and context fields;
existing hunt and ledger data remains readable; and no automated collection or
valuation is implied.

## Planned: v3.1 Automatic market evidence collection

**Goal:** Collect relevant market evidence from approved sources while keeping
each observation traceable and reviewable.

**Major scope:** Source adapters, query construction from verified card identity,
rate-limit and transient-error handling, provenance capture, deduplication,
partial-failure behavior, caching, and explicit user controls for network use.

**Exit criteria:** Supported sources return timestamped, attributable evidence;
failed sources do not erase existing snapshots; collection respects documented
source and privacy constraints; and mocked tests require no live network calls.

## Planned: v3.2 Market summarization/history

**Goal:** Turn collected evidence into transparent summaries and a useful local
history without hiding uncertainty.

**Major scope:** Comparable normalization, filters for condition/grading/region,
outlier visibility, snapshot summaries, historical storage, trend views, and
clear separation between observed evidence and derived values.

**Exit criteria:** Users can trace every summary to its underlying evidence,
compare snapshots over time, see exclusions and uncertainty, and recover the
original observations without relying on a generated narrative.

## Planned: v3.3 Decision/scoring integration

**Goal:** Incorporate reviewed market evidence into hunt decisions while keeping
the collector in control.

**Major scope:** Evidence-aware scoring inputs, freshness indicators, deal-edge
calculations, confidence presentation, manual overrides, and auditability of the
values used for ranking.

**Exit criteria:** Ranking shows which evidence and user inputs drive each
result; stale, missing, or conflicting evidence is visible; manual decisions
remain authoritative; and exact-ID gates still apply before ranking or purchase.

## Planned: v4 Hunt UX / analytics

**Goal:** Make live hunts faster to operate and make past hunt outcomes easier
to understand.

**Major scope:** Streamlined navigation and review, richer filtering and
comparison, hunt-level summaries, funnel/outcome analytics, and useful views over
saved local history.

**Exit criteria:** Representative hunts require fewer review interactions;
analytics can be reproduced from local records; navigation and recovery work
across reruns; and usability improvements do not weaken identity or purchase
gates.

## Planned: v5 Portfolio lifecycle / repricing

**Goal:** Extend the ledger from acquisition tracking into a maintainable local
portfolio lifecycle.

**Major scope:** Inventory lifecycle states, portfolio roles, periodic market
snapshots, repricing workflows, realized/unrealized tracking, review queues, and
export-compatible history.

**Exit criteria:** A purchased card can be tracked through its lifecycle without
losing acquisition history; repricing retains source and timestamp context;
portfolio summaries reconcile to local records; and migrations preserve prior
ledger data.

## Planned: v1.0 Stable

**Goal:** Consolidate the validated product into a stable, documented release
with explicit compatibility expectations.

**Major scope:** Resolve release-blocking defects, stabilize supported local data
formats, complete migration and recovery documentation, establish repeatable
release checks, and align setup, product, architecture, and operational docs.

**Exit criteria:** Supported workflows pass automated and manual release checks;
upgrades preserve documented user data; install and recovery steps are verified
on supported platforms; known limitations are published; and the release is
tagged only after the Definition of Done is satisfied.

## Ongoing, non-blocking work

Exact-print identification quality, crop heuristics, prompt/schema refinements,
and model evaluation continue across milestones. Improvements must preserve the
conservative review gate and provider contract, but they are not prerequisites
for starting the market-research milestones.

## Cross-cutting invariants

- User-owned `data/` content is never silently replaced or deleted.
- Manual operation works without an API key.
- Only explicitly submitted crops leave the local machine.
- API keys never enter source control or audit records.
- One failed or malformed result cannot erase prior candidate/session state.
- Exact-card ambiguity cannot silently enter Active Ranking or the ledger.
