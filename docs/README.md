# Card Hunt Local documentation

This directory is the planning and technical reference for Card Hunt Local.
The root [README](../README.md) remains the quick-start guide.

## Start here

| Document | Purpose |
| --- | --- |
| [Product definition](PRODUCT.md) | Who the app serves, what v2 does, its safety boundaries, and how success is judged. |
| [Architecture](ARCHITECTURE.md) | Runtime components, data flow, state, persistence, AI boundary, and failure behavior. |
| [Roadmap](ROADMAP.md) | Current baseline and proposed milestones, with explicit exit criteria. |
| [Active v2.1 milestone](milestones/v2.1-workflow-hardening.md) | Implemented hardening baseline, remaining workflow scope, and completion criteria. |
| [Decision log](DECISIONS.md) | Durable technical and product decisions already embodied in the app. |
| [Development guide](DEVELOPMENT.md) | Setup, verification commands, change boundaries, review checklist, and Definition of Done. |

## Documentation rules

- Describe shipped behavior in the present tense and proposed work in the
  future or as a proposal.
- Treat `data/`, hunt CSVs, crops, the ledger, and audit logs as user-owned
  state. Never replace or delete them as part of application or documentation
  work.
- Never include `.env` contents, credentials, API keys, or copied audit data in
  documentation, tests, screenshots, or commits.
- Keep exact-card identification distinct from species recognition. Ambiguous
  variants must remain visible to the user and blocked by the confidence gate.
- Do not describe market research, sold-comparable collection, or purchasing
  recommendations as automated in v2.
- Update the product, architecture, roadmap, and decision log together when a
  change crosses their boundaries.

## Planning workflow

1. Start with the active milestone, [ROADMAP.md](ROADMAP.md), or an issue.
2. Define the user outcome, constraints, acceptance criteria, data impact, and
   manual-test requirements before implementation.
3. Add a decision entry when the change creates a durable constraint or
   meaningfully changes privacy, persistence, provider behavior, or ranking.
4. Update current-state documentation only after the behavior ships.

Use [the feature-spec template](templates/FEATURE_SPEC.md) for work that is too
large or risky for a short issue description.
