# Process, collection, scheduling and non-database preparation map

Baseline: `main` at `784d86f11`, clean tracked tree (one untracked doc, `docs/libraries/parsing/torch.md`).
Examined 2026-11-12 by reading source. Read-only: no test run, no collection, no DB, no timing.
Two exceptions, both pure imports of product code in the project venv (no DB, no models):
`import corpus_structure.cli.app` and `import native_test_support` plus
`corpus_structure.semantic.runtime`, to read `sys.modules`; and `len(core.schemas.SCHEMAS())`.
Counts labelled "grep" are textual counts, not collected-node counts. DB template/clone cost
(DTA-024) is outside this map except where it shapes scheduling.

Paths are repo-relative; `PKG` = `python/corpus-structure`.

---------------------------------------------------------------------------------------------

## 1. The run route

### 1.1 Chain of processes for `uv run ci test [--workers N] [-- PATH...]`

1. `ci` interpreter. `PKG/src/corpus_structure/cli/app.py:36-45` (`main` splits `--`, passes the
   selectors as `CliState.test_args`). Importing `cli.app` imports all 22 command modules
   (`cli/__init__.py:8-31`, REGISTRY `:33-56`). Observed 2026-11-12 after
   `import corpus_structure.cli.app`: `sys.modules` contains sqlalchemy, psycopg, psycopg_pool,
   linkml_runtime, pydantic, rich, typer; does not contain spacy, sympy, scipy, numpy, fastmcp, lark,
   torch, docling_core. (The same fact is asserted by a fresh-interpreter test,
   `PKG/tests/test_cli.py:276-300`.)
2. `run_tests` (`cli/testing.py:565-619`). If any selector was given: `_validate(args)`
   (`:447-461`) runs `uv run python scripts/test_receipts.py validate-pytest --report-selection --
   ARGS` through `run_owned` (a new `uv` + `python` for argument screening only;
   `scripts/test_receipts.py:1536-1552`, `1621-1627`). `narrowed` is true iff a path or `-k` selector
   was supplied; `-q/-v` alone is not a selector.
3. `result_store(ctx).operation("test", ..., observations=True)` opens a managed result workspace
   (`cli/managed.py`, `operation`; `publish` at `:314` registers the lane directory by inode, no copy).
4. `_lane("ordinary")` (`:463-539`): `run_recipe("test-all", *args, env=...)` (`cli/recipes.py:128-148`)
   -> `just --justfile ... test-all ARGS` -> bash recipe at `justfile:17-34`. With
   `CORPUS_CI_RECEIPT_DIR` set (always, from `_lane`) it execs
   `uv run --no-sync python scripts/test_receipts.py run --managed-lane ordinary --out-dir DIR
   [--workers N] [--python-only] -- ARGS` (`justfile:21-32`). `CORPUS_CI_PYTHON_ONLY=1` is set when
   `narrowed or selection is not None` (`testing.py:497-498`).
5. `scripts/test_receipts.py main` (`:1600-1760`):
   - `_managed_pytest_args` (`:1555-1593`): ordinary lane gives `-n <N|auto> --dist=loadgroup -m "not
     shared_cluster_fault" ARGS`; fault lane gives `-n 0 -m shared_cluster_fault
     tests/scripts/test_native_auth.py`.
   - `invocation_context()` (`:273-280`, called at `:1706` and again by the `context` action) runs
     `git ls-files --others`, `git rev-parse HEAD`, `git status --porcelain`, `git diff HEAD --binary`
     (hashed) and SHA-256s every untracked file (`:251-260`).
   - `run_python` (`:312-356`) -> `run_process` Popen of `sys.executable -m pytest ARGS -p
     qualification_plugin --report-log reportlog.jsonl --junitxml pytest.junit.xml -rA
     --hypothesis-profile=ci -o faulthandler_timeout=900 -o faulthandler_exit_on_timeout=true`, env
     `HYPOTHESIS_PROFILE=ci`, `QUALIFICATION_RECEIPT_DIR`, ambient `PYTEST_ADDOPTS`/`PYTEST_PLUGINS`/
     `PYTEST_XDIST_AUTO_NUM_WORKERS` stripped when managed (`:324-331`). `run_process` polls the child
     every <=0.1 s (`:185-189`) in its own session/group and settles the group afterwards (`_stop_group`).
   - `run_rust` (`:359-428`) unless `python_only` or the Python child was cancelled (`:1729-1741`):
     `rustc --version`, `cargo nextest --version`, `cargo nextest list --release --workspace
     --message-format json`, then, under a `flock` on `<target>/nextest/qualification/.junit.lock`,
     `cargo nextest run --release --workspace --profile qualification --no-tests=warn`; each is a
     separate owned process with stdout/stderr files. If the list step cannot name the target dir, the
     rest is skipped with `rust-state.json`.
   - After both: `classify([directory])` (`:906-...`) reads `reportlog.jsonl` and every
     `events-*.jsonl` back, then writes `invocation.json` and `classification.json` (`:1744-1755`),
     prints a JSON settlement line that `_lane` parses.
6. Without selectors (`declared == "all"`) a second lane runs afterwards (`testing.py:612-617`): `just
   test-native-faults` (`justfile:37-49`, env `CORPUS_TEST_NATIVE_AUTH_CRASH=1`), `-n 0`, python-only,
   one file (`tests/scripts/test_native_auth.py`), with the same plugin/receipt machinery. A fault
   session collects only that file, so the package conftest is not imported there.
7. `ci test retry` (`testing.py:1005-1090`) adds, per lane: `uv run python scripts/test_receipts.py
   context` (git again), `classify --summary` (twice), and `write_unresolved`
   (`scripts/test_receipts.py:1457-1524`), which runs a full body-free collection session
   `run_python(... -n 0 --collect-only -m ... @required.txt)` of the entire required selection before the
   retry session itself. `coverage`/`failures` subcommands each spawn `uv run python
   scripts/test_receipts.py classify ...` through `_supervisor` (`testing.py:409-444`).

Other test routes present: `justfile:14` `check: test py-test` with `py-test` = plain `uv run pytest`
(`:154-156`, addopts apply, no receipts) and `test` = `cargo nextest run --release --workspace`
(`:137-138`). Whether these are still used is not established here.

### 1.2 What every invocation does regardless of selection size

Observed from code:
- 1 `ci` process + (`uv`, `just`, `bash`, `uv`, controller `python -m pytest`) + N xdist worker
  interpreters + `git` calls at start (`invocation_context`) + the `classify` pass at the end.
  With a selector, +1 `uv`+`python` for `validate-pytest`.
- Controller and each worker load the same plugin set. Entry points present in `.venv`:
  anyio, faker, hypothesis (`_hypothesis_pytestplugin`), platformdirs, pytest_logging,
  pytest_reportlog, xdist (+looponfail) (site-packages `*/entry_points.txt` `[pytest11]`), plus
  `-p qualification_plugin`. Nothing sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD` (managed mode only removes
  it from the env, `test_receipts.py:326-329`).
- Files written per invocation: `invocation.json` (twice), `runner.process.json`,
  `pytest.stdout/.stderr/.process.json`, `reportlog.jsonl`, `pytest.junit.xml`,
  `events-<worker>-<pid>.jsonl` per process (opened exclusively, `qualification_plugin.py:74`),
  `classification.json`; Rust: `rustc/nextest-version/nextest-list/nextest.{stdout,stderr,process.json}`,
  `nextest.junit.xml`, `rust-state.json`.
- Events per test per executing process: `logstart`, `phase_start` setup/call/teardown, `logfinish`
  = 5 JSON lines, each `flush()`ed (`qualification_plugin.py:42-48`, `135-156`, `179-183`). The
  controller also receives xdist's replay of logstart/logfinish and writes its own stream. Reportlog
  adds one line per phase report. `-rA` prints a summary line for every passed test.
- Per worker at `collection_finish` (`:103-128`): one event holding the full selected nodeid list, an
  alias map and an affinity-group map keyed by every node, plus the `native_required` list, so the
  event size is O(collected items) per worker. The uniqueness loop at `:106-111` is O(items).
- `session_start` records `math_pool_cap=8` as a literal (`:99`), duplicated from
  `PKG/tests/math_support.py:278`.
- Per-test `faulthandler_timeout=900` (`TEST_TIMEOUT`, `test_receipts.py:31`), session 14400 s.
- `observe_connection` (database) calls `record_native_context`, which emits a `native_context`
  event per physical connection acquisition when a sink is open (`native_test_support.py:668-...`,
  `qualification_plugin.py:51-64`).

### 1.3 What a narrowed selection changes (observed)

- `CORPUS_CI_PYTHON_ONLY=1`: Rust route (`rustc`, nextest list, nextest run) skipped; fault lane not
  run (`testing.py:612-617`). `--lane ordinary` without selectors keeps the Rust route.
- Pytest receives the selector paths, so `testpaths` is not used and only the conftests on those paths
  (and rootdir `conftest.py`) are imported. Selecting only under `tests/scripts/` does not import
  `PKG/tests/conftest.py` (the CLI app, sqlalchemy, hypothesis profile registration, DB fixture
  machinery). A path under `PKG/tests/` imports it.
- `-n` stays `auto` (or `--workers N`) even for one file; worker count is not reduced by selection
  size. xdist creates `numprocesses` workers regardless (`qualification_plugin.py` records
  `workers_created`; `test_receipts.py:792-846` `_worker_facts`). Open question: whether xdist
  suppresses idle workers when fewer work units than workers exist (xdist behavior, not repo code).
- The Hypothesis profile: package conftest registers/loads `ci` (see 2.5). Outside the package the
  built-in Hypothesis `ci` profile loads (`hypothesis/_settings.py:637-645`; deadline None, derandomize,
  database None; `max_examples` stays 100).

---------------------------------------------------------------------------------------------

## 2. Worker and session startup

### 2.1 What each xdist worker does before its first test

(xdist 3.8.0, pytest 9.1.1; behavior of xdist is from installed source, not repo code.)
A worker is a new interpreter (execnet popen) that re-parses `pyproject.toml` options
(`pyproject.toml:43-56`), autoloads the plugins in 1.2, imports conftests, then **collects the full
selection itself** (every test module imported in `importlib` mode) and reports its nodeid list so the
controller can check all workers agree. `test_receipts.py:631` enforces "workers disagree on selected
scheduled identities". The controller does not collect the tests; N workers each pay the entire
import-and-collection cost. In a full run this is 525 test files (grep: 497 under PKG, 28 under
`tests/`), about 4,129 `def test_` (grep: 3,841 + 288), 852 `parametrize` decorators (grep).

Hooks run on every worker at collection:
- `conftest.py:9-18` (`pytest_configure`) creates `build/tmp/pytest` and sets `PYTEST_DEBUG_TEMPROOT`.
  `tests/conftest.py:6-16` and `PKG/tests/conftest.py:91-103` repeat that logic (3 copies of the same
  code, kept for "run this package alone").
- `conftest.py:21-50` (`pytest_collection_modifyitems`, wrapper): marks math preparation tests with
  `xdist_group("math_preparation")` (see 3.2); after deselection raises `UsageError` if
  `shared_cluster_fault` items are mixed or if a parallel run includes them.
- `PKG/tests/conftest.py:122-138`: iterates all items; adds `db` marker when `item.fixturenames`
  intersects `DB_FIXTURES` (`:71-88`, 14 names); `_missing_local_corpus` (`:106-119`) reads up to 3
  files under `docs/statistics_corpus` (once per worker, only if any `corpus`-marked item is selected)
  and, if absent or an LFS pointer, adds a `skip` marker plus `user_properties` to every `corpus` item.
- `scripts/qualification_plugin.py` hooks listed in 1.2.

### 2.2 Package `tests/conftest.py` import cost

It imports at module load (`:24-54`): `hypothesis.settings`, `sqlalchemy`, `typer.testing.CliRunner`,
`corpus_structure.cli.app` (all 22 command modules; resulting set in 1.1), `cli.output`,
`core.db.ownership`, `semantic.runtime`, `settings`, and `scripts/native_test_support.py`
(sqlalchemy, `core.db.extensions`, `core.db.ownership`, `settings`, `test_prerequisites`; its docstring
says importing it acquires no resource). Observed after importing `native_test_support`,
`semantic.runtime`, `core.db.ownership`: sqlalchemy, psycopg, linkml_runtime loaded; spacy, sympy, lark,
fastmcp, numpy, torch not. `PKG/tests/semantic/conftest.py:9-20` adds `semantic.migrations.upgrade`,
`core.db.extensions` for modules under `semantic/` (and `acceptance/conftest.py:3-4` re-imports its
two fixtures).

### 2.3 Fixtures with session scope or autouse (per worker process)

Autouse: `refuse_unbound_application_target` (`PKG/tests/conftest.py:189-200`) for every test under
`PKG/tests/`; it depends on session fixture `native_settings` (`:183-186`, constructs `Settings()`,
reading env/dotenv once per worker) and does a `monkeypatch.setenv` per test. Also
`test_settings.py:13` and `ingest/test_pdf_recognition.py:106` (module-local autouse).

Session fixtures by consumer group (25 `scope="session"` declarations, grep; 52 `scope="module"`, grep):
- DB, built on first use per worker: `native_server` (`:243-252`: `check()`, `check_roles`, `sweep()`,
  `record_server_context`), `semantic_head_template` (`:256-260`, bootstraps one template database per
  worker: `native_test_support.py:613-630`), `db_server`, `db_engine` (one clone per worker),
  `serving_scenario_seed` (`semantic/serving_scenarios.py:288`), `db_support`.
- Math (`PKG/tests/math/conftest.py:28-78`): `spike_content`, `spike_readings`, `spike_extraction`,
  `spike_scoped`, `s0r2_content/readings/extraction/scoped`, `env`, `analyse_pages`, `coverage_of`.
  The readings/extraction/scoped stages each run a spawn pool (3.3).
- LLM tests (`PKG/tests/llm/conftest.py:146-158`): `env` builds
  `name_map([load_pack(REPO/"domains/statistics")])` once per worker that runs an `llm/` test.
- `ingest/conftest.py:23`: `ingest` (a function reference, no work).
- `tests/scripts/test_parallel_harness.py:281-289`: four dummy session fixtures inside a *generated*
  test source (not real).

### 2.4 Import-time work in test and support modules (search-based)

Search: top-level assignments whose right side calls `prepare_release|prepare_pack|load_pack|read_text|
read_bytes|json.load|yaml.*load|load_methods|compile_|build_|model_validate|source_bundle|SchemaView|
pipeline(|spacy|ProcessPool|open(` under `tests/` and `PKG/tests/` (regex over column-0 statements),
plus a column-0 call scan. Findings (no module-level `prepare_release(...)`; all prepare calls are
inside functions or fixtures):
- `PKG/tests/semantic/test_pdf_records.py:575` `_NATIVE_DEFINITIONS = json.loads(native_schema_bytes())["$defs"]`.
- `PKG/tests/ingest/test_renditions.py:32` `SPIKE = json.loads(... spike_renditions.json ...)` (collection-time read).
- `PKG/tests/core/test_shapes.py:197-199` `NON_RECURSIVE = sorted(... schemas.SCHEMAS() ...)`: 28 schemas,
  22 selected after the name filter (observed by calling `core.schemas.SCHEMAS()`); it is a
  parametrize list, so it is evaluated by every worker at collection.
- `PKG/tests/orchestrate/test_work_context.py` etc. are function-level. Cheap module-level key
  construction (`document_key(...)`, `key(...)`) in `core/test_conformance.py:92,188-206`,
  `core/test_keys.py:63`, `core/test_references.py:123`, `core/test_identity.py:56`.
- Collection of `math/test_property.py` imports `hypothesis.extra.lark` and `hypothesis_jsonschema`
  is imported by `core/test_shapes.py:22` for all workers.
- Not found by this search: module-level model loads or spaCy pipeline construction. Limit: statements
  inside decorators' argument lists that call functions (for example computed `parametrize` lists) were
  checked only by the regex above and by reading `test_shapes.py`.

### 2.5 Hypothesis profile registration

`PKG/tests/conftest.py:65-69` registers `ci` (`deadline=None, derandomize=True, database=None,
print_blob=True, max_examples=300`) and an unmodified `dev` (Hypothesis defaults: 100 examples,
200 ms deadline), loading `HYPOTHESIS_PROFILE` (default `dev`). Managed runs set `HYPOTHESIS_PROFILE=ci`
(`test_receipts.py:332`) and also pass `--hypothesis-profile=ci` (`:343`). The plugin records the active
profile at `session_start` (`qualification_plugin.py:86-100`). A plain `uv run pytest` runs `dev`.

---------------------------------------------------------------------------------------------

## 3. Scheduling

### 3.1 Options

`pyproject.toml:46-56`: `--import-mode=importlib -n auto --dist=loadgroup --max-worker-restart=0
-m "not shared_cluster_fault"` plus strictness and `-q`. The managed route re-states `-n`,
`--dist=loadgroup`, `-m` (`test_receipts.py:1585-1592`), so they appear twice in argv.
`-n auto` = `psutil.cpu_count(logical=False)` (psutil is installed; xdist 3.8.0 `plugin.py:16-34`),
overridden only by `PYTEST_XDIST_AUTO_NUM_WORKERS`, which managed mode strips. The requested count is
recorded as `workers.requested` (`testing.py:597-601`, `test_receipts.py:1708-1716`) and the actual
count is read back from the `workers_created` event into `invocation.json`
(`test_receipts.py:1745`, `_worker_facts` `:792-846`). `--max-worker-restart=0` makes any worker loss
fatal for the attempt (the receipt retains unresolved cases for retry).

### 3.2 What `loadgroup` does here

Installed `xdist/scheduler/loadgroup.py:12-60`: a subclass of `LoadScopeScheduling` whose scope is the
`xdist_group` name if the nodeid carries `@name`, otherwise **the whole nodeid**. So every ungrouped test
is its own work unit; there is no module or class affinity. Consequence (fact about scheduling, not a
measurement): a module-scoped or session-scoped fixture is built on every worker that happens to run any
consumer of it.

Every `xdist_group` assignment in the production trees (search: `xdist_group|loadgroup` over `tests`,
`PKG/tests`, `scripts`, `conftest.py`):
- Only `conftest.py:27-37`: items whose `fixturenames` intersect `{spike_readings, spike_extraction,
  spike_scoped, s0r2_readings, s0r2_extraction, s0r2_scoped}` get `xdist_group("math_preparation")`.
  `fixturenames` is the transitive closure, so indirect consumers are included. `spike_content` and
  `s0r2_content` are deliberately outside the set (cheap retained load). Consumers found (grep of test
  signatures, approximate): `math/test_scope.py` (`test_core_standing_contexts`,
  `test_suppose_again...`, `test_held_out...` (corpus-marked), `test_annotated_scopes_reported`,
  `test_scopes_are_typed...`), `math/test_property.py::test_corpus_layer_on_the_spike_pages`,
  `math/test_spans.py::test_m09_on_the_spike_pages`. Tests in `tests/scripts/test_parallel_harness.py`
  (`:269-322`, `:324-363`) assert this affinity, including that `test_m13_rebuilds...` and
  `test_real_spawn_transports`/`test_staged_corpus_relations...` stay outside the group.
- No other group exists in production. The rest of `xdist_group` hits are inside generated sources of
  `test_parallel_harness.py`/`test_test_receipts.py`.
- All grouped items form one work unit, so one worker executes the whole math preparation chain
  (three sequential spawn pools per scope, 3.3).

### 3.3 Per-worker repeated preparation (non-DB), by fixture/helper

All are "once per process that needs it"; with no module affinity, the same content can be rebuilt on
several workers.
- Math chain (`PKG/tests/math_support.py:268-370`, `math/conftest.py`): per stage
  (`reading_pages`, `extraction_pages`, `scoped_pages`) `_run_pages` creates a *new* `ProcessPoolExecutor`
  with spawn context, `max_workers = min(8, len(pages), os.process_cpu_count())` (`:278`), one task per
  page; pool is killed on failure and `shutdown(wait=True)` on success. For the spike set that is 4 pages
  (<=4 children/stage); for S0R2, 3. Children are fresh interpreters importing
  `math_support` -> `corpus_structure.methods.math.*` (grammar/lark/sympy) and
  `math_worker_transport`; each child builds its Earley parsers (grammar `_PARSERS`, `_classify`,
  `_shipped` caches are per process, `methods/math/grammar.py:181,227,235,313-325`). Scope stage: each child calls
  `primary_scope_fixture` which constructs `spacy.lang.en.English()` blank pipeline and a `PreparedScopeCues`
  (`math_support.py:158-200`). The parent gets pickled results back (payload size not measured).
- Retained archive reads: the 11.4 MB `fixtures/trace/archived-renditions.json` is parsed independently
  by `math_support._retained_inputs` (`lru_cache(1)`, `:113-118`), `archived_source._archive` (`@cache`,
  `archived_source.py:13-15`), `semantic/test_trace_reference_fixture.py:21` (module fixture, direct
  `json.loads`) and `ingest/test_corpus.py:13`. In spawned math children `load_page` is called again
  (coverage workers call `read_page` -> `load_page` in the child, `math_support.py:260-262`, `coverage_rows`
  `:386`).
- Release preparation: see section 9 (`prepare_release` `lru_cache(8)`); 52 module-scope fixtures, many
  returning `prepare_release(...)` of the same bundle in each module that imports the shared `prepared`
  fixture (e.g. `semantic/test_formal_evidence.py:29-34` imported into 8+ other modules as
  `from semantic.test_formal_evidence import prepared as prepared`).
- spaCy `en_core_web_sm`: `ingest/sentences.pipeline(config)` `@functools.cache` keyed by
  `SentenceConfig`; see section 9. Spawned CPU workers (`semantic/cpu_execution.py`) load their own copy.
- Pack loads: `llm/conftest.env` (`load_pack(domains/statistics)`, session); `schema/test_packs.py:46-48`
  `stats` (module, `load_pack` + `build_lookup` + `compile_key_schema`) and 12 more `load_pack(` sites (grep)
  and 11 `prepare_packs(` sites (grep).
- Pool size interplay: a math `_run_pages` pool may use up to 8 spawn children while xdist runs
  `numprocesses` workers concurrently; `CPUExecutionScope` pools (`CharacterizationExecutionPolicy(workers=N)`)
  add more children per test. Nothing in `pyproject.toml` or the harness bounds the product.

### 3.4 Nested scheduling inside tests

`tests/scripts/test_parallel_harness.py` and `tests/scripts/test_test_receipts.py` start **real nested
pytest sessions** (with their own xdist workers, plugin autoload and `qualification_plugin`) through
`run_python`. Static count: parallel harness about 17-19 nested sessions (parametrizations: 2 + 8 + 1 + 2
+ 2..4 + 1 + 1 over the seven session-launching tests, `:55,167,197,253,269,324,366`); test_receipts
`child(...)` at 13 sites plus 2 further `run_python` (grep), 67 tests in the file. Two of the harness
tests are DB-bound (`:55-130` one parametrization creates DB clones in parent and child).

---------------------------------------------------------------------------------------------

## 4. Process boundaries inside tests

Static inventory (search: `subprocess.(run|Popen|check_output)`, `sys.executable`, `with_name("ci")`,
`ProcessPoolExecutor`, `multiprocessing`, `get_context`, `shutil.which` over `tests`, `PKG/tests`,
`scripts/native_*`). For each cluster: the claim that needs the boundary, and what each child imports or
prepares before working.

### 4.1 Installed `ci` executable (7 files; each call is a fresh `ci` interpreter importing the CLI app,
section 1.1; with `ci test coverage|failures` each also spawns `uv run python scripts/test_receipts.py classify`)

| Site | Calls (static) | Claim needing the real boundary | Child prepares |
|---|---|---|---|
| `test_cli_test_evidence.py` `_run`, `:25-33` | 31 call sites across 9 tests (10 in `test_installed_compact_coverage_and_exact_failures`, `:199`); +PTY run `_terminal_stdout` `:470-500` (parametrized by width); +1 `scripts/test_receipts.py classify` direct `:226-240` | installed command rendering/pagination over retained receipts; terminal width | CLI app + (coverage/failures) `uv` + `classify` Python |
| `semantic/test_review_cli_native.py` `installed_ci` `:31-80` | 6 + 6 + 3 invocations in the 3 tests (`:131-,187-,264-`) | installed review/model commands against a native DB (env URLs) | CLI app; DB connect; the test also runs `prepare_packs` in-process before (`:275`) |
| `semantic/test_runtime_entrypoints.py::test_current_cli_stdio_journey_and_settlement` `:464-607` | 4 parametrizations (`complete`, `early_exit`, `tool_failure`, `cancelled`), each 1 `ci mcp serve` stdio child via fastmcp `StdioTransport` | stdio MCP session lifecycle, process-group settlement, `pg_stat_activity` principal visibility | CLI app + MCP server build; per case: DB clone, `build_resubmission_case` (`semantic/agent_scenarios.py:36-`) |
| `semantic/test_condition_publication_native.py:481-520` | 1 `ci structure list` | CLI vs in-process transport parity | CLI app; DB |
| `test_cli_managed.py` `:203,218` | 2 `ci results watch|list|context` | installed command works, stderr empty | CLI app |
| `test_cli_observations.py:328-345` | 2 `ci results inspect|watch` (+1 `sys.executable -c` that leaves an unsettled operation) | cross-process observation of an unsettled run | CLI app |
| `test_cli_model_inspect.py:150-185` | 1 run + 1 `git apply --stat` + 1 Popen with closed stdout | exact stdout bytes and EPIPE exit 74 | CLI app |

### 4.2 `sys.executable -c ...` fresh-interpreter controls (29 files use `sys.executable`; grep)

- Import hygiene: `test_cli.py:276-340`: 4 parametrized (`--help`, `schema --help`, `mcp --help`,
  `experiment`) + 2 more; claim: after `CliRunner.invoke(app, ...)` or `build_semantic_server()` none of
  sympy/scipy/spacy/pyarrow/duckdb/`semantic.prepare` is in `sys.modules`. Necessarily a fresh
  interpreter (the worker's own `sys.modules` is not clean). Other import-hygiene children:
  `ingest/test_pdf_recipe.py:96-107`, `semantic/test_alembic_native.py:150-185` (also needs a DB URL),
  `semantic/test_companion_export_native.py:860-890` (`python -I`, offline consumer).
- Cold-process determinism (hash seed / identity): `schema/test_packs.py:68-87` (2 children, each
  `prepare_packs((statistics pack))`; full cold statistics preparation twice), `semantic/test_prepare.py:566-
  650` (2 children, each cold `prepare_release` of a small bundle), `semantic/test_statistics_model.py:108-
  140` (2 children, small cold `prepare_release`), `semantic/test_projection_analysis_products.py:100-160`
  (child per `prepare(...)` call, full semantic-2 preparation incl. `trusted_execution_inputs`),
  `schema/test_model_explanation.py:140-165` (3 children, SQL diff), `semantic/test_terminology.py:110-140`
  (2 children, STATO conversion), `semantic/test_interpretations.py:150-195` (3 runs of an offline
  authoring script with `-I`), `semantic/test_scenario_ports.py` and `semantic/test_operation_call_generation.py`
  (children running generated python), `core/test_method.py:230-250` and three more (pyrefly).
- Closed-pipe/EPIPE: `test_cli_report_delivery.py:15-40,100-125` (`timeout=15`) with several parametrizations.
- Fresh-process failure settlement: `test_cli_managed.py:150-180` (child that `os._exit`s mid-operation),
  `:240-280` (cancellation of `run_owned`, SIGTERM handler sleeps 1 s).

### 4.3 External tools

- `pyrefly check` on a temp file with repo config: `semantic/test_typed_realization.py:82-112` (2 runs),
  `semantic/test_scenario_ports.py:12-60` (2), `semantic/test_operation_call_generation.py:256-320` (2),
  `core/test_method.py:232-260` (1); skipped via `skipif(shutil.which("pyrefly") is None)` at collection.
- `linkml-lint`: `schema/lint_support.py:30-50` `lint_errors`, 3 call sites (grep) in `schema/test_model.py`,
  `schema/test_packs.py:120-`, `test_lint_support.py` (2 raw runs), gated by `skipif(which(...) is None)`.
- `git`: temp-repo init/add/commit/status in `tests/scripts/test_adr.py`, `test_docs.py`, `test_repo_paths.py`,
  `schema/test_model_change_preview.py`, `schema/test_model_explanation.py`, `model_change_support.py:25-30`,
  `test_cli_model_inspect.py:350-366` (each call is a short `git`, many per test).
- Real `just`: `test_cli_recipe_reporting.py` (`run_recipe`/`run_recipe_steps` at 7 sites, a temp `justfile`
  that imports the repo justfile, `:20-60`, plus a 60 s `sleep` recipe killed by a signal); `tests/scripts/
  test_setup_env.py:30-70` runs `bash scripts/setup-env` against a stub toolchain.
- `uv` / `cargo`: not run for real by tests; `test_cli_test_evidence.py:110-180` and
  `tests/scripts/test_test_receipts.py` monkeypatch `run_recipe`, `run_python`, `run_rust`.

### 4.4 Spawn pools and long-lived child controls

- Math lifecycle: `math/test_workers.py` (12 test functions, grep; `_run_pages` with `workers=1`, `timeout=15|2`):
  `test_spawn_with_parent_thread_and_empty_input`, `test_worker_failure_identifies_page[error|exit]`,
  `test_deadline_kills_stalled_worker_and_preserves_completed_diagnostics` (child sleeps 60; production
  deadline arg `timeout=2` injected), `test_interruption_remains_interruption`, `test_keyed_payloads...`,
  `test_spawned_vendored_page_returns_real_span_rows` (a full coverage worker on LocationScale),
  `test_staged_corpus_relations_preserve_direct_page_semantics` (`:325-353`: spawn read of the Normal page
  with `seconds=30`, an in-process `read_page` of the same page, an extraction pool, and a third pool
  `reading_positions`; it takes `spike_content` only and deliberately does not use the group-affine
  session chain). Child targets: `math_worker_cases.probe` (stdlib + `multiprocessing`),
  `reading_positions` (lark). A same-file precedent for avoiding the pool: `:230-262` replaces `_run_pages`
  with an inline executor to test option forwarding.
- CPU execution: `semantic/test_cpu_execution.py` (real `CPUExecutionScope` spawn pools with
  `Manager`, `:221,256,380`; 10 test functions, grep; `packet(prepared)` rebuilt per test `:20-45`),
  `test_cpu_lifecycle.py` (6 tests, kill/grace/IPC lock; see section 5). Pool children import
  `semantic.cpu_execution` worker main and the formal-evidence method inputs (spaCy/sympy path).
  Fixture: module-scope `prepared` (`semantic/test_formal_evidence.py:29-34`: `prepare_release` of
  `core.yaml` with characterization inputs).
- PDF/gliner/PM2 workers: `semantic/test_pdf_lifetimes.py` (spawn context wrapped to observe child pids; 8
  test functions, grep), `tests/test_pdf_process.py` + `PKG/tests/pdf_process_support.py` (`_blocked_child` ignores SIGTERM,
  `sleep(60)`), `ingest/test_pdf_worker_stdio.py:60-105` (a `sys.executable` runner that spawns), `ingest/test_pdf_chandra.py:213`,
  `methods/test_gliner.py` + `methods/gliner_worker_cases.py`, `methods/test_pm2_worker.py` (child script is
  stdlib-only; `:20-60`; 8 test functions, grep; timeouts injected). Claim: owned child retired / group settled before
  custody released.
- Receipt supervisor: `tests/scripts/test_test_receipts.py:1050-1230` (process-group settlement with
  `sleep(60)` descendants, signals) and `test_native_auth.py` (fault lane, serial, 9 spawn sites, `sudo -n`
  guardian at `:985-995`).

---------------------------------------------------------------------------------------------

## 5. Real-time waits

Search: `time.sleep`, `pg_sleep`, `monotonic()+`, `.wait(`/`.join(`/`.result(` with numeric timeouts, named
timeouts, `lock_timeout`/`statement_timeout`. Grouped by purpose. "Injectable" = a parameter or setting
reachable from the test; "module constant" = patchable only by `monkeypatch`.

### 5.1 Waiting out a production grace period (the test spends the production constant)

- `semantic/cpu_execution.py:456-457` `_COOPERATIVE_CLOSE_SECONDS = 5.0`, `_WORKER_EXIT_SECONDS = 5.0`
  (module constants; used `:545,819-820,879`; **not** a constructor/policy argument; no test patches them:
  grep for `monkeypatch.*SECONDS` found none).
  - `semantic/test_cpu_lifecycle.py:59-84` asserts `4.5 <= elapsed < 12` (waits out cooperative grace
    against an initializer ignoring SIGTERM).
  - `:321-385` (parametrized `cancellation|stop`): `stop` asserts `9.5 <= elapsed < 12` (waits out both
    5 s constants); other timings assert `<1`, `<5`.
  - `:87-134`, `:137-168` (`<12`), `:201-318` (`close_finished.wait(12)`): bounds are literals tied to the
    constants.
  - These six tests use the module `prepared` fixture and the shared `packet(prepared)` from
    `test_cpu_execution.py`.
- `pm2_worker`: `methods/test_pm2_worker.py` passes `startup_timeout_seconds=5|0.05`,
  `inference_timeout_seconds=0.2|5` (parameters of `open_pm2_worker`, `methods/pm2_worker.py:388-400`;
  injectable). Hanging child modes sleep 60 s but are killed (`:157-235`); `inflight` tests poll with
  `time.sleep(0.01)` up to 4 s for the child to write a marker. `_POLL_SECONDS = 0.1` module constant
  (`pm2_worker.py:23`).
- Run-supervisor: `tests/scripts/test_test_receipts.py` `child(..., timeout=1|10, test_timeout=0.2|3)`
  (injectable via `run_python` args; children sleep 30-60 s and are killed). Real waits: `:441-470`
  (`time.sleep(30)` hang controls bounded by 0.2 s test timeout or 1 s session timeout).
  `:1060-1230`: 0.02-0.2 s polls and 60 s sleeper descendants settled by `_stop_group`. The supervisor's own
  poll interval `0.1` and `_stop_group` grace are module constants (`test_receipts.py:185-189,217-240`; not
  read here beyond that).
- `test_cli_managed.py:240-280`: a child traps SIGTERM and sleeps 1 s before settling (`run_owned` forward
  deadline 45 s, `recipes.py:94`), test deadline 5-10 s.
- `native_test_support.py:216-250` `_drop`: 2.0 s retry loop (`sleep(0.05)`) on SQLSTATE 55006.
  `scripts/native_auth.py:222-232` 15 s poll with 0.05 sleeps. `tests/scripts/test_native_auth.py` (fault
  lane): sleeps 0.01-0.15 polls, `time.sleep(30)` and `pg_sleep(5)` victims, a 5 s sleep inside the
  guardian wrapper (`:989`).

### 5.2 Lease/claim/heartbeat timers

- `semantic/test_claim_owner_native.py`: `renewal_statement_timeout_seconds=0.5/0.03`,
  `renewal_lock_timeout_seconds=0.5/0.01`, `completion_statement_timeout_seconds` parameter (`:104-105,
  187-189`), `pg_sleep(0.15)` victim (`:205`), `Event.wait(5)` upper bounds. The timeouts are settings of the
  production owner (injectable); production defaults are 120/10/5 s (`db/test_outcomes.py:106-108`).
- `db/test_lifetime_native.py`: `BorrowerCancellation(timeout=2)`, pool `timeout=0.15`, 
  `renewal_statement_timeout_seconds=0.1` (injectable), `pg_sleep(20)` victims (cancelled, so the 20 s is
  an upper bound), `wait_until(..., timeout=5)` polls (`:37-45`). `db/test_adbc_lifetime.py` (`pg_sleep(20)`
  x2, `OperationCancellation(timeout=2)`, `wait(10)`), `semantic/test_companion_export_native.py:533-628`
  (`pg_sleep(20)` x2, `OperationCancellation(timeout=2)`), `semantic/test_pdf_publication.py:300-310,576-680`
  (`pg_sleep(10)`, `statement_timeout='15s'`, `lock_timeout='500ms'`), `semantic/test_pdf_payload_native.py:232-235`,
  `test_pdf_projection_isolation.py:72`, `test_packet_input_snapshot.py:45`, `test_native_agent_hold.py:81`
  (`lock_timeout='100ms'`).
- `intervene/test_automated_receipts.py:55-95`: child script sleeps 10 s; `extract_run(timeout=0.3)`
  (injectable).

### 5.3 Cancellation windows and deadlines (CPU, timer based)

- `math/test_stages.py:158-235,425-440`: `grammar.deadline(0.02..0.5)` with `time.sleep(0.02..1)` inside;
  test spends the (injectable) deadline. `math/test_grammar.py:440-470`: `G.parse(..., seconds=0.3)` twice with a
  patched resolver sleeping 1 s twice (expiry cuts it; asserts `< 0.8`). `test_actual_tiny_budget_always_restores_deadline_setup_state`
  loops 20x `deadline(1e-9)` + `sleep(0.01)`.
- `math/test_workers.py:34-60`: `assert_settled` polls up to 5 s with 0.02 sleeps.
- `semantic/test_constructions.py:467,563` `parse_seconds=2|0`, `semantic/test_record_interpretation.py:452,508`
  `SearchLimits(max_seconds=0|0.5)`, `test_local_interpretation.py:136`, `test_source_views.py:910` `seconds=0.01`,
  `test_source_cli.py:305` `seconds=0.75`, `llm/test_cascade.py:140` `regex_timeout=1e-9`: precedents that
  inject a zero or tiny budget instead of waiting.
- `ingest/test_pdf_recognition.py:127` `time.sleep(reply)` (fake server latency), `:178 timeout_seconds=30`,
  `ingest/test_pdf_capacity.py:56,89` (`timeout_seconds=2|90`).

### 5.4 Other

- `tests/test_pdf_process.py:27-41` 15 s polling deadline with `wait(0.01)`; `test_cli_recipe_reporting.py:91-105`.
- `semantic/test_authored_sql.py:31`, `test_prepared_sql.py:65`, `test_database_description.py:262`:
  `pg_sleep(1)` appears inside SQL text that is *refused/parsed*, not executed.
- `tests/scripts/test_parallel_harness.py`: `time.sleep(0.15)`/`pg_sleep(0.15)` inside generated test bodies
  (4 sites) to force interleaving.

---------------------------------------------------------------------------------------------

## 6. Generated testing (Hypothesis)

Profiles: section 2.5 (`ci`: 300 examples, derandomized, no database, no deadline; set in managed runs).
`@given` sites (grep: 27 test functions, 11 files). Example budget is the profile unless stated.

| File:line | Test(s) | Override | Per-example work |
|---|---|---|---|
| `core/test_canonical.py:66,72,101,204,212` | 5 | none (300) | pure: canonical JSON bytes/decimal/float |
| `core/test_keys.py:574` | 1 | none | pure key construction on small `page(...)` |
| `core/test_locators.py:563,568,578,588,606,636` | 6 | none | pure: builds tiny renditions, `LocatorIndex`, `model_validate_json` round trip |
| `core/test_shapes.py:159,171` | 2 x `FORMS` (authored, stored) | none (300) | pure: pydantic + `jsonschema` `Draft202012Validator` (`validator(...)`) |
| `core/test_shapes.py:193-194` | 1 x 22 schemas | `max_examples=40` | `hypothesis_jsonschema.from_schema` draw + pydantic + jsonschema validation; `drawn` is `@functools.cache` (`:187-189`) |
| `core/test_tex.py:68,315,325,333,342,388` | 6 | none | pure string/TeX normalization |
| `evaluate/golden/test_sets.py:55`, `test_split.py:74` | 2 | none | pure permutations/splitting |
| `evaluate/test_equivalence.py:115` | 1 | none | pure `_seed` hashing |
| `llm/test_cascade.py:158-174` | 1 | `suppress_health_check=list(HealthCheck)`, `deadline=None` | pure regex cascade over real rendition sentences (module fixture `sentences` loads retained Normal page) |
| `math/test_property.py:121-137` | `test_generated_layer` | same settings, **no max_examples** (300) | pure CPU: each example `G.parse(latex,"any_value",macros)` on a lark/Earley grammar with sympy-backed resolver, then `print_tree`; `from_lark` strategy built once per call (`_strategy` builds `parser_for`) |
| `semantic/test_native_closure.py:530-575` | `test_generated_codec_batch` | `max_examples=16`, function-scoped fixture check suppressed | **database**: `semantic_db_engine` + `codec_binding` (fixture does a full `archive(admitter)` = `source_bundle` + `prepare_release` + `persist_release` + a realization insert) once; each example opens a connection and does one typed batch inside a rolled-back transaction |

Fresh interpreters/subprocess/file work per example: none found in the pure sites; only the native-closure
site touches a DB. Search: `@given` over `tests` and `PKG/tests`; each body read or sampled
(`test_canonical`, `test_keys`, `test_tex`, `golden/*` were sampled by signature and imports only).

---------------------------------------------------------------------------------------------

## 7. Heavy single tests, by structure

(no timing; the retained receipt `.../test-receipts/ordinary-001` is historical orientation only)

1. **`math/test_coverage.py::test_coverage_beside_s5`** (`corpus` marker, skipped when the corpus is
   absent at `conftest.py:128-138` before setup). Work: `coverage_of(78 first-pass pages)` ->
   `_run_pages(coverage_rows, pages)` (`math_support.py:376-428`): one spawn pool, up to 8 children, 78
   page tasks, each child `read_page` -> `load_page` (parses the 11.4 MB retained JSON per child process
   via `_retained_inputs`) -> `read_spans` for every math span with a 2 s default deadline. Parent then
   compares per-span statuses with `data/s5_coverage.json` and the tree/token property. Essential to the
   stated claim: the 78-page span reading and the comparison to S5; per-child archive parse is an
   implementation detail. `analyse_pages`/`analyse_all` (`conftest.py:73-75`, `math_support.py:348-350`)
   have no test consumer (search: `analyse_pages|analyse_all` over tests, only definitions).
2. **`math/test_property.py::test_generated_layer`**: single test, up to 300 CPU examples in one process,
   parser built by `G.parser_for` inside `_strategy` and again inside `G.parse` via cache; not corpus-gated.
3. **`acceptance/test_regeneration.py`** (654 lines): 4 families through `CliRunner` (in process). Each
   `retained_integrated_cli` setup (`:22-101`) copies `domains/<domain>` into tmp (statistics = 3.6 MB,
   toy = 56 KB), builds a toy PDF via `runpy.run_path(fixtures/toy/build_pdf.py)`, seeds a retained product,
   then `regenerate` runs the full prepare pipeline against a fresh semantic clone. Setups: lifecycle x2
   (statistics `acceptance-native`, toy `transfer`; `:105-393`, which invoke the CLI 6+ times), failure x2
   (`:395`, toy), diagnostic-binding x2 (`:510`, toy), repeated-preparation x1 (`:629`, statistics, runs
   `regenerate` twice with producers forbidden the second time). 2 statistics-pack setups, 5 toy setups
   (counted by call site and parametrization). Whether the statistics `prepare_release` is served from the
   `lru_cache` across these tests depends on identical bundle bytes (the copied `methods.yaml` is edited,
   `:44-60`); open question: is `methods.yaml` part of the release bundle?
4. **`schema/test_packs.py::test_hashes_are_equal_across_processes_hash_seeds_and_load_paths`** (`:61-87`):
   2 fresh interpreters, each importing `semantic.regeneration` and doing `prepare_packs` of the statistics
   pack (cold `load_pack` + `prepare_release`), different `PYTHONHASHSEED` and relative/absolute path;
   asserts equal release id and artifact digests. Essential: independent processes with different seeds; the
   in-process `lru_cache` cannot stand in. Per-child preparation is the same content twice by design.
5. **`db/test_cli_db.py`** (`:120-170`): `test_cli_subprocess_acknowledges_creation_before_failed_migration`
   runs `python -c "from corpus_structure.cli.app import main; main()" db init` as the child, with a
   reserved database and a bare template (`timeout=30`). One child, one CLI import, one failed migration.
   Other tests in that file use `CliRunner` in process (`:43-112`).
6. **`semantic/test_runtime_entrypoints.py::test_current_cli_stdio_journey_and_settlement`** (`:464-607`):
   4 modes x {DB clone via `semantic_db_engine`, `semantic_writer_engine`, `build_resubmission_case`
   (core.yaml + generated domain schema -> `prepare_release` (cache hit across modes in one worker) ->
   `persist_release` + run/task creation), one real stdio `ci mcp serve` child, anyio client journey}.
   Per-mode distinct claims: complete submission, client early exit, tool failure, cancellation; each
   asserts child group gone and no `ci-mcp-semantic` backend left in `pg_stat_activity`.
7. **`semantic/test_operation_reporting_native.py`** (375 lines, 4 tests): each persists `prepared()` (module
   `lru_cache`d report fixture) into a fresh clone, then drives in-process `cli(...)` (`CliRunner`) and an
   in-memory fastmcp `Client`; `:195-` prepares two bundles (`before`/`after`). No subprocess.
8. **`math/test_workers.py`**: structure in 4.4. The widest test is the staged-parity one (3 spawn pools +
   1 in-process read of the same Normal page).
9. **`ingest`/`semantic` PDF and CPU controls**: `test_cpu_lifecycle.py` (6 tests) and `test_cpu_execution.py`
   (10 test functions) each create a real `CPUExecutionScope` with its own pool and Manager (spawn); their grace waits are
   in 5.1.
10. **Nested pytest sessions**: `test_parallel_harness.py` and `test_test_receipts.py` (3.4). Each nested
    session loads the autoloaded plugin set, the plugin, and (for xdist cases) starts 2 workers.
11. **`test_cli_test_evidence.py`**: 31 `ci test` subprocess calls (4.1), most with a nested `uv run python
    scripts/test_receipts.py classify`.
12. **`semantic/test_review_cli_native.py`**: 15 installed `ci` invocations over 3 tests (4.1).

Prepared more than once (observed facts):
- `prepare_release` of one source bundle in several modules (cache hit only inside a process and while
  within the 8-entry LRU; section 9).
- Retained archive JSON parsed by up to 4 independent loaders per process, and again in each spawn child that
  calls `load_page`.
- Statistics pack `prepare_packs`: cold in 2 children (`test_packs.py`), in `regeneration` x2, and in
  `semantic/test_review_cli_native.py:275`.
- The same Normal/LocationScale pages read in `spike_readings` chain, `test_workers` and `llm/test_cascade`.

---------------------------------------------------------------------------------------------

## 8. Prerequisite and skip handling

Where decided:
- Collection-time: `corpus` marker -> `skip` marker added in `PKG/tests/conftest.py:122-138` (before setup, so
  no fixture runs); `skipif(shutil.which(...) is None)` (pyrefly: `core/test_method.py:232`,
  `semantic/test_scenario_ports.py:12`, `test_typed_realization.py:82`, `test_operation_call_generation.py:256`;
  linkml-lint: `schema/test_model.py:43,49`, `test_packs.py:120`); `skipif` on env opt-in
  (`semantic/test_pm2_parser_stage_native.py:42` `CORPUS_PM2_NATIVE_TEST_ASSETS`, `methods/test_gliner.py:381`
  `CORPUS_GLINER_DIAGNOSTIC`); `skipif` on platform in `test_native_auth.py` (5 sites).
- Setup-time (fixture raises `PrerequisiteUnavailable`, `scripts/test_prerequisites.py`): DB server/role/
  extension checks in `native_test_support.py:257,506-531` (called from `native_server`/templates, so decided on
  the first DB fixture a worker builds); the plugin turns it into `qualification_prerequisite` user
  properties (`qualification_plugin.py:159-176`). A missing server therefore fails each DB test's setup
  (the session fixture is retried per test) and is classified as `blocked`.
- Body-level `pytest.skip` after fixtures have already run (search: `pytest.skip(`, `importorskip`):
  - `semantic/test_characterization_native.py:1729` and `:2114`: skip if `CORPUS_PM2_NATIVE_TEST_ASSETS`
    unset. Both tests request `characterization_source` / `private_build` + `semantic_writer_engine`
    (`:34-60`, `semantic/pdf_staging_support.py:143-144`): a DB clone, release prepare, task publish and
    `publish_selected` run before the skip.
  - `semantic/test_native_documents.py:93,97` (`captured_page=True`, also `corpus`-marked): skips after
    `semantic_db_engine`, `semantic_writer_engine`, `semantic_reader_engine` and
    `prepare_operation_scenario(..., observations=True, composed=True)` have run (`:34-60`).
  - `ingest/test_pdf_recognition.py:172` (`owner()` skip inside the helper called after the test has
    already requested its local fake-server fixture, `:136-163`; exact fixture order per test not checked).
  - `semantic/test_pdf_json_publication.py:211` skip if the 558 MB witness is absent (checked first in the
    body, little prior work).
  - `tests/test_pdf_alignment.py:172,175`, `tests/test_pdf_conversion.py:31,82` (`importorskip`),
    `semantic/test_artifact_identity.py:337` (`importorskip("splink")`).
- `tests/scripts/test_native_auth.py` and `test_test_receipts.py:492,1098` platform skips inside bodies.

---------------------------------------------------------------------------------------------

## 9. Caches that span tests

Production caches that tests rely on (all per process, none persisted; each xdist worker and each spawn
child starts cold):

| Function | Cache | Key | Size | Notes |
|---|---|---|---|---|
| `semantic/prepare.py:573` `_prepare_release_cached` (fed by `prepare_release` `:539-570`) | `lru_cache` | `(SourceBundle, ResolvedDependencies, PreparationProfile, stack)` frozen dataclasses hashed by content; unhashable inputs bypass (`:567-568`) | 8 | compiler stack from `_compiler_stack()` in the key; `prepare_release` tests assert reuse and invalidation (`semantic/test_prepare.py:525-560`) |
| `semantic/contracts.py:1799` `_compile_execution_model_cached` | `lru_cache` | `(ExecutionModelInputs, compiler_version)` | 8 | |
| `semantic/contracts.py:1094` `_bound_execution_model` | `lru_cache` | `(body bytes, model_id)` | 16 | cleared by `semantic/test_invariant_failures.py:226` |
| `semantic/execution_admission.py:363,465` | `lru_cache` | stamps / frozen expectations (pglast parse) | 4 / 32 | |
| `ingest/sentences.py:56` `pipeline(config)` | `functools.cache` | frozen `SentenceConfig` | unbounded | each distinct config = separate `spacy.load("en_core_web_sm", exclude=...)`; defaults differ: `SentenceConfig()` excludes `("ner","lemmatizer")`, `AnnotationProfile` and `native_evidence` use `exclude=("ner",)` (`ingest/annotations.py:39`, `methods/native_evidence.py:51`) |
| `methods/math/grammar.py:181,227,235` and `_PARSERS`/`_FOREST_PARSERS` dicts (`:310-325`) | `cache` / dict | macro classification key | unbounded | Earley parser build is per process; `_MEMO` OrderedDict parse results (`:966-997`, `MEMO_SIZE`), tests substitute `G._MEMO` (`math/test_grammar.py:440-470`) |
| `semantic/operation_reporting.py:64,107,115`, `ontology.py:999` (`_qualified_shape_triples`), `formal_evidence.py:296,314,351,375`, `scientific_evidence.py:49,58,125,248,341`, `retained_rules.py:30,170,236,1185`, `structural_parsing.py:57,94,104,175`, `pdf_records.py:33,157,163,196`, `pdf_contracts.py:50,89,190`, `pdf_payloads.py:398,415`, etc. | `lru_cache` | mostly 0-arg or small keys | 1-64 | schema/grammar/recipe loaders; about 60 decorated sites under `src` (grep) |

Test-side caches:
- `semantic/domain_scenarios.py:659` `fixture_model(...)` `@cache` keyed by 10 scalar flags: composed model per
  (scope, unique, label_range, inlined, record_target, min/max, qualification, conditional, composed).
- Per-module `@cache` helpers building prepared releases: `native_math_primary.py:147` `pure_source_release`,
  `semantic/test_identity_resolution.py:18` `release(keyed)`, `test_semantic_reason_producers.py:36`,
  `test_record_compiler15.py:33`, `test_record_contracts.py:45`, `test_record_assertions.py:48`,
  `test_proposals.py:24` `prepared(composed)`, `test_operation_reporting.py:35,58`, `test_core_operation_calls.py:20`,
  `test_operation_call_generation.py:35`, `test_invariant_failures.py:34`, `test_projection_analysis_products.py:178`,
  `test_record_policy_products.py:22`, `test_reference_positions.py:23`, `test_ontology.py:782`,
  `methods/primary_reading_fixture.py:24`, `methods/test_m1_producer.py:38`, `methods/test_record_assembly.py:41`,
  `evaluate/test_record_references.py:36`, `evaluate/test_record_alignment.py:46`, `evaluate/test_semantic_alignment.py:22`,
  `semantic/primary_formal_fixture.py:15`, `semantic/test_pdf_candidate_capture.py:32`.
- `math_support._retained_inputs` (`lru_cache(1)`), `archived_source._archive` (`cache`), `llm/conftest.data`/`page_view`
  (`:80,111`), `core/test_shapes.drawn`.
- 52 module-scope fixtures (grep), e.g. `prepared` in `semantic/test_formal_evidence.py:29` imported by name into
  `semantic/test_cpu_execution.py:24`, `test_cpu_lifecycle.py:16`, `test_cpu_annotations.py:13`,
  `test_formal_sources.py:13`, `methods/test_formal_evidence.py:10`, and similar `prepared` re-exports for
  `test_record_consumers`, `test_characterization`, `methods/test_native_evidence`,
  `methods/primary_reading_fixture`; a re-exported fixture is a separate module-scope instance per importing
  module, so each module calls `prepare_release` again and relies on the process-wide LRU for reuse.

Tests that clear caches (search `cache_clear|cache_info`): `semantic/test_prepare.py:528,559`
(`_prepare_release_cached`), `semantic/test_execution_release.py:121` (same), `semantic/test_operation_reporting.py:532`
(`reports._report_model`), `semantic/test_invariant_failures.py:226` (`_bound_execution_model`),
`semantic/test_prepared_graph_candidates.py:30` (`_qualified_shape_triples`). A clear drops all entries for
every later test in the same process, not only the one under test.

Validity premises (facts / open):
- `_prepare_release_cached` returns the *same* `PreparedRelease` object to every caller (identity asserted at
  `test_prepare.py:539`). Reuse is valid only if consumers never mutate it; the repository comment on math
  fixtures says session products are read-only (`math/conftest.py:24-26`), but no analogous statement or
  freezing for `PreparedRelease` was checked. Dataclasses are frozen for inputs; the `PreparedRelease`
  mutability was not examined (open).
- LRU size 8 vs the number of distinct bundles in one worker (semantic-1 small bundles, `core.yaml`
  characterization inputs, semantic-2 trusted inputs, statistics pack, pack variants): eviction is possible;
  not quantified.
- `fixture_model(...)` keyed on scalars returns shared model objects (open: mutation).

---------------------------------------------------------------------------------------------

## 10. In-repository precedents for cheaper realizations (facts, no recommendation)

- In-process orchestrator tests next to nested-session ones: `test_test_receipts.py:947-1000`
  (`test_cli_watchdog_overrides_and_cancellation`) monkeypatches `run_python`/`run_rust`/`source_identity`
  and exercises `main`, versus `child(...)` nested sessions for real failures.
- Injected tiny budgets instead of waiting: `grammar.deadline`, `parse_seconds=0`, `SearchLimits(max_seconds=0)`,
  `regex_timeout=1e-9`, `extract_run(timeout=0.3)`, `open_pm2_worker(..., startup_timeout_seconds=0.05)`,
  `renewal_statement_timeout_seconds=0.03`.
- Inline executor in place of a spawn pool: `math/test_workers.py:230-262`.
- Observation of real spawn through a wrapped context rather than an additional child:
  `semantic/test_pdf_lifetimes.py:23-50,106-133`.
- Affinity mark for a shared preparation chain: `conftest.py:27-37` plus its pure-collection test
  `test_parallel_harness.py:324-363`.
- `ci test` `validate-pytest` spawns two processes only to screen arguments, while the same function
  `validate_pytest_args` is a pure Python function in `scripts/test_receipts.py:1536`.
- Single `semantic_head_template` per worker with clones (DTA-024's subject; ADR-0032), with the same
  per-worker shape as the math chain.

---------------------------------------------------------------------------------------------

## 11. Limits and open edges

- No runtime observation: scheduling consequences of `loadgroup` are read from installed source; actual worker
  counts, per-worker module distribution and fixture rebuild counts are not measured.
- Test counts are grep counts of `def test_` and decorators, not collected node ids.
- Section 4 call-site counts assume linear control flow in each test; loops (`for args in (...)`) were counted
  as listed.
- Not read in depth: `tests/scripts/test_native_auth.py` internals (fault lane), `test_pdf_chandra.py`,
  `methods/test_gliner.py`, `ingest/test_pdf_recognition.py` beyond cited lines.
- DB-side per-worker template, clone leases and sweep are intentionally not mapped (database mapper).
- Unresolved: whether `check`/`py-test` recipes (`justfile:14,155`) have current callers; whether xdist starts
  idle workers for tiny selections; mutability of `PreparedRelease` and `fixture_model` outputs; whether
  `methods.yaml` is part of the statistics release bundle in `test_regeneration.py`.
