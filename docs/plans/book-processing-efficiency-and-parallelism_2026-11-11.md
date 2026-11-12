# Book-processing efficiency and parallelism

**Status: BEP-00–06 selected scope and required07a implemented/scoped-qualified; other07b/08/09 planned · Authored2026-11-11.** Owns BEP-00–BEP-09 and the scheduled disposition of the [source review](../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md)'s O01–O08 and RC01–RC04. This coordinator owns combined acceptance and investigation decisions; companions own the detailed contracts identified below.

## Authority, scope and baseline

Planning input is the review at commit f81a380cd, inspected product source4d0ca7eb7. The initial authoring changed no production code. RC01–RC04 were explicitly accepted by the operator on2026-11-11; current implementation and scoped qualification are recorded below.

The target is comprehensive processing of the retained Grinstead–Snell book:316 natural SourceViews over the original518-page document, every selected characterization family, independently useful layers and one combined document view. Preserve context, source coordinates, provider attribution, packed choices, coverage and uncertainty. Reuse authentic native capture rather than repeating PDF recognition.

This is a standalone series. Existing text-characterization plan files are intentionally unchanged and supply no sequencing authority. BEP does not claim or transfer TC completion, outstanding semantic assessment, or TC-E01–07 disposition. Current implemented contracts and retained evidence supply integration inputs. Reconciliation of the TC plans is a separate later task, after this scope completes.

The operator chose to keep the current book running unchanged during authoring. Future production changes must occur only after its bound execution has settled or an explicitly authorized cancellation has drained owned work. Preserve earlier outputs and unsuccessful attempts; a live run is not qualification of this target.

[D6](../design/D6-orchestration-metrics-policies.md), [D3](../design/D3-database.md), [ADR-0081](../adr/0081-enriched-document-analysis-layers.md) and [ADR-0082](../adr/0082-explicit-analysis-selection.md) govern the implemented baseline. Apply [core principles](../design_review/design_principles/core/design-principles.md), [efficiency heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md), code-intelligence profile and binding through standard.toml. Focused foundation assessment here does not initiate a broad audit or certify the enclosing architecture.

The retained source basis is project nce-grinstead-snell-full-book, capture496/cut614, release c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189. Native input is task1627/product integrated/digest35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb. The original PDF digest is763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e. Preserve inherited display/inline/cell recognition and source-health limits separately from source membership.

## Combined target and foundation assessment

One invocation-owned coordinator advances a bounded set of ready natural units. Warm spawned CPU workers execute parser-bearing kernels on their process main threads. Persistent provider/profile lanes retain model state and service compatible requests. Independent inference returns private responses; each regional builder reduces them in stable source/provider/question order. The coordinator owns task/run supervision, publication and final composition.

Current strengths survive: exact retained source, immutable published products, native claim/attempt fences, selective source reads, manifest composition, existing spaCy/D1 batching, model residency, and TC-E06/07 corrections. Current obstacles are the serial regional comprehension, synchronous singleton scheduling, repeated full release rederivation, repeated dependency reconstruction, ContextVar borrower refusal and scalar provider preparation. These need changes across actual consumers, not another wrapper around the present serial loop.

The source reader temporarily rebinds its connection; it is not a transferable worker object. PreparedRelease may contain non-picklable compiled state. LayerReport.payload currently returns a fresh mutable value. Existing cross-run stage products cannot be replaced with hypothetical dependency pins. These foundation judgments shape BEP-01–05.

Physical concurrency is separate from semantic family selection. Batch membership, precision and device can affect inference and therefore need explicit identity/provenance treatment. Pure placement choices should not arbitrarily become semantic differences or weaken complete reuse keys.

Initial topology selects one resident per provider/profile, a finite CPU pool and bounded regional admission. Exact operating counts are settled in BEP-07b before integrated qualification. Capacity-one diagnostic execution uses the same implementation; retaining a second legacy serial backend is not selected.

## Operator-confirmed rule changes

| Item | Decision2026-11-11 | Consequence and implementation route |
| --- | --- | --- |
| RC01 | Accepted explicitly | Permit independent-unit/producer overlap; BEP-00 records the decision and updates D6's barrier policy before dependent implementation. Real dependencies and final settlement remain. |
| RC02 | Accepted explicitly | Replace ambient exclusive borrower refusal with operation-owned lane admission; BEP-00 records ownership, BEP-04 replaces the old mechanism with teardown guarantees preserved. |
| RC03 | Accepted explicitly | Reuse fully verified immutable preparation within scope; BEP-01 preserves uncached live DB admission. Architectural rationale/owner updates are scheduled by BEP-00. |
| RC04 | Accepted explicitly | Separate preparation/inference/reduction and migrate batch authentication with projectors; BEP-03/04/06 deliver the working seams under BEP-00's recorded target. |

BEP-00 uses the ADR skill and applicable D3/D4/D6/D8 owners for durable rationale; accepted ADRs remain immutable and are superseded only where necessary. No additional rule reversal, general cross-run DAG or changed semantic-family target is approved by these decisions.

## Package ownership and execution dependencies

BEP-00–03 are **implemented and scoped-qualified** by the first-increment receipts below. BEP-04/05, BEP-06 batching and required07a are implemented; operator-required D1 CUDA/BF16 qualification passed in this increment, with final scoped acceptance below. Other BEP-07b/08/09 remain **planned**. An agreed interface permits design work; working integration requires delivered prerequisites.

| Package | Required input | Delivered capability and owner |
| --- | --- | --- |
| <a id="BEP-00"></a>BEP-00 | Review, acceptedRC decisions, current source | Record target decisions, source/worker/attempt/branch contracts and formal review route; coordinator owns shared target. |
| <a id="BEP-01"></a>BEP-01 | BEP-00 preparation validity | Once-per-operation/address-space verified release preparation, consumed throughout internal execution; [prepared state](book-processing-efficiency-and-parallelism/prepared-state-and-cpu-kernels.md). |
| <a id="BEP-02"></a>BEP-02 | BEP-01, BEP-07a early capacity contract | Bounded authenticated regional hydration/index/validation reuse; same companion. |
| <a id="BEP-03"></a>BEP-03 | BEP-00 CPU packet decision, BEP-01/02 working inputs, BEP-07a | Main-thread CPU kernels in warm spawn workers with owned results; same companion. |
| <a id="BEP-04"></a>BEP-04 | BEP-00, BEP-01/02, BEP-07a | Resident lane admission and independent private inference branches; [coordinator/lanes](book-processing-efficiency-and-parallelism/coordinator-and-provider-lanes.md). |
| <a id="BEP-05"></a>BEP-05 | BEP-03/04 working computation, BEP-07a | Bounded ready frontier, exact child registration, coherent publication and recovery; same companion. |
| <a id="BEP-06"></a>BEP-06 | BEP-04/05 plus batch decisions and capacity contract | Compatible native batching with exact envelope/member authentication and cancellation; [batching](book-processing-efficiency-and-parallelism/provider-batching.md). |
| <a id="BEP-07"></a>BEP-07 | Early: BEP-00. Full: working BEP-03–06 | Early shared policy/admission contract, then coordinated thread/device/count decisions and CUDA qualification; [resources/operations](book-processing-efficiency-and-parallelism/resources-devices-and-operations.md). |
| <a id="BEP-08"></a>BEP-08 | Early policy/status contract; working BEP-05–07 for cutover | Migrate existing demand/ingest/analytical entry points, status and cancellation, retire superseded paths; same companion. |
| <a id="BEP-09"></a>BEP-09 | BEP-01–08 integrated, required investigations settled | Final functional/provider/nonfunctional union, actual full-book execution and pinned consumers; [qualification/investigations](book-processing-efficiency-and-parallelism/integration-qualification-and-investigations.md). |

BEP-07a is an early prerequisite slice, not a requirement to finish CUDA work before implementing CPU concurrency. Provider-specific design and operational surface design can overlap kernel work once their contracts are settled. BEP-03/04 share method seams and must coordinate edits. BEP-05 cannot integrate stubs instead of actual worker/lane completion. BEP-06 and later07b may progress by provider; combined acceptance waits for their selected obligations.

BEP-06 first delivers working CPU batch contracts and integration. BEP-07b can consume that slice to select device arrangements; any newly selected CUDA profile then receives device-specific BEP-06 batch qualification before BEP-09. Native-thread API inspection can start under07a before this join. These are prerequisite slices, not a requirement that06 and07 finish before one another.

## Review correspondence and scheduled disposition

| Source | Disposition / responsible package | Closure meaning |
| --- | --- | --- |
| O01 | Implemented/scoped-qualified BEP-01 | Full preparation amortized over valid scope through all execution layers; live admission preserved. |
| O02 | Implemented/scoped-qualified BEP-02 | Bounded immutable regional reuse with fresh-value public APIs and trust protections. |
| O03 | Implemented/scoped-qualified BEP-05 | Independent regions progress without unrelated ordering barriers. |
| O04 | Implemented/scoped-qualified BEP-03/04/05 | Main-thread CPU execution, resident lanes and deterministic private-result reduction work together. |
| O05 | Scoped-qualified CPU HanLP/GLiNER and CUDA-required D1; other devices remain07b | Existing batching preserved; selected native admission/batch contracts migrated and qualified. |
| O06 | Required07a and selected D1 CUDA slice delivered; other devices/final counts remain BEP-07b | Coordinated policy delivered; mandatory CUDA investigation and selected profiles explicitly disposed. |
| O07 | Scoped05/07a implementation; enclosing09 remains open | Fences, renewal, DB progress, proportional recovery and exact composition remain effective. |
| O08 | Planned BEP-08 | Existing operations expose policy and meaningful capacity/prerequisite progress; cancel/resume usable. |

The investigation and capability tables in the qualification companion are part of this coordinator's scope; they do not create another execution ledger. Opportunities remain opportunities, not relabelled diagnostic defects. New execution findings belong here with responsible component, consequence and closure evidence.

## Completion and adoption boundary

Complete every baseline package, settle mandatory investigations and record triggered conditional decisions. Preserve518-page/source-family accounting, original recognition limits, deterministic supported structure and honest partial outcomes. Qualify actual providers and retained consumers; mocked execution establishes only local behavior. No universal accuracy or speedup threshold is invented.

Implementation performs targeted checks during delivery. After complete functional scope and final maintenance, run applicable uv run ci test and uv run ci check, explicit native/provider selections and the retained required test-identity union. Documentation uses uv run ci docs check. Original failed/interrupted receipts remain; later evidence must match final source/context or have an explicit applicability judgment.

Private deployment/regeneration is distinct from default activation, project selection and promotion. Those final effects require their existing authority. The later handoff identifies actual implemented changes and remaining TC reconciliation; it does not edit TC plans as part of this series.

## Authoring outcome

Created the new series only, plus publication/checkpoint links. Product tests, native execution, migrations and benefit measurements for BEP: **not_run**; this is plan authoring. Independent coherence assessment found no material coverage/authority gaps; its CPU/device prerequisite ambiguity was corrected in this coordinator and both affected companions. The TC plan paths were checked unchanged against HEAD. uv run ci docs check --json: **passed**2026-11-11, result5da6588a33f4441490a36dffd3c97e1c,880 canonical pages/zero link errors. git diff --check: **passed**. Production/provider checks remain **not_run** for this authoring-only scope.

just turn-end: **passed**2026-11-11,1122 Python files unchanged. No production or existing TC plan edits occurred.

## Authorized first increment · 2026-11-11

The operator authorized BEP-00–03 and the minimum BEP-07a prerequisite slice from the
conversational execution approach. BEP-04–09, provider lanes, batching, CUDA and final operating
counts remain later scope. TC plan files remain unchanged. Source baseline is539a437da.
BEP-00 publishes shared contracts and the scheduled target review before dependent production
implementation. BEP-01/02 integrate verified invocation preparation and bounded regional ownership;
BEP-03 integrates actual formal/construction/contextual-evaluation kernels in warm spawned workers.
Current regional scheduling order remains until BEP-05. The contextual evaluator does not call
SymPy; unrelated scientific/domain consumers are outside this increment.

### Execution findings

| ID | Responsible component / disposition | Evidence and consequence |
| --- | --- | --- |
| BEP-E01 | Native-evidence production/publication; open, required before full-book qualification | Run610/task2528 failed when publication exceeded the existing8MiB layer contract. `uv run ci status 610 --project nce-grinstead-snell-full-book --json` passed2026-11-11: failed run, terminal supervisor/readiness, zero unresolved agents/orphans. Original failure remains in native history and build/tc11-book-execution.log. No cap change, semantic truncation or book restart is included in00–03. Transport bounds do not repair an oversized canonical product. |
| BEP-E02 | D1 device selection; closed in this increment | Actual two-prose-region capture exposes the incorrect CPU default: D1 exceeds120s and produces failed/unavailable family coverage. Original91203c735f4b4b1e87dddfa0f6dd89a2 and diagnostic retryf0766f5fa43141029e614de30b99e2e0 remain failed. Operator requires D1 always CUDA (2026-11-11). Current D1 configs/launches require CUDA/BF16 with120s inference and no CPU fallback. Native question/cohort/source/custody qualification passed bep.d1-cuda-ordered-native; actual captured-prose/native publication passed4/4,6dfe911f0ea14484a2bcd95d8bda8635. The tentative600s CPU override is removed. |
| BEP-E03 | PM2 native transport/member authentication; closed in this increment | Actual CUDA literal-question probe exposed canonical JSON sorting of meaningful declared question/option/state order in new client/coalescer/reply seams. Shared ordered-native codec and version2 member/cohort receipts restore the existing contract; originalversion1 reads retain original hashes. Focused58 controls passed1918758d82714f83af87baad129fb849 and actual CUDA ordered/source checks passed; final current-source native publication passed4/4,6dfe911f0ea14484a2bcd95d8bda8635. |

Qualification for this increment is targeted preparation/trust/native-publication and actual-spawn
behavior. It does not establish final policy, provider parallelism or whole-book qualification.
Implementation and check receipts will be recorded here against the integrated source.

### First-increment implementation and scoped verification

**Implemented; scoped checks2026-11-11.** ADR-0083 and the
[foundation review](../design_review/reviews/design_review_book-execution-foundations_2026-11-11.md)
record BEP-00 target and assembled acceptance. BEP-01/02 and BEP-03 are integrated through the
actual entry points and three CPU method adapters; the [prepared-state owner](book-processing-efficiency-and-parallelism/prepared-state-and-cpu-kernels.md)
describes the delivered seams. This first-increment receipt covers CPU/regional07a only;
second-increment provider/database admission is recorded below. Final counts/devices and
enclosing qualification remain with07b/09.

| Command / selected obligation | Outcome2026-11-11 / managed receipt |
| --- | --- |
| `uv run ci test --json -- python/corpus-structure/tests/orchestrate/test_execution_preparation.py python/corpus-structure/tests/orchestrate/test_whole_document.py python/corpus-structure/tests/orchestrate/test_project_retained_source.py python/corpus-structure/tests/semantic/test_characterization.py` | passed65;15967b88310d499cb1b1d94aa172182b |
| `uv run ci test --json -- python/corpus-structure/tests/test_cli.py python/corpus-structure/tests/methods/test_m1_cli.py python/corpus-structure/tests/orchestrate/test_source_configurations.py python/corpus-structure/tests/orchestrate/test_slices.py python/corpus-structure/tests/orchestrate/test_characterization_demand.py python/corpus-structure/tests/orchestrate/test_source_reader.py` | passed46;f39fe2fd16ac409084b1bb9d621e2b20 |
| `uv run ci test --json -- python/corpus-structure/tests/semantic/test_cpu_execution.py python/corpus-structure/tests/methods/test_formal_evidence.py python/corpus-structure/tests/orchestrate/test_execution_preparation.py python/corpus-structure/tests/semantic/test_characterization.py` | passed61;c60b17ff58d54b1497b401712f62e6b5 |
| `uv run ci test --json -- python/corpus-structure/tests/semantic/test_cpu_execution.py::test_full_slot_blocks_method_source_hydration_before_input_factory` | passed1;6b25a68e206648bbb4de704bf3a1108e, after test-only typing cleanup |
| `uv run ci test coverage c60b17ff58d54b1497b401712f62e6b5 6b25a68e206648bbb4de704bf3a1108e --view unresolved --limit 10 --json` | covered61 required identities, zero unresolved/context unknowns/missing lanes; source difference is test-only monkeypatch typing cleanup |
| `uv run ci check --only types --view steps --json` | passed;e03e680a846f43f882b56f1daa61abe8 |
| `uv run ci check --only lint --view steps --json` | passed;8c8f040e75c64a9f8b814172f902e982 |
| `uv run ci doctor --json` | passed;11e1b132b2ec4bafa06decb891e19f22, following a transient pinned-wheel metadata timeout; no offline override/dependency change |

Selected controls establish real spawn/main-thread/warm placement, controlled two-worker completion
ordering, byte backpressure, admission before hydration, cancellation/start failure, malformed or
misrouted replies, mutation isolation, fresh authorization and exact transitive validation reuse.
The independent review's recorded source fingerprint predates only equivalent nested-with
combination and formatting; semantic behavior and ownership are unchanged. The61-control endpoint
covers those final production semantics. The earlier65/46 selections remain applicable to unchanged
adjacent behavior; final61 repeats affected preparation/characterization controls.

Preserve unsuccessful attempts: CPU serialization failure6ceecdbca870407e81e00fc5be4624f0;
initial native selection2e5564c6e7334635844c4908441e293e (one passed/two runtime-pin refusals while
source changed during execution); intermediate typing/lint failures07b122cfef2e46bda76c1719d661f3c3,
7acf1e5244a64b7d830b0b76823bf517,5a5135b153fa4c2cbf8c24f6cca99753,
0cf4ab73381d458c97c5367e9b6040d2,e182c34e15ff41839959c829e919bc61 and
e0ec23761cd44d3aab189adbb5eb843c. Later passes do not relabel them. No runtime guard was weakened.
Full BEP campaign, benefit measurement and book restart are not_run at this partial-series boundary.


### First-increment native acceptance and next work

**Tested2026-11-11.** With existing actual PM2 assets:

```sh
CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py -k 'test_empty_and_image_only_capture_enriches_without_language_provider_calls or test_unprojected_native_formula_publishes_and_replays_item_anchored_syntax or test_real_primary_demand_publishes_all_stages_and_reuses_exact_products'
```

**passed3/3**,fcad375338c54560955a717574e9532a. These exercise actual protected publication,
item-only formula correspondence/detached replay, complete real-provider primary demand and exact
reuse, two empty/image-only regions and final composition, and the real full-loader count of one
per invocation. No mock establishes provider passage. Native source remained frozen during the
successful run. The earlier2e5564c6e7334635844c4908441e293e runtime-pin refusals remain failed;
`uv run ci test coverage 2e5564c6e7334635844c4908441e293e fcad375338c54560955a717574e9532a --view unresolved --limit 10 --json`
reconciles the same required selection. The replacement covers final production source/context;
no failed result is relabelled. Required functional receipts are held while this plan consumes them.

The root judges BEP-00–03 and the CPU/regional07a prerequisite complete at this scoped boundary.
This includes integrated consumers, actual workers, targeted functional/native checks, types/lint,
documentation and independent assembled review. BEP-00 rationale/review is commitb85404293.
This first-increment receipt established worker capability, while ready regional coordination
and provider lanes/batches are covered by the second increment below. Capacity-one uses the
same spawned path. Final counts/devices and integrated full-book qualification remain07b/09.
BEP-E01 remains open and must be resolved before eventual full-book acceptance. TC plans are unchanged.
The second increment advances provider lanes and ready coordination from this foundation;
no full-book restart or final operating-policy selection was implied by first-increment closure.

Final first-increment source is commitbdb2bae11 (ADR-0083 target/reviewb85404293).
The native coverage report retains aggregate statusfailed because the original attempt failed;
its node coverage is covered3/3, zero unresolved/missing lanes/unknown contexts and no unsettled
attempts. The final-source replacement passed all3 and is the applicable native qualification.
`uv run ci docs check --json` passed,c7b25e6bbc9243d89eec5608677afdcf,882 canonical pages and
zero link errors. `just turn-end` passed with1126 Python files unchanged at final maintenance;
`git diff --check` passed. Later receipt-only prose changes preserve publication applicability.
Only main remains as a worktree; no push, default activation, selection or promotion occurred.


## Authorized second increment · 2026-11-11

**Implemented and scoped-qualified.** The operator approved BEP-04/05 and BEP-06 CPU delivery plus required07a
provider/database/thread controls. Subsequent operator steering adds CUDA-required D1/BF16 now;
other BEP-07b device/final-count work remains later. TC plans stay
unchanged and BEP-E01/full-book restart remain outside this increment. Baseline380fecc74.
ADR-0084 and the ready-coordination target review own the published target. Initial policy admits
two regions, two CPU workers/submissions, two active stage runs and four logical claims; one
resident/exchange per provider and one pending native batch, foreground DB work serialized to
preserve renewal progress. These are bounded integration defaults, not final optimal counts.
PreparedWork/ReadyGroup plans keep all registration, reader and builder work in the parent;
private WorkHandles own computation/cancellation and charged reply lifetimes. Physical slots
leave after drained collection, reply bytes after reduction, and resulting draft credits at durable
settlement. No generic cross-run DAG or parallel whole-demand wrapping is selected.

Selected06-I1 disposition: HanLP2.1.7 has no supported prepared-sample input to native multitask
prediction. Bulk admission obtains actual native subword lengths with per-member limitations;
inference retains native preparation.06-I2 uses versioned compact batch headers, ordered exact
member commitments and ordinal-bound observations; whole-population checks occur at admission,
member/replay checks against original context/policy. Historical v1 receipts retain original
read-only semantics, while the current producer emits v2.06-I3 selected CPU regrouping and corrected production nested-cue/flat-function projection are
qualified by retained evidence.06-I4 actual lane lifecycle controls passed at their bounded scope;
final integrated scheduler/native DB receipts remain required below.

Implementation, affected consumer migration and final scoped qualification are complete below.
No whole-book completion or measured improvement is claimed.

### Second-increment implementation and verification

ADR-0084 and ADR-0085, the updated D3/D4/D6/D8 owners and the
[assembled review](../design_review/reviews/design_review_book-ready-coordination_2026-11-11.md)
record the accepted realization. The review accepts the assembled source at Interface-checked
strength, initial fingerprint431330e26482645bf4f79344e2815b508fb360db02e01f0c442eee4c1b07cd93
for its33 product files. BEP-E02 subsequently adds the operator-required CUDA selection and
order-preserving transport/receipt correction, with focused review and new actual qualification. Capacity-one and parallel
execution share one authoritative driver; obsolete primary serial/ambient borrower routes are
removed. Required07a is implemented at finite integration defaults; final counts/CUDA stay07b.

BEP-06-I1 closes unsupported prepared-sample reuse with native inference preparation preserved;
I2 delivers shared current/historical authentication and consumer migration. I3 selects ADR-0085's
released CPU numerical semantics. I4's8 real HanLP/GLiNER lane scenarios preserve useful members,
actual ordinal/cohort provenance, joined native children and zero retired-owner budget. The
[evidence owner](../design_review/evidence/2026-11-11_book-provider-batches/README.md) retains all
five records and raw failed/superseded attempts; only the nested production projection record
qualifies current cue overlap policy. Probe execution predates the lazy-admission repair;
unchanged native worker/coalescer semantics apply, while final tests qualify that repair.

Final scoped commands and native integration outcomes are being reconciled here. Full BEP09
campaign, final operating policy, CUDA and full-book restart remain not_run at this increment.
BEP-E01 is still open, required before full-book qualification. No TC plan change is included.

#### Final functional/check selections · 2026-11-11

The required scoped union comprises the following selections, the actual-provider integration
selection below and I1–I4's retained native records. These are second-increment obligations,
not the BEP-09 campaign. The main226-node selection's original failure remains failed; coverage
reports every required identity covered by the final replacement, zero unresolved nodes,
missing lanes, execution-context differences or context unknowns. Source differences are the
admission control's migration from unsupported external whole-method thread wrapping to two
plans in the same driver, plus independent historical receipt/new native tests and documentation.
These earlier controls precede BEP-E02; its affected final replacements and source applicability
are recorded with the CUDA correction below.

```sh
CORPUS_GLINER_DIAGNOSTIC=1 uv run ci test --json -- python/corpus-structure/tests/methods/test_gliner.py python/corpus-structure/tests/methods/test_pm2_worker.py python/corpus-structure/tests/methods/test_characterization_resources.py python/corpus-structure/tests/methods/test_native_evidence.py python/corpus-structure/tests/methods/test_contextual_characterization.py python/corpus-structure/tests/methods/test_model_characterization.py python/corpus-structure/tests/methods/test_pm2_gliner_classification.py python/corpus-structure/tests/methods/test_definition_applicability.py python/corpus-structure/tests/semantic/test_model_characterization.py python/corpus-structure/tests/semantic/test_cpu_execution.py python/corpus-structure/tests/semantic/test_cpu_annotations.py python/corpus-structure/tests/orchestrate/test_ready_coordination.py python/corpus-structure/tests/orchestrate/test_execution_preparation.py python/corpus-structure/tests/orchestrate/test_characterization_demand.py python/corpus-structure/tests/orchestrate/test_source_reader.py python/corpus-structure/tests/semantic/test_characterization.py python/corpus-structure/tests/semantic/test_claim_owner_native.py
uv run ci test retry f55bb9ed44de448387414054798fb4b1 --lane ordinary --json
uv run ci test --json -- python/corpus-structure/tests/methods/test_pm2_gliner_classification.py
uv run ci test --json -- python/corpus-structure/tests/methods/test_formal_evidence.py python/corpus-structure/tests/semantic/test_formal_evidence.py python/corpus-structure/tests/semantic/test_constructions.py python/corpus-structure/tests/semantic/test_contextual_characterization.py python/corpus-structure/tests/semantic/test_characterization_evidence.py python/corpus-structure/tests/semantic/test_characterization_replay.py python/corpus-structure/tests/semantic/test_primary_analytical_replay.py python/corpus-structure/tests/semantic/test_characterization_completion.py python/corpus-structure/tests/semantic/test_characterization_manifests.py python/corpus-structure/tests/methods/test_characterization_composition.py python/corpus-structure/tests/orchestrate/test_whole_document.py
uv run ci test coverage f55bb9ed44de448387414054798fb4b1 279f437102464477a9d2bf9f6d56f20f f5ed638863254844b72f743769b0eb76 --view unresolved --limit 10 --json
```

| Selection / command | Actual outcome / managed receipt |
| --- | --- |
| Main provider/CPU/coordinator/native-claim226 controls; opt-in GLiNER diagnostic uses actual pinned checkpoint | Original failed1/passed225,f55bb9ed44de448387414054798fb4b1; final exact retry passed1,279f437102464477a9d2bf9f6d56f20f. Coverage covered226/226 with original failure preserved. |
| Current/historical classification authentication and detached replay | passed11,f5ed638863254844b72f743769b0eb76 |
| Formal/construction/contextual, validators, replay, completion, composition and captured-document adjacent selection | passed186,0887932d63d8471686995f8e9d888d06 |
| `uv run ci check --only types --view steps --json` | passed,4c69e3c0095d495c8f4091a29b1c0608 |
| `uv run ci check --only lint --view steps --json` | passed,dc7f9a813f45462498e642dda70903fe |
| `uv run ci docs check --json` | passed,da15d3c7d33b4fad82e896177237388f;886 canonical pages/zero link errors, before final receipt-only checkpoint edits |

Selected controls cover independent ready completion, stable reduction, generation-safe CPU
cancellation, real spaCy worker execution, admission-before-hydration/serialization, transient
byte saturation, actual provider framing/refusal, strict batch/cohort/member authentication,
unchanged threshold/raw-score semantics, historical-v1/current-v2 refusal boundaries and native
renewal/late-publication/uncertain-completion fences. Mocked controls do not establish native
provider passage; actual providers have their explicit native rows and evidence records.

Earlier integration failures remain retained:5818a85847f848149dc384e985561c8d (ClaimedTask logging
used mapping access; corrected to typed fields),148af1ea184647cd98a1d63b18a6a798 (one passed,
one runtime-pin refusal while product source changed),8d945d79be634d9584a8e656ad5d67a0 (lint),
357a4c26bc6f423dabc3076fad3214e1 (test-only ParserProduct accessor), and195baaba3f2448e5869e2f8a2d93f41c/
97e7ca13c5a54d76a1861e0dd7530c30 (the same new historical test's accessor). Final11-control pass
covers the corrected historical expectation. Earlier target/type/test attempts retain original
managed records; their failure is not relabelled as qualification.

#### Actual native publication and captured-document integration

Product source was frozen during these selections. BEP-E02 later changes CUDA selection and
native serialization, so final current-source qualification requires its fresh replacements.
The asset prefix selects the installed locked native services; no provider is mocked.

```sh
CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py -k 'test_empty_and_image_only_capture_enriches_without_language_provider_calls or test_unprojected_native_formula_publishes_and_replays_item_anchored_syntax or test_real_primary_demand_publishes_all_stages_and_reuses_exact_products'
CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py::test_two_language_regions_complete_captured_characterization_with_actual_providers
```

The first selection **passed3/3**,1f4b3016b40a4190a49a5f8d9efa24a6. It exercises actual selected
providers through all six primary stages with exact settled-product reuse, two-region empty/image
capture with zero language-provider demand and one full release verification per invocation, and
unprojected native formula publication/replay under the actual PostgreSQL/source fences.
The two-language-region selection failed91203c735f4b4b1e87dddfa0f6dd89a2 and diagnostic
retryf0766f5fa43141029e614de30b99e2e0: D1 native inference timed out at120s. Assertions were
not weakened; dependency-unresolved available/partial coverage already passes. BEP-E02 owns the
CUDA-required repair and actual prose qualification.

Native coverage reconciliation of the earlier failed2-test attempt reports both required
identities covered by the final3-test pass. Its aggregate remains failed and reports native-binding
unknown for the original pre-claim failure; the final applicable attempt has complete native
observations against frozen source. This unknown is retained, not silently cleared or used as
positive evidence. Exact final native passage supplies the replaced obligations.

Architecture/evidence commit:0ce41be43. Product/affected tests commit:adf024fd7. Later changes are
plan/checkpoint receipts only, with final publication/maintenance recorded at handoff.


BEP-E02 follows the operator's explicit CUDA-required correction. D1 is not an optional CPU
fallback: current primary and managed D1 authoring/launch must select CUDA and BF16, refusing an
unsupported device rather than silently moving to CPU. The existing120s inference and300s startup
bounds remain. Installed runtime inspection found torch2.15.0+cu132, CUDA13.2, sm120/RTX5090 and
BF16 support. This capability check is not native model qualification. Scoped D1 CUDA question/
batch/source/custody evidence and fresh native publication remain required; other07b providers,
replicas and final counts are still later. Native/functional attempts5f36b1dc2a7a4da89ffb8cf81f71d10e
and527f0926179e4508903aa40cdcb99395 were intentionally interrupted and drained when this steering
arrived; no CPU600s qualification is claimed.


Actual D1 CUDA execution also exposed a native transport regression before final cutover:
canonical JSON encoding sorted meaningful question/option keys at the lane seam. The declared
question factory's order remains authoritative. Restore ordered native request/reply transport
and PM2receiptv2 exact ordered-member commitments, retaining originalv1 read semantics. Shared
validation remains authoritative; current D1 authoring requires v2 plus actual CUDA/BF16. The
provider-scoped released model policyv3 binds this selected numerical profile. No native
question/batch/source population or threshold is silently changed to pass qualification.


### Current-source CUDA/order qualification

The final current-source selection repeats the main functional controls after CUDA-only guards,
released policyv3 and ordered PM2receiptv2 integration, and adds managed interpretation admission.
The adjacent186-control selection was rerun unchanged after those shared changes and **passed**,
b81ae84d529c4744bd1c915eeb363b9e. Focused58 order/receipt/current-profile controls **passed**,
1918758d82714f83af87baad129fb849. Managed real-native source refusal **passed**,
f605d6cea728493a8fb6662740538788. Earlier scoped passes remain at their original source boundary.

Final `uv run ci check --only types --view steps --json` **passed**,
8a93c21b4922479eadc93181332dbd25; `--only lint` **passed**,
cb421cc1e22c4e1ebf39d3959ae7fcc5. Environment-shaped investigation used
`uv run ci doctor --json`, **passed**822a98a09978489f89dac91869287d11; no dependency changes.
`uv run ci docs check --json` **passed**514168de09024f95bb1089d17b9050fc,887 canonical pages,
zero link errors before final evidence/receipt/checkpoint publication.

The new [D1 CUDA evidence](../design_review/evidence/2026-11-11_book-d1-cuda/README.md) owns actual
CUDA/BF16 source/question/member and custody checks. Seven function cohorts include13 members,
with distinct equal-text source contexts; two genuinely pending logical jobs coalesce in one
physical CUDA lane. Ordered literal/source-field requests and actual stage1 frozen prior answers
are checked independently. Active cancellation stops the owned child, releases byte credit and
permits GPU custody reacquisition. Native BF16 confidence varied up to0.01866078038429342 in this
bounded panel while discrete outputs agreed there. This is not negligible-by-definition, a global
error bound, CPU equivalence or threshold/label stability guarantee. Actual unrounded native
probabilities and exact cohort/source provenance remain authoritative under policyv3/ADR-0086.
The initial CUDA attempt retains its literal-order failure as partial evidence; only the corrected
ordered-receipt attempt qualifies the current route.


The final expanded237-control selection03786217ec8043279fcf695c5f815084 remains **blocked**:
236 passed; one opt-in `test_alternate_domain_parser_run_retains_siblings_after_profile_refusal`
requires assets to qualify CUDA HanLP/Maverick/DiPO. That test exercises unchanged, other-provider
GPU profiles outside this D1-only CUDA increment and remains with07b, not silently counted passed.
The current required selection excludes that named unrelated CUDA scenario and retains all D1
managed admission/closure controls. Its fresh explicit command is the main functional selection
above plus python/corpus-structure/tests/semantic/test_pm2_parser_stage_native.py and
`-k 'not test_alternate_domain_parser_run_retains_siblings_after_profile_refusal'`, with
CORPUS_GLINER_DIAGNOSTIC=1. Original237-node report and its one unresolved identity are preserved;
this increment claims only its explicitly selected applicable union.


### Second-increment closure · 2026-11-11

**Implemented and scoped-qualified:** BEP-04/05, selected BEP-06 CPU HanLP/GLiNER plus required
CUDA/BF16 D1, and required07a admission/thread/custody integration. D1 CUDA was explicitly selected
by the operator during execution; all current D1 defaults/launches require CUDA/BF16 and refuse
CPU fallback. No600s CPU override remains. ADR-0086 and commitbd53c0fa1 record that selection and
ordered-native transport/receipt correction, following foundation commits0ce41be43/adf024fd7.

| Final obligation | Outcome / current managed receipt |
| --- | --- |
| Main functional/provider/CPU/coordinator/native-claim/managed-D1 controls, scoped command above | passed236/236,12916646acbc4072ac90cad2dfd458af |
| Adjacent formal/construction/contextual/validation/replay/completion/composition selection | passed186/186,b81ae84d529c4744bd1c915eeb363b9e |
| Current-source actual native publication/reuse, empty/image capture, formula replay and two-language-region captured-document path | passed4/4,6dfe911f0ea14484a2bcd95d8bda8635 |
| CUDA selected native D1 batching/question/source/receipt/cancellation/custody panel | passed,bep.d1-cuda-ordered-native; finalizer7b64b32583794b46a65ed07159190842 |
| Initial CUDA order-regression partial result, preserved/superseded | partial,bep.d1-cuda-initial-order-regression; finalizer74c33346ddda47ea90d88553a4b5223b |

Final native command:

```sh
CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py -k 'test_empty_and_image_only_capture_enriches_without_language_provider_calls or test_unprojected_native_formula_publishes_and_replays_item_anchored_syntax or test_real_primary_demand_publishes_all_stages_and_reuses_exact_products or test_two_language_regions_complete_captured_characterization_with_actual_providers'
```

`uv run ci test coverage 12916646acbc4072ac90cad2dfd458af --view unresolved --limit 10 --json`
and the same command for6dfe911f0ea14484a2bcd95d8bda8635 report each required selection fully
covered, with zero unresolved nodes, source/context differences, unknown contexts, missing lanes
or unsettled attempts; native observations are complete. The186-node pass is the final-source
replacement for its earlier receipt. Original failures, blocked237-node broader selection and
operator-interrupted attempts retain their actual outcomes and managed holds.

Final reviewed product footprint matches33 source files at
9d2b51c7ae7958e2bd438b416baa2195930ba96ac91ddbc12c640677cb3e714b. Final source is
bd53c0fa1; subsequent edits only update plan/checkpoint receipts. The required scoped union now
covers physical concurrency/admission, current/historical receipt/source fidelity, actual provider
execution, cancellation/claim/renewal/publication fences and actual combined two-language-region
capture. Two actual text regions each retain all six stages, exact source-view/pointer/half-open
coordinates and one full composed view in original source order. No mock establishes provider
passage, prediction accuracy, arbitrary threshold invariance or a measured speedup.

BEP-06-I1/I2/I3/I4 close at this selected profile scope: supported HanLP bulk admission with native
inference preparation retained, shared exact receipt migration, qualified provider-scoped native
numerical semantics, and bounded real lifecycle plus native DB publication. Earlier CPU D1 native
evidence remains historical and does not qualify CUDA. HanLP/GLiNER CPU lifecycle controls retain
applicability to unchanged worker cancellation/retirement and source scatter; final v2 controlled
receipt tests and current native publication cover the changed ordered codec. Other-provider CUDA,
final counts/replicas, BEP-08 operating surfaces and BEP-09 whole-book/consumer qualification remain
later. BEP-E01 stays open and must be resolved before full-book acceptance. TC plans are unchanged.


Final publication `uv run ci docs check --json` **passed**715c428a493149a79830d99413face0e,
888 canonical pages and zero link errors; ADR index/lint and agent lint passed in that route.
Final root `just turn-end` **passed**,1131 Python files unchanged. `git diff --check` passed;
TC coordinator/companions are unchanged against380fecc74. Only main exists as a worktree.
Later receipt-only prose preserves source and publication applicability. No push, project/default
activation, selection, promotion, recognition restart or book rerun occurred.
