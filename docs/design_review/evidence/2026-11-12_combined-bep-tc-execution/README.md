# Combined BEP and TC execution

Owning plans: [BEP](../../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
and [TC](../../../plans/text-characterization_2026-11-10.md). Implementation began at868e1befe.
Combined final qualification and full-book processing are not run in this increment.

## Protected inventory reader · Tested2026-11-12

The dedicated corpus_structure_dev database on PostgreSQL18/corpus port5434 was observed at
semantic_bep_capacity. The existing typed native change route produced a forward revision
semantic_bep_inventory. It changes only ops.read_characterization_inventory and the dependent
execution contract descriptor; owner and ACL are preserved. No activation or selection occurred.

| Command | Outcome | Managed result |
| --- | --- | --- |
| `uv run ci model change preview - --json` | passed | e598b5b18b9844a7858a1b41a61c17ed |
| `uv run ci model change candidate e598b5b18b9844a7858a1b41a61c17ed --json` | passed; rollback-only candidate | 58ff273d054a41b7a58d043dd664ad0d |
| `uv run ci model change register 58ff273d054a41b7a58d043dd664ad0d --json` | passed | 54b60cda2dd1436581d0bb8442d66a0d |
| `uv run ci model change deploy 58ff273d054a41b7a58d043dd664ad0d --json` | passed; development only | 774bd7d911224d40be8ab2de5f2c8ebc |
| `uv run ci test --workers 1 --json -- python/corpus-structure/tests/semantic/test_characterization_native.py::test_protected_inventory_summarizes_exact_native_provenance_without_annotation_payload` | passed1/1 | 5ff5b9a4414241e09a153ad880735569 |

The initial reader control65cc475530d64aba95d0b7c1af30004f failed because its fixture selected
a release without AnnotationLayer. Added the same characterization_pdf fixture selection used by
adjacent controls. Exact retryfc9c1c75f22a46479ca425e9ade036f5 refused after parametrization changed
the node identity; the fresh selection above exercised the corrected control. Both original
outcomes remain retained. This is actual protected-reader provenance/shape verification, not
provider inference or enclosing plan qualification. Sealed-template qualification remains later.

## Python3.14 and Protobuf override · Tested2026-11-12

`python314_probe.py` owns the bounded actual-model probe. An isolated Python3.14.10 environment
installed all117 exact packages exported from the old common312 lock; SentencePiece0.2.0 built
successfully. Maverick/DiPO imports and actual CUDA/FP32 inference passed using Protobuf3.20.0.
The operator explicitly requested overriding the pin. `uv pip install --python
/tmp/corpus-nlp314-probe/bin/python --no-deps protobuf==6.33.6` replaced that dependency; both
actual model paths passed again. The root environment was then deliberately updated with exact
Maverick1.0.7, DiPO0.2.1, Lightning2.6.6, SentencePiece0.2.0 and TensorBoard2.18.0, plus the
explicit uv Protobuf6.33.6 override. Intended transitive moves include OmegaConf2.4.0→2.3.1 and
Setuptools81.0.0→80.10.2. No wholesale upgrade was selected.

`TC_PROBE_PYTHON=/home/paul/corpus-structure/.venv/bin/python uv run python
docs/design_review/evidence/2026-11-12_combined-bep-tc-execution/python314_probe.py` passed both
models in the full root environment. Maverick emitted4mentions/2clusters over8tokens; DiPO
emitted2EDUs/1RST split. Both child returncodes0, Python3.14.10/Protobuf6.33.6/CUDA:0/FP32.
These are compatibility checks, not semantic grades or output-equivalence proof. The loaders
emit existing TorchScript/tokenizer/upstream checkpoint warnings; no new incompatibility was
observed in these bounded paths. Nemotron custody surrounds and is restored after the probes.

ADR-0091 selects a single root host; the unused isolated environment is retired. Required
provider/shared-host qualification remains open. `uv run ci doctor --json` passed,
d1b50072037448aa8a10dd0bf8a217f0 (tools only).


## Shared host and adapter checks · Tested2026-11-12

`uv run python docs/design_review/evidence/2026-11-12_combined-bep-tc-execution/shared_host_probe.py`
passed actual D1 and HanLP requests submitted concurrently through one production host. D1 returned
12; HanLP retained six tokens with lemma/POS/SRL/DEP/CON output. This verifies the bounded request
paths, not measured overlap or a fully loaded six-provider population.

Actual hosted spaCy control9d74149cbe2b49c9927a974b0099beaf passed1/1. The initial
e8f3f616d5b0443fa0caa5d7c7eaf76d stalled because the logical annotation handle omitted `flush`;
owned supervisor interruption settled it failed. A regression control now requires forwarding that
flush before completion. Retryed7d389df427453c94ad02cf5270fc84 failed the overly broad all-GPU
parameter guard. The pinned spaCy transition checkpoint deliberately retains its CPU upper classifier;
the corrected guard authenticates only that precise subtree as NumPy/FP32 and requires all remaining
learned arrays on CuPy/FP32, retaining actual placement observations. No whole-model fallback occurs.

`CORPUS_GLINER_DIAGNOSTIC=1 uv run ci test --workers 1 --json --
python/corpus-structure/tests/methods/test_gliner.py::test_native_boundary_diagnostic_observes_and_rescores_exact_occurrence` exercised the actual small CUDA
path (the opt-in is required). Initiala4f769f16203488a8a25c36569f31b1f failed because the diagnostic
bypassed batch placement and constructed explicit-span indices on CPU. Both now follow the model
device/dtype. Retrya63fceb6841a4296838b3a4bb9dc81de passed1/1. These original failures remain visible.

The normalized `runtime-compatibility.json` is a report of the observed probe outputs, not a raw
console transcript. Recordbep-tc.gpu-runtime-compatibility was finalized by
`uv run ci evidence finalize 2026-11-12_combined-bep-tc-execution bep-tc.gpu-runtime-compatibility
--json`, passed26b3ef82ed2b44e8843c51fb90ec74c0. Model outputs are compatibility evidence, not linguistic grades.

## Coordinated primary-language and native integration · Tested2026-11-12

Primary declaration syntax, predicates/roles/cues and examination availability replace remaining
private recognition. Definition-chain/domain selection remains downstream. Contextual query12 and
all three -2 retrieval recipes bind exact primary/contextual annotations; detached replay and native
admission share that closure. Superseded HanLP frame/cue production, dead reader APIs, old per-model
workers and unused service manifests are removed. Historical native evidence/profile identities stay
original. TC-E13 is a grammar-relative coverage clarification, not a demonstrated parser defect.

Independent implementation review found two consequential gaps: optional native cue columns could
be treated as examined absence, and one malformed declaration sentence could erase healthy facts.
Primary examination state and a separate sentence-local declaration-syntax family repair both.
Root integration review also removed transient preparation memo from durable recovery snapshots,
reauthenticated spaCy/GLiNER identities and declared the complete recovered population before serving.
Focused recovery/flush controls17723510d8164827b859e87f6c23b5e2 passed12/12; actual resume control
16be5d5068e148559d2c5fa20e642379 passed1/1. Earlier integrated application/recovery selection
7bde630a3fe543319db4c9dd24f73578 passed91/91. Their original source/context limits remain recorded.

| Command | Outcome | Managed result |
| --- | --- | --- |
| `uv run ci model change preview - --json` | passed; predecessor semantic_bep_inventory | 1c40c3fd9bea42f7b56109cb90de80b2 |
| `uv run ci model change candidate 1c40c3fd9bea42f7b56109cb90de80b2 --json` | passed; rollback-only | 21b9cb5a4cc5484b972719cef3f10615 |
| `uv run ci model change register 21b9cb5a4cc5484b972719cef3f10615 --json` | passed | e1f2d47aa36f41ad9bdc78f611f29f7e |
| `uv run ci model change deploy 21b9cb5a4cc5484b972719cef3f10615 --json` | passed; development only | 2469124379844faba5fab736fb390b74 |

The operation view showed three changed function bodies: source-contribution admission, primary
declaration-component authentication and the dependent execution contract descriptor. Owners/ACLs
were preserved. Native head is semantic_tc_primary_gpu; deployed release
f2a4573f84e50bbdbacc3cf8abd9083a73cb965936829fa69aff4bc2bb240a9e. Frozen SQL and declaration changes
were reviewed before registration/deployment. The explanatory parser cannot parse the multi-statement
frozen descriptor wrapper; rollback-only authoring and deployment execute the actual SQL successfully.
No activation, selection, promotion or recognition rerun occurred.

## Scoped checks and retained history

- `uv run ci check --only types --json`: passedbcd60113ed7f4ba5bf7590d871fe4e6a after explicit
  reply-mode/ownership/declaration type repairs. Original failed44d2/f070/dca1 receipts remain in managed storage.
- `uv run ci check --only lint --json`: passedbf30507ec2a643a0b3d2a83c9e65614f.
- `uv run ci check --only deps --json`: passed11f4ad6d37a7475f9fb1086802e42d0a.
- `uv run ci adr lint --json`: passed4c29970afba14244b3a99aa5890c8b3f.
- Initial documentation check268f8a89aaa143eb9dfaeb438515f42d failed solely on the stale ADR index;
  root turn-end regenerated it before retry.

Worker results retain their worktree source and execution context. The
`worktree-history-manifest.json` indexes23 original result directories and their raw snapshots under
raw/worktree-managed-history. These include failed collection/environment attempts, not just passes;
they are historical snapshots, not rewritten main-source qualification or newly established custody.
Original worker Git histories are retained in main before branch/worktree cleanup.

Combined final functional/native/provider/fault qualification, full-population GPU lifecycle,
TC-E12/TC-10 semantic grading, sealed-template reconciliation and whole-book execution remain open
under the two owning coordinators. Old memory-interrupted0a78c71ce1a949e38e906c9c5392c1f3 remains
held/unsettled: standard recovery refused unproven settlement. No memory attribution, measured
speedup, semantic grade or complete-plan pass is inferred from these scoped checks.


The final focused integration command was `uv run ci test --workers 2 --json --
python/corpus-structure/tests/methods/test_native_host.py
python/corpus-structure/tests/methods/test_characterization_resources.py
python/corpus-structure/tests/methods/test_contextual_query.py
python/corpus-structure/tests/methods/test_definition_declaration_primary.py
python/corpus-structure/tests/methods/test_m1_assertion_qualification.py
python/corpus-structure/tests/orchestrate/test_characterization_recovery.py
python/corpus-structure/tests/semantic/test_contextual_query_replay.py`.
Result082c8d819c524621bdfc989f70c31f25 failed106passed/8failed. Every failure was the same M1
controlled decoder stub omitting the new providers/native_profile keyword arguments; production
was unchanged by the repair. `uv run ci test retry 082c8d819c524621bdfc989f70c31f25 --lane ordinary
--workers 2 --json` passed8/8,78d9f49d5ebf45209177e62473d78f57. The original failure remains retained;
these receipts cover the114 selected identities with that fixture-only applicability judgment.
They do not replace the combined final required union.

`uv run ci docs check --json` passed390c423de6c4493aa603c62dd007ef9c,918canonical pages/zero link
errors after index regeneration. `just turn-end` and `git diff --check` passed. Final handoff
maintenance and publication checks are recorded in STATUS and the owning plan.


Final publication `uv run ci docs check --json` passedda4c010c45ba4d228a761e21a242769c,
918canonical pages/zero link errors. `uv run ci evidence check --json` initially failed
d9831b3241f741c695c7354c36c492a8 on two stale generated indexes. `uv run ci evidence index --json`
passedd121d2d996274d59bb7bd1976fb47135 updated the global and local indexes; the exact check
passedfdc1ef2a00974fae9f680f9576dccca0 with zero errors and42 historical warnings. The new
compatibility record has no hash/finalization error; unrelated historical input/supersession
warnings remain unchanged in scope. Root final maintenance/diff checks passed. Worktrees/branches
were removed after patch-equivalence verification and original-history merge4d6a12b48.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**BEP-TC**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Python 3.14 and a Protobuf override support selected native CUDA paths](records/bep-tc.gpu-runtime-compatibility.json) | BEP-07 | passed | ADR-0091, BEP-07, BEP-08 | 2026-11-12 |
<!-- evidence-index:end -->
