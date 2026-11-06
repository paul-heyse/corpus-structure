# Fatal-worker shutdown policy

**Implemented and bounded Tested,2026-11-06.** The project pytest defaults now set
`--max-worker-restart=0`. The ordinary `-n auto` and `--dist=loadgroup` selections
remain. A native worker crash ends that attempt with failed/incomplete evidence;
remaining obligations can be selected explicitly from the existing receipt workflow.
This policy does not repair or conceal the original CPython GC SIGSEGV.

The root captured the original controller and original/replacement worker stacks
in `pid-2682226.txt`, `pid-2682293.txt` and `pid-2953984.txt`. They show the controller
waiting for an xdist event and sampled workers waiting for the next prefetched item.
`interruption.json` records the authenticated SIGINT of that stalled pytest process.
The completed original/replacement collection manifests contain identical selected
IDs, aliases and affinity groups. These observations establish the stalled attempt;
they do not prove the native fault's corrupting component or every scheduler detail.

## Selected native capability

The [official pytest-xdist crash documentation](https://pytest-xdist.readthedocs.io/en/stable/crash.html)
documents disabling automatic replacement with this option. The installed pinned
pytest-xdist3.8.0 `xdist/dsession.py::DSession.worker_errordown` checks the zero limit
and calls `triggershutdown`; its replacement branch is not taken. That observed
implementation and the real controls below support this selection. No custom
scheduler, restart loop, skip, global serialization or dependency change was added.

The single default policy owner is root `pyproject.toml` pytest addopts. Existing
isolated harness controls already passed this option explicitly; they had not
exercised the root default. The new regression loads the actual root configuration,
uses two workers for a bounded fatal-process scenario, and supplies no restart CLI
override. One grouped test exits natively, six grouped bodies remain queued, and an
independent test can complete. The assertions inspect effective configuration and
worker-ready events, not terminal prose that quiet output can suppress.

## Actual controls

**passed**,2026-11-06, exit0 and three outer test cases:

```sh
QUALIFICATION_CONTROL_RECEIPTS=/home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-gs120/qualification/scheduler-stall/probe-receipts uv run pytest -n auto tests/scripts/test_parallel_harness.py -k 'project_policy or (real_distributed_failure_boundaries and loss)' -q
```

`policy-controls003.log` retains the outer result. `policy-controls003.json` pins
the source/configuration and exact retained child receipt paths. The three cases
are the root-policy native exit plus the existing serial and two-worker loss
controls. The child failures are intentional, and remain classified failed or
incomplete. They are not reported as passing test runs.

For the new root-policy control, the actual effective restart limit is0, the
worker count is2 and distribution isloadgroup. Exactly gw0/gw1 become ready,
one worker loss is retained, all six queued nodes are `not_run`, the attempt
returns nonzero naturally without its watchdog interrupting it, and no owned
process group remains after cleanup. The first probe's outer assertion failed
because quiet output omitted a narrative shutdown message. That failed log and
child receipt are preserved; the replacement assertion checks the effective
option and actual worker events instead. The second new-probe run passed, and
the final three-case selection passed after retaining effective policy metadata.

**passed:** scoped `uv run ruff check tests/scripts/test_parallel_harness.py --quiet`
and `git diff --check -- pyproject.toml tests/scripts/test_parallel_harness.py`.
No production source changed; `serve/review_bundle.py` remains SHA256
`f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928`.

**not_run here:** full functional qualification, native authentication fault lane,
global typing/hygiene/maintenance or commits. The root owns their final source and
required-union applicability. The [separate interpreter investigation](../interpreter-crash/README.md)
owns the original SIGSEGV diagnosis/reproduction; its cause remains unresolved by
this shutdown-policy change.
