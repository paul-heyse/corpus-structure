# Declared data operations — design authority map

Supporting document for the
[declared data operations review](../design_review_declared-data-operations_2026-11-12.md),
which owns the findings and every remedy. This page records what the design standard, the
architectural sections and the accepted decision records already say about the four properties
the operator asked for, the vocabulary to reuse, and the accepted decisions the target touches.

**Evidence.** Read from the design documents on 2026-11-12 through a delegated read-only
mapping. The review's author re-read ADR-0060, ADR-0063 and ADR-0090. Other quotations were
not re-read against their sources. No code was read for this page. Items marked *inferred* are
readings, not statements in the sources.

**Reading notes.** The focused section owners are `docs/design/D0`–`D9`. D6 states that its
§1–§4 are earlier proposed detail qualified by the later sections at the top of the file, so
where they differ the later text is current.


**Audit reconciliation2026-11-12.** This remains an implementation/authority baseline,
not the target specification. The [corrected target](target-contracts-and-storage.md) and
[principal §§4–11](../design_review_declared-data-operations_2026-11-12.md#4-corrected-target-state)
supersede original proposed mechanisms; the [companion](../audits/design_review_declared-data-operations_2026-11-12_audit.md)
records every recommendation disposition. Original dated counts and unrefreshed observations
remain historical, not new execution evidence.


## Property 1 — Operations as uniformly specified ports with contracts

**Standard.** DP-08 requires every domain operation to have a contract covering inputs,
applicability, outputs or state changes, invariants, effects and failure outcomes. It adds that
a first-class operation specification is needed only when a consumer must discover, inspect,
compose, plan or persist operations in that form. A planner that derives ready work from
declarations is such a consumer. FP-02 allows a trait or adapter for credible variation; FP-03
allows a registry only for real variation.

| Owner | What it decides | Status |
|---|---|---|
| D4 §1, the method contract | The `Method` protocol and six rules, including no routing inside methods | Proposed, 2026-10-28 |
| D2, composed execution contracts | Released contract inputs describe concepts, state dimensions, transitions, operations, invariants and implementation owners | Implemented source |
| D2 and ADR-0081, released characterization contracts | Operation declarations name produced families, required layers, result determinants, preconditions, effects and outcomes | Implemented; bounded Tested |
| D3 and ADR-0033, release-scoped execution projections | Seven fixed relations; supported variation becomes additional release rows | Implemented |
| ADR-0047 | Generate concrete typed callables; keep specialized algorithms in trusted implementations | Accepted target |
| ADR-0091 | One frozen provider profile owns model, artifact, runtime, device class, dtype, backend and numerical meaning; registry injection supplies implementation, not intent | Implemented; bounded Tested |

**Rejected earlier.** ADR-0031 rejected a universal workflow engine. ADR-0033 rejected
interpreting arbitrary effect programs and a generic entity-attribute-value store.

**Open.** The BEP coordinator and its qualification companion record a stronger
ports/adapters and dependency-driven design as a subsequent inquiry. The BEP/TC evidence
README lists the limits it must respect: readiness uses in-process predicates, a missing
persisted edge is not absence of a dependency, and provider queue and inference transitions
are not persisted.

## Property 2 — Dependencies expressed on object state

**Standard.** FP-05 asks for explicit dependencies, lifecycle and state transitions. DP-19
asks that planned, running, completed, partial, stale, cancelled and failed be distinguishable
and that material workflows be explicit plans or state machines. DP-02 keeps not supplied, not
applicable, not yet computed, unknown and failed distinct. H22 orders only work with a real
dependency.

| Owner | What it decides | Status |
|---|---|---|
| D6 §1 under ADR-0083 | Real dependencies determine readiness; a stage-wide terminal barrier is not a semantic prerequisite | Accepted target |
| D6 §1 | A unit is eligible for a stage when its method's `select` or a chain entry would route it; each eligible unit gets a task or a skip with a reason | Proposed, 2026-10-28 |
| D6 §2 | Upstream declarations belong to the graph, never to a method | Proposed |
| D4, demands | Decomposition-only, structural-only, interpreted and assessed results are distinct demands; weak demands do not perform stronger work | Retained route |
| D6, characterization layer lifecycle | Provider absence stays visible in coverage and cannot satisfy a stronger dependency | Implemented |
| ADR-0082 | `layers` holds the dependency closure and `active_layers` the explicit selection; no mutable latest | Accepted |
| ADR-0084 and D3 | Dependent tasks are registered only after their immutable input identity exists; no placeholder products or general cross-run graph | Accepted target |

**Open.** OPEN-D6-1, barriers versus dataflow, is deferred to phase 2 in the design-phase
plan. D6 records that the complete invalidation matrix remains open.

## Property 3 — Versions from operation fingerprints

**Standard.** DP-04 distinguishes the enduring entity, its revision, an execution attempt and a
stored artifact, and semantic identity from preparation dependencies, physical realization and
build provenance; one digest need not serve all four. DP-09 keys reuse on every
result-affecting input and invalidates at the finest granularity the evidence supports, while
noting that complete build provenance need not become every key. H13 propagates relevant
changes and stops when a recomputed value is substitutable.

| Owner | What it decides | Status |
|---|---|---|
| D4 §1 rule 4 and D6 §4 | The input hash is built from method name, version, config hash and the method's input digest; task ids are provenance only; an upstream rerun with identical output leaves consumers reused | Proposed; accepted as P0CL-02 |
| D6, semantic run binding (ADR-0027) | Task reuse requires the complete recorded binding; this conservative profile can recompute deterministic work after a policy-only change | Accepted |
| ADR-0060 and D6 | One operation-dependency projection for task hashing, twin selection and origin validation, scoped for two M1 methods; unknown determinants remain significant | Implemented |
| ADR-0063 and D3 | Semantic identity includes contracts, declared behaviour versions and grammar and model assets; executable source has a separate runtime identity; task reuse also respects runtime identity | Implemented; scoped Tested |
| D6, characterization layer lifecycle | A tokenizer, model, prompt or context change invalidates affected inference; a changed pure construction can reuse retained native evidence | Implemented |
| D2 | A new released construction rule can consume an unchanged native-evidence layer without rerunning inference | Implemented |
| ADR-0085 | Logical request identity includes the numerical policy; actual grouping is computation provenance | Accepted |
| ADR-0090 and DESIGN | Operation lineage is outside semantic determinants | Accepted target |

**Open.** The invalidation matrix; a per-result deployment identity (audit DA-032); a stored
meaning key (OPEN-D3-4); the served model identity entering the digest (SET-01).

## Property 4 — A retained record of actions and prior state

**Standard.** DP-05 keeps execution from mutating the definition it executes. DP-21 traces
every output to its sources, policies, providers, transformations and attempt, and asks that
selection, reuse and rejection be observable without instrumentation dominating useful work.
H25 scales durable history to real readers and writers. H26 notes that rich observability need
not emit an event for every primitive operation.

**Decided.** All are immutability rules; none is a state-change log. ADR-0014 makes
observations append-only and finished runs immutable. ADR-0081 creates new immutable layers
when dependencies change. ADR-0064 keeps completed results immutable. ADR-0077 requires
selection among competing decisions. ADR-0063 keeps the producing provenance of historical
runs. ADR-0084 leaves historical receipts read-only.

**Open.** No design document describes a general event or state-change log.

## Vocabulary to reuse

| Concept | Project term | Owner |
|---|---|---|
| Operation, semantic | `OperationContract`, `sem.execution_operation`, bound operation | ADR-0033, ADR-0027 |
| Operation, invocation | `SourceOperationLink`, managed operation | ADR-0090, ADR-0069 |
| Implementation | `Method`, method family, tier | D4 §1 |
| Unit | `TaskUnitType`; source view | D4, D6 |
| Task and attempt | `ops.task` lifecycle, attempt fence, lease, holder, twin | D6 §3.1, D3 §8 |
| Run | `ops.run`, cut, promoted run, demand anchor | D6 §2, D3 |
| Release | Semantic release; runtime binding | ADR-0024, ADR-0063 |
| Product | `ProductReference`; layer; enriched document view | ADR-0081, ADR-0082 |
| Fingerprint | Input hash, config hash, semantic determinants, runtime identity, logical request identity | D6 §4, ADR-0063, ADR-0085 |
| Demand | Weak and strong demands; capability | D4 |
| Receipt | Publication receipt; native batch receipt; managed result receipt | ADR-0084, ADR-0069 |
| Fate and coverage | Every eligible unit has a fate; family coverage outcomes | D6 §1, D1 |

"Operation" has two existing meanings. The review uses *data operation* for the declared
derivation and leaves the existing terms as they are.

## Accepted decisions the target touches

| Decision | What it says | Relation to the target |
|---|---|---|
| ADR-0063 | Task reuse respects runtime identity; no universal equivalence engine | The reuse clause is the main obstacle to property 3. Its revisit trigger names reuse without producing-runtime compatibility |
| ADR-0060 and D6 | Changing the executable release does not authorize task reuse across releases; full-binding defaults for methods outside the two scoped ones | The target scopes every operation by declared determinants and admits inputs across releases by contract |
| ADR-0014, §B2 | Knowledge is materialized per run; current means the promoted run. Rejected: methods writing knowledge directly, and one mutable knowledge base | Kept. The target stops at consolidation and adds a record of what a cut consumed |
| Rationale §4.5 and D6 | Consolidation is rebuilt per pass and not cached | Kept |
| ADR-0081 | A product reference includes the producing task | The target makes the task provenance (*inferred* tension with D6 §4's task ids as provenance only) |
| ADR-0083, ADR-0084, ADR-0090 | No general durable graph, broker, batch ledger or mutable operation table | Kept. The target stores derivations as facts and plans in process |
| Rationale §4.12 | Workflow engines declined as a second authority over task state | Kept |
| ADR-0047, ADR-0024, ADR-0067 | Historical compatibility routes removed in favour of regeneration | Consistent with a regenerating cutover |
| Principle P11, ADR-0006, ADR-0059 | Every mechanism needs a consumer; no additional ledger | The derivation record's consumers are reuse, planning and change determination |

## Related open findings elsewhere

The [phase 0 coordinator](../../../plans/phase-0_2026-10-28.md) §11 owns DA-001 to DA-025 and
F01 to F04. Those nearest this subject are DA-004 (operations reinterpret JSON dumps), DA-009
(contracts, key scheme and derived forms unversioned), DA-012 (operational closed sets with
uneven authority) and DA-017 (`agent_reuse` undefined). Their rows read open, which may be
stale given later work (*inferred*). The
[BEP coordinator](../../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md#execution-findings)
owns E09 and E15–E19. This review changes none of those dispositions.

## Corrected rule-impact map

The principal RC01–RC09 is the current proposed mapping. In addition to the original seven
impacts, provider/profile fingerprint semantics affect ADR-0085/0091 (RC08); source custody and
current-only regeneration require preservation/correspondence across ADR-0050/0064/0067 (RC09).
Original “kept” entries above describe obligations, not a prohibition on replacing their current
physical representation. Retain protected admission, exact attempts and source/evaluation
separation while extending the governing model. Accepted ADRs remain unchanged by this audit.
