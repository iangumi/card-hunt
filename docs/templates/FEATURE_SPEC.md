# Feature: <name>

**Status:** Draft

**Owner:** <name or unassigned>

**Target milestone:** <roadmap milestone or unplanned>

## Problem

What user problem exists, and what evidence shows it matters?

## Outcome

Describe the user-visible result without prescribing implementation.

## In scope

- <capability>

## Out of scope

- <explicit exclusion>

## Requirements

1. <testable requirement>

## Trust, privacy, and data impact

- What stays local?
- What, if anything, crosses the network boundary and on which explicit action?
- Are candidate, hunt, ledger, crop, or audit schemas affected?
- How are existing user files preserved and recovered on failure?
- Could the change weaken the exact-ID or purchase gate?

## Failure behavior

Describe partial failures, retries, state preservation, recovery, and user
feedback. A failure involving one crop must not erase unrelated or previously
successful candidate state.

## Acceptance criteria

- [ ] <observable outcome>
- [ ] Manual mode works without an API key.
- [ ] Ambiguous identities remain blocked unless manually verified.
- [ ] Existing local data remains readable and is not overwritten.

## Verification plan

### Automated

- <offline unit or integration test>

### Manual

- <representative workflow check>

## Rollout and rollback

How can the change be introduced safely, disabled, or reverted without losing
user data?

## Documentation and decisions

- Documents to update: <README/product/architecture/roadmap/development>
- Decision entry required: <yes/no and why>

## Open questions

- <question>
