# BEP audit repair evidence

BEP-E08 CPU teardown checks on 2026-11-12, isolated worktree
`/home/paul/corpus-structure-bep-lifecycle`, branch `bep-audit-lifecycle`, baseline
`c7ea2ef70`. CPython 3.14.10 and editable product imports resolved from this worktree.
No GPU, model, book or database execution was selected.

## Integrated CPU checks · 2026-11-12

**passed**: `uv run ci test --workers 1 --json -- python/corpus-structure/tests/semantic/test_cpu_execution.py python/corpus-structure/tests/semantic/test_cpu_lifecycle.py`,
18 selected/18 passed, managed result `27f55c0d6f1e4552b28cd529887ca8fe`, requested/actual workers1/1,
in main after the integration correction below. Custody settled; result held.
[Retained ordinary lane](../2026-11-12_cli-27f55c0d6f1e4552b28cd529887ca8fe/README.md).
Scoped `uv run ruff check --no-fix` and `uv run pyrefly check` against the CPU implementation
and lifecycle tests **passed**. Complete assembled application/GPU/provider qualification remains open.

Independent source review found synchronous `CPUHandle.cancel`, parent Event reads and admission's
Array lock could block before reaching bounded close. Parent checks now use their logical closed
fence; cancellation signals without waiting and retries pending cooperative flags through existing
retirement/admission progress. Admission bounds lock acquisition and restores temporary bytes on
failure. Native controls exercise cancel, collect and admission before close after worker death.
The abandoned Array-lock case retires successfully; the abandoned stop-Event case reports bounded
unproven cleanup with retained credits rather than claiming a blocked helper retired.

Earlier isolated source **passed17/17**, `8101859db3f04f15bc85957d120daa66`,
[retained ordinary lane](../2026-11-12_cli-8101859db3f04f15bc85957d120daa66/README.md).
It precedes this integration correction and is not final-source qualification. Its scoped Ruff,
format and Pyrefly checks also passed for that source.

The normal owner gives five seconds of cooperative grace and five further seconds for death
confirmation, including scope/native lock acquisition. Native submit runs outside the scope lock;
in-flight submissions and CPython 3.14.10's actual worker dictionary remain owned through close.
The native closer fences admission/captures the manager under its native lock, then invokes the
public shutdown or kill API. Late additions to the owned worker dictionary stay visible during
forceful cleanup. Parent cancellation fences are immediate. Cooperative stop signalling
has a bounded helper; logical cancellation uses nonblocking Array signalling, so abandoned IPC locks cannot block the caller.
Credits retire only after processes, native manager, submissions and cleanup helpers retire;
otherwise close reports a terminal honest failure and retains the ownership and failure.
Discarding close does not collect results or invoke a caller activity callback.

Native controls cover an initializer ignoring stop/SIGTERM, cooperative stop, a failed worker
with a SIGTERM-ignoring sibling, a third submission blocked behind the broken manager lock,
workers exiting while holding cancellation or stop locks, credits retained at actual kill,
independent logical cancellation/generation reuse, and primary failure preservation.
The abandoned-lock control intentionally receives a bounded cleanup failure with no live owned
worker processes; its stop helper remains blocked, which is reported rather than relabelled retired.

## Additional preserved setup failure

**failed**: initial six-control development selection (then five selected) produced
`0e615339ff7344a3907bcb1a9dce635c`, four passed/one failed, with settled custody and established
cleanup. The third-submission setup observed the child exit but the native manager did not
enter broken cleanup within its 30-second setup deadline.
[Retained failed ordinary lane](../2026-11-12_cli-0e615339ff7344a3907bcb1a9dce635c/README.md).
The result is held; no recovery or outcome change occurred.

Selected-source inspection found `ProcessPoolExecutor.submit` wakes its manager before dynamic
spawn. The manager can rebuild its sentinel list before that newly spawned process is registered.
The corrected control waits for actual worker exit, explicitly wakes the native manager, then
requires the actual broken-manager lock state before testing the concurrent third submission and
normal close. This is deterministic failure setup, not a replacement for teardown.
The focused corrected control passed `7948fccfbcff4acba6345585a32f8662`; the complete final-source
selection above includes that control. Earlier development passes `63ca0d9b97f64416a46aa4a33bd7a583`
(16 selected) and `454d6fda9226478e9fe8b1e089190918` (six selected) retain their original source scope.

## Prior implementation checks

These passes precede the subsequent submit-versus-close repair. They keep their original
source scope and do not qualify the later native submission/worker-registry changes.

- **passed**: `uv run ci test --workers 1 --json -- python/corpus-structure/tests/semantic/test_cpu_execution.py python/corpus-structure/tests/semantic/test_cpu_lifecycle.py`,
  15 selected/15 passed. Managed result `3fdca360ce47407796ab9aab5564bc05`, custody settled,
  cleanup established. [Retained ordinary lane](../2026-11-12_cli-3fdca360ce47407796ab9aab5564bc05/README.md).
  This run precedes only whitespace and test containment/assertion edits covered below.
- **passed**: `uv run ci test --workers 1 --json -- python/corpus-structure/tests/semantic/test_cpu_lifecycle.py`,
  final four selected/four passed. Managed result `eced76a71511464c9484f1f9ec589336`,
  custody settled, cleanup established. [Retained ordinary lane](../2026-11-12_cli-eced76a71511464c9484f1f9ec589336/README.md).
- **passed**: scoped `uv run ruff check --no-fix`, `uv run ruff format --check` and
  `uv run pyrefly check` against `cpu_execution.py` and `test_cpu_lifecycle.py`.

Native controls cover a hung initializer ignoring SIGTERM, cooperative stop, a failed worker
with a SIGTERM-ignoring sibling, independent logical cancellation/generation reuse, and retained
credits plus primary exception preservation when physical retirement cannot be confirmed.
An unproven close is a terminal honest failure; repeated close reports the retained failure and
keeps credit, without claiming recovery. Complete integrated qualification belongs to the coordinator.

## Preserved failed attempt

**failed**: the same two-file command first produced result
`4692c11b2def4e29933879ea020e519d` (15 selected, 14 passed, one failed). The original
broken-worker test waited for a `BrokenProcessPool` future before invoking close and reached
its 30-second timeout. The corrected control observes native worker death, then exercises normal
close with cleanup in `finally`. This failure is not replaced by the later passes.

`uv run ci results hold 4692c11b2def4e29933879ea020e519d --json` protected the result.
Its metadata remains custody-unsettled; no recovery was performed. Promotion using
`uv run ci evidence retain 4692c11b2def4e29933879ea020e519d --role ordinary --for BEP-E08 --json`
was **blocked**, reporting `evidence promotion requires established custody; inspect the managed result`.
The original was left unchanged in the worktree before its raw archive was preserved for worktree removal.

A root-authorized byte-for-byte snapshot is preserved at
`raw/failed-4692c11b2def4e29933879ea020e519d/`, including all 16 original files and hidden metadata.
[Snapshot manifest](failed-snapshot-manifest.json) records each relative path, byte count and SHA-256;
copy verification compared every file with its original bytes. This is a **raw unsettled snapshot**,
not accepted native evidence and not an importable managed receipt. Any copied `.owner.json`,
lease or hold file is historical raw data, never current ownership in the receiving checkout.
Neither the original outcome nor custody was changed, recovered, promoted or finalized.

All nine isolated managed-result directories are additionally preserved byte-for-byte under
`raw/worktree-managed-history/` before removing the temporary checkout.
[History manifest](worktree-history-manifest.json) records 137 files with sizes and SHA-256.
These are raw historical snapshots, not importable managed receipts or live custody; the separately
retained records above preserve their own accepted scope. No failed/unsettled outcome was changed.

`raw/isolated-source/` retains the exact CPU implementation and lifecycle tests from the isolated17-case pass before main integration corrections.
