# pytest

**Realization assessed:** pytest 9.2.0.
**Researched:** 2026-10-29 by the R2 cluster.

There is no overview page for pytest. The research used Context7, which documents 9.1.1 (one release
behind), together with the installed source (`_pytest/faulthandler.py` and `_pytest/junitxml.py`).
pytest-timeout was assessed from its documentation only, since it is not installed. A route probe ran
deliberate passing, skipping, failing and hanging cases
([evidence](../../../design_review/evidence/2026-10-29_library-leverage-postgres-migrations/README.md)).

## Reusable opportunity types

<a id="pytest-outcome-reporting"></a>

### `pytest/outcome-reporting`

**APIs:**
- `--junitxml` (default `junit_family=xunit2`) writes per-test outcomes, with skip reasons inside
  `<skipped>` elements (probe-observed).
- `-r` summary characters.
- `faulthandler_timeout` combined with `faulthandler_exit_on_timeout` (both present in 9.2.0) dumps
  tracebacks for every thread and then calls `_exit(1)`.

**Hang behaviour (probe-observed):**
- the run exits with code 1;
- the hung test is named in the traceback;
- the tests after it do not run;
- **no JUnit file is written**.

**pytest-timeout (documented):**
- The `signal` method fails only the timed-out test, keeps running, and leaves the JUnit report
  intact. It uses `SIGALRM`, so it conflicts with any code under test that also uses `SIGALRM`.
- The `thread` method calls `_exit(1)` and writes no JUnit file.

**Comparative review correction (2026-10-29).** The `signal` method does more than conflict with
code under test that runs its own `SIGALRM` deadline. If that code ends its deadline with
`setitimer(ITIMER_REAL, 0)`, the reset cancels pytest-timeout's outer timer. The test then runs with
no timeout at all, silently. This comes from reading the deadline code; it was not probed with
pytest-timeout installed.

**Streaming alternative (pytest-reportlog, from upstream source; not installed).**
- `--report-log=<path>` writes one JSON line per `TestReport` and `CollectReport`, flushes after each
  write, and ends with a `SessionFinish` record.
- Combined with faulthandler-exit, a hang keeps every flushed completed outcome. A call-phase
  hang also keeps the item's setup report. It does not supply a collected-node manifest or
  phase-start events: pytest serializes `CollectReport.result` as null. Public collection and
  runtest hooks must supply exact selection and execution attribution where needed.
- A missing `SessionFinish` marks an interrupted run.
- This removes the limit that a missing JUnit file loses every outcome.

**What remains with the caller:**
- Mapping outcomes to a qualification vocabulary.
- Distinguishing process failure, incomplete phases, collected unexecuted cases and missing reports.
- Recording the provider context of the run.

## Applicability at source `d739b88`

<a id="applicability-cbo-011"></a>

### CBO-011 — qualification outcome classification: **fits with conditions**

**Opportunity:** [CBO-011](../../codebase/engineering-workflows.md#cbo-011) (diagnosis:
[DTA-003](../../../design_review/test-audit/execution-and-qualification.md#dta-003)).

- **Outcomes.** `--junitxml` with `-rA` records per-test outcomes and skip reasons faithfully.
  Qualification needs explicit prerequisite/applicability metadata; a reason prefix alone is
  insufficient. Preserve raw skips and never turn a skipped required obligation into a pass.
- **Hangs.** Built-in `faulthandler_exit_on_timeout` makes a hang observable, but loses the JUnit
  file and every later outcome.
  - pytest-timeout's `signal` method **conflicts with the math grammar's `SIGALRM` deadline**
    ([CBO-023](../../codebase/consumers-and-operations.md#cbo-023)).
  - Its `thread` method behaves like faulthandler.
  - A credible complete option is faulthandler-exit plus a route that treats a missing JUnit file as
    `failed`, naming the hung test from the traceback dump.
  - Narrower per-test bounds would need a wrapper that runs each test in its own process.
  - **Comparative review (2026-10-29):** prefers pytest-reportlog streaming plus faulthandler-exit
    over the missing-JUnit rule ([review](../../reviews/engineering-workflows.md#cbo-011)).
- **Hypothesis replay.** See [hypothesis](../hypothesis/README.md#applicability-cbo-011).
- **Not assessed here.** Nextest's `--no-tests=pass` is outside these libraries.

## Coverage limits

- pytest-timeout was not installed or exercised.
- Context7 lags the installed release by one minor version.
