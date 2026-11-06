# Final WCE qualification and applicability

**Tested,2026-11-06: selected functional/native/provider/consumer/nonfunctional union passed.**
[final-union.json](final-union.json) accounts for **5063 unique required nodes**:5055 ordinary
and8 exclusive fault cases, including885 native-required identities. Required-node coverage is
complete with zero unresolved. The [coordinator](../../../../plans/witnessed-corpus-enrichment_2026-11-05.md)
owns acceptance and current finding disposition. These are selected shared-development results,
not complete knowledge, scientific truth or an absence-of-all-runtime-faults claim.

## Functional receipts and recovery

| Command/evidence | Outcome and actual scope |
|---|---|
| `just test-all -n auto` | **failed/interrupted**, preserved in [ordinary-attempt003](test-receipts/ordinary-attempt003/).5054 selected:5034 passed,2 assertions failed,1 worker crashed,17 incomplete/unexecuted. Native GC loss and the subsequent scheduler stall are retained, not relabelled. |
| `just test-all -n auto @docs/design_review/evidence/2026-11-06_wce-gs120/qualification/affected-current.txt tests/scripts/test_parallel_harness.py` | **passed289**, clean reporting/worker/native health. [Current receipt](test-receipts/affected-current004/) replaces every228 case from the crashed worker, all20 unresolved nodes and whole modified files, and includes the new fatal-policy probe. These overlap earlier results and are not added to them. |
| `just test-native-faults` | **passed8** after parallel work completed; [exclusive receipt](test-receipts/native-faults001/). Dedicated-cluster authentication faults do not overlap live producers/consumers. |
| [Machine union](classified-current-union.json) | `required_node_coverage=covered`, zero unresolved. Its aggregate historical status intentionally remains `failed` because the failed campaign is included. [Assembly](build_final_union.py) checks current replacement passes and records source/context applicability separately. |
| Normal/debug-allocator last30-node histories | **passed30 each**, healthy process/report/native context. [Diagnosis](interpreter-crash/README.md) retains exact order, trace, symbolization and environment. The SIGSEGV was not reproduced; no native-GC fix is claimed. |
| Actual two-worker fatal policy probe | **passed** under the project default `--max-worker-restart=0`; [probe](scheduler-stall/README.md). It naturally reports a fatal failure/six queued `not_run` cases and no surviving process group. Auto/loadgroup remain enabled. |

Product source is3552edf69, validation harness83d0c295d, portable verifier SHA256
`f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928`. The only post-original
harness corrections are the registry's actual `locate.definition_terms` entry, use of the owned
300s default in positive transport tests, and explicit fatal-worker shutdown/probe. All transport
assertions and genuine timeout/cancellation controls remain. Product/semantic/native code did
not change during recovery. Other original passes came from separate unaffected workers; all
cases from the failed worker now have healthy current parallel passes. Machine source contexts
also reflect documentation/evidence and preserved concurrent operator changes.

The original CPython3.14.10 failure was in `visit_decref → dict_traverse` during garbage collection.
Its allocation site does not identify the corrupting component. A repeated crash, core or allocator
finding triggers wider native-lifetime/dependency investigation. No dependency, GC, interpreter or
backend workaround was introduced to hide it. Qualification establishes the declared current
functional and crash-termination scope; the unexplained original fault remains a recorded limit.

## Actual corpus and consumers

All journeys use the SAME120 exposed Grinstead–Snell physical pages191–310. Recovery140–151
retains12 original native products/48 views/all120 projected pages/zero duplicate fields without
repeating PDF conversion, recognition or GLiNER. Text availability and native-text fidelity are
separate claims.

Actual GLiNER2.5 model161/cut245 retains97 raw envelopes,44 components,66,638 contribution and
interpretation rows,42,781 operations including39,098 zero outputs. Its exact checkpoint/revision/
five files and explicit CPU FP32 profile are authenticated.200 bounded Reader pages,48 selected
files/seven portable partitions reconcile the complete selected population. Original PDFs remain
separate from portable declared-context closure.

Three policy arms162/170/180 share8210 IDs/84 cohorts;41 requests per arm execute and3 oversized/
40 inapplicable cohorts remain explicit. Comparison163 preserves unknown units and withheld interval
claims. Ten actual E5 graphs retain14 private own-component edges/28 fresh vectors/126 reuses.
Artifact183/1070/cut247 retains142 source records/116 private proposed pairs/zero alias pairs,
with fixed diagnostic assumptions and no EM/calibrated identity or automatic merge.

Protected set13/A43/B44/C45 retains original independent parents/alternatives. Only two narrow
attachments publish in169/cut225; whole-report, unassessed and two unsupported component attempts
refuse natively. Other retained output remains private/proposed.

Dossiers184/1071/cut249 and185/1072/cut251 share identical8280 member objects and4facet objects:
coupled180's8210 source contributions plus70 role spans from named/protected169's35 components.
The separately retained9 model additions/other model families are outside that declared selection.
Both choose12/retain8268 omitted members. Greedy displays4 role facets of2 already-supported
attachments; deterministic source-ID control displays0. No new source facts follow. Native completion
passes93,576.252ms/16,183.975ms under120s; different policies/timings are no speedup comparison.
Both full files,378,023,362/378,021,584-byte complete portable bundles, and fresh4-page CLI/MCP
parity/four refusal checks pass. Interactive8M and separately declared file budgets remain distinct.

[All23 earlier final current bundles](bundle-reverify-run001.json) plus both new dossiers verify on
f473: **25 final bundles**. [Current journeys](../records/wce.gs120-current-journeys.json) and
[model delivery](../records/wce.gs120-model-delivery.json) retain exact source/runtime pins and
failed/interrupted predecessors. This establishes current-contract/closure integrity, not meaning.

## Meaning, conditional work and nonfunctional health

[Reviewer inputs](../assessment/README.md) and the [benefit account](../assessment/benefit-account/README.md)
retain64 selected source cases,35 named plus9 model-addition assessments, selected table/note/
policy/context/artifact/dossier judgments, original812 overlapping authored records, and all raw
outputs. Useful partial structures, wrong roles/subjects, damaged formulas, missing conditions,
ambiguity and unassessed scope remain distinct. Two native-only captions and broad provider/graphic/
source-science questions remain bounded limits.

[Operation fitting availability](../assessment/operation-fit-availability/README.md) is
**unavailable/not_run**:17 declared completed runs/91,310 rows have zero exact compatible emitted
events and zero corresponding protected operation grades. Controlled fitting is separate; no
held-out/origin gate or labels were invented. Conditional pgmpy/Pyro/GEE/PPI/optimization/learned
challengers retain the coordinator's concrete triggers.

**passed:** `just hygiene` (all checks), `just ready`, `just model check` (revision0.6.5), final
read-only CB archive/runtime identity, and evidence checking (0errors/40 older out-of-scope warnings).
The original CB semantic release and producer runtime pins remain unchanged. Rust nextest selects
zero functional tests; **not_run** is explicit, with separate Clippy/dependency/format passes and
rustc1.101.0-nightly(2d20b42b8 2026-11-04).

[Retirement](../retirement/README.md) traces removed classifier/singleton/manual/supplied/old semantic
reader paths, current catalog/MCP integration and all three removed merged task worktrees.
Authentic raw sources, frozen installation predecessors, plans and evidence remain. Concurrent
operator process/role/AGENTS/library-documentation edits are preserved outside task authorship.
