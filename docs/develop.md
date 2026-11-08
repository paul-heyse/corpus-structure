# Develop locally

Use `bash scripts/setup-env` to prepare a checkout from its committed
lockfiles. Run `uv run ci doctor` to check the installed tools.

- Read [contributor instructions](../AGENTS.md) for local conventions.
- Use the [current code trace](design/README.md#trace-a-result-through-the-code)
  to locate the component you want to change.
- Follow the [ci command routes](../.claude/skills/ci/SKILL.md) for focused checks
  and the [shared roles](../.agents/roles/README.md) for coordinated work.
- For documentation, use `just bootstrap-docs` and `just docs-serve`.
  [Publishing operations](publishing.md)

[Inspect retained examples](examples/README.md) · [Reproduce the contextual experiment](examples/README.md#reproduce-the-contextual-example)
