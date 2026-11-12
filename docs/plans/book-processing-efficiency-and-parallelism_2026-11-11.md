# Book-processing efficiency and parallelism

**Status: BEP-00–03 implemented and scoped-qualified; later packages planned · Authored2026-11-11.** Owns BEP-00–BEP-09 and the scheduled disposition of the [source review](../functional_reviews/book-processing-efficiency-and-parallelism_2026-11-11.md)'s O01–O08 and RC01–RC04. This coordinator owns combined acceptance and investigation decisions; companions own the detailed contracts identified below.

## Authority, scope and baseline

Planning input is the review at commit f81a380cd, inspected product source4d0ca7eb7. Creating this series implements no production change. RC01–RC04 were explicitly accepted by the operator on2026-11-11 for this target; implementation, architectural recording and qualification remain planned.

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

BEP-00–03 are **implemented and scoped-qualified** by the first-increment receipts below. The CPU/regional prerequisite of07a is delivered; its provider/database obligations and07b remain open. BEP-04–09 remain **planned**. An agreed interface permits design work; working integration requires delivered prerequisites.

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
| O03 | Planned BEP-05 | Independent regions progress without unrelated ordering barriers. |
| O04 | Planned BEP-03/04/05 | Main-thread CPU execution, resident lanes and deterministic private-result reduction work together. |
| O05 | Planned BEP-06 | Existing batching preserved; selected native admission/batch contracts migrated and qualified. |
| O06 | Planned BEP-07 | Coordinated policy delivered; mandatory CUDA investigation and selected profiles explicitly disposed. |
| O07 | Planned BEP-05/07/09 | Fences, renewal, DB progress, proportional recovery and exact composition remain effective. |
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

Qualification for this increment is targeted preparation/trust/native-publication and actual-spawn
behavior. It does not establish final policy, provider parallelism or whole-book qualification.
Implementation and check receipts will be recorded here against the integrated source.

### First-increment implementation and scoped verification

**Implemented; scoped checks2026-11-11.** ADR-0083 and the
[foundation review](../design_review/reviews/design_review_book-execution-foundations_2026-11-11.md)
record BEP-00 target and assembled acceptance. BEP-01/02 and BEP-03 are integrated through the
actual entry points and three CPU method adapters; the [prepared-state owner](book-processing-efficiency-and-parallelism/prepared-state-and-cpu-kernels.md)
describes the delivered seams. CPU/regional07a is delivered; provider/database admission and
final counts/devices remain open with07a/07b. O04/O06 and enclosing qualification remain open.

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
Full hybrid admission, ready scheduling, provider lanes/batches, final counts/devices and integrated
BEP qualification remain with04–09. Capacity-one current production uses the same spawned path;
controlled two-worker tests establish worker capability without claiming book-region parallelism.
BEP-E01 remains open and must be resolved before eventual full-book acceptance. TC plans are unchanged.
Next ready work is BEP-04 provider lanes and BEP-05 coordination once their actual prerequisites
are delivered; no full-book restart or final operating-policy selection is implied by this closure.

Final first-increment source is commitbdb2bae11 (ADR-0083 target/reviewb85404293).
The native coverage report retains aggregate statusfailed because the original attempt failed;
its node coverage is covered3/3, zero unresolved/missing lanes/unknown contexts and no unsettled
attempts. The final-source replacement passed all3 and is the applicable native qualification.
`uv run ci docs check --json` passed,c7b25e6bbc9243d89eec5608677afdcf,882 canonical pages and
zero link errors. `just turn-end` passed with1126 Python files unchanged at final maintenance;
`git diff --check` passed. Later receipt-only prose changes preserve publication applicability.
Only main remains as a worktree; no push, default activation, selection or promotion occurred.
