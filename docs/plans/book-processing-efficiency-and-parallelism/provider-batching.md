# Compatible provider batches and attributed results

<a id="BEP-06"></a>

**Status: Native authentication/cross-region coalescing delivered; BEP-06 implementation remains incomplete for local GLiNER batching and aggregate PM2 byte admission (audit2026-11-12).** This companion develops **BEP-06**, implementing selected
[O05](../../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md#O05).
The [series coordinator](../book-processing-efficiency-and-parallelism_2026-11-11.md) owns shared
contracts, package state, opportunity disposition, investigation coverage and assembled acceptance.
The operator accepted **RC04** on 2026-11-11: separate preparation, inference and deterministic
reduction, migrating GLiNER batch authentication and projectors together. Acceptance authorizes the
target and its decision route; the delivery section below records the implemented CPU slice.

Planning baseline is main `f81a380cd`; inspected production source is `4d0ca7eb7`, dated
2026-11-11. No provider, probe, test or database operation was run while authoring this companion.
TC-E06 indexes, TC-E07 line-safe literals, existing model residency and existing native batches
are implemented baseline, not work claimed by BEP-06. The existing TC plan retains its scope.

## Resulting capability and responsibility

An ordinary characterization operation can submit compatible ready inference requests in bounded
native batches while retaining each request's exact source context, released questions, candidate
population, provider/runtime selection, outcome and recovery owner. A batch groups computation;
it never concatenates passages into a new language context or turns a provider-local index into a
source coordinate. Requests from several admitted regions can share a provider invocation when
the same compatibility and attribution contract qualifies that grouping.

The provider lane receives prepared immutable requests, admits a bounded compatible population,
executes the selected native batch API and returns an attributed response for each member. The
coordinator owns durable task identity, claims and completion; one owner reduces each region's
responses into its builder in the declared stable order. Provider callbacks do not concurrently
mutate builders. Semantic families remain distinct even when one physical invocation serves them.
The [D6 lifecycle owner](../../design/D6-orchestration-metrics-policies.md),
[ADR-0081](../../adr/0081-enriched-document-analysis-layers.md) and
[ADR-0082](../../adr/0082-explicit-analysis-selection.md) continue to govern private standing,
source attribution, exact dependency closure and active-analysis selection.

The principal benefit is avoiding scalar admission and underfilled invocations where compatible
work exists, while keeping resident models useful across regions. This is **Proposed**, not a
throughput claim. FP-04/07, A2/A4 and H2/8/10/12/16–24/28 favor this realization over one model
replica per task, unbounded queues or another scheduler. Native batching does not justify creating
more inference demand, dropping a family, widening a context or waiting indefinitely to fill a
batch. A standalone demand must make progress with its available population.

## What already exists and what changes

References identify the inspected source revision; line numbers below are orientation, not frozen
interfaces. Installed provider environments and exact dependency pins are authoritative during
implementation.

| Provider path | Existing capability to preserve | BEP-06 change and consequential conditions |
| --- | --- | --- |
| spaCy | [ingest/annotations.py](../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py), lines236–279, streams prepared Docs through `Language.pipe(..., as_tuples=True, batch_size=..., n_process=1)`; [sentences.py](../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py), lines56 onward, caches the selected pipeline. Native text/layout/token checks protect atom-preserving inputs. | Keep this native batching and residency through method-seam changes. Feed compatible prepared inputs without retokenizing them. Adding `n_process` is not the selected whole-pipeline execution mechanism; any later selection must fit BEP-04/07 ownership and avoid nested process pools. |
| HanLP | [native_evidence.py](../../../python/corpus-structure/src/corpus_structure/methods/native_evidence.py), lines179–264, admits each sentence with `prepare_only`, then packs inference using actual subword lengths, sentence/character and padded-subword bounds. [pm2_hanlp.py](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp.py), lines72–112/159–205, uses actual task transforms/dataset samples and one multitask `model(sentences, tasks=..., skip_tasks="tok", resolved_tasks=...)` invocation. | Deliver bounded bulk sentence admission and correct member results. Investigate whether the installed native route can reuse the exact prepared samples through inference without duplicating native planning. Reuse is selected only if its complete supported route preserves word/subword correspondence, head population and native preparation behavior. Every sentence remains whole. |
| D1 | [model_characterization.py](../../../python/corpus-structure/src/corpus_structure/methods/model_characterization.py), lines455–558, batches ready independent question jobs by sixteen while retaining per-job prior answers and real question-stage dependencies. [pm2_native.py](../../../python/corpus-structure/src/corpus_structure/methods/pm2_native.py), lines117–156, invokes native `system_one_batch(..., set_size=16)`, repacks by row length and scatters by request ordinal. | Preserve these capabilities; expose compatible ready jobs to the lane across admitted regions. Keep each original state, context, options, candidate population and prior-answer prerequisites. A ready job need not wait for an unrelated region's question stage. Do not replace native length packing with a second application packing engine. |
| GLiNER | [gliner_worker.py](../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py), lines157–218/350–384, already calls `model.batch_extract` with bounded inputs under one selected pack/profile/policy and one active exchange. Characterization currently sends singleton cue and function scopes. | Batch compatible scopes and migrate the complete batch/member authentication path. Native report computation/request digests bind the full admitted input population. [classification authentication](../../../python/corpus-structure/src/corpus_structure/methods/pm2_gliner_classification.py), lines156–201, and [cue projection](../../../python/corpus-structure/src/corpus_structure/semantic/model_characterization.py), lines957–1008, currently reconstruct singleton digests; changing only the tuple length is incorrect. |
| Maverick / DiPO | [contextual_characterization.py](../../../python/corpus-structure/src/corpus_structure/methods/contextual_characterization.py), lines441 onward, supplies different native requests: canonical sentences for Maverick, exact context text for DiPO. | BEP-04 overlaps their independent lanes. BEP-06 batches them only if a focused examination of the selected provider interface establishes independent-document/context semantics and useful native support. Lack of such a route leaves scalar requests in their concurrent resident lanes; it does not block the selected HanLP/D1/GLiNER delivery. |

## Shared contract and working integration dependencies

Package identifiers below refer to the coordinator's authoritative package definitions. An agreed
contract permits internal design; only the working prerequisites permit production integration.

| Input | Needed contract or capability | Availability required by BEP-06 |
| --- | --- | --- |
| [BEP-00](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-00) | Request/member identity, physical batch provenance versus result-affecting determinants, exact source/release/runtime binding, ordering, attributed outcomes and cancellation ownership. RC04's architectural/model route is recorded there. | Settled shared decisions before fixing new report/request identity or public method seams. Internal API/source research can begin earlier. |
| [BEP-04](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-04) | Working resident provider lanes and preparation/inference/reduction seams, with explicit ownership instead of implicitly borrowed `ContextVar` sessions. | Actual lane admission, dispatch, response and close behavior before claiming production batching integration; a type sketch or accepted lane design is insufficient. |
| [BEP-05](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-05) | Working completion-driven coordinator, region/task association, claim renewal and fenced completion, with bounded ready work and deterministic reductions. | Actual multi-region dispatch/completion before qualifying cross-region batches. Local compatible-scope batching can be integrated and checked earlier against the same contracts. |
| [BEP-07](../book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-07), early slice BEP-07a | Early resource-policy contract: provider/profile/device compatibility, native thread settings, queue/input/reply/resident bounds and supported operating choices. | Agreed policy before choosing packing/admission limits; effective working child settings before selected real-provider qualification. BEP-06 does not wait for every later resource experiment to begin internal design. |

The package returns compatible batch admission and response/projection capabilities to BEP-04/05,
plus the selected provider evidence and limitations needed by integrated qualification. It does
not own worker counts, GPU selection, database publication or a second durable queue. Changes
affecting common packet or identity fields must be reconciled with BEP-00/04/05 before dependent
implementations rely on them. Source files in the table are shared integration surfaces, not
exclusive editing authority for a future worker.

## Batch contract and physical execution

A member binds its original logical request and source ordinal to the exact provider input,
selected release/runtime/artifacts, method/question/pack policy and the task attempt or other
coordinator-owned borrower association. The batch envelope records its complete ordered admitted
population and selected physical inference policy; each returned member identifies that envelope
and its member ordinal. Reuse the existing request/report representations where they can carry
this meaning. Conceptual names do not require a new service, persisted record or generic framework.

Compatibility is provider-specific. GLiNER members share the exact `GlinerPack`, profile,
threshold, overlap policy and installed inference policy, while each keeps its own context ID,
digest and source mapping. Cue and classification packs remain separate compatible groups unless
the actual combined native API and semantic contract qualify a deliberate replacement. D1 jobs
must have their required prior answers and candidate populations before becoming ready. HanLP
members share native runtime, multitask head/profile selection and device policy; actual lengths
govern admission. No provider batch crosses a changed release/runtime/profile merely because the
model name matches.

The lane fills batches from already admitted useful work under count, input-byte, token/padding
and reply bounds supplied by the provider and BEP-07a. It submits available smaller populations
when waiting would obstruct standalone or remaining useful work. The coordinator bounds the
combined ready/queued/in-flight/reply state; a bound on one native call alone is insufficient.
Packing should delegate to existing native capabilities where available. Retain useful complete
members when one member is unsupported, invalid or cancelled, but never interpret a malformed
whole envelope as valid attributed output.

**Identity is settled before task formation.** BEP-06-I3 below determines whether changing batch
membership/order affects selected provider results or their declared reproducibility. When
qualified as physical placement only, record the actual envelope as computation provenance and
preserve each logical request identity. If grouping is result-affecting under the selected
contract, bind the exact group or governing inference selection into configuration/input identity
before the coordinator creates dependent tasks. Do not rewrite a registered task's identity,
infer a missing member, or let completion timing silently choose semantic determinants. Stable
grouping is a concrete alternative when required, with its possible waiting/packing tradeoff
stated. BEP-00 owns the shared rule; BEP-06 implements its provider-specific realization.

Whole-batch validation authenticates the exact envelope/population/policy and cardinality. Member
validation authenticates context, ordinal, native report, effective runtime and source mapping.
GLiNER's existing request/observation digest and effective-profile checks remain shared between
cue and classification consumers; introduce batch-aware authentication there rather than a
second projector-specific validator. Per-item reduction uses the authenticated native member and
original mapping. Physical batch membership must not falsely relabel a source scope as evaluated
or turn an unknown/unsupported member into successful empty coverage.

Cross-region batches have multiple logical cancellation owners. Before dispatch, drop cancelled
uncommitted members and form/authenticate the actual admitted envelope. After dispatch, a stale
member loses completion rights; useful surviving members may finish. Do not reuse that ordinal
for another request. Cancel shared native work when invocation cancellation or loss of every live
borrower removes its usefulness. Any contract-required change in the admitted population creates
an actual new envelope; the original outcome remains attributable. Lane crash retires the lane
and follows existing coordinator/task retry policy, never an additional provider retry loop.
Publication and uncertain publication recovery remain the coordinator's fenced durable route.

## Bounded investigations before dependent implementation

These are mandatory questions with finite decision outputs, not a benchmark campaign or optional
future research. Inspect the installed version/source first; use a small retained functional
probe only where the consequential behavior remains uncertain. During execution, place necessary
probe evidence and records through the existing evidence route. Source inspection can settle an
unsupported API; it cannot establish actual selected-provider fidelity on its own.

| ID | Question and bounded settling evidence | Decision output and dependent work |
| --- | --- | --- |
| BEP-06-I1 | Examine installed HanLP task transform, dataset/dataloader, native multitask dispatch and model call at the selected pinned revision. Establish how bulk admission reports each original sentence's actual subword length, and whether inference accepts/reuses prepared samples without retokenizing or changing head execution. If source leaves uncertainty, exercise only representative short/long, mixed-size and inadmissible sentences through the real selected path. | Choose the complete supported prepared-sample route and verify word/subword/head correspondence, or explicitly retain native inference preparation while delivering bulk admission. Do not introduce an application imitation of HanLP's planner. Settles the HanLP implementation branch before removing any preparation checks. A supported reuse route is implemented when found; unsupported reuse closes that branch with its reason rather than leaving an open speedup promise. |
| BEP-06-I2 | Trace `request_digest`, `GlinerWorker._exchange`, report creation, `authenticated_gliner_report`, `classification_product` and `project_gliner_cues`. Settle one exact batch/member envelope shared by both projectors, including retained report/replay meaning. Use independently authored mismatch cases and a real compatible multi-context response to settle binding and scatter. | Specify and implement batch-level authentication plus member association through both producers and affected retained/detached consumers. Any needed released schema/operation-version change goes through BEP-00's authority route. Blocks GLiNER batching cutover, not preservation of current native calls during investigation. |
| BEP-06-I3 | For selected real HanLP/D1/GLiNER paths, compare singleton and compatible mixed-size batches, reordered members, and admissible regrouping on the same exact source inputs. Inspect the native numerical/packing behavior and distinguish expected numerical variation from changed semantic output or attribution. Do not assume identical bytes across arbitrary batch/device choices. | Record each provider's qualified compatibility, inference-identity and stable-grouping rule under BEP-00, with any supported variation and limits. Apply the rule before cross-region task identity/dispatch. A device-policy change consumes BEP-07's actual qualification; CPU evidence does not qualify CUDA. |
| BEP-06-I4 | Through working BEP-04/05 lanes, exercise one cancelled/stale member with useful siblings, whole-operation cancellation, a partial/invalid reply and a provider crash. Observe ownership, exact admitted envelope, completion fences, retained siblings, bounded outstanding state and lane retirement. | Close cross-region cancellation/failure integration only when the working route preserves member attribution and existing retry ownership. A prior contract agreement or mocked provider result does not satisfy actual provider obligations. |

## CPU and selected-device prerequisite slices

BEP-06 first delivers and qualifies the working CPU batch route, including envelope/member
authentication and cross-region borrower handling. BEP-07b consumes that working slice to select
and qualify device/runtime arrangements. Each newly selected device profile then receives its
BEP-06 batch-specific qualification before BEP-09. CPU completion does not qualify CUDA batches;
a GPU batch prerequisite does not prevent CPU delivery. BEP-06-I3 records the separate scope of
each result. Whole-package completion is not a prerequisite in both directions.

## BEP-06 delivery and consumer migration

First settle the BEP-00/BEP-07a interfaces and the internal investigations needed for the selected
provider routes. Preserve current spaCy and D1 native batches while exposing their inputs and
responses at the BEP-04 seams. Deliver HanLP bulk admission and its settled prepared-sample
choice; deliver GLiNER batch-aware shared authentication, producers and projections together.
This can use already available compatible scopes inside an operation while coordinator work
continues. Complete cross-region batching through the actual BEP-04/05 dispatch, cancellation and
reduction paths after their working prerequisites exist. Provider-specific bounds and useful
progress under short populations are part of the capability, not follow-up tuning.

Migrate all affected entry points to those same seams: public standalone
`execute_characterization_demand`, post-capture `characterize_captured_run` used by ingest, and
the explicit selected-view/retained-layer analytics route. Analytics and replay continue reading
the selected settled evidence without starting inference. Rule-only contextual refreshes keep
their exact retained-native reuse; a new batch facility must not force providers to rerun or
select obsolete interpretations from retained closure. The ordinary method graph remains usable
for its supported callers with the same authoritative implementation; do not leave an old
singleton-only projector or serial inference implementation as a hidden alternative.

Existing durable products retain their original truthful read/replay contracts. Where the new
batch envelope changes persisted shape or inference meaning, update the owning released types,
operation versions and affected live/detached readers within the same delivery, using the existing
authority route. Do not rewrite historical products or manufacture missing batch provenance for
them. Remove superseded singleton digest reconstruction and obsolete mechanism-specific tests
after their consumers migrate; preserve independent source/semantic expectations and deliberate
invalid native controls. No new provider service, batch ledger or compatibility adapter is
required merely to stage the change.

## Completion evidence and limits

BEP-06 acceptance requires the selected working provider routes and consumer migrations, not only
a batch-capable method signature. Targeted checks cover:

- Mixed sizes and distinct but equal-text contexts preserve member cardinality, stable reduction,
  exact source extents, tokens, head/answer association, candidate identity and family coverage.
  Native provider limits preserve unsplit sentences and honest unsupported/partial outcomes.
- Wrong/missing/duplicated/reordered members, wrong pack/profile/release/runtime, altered envelope
  or ordinal, stale request digests, invalid native content and forged observation attribution
  refuse at the owning shared validator. An invalid member cannot contaminate useful siblings.
- D1 dependencies remain per job: unresolved premises block only dependent questions; unrelated
  ready jobs can run. spaCy retains atom/layout checks and native `pipe` batching.
- Standalone small demands, ingest after authentic capture, retained-native refresh and explicit
  analytics selection preserve their supported behavior; replay/export reads the exact new or
  historical product closure without inference. GLiNER cue/function consumers both authenticate
  the real batch envelope and original member context.
- Working cross-region cancellation, crash and fencing scenarios in BEP-06-I4 preserve useful
  siblings and prevent stale publication. BEP-07 bounds cover buffers and native execution
  together; increasing batch size does not bypass admission or delay every remaining member.

Use targeted existing method/native/control tests and narrowly added independent expectations
where behavior changes; do not mirror the projector to generate its expected output. Run selected
actual providers for their native obligations and retain failed/interrupted results. Package
verification feeds the coordinator's final required union; it does not trigger a full campaign
after each edit. Commands and managed receipt IDs are recorded when executed under the `ci`
workflow. Current scoped checks and their actual outcomes are recorded in the coordinator and the delivery section below.

No measured speedup, numerical optimum or new benchmark obligation follows. Completion establishes
correct compatible batching, removed scalar admission where selected, complete attribution and
integration with bounded useful parallelism. Quantitative benefit claims require separate
representative measurement if later made.

## Delivered CPU batch contract and investigation decisions

- **I1 / BEP-I02:** HanLP2.1.7's supported multitask predict route does not accept reusable prepared
  samples. Bulk native admission returns each original sentence's actual subword length and
  limitations; inference retains native preparation. No application tokenizer/planner imitation
  or deferred unsupported prepared-sample promise remains.
- **I2:** Current GLiNER producer2 emits a compact v2 header, ordered exact logical member hashes
  and ordinal-bound observations. Whole-population admission and shared member authentication
  cover cue/function projection and retained replay. Historical v1 uses its original authenticated
  policy and request/observation hashes, without manufactured provenance. HanLP producer2 sentence
  annotations retain native_batch; D1 retains its exact member/cohort receipt. Shared validators
  own strict header, cohort, ordinal and exact request checks.
- **I3 / BEP-I03:** ADR-0085 selects released CPU float32 native numerical semantics. Raw returned
  scores and thresholds remain unchanged. Actual grouping is authenticated provenance; authentic
  retained observation reuse does not promise bitwise-identical fresh inference. GLiNER confidence
  varied in the bounded real panels, while discrete outputs agreed there. This is no universal
  epsilon or threshold-stability claim. The corrected production panel uses nested cues and flat
  function classification; earlier flat-cue panels remain explicitly superseded.
- **I4:** Eight actual HanLP/GLiNER lane scenarios cover stale borrowers with useful siblings,
  invocation cancellation, owned native-child crashes and individual GLiNER byte/native-preparation
  refusal. Useful members retain actual envelope/ordinal and original context; all probe-owned
  children drain and budget returns to zero. Controlled corruption tests and native DB tests
  supply their separate obligations. This is bounded CPU evidence, not every provider/device
  crash combination.

The [evidence owner](../../design_review/evidence/2026-11-11_book-provider-batches/README.md)
retains exact commands, raw replies, source checks, failed attempts, numerical limits and record
supersession. Native probe execution predates the final lazy-admission repair; unchanged worker/
coalescer semantics remain applicable, while the final root union qualifies admission and DB
integration. spaCy annotation now runs through detached CPU work while retaining native pipe and
atom/layout checks. D1 preserves native16-job length packing and actual per-job dependencies.
Maverick/DiPO retain independent scalar-document semantics in concurrently admitted resident lanes;
no qualified multi-document native batch API was selected for them.

Public demand and capture enrichment use the same method plans, lane owner and parent reduction.
The JSONB optional native_batch field requires a new semantic release, not a physical column.
CUDA-specific batch qualification remains conditional on BEP-07b's selected device profiles.


## Historical selected D1 device and native-order correction · 2026-11-11

Operator steering2026-11-11 requires D1 CUDA/BF16 for current primary and managed execution.
There is no CPU execution fallback. ADR-0086 records that selected inference profile; other07b
GPU profiles/counts remain later. The original D1 CPU panels remain authentic historical evidence
and do not qualify current D1. Actual CUDA batching, questions/source projection and owned GPU
teardown must pass under the current selected profile before this increment closes.

The first actual CUDA probe confirmed native CUDA/BF16 execution but exposed sorted question/
option keys in the new lane's canonical JSON transport. The declared QuestionRequest intentionally
preserves that order. The repair separates order-preserving native wire/reply bytes from semantic
canonical hashing. PM2 receiptv2 commits each member's ordered native bytes and a version-domain
cohort hash; current D1 authoring requires that receipt and actual CUDA/BF16 startup. Originalv1
receipt reads retain original canonical semantics. This restores the existing declared-input
contract; it does not select a new semantic question order. The new semantic release/policy and
CUDA configuration/runtime retain their own exact identities. Native question/dependency checks
and unsupported/unknown outcomes remain intact. BEP-E02 and the coordinator own final receipts.


Final second-increment acceptance2026-11-11 is **scoped-qualified** in the coordinator:
236 functional/managed-admission controls,186 adjacent controls and4 actual native document-path
checks passed after final source freeze. The CUDA D1 ordered-question/cohort/source/custody panel
also passed. BEP-E02/E03 are closed there; BEP-E01 and other07b/08/09 scope remain open. The
coordinator owns exact commands, receipt IDs and source/context applicability.


## Completion audit boundary · 2026-11-12

The [coordinator audit](../book-processing-efficiency-and-parallelism_2026-11-11.md#completion-audit)
retains shared current/historical authentication, exact source/member projection and the bounded
selected-provider panels. It does not infer local batching from cross-region coalescing.
Model characterization still awaits each local cue/function singleton before exposing the next
scope (BEP-E10). PM2 compatibility checks counts/padding but not the merged frame size, so legal
requests can fail only because of grouping under a supported smaller byte policy (E11).
Complete those accepted obligations through the existing authenticated lane and stable reduction.
Current disposition/qualification remains with the coordinator; no new provider/test execution or
measurement was performed. Other-provider CUDA and multi-document Maverick/DiPO batching remain
outside the explicitly selected operating scope.
