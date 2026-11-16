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

## Statistics application inputs

[`domains/statistics/operations.yaml`](../domains/statistics/operations.yaml) is the explicit
current application acquisition package for model change requests (`data_operations`, relative
to the workspace). Select the logical execution profile explicitly in the deployment request;
the application manifest contains no runtime selection or deployment authority.

The package captures the statistics/core/terminology schemas and named local terminology assets,
standard streaming PDF capture, organization, enrichment and integrated recognition, primary
provider profiles, construction/math, baseline M1 candidates, E5-small-v2/384 contextual encoding,
downstream products and protected reference/record-policy contracts. Qwen, external actor
protocols and visual interpretation are unselected. Provider availability does not establish
candidate quality, accepted readings or completed corpus coverage.

The checked-in profiles freeze local metadata acquired on 2026-11-16 through the existing native
preflight and asset readers, without model inference. They name the actual local PM2/GLiNER/E5
caches, qualified Docling asset bundle and isolated Nemotron interpreter/worker. Relocation or
runtime changes require reacquisition through those owners. The PDF recipe and prepared asset
manifest must remain paired. Integrated recognition additionally requires the actual managed
service generation and handoff described by the [recognition service](../services/nemotron-parse/README.md);
the configured endpoint and trusted-service requirement do not prove a running generation.
Deployment, runtime registration, source-demand bootstrap and actual provider qualification are
separate operations; merely preparing this package performs none of them.

[Inspect retained examples](examples/README.md) · [Reproduce the contextual experiment](examples/README.md#reproduce-the-contextual-example)
