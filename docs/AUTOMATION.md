# Automation policy

## Goal and authority

The automated milestone runner advances Card Hunt Local from the active
milestone through **v1.0 Stable**. Repository documentation is the source of
truth for scope, sequencing, acceptance, architecture, and safety constraints.

Before every run, read:

1. [`AGENTS.md`](../AGENTS.md)
2. [`ROADMAP.md`](ROADMAP.md)
3. the active milestone specification linked from the roadmap
4. the standard [Definition of Done](DEVELOPMENT.md#definition-of-done)

Consult [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
[DECISIONS.md](DECISIONS.md) wherever the slice touches their concerns.

If these sources disagree, preserve the working state and pause for human
direction. Automation must not resolve product or milestone conflicts by silently
expanding scope.

## Run discipline

Work on one coherent, reviewable slice at a time. A slice should have one clear
outcome, bounded files, testable acceptance criteria, and a useful handoff even
when later milestone work remains.

Before modifying files on every run:

- inspect `git status --short`, unstaged changes, staged changes, and untracked
  non-ignored files;
- preserve all relevant tracked and untracked local work;
- confirm the slice belongs to the active milestone;
- identify applicable automated and manual acceptance checks;
- confirm the current branch is a non-`main` automation/development branch.

If the current branch is `main`, detached, or ambiguous, pause before editing or
committing and request human direction. Automation must not broaden product
scope, skip work into a later milestone, or reorder milestones automatically.

At all times:

- preserve identity-confidence, manual-verification, purchase, privacy, and
  data-preservation gates;
- never read, print, copy, or commit secrets or local secret configuration;
- never modify, replace, migrate, or delete user-owned data; migration code must
  be developed and tested against synthetic or disposable copies, then paused
  for human approval before any real-data operation;
- treat `data/`, crops, hunts, ledger files, audit logs, and exports as user-owned;
- prefer recoverable changes and preserve the working state on failure.

## Permitted automated work

Within the active milestone and an approved run, automation may:

- edit application code and documentation;
- add or update offline tests;
- run `pytest`;
- run module import smoke checks;
- run `git diff --check`;
- perform other non-destructive, offline checks required by the active spec;
- update milestone and roadmap status only when the documented acceptance and
  exit criteria are actually satisfied;
- create a local commit after one coherent slice passes its applicable automated
  verification and no mandatory human pause remains for that slice.

Automated tests must not make live Gemini or market-provider calls and must not
require real credentials.

## Mandatory human pauses

Automation must pause and report before proceeding or claiming acceptance when:

- visual or interactive UI behavior needs human verification;
- a real Gemini or other API call is required;
- an external market-data source or provider would be introduced or changed;
- a persistence migration could affect existing user data;
- a destructive change is proposed;
- requirements, acceptance criteria, branch intent, or document authority are
  ambiguous;
- automated checks fail unexpectedly;
- a milestone requires manual acceptance before completion.

Automation may prepare a reviewable implementation before a visual/manual pause
when the requirements are otherwise clear, but it must not represent the slice
or milestone as accepted until the required human check is recorded.

## Git policy

- Use the current non-`main` automation/development branch.
- Do not switch to, commit on, push to, merge into, or rebase `main`.
- Never push or force-push any branch.
- Never delete branches.
- Never use destructive Git operations to discard or conceal local work.
- Create a local commit only after a coherent slice passes applicable automated
  verification and has no unresolved mandatory approval gate.
- Do not commit user data, secrets, generated crops, hunt files, ledger files,
  audit logs, exports, credentials, or local secret configuration.
- Keep unrelated pre-existing work out of the commit.

This local-commit permission applies only when the human has explicitly requested
an automated milestone run governed by this policy. Outside such a run,
`AGENTS.md` requires explicit permission before committing.

## Milestone advancement

Do not mark a milestone complete until every exit criterion is satisfied,
applicable automated checks pass, and required manual acceptance is recorded.

When a milestone is genuinely complete:

1. update its specification with the final status and evidence;
2. update `ROADMAP.md` to mark it completed;
3. activate the next milestone already listed in the roadmap;
4. use the next run to select a coherent slice from that newly active milestone.

Activating the next listed milestone is not permission to reorder milestones or
invent additional scope. Stop the automated program when the **v1.0 Stable** exit
criteria are satisfied.

## Failure behavior

On failure:

- preserve the working tree and all useful diagnostic state;
- report failing tests and checks exactly; do not hide, disable, or relabel them;
- distinguish an implementation defect from an environment or manual-approval
  blocker;
- do not repeatedly retry the same implementation without new evidence or a
  changed hypothesis;
- stop and report the blocker when human judgment, credentials, external access,
  destructive action, or ambiguous requirements are involved.

## Run report

Every run reports:

- completed work and files changed;
- automated verification results;
- active milestone progress and acceptance criteria affected;
- manual blockers, approvals, and checks still required;
- the next intended coherent slice;
- local commit information when a commit was permitted and created.
