# Python parallel execution configuration

**Tested 2026-11-06:** bounded configuration controls passed with Python3.14.10,
pytest9.1.1 and pytest-xdist3.8.0 on the current Linux workstation. This evidence supports
TR-10's test runner configuration; it does not complete the required functional union.

The default pytest invocation and `just test-all` use16 workers and the library's `loadgroup`
scheduler. Math tests share the `math_preparation` group, keeping their session preparation
and nested page pool in one process. This avoids replicating shared preparation; it does not
claim that each individual corpus case previously ran16 times.

The eight actual shared-cluster authentication fault nodes belong to the separate
`just test-native-faults` lane: the existing enable flag, `-n 0` and
`-m shared_cluster_fault`. The normal lane excludes that marker. A collection guard rejects
fault nodes under parallel execution and mixed selections even in a serial invocation.
These lanes must run consecutively. No shared PostgreSQL configuration was changed.

## Compatible dependency pair

Context7 was queried first for pytest-xdist scheduling and pytest9.2 node identities.
[PyPI](https://pypi.org/project/pytest-xdist/3.8.0/) supplies current stable xdist3.8.0.
Its [loadgroup implementation](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py)
writes `item._nodeid`. [pytest9.2](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/nodes.py)
reads a structured `_id` instead, so this combination silently ignores grouping.
The four early group-flag controls passed their limited assertions while their raw reports
show the shared group split between gw0/gw1. They do not establish grouping.
[pytest9.1.1](https://github.com/pytest-dev/pytest/blob/9.1.1/src/_pytest/nodes.py) retains the
compatible identifier and the existing faulthandler exit-on-timeout setting. The exact pytest
pin was moved from9.2.0 to9.1.1; pyrefly1.4.0 and other declared dependencies were preserved.
No private-node adapter or custom scheduler was added.

## Bounded final result

The final command ran only newly authored cases:

```sh
uv run python scripts/test_receipts.py run --python-only \
  --out-dir build/test-receipts/qualification/parallel16-compatible-20261106 \
  -- docs/design_review/evidence/2026-11-06_parallel-test-execution/test_parallel_smoke.py \
  -k test_compatible_pair
uv run python docs/design_review/evidence/2026-11-06_parallel-test-execution/summarize.py
```

Both passed. [The summary](compatible-summary.json) records32 parallel items across16 distinct
worker IDs/PIDs,16 overlapping call intervals, and eight same-group items on one worker.
Two distinct owned bare PostgreSQL clones were acquired concurrently on different workers;
both have complete item-bound native contexts and normal PgAdmin teardown. This is a two-clone
functional control, not qualification of sixteen simultaneous native fixture families or a
capacity claim for the existing PostgreSQL connection envelope.

The final raw reportlog has40 call reports with their scheduler suffixes. Sixteen worker
collection manifests supply explicit execution-to-canonical mappings. Classification retains
40 canonical identities, including literal `@` characters in parameter IDs, and complete native
associations. The classifier reports no stream errors or worker losses. Raw streams remain
unchanged; identity normalization occurs only in the derived classification. A further read-only
classification against the actual gw0 worker manifest passed all40 canonical required identities
with no unresolved items; its result is retained in `raw/required-union-classification.json`.

Collection-only commands selected the eight real fault nodes and rejected parallel fault or
mixed serial selections before any test body. A newly authored serial-lane control passed under
the initial pytest9.2 environment; its historical version is retained explicitly. The root runs
final static maintenance and qualification accounting. `just ready` passed after the dependency
changes. No pre-existing successful product cases, full suite, old fault cases or Rust tests ran.

## Retained attempts

`raw/` contains unchanged copies of every receipt and command classification:

- `parallel16-smoke-20261106`: failed startup because an evidence-only run bypassed the descendant
  conftest's checkout temp-root setting and reached a foreign-owned `/tmp/pytest-of-paul`.
  The new common root conftest now establishes checkout scratch before xdist starts.
- `parallel16-smoke-20261106-final`: failed strict collection because the evidence-only module
  did not inherit the descendant `db` marker declaration. The shared marker is now in pyproject.
- `parallel16-smoke-20261106-run3`:32 passed under pytest9.2, with16 workers/two native clones;
  grouping was ineffective, so this remains historical concurrency evidence only.
- `parallel-group-identity-20261106`: four weak group-flag assertions passed under pytest9.2;
  raw reports independently reveal that grouping split across two workers.
- `parallel-serial-lane-20261106`: one new pure serial-selection case passed under pytest9.2.
- `parallel16-compatible-20261106`: final40 newly authored cases passed under the compatible pair.

The earlier successful product receipt, interrupted run and original4762-node selection (1390 remain pending after the operator stop and failed-node repair)
remain at the owning TR-10 plan. This probe neither supersedes them nor establishes full-series
qualification. Raw evidence is retained through the existing `raw/**` Git LFS rule.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Test runner configuration**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Bounded sixteen-worker configuration and canonical receipt identity](records/tests.parallel16-configuration.json) | TR-10 | passed | TR-10 | 2026-11-06 |
<!-- evidence-index:end -->
