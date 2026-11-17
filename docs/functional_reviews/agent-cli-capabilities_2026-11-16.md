# The `ci` CLI as an agent's working tool — functional-extension review

**Date:** 2026-11-16 · **Status:** all recommendations `Proposed`; nothing here is accepted scope.

## Scope

The operator asked how the Typer-based `ci` command could be deepened, made easier to use and
extended so that coding agents scope and make changes to this codebase and its model more
effectively. Supplied hypotheses: Typer and Rich are the key libraries; test-result creation,
storage and retrieval might benefit from a more structured but light approach, possibly `sqlite3`;
the introspection libraries (ast-grep-py, LibCST, Astroid, ty, Griffe) and NetworkX might enable
useful commands. Two later directions shaped the inquiry: ground it in first principles and in the
reviewer's own experience as a user, with Codex logs from the last three days as supporting data;
and propose nothing that looks back over past runs (flaky tests, per-test history, trends), because
the codebase is changing too fast for history to mean anything.

The review follows the agent's loop — orient, scope, edit, verify, read results — and each
opportunity states whether its support is observed or reasoned.

## Baseline and evidence

Source baseline: `main` at `99edcaec2` plus concurrent uncommitted DDO work, inspected 2026-11-16.
Python 3.14.10, Typer 0.28.0, Rich 15.0.0.

Five sources, kept separate so they could check one another:

1. **Hands-on use** of the installed CLI by the reviewer (read-only commands), written down before
   the other evidence arrived.
2. **Codex session logs, 14–16 November**: 88 sessions, 26,159 shell commands, extracted to
   [aggregated tables](../design_review/evidence/2026-11-16_cli-agent-usage/README.md). Counts
   below are counts from this window. One root session supplies 27% of commands; classification is
   by regular expression and by the first statement of compound commands.
3. **Library research** against the repository overviews and the installed sources, with small
   read-only probes. Timings are single runs on this machine and indicative only.
4. **An independent design-reviewer assessment** of result storage, reached without the
   coordinator's conclusions.
5. **An independent challenge of the draft** by a second design reviewer, who checked its claims
   against code, the CLI and the raw logs. It corrected several facts and changed O03, O04, O05,
   O06 and O07; where it differs from the first assessment, this review says so.

### What the CLI is today

`python/corpus-structure/src/corpus_structure/cli/`: 36 modules, about 14,600 lines, 131 leaf
commands in 25 groups, composed eagerly through `REGISTRY` (`cli/__init__.py:30`). Output goes
through `emit()` (`cli/output.py:152`): `--json` writes the Pydantic model; otherwise a
per-command Rich rendering. `--json` is a per-command option; `--view`, `--limit`, `--after` and
`--max-bytes` exist on some commands. Managed results live one directory per invocation under
`build/ci/` (`ResultStore`, `cli/managed.py:476`), governed by
[ADR-0069](../adr/0069-cli-operations-custody.md).

Three earlier reviews built this surface:
[typer-cli-target](typer-cli-target_2026-11-07.md), [cli-reporting](cli-reporting_2026-11-07.md)
and [cli-and-logging](cli-and-logging_2026-11-10.md). Their plans are implemented, and no active
plan schedules anything proposed below. Three of their recommendations were not realized by those
plans and reappear here with usage evidence they did not have: a flat layout for pipes
([cli-reporting O01](cli-reporting_2026-11-07.md#O01), here O01), scheduled collection of expired
results ([typer-cli-target O03](typer-cli-target_2026-11-07.md#O03), here O04) and help grouping
([typer-cli-target O05](typer-cli-target_2026-11-07.md#O05), here O09). The rest is new: finding a
result without its ID, holds that name their consumer, verification scoped to a change, and
questions about the repository's own source. The first review deferred codemods until a recurring
hand-written transformation was observed; O08 reports on that condition.

### What agents do with it (observed, 14–16 November)

| Activity | Commands | Share |
|---|---|---|
| Reading files (`sed`, `cat`, `nl`, `head`) | 8,469 | 32% |
| Searching (`rg`, `grep`) | 5,721 | 22% |
| `git` | 3,418 | 13% |
| Inline Python | 3,365 | 13% |
| `ci` | 3,152 | 12% |

- The CLI has displaced direct tools for running things: 9 direct `pytest` calls against 758
  `ci test` launches. It is used hardest for tests and results: `test failures` 822, `test` 758,
  `results hold` 439, `model change` 332, `results show` 280, `check --only types` 189,
  `test retry` 167.
- Agents prefer the machine form and then reduce it themselves. 770 of 822 `test failures` calls
  pass `--json`. 255 commands pipe a `ci … --json` call into an inline Python one-liner:
  `results output` 57, `model change` 47, `test failures` 46, `results hold` 40, `results show`
  21. A further 139 commands read files under `build/ci/<id>/` directly.
- Reading and searching source is more than half of everything agents run. 766 searches are
  followed within six commands by two or more windowed reads of their own hits; 4,985 search
  patterns are alternations of four or more names; 149 inline scripts walk source with `ast` or
  `inspect` because a search could not answer the question.
- Agents choose tests by hand: 737 of 758 launches name paths.
- Usage errors are uncommon but real. The raw logs contain "No such option" for `--reason`,
  `--max-chars`, `--node`, `--view`, `--tail`, `--collect` and `--limit`, and "No such command"
  for `result`, `corpus` and `inspect`. `--help` was called 171 times; the generated reference
  (`ci docs commands`) five times.
- Parallel executors work in sibling worktrees: 13,835 commands reference another worktree's path.
- The older scratch-capture habit has gone: five capture-then-reread sequences in the window, and
  none of the 1,112 `build/*.log` files is newer than 11 November.

### What the reviewer found using it (observed, 2026-11-16)

- A call costs between about 1.2 and 2.5 s before it does anything, depending on load.
- `ci test failures ID` for a run with eight failures prints 7,912 bytes as text and 3,925 bytes as
  JSON. The text table is fitted to 80 columns, so each test ID is broken across five to nine
  lines and cannot be copied into `ci test -- NODE`. All eight failures had the same one-line
  cause, listed eight times. The raise location is absent unless `--native-traceback` is added,
  which returns 7,516 bytes for one failure.
- `ci results list` returns results in ID order. IDs are random, so the order is arbitrary in
  time; the only filter is `--action`. The reviewer had to scan the manifests with a script to
  find the most recent failed test run.
- `build/ci` holds 6,236 results in 24 GB and gains about 1,000 a day.
- Nothing answers "who uses this, who calls it, what imports it" for working-tree code.
  `ci model source navigate | impact | …` serve captured declared-operation sources through an
  input file, not the tree being edited.

## Recommended target

| | Opportunity | Support | Priority |
|---|---|---|---|
| [O01](#O01) | Output written for a pipe, on the most-used reads | Observed | First |
| [O02](#O02) | Failures read as cause, location, detail — in the test run's own report | Observed | First |
| [O03](#O03) | Find a result by what the agent knows | Observed | First |
| [O04](#O04) | Holds that name their consumer, and expiry that happens | Observed | First |
| [O05](#O05) | One per-result table; results that know their source; a two-run delta | Reasoned, part observed | Second |
| [O06](#O06) | Diagnostics partitioned by the change | Part observed | First |
| [O07](#O07) | Questions about the working tree's own code | Observed need, reasoned design | Second |
| [O08](#O08) | Previewed mechanical change | Weak | Conditional |
| [O09](#O09) | Leaner start and help | Observed, small | With O01; before O07 |
| [O10](#O10) | Worktree support, checkout identity and search hygiene | Observed | First |
| [O11](#O11) | Model-change and recipe-output reads | Observed need, not yet examined | Next inquiry |

On the operator's hypotheses. Typer and Rich supply O01 and O09 without new machinery. The
introspection libraries and NetworkX support O07, though the strongest mechanisms turned out to be
the `ty` language server and `ruff analyze graph`; Griffe and ast-grep have narrow roles, and
Astroid and LibCST metadata almost none. A SQLite store across runs is not recommended while
history is out of scope; a structured per-result table is, and SQLite is one acceptable format for
it. The reasoning is under [O05](#O05).

<a id="O01"></a>
### O01 · Output written for a pipe, on the most-used reads

**Who and what.** Agents reading test failures, result status and listings, and check outcomes.
Today the default report is laid out for an 80-column terminal; agents respond by adding `--json`
and reducing it in Python. Afterwards, a piped call to these commands returns a dense,
line-oriented report by default: one record per line, identifiers never wrapped or shortened, no
borders or padding, an explicit "N more: `<next command>`" line when bounded. `--json` stays the
typed form for programs.

For the eight-failure run above, the default would be something like:

```
result ef52a7c8369a45f4acec87c32035c025 failed · ordinary: 8 failed, 2 passed
8× PreparationError: source.selected_views/discovery: frozen source-set policy requires its explicit named set
   raised python/corpus-structure/src/corpus_structure/semantic/data_operation_compilation.py:144
   python/corpus-structure/tests/semantic/test_source_discovery.py::test_acquire_preserves_body_under_its_older_pinned_source_contract [setup]
   python/corpus-structure/tests/semantic/test_source_discovery.py::test_closed_empty_source_selection_is_explicit_and_has_nominal_members [setup]
   6 more: ci test failures ef52a7c8369a45f4acec87c32035c025 --after 2
next: ci test retry ef52a7c8369a45f4acec87c32035c025 --lane ordinary
```

**Why it matters.** These are the most-used reads, and the pipelines on `test failures`,
`results show` and `results hold` (107 of the 255) are agents building this view themselves.
[cli-reporting O01](cli-reporting_2026-11-07.md#O01) recommended a flat layout for headless
transcripts; the delivered views are bounded and typed but still drawn as terminal tables.

**Scope.** `test failures`, `results show`, `results list`, `check` and the `ci test` final
report first — not all 131 commands. The shared renderer then serves others as they are touched.
Delivery includes changing the `ci` skill reference, which currently steers agents to `--json`;
otherwise they will keep passing it.

**Mechanisms.**
- Choose the layout from the console, not a flag: `Console.is_terminal` is false under a pipe
  (rich.md §2.4, §7.6). In that case render with `Table.grid` or `box=None, show_edge=False,
  pad_edge=False`, columns `no_wrap=True`, and print with `soft_wrap=True`; a probe measured 243
  characters for a grid against 567 for any boxed table. Rich pads every line to full width and
  has no switch for it, so the piped renderer strips trailing whitespace after `Console.capture()`,
  or uses `Console.out` for plain lines.
- One model, two layouts: `__rich_console__(console, options)` sees `options.is_terminal` and
  `options.max_width` (rich.md §2.2), so each report keeps one renderer that adapts, in place of a
  second rendering path.
- One contract for bounds: the shared `Annotated` aliases in `cli/output.py` (as `JsonOpt` is
  today) extended to `--limit`, `--after` and `--view`, so the options mean the same thing wherever
  a command pages. Several of the observed "No such option" errors (`--limit`, `--view`) are agents
  assuming this already holds. Typer has no option-group injection; aliases are the native route
  (typer.md §3).
- Root-level global options are a poor fit: Typer groups do not accept parent options after the
  subcommand (`typer/core.py:993`). If one switch is wanted, `typer.Option(..., envvar=…)` on the
  shared alias turns a mode on from the environment and `ctx.get_parameter_source` lets an explicit
  option win (typer.md addendum §3.1–3.4).

**Alternatives.** Make JSON the default when piped: simplest, but JSON repeats field names on every
record and carries provenance fields the agent rarely wants; the pipelines exist to strip those.
A `--fields` projection on JSON: useful for programs, still a second step for the common read.

**Delivered when** an agent reads a failed run, a result's status and a check outcome without
`--json` and without a post-processing step, and can paste any identifier from the output into the
next command.

<a id="O02"></a>
### O02 · Failures read as cause, location, detail — in the test run's own report

**Who and what.** An agent that has just run tests. Today `ci test` ends with lane outcomes and a
result ID: the `Campaign` report carries only id, outcome, lanes and next action
(`cli/testing.py:46-50`), and lane counts go to stderr (`testing.py:794-797`). The agent then calls
`ci test failures ID` (the first read after a launch 273 times), and often again with
`--native-traceback` (199 uses) to learn where the failure was raised. Afterwards, a failing
`ci test` ends with the digest itself: failures grouped by identical cause, the raise location for
each group, a few example test IDs, the command for one test's full detail, and the retry command.

**Why it matters.** It removes one round trip from most failing runs and usually a second. With
several failures from one cause — the common shape after an edit — the agent sees one cause, not a
list to compare by eye; one observed pipeline was an agent grouping failures by diagnostic itself.
Because 629 of 758 launches were still running when the agent's shell first yielded, agents read
the end of the run through polled session output, so a final report that is complete in itself is
what they actually see.

**Mechanisms.** The data is already retained and parsed: the `reprcrash` path and line and the
frame locations are extracted in `scripts/test_receipts.py:1529-1762` and exposed as
`native_traceback.locations` (`cli/testing.py:111`). The change is in what the default selects:
carry the `reprcrash` location on every failure item; group by exception type, message and raise
location; and have the lane supervisor's settle output carry the bounded failure projection so
that `_finish()` (`testing.py:807`) reports it without starting another classification process.
Locations should be relative to the checkout; the observed payload carried an absolute path into
another worktree. `--native-traceback` remains the full-detail read.

**Delivered when** a failing targeted run needs no follow-up command for the agent to open the
right file at the right line.

<a id="O03"></a>
### O03 · Find a result by what the agent knows

**Who and what.** An agent that has lost a result ID — after context compaction, across a
delegated worker, or because it launched three runs. Today the ID printed on stderr is the only
handle. Afterwards: listing is newest first with filters for outcome and time, and `latest` is
accepted where a managed result ID is (`ci test failures latest`, `ci results show latest
--action test`), always echoing the ID it resolved to.

**Mechanisms.**
- Time-ordered IDs: `uuid.uuid7().hex` (standard library in Python 3.14) in place of `uuid4().hex`
  at `cli/managed.py:540`. The 32-character form still matches `_ID` (`managed.py:36`).
- Listing changes with it. `ResultStore.list` iterates ascending and pages with
  `path.name <= after` (`managed.py:919-920`); newest-first reverses both, so the cursor's meaning
  changes and should be restated, not assumed.
- Existing random IDs do not interleave: version-7 IDs currently begin `01a1…`, so most legacy IDs
  sort after every new one, and the held legacy results never expire. The ordered listing should
  therefore consider only version-7 IDs; legacy results stay reachable by explicit ID until they
  are collected or, where a plan cites them, re-held under O04 or promoted with
  `ci evidence retain`.
- Scope `latest` to the checkout that made the result, recorded in the manifest. That is
  verifiable today and separates worktrees; a per-agent session label would be finer but no usable
  Codex session identifier was established.
- D8 rejects silently selecting "latest" for semantic reads (D8 §4). This proposal is limited to
  managed invocation results, where the thing selected is the agent's own most recent run and the
  resolved ID is printed; the review should not be read as loosening the semantic rule.

**Alternatives.** An index to answer "latest": unnecessary once IDs sort by time. See O05.

**Delivered when** an agent that kept no ID reads its last test run's failures in one command and
sees which result that was.

<a id="O04"></a>
### O04 · Holds that name their consumer, and expiry that happens

**Who and what.** The operator, and every agent that cites a result. Observed: `ci results hold`
was called 439 times in three days. 2,894 of the 6,236 stored results are held, 2,868 of them by
themselves with no dependent; a further 2,399 unheld results are past their expiry, the oldest by
9.8 days. The store is 24 GB.

Agents hold results because the `ci` skill tells them to: record result IDs in the consuming plan
and hold them "while a named consumer depends"
(`.claude/skills/ci/references/testing-and-results.md:116-122`), and plans do cite raw result IDs
as closure evidence. But the consumer cannot be named. `hold --dependent` accepts only another
result ID (`managed.py:769-771`); agents tried `hold ID --reason 'DDO I02 extraction integration'`
and `--reason DDO-current-runtime` and were refused. So every such hold is anonymous and nothing
releases it when the plan item closes. Separately, unheld results expire only when someone runs
`ci results gc --apply`, which the skill reserves for "when cleanup is authorized".

**Proposed.**
- Let a hold name what depends on it: `hold ID --for <plan item, record or label>`, stored with the
  hold. `release-hold --for <consumer>` releases everything held for it, and the `gc` preview
  groups holds by consumer so stale ones are visible.
- Prefer `ci evidence retain` for citations meant to outlive the working set; a hold is for the
  duration of a piece of work.
- Let expiry of unheld, settled results happen without a manual step — for example when a new
  result is created — within ADR-0069's existing rule about what may be collected.
  [typer-cli-target O03](typer-cli-target_2026-11-07.md#O03) proposed optional scheduling; this
  was not realized.

**Decision needed.** Automatic expiry changes the current rule that `gc --apply` runs only when
authorized. That is the operator's decision, recorded as an amendment to D8 §4 and the skill
reference, or an ADR if the operator sees real alternatives.

**Delivered when** every hold names something, closing a plan item releases its holds in one
command, and the store's size tracks the retention policy.

<a id="O05"></a>
### O05 · One per-result table; results that know their source; a two-run delta

**Who and what.** An agent between two runs of the same tests, before and after an edit, and
every view that reads a test result.

Three connected changes:

1. **One compact per-test table per lane, replacing `classification.json`.** One full campaign's
   `classification.json` was 141 MB, about 97 MB of it duplicated context and node data. Nothing
   reads its content: the two consumers only check that it exists (`managed.py:1043`,
   `testing.py:756`), and every view reclassifies from the raw log in a separate
   `uv run python scripts/test_receipts.py classify` process (`testing.py:1466-1475`). Write one
   table at classification — test ID, lane, phase, outcome, reason, raise location — and have the
   views read it. This removes a large unused artifact and a subprocess from every failure read,
   and it is the structure O02's grouping needs.
2. **Source currency.** `ci results show` reports whether the result still describes the tree:
   `source: current`, or `changed (2 files, 1 under the selection)`. The supervisor's
   `source_identity()` (`scripts/test_receipts.py:263-272`) already records `git status
   --porcelain` and per-file hashes of untracked files; only the tracked diff is a single
   aggregate hash. Hashing each path that porcelain status lists, and using
   `git diff --name-only` between the two commits when HEAD has moved, names the changed files
   without snapshotting the tree. (A full snapshot through a temporary git index was considered
   and rejected: it would rehash the tree, including 47,535 LFS files, on every run.) The manifest
   should also record the normalised selection, which today is only inside the lane receipt.
3. **A two-run delta.** `ci test coverage A B…` already compares attempts against the first
   result's selection, joins test identities across receipts and reports when source contexts
   differ (`testing.py:1076`, `test_receipts.py:1359`). Add a `--view delta` to it — newly
   failing, fixed, still failing, plus the files changed between the runs — in place of a new
   command. With O03 this is `ci test coverage latest~1 latest --view delta`. It compares the run
   just made with the one before it; it is the agent's immediate before-and-after, not history.

**The storage question.** The operator's hypothesis was a more structured store, possibly SQLite.

| Realization | What it adds for an agent | Cost |
|---|---|---|
| SQLite index across the result directories | Fast "latest" and filters, which ordered IDs give for nothing; per-test queries across many runs, which is the excluded history | A second record of truth, a write under the store lock on every result, a rebuild path, schema changes |
| SQLite as the store of record | Nothing beyond the above | Replaces verified custody code; cannot replace the locks, which depend on process lifetime and directories; supersedes ADR-0069 |
| DuckDB over the files in place | Ad hoc analysis across runs | Bypasses leases, redaction and bounds; ties agents to the receipt layout, which then cannot change freely |
| One structured table per result, written at classification, under that result's lease and expiry | Everything in this opportunity and O02's grouping | Replaces an artifact nothing reads; rebuildable from the raw log |

The recommendation is the last row. Its format — sorted JSON lines or one SQLite file per result —
is an implementation choice: `sqlite3` is in the standard library, so the stdlib-only supervisor
is no obstacle, and a per-result file has one writer and no concurrency question. Sorted JSON
lines are enough for a merge of two runs; SQLite earns its place once per-run views need grouping
or joins that a sorted scan handles awkwardly, and O02's group-by-cause is the first such view.
The two independent reviewers differed here: the first treated a per-result SQLite file as a large
rewrite of the supervisor's projection code; the second pointed out that the table replaces an
unused artifact and is the natural home for structure now. This review follows the second.

A store *across* runs is declined because, with history excluded, every question an agent asks
concerns one run, two runs or the newest run. If the operator later wants history or flaky-test
detection, a derived cross-run index becomes reasonable and the per-result tables are what it
would be built from.

**Delivered when** a failure read starts no reclassification process; `results show` says whether
a pass is stale; and an agent, after an edit and a rerun, learns in one bounded call what its edit
fixed and what it broke.

<a id="O06"></a>
### O06 · Diagnostics partitioned by the change

**Who and what.** An agent that has edited some files in a tree other agents are also editing.
Today `ci check --only types` checks the whole repository (189 calls; of the stored
whole-repository type results, 241 failed and 206 passed), and the agent sorts its own errors from
everyone else's. Afterwards, `ci check --changed [--since REF]` reports diagnostics in two parts:
detail for files the agent changed, counts by file for everything else.

**Mechanisms.** Run the whole project and partition the result; do not check a subset.
`pyrefly check --output-format json` took about 1.1 s for the full project in a probe, and
checking only the changed files would miss breakage in their consumers — those appear in the
"elsewhere" part, where a consumer newly broken by this edit will show up next to pre-existing
failures. `ruff check --output-format json` is file-local, so limiting it to changed files is
sound. The changed set is `git diff --name-only` against the reference plus untracked files.
"New since a reference" would be better still, but needs diagnostic keys that survive line moves;
that was not established, so the partition by path is the proposal.

**Rule impact.** This is a view over existing checks, not a new alignment lint.

**Delivered when** an agent in a shared tree can tell in one call whether the errors are in its
files.

<a id="O07"></a>
### O07 · Questions about the working tree's own code

**Who and what.** Any agent scoping a change; code-mapper and reviewer roles most of all. Reading
and searching are 54% of all commands. The typical chain is a search for several names at once,
then windowed reads of the hits, repeated per symbol. Afterwards a small `ci code` group answers
the questions search answers badly, each bounded and in O01's layout:

| Command | Answers | Mechanism |
|---|---|---|
| `ci code refs NAME` or `PATH:LINE` | Every use, tests included, type-resolved | `ty` `references` |
| `ci code callers NAME` | Who calls this | `ty` `callHierarchy/incomingCalls` |
| `ci code outline PATH` | What is in this module, with line ranges | `ty` `documentSymbol` |
| `ci code importers MODULE [--tests]` · `reach MODULE` · `why A B` | Who imports this; everything downstream; the import path from A to B | `ruff analyze graph` + NetworkX `predecessors`, `ancestors`, `shortest_path` |

**Why these mechanisms.**
- `ty server` 0.0.102 advertises all the navigation operations and answered on the real tree in a
  one-shot process: references in 0.13–0.77 s on first call, incoming calls in 0.03 s (18 callers
  including tests). No index, cache or long-lived server is needed. It models Pydantic fields: a
  field reference query returned the constructor keyword and the attribute reads. `pyrefly lsp`
  works too but returns empty cross-file answers unless started with
  `--indexing-mode lazy-blocking`, and missed the constructor keyword.
- The existing client is reusable: `_Session` and the position helpers in
  `semantic/source_navigation.py:102-222`. What ties that module to captured sources — documents
  copied to a temporary directory, an empty environment with no site-packages, a hard-coded
  analyzer profile — is what a working-tree route must not copy: it points the server at the
  repository and the real `.venv`. One shared client with two callers.
- `ruff analyze graph --direction dependents` produced the file-level import graph in 0.36 s from
  the existing ruff cache; a standard-library `ast` walk took 2.4 s and can label each edge as
  top-level, function-local or type-checking-only. The codebase has 8,425 function-local imports
  against 9,693 top-level; with only top-level edges the graph is acyclic in 18 layers, and with
  all edges it has cycles up to 224 modules. Commands should say which edge set they used.
  NetworkX's reachability functions do the rest (networkx.md, directed reachability and ancestry).
- Astroid cannot infer Pydantic field access (`Uninferable` in the probe) and adds nothing here.
  LibCST's repository-wide name resolution took 99 s; it belongs to rewriting (O08) on a
  prefiltered file list, not to queries.

**Test selection stays the agent's choice.** `importers MODULE --tests` lists test modules that
reach a module; it does not pick the run. Agents already name paths, and with this many
function-local imports and widely imported core modules (`semantic.identity` has 238 importers)
automatic selection by reachability would tend to select most of the suite. It is also not sound:
it misses fixtures supplied by `conftest.py`, modules loaded through `importlib.import_module`,
CLI tests that reach code through lazily importing commands, and helpers resolved through the
tests directory. No line-coverage tool is installed to do better (`ci test coverage` reconciles
which tests ran; it is not line coverage). The command should state these limits in its output.

**Model-centred scoping.** For "everything that reads or constructs this field", no single tool
is sound. `ty` references are the precise core; string keys in `model_dump()` output, aliases,
JSON and SQL need a plain search. `ci code refs` on a field should return the type-resolved set
and name the kinds of use it cannot see.

**Left out on purpose.** `def` and structural `search`: finding a definition or a pattern is one
`rg` or `ast-grep` call already. An interface difference against a git reference (Griffe
`find_breaking_changes`, 0.06 s after two 1.2 s loads): at the design stage breaking replacements
are the norm and `refs` finds the consumers to migrate. If it is ever wanted, the old side must
come from `git archive`, not Griffe's `load_git`, which creates a branch and worktree in the
repository (`griffe/_internal/git.py:120-150`).

**Prerequisite.** O09's start-up work. A call that takes 1.5 s before it starts competes with an
instant `rg`; the case for `ci code` is the questions where `rg` needs a chain.

**Alternatives.** Expose the same operations through the existing MCP server (`ci mcp serve`) or
let agents attach a language server directly: reasonable for interactive harnesses, but the CLI is
the route every role already has and demonstrably uses. A persistent symbol index: unnecessary at
these timings and one more thing to keep fresh.

**Delivered when** a code-mapper's "who uses X" chain is one call returning file, line and
enclosing symbol, and an agent changing a model field starts from a list instead of a search.

<a id="O08"></a>
### O08 · Previewed mechanical change — conditional

**What.** A rewrite as a reviewed operation: a command produces a unified diff as a managed
result; `--apply ID` writes it if the target files are unchanged since the preview. This is the
preview-then-apply shape the CLI already uses for model changes.

**Mechanisms available.** `ty` and `pyrefly` `textDocument/rename` return a type-resolved edit set
without applying it. LibCST `RenameCommand` handles qualified-name and import-aware renames, and
`parallel_exec_transform_with_prettyprint(unified_diff=N)` returns diffs without writing
(libcst.md, qualified-symbol renaming). ast-grep-py's `SgNode.replace` and `commit_edits` give
syntactic rewrites as strings to diff (ast-grep-py.md §7.1–7.3); the `ast-grep` command-line
binary does the same with `-r` but is a host tool, not a pinned dependency. Apply-by-ID needs only
the stored diff and content digests of the target files.

**Why conditional.** The 7 November review set the bar at an observed recurring hand-written
transformation. The logs do not clear it: three clear same-edit-across-files episodes in patch
calls. There are 1,574 inline edit scripts that touch several files, but they were not read, and
Codex writes most edits that way regardless. Pydantic field renames, the change most likely to
recur here, are the case syntactic tools handle worst.

**Revisit when** a rename or signature change across many files is next planned; try the `ty`
rename route by hand first.

<a id="O09"></a>
### O09 · Leaner start and help

Small; do it with O01 and before O07.

- **Start-up.** Importing the application takes 0.8–1.0 s; building the command tree takes 0.04 s.
  The cost is module-level imports in three command modules: `cli.demands` 0.44 s, `cli.db`
  0.15 s, `cli.research` 0.09 s. Moving those behind function-local imports, as the rest of the
  CLI already does, removes most of it without lazy command groups, which Typer 0.28 does not
  provide natively.
- **Help under a pipe.** `ci db --help` is 1,538 characters with Rich panels and 495 in plain
  mode. `rich_markup_mode=None` on the application gives plain help and plain usage errors; it is
  per application, so the choice is made once in `main()` from whether stdout is a terminal.
  (`TYPER_USE_RICH=0` does the same but must be set before Typer is imported.) Plain mode shortens
  long help text, so descriptions that matter should be written to fit.
- **A developer-loop panel.** Group the dozen commands used when editing code (check, test,
  results, format, docs, adr, evidence, and `code` if O07 proceeds) ahead of the 25 product groups
  with `rich_help_panel`, as [typer-cli-target O05](typer-cli-target_2026-11-07.md#O05) proposed,
  so root help is an orientation.
- **Gaps.** Four root commands have no help text. `ci check --only` does not list its values; an
  `Enum` type makes help and completion show them.
- **Singular and near-miss names.** Agents typed `ci result` and `ci inspect`. Typer already
  suggests corrections for mistyped commands and options, so no new error machinery is needed;
  the observed misses are mostly options that exist on sibling commands, which O01's shared
  aliases address.
- **Where not to invest.** The generated reference: five uses against 171 `--help` calls. Help is
  where agents look.

<a id="O10"></a>
### O10 · Worktree support, checkout identity and search hygiene

Beside the CLI as much as in it, but it taxes every call.

- **Worktrees.** AGENTS.md permits a worktree when parallel agents must edit production code
  concurrently, which is the executor case, and executors use them constantly: 13,835 commands
  reference another worktree's path; about 1,900 carry a 200-character
  `UV_PROJECT_ENVIRONMENT=… PYTHONPATH=…` prefix; 69 outputs report the agent environment
  unavailable in a fresh worktree; one executor ran the same "which checkout am I in" check five
  times. The route is permitted but unsupported.
- **Testing the wrong source.** The editable install in the main checkout's environment points at
  the main checkout's `src`. A worktree executor that forgets the `PYTHONPATH` prefix tests main's
  code and gets a confident result about the wrong tree. Proposed: record the imported package's
  location against the checkout in each manifest, show both in `ci context show` as a one-line
  identity (checkout, branch, environment, package source, results root), and refuse or warn when
  they disagree. With that, `ci` can resolve its checkout from the working directory and the
  prefix becomes unnecessary.
- **Shell noise.** 92% of command outputs begin with two `direnv` log lines. Setting
  `DIRENV_LOG_FORMAT` to empty in the agent environment removes them.
- **Runaway search.** One `rg` over `docs` produced about 714 MB before the output cap because
  evidence folders hold raw outputs; seven others produced tens of megabytes. An ignore file for
  search tools covering evidence raw outputs and `build/` fixes this at no cost to intended reads.

**Delivered when** a worktree executor runs `ci test -- PATH` with no environment prefix and the
result records which source it tested.

<a id="O11"></a>
### O11 · Model-change and recipe-output reads — next inquiry

The operator's scope includes changes to the model, and this review did not examine that workflow
in depth. What the logs show: `ci model change` was called 332 times and piped into inline Python
47 times, mostly `inspect-candidate --view operations|sql --limit N --json`; one agent wrapped
`inspect-candidate` in a loop over `--after` to collect every page. `ci results output ID --stream
stdout --json` was piped into Python 57 times, the largest single source of pipelines. In both
cases an agent is reducing a typed report to the few fields it wants, which is the symptom
AGENTS.md calls a missing view.

The scripts' bodies were not read, so which fields agents extract is not established. The next
step is small and specific: read those roughly 100 pipelines, name the two or three answers they
compute, and give `model change inspect-candidate` and `results output` a view for each in O01's
layout. This belongs with whichever plan takes O01.

## How the opportunities fit together

O01 is the base: O02, O03, O06, O07 and O11 present their answers through it. O02 and O05 share
the per-result table; O02 can be delivered first against the current classification and move onto
the table when O05 lands. O03 supplies `latest`, which O05's delta uses. O04 is independent and
urgent in its own right. O07 depends on O09's start-up work. O08 waits.

A reasonable order:

1. O10 (search ignore file, direnv noise, checkout identity and the wrong-source guard) and O04.
2. O01 with O02 and O09 on the test path; O06; O03.
3. O05; O07; the O11 inquiry.
4. O08 when its condition is met.

## Observed but outside the CLI's reach

- Orientation reading is heavy: every session reads the worker contract, and one root session with
  30 compactions read the DDO plan 126 times and `STATUS.md` 72 times. Shorter orientation
  documents would help more than a command.
- Agents wait on tests: a traced median of 95 s per `ci test` run, with polling in between. The
  CLI can make the final report complete (O02); it cannot make the harness wait better.
- Codex writes most edits as inline Python replace scripts (2,596) rather than patches (1,148).
  That is the harness's habit, not a gap in `ci`.

## Evidence limits

- The log window is three days dominated by one plan (DDO); the command mix will shift with the
  work. Counts come from regular-expression classification and were validated only by reading a
  sample of episodes and by the second reviewer's spot checks, which found the usage-error table
  incomplete (it kept only the first line of each error).
- All timings are single runs on one machine, reported to show feasibility, not performance.
- Not verified: a session identifier usable from Codex; how pyrefly's `--baseline` matches
  diagnostics; why the `ast` and `ruff` import graphs give different dependant sets for the same
  module (67 against 87 in one case); the token cost of box characters; what the O11 pipelines
  extract.
- Every design statement here is `Proposed`. Observed facts are dated 2026-11-16.

## Handoff

Selected opportunities go to `create-plan` citing `agent-cli-capabilities_2026-11-16.md#O01` and
so on. Decisions and rule impacts to carry: ADR-0069, D8 §4 and the `ci` skill's results reference
for O03–O05 (automatic expiry and consumer holds need the operator's decision); D8's "no silent
latest" rule, which O03 leaves intact for semantic reads; the `ci` skill's `--json` guidance for
O01. No recommendation adds a dependency: `ty`, `ruff`, `pyrefly`, Griffe, LibCST, ast-grep-py and
NetworkX are pinned, and `sqlite3` and `uuid7` are in the standard library.
