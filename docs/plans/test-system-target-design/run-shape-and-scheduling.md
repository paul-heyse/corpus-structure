# Run shape and scheduling

**Status:** Accepted design companion; the [coordinator](../test-system-target-design_2026-11-13.md)
owns current implementation, findings and qualification state. **Created:** 2026-11-13.

**Present-state framing, 2026-11-13.** Non-gated functional scope has reached the coordinator's
integration boundary. The [assembled review](../../design_review/reviews/design_review_test-system-assembled_2026-11-13.md)
assesses that implemented architecture within its stated scope. The contracts and original
implementation instructions below retain the accepted design; dated source descriptions are
baseline evidence, not current implementation or qualification claims.

This companion owns the design of packages TS-04 and TS-12: the managed route sizes its workers
to an explicit selection of test ids, and designated expensive preparation is kept on one worker
per run through affinity groups. The
[coordinator](../test-system-target-design_2026-11-13.md) owns package state, finding
disposition and the rule decision RC02; nothing here restates them.

**Baseline and evidence.** Original source was read at `main` `683e9a955`; revision source was
inspected at `b1b4a4de0`, 2026-11-13, incorporating
[I05 and I06](../../plan_improvement_reviews/test-system-target-design_2026-11-13.md).
Line citations are as read. Design statements were **Proposed** at original authoring and
subsequently accepted through the coordinator. Baseline source facts are
**Interface-checked by source inspection, 2026-11-13**. Durations
quoted from the audit are **Measured** from stored results on a shared workstation and are
orders of magnitude. No package here has a speed target. Paths `tests/…` and `src/…` are
relative to `python/corpus-structure/`; root paths are written as root `tests/…`, `scripts/…`,
`conftest.py`, `pyproject.toml`. Section references are to the
[design review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md)
(§4.7, §6.1 for F02 and F05, §12 for RC02); option ids (W1, G1 and so on) are those of its
[supporting document](../../design_review/reviews/test-system-target-design/options-and-classification.md),
Part A.

## Original inspection baseline and reused mechanisms

**Worker count.** The managed route builds the pytest arguments in `_managed_pytest_args`
(`scripts/test_receipts.py:1555–1593`). For the ordinary lane it passes `-n <workers>` when
`--workers` was given and `-n auto` otherwise (`:1586–1593`); the fault lane passes `-n 0`
(`:1583–1585`). `--workers` travels from `ci test` as `CORPUS_CI_TEST_WORKERS`
(`src/corpus_structure/cli/testing.py:493–494`) through the `test-all` recipe (root
`justfile:23–25`). Plain pytest gets `-n auto` and `--dist=loadgroup` from root
`pyproject.toml:64–65`. A one-test run therefore starts one worker per core. Each worker imports
the package conftest, which imports the CLI application (`tests/conftest.py:37`), collects the
selection, and the run ends through xdist's gateway shutdown, whose exit timeout is ten seconds
(`.venv/…/xdist/workermanage.py:45`). The audit measured trivial two-worker runs at about six
seconds of wall time and a three-test run on sixteen workers at about fifteen (§6.1, F05).

**Affinity.** The root collection hook already assigns one group by fixture closure: an item
whose `fixturenames` intersect six math preparation fixtures is marked
`xdist_group("math_preparation")` (root `conftest.py:21–37`), and `--dist=loadgroup` keeps a
group on one worker. Everything else is scheduled per item, so a module- or session-scoped
fixture is built once on every worker that receives one of its consumers. Measured in one full
run (§6.1, F02): the statistics pack fixture behind `tests/orchestrate/test_policy.py:36–38`
spent 28–37 s on each of ten workers; `tests/semantic/test_interpretations.py` 25–34 s on eight;
root `tests/test_native_run_scope.py` 16–21 s on seven; the HanLP profile about 19 s on both
workers of a two-worker run.

**What is reused.** The built-in `loadgroup` scheduler and the root hook; no custom scheduler is
added. The receipt machinery already keeps identities stable under grouping (below). The
recorded worker facts already distinguish a serial run: `_worker_facts` reports an actual count
of zero when the session started with no workers (`scripts/test_receipts.py:824–830`).

## Target design and contracts

| Operation | Consumes | Decides | Produces |
|---|---|---|---|
| Worker sizing (TS-04) | The forwarded selectors, or a retry selection file, and `--workers` | Serial, capped, or `auto` | The `-n` and cap arguments, and the request recorded in the invocation |
| Affinity designation (TS-12) | The collected items' fixture closures and one designation table | At most one group per item | `xdist_group` marks before xdist reads them |

**What consumers stop doing.** A developer running one test through `ci` stops paying for
sixteen worker start-ups and a gateway shutdown. Workers stop rebuilding a designated
preparation that another worker already holds.

**Preserved guarantees.** Logical test identities in classification, retry and coverage are
unchanged. The fault lane stays serial and owns its selection. An explicit `--workers` is
honored exactly. The managed Hypothesis profile is the same for focused and full runs. Path and
keyword selections keep today's parallelism.

**Intentional behavior changes.** A managed run of one explicit id runs in the controller
process with no workers; a managed run of *k* explicit ids starts at most *k*. Tests in a
designated group run on one worker in collection order.

## Pivotal library mechanisms

| Mechanism | Condition the design relies on | Reference |
|---|---|---|
| `-n 0` | No workers and no gateway shutdown; distribution is disabled (`.venv/…/xdist/plugin.py:326–328`) | §7, "Worker sizing" |
| `--maxprocesses N` with `-n auto` | xdist takes the smaller of the resolved `auto` count and `N` (`.venv/…/xdist/plugin.py:84–91,318–324`), so the route does not re-derive the core count | Installed xdist 3.8.0, read 2026-11-13 |
| Worker count is fixed before collection | `pytest_xdist_auto_num_workers` runs in `pytest_cmdline_main` and sees only arguments (`plugin.py:304–316`); the count cannot follow the collected selection | §7, "Worker sizing" |
| `xdist_group` under `--dist=loadgroup` | Marks are read after `pytest_collection_modifyitems`; two marks on one item are sorted and joined into a new combined group, and the group is appended to the node id as `@group` (`.venv/…/xdist/remote.py:254`) | §7, "Affinity groups" |
| Hypothesis `derandomize=True` | Examples are derived from the test's source, so every run of an unchanged test explores the same examples | Profile at `tests/conftest.py:65–69` |

## TS-04 — Workers sized to explicit selections

**Required input.** None. RC02 is accepted.

**Implementation vision.** The change is in `_managed_pytest_args`. When the lane is ordinary
and `--workers` was not given, it looks at the selection it is about to forward:

- **Explicit test ids.** A selector is an explicit id when it contains `::`. This is the test
  the function already applies to retry selections (`:1579`), and `_forwardable_selector`
  (`:1527–1534`) has already established that the part before `::` resolves inside one of the
  two test trees. A retry selection file is a list of canonical ids and is sized the same way.
- **Everything else.** A path to a file or directory, or any `-k` expression, is not an
  explicit id. If the selection contains one, or contains no selector at all, the run keeps
  `-n auto`. A file can hold many independent tests, and the count is fixed before collection.

| Selection | Arguments | Recorded request |
|---|---|---|
| `--workers N` | `-n N` (as today) | `N` |
| Exactly one explicit id, nothing else | `-n 0` | `0` |
| *k* distinct explicit ids, nothing else | `-n auto --maxprocesses k`, which is `min(auto, k)` | `auto` with the cap *k* |
| Any path or `-k`, or no selector | `-n auto` (as today) | `auto` |

*k* is an upper bound on useful workers because each ungrouped test is its own unit of work
under `loadgroup`. The function returns the sized request alongside the arguments, and the
invocation record (`scripts/test_receipts.py:1712–1719`) stores that instead of
`args.workers or "auto"`. The manifest scope that `ci test` writes before the lane runs
(`src/corpus_structure/cli/testing.py:597–603`) is already replaced by the supervisor's report
at `:516`; it only needs to stop asserting `auto` for a request the supervisor will size. The
`ci test retry` path records its request the same way (`:1072–1077`).

**A limit to state, not to solve.** An id that names a class, or a parametrized function
without its parameter, selects several items. With one such id they run serially; with *k* they
share at most *k* workers. That matches the accepted rule. A developer who wants parallelism
for such a selection passes `--workers`.

**Plain pytest.** Root `pyproject.toml:64` keeps `-n auto` as the default for plain `pytest`,
and a developer who runs one test without `ci` passes `-n 0` after it; the later option wins.
Sizing is not added to plain pytest, because the managed route is the supported one, it is the
only one that records a request, and a second owner of the worker count in a conftest hook
would have to agree with it. The comment beside the `addopts` entry notes that the managed
route sizes explicit ids.

**Text that changes.** `.claude/skills/ci/references/testing-and-results.md:16` says "The
ordinary managed pytest lane supplies xdist auto parallelism". It becomes a statement of the
table above: one explicit id runs serially, several ids run with at most that many workers,
path and `-k` selections and the full campaign use `auto`, and `--workers` overrides. The help
text of the option (`src/corpus_structure/cli/testing.py:33`, "default: auto") is adjusted to
match. The completed parallel-execution companion (`:113`, "Retain auto as initial default") is
history and is not edited.

**Controls.** Root `tests/scripts/test_test_receipts.py:1448–1500` already exercises
`_managed_pytest_args`, including a parametrized check that no `--workers` yields `auto`
(`:1475`). That case is split by selection: one id yields `-n 0`; three ids yield `auto` capped
at three; an id mixed with a path, a lone path, a `-k` expression and an empty selection yield
`auto`; `--workers 3` with one id yields `-n 3`; a one-line retry file yields `-n 0`. The CLI
evidence control that builds worker facts from `workers or "auto"`
(`tests/test_cli_test_evidence.py:143`) follows the recorded request.

**Successful example.**
`uv run ci test --json -- python/corpus-structure/tests/test_db_fixtures.py::test_server_url_follows_the_settings_default`
records a requested count of zero and an actual count of zero, and one event file written by
the controller. The same file given as a path records `auto`.

**Revealing failure case.** Two ids whose items carry one affinity group are a single unit of
work, so the second worker starts and receives nothing. The cap is an upper bound, not a
promise of use, and nothing is wrong.

**Acceptance and closure.** A one-test managed run records zero workers; a *k*-id run records
at most *k* created; a path or `-k` selection and the full campaign are unchanged; the `ci`
skill reference states the rule.

**Targeted verification.** `uv run ci test -- tests/scripts/test_test_receipts.py
python/corpus-structure/tests/test_cli_test_evidence.py`, then the successful example above as
the functional check.

**Original implementation premise (current disposition: coordinator).** That `-n 0` in the ordinary lane leaves receipt classification unchanged. The
fault lane already runs with `-n 0` through the same supervisor, and the successful example
settles it for the ordinary lane.

## TS-12 — Affinity groups for designated preparation

**Required input.** None for the initial table: existing local fixtures use consumer-module
qualifiers, so the package does not wait for any fixture to move. The shared-statistics designation changes together with TS-06's fixture
merge; each TS-10 family supplies its distinctive fixture before its designation is added.

**Implementation vision.** The root hook (root `conftest.py:21–37`) reads one designation table
beside the existing math list. Each row names a fixture, an optional **consumer-module**
qualifier, and a group. For each collected item, the hook matches fixture names in its
`fixturenames` and, when a qualifier is present, compares it with the item's collected module
identity. The qualifier never names a support module merely because a fixture was defined
there. Shared fixtures use distinctive names without qualifiers; genuinely local generic names
use consumer-module qualifiers. The hook then deduplicates all matching rows by group value
before assigning the one `xdist_group` mark.

*One group per item.* xdist would silently join two marks into a third group, which keeps
neither preparation on one worker. The hook therefore assigns at most one group, and raises a
`pytest.UsageError` at collection when an item resolves to two distinct group values. Existing
explicit marks participate in the same group-value set: repeated occurrences of the same value
collapse to one mark; distinct values refuse. Two rows such as `prepared` and its dependent
`policy` can legitimately match the same item and the same group. A conflict is settled where
the designation or explicit mark is authored, before xdist can join group names.

*Consumer-module qualification (I05).* The designated fixtures have generic module-local names today:
`stats`, `prepared`, `inputs`, `policy`, `profile`, `source_release`. Module-level functions with those six
names are defined 57 times across the two test trees, so a bare name would capture unrelated
modules. Each row for a genuinely local fixture therefore carries the consumer module where
that fixture is resolved. These explicit designations do not need pytest-internal inspection
of fixture-definition ownership. Merging the four statistics-pack fixtures into one
support-owned fixture is an explicit item of [TS-06](scenario-and-support-ownership.md). In that
same change, those local rows become an unqualified row for the distinctive shared fixture,
such as `statistics_pack_prepared`; an optional shared policy fixture has its own distinctive
name mapped to the same group. Its consumer closure receives the group wherever the fixture
is imported. A row qualified by the support module would match no such consumer and is excluded
from the target design.

*Group by preparation value.* Rows that prepare the same value share a group, so the consumers
in different modules land on one worker. With today's four separate module fixtures, one group
confines the four builds to one worker and removes the per-worker repetition; once TS-06's
merged fixture exists, the value is built once there.

**The designation list.** The criterion is *cheap bodies only*: a preparation is designated
when its consumers' own test bodies are cheap, so that running them on one worker costs little
beyond the preparation. A module whose bodies are expensive is not designated, because grouping
would serialize real work.

| Preparation | Fixtures at the inspection baseline | Group |
|---|---|---|
| Statistics pack, prepared | Before TS-06: consumer-qualified `stats` in `tests/orchestrate/test_policy.py:36–38`; `prepared` in `tests/semantic/test_interpretations.py:22–24`; `prepared` and `policy` in `tests/schema/test_rules.py:25–32`; `inputs` and `policy` in `tests/semantic/test_rule_literal_bindings.py:16–23`. After TS-06: distinctive shared preparation/policy names without qualifiers | one group for all four modules; duplicate matches for this value collapse |
| HanLP profile | `profile` in `tests/semantic/test_hanlp_products.py:29–43` | its own group |
| Trusted execution-model compile | `source_release` in root `tests/test_native_run_scope.py:35–42` | its own group |

Each row is confirmed against the criterion when it is added, by reading the module's bodies;
the review's measurements show the preparation dominating in the first three statistics-pack
modules and in the run-scope module. `configs` in `tests/orchestrate/test_policy.py:41–43` is in
the same module and rides with its group. The math preparation list is expressed as rows of the
same table, so there is one mechanism.

**Family groups: the contract TS-10 consumes.** A rollback-class family is one work unit: its
cases are cheap once the family clone exists, and without a group every worker that received
one case would build the seed and the family clone. The contract is:

- TS-10 defines one named fixture per family, with a name that is unique across both test
  trees. The fixture calls `scenario_seeds.rollback_family(recipe)`, and the family's cases
  request it, so it appears in their `fixturenames`. A call of `rollback_family` in a test body
  would be invisible to the hook, and the seed rule forbids it in any case.
- When TS-10 migrates a family, it adds one row to the designation table, naming that fixture
  and a group named for the family.
- A family case resolves to no other distinct designated group; the collection error above
  enforces it. Several fixtures designating the family's same group remain valid.

Commit-class consumers of a recipe seed are not grouped. Grouping them would remove per-worker
seed builds in a full run but would put a focused module's real bodies on one worker; the
coordinator's candidates table carries the trigger for revisiting this with receipts.

**Group suffixes do not change receipt identities** (confirmed in source and in one stored
result). The qualification plugin stashes each item's node id before xdist appends the group
(`scripts/qualification_plugin.py:29–34`) and emits a map from scheduled to logical ids, with
the affinity groups, at collection finish (`:103–128`); it refuses an ambiguous or duplicate
identity (`:108–109`). `classify_receipt` (`scripts/test_receipts.py:612`) rewrites every node
id, selection and native-required entry through that map. Retry writes logical ids to its
selection file, and coverage reads the classified result. Adding, renaming or removing a group
is therefore safe for `ci test retry` and `ci test coverage`; the suffix appears only in the
raw report log and JUnit file. Under `-n 0` there is no suffix at all.

**Controls.** Root `tests/scripts/test_parallel_harness.py` already runs child suites with
shared, composite and fixture-dependent groups and checks the recorded affinity
(`:83–101,270–339`). Extend those controls over a child copy of the hook: an imported distinctive
shared fixture receives its group in a different consumer module; a generic local fixture
matches only its consumer-qualified row; an unrelated same-name fixture stays ungrouped; two
closure matches for the same group yield one mark; and distinct group values fail collection
with the usage error. Retain logical receipt/retry identity checks across grouped and serial
execution. No control asserts a duration.

**Successful example.** In a full run's receipts, every item of the four statistics-pack
modules carries the one group and ran on one worker; the same holds for the HanLP and
run-scope groups.

**Revealing failure case.** A later test added to `tests/orchestrate/test_policy.py` with an
expensive body would be serialized behind the group. The criterion is rechecked when a
designated module gains tests of a different character, and the row is narrowed or dropped.

**Acceptance and closure.** Receipts' affinity groups show each designated preparation on one
worker per run; no item carries two distinct groups; repeated matches for one group succeed;
imported shared support is designated correctly and unrelated local fixtures stay outside it;
logical identities and retry selections are unchanged. TS-06's statistics merge updates the
fixture names, importers and designation together.

**Targeted verification.** `uv run ci test -- tests/scripts/test_parallel_harness.py`, then
`uv run ci test -- python/corpus-structure/tests/orchestrate/test_policy.py
python/corpus-structure/tests/semantic/test_interpretations.py
python/corpus-structure/tests/schema/test_rules.py
python/corpus-structure/tests/semantic/test_rule_literal_bindings.py` and a reading of the
recorded groups and executing workers.

**Original inspection premise.** That the four statistics-pack fixtures prepare the same value. They call
`prepare_packs` on the same directory (`src/corpus_structure/semantic/regeneration.py:412–418`)
and take its last element, so it holds by reading. TS-06's merge of the four into one fixture
settles it by construction. Current integration and evidence are owned by the coordinator.

## Native runner capacity integration

**Accepted TS-24/25 interaction.** [PostgreSQL tooling](postgresql-tooling.md) owns SQL/TAP
cohort execution and optional `pg_virtualenv` cluster lifetime. Its `pg_prove` job count consumes
the same managed run capacity decision as pytest worker sizing; it is not a second automatic
pool owner. The ordinary pytest lane retains TS-04's sizing above. Under TS-24's selected batch
contract, outer pytest scheduling owns concurrency and each `pg_prove` invocation initially uses
one job. File-level jobs can increase only through that same capacity owner and only for files
with independent state; independently auto-sized nested pools are excluded. Batch selection
passes the exact selected logical case mapping, and each pytest item consumes its own native
case result rather than rerunning a complete suite. TS-12's existing fixture/group rule can
confine a shared family batch when its cheap consumers use a distinctive family fixture.
`pg_virtualenv` wraps the cohort's owned cluster lifetime and adds no scheduler. Native receipts
retain logical test identities and report their actual runner/job and item-bound acquired
context through the evidence contract.

This is coordination of the existing runner boundaries, not a bespoke scheduler. TS-24 owns the
cohort/result contract and capacity integration; TS-25 must consume it before introducing an
ephemeral-cluster route. Required provider/native scope remains owned by the coordinator and
[evidence contracts](evidence-contracts.md).

## Decisions that are not packages

**Hypothesis.** The managed route keeps the `ci` profile for focused and full runs: 300
derandomized examples, no example database (`tests/conftest.py:65–69`; set by the supervisor at
`scripts/test_receipts.py:334`). A focused run and a qualification run then explore the same
examples, so a focused pass means the same thing. The one property that dominated a stored run
(`test_generated_layer`, 198 s, about 0.66 s per example) is slow because every example
re-reads the implementation inputs, by source reading; that is removed by TS-03 in the
[snapshot companion](implementation-snapshot-and-timing.md). The example count is not the
lever, and a smaller focused profile stays rejected.

**Dependency-based selection.** Rejected. A test's result here depends on SQL files, YAML
models, frozen migration artifacts and about a hundred implementation files that are hashed
into runtime fingerprints. A Python coverage map, which is what `pytest-testmon` records, sees
none of them, so an incomplete dependency key would silently skip affected tests (the review's
gate G6). Selection stays a developer's judgment. The managed route already admits `-k`
(`scripts/test_receipts.py:1536–1552`), so `-k data_operation` selects the declared data
operations (DDO) modules by name.

**Scheduled collection correction.** W2 lazy CLI activation is part of
[TS-06](scenario-and-support-ownership.md#ts-06--support-modules-import-rules-and-recipe-values),
alongside early TS-04 work: both `cli.app` and `cli.output` imports move into `Cli.__call__`
because either submodule otherwise executes the package's eager command-registry import.
Cold non-CLI collection and existing CLI consumers establish that boundary without a timing
threshold. This removes the established unconditional path; other imports may still activate
the CLI.

**Low-priority candidates.** Argument screening without a second interpreter (W3; the screening call is `_validate`,
`src/corpus_structure/cli/testing.py:447–465`), deferred collection-time loads (C1), the
controlled PDF builder loaded once per process (S3), concurrent cold-process children (P1) and
long single tests dispatched first (G3) are not scheduled. Their triggers, and their state, are
in the coordinator's
[candidates table](../test-system-target-design_2026-11-13.md#candidates-rejected-options-and-open-premises).
TS-04 makes the remaining fixed overhead easier to inspect: once a one-test run has no workers,
its remaining work can be assessed after the reused-head path in the
[lifecycle companion](native-lifecycle-and-deployment.md) and TS-06's lazy CLI imports are in
place. No timing experiment is required before implementing that scheduled correction; the
remaining candidates keep their own custody and uncertainty conditions.

## Outside this companion

The merge of the statistics-pack fixtures into one support owner is an item of TS-06 in the
[scenario and support ownership companion](scenario-and-support-ownership.md). The rollback
families that consume the family-group contract are in the
[isolation companion](isolation-and-seeds.md).
