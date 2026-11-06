# Numerical result invariants

**Tested, 2026-11-06:** bounded Python contracts and exact native numerical blocks.
Complete native contribution admission and event fitting under the combined new
migration remain **not_run** in this slice; the integrating coordinator owns them.

The existing `validate_local_interpretation_report` owner now checks the numerical
request/result after custody seals have been validated. The native source-contribution
owner implements the same boundary in its existing local-report block. No helper
operation, lifecycle, solver replay, or rescore of priors is added.

Completed local products require unique decision/candidate populations, compatible
factor axes and cardinalities, declared computation dependencies, finite log values
or explicit negative-infinity hard zeros, exact requested marginal/event membership,
unit-interval probabilities, normalized marginals, and complete coherent assignments
within hard support. Displayed alternatives preserve their actual probability mass:
only a complete positive-support display must sum to one. Log potentials and the
log partition may legitimately be negative. Noncompleted outcomes retain their
request and diagnostics but cannot carry probabilities or exact-support claims.

Operation-event fit results enforce status, parameter and prediction coherence in
Python. Native fitting additionally rejects explicit JSON null algorithm numbers,
invalid numeric prediction probabilities, and fitted probabilities under a nonfitted
status. Existing source-frame, C-pass, population, digest and protected-read guards
remain in place. This changes result validity, not fitted labels or probability standing.

The supplied fixture repair also freezes the actual source-view key, authenticated
logical source pin, and both independently fixed native cell scopes/anchor IDs, with
explicit unconstrained auxiliary endpoint fields. Exact head/tail expectations,
the two positive/two reversed-negative events, and all forgery/protection tests remain.
The provided native bigint→integer JSON-index correction is included.

## Checks

- **passed:** `pytest` with `-n auto` on `test_local_interpretation_reports.py`,
  `test_local_interpretation.py`, `methods/test_local_interpretation.py`, and
  `evaluate/test_operation_fitting.py`: 55 tests, final `raw/tests003.log`.
- **passed:** scoped `pyrefly check`, zero errors (`raw/types003.log`).
- **passed:** scoped `ruff check` and `git diff --check` (`raw/lint004.log`).
- **passed:** `rollback_controls.py` compiled both owned SQL files and ran exact
  numerical blocks as temporary functions in a rollback-only PostgreSQL transaction.
  One valid local product with negative logs and truncated display and one valid fit
  were accepted; seven malformed local products and eight malformed fit products
  were rejected. Final receipt: `raw/rollback004.log`.
- **not_run:** full new native admission/fitting tests. New resealed-forgery controls
  are in `test_contributions_native.py` and `test_operation_fitting_native.py` for
  the coordinator's combined migration. Current deployed old SQL is not relabelled
  as testing these new branches.

The rollback control uses the exact numerical blocks extracted from the production
SQL owners. It does not exercise their enclosing source custody or protected database
write lifecycle. Its successful controls establish only the numerical boundary stated
above. Earlier bounded receipts, including initial formatting diagnostics, are retained.

Commands used the main checkout interpreter and site packages with this worktree's
`PYTHONPATH`, without synchronizing an environment:

```sh
BASH_ENV= PYTHONPATH=/home/paul/corpus-structure-wce-numerical/python/corpus-structure/src \
  /home/paul/corpus-structure/.venv/bin/python \
  docs/design_review/evidence/2026-11-06_wce-numerical-contracts/rollback_controls.py
```

The same interpreter/PYTHONPATH runs `-m pytest ... -n auto`; scoped typing uses
`-m pyrefly check --site-packages-path /home/paul/corpus-structure/.venv/lib/python3.14/site-packages`
and `--python-interpreter-path /home/paul/corpus-structure/.venv/bin/python`.
