# Testing and managed results

## Select and run

Use a targeted selection while implementing. Use the default campaign at the plan's full
qualification boundary. If the operator scopes final validation to failures and affected tests,
retain the broad receipts and reconcile them with the scoped replacements.

```sh
uv run ci test --json -- python/corpus-structure/tests/test_cli.py
uv run ci test --json -- -k test_recipe_redacts_before_clipping
uv run ci test --json
```

Put `ci` options before `--` and pytest selectors after it. Quote a selector that contains
shell metacharacters or spaces. The ordinary managed pytest lane runs one explicit test id
serially and caps several distinct explicit ids at that many xdist workers. Paths, `-k`
selections and the full campaign use xdist auto parallelism; `--workers N` overrides sizing.
An id naming a class or a parametrized function without a parameter follows the same rule,
even when it selects several items. The lane retains repository collection policy.
A path or `-k` narrows to ordinary pytest.
The default campaign runs the applicable ordinary and exclusive fault lanes. Use
`ci test --lane fault` only for the owned fault selection. This lane is serial and owns its
selection. Coordinate it with other work using the shared cluster.

Ordinary selection excludes opt-in `provider_evidence` identities. Use
`uv run ci test --providers-only -- PATH` to select and require them; this is incompatible
with the exclusive fault lane. Explicit provider node IDs require this mode. Missing named
prerequisites are decided before fixtures, reported as `blocked` with every missing reason,
and cannot become optional passing evidence. An empty provider selection is `not_run`.
The evidence selection is retained through recollection, manual retries and coverage.

Use `uv run ci test collect --json -- PATH` for a managed, serial inventory without fixture
or test execution; `--providers-only` applies the same provider selection. Its action is
`test.collect`, with separate collection outcome and functional `execution_outcome=not_run`.
Read native-required flags, their count, groups and observed workers with
`uv run ci test scheduling RESULT_ID --limit 20 --json`. Collection receipts cannot establish
functional coverage or supply functional retries.

For a throwaway functional cohort, use `ci test --native-host private -- PATH`.
One PostgreSQL18 host serves the selected Python/SQL work and its workers. Shared is the
default; private mode refuses shared authentication, peer and durability claims. An unnarrowed
private selection requires `--lane ordinary`, since the fault lane keeps its shared host.
Retry and recollection retain private mode; each replacement host has a new observed incarnation
that coverage reports rather than treating it as the original server. Bootstrap/cancellation
logs remain with the managed result; uncertain child custody prevents host teardown.

## Recover, retry and reconcile

```sh
uv run ci test failures ORIGINAL_ID --lane ordinary
uv run ci test retry ORIGINAL_ID --lane ordinary --json
uv run ci test coverage ORIGINAL_ID RETRY_ID
uv run ci test coverage ORIGINAL_ID RETRY_ID --view unresolved --limit 20 --json
uv run ci test scheduling RESULT_ID --limit 20 --json
```

- Use `test failures` for failed or prerequisite-blocked nodes, their phases and lanes.
  Collection-time prerequisite skips retain every named reason in the same view; an actual
  teardown failure remains a separate failed event.
  A child failure before pytest starts has a separate bounded, redacted startup diagnostic;
  it does not invent a test node or pytest native traceback.
  Add `--native-traceback --diagnostic-chars 32768` for retained pytest file locations and native
  chain descriptions. Source listings, locals and captured streams are excluded; unsupported
  native-only representations remain explicitly unavailable/partial. This view cannot recover
  assertion detail pytest did not record.
  Use `results show` for outcome, custody, expiry, published roles, diagnostic availability
  and the next action. Use `results watch ID` for bounded progress on an active invocation.
  `results inspect ID --view observations --json` reads safe collected events; use
  `--view timeline` for their parent-journal order. Severity/stage/method selectors filter
  collected rows; they cannot recover events omitted at collection. Continue using the
  returned `--after` cursor. A task-attempt filter supplies `--provider-invocation`,
  `--task` and `--attempt` together. Native state and availability remain separate from
  provider-reported observations; follow the returned owner-specific actions.
- Check/recipe reports include a retained-output read hint. Use
  `ci results output ID --stream stdout --json` for the safe retained output, adding the
  exact `--step STEP` from the hint for a bundle. Select stderr independently. Continue with
  returned `--after`; its coordinate is retained safe Unicode codepoints, not native bytes.
  Collection truncation and native byte counts remain explicit. Reading never reruns the check.
- Use an exact retry for a settled result with eligible unresolved pytest identities.
  Selected blocked identities can be retried manually after their prerequisites become available;
  their original blocked receipt and evidence mode remain intact.
  The supervisor recollects the required selection before running those nodes. Each retry
  has a new managed ID. If no authoritative collection survived or the failure is outside
  node scope, follow the fresh-lane action instead.
- When custody is unsettled, follow the result's recovery guidance. `results recover ID`
  can settle an abandoned managed test invocation when its supervisor proves the child
  groups drained. A live or unproven owner remains protected. Resolve custody before
  starting a replacement that could conflict with it.
- Give `test coverage` the original required selection first. Inspect `missing_lanes`,
  `lane_selections`, unresolved nodes, source differences, execution-context differences
  and unknowns, and native evidence. Follow the report's action for the affected attempt.
  The original failure remains visible even when replacements cover every required node.
  A coverage report's successful delivery does not establish qualification by itself.
  Use the owning plan to judge applicability and record omitted or blocked obligations.
- Use `test scheduling` for collection affinity groups, their logical members and workers
  observed executing phases. Filter with `--group`, select `--lane`, and page with `--after`.
  Collection designations and observed execution remain separate; worker assignments are
  unavailable when they were not recorded. The same view reports acquired native heads,
  reuse/verification and deployment-key gaps, with explicit limits on head records.

## Retained schema diagnostics

`ci schema check --retain-diagnostics --json` preserves its operation outcome when optional
validation-document publication is unavailable. Read expected validation with
`ci schema diagnostic ID --view correction`; default JSON returns the original document.
Unexpected defects retain their original exception and use the separate safe exception journal:
`ci results inspect ID --view observations --json`. A validation-document refusal does not
establish that exception observations are absent. Respect the returned availability and bounds.

## Retrieve and retain

Default to managed storage and record IDs in the consuming plan or evidence. Use
`ci results list` if an ID is missing. `uv run ci results export ID --role ROLE --json`
returns the published path. Leave the destination unset for ordinary retrieval. Specify
`--destination` for deliberate delivery to a caller that needs a separate copy.

Unheld settled successes expire after one day. Failures and interruptions expire after one
week. Use `results hold ID` while a named consumer depends on an invocation and
`results release-hold ID` when the dependency ends. Use `results gc` to preview eligible
managed retirement and `results gc --apply` when cleanup is authorized. For durable evidence,
use `uv run ci evidence retain ID --role ROLE --for PLAN-ITEM --json` with the necessary
artifact role and its actual consumer. The evidence owner records and hashes the retained copy.

See the [testing rules](../../../../AGENTS.md#testing-rules) and
[managed results and testing plan](../../../../docs/plans/cli-operations/managed-results-and-testing.md).
