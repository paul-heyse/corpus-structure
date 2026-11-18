# Production-efficiency integration

**Accepted scope · 2026-11-17; current implementation and qualification state belong to the coordinator.** Integrates the
[production-efficiency review](../../design_review/reviews/design_review_production-efficiency_2026-11-17.md)
as published at `2cc4e4d9d` (source baseline `fc73d2c8c`) into DDO-03–12. The
[coordinator](../declared-data-operations_2026-11-12.md#production-efficiency-integration--2026-11-17)
alone owns package state, the disposition of every finding, the rule-change record and the
execution queue. This page owns the cross-cutting target, the shared mechanisms, the slice
dependency order, and the contracts that have no other companion. Each other companion owns the
mechanism contract for its area in a section dated 2026-11-17.

The review's findings and rule impacts are cited here as `PE-Fnn` and `PE-RCnn`. The prefix is
required: the coordinator already uses `F01–F14` and `RC` numbers for earlier reviews. `PE-F27`
was withdrawn by the review and stays retired. Slices are `PE-Snn`; items found while preparing
this plan are `PE-Dnn`.

## Basis and re-baseline

The review read `fc73d2c8c`. Before authoring, every cited site was re-read at `2cc4e4d9d`
(2026-11-17, static reading). Only two production files had changed, and no finding had moved
or been corrected. The already-integrated narrower corrections were in the code the review read,
so each finding describes what remains after them:

| Earlier item | What it closed | What `PE` work remains |
|---|---|---|
| DDO-SI-23 | Binding rows shared inside one `admitted_data_read` statement | PE-F06: the base is still re-derived across the separate ready, generation-ready, hydrate and attach statements, and validity still precedes reduction |
| DDO-SI-27 / ADR-0121 | Selected-support acquisition and proof | PE-F07 grew: `ddo_require_source_set_acquisitions` and `ddo_require_selected_output` add one whole-demand pinned read per cut and per use |
| DDO-SI-24 | Source-cut authentication once per reference-authoring invocation | PE-F29: the grade-side double alignment and per-case annotation authentication are untouched |
| DDO-SI-29 | Bounded reuse of the composed effective model | PE-F04 and PE-F09 e are untouched |
| DDO-CA-13 | Capsule-aware admission | PE-F11: capacity 2 is the result after CA-13. No repository file overrides the execution-policy defaults |

Corrections to the review found during preparation, carried into the contracts:

- **PE-F03:** `open_release` returns what every read consumer uses, with one gap:
  `serve/selected_source.py` also needs the archived dependencies. `semantic/visual_routing.py:660`
  is a further read caller the review missed.
- **PE-F14:** whole-document hydration already uses one ordered cursor and one materialization
  bound. The remaining work is the per-scalar point reads and their preflight.
- **PE-F26:** on the record-publication path the producer does not run the output checks. The
  read-back child is the only complete output certification there. The target must add producer
  certification; it cannot simply remove the child.
- **PE-F26:** every stage product has consumers beyond the next stage, and stages take the
  capture as input. Private intermediate stages are therefore not an option.
- **PE-F28:** the native capture path already finishes a frozen build. Only the draft-stage path
  recomputes and then refuses.
- **PE-F13:** no production operation declares a non-scalar form. The batch path is complete and
  used only by tests and the execution-evidence leaf.

## Execution clarification — library integration · 2026-11-17

The operator authorized the detailed execution approach, including its subsequent library
assessment. Pydantic 2.14.1 owns callable/DTO boundary validation and serialization; prepared
adapters retain distinct strict JSON and Python ingress. cattrs 26.2.1 owns strict immutable
representation conversion. Dedicated converters configure exact primitives before generating
nested hooks. Neither library replaces portable Draft 7 wire semantics or canonical identity codecs.

PE-S04/S13 includes preparing the current effective-model cattrs decoder once and rejecting
primitive coercion. Current v9 compact omissions/defaults remain paired with their encoder;
they are not historical compatibility. PE-S05 also prepares the static typed-call adapter and
reuses decoded immutable correspondence by actual artifact bytes and effective-model identity.
Native admission and authorization remain live. Untrusted model instances retain reconstruction
and validation; unchecked construction/copy updates do not establish custody.

PE-S13 retains the complete prepared release: boundary products, JSON Schema, vocabulary
snapshots, OWL/SHACL and coverage declarations. Candidate/deploy reuse these exact artifacts.
The fingerprint includes supplied import/ontology bytes, profile and consequential preparation,
generator and library determinants. Mutable SchemaViews remain preparation-local.

LinkML already supplies effective declarations and physical PostgreSQL metadata; RDFLib and
pySHACL already supply derived graph artifacts and explicit RDF conformance. PE-S16/S17/S40
extend those existing model owners. No PostgreSQL-to-RDF materialization, live SHACL validity
cache, new msgspec codec or dataclass-to-attrs migration is selected. Such a projection would
need explicit occurrence/order/null/cut/protected-support fidelity and would retain live native
fencing and authorization. SHACL shape coverage does not imply those transactional guarantees.
Existing graph-copy, no-implicit-inference and structured failure boundaries remain deliberate.
PDF producer certification and reconstruction use the actual lowerer and native schemas.

Source reading also settles PE-S00's visibility choice: native graph writers refuse after
acquisition in the same owner transaction; acquisition bookkeeping remains permitted. Completion
helpers must separate immutable correspondence from their live family checks, including PostgreSQL
linguistic/catalog premises. Watermarks include raw visible identity cardinalities, exact pins,
trust epochs and kernel identity, avoiding timestamp-tie omissions. The coordinator owns execution
state and verification; these clarifications do not claim implementation or qualification.

## Workload premise

One operator, one workstation, a local GPU, a dedicated PostgreSQL 18 cluster. The benchmark is
the 518-page book; the target is multi-document corpora. Consumers are `ci`, typed queries and
exports, and an agent tier on MCP. The dimensions that multiply work are pages per document,
items and pieces per source view, obligations and requests per demand, documents per corpus, MCP
requests per session and `ci` invocations per session.

All expected benefits in this series are qualitative: each slice removes work the source shows
is repeated or amplified. No slice has a timing or throughput acceptance criterion, and no
benchmark framework, cost model or runtime accounting is added. A quantitative claim would need
a measurement and is not required for closure.

## Target reasoning: six causes, four shared mechanisms

The review groups its findings under six structural causes. The target answers each cause once.

| Cause | Target answer | Findings |
|---|---|---|
| Immutable things lose their established status | **Establish once, carry with the premise.** A property of an immutable input is established where uncertainty enters and is carried while its premises hold. Only the premise that can change is re-checked | PE-F03, F04, F09, F18 |
| Bytes-backed snapshots decoded per read | **One prepared immutable view per kernel call** | PE-F01 |
| Access paths missing for probed keys | **Declare the access path with the owner of the data** | PE-F02, F08, F15 |
| Validity recomputed from whole-demand state | **Set-wise validity per statement; acquisition evidence for pinned reads; one binding authority** | PE-F05, F06, F07 |
| Semantic unit became the physical unit | **Set-form interfaces with per-item results** | PE-F10, F12, F13, part of F14 |
| Preparation scoped to a call | **Process- or release-lifetime preparation with live admission** | PE-F16–F24 |

PE-F11 (capacity coupling), PE-F25, F26 and F28 (PDF movement and recovery) and PE-F30 (lock
mode) have their own contracts in the owning companions.

### Mechanism 1 — establish once, carry with the premise

An immutable input has three kinds of fact about it. The target treats them differently.

- **Immutable correspondence** (bytes hash to a digest; a payload matches a schema; a completion
  matches its intent). Established once at the boundary where the bytes enter, recorded with the
  identity of the code that established it, and not replayed.
- **Mutable premises** (revocation, population supersession, cut trust, runtime binding, file
  metadata, the installed native kernel). Re-checked wherever relied on.
- **Caller authority** (role membership, claim fence). Checked on every call.

Every use of this mechanism names which facts are in which class and what identifies the
establishing code:

| Use | Established once | Identity of the establishing code | Re-checked per use |
|---|---|---|---|
| Release on read paths (PE-F03) | Archive opened and digest-checked through `open_release` | Compiler version and archive header | Archive digest on each open |
| Release basis for execution (PE-F03) | Full re-derivation at a host's first use | Engine, archive digest, finalization, runtime and compiler determinants | Archive header row and runtime binding on each run |
| Wire protocol (PE-F04) | Ambient protocol, per-operation schemas, validators, once per process | Contract digest in the native envelope | Envelope digest against the process's protocol |
| Captured Python sources (PE-F09 a) | Full authentication at port acquisition and at worker import | Source digests in the descriptor | File metadata and object identity |
| Release facts in native code (PE-F09 b) | Lowered into typed rows at release admission | `lowering_digest`, native kernel digest | Kernel digest equality |
| Completion at publish (PE-F09 c) | Immutable correspondence at retention | Kernel digest recorded on the intent | Support, revocation, cut trust, caller authority |
| Retained products at consumers (PE-F09 d) | Product validation at production | Validator implementation revision | Body identity and consumer-relative premises |
| Model assets (PE-F09 f) | Content hash once per process and stat identity | — | File metadata before and after load |
| Serving identity (PE-F09 g) | Import-time source digests | Query custody loader | File metadata and module identity |

A digest alone is never treated as proof of meaning. Each row above pairs the digest with the
identity of the validating code and the premises under which it validated.

### Mechanism 2 — file custody by metadata with content confirmation

PE-F09 a, f and g share one helper (working name `FileCustody`). It authenticates a file by
stat, read and digest compare, then stat again, and records
`(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` with the digest. A record whose change
time falls within the filesystem's timestamp granularity of the wall clock is marked racily
clean and is re-hashed at the next check. A later check is one `stat`; any difference triggers a
re-hash, equal bytes refresh the record and changed bytes refuse.

This replaces per-call re-reading, re-parsing and re-hashing. It keeps detection of on-disk
change, which is real in a tree that agents edit concurrently. A long-lived process serves the
code it imported and refuses, with a restart instruction, once a custody source changes. It
never re-imports silently.

### Mechanism 3 — the prepared immutable source view

PE-F01 and PE-F02 share one owner, factored out of the existing `PreparedNativeSource`
(`semantic/source_contexts.py`). The operations companion owns its contract. Its lifetime is one
kernel call; no cross-request cache is added.

### Mechanism 4 — set-form interfaces with per-item results

PE-F10, F12 and F13 use the same shape: one physical call carries a set; each item keeps its own
identity, outcome, receipt and fence; an item-local refusal does not fail its siblings; a
failure of the shared physical unit fails every member, each keeping its ordinary retry. Locks
that protect the whole call are taken outside per-item savepoints. Replay of the whole call
returns the same per-item results and inserts nothing.

## What each change must preserve

The review's "Preserve" lists are acceptance conditions. The ones that constrain several slices:

- PostgreSQL remains the transactional authority (§B4); one release governs interpretation
  (§B5). Validation at the security-definer boundary stays.
- Revocation of a derivation, recipe, runtime, product or original admission invalidates
  dependents. A directly revoked producer is never rehabilitated by replacing upstream support.
- The complete protected dependency closure is retained (ADR-0110, unchanged).
- Per-item fates, receipts and fences; idempotent obligation identity; member failure isolation.
- The retained completion intent is the recovery point. Retain and publish stay separate
  transactions (products companion, PE-S21).
- One observation per vector, question or page (§B2); exact occurrence identities; block-local
  inference scope.
- Freeze, then validate, then seal; immutable per-stage publications with their own identity.
- No connection is held across compute. The bound on combined live memory holds.
- Chandra OCR stays excluded.

## Slices and dependency order

A slice delivers a coherent behavior change with its consumers migrated and its superseded
machinery removed in the same change. The owning companion gives each contract. Waves express
dependency, not synchronization barriers: any slice whose prerequisites are met may proceed.

| Slice | Delivers | Findings | Owner companion / package | Needs |
|---|---|---|---|---|
| PE-S00 | Bounded reading that decides later slices (list below) | — | this page | — |
| **Wave 1 — local, no native change** | | | | |
| PE-S01 | Wire protocol prepared once per process | PE-F04 (memo) | contracts-and-compilation / DDO-03 | — |
| PE-S02 | Prepared immutable source view and its consumers | PE-F01 | operations / DDO-07, 08 | — |
| PE-S03 | Keyed and ordered access in kernels and validators | PE-F02 | operations, rich / DDO-07–09 | PE-S02 |
| PE-S04 | Read and external release access; MCP lifespan engines; external packet cache | PE-F03 (read), F16, F18 | interfaces, postgresql / DDO-10 | — |
| PE-S05 | File custody; captured-source authentication; per-port adapters | PE-F09 a, e | demand-planning / DDO-03, 06 | — |
| PE-S06 | Serving identity from import digests with metadata drift check | PE-F09 g, PE-RC08 | interfaces / DDO-10 | PE-S05, ADR-I |
| PE-S07 | Model-asset custody with parent-to-child handoff | PE-F09 f | operations / DDO-07 | PE-S05 |
| PE-S08 | Established validity at consumers; one rich-graph validation | PE-F09 d | rich, operations / DDO-08, 09 | — |
| PE-S09 | Recognition failure classes; draft stages finish frozen builds | PE-F28 (part), PE-RC07 | operations / DDO-07 | ADR-0126, ADR-0127 |
| PE-S10 | Grading reference stage; indexed plan lookups | PE-F29 | interfaces / DDO-10 | — |
| PE-S11 | Lazy `ci` command registration | PE-F22 | this page / DDO-10 | — |
| PE-S12 | Result-reading verbs from settled classification | PE-F23 | this page / DDO-10 | PE-S00 |
| PE-S13 | Model-change cycle reuses the candidate's prepared archive | PE-F24 | this page / DDO-11 | PE-S00 |
| PE-S14 | Unreferenced code and duplicate verifications removed | PE-F31 | this page / DDO-07–11 | — |
| PE-S15 | Grammar authenticated once per process; HanLP admission per frame-bounded chunk | PE-F21 (a), F13 (HanLP) | operations / DDO-07 | PE-S05 |
| **Wave 2 — native successor N1 (no wire change)** | | | | |
| PE-S16 | Indexes and the exact-pin union | PE-F08 | products, postgresql / DDO-04 | — |
| PE-S17 | Release facts lowered at admission | PE-F09 b | products / DDO-04 | — |
| PE-S18 | Set-wise validity; reduction before validity | PE-F05, F06 (native) | products, change-reuse / DDO-04, 09 | PE-S16, S17, ADR-A |
| PE-S19 | Pinned read as acquisition evidence | PE-F07 | products / DDO-04 | PE-S18 |
| PE-S20 | Share locks for settlement | PE-F30 | products / DDO-04 | ADR-A |
| PE-S21 | Kernel-sealed completion intent | PE-F09 c | products / DDO-04 | PE-S17–S19 |
| PE-S22 | Executor reuses the attached binding; failed requests filtered before binding | PE-F06 (Python) | demand-planning / DDO-05, 06 | PE-S19 |
| **Wave 3 — admission and lifecycle** | | | | |
| PE-S23 | Two-stage byte admission; page size independent of admission; ready queue | PE-F11, PE-RC03 | demand-planning / DDO-06 | PE-S22, ADR-B |
| PE-S24 | Claim and hydrate in one transaction | PE-F19 (part) | demand-planning / DDO-06 | — |
| PE-S25 | Process-scoped execution host; carried verified basis | PE-F19, F03 (execution), PE-RC05 | demand-planning / DDO-06 | PE-S04, S05, S23, ADR-0125 |
| **Wave 4 — native successor N2 (wire change)** | | | | |
| PE-S26 | Set-form native operations; readiness watermark and single-obligation read; member set inserts | PE-F10, F06 (waiting obligations), F12 (members) | products, contracts, demand-planning / DDO-03–05 | N1 |
| PE-S27 | Wire validation placement and contract digest | PE-F04 (checks), PE-RC01 | contracts, products / DDO-03, 04 | PE-S00, PE-S01, ADR-0128 |
| **Wave 5 — model-call granularity** | | | | |
| PE-S28 | Encoder batch qualification (bounded) | PE-F13 | operations / DDO-07 | — |
| PE-S29 | Encoder batch form | PE-F13, PE-RC04 | operations / DDO-07, 08 | PE-S02, S07, S28, ADR-E; its native form check rides the first successor after PE-S28 passes |
| PE-S30 | CUDA GLiNER batch qualification (bounded) | PE-F13 | operations / DDO-07 | — |
| PE-S31 | One host exchange per question set; multi-input M1 questions | PE-F13 | operations / DDO-07 | PE-S30 |
| PE-S32 | Learned primary across blocks | PE-F13 | operations / DDO-07 | PE-S02, S31 |
| PE-S33 | Grammar prepared once with per-region terminals (gated) | PE-F21 (b) | operations / DDO-07 | PE-S15 |
| **Wave 6 — PDF (native successor N3, then N4)** | | | | |
| PE-S34 | Set-wise companion adoption | PE-F12 (companions) | operations, postgresql / DDO-07 | — |
| PE-S35 | Single adoption of page artifacts from the spool | PE-F25 | operations / DDO-07 | PE-S34 |
| PE-S36 | Producer certification; round-trip oracle per lowering identity | PE-F26, PE-RC06 | operations / DDO-07 | PE-S00, ADR-0130 |
| PE-S37 | Admitted bulk scalar read; narrow inventory read; ordered observation read | PE-F14 | operations, postgresql / DDO-07 | — |
| PE-S38 | Recognition worker per slot; context once per operation; page-atomic publication | PE-F20 | operations / DDO-07 | PE-S09 |
| PE-S39 | Capture resumes from the spool | PE-F28 (capture) | operations / DDO-07 | PE-S35, ADR-0127 |
| PE-S40 | Content-addressed byte streams | PE-F26 (copies) | operations, postgresql / DDO-07, 11 | PE-S36 |
| **Wave 7 — serving consumers** | | | | |
| PE-S41 | Per-publication search projection | PE-F15 | interfaces / DDO-10 | — |
| PE-S42 | Continuation pages without replay; read-scoped support closure | PE-F17 | interfaces / DDO-10 | PE-S19 |

**Order within the series.** Wave 1 has no rule or native prerequisite beyond the ADRs named and
should start first. PE-S16 to PE-S22 form one native change set and precede PE-S23, because a
frontier page larger than a handful would otherwise re-read the frontier once per item. PE-S26
builds on N1's validity and read contracts. PE-S29 and PE-S31 each follow their qualification
slice. PE-S35 precedes PE-S39 because spool-only custody is what makes page-level resume
independent of GPU determinism.

**Native successors.** The chain owner serializes all captures after the head current when this
work starts. Frozen predecessors are never edited. The slices group into four successors:

| Successor | Slices | Protocol | Notes |
|---|---|---|---|
| N1 | PE-S16–S21 | unchanged | Reads acquired before N1 refuse with "reacquire". Intents retained before N1 publish through the full completion battery; they are not regenerated |
| N2 | PE-S26 (set operations, the read page's `inputs_watermark`, the `obligation_id` read filter), PE-S27 | changed: set operations, read request and page fields, envelope contract digest | `read_demand_result_request` is a closed schema, so any new field is a protocol change and belongs here. Native and application captures are reacquired. The effective model version is expected not to move (no bound-role or interpreter semantics change); the root confirms at authoring |
| N3 | PE-S34, PE-S36, PE-S37 ordered observation read, PE-S40, PE-S41, and the encoder declared-form check of PE-S29 if PE-S28 has passed | PDF and serving functions, shared byte storage, contextual producer check | The retained N3 request includes the typed S40 backfill and retirements. The encoder check can take its own successor once ready. |
| N4 | Remaining read-scoped closure of PE-S42 and subsequent native conversions | read closure and remaining generators | Capture against the exact installed predecessor after the N3 transition. |

Fewer successors are acceptable where slices are ready together. More are acceptable when a
slice is blocked; a successor never waits for an unrelated slice.

**Shared editing surfaces.** The generated DDO acquisition, read and settlement modules,
`data_operation_projections.py`, `data_operation_storage.py`, `orchestrate/data_operations.py`
and the physical model own PE-S16–S27. One contributor at a time owns each file within a wave;
the root integrates.

### PE-S00 — bounded reading

Each item decides a named slice and is settled by reading source, not by a probe.

| Question | Decides | How |
|---|---|---|
| Does `pg_jsonschema` 0.3.4 compile a validator on every call? | PE-S27: which output check is kept; the gain of set-form validation | Read the pinned extension source (`library-research`) |
| Which `ddo_require_*_completion` and `_require_*_producer` helpers read only immutable rows? | PE-S18, PE-S21: what validity and publish may skip | Confirm the I/M/A classification in the products companion body by body |
| Can a row written later in the acquiring transaction tie `frontier_at`? | PE-S19: strict owner-row visibility or no post-acquisition writes | Read `ddo_read_visible` and the acquiring transactions |
| Does the container `body_schema` already cover member schemas? | PE-S26: whether per-member validation is redundant | Read the lowered product contracts |
| Does the release capture the PDF record lowering and reconstruction sources? | PE-S36: definition of the lowering identity | Read the PDF facet's validation contract |
| Does `classification.json` hold per-node data sufficient for the reading verbs? | PE-S12 | Compare the classifier output with the projections |
| What do `Candidate` and the staged preview record about compile inputs? | PE-S13 | Read `cli/model.py` and the model-change contracts |
| Is every binding candidate, including exact-pin uses from other demands, inside the read's recorded scope closure? | PE-S19: whether pin scopes are added at acquisition | Read the read seeds against the binding arms in `data_operation_projections.py` |
| Does any consumer recompute a CPU packet digest from packet contents? | PE-S05: packets carry digests | Read the receipt consumers |

### Questions that need a first executed slice

These cannot be settled by reading. Each is the first bounded step of the slice that needs it,
names the one decision it informs, and uses the smallest input that decides it.

| Slice | Question | Decision |
|---|---|---|
| PE-S28 | Do batched E5 and Qwen vectors keep identity populations, own-member nearest-singleton attribution and normalization admission, when encoded singly, mixed, reversed and regrouped? | Per profile: declare the batch form, or stay scalar until an attribution fault is repaired |
| PE-S30 | Do production GLiNER packs on CUDA give attributable results under the same regroupings? | Whether PE-S31 may form larger cohorts. Cross-request coalescing on CUDA already runs ahead of this qualification (PE-D05), so this slice comes first |
| PE-S39 | Can the pinned Docling pipeline skip page stages for spooled pages and assemble over restored plus new pages? Are GPU page outputs identical across processes? | Whether resumed-versus-uninterrupted equality is asserted on GPU or only against the same spool |
| PE-S33 | Is the forest exactly equal between the per-region compile and a prepared grammar with supplied terminals, over the book's regions? Do same-terminal, same-start alternatives occur? | Adopt the prepared grammar with a pin hold, or keep PE-S15 only |
| PE-S02, S18 | View sizes and support-graph shape for the benchmark book; planner behaviour in the binding universe | None. They set magnitude only; the slices proceed without them. The index-usability check of PE-S16 covers the planner |

## Contracts owned here

### PE-S11 — lazy `ci` command registration (PE-F22)

`cli/__init__.py` imports all 18 command modules, and through `cli/model.py` the model-change
toolchain, on every invocation. Target: `REGISTRY` becomes an explicit table of command names,
owning module and registration function. `main()` imports only the module that owns the invoked
command. `--help`, no arguments, completion and `ci reference` import every module. Result types
that heavy modules export only for annotation move to light leaf modules.

Query-custody modules are compiled from source in every process. The custody loader may cache
compiled code in a custody-owned directory keyed by the verified source digest and the
interpreter magic number. The key is the exact bytes, so the guarantee is unchanged. This part
is optional and lands only if the registry change leaves it material.

Preserve the explicit registry contract and `ci reference` generation. Confirm the pinned
Typer route (a lazy group class or dispatch on the first argument) in the slice.

Acceptance: a dispatch test asserts that the declared names equal what full registration
produces and that invoking one command imports no other command module. That is a functional
test of dispatch, not an alignment lint.

### PE-S12 — result-reading verbs (PE-F23)

`coverage`, `scheduling`, `failures` and `retry` each start a fresh `uv run` that re-parses the
raw receipt streams. Target: for a settled receipt whose `classification.json` exists and is
bound to that receipt, compose the projection from it. Unsettled or missing receipts
re-classify as today. The supervisor is called with `uv run --no-sync`, as the managed lanes
already are. Pytest-argument validation moves into the lane run, which already receives the
arguments. `retry` requests summary and unresolved selection in one call.

Preserve: the checkout's supervisor owns classification semantics (ADR-0069); receipt
authentication; recomputation for active receipts. PE-S00 decides whether the persisted
classification needs extending first.

### PE-S13 — model-change cycle (PE-F24)

Preview, candidate and deploy each re-prepare the release. Target: the candidate records an
input fingerprint (the digests the compile consumes: declared sources, physical sources,
migrations, compiler implementation) and retains the prepared archive with the candidate
result. Deploy verifies the fingerprint against the working tree, refuses on any change as
today, and then verifies and reuses the retained archive. Candidate reuses the preview's result
for an identical request. Compiles per change fall from three to at most one.

Not changed: the 285 frozen revisions and their size. Frozen revisions are never rewritten, and
a change to the revision format is not proposed here. Each future revision still stores a full
native catalog.

### PE-S14 — unreferenced code and duplicate verification (PE-F31)

- Delete `orchestrate/liveness.py` (no importer; already listed for retirement in the
  PostgreSQL companion) and `semantic/data_operation_execution_context.py`
  (`load_data_operation_execution_context` has no caller, PE-D06).
- Delete `evaluate/task_semantics.py`. It has test importers only; the graph companion planned
  to migrate it "with actual consumers", and there are none. Remove its tests with it.
- Delete `gliner_extract_members` and `gliner_extract` (no caller). Re-grep at execution, since
  dynamic use was not excluded. Delete `HostedPipeline.pipe` only if its static callers are tests.
- `describe_database` uses one read engine for release, admission and description.
  `compare_companion_exports` verifies each export once and passes the verified manifests on.
- Cache `artifact_profile`, `companion_profile` and `record_write_profile`, which re-parse YAML
  or rebuild per call.
- The review did not independently check two lane observations: the static staging-metadata
  rebuild behind the profile caching above, and repeated encode and digest per native
  transport exchange. Verify both first; act only on what is confirmed.
- `read_packet` returns raw inputs beside their decoded views. Return the views only, unless a
  consumer reads the raw inputs; re-grep at execution.

## Discovered items

| ID | Observation | Route |
|---|---|---|
| PE-D01 | Concurrent MCP renders each construct their own 2 GiB budget, so combined live memory is unbounded across them (inferred from `intervene/native_render_tools.py`) | Closed by PE-S25: one budget per process, one active run per host |
| PE-D02 | Lark's dynamic Earley scanner takes one match per terminal per position. Two positioned alternatives for one terminal at one start would silently drop the second. Whether `classify()` can produce such pairs is not established | A correctness question, independent of efficiency. The reading step that answers it (does `classify()` emit same-terminal, same-start pairs) starts with Wave 1 and does not wait for PE-S33 |
| PE-D03 | A row written later in the acquiring transaction can tie `frontier_at` at microsecond resolution and be visible without appearing in a stored scope list | PE-S00, then PE-S19 |
| PE-D04 | The record-publication path has no producer-side output certification | PE-S36 adds it; this is why PE-F26 is not a removal |
| PE-D05 | Cross-request GLiNER coalescing on CUDA is live ahead of its ADR-0085 qualification | A correctness question. PE-S30 starts with Wave 1, serialized with other GPU cohorts |
| PE-D06 | `load_data_operation_execution_context` has no caller; `visual_routing.py:660` is an unlisted `load_release` read caller | PE-S14, PE-S04 |
| PE-D07 | An executor transaction that holds a pinned read's share lock and then attaches with an exclusive lock on the same scope can deadlock against a second such executor (inferred, not observed) | Removed by PE-S20 |

## Acceptance across the series

Each companion states the evidence for its slices. The common rules:

- Evidence must be able to expose a wrong implementation: products, identities, refusals and
  receipts compared against independently specified expectations, never against the output of
  the function under test. Where a retired implementation is kept in test code as a second
  implementation, it is differential evidence, not the oracle.
- Equivalence slices (PE-S02, S03, S18, S26, S34–S37) compare published products or query
  results before and after on bounded inputs, plus the refusal cases the change could weaken.
  PE-S29 is a population-equivalence slice: the same members each get exactly one vector, and
  identities change only through the new policy's profile id.
- No timing, throughput or capacity number is an acceptance criterion. Where a test checks a
  bound, the expected value is computed from the policy constants.
- Targeted checks close a slice. DDO-12 owns assembled qualification of the corrected source,
  including the whole-book same-demand run.

## Formal review

**Operator clarification · 2026-11-17:** the detailed execution planning and its independent
boundary assessments establish the design basis for these accepted changes. Do not repeat that
planning or introduce another formal design-review/audit engagement as an implementation gate.
The previously listed blanket prerequisites are withdrawn. Ordinary implementation review,
functional verification and the accepted ADR routes remain. Reopen only a concrete consequential
choice or mismatch revealed by implementation; continue independent authorized work.

The preservation questions in the native, host, PDF, failure and model companions remain useful
implementation criteria. Model qualification still precedes larger batches. Recognition/PDF is
the accepted scope of the failure-classification change; extending it requires an actual reason.

## Library behaviors the target relies on

Each is confirmed against the version-matched source or documentation in the slice that uses
it, before the dependent code is written.

| Behavior | Used by | Reference to confirm |
|---|---|---|
| Row locks taken inside a subtransaction are released when it rolls back, so call-wide locks are taken outside per-item blocks; `FOR SHARE` conflicts with `FOR UPDATE` but not with itself | PE-S20, PE-S26 | PostgreSQL 18 documentation, explicit locking and `SAVEPOINT` |
| `json_matches_schema` validator construction per call | PE-S27 | `pg_jsonschema` 0.3.4 source |
| Dynamic Earley reads terminals through a replaceable term matcher; no public data-supplied terminals | PE-S33 | Lark 1.3.1 `parser_frontends.py`, `parsers/xearley.py`; needs a `docs/pins.md` hold if adopted |
| Lazy command group or first-argument dispatch | PE-S11 | The pinned Typer and Click sources |
| Page-stage hooks that restore spooled pages before global assembly | PE-S39 | The pinned Docling `StandardPdfPipeline` and the existing `StreamedPipeline` hooks in `ingest/pdf.py` |
