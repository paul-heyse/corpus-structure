# Evidence maps for the test architecture and efficiency review

**Question.** What does the test system actually do when it prepares, schedules and runs tests,
who owns its scenarios and refusal evidence, and which library and PostgreSQL capabilities could
carry cheaper preparation? These maps were prepared as inputs to the
[design review of test architecture and efficiency](../../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md)
(2026-11-12), which consumes test audit publication `cf24c0e80`.

**Standing.** Inputs, not conclusions. The review is the judgment; where it disagrees with a map,
the review governs. Known errors the reviewer found are listed below so the maps are not reused
uncorrected.

**How they were produced.** Read-only delegated workers at `main` `784d86f11`, 2026-11-12: three
`code-mapper` contributors and one `library-research` contributor. No tests, collection, database
operations, provider calls, benchmarks or timing were run. One worker imported
`corpus_structure.cli.app` and called `core.schemas.SCHEMAS()` in the project environment to read
loaded-module and schema counts. Library versions checked: pytest 9.1.1, pytest-xdist 3.8.0,
Hypothesis 6.170.12, SQLAlchemy 2.1.6, psycopg 3.3.6, PostgreSQL 18.6; PostgreSQL source citations
are from the 18 branch head, not the 18.6 tag.

| File | Covers |
|---|---|
| [native-lifecycle-map.md](native-lifecycle-map.md) | Template, clone, policy replay, sweep and lease ladder; committed-scenario fixtures and consumers; rollback-only families and their validity premises; pure SQL-function tests; cluster configuration; teardown |
| [process-scheduling-map.md](process-scheduling-map.md) | The `ci test` route, worker and session startup, xdist scheduling, process boundaries, real-time waits, Hypothesis usage, structurally heavy tests, skips, caches |
| [ownership-evidence-map.md](ownership-evidence-map.md) | Support owners and cross-module imports, the `private_source` contract, large builders, assembly copies, refusal idioms with intended guard reasons, absence assertions, evidence-class switches, CPU lifecycle seams, superseded machinery |
| [library-capabilities.md](library-capabilities.md) | xdist cross-worker sharing and scheduling, pytest fixture and subtest semantics, PostgreSQL 18 database copy and what clones carry, disposable-cluster settings, transactional isolation limits, Hypothesis profiles |
| [historical-receipt-summary.md](historical-receipt-summary.md) | Per-phase time derived from one retained full-lane receipt of 2026-11-07 at older source (`2b11a881`, 16 workers, 5,070 tests); orientation only, not a current measurement |

**Corrections recorded by the review** (its §13):

- `library-capabilities.md` says no import in the test trees triggers duplicate module objects
  under `--import-mode=importlib`. That is wrong: test modules in non-package directories are
  imported by absolute name (for example `from ingest.test_annotations import …`,
  `from evaluate.test_operation_assessment_native import …`) and load twice.
- `process-scheduling-map.md` says the math preparation chain re-parses the 11.4 MB retained
  archive in every spawned child. Only the coverage worker does; the staged chain ships page
  content.
- `ownership-evidence-map.md` reports no importer for `tests/fixtures/support.py`; it is loaded
  by path from `tests/fixtures/test_fixtures.py`. Its note about raw outputs under a scratchpad
  `work/` directory refers to files that were not retained.

**Result and consumer.** No finalized record: the maps informed the review and carry no
independent result. They stay while that review has open findings.
