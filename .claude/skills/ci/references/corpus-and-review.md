# Corpus and review work

## Read and prepare the intended run

```sh
uv run ci status RUN_ID --project PROJECT --json
uv run ci tasks RUN_ID --project PROJECT --json
uv run ci eval operation-event-availability RUN_ID --project PROJECT --json
```

Use `ci status` without a run ID for the configured project's latest run. Pin the project
and run when interpreting evidence or performing an effect. Read the status's readiness
and supervisor state together. Intentional handoff at a retained source-ready cut can be
resumed. An orphan, terminal refusal or unassessed supervisor requires its own diagnosis.

Use `ci ingest` for source-only preparation on an existing bound project. Supply a project,
domain, corpus or source binding only when it selects the intended inputs. Ingest prepares
a cut under the existing release. Use `ci run resume RUN_ID --project PROJECT` to continue a
supported retained attempt. `ci regenerate` performs the broader regeneration workflow and
is appropriate when that is the requested operation.

Use the `source`, `records`, `contributions`, `structure`, `query` and `explain` groups
to inspect released structures and their evidence. Choose the particular subcommand from
group help. For fitting, read `operation-event-availability` first. Its outcome and next action
distinguish missing compatible events, an unavailable evaluation and an unfit population.
Use fitting or evaluation write routes only with their applicable inputs and authority.

## Export an exact retained selection

Prepare a selection JSON that names the completed source and requested evidence.
Use `--exact-closure` when the delivery must include only exact retained predecessors.
The command publishes the bundle under a managed ID. Supply an existing selection file or
pipe the selection JSON to `review export -`. Inspect the managed result directly by ID.
See the [selection model](../../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py).

```sh
uv run ci review export SELECTION.json --exact-closure --json
uv run ci review inspect --result RESULT_ID
uv run ci review verify BUNDLE_PATH --json
```

Use a detached bundle path when verifying an intentional handoff. If an
ordinary export was interrupted after binding its selection and source, inspect its
settlement and follow its next action. `uv run ci review retry RESULT_ID --json` replays
the same retained selection and source binding. If the export never acquired a binding,
submit the selection explicitly. Evaluated exports use a separate evaluator route and
authorization.

See the [corpus and operations plan](../../../../docs/plans/cli-operations/corpus-and-operations.md)
and the [managed results reference](testing-and-results.md).
