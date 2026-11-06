# Native pytest worker crash investigation

**Partial,2026-11-06.** Read-only diagnosis of the actual SIGSEGV in final broad receipt
`build/test-receipts/qualification/20261106T211956Z-2681505`. No product, harness, dependency,
toolchain or host setting was changed. After coordinator GO, the exact30-node history replay
passed in one fresh process; the original crash is not reproduced or explained. The coordinator
owns acceptance and final-source applicability.

## Established facts

- Worker `gw0`, PID2682283, had started228 nodes before dying in setup of the final parameter of
  `test_exact_bound_literals_compile_and_nearby_unknown_literals_refuse`. The rule assertion/body
  had not run. Its module fixture was preparing the statistics pack.
- Python's faulthandler reports garbage collection during LinkML's conversion of PyOxigraph
  quads to triples in `canonicalize_rdf_graph`, called by ontology artifact preparation. This is
  the triggering allocation location, not proof that RDF canonicalization corrupted memory.
- `addr2line -f -C -e <actual-python> 0x1800600 0x1abda0a 0x1abf3ef` resolves the crash to
  `visit_decref`, `dict_traverse.warm`, `gc_collect_main.warm`. GC was traversing dictionary
  references. The available trace cannot identify the bad referent or its creator.
- The actual executable is the uv CPython3.14.10 build. Installed distributions are
  LinkML-runtime1.12.1, PyOxigraph0.5.13, RDFLib7.6.0, PyArrow26.0.0,
  Pydantic2.14.1/pydantic-core2.50.1, pytest9.1.1, pytest-xdist3.8.0, execnet2.1.2.
- There is no available system coredump. The coordinator's contemporaneous kernel journal
  has NVIDIA API mismatch warnings but no OOM report in the checked interval; approximately86GiB
  memory was available. These observations do not establish an NVIDIA cause or exhaust every
  possible resource condition. The actual failure is SIGSEGV, not a reported OOM kill.

[diagnosis001.json](diagnosis001.json) retains the initial read-only identities and bounded observations.
[pytest-stderr-snapshot.txt](pytest-stderr-snapshot.txt) and [gw0-events-snapshot.jsonl](gw0-events-snapshot.jsonl)
freeze the observed raw trace/history; they do not replace the complete broad receipt.

## History-sensitive next check

The last30 nodes span about three minutes of original worker history: queue/read contracts,
two Arrow record-family roundtrips, native record/support cases, archive compatibility/cache
cases including a two-thread cold-open test, a review-view generator interruption test, then
schema preparation at the crash. Those are retained in [preceding-30-nodes.txt](preceding-30-nodes.txt).
A fresh isolated rerun of just the crashing node cannot test this process-history interaction.

The first proposed reproduction preserves that order in one process, using the ordinary receipt
runner and an explicit `-n0` diagnostic override. This is a causal isolation, not serializing the
qualification campaign or claiming robust parallel success:

```sh
uv run python scripts/test_receipts.py run --python-only --command-timeout 600 --out-dir build/test-receipts/qualification/crash-history001 -- -n 0 @docs/design_review/evidence/2026-11-06_wce-gs120/qualification/interpreter-crash/preceding-30-nodes.txt
```

If the unmodified environment reproduces, capture the first failure before selecting a repair.
If it does not, an explicitly labeled `PYTHONMALLOC=debug` run can look for earlier allocator
misuse. That environment changes allocation/timing and a pass would not prove the original crash
resolved. A wider history or targeted dynamic-model/GC experiment is warranted only if the
bounded result leaves that consequential uncertainty. No debug-allocator or wider-history run is claimed here.

## Bounded source and upstream assessment

A search in `tests/` and `python/corpus-structure/tests/` found no `ctypes`, `from_address`,
`PyCapsule`, `_export_to_c` or `_import_from_c` use. This is not proof that every loaded native
extension or library is memory-safe. No concrete application/harness native-pointer misuse was
identified. The preceding concurrent archive reconstruction uses Python/Pydantic/cattrs paths;
its temporal proximity is not causation.

CPython documents that GC traverses references through container `tp_traverse` implementations
([GC design](https://github.com/python/cpython/blob/main/InternalDocs/garbage_collector.md)).
Upstream [CPython149590](https://github.com/python/cpython/issues/149590) demonstrates that the
same GC/dictionary stack can result from unbalanced references, but its multiple-faulthandler
trigger was not found in the bounded repository search and its fix was backported to3.14 in May2026.
The [Pydantic12867](https://github.com/pydantic/pydantic/issues/12867) shutdown/TzInfo report has
native pydantic frames and finalization semantics unlike this mid-run dictionary traversal; it
is not evidence for a particular dependency bump here. No matching established upstream fix
has been identified for this exact current environment/trace.

**Conclusion:** native reference-traversal corruption is the observed failure category; the
responsible component and reproducible trigger remain unestablished. Disabling GC, silently
switching canonicalization backend, globally serializing tests or treating one fresh pass as a
root-cause repair would conceal that uncertainty. The existing failed/crashed receipt must remain.

## Executed history replay001

**passed**,2026-11-06: the exact command above executed all30 selected nodes, including actual
isolated native fixture effects, in120.30s. The owned process exited0; classified receipt health
is passed, with no stream errors or worker losses and complete acquired native provenance.
[history001-result.json](history001-result.json) records the outcome and original receipt location;
[history001.log](history001.log) retains the controller output. Verifier/product source remained
`f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928`.

**Crash not reproduced.** This fresh-process result narrows the evidence: the last30 nodes are
not sufficient to reliably reproduce the preceding228-node process's fault. It does not resolve
that failure, prove all parallel workers stable, identify a corruptor or justify hiding it.
No GC setting, allocator, dependency, source or acceptance expectation was changed. A bounded
debug-allocator replay or a wider actual worker history remains a decision for the coordinator.

## Executed debug-allocator replay001

**passed**,2026-11-06: the same30 nodes ran in one fresh process under `PYTHONMALLOC=debug`,
with an owned600-second command bound. The actual uv runner, Python receipt runner and pytest
child environment were observed through `/proc`, retaining only the selected diagnostic keys in
[history-debug001-environment.json](history-debug001-environment.json). No GC state/threshold,
product/harness source, dependency or host setting was changed by this diagnostic.

[history-debug001-result.json](history-debug001-result.json) binds the exact command, environment
observation hash, source identity and complete classified native result. All30 nodes passed; the
process exited0, with no stream errors, lost workers or allocator diagnostic.

**Crash again not reproduced.** This is an allocation/timing variant, not an ordinary-parallel
qualification pass or a native-GC fix. The responsible component remains unidentified.

## Bounded acceptance recommendation and future trigger

- Preserve the original worker SIGSEGV and resulting controller/scheduler failure as failed
  evidence. Neither successful history replay rewrites that outcome.
- Reassess the actual affected semantic file/nodes under the current ordinary `-n auto` harness,
  with complete native acquisition and healthy process/reporting. Such a pass establishes those
  current functional obligations, not the cause of the prior process corruption.
- Verify fatal-worker handling independently: it must terminate and report failure rather than
  hang or silently omit cases. A restart-policy/liveness correction resolves that distinct
  behavior; it does not repair native GC corruption.
- Keep an explicit unexplained-native-crash limitation. Recurrence, allocator diagnostics or an
  actual core/heap trace is the trigger for a wider exact-worker-history or focused dependency
  lifetime investigation. No speculative production/backend replacement, GC suppression or
  arbitrary dependency move is supported by the current evidence.

The coordinator owns whether the resulting current functional/provider/nonfunctional union is
acceptable within its stated scope. These diagnostics alone establish neither full parallel
stability nor a clean complete campaign. No test assertion, acceptance rule or source was changed.
