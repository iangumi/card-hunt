# Repository guidance

Before making changes, inspect the current working tree, including tracked
modifications and untracked non-ignored files. Preserve relevant local work.

If `.codegraph/` exists, use `codegraph explore` before grep/find or broad source
reading when locating or understanding code.

Read these before implementation:

- [Product](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisions](docs/DECISIONS.md)
- [Active v2.1 milestone](docs/milestones/v2.1-workflow-hardening.md)
- [Definition of Done](docs/DEVELOPMENT.md#definition-of-done)

Stay within the active milestone unless the user explicitly changes scope.
Preserve `data/`, ledger files, hunts, crops, audit logs, and all other user-owned
state. Never read, expose, or commit `.env`, credentials, tokens, API keys, or
local secret configuration. Avoid destructive Git operations, and never discard,
reset, clean, stash, overwrite, or delete local work without explicit approval.

Do not commit or push unless the user explicitly asks.
