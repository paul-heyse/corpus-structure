# Book-execution foundation target review

## 1. Scope and decision

**Design / target · 2026-11-11 · independent reviewer: BEP foundation reviewer.**
**Accept scoped, Proposed**, the hybrid target and the BEP-00–03 contracts below. This is
pre-implementation target acceptance, not acceptance of worker code or full-book qualification.

Focus is the operator's combined efficiency-oriented design-principle and maximum local
parallelism inquiry, with Python3.14 executor capabilities as mechanisms to assess. Source is
clean539a437da. The audit input is the working-tree [entry reconciliation](../audit/README.md#book-execution-entry-refresh)
over that source, including the bounded [DA-042](../audit/execution-fit.md#da-042) update;
publication revision is established by the coordinator's subsequent commit. Applied standard:
core3.3, heuristics1.0, code-intelligence1.4 and repository binding, using design-review and its
code-intelligence companion. Source inspections below are Interface-checked2026-11-11.

Workload:316 natural views over the retained518-page document, skewed formula/prose regions,
complete selected families, exact retained dependencies, one operator and one local host.
BEP-00–03 establishes reuse and actual CPU placement. The ready frontier, resident provider
lanes, batching, final device/count decisions and full-book delivery remain enclosing obligations.
Run610's oversized native layer is a known separate publication limit; this review accepts no
repair by truncating context/families, widening that contract or restarting recognition.

## 2. Responsibilities and fidelity

| Owner | Authoritative responsibility | Derived form and allowed consumer |
| --- | --- | --- |
| Released semantic operations | Applicability, configuration, source/choice/coverage meaning | Parent method adapter and pure kernel realize the same operation |
| Invocation execution context | Full release verification and validity premises for this operation | Explicitly passed preparation; no public caller-controlled trusted flag |
| Regional owner | Sufficient exact source/dependency values and bounded lifetime | Immutable internal views shared between independent reader instances |
| CPU execution scope | Spawn lifecycle, admission and private calculation | Canonical packet/result; no database or provider descendants |
| Existing claim/completion owner | Durable attempt, renewal, result validation and publication | Worker completion alone confers no visibility or admission |
| Provider lane owner, later | Compatible residency, routing, stop/drain | Private inference replies, stably reduced by semantic owner |

Source facts retain the exact base, original ordered extents, native item/ancestor references and
projection/recipe. Formal parses retain correspondence and packed ambiguity; witnessed roles retain
released premises and required choices. Contextual evaluation consumes a selected retained graph,
not scientific truth. Unknown, unexamined, unsupported and failed remain distinct outcomes.
Neither equal strings nor matching packet shapes substitute for source/dependency identity.
Published layers remain under their original release contracts; active analyses remain distinct
from retained validation closure. These distinctions govern actual kernel inputs and publication,
rather than being documentation-only labels.

## 3–4. Contracts, composition and actual seams

The current demand boundary fully loads a release at
[characterization.py](../../../python/corpus-structure/src/corpus_structure/orchestrate/characterization.py):583–605;
the regional loop and final composition call it again. Stable preparation is already passed to
registry/stage execution. Replace the repeated loader with a private context constructed only by
successful full verification. Historical open_release and registry.prepared are not that authority.
Validity follows actual release/compiler/runtime determinants; regional text and unrelated physical
limits do not force release recompilation. Current database admission and source permission checks
remain live. The context belongs to one invocation/address space, not a process-global cache.

BoundReader locally retains a source view but successive stage readers reload layers through
characterization_layers. A separate regional owner can retain exact validated dependency views
without sharing connection ownership. Canonical content is immutable; LayerReport.payload remains
a fresh mutable public value. Internal trust requires protected acquisition or validation under the
exact original-release/source/closure premises. Digests and constructor-created reports confer no
trust. Newly computed output crosses validation before protected publication.

The CPU packet carries exact correlation, operation/configuration, sufficient ordered native source
values, dependency pins plus canonical bytes and participating release capsules. PreparedRelease
contains an RLock, lazy closures and generated models; PreparedSourceView contains mutable/cached
working state. Transfer owned primitives/bytes, not those populated objects. Existing archive_reader
open_release_parts/reconstruct_release permits DB-free worker-local hydration. Check capsule and
runtime correspondence at initialization. Hydration does not establish live database admission.

Actual method seams are FormalEvidenceMethod, ConstructionCharacterizationMethod and
ContextualInterpretationMethod. The latter builds ContextualEvaluator over retained layers and does
not call scientific_evidence/SymPy. Scientific domain consumers are not silently moved into this
scope. Stable declaration/vocabulary preparation can be worker-local; source-specialized protected
atom grammars must retain packet-specific lexical/source conditions.

Select ProcessPoolExecutor with explicit multiprocessing.get_context("spawn"), initializer and
initargs, module-level kernels, one parser-bearing operation per worker main thread. Parent
adapters submit real work and synchronously await it while checking claim lifetime; later BEP-05
can consume the same execution capability without a second kernel implementation. This preserves
SIGALRM/nested deadline constraints and avoids whole-demand thread wrapping. Spawn/picklability,
initializer failures and pool-wide termination semantics are specified by the
[Python3.14 executor contract](https://docs.python.org/3.14/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor).

Minimum07a supplies finite item/byte admission covering regional bodies, packets and replies
awaiting parent consumption. Capacity remains charged through the final consumer. A full budget
backpressures; an indivisible oversized item explicitly refuses without semantic splitting. This
increment integrates with the current serial regional driver; it does not claim ready-frontier
parallelism. Initial capacity-one execution uses the same worker path. Final operating counts
belong to07b, not CPU-count defaults.

Parent renewal remains active during hydration, waiting and completion preparation. Stop prevents
new submission, signals operation-owned cooperative cancellation, discards late replies and drains
under bounded deadlines, with pool termination as fallback. Future.cancel does not interrupt an
executing call. Operation-wide cancellation suffices for this serial integration; independently
addressable claims are required before BEP-05 admits multiple durable logical claims. Native fencing
still decides whether a result may publish.

## 5. Change and failure scenarios

| Scenario and kind | Locality and preserved guarantee | Settling evidence |
| --- | --- | --- |
| New released construction, domain extension | Change semantic operation/rules and relevant packet config; no dispatcher interpretation of role meaning | Existing independent role/choice expectations through pure and spawned route |
| Compiler/runtime change, binding | New verified context/capsule or refusal; archive reads retain original meaning | Mismatched runtime/release negative control |
| Executor substitution, mechanism | Private packets isolate transfer/lifecycle, while main-thread deadlines and cancellation constrain valid substitutes | Actual child/main-thread, startup failure and deadline controls |
| Slow formula/fast prose, workload skew | Bounded outstanding state and stable result correlation; later05 owns independent regional scheduling | Out-of-order worker result and budget controls |
| Lost claim during calculation, failure | Parent stops scope and ignores late output; no child DB effects | Native stale-completion refusal and real cancellation |
| Mutation/forged dependency, trust | Fresh public values; internal reuse requires authentic original closure | Mutation isolation, wrong source/release and forged report controls |
| Oversized canonical layer, workload limit | Existing native bound refuses; scheduling cannot create whole-book acceptance | Preserve run610 failure in BEP owner; repair remains separately scoped |

## 6–7. Gates and findings

| Gate | Target verdict and evidence |
| --- | --- |
| G1 Authority | pass: semantic definitions/native settlement remain authoritative; private preparation is derived |
| G2 Fidelity | pass: original source extents, packed choices, typed outcomes and archived contracts retained |
| G3 Validity | pass: trusted reuse has exact premises; new/untrusted outputs still validate |
| G4 Hidden behavior | pass: explicit invocation/worker ownership; CPU kernels have no publication effects |
| G5 Recovery | pass: bounded admission, parent claims/renewal and terminal fencing; independent-claim concurrency excluded here |
| G6 Transformation/reuse | pass: complete determinant-specific reuse and canonical source-preserving envelopes |
| G7 Claims | pass: target acceptance separated from implementation/provider/whole-book qualification |
| G8 Library leverage | pass: stdlib spawn/initializer/futures selected; no bespoke pool, broker or DAG |
| CI-G1 Fidelity | pass: original source/provider/release references, typed meanings and unknown states retained |
| CI-G2 Evidence closure | pass: exact pinned closure stays under native/read/export owners |
| CI-G3 Evaluation integrity | pass in scope: worker inputs are frozen production source/configuration/dependencies; no protected-reference or assessment-store route is introduced |

These are design-sufficiency judgments, not test results. DA-042's current manifestation is the
repeated book-demand release verification; O01–08 remain source functional-review opportunities,
not renamed diagnostic defects. No new rule reversal is identified. Implementation review must
check that cache constructors, validity and cancellation actually realize these premises.

## 8–9. Alternatives, foundations and execution fit

Keeping serial execution and merely caching a top-level call is simplest but leaves inner
reconstruction and parser placement unchanged. Threading complete demands keeps ambient readers,
provider borrowers and off-main-thread deadlines entangled. A global verification cache has a
smaller call-site diff but obscures validity and authorization lifetime. A general DAG/resource
framework adds another scheduler without a current cross-run requirement. Shared-memory/mapped
transfer is conditional on demonstrated movement burden; owned bytes are the simpler initial seam.

The selected scoped execution context plus regional owner and stdlib process pool offers useful
reuse without transferring live resources. It introduces packet serialization and worker startup,
while warm lifetime amortizes stable preparation. No measured speedup or memory bound follows;
whole-book fit still depends on later scheduling/provider work and the publication limit.

A1 satisfied, Proposed: coherent preparation/computation/effect ownership (FP-01/02/06).
A2 satisfied, Proposed: exact source, released operations, closure and outcomes govern behavior
(FP-04/05; DP-01/02/08/09; CI-01–06/10/11/13).
A3 satisfied, Proposed: ingest, standalone demand and book reuse the same boundary; kernels compose
without lifecycle ownership (FP-03; DP-14/17/18).
A4 satisfied within this increment, Proposed: preparation follows validity scope, bodies follow
consumer lifetime and pending work is finite (FP-07; DP-10/19/20/23; H12–20). Enclosing whole-book
execution fit remains unresolved and is not offset by these scoped judgments.

## 10. Verification shapes and limits

Use existing independent formal/protected-atom/choice expectations, mutation and forged-input
controls, real spawned process/main-thread round trips, startup/timeout/cancellation and bounded
state behavior. Native tests must cover actual publication/fencing; model mocks do not qualify
providers. No new benchmark, generalized validator or design-alignment lint is required.
Tests, probes and provider execution during this static review: **not_run**.

## 11. Authority changes

Only the source review's already accepted RC01–04 apply: independent work may overlap, provider
borrower ownership becomes explicit admission, verified immutable preparation may be reused, and
preparation/inference/reduction plus batch authentication acquire explicit seams. Record these in
ADR-0083 and D3/D4/D6/D8. No changed §B semantic meaning, source custody, knowledge standing,
provider output interpretation or public arbitrary-layer upload is introduced. If the prior stage-barrier rule were retained instead of accepted RC01, regional barriers would
remain. Retaining the prior borrower/preparation/batch rules instead of accepted RC02–04 would
prevent the intended hybrid target through these explicit reuse/lane/batch boundaries.

## 12. Bounded conclusion

Accept scoped the specified target contracts for BEP-00–03 and minimum07a. Implementers may begin
against them after architectural publication. This establishes neither assembled implementation
acceptance nor enclosing architecture acceptance. The [BEP coordinator](../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md)
owns actual disposition, required follow-ups and the later assembled review/qualification boundary.

## Assembled foundation assessment · 2026-11-11

**Accept scoped, Interface-checked**, the assembled BEP-01–03 implementation and required
CPU/regional07a prerequisite. This supplements the entry target judgment above. Inspected source
is539a437da plus the current BEP product edits in cli/orchestrate, methods/formal_evidence,
methods/construction_characterization, methods/contextual_interpretation, orchestrate/characterization,
orchestrate/commands, orchestrate/semantic, orchestrate/source_reader, semantic/characterization,
semantic/operations and new semantic/execution_preparation and semantic/cpu_execution. The combined
SHA-256 of sorted changed product paths and their bytes, each followed by a NUL separator, is
`0805f0f9f972fb9f26bb6803c76ae5966d913ba3b9a8d84622ead9728e2bea4e`.
This identifies inspected source before the root's final maintenance; whitespace-only maintenance
requires applicability reconciliation, and behavioral edits require affected reassessment.

VerifiedExecutionPreparation is constructed by full-loader success, explicitly shared through
internal book/demand, command capture/enrichment and ingest paths, and closed by its invocation.
The previously repeated regional full-loader calls are replaced by require_release on that owned
context. Standalone source execution owns its CPU scope. Existing database admission, task claim,
ScopedSourceReader borrowing and native exact completion remain in their original owners.

RegionalPreparation retains canonical source values and reconstructs separate working dictionaries
for each reader, so one reader's topology/layout or native-item mutation cannot alter another's
source body. Source selection is rechecked by BoundReader; protected layer cache hits read the
native manifest under the current run. Public LayerReport.payload remains fresh. Recursive proof
keys bind exact transitive dependency pins/content and the original PreparedRelease owner; strong
references prevent object-identity recycling after archive-cache eviction. Cached dependency proofs
can seed the scoped validator, while the new root is removed from that seed and validated again.
Decoded internal dependency metadata is deeply immutable. Proof bodies/keys consume the same
encoded-state budget and leave with the regional owner. This establishes a bounded private
metadata/proof view, not elimination of every public payload decode inside existing algorithms.

CPU method.run paths now call the shared parent adapter; former algorithms are private
_run_prepared kernels, not an optional legacy production backend. The child uses a finite
in-memory reader over transferred source/layer values and main-thread computation. Primary release
preparation lives with its worker; participating historical release preparations are per call and
do not accumulate across book regions. Construction vocabulary/matchers retain bounded worker-local
preparation. Narrow cost fields survive result transfer. Parent validation verifies canonical
results, exact base/scope/operation and request correspondence before ordinary native settlement.

Capsule hydration is explicitly private trusted-parent transport. It checks manifest identity,
boundary runtime, artifact correspondence and supported reconstruction; it does not claim that
reconstruct_release authenticates arbitrary self-consistent forged products against original source
inputs. Full execution verification and authentic historical opening remain parent responsibilities.
No public arbitrary-capsule admission interface is introduced.

The adapter enters admitted_inputs before loading dependencies, archived releases or source values.
Its private permit owns a submission slot and reserves the maximum packet/reply allowance through
hydration, transfer and parent validation. Secondary capsules are serialized inside that admission.
Waiting for another admitted transfer to release byte capacity is backpressure; a complete input
that cannot fit the remaining fixed regional state refuses explicitly. Capacity-one is the selected
initial production route. The budget covers retained encoded bodies and bounded transfer payloads,
not interpreter/native RSS. Reserving the maximum transfer allowance trades utilization for simple
finite admission; final operating counts and broader concurrency remain07b/05 responsibilities.

Stop state is invocation-owned; waiting/reading adapters check claim lifetime, worker kernels use
cooperative stop and existing deadlines, and the parent discards stale replies. Exceptions during
execution terminate the owned pool after bounded drain. Current serial integration permits
operation-wide stop; this does not qualify independently cancellable concurrent durable claims.

A1–A4 and G1–G8 are satisfied at Interface-checked strength for these bounded responsibilities.
CI-G1 fidelity is preserved through unchanged semantic kernels and exact positioned inputs;
CI-G2 evidence closure remains under original native/read/export owners; CI-G3 retains the
production-only frozen input route, without a protected assessment/reference path. No unresolved
MUST gap was found in this inspected scope. These judgments do not establish tests passed,
provider accuracy, measurable speedup, whole-book execution fit or full07a/07b completion.

Tests/providers/probes by this reviewer: **not_run**. The coordinator owns actual receipts and
final-source/context applicability, including failed native attempts during concurrent source edits;
none are relabelled passed by this assessment. Keep the independent regional-ready coordinator,
provider lanes/batching, final policy/device investigation and run610 publication-size limit open
under the BEP coordinator. No text-characterization completion or plan reconciliation follows.
