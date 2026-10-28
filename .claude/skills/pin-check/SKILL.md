---
name: pin-check
description: Add, bump, hold or release a dependency pin. Use when changing a dependency in a manifest or a hold in docs/pins.md.
---

# Pin check

Every declared dependency is pinned exactly; the lockfiles hold the rest (AGENTS.md, Dependencies).

- **Add or bump:** `uv add 'pkg==x.y.z'` (plus `--project <dir>` for a sub-project), or
  `cargo add pkg@=x.y.z` (a git dependency by its `rev`).
  Move a family together. Read the lock diff so that only what you meant moved, run the tests the
  move affects and name it in the commit.
  `just deps` checks that every registry
  dependency is exact and declared families resolve to one version.
  Documentation binaries are pinned in `docs/site.toml`; after a change run `just bootstrap-docs`
  and `just docs-test`.
- **Hold:** add a `docs/pins.md` row with the reason, when to revisit it and today's date.
  **Release:** delete the row.

Never re-resolve wholesale (`uv lock --upgrade`, bare `cargo update`) unless the operator asks.
