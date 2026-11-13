# Test-audit refresh: cost map from stored test results — 2026-11-13

**Question.** Where does the time of the test scope go, for a full run and for the focused runs
used during implementation? The [test audit](../../test-audit/README.md) refresh of 2026-11-13
uses the answer to direct static review and to support its numerical statements.

**Consumer.** [Test audit, execution and qualification](../../test-audit/execution-and-qualification.md#measurements)
and the findings that cite a run id. No record is finalized: this is a reading of existing
receipts, not a new measurement campaign.

## Method

No test, build or database operation was run. `cost_map.py` (stdlib only) reads the managed
results that `uv run ci test` already stores under `build/ci/<id>/`: `manifest.json`,
`ordinary/pytest.process.json` and the pytest-reportlog file `ordinary/reportlog.jsonl`, which
holds a duration, start, stop and worker for the setup, call and teardown phase of every test.

```console
uv run python cost_map.py full build/ci/2e2a0e30adfb435ba5bdf62d0d37de96   > raw/full-2e2a0e30.md
uv run python cost_map.py full build/ci/e332a3ef0884454988beaad5af1166b7   > raw/narrowed-e332a3ef.md
uv run python cost_map.py narrowed build/ci 60                             > raw/narrowed-last60.md
```

`build/ci/` is a local, untracked store; the three outputs under `raw/` are the retained copy.
Python 3.14.10, run on 2026-11-13.

## Conditions and limits

- **Run `2e2a0e30…`** is the latest passed full run: 2026-11-10, 16 xdist workers, 6,025 ordinary
  tests plus 8 fault-lane tests, Hypothesis `ci` profile. It predates the declared-data-operations
  tests, none of which are in it.
- **Run `e332a3ef…`** is the 442-test closeout union of the declared-data-operations plan:
  2026-11-13, 6 workers, narrowed.
- **The last 60 passed narrowed runs** are from 2026-11-12 and 2026-11-13 with 1 to 16 workers.
- The workstation was shared with other sessions during all of these runs, so durations carry
  uncontrolled load. Treat them as the order of magnitude under ordinary development conditions,
  not as a benchmark. Nothing here measures a speedup.
- A phase duration says where time was spent, not why. Attribution to a cause comes from source
  reading in the audit, and is labelled there.
- "Worker-seconds" is summed phase time across workers. Wall time is the managed result's start
  to settlement.

## Results

Full run `2e2a0e30…` (`raw/full-2e2a0e30.md`):

- 1,503 s wall; test phases span 1,428 s; 21,977 worker-seconds, 96% of the capacity of 16
  workers over that span. The run is bound by total work, not by idle workers.
- Call 13,484 (61%), setup 7,833 (36%), teardown 660 (3%) worker-seconds.
- Setup is concentrated: 4,922 tests set up in under 0.05 s; 198 tests take over 15 s each and
  total 5,989 s; 137 take 5–15 s and total 1,436 s.
- `semantic/` holds 16,481 worker-seconds (75%).
- 29.5 s pass between pytest start and the first test phase, and 16.2 s between the last phase
  and process exit.

Closeout union `e332a3ef…` (`raw/narrowed-e332a3ef.md`):

- 504 s wall on 6 workers; 2,636 worker-seconds.
- `semantic/test_domain_operations.py`: 888 worker-seconds over 35 tests, 864 of them in the call
  phase.
- `semantic/test_data_operation_storage.py`: 416 s setup against 44 s call over 26 tests.
- All `test_data_operation_*.py` files together: 641 s setup against 89 s call.
- The largest single setup on each worker is 43–68 s.

Narrowed runs (`raw/narrowed-last60.md`):

- Wall time minus the span of test phases has a median of 7.5 s (4.9–17.3 s): about 3.4 s from
  pytest start to the first phase and about 3.4 s after the last phase.
- A run that touches the database adds one long first setup per worker. Run `6a6894c8…` is one
  storage test on one worker: 104.5 s wall, of which 93.3 s is that test's setup.
