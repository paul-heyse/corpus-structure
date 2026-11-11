# Enriched-document text characterization implementation series

**Status: TC-00–09 functionally qualified; TC-10/11 execution in progress · 2026-11-11.**
This coordinator owns TC-00–TC-11, TC-I01–09, O01–O07 disposition and combined completion.
Supporting plans own package design; this page owns current package state. The required functional/provider union for TC-03–09 and its TC-01/02 prerequisites is covered. TC-10/11 independent semantic assessment and full-book qualification are now authorized and in progress. Activation/selection retains its explicit final effect authority; conditional branches remain trigger-driven.

## Target and basis

Produce a combined **enriched document**, preserving the source's sections, reading order, pages,
native items, tables, figures, formulas and exact locations while adding identified linguistic,
construction, semantic and contextual layers. Analytics and conceptual enrichment consume that
representation and can add further identified layers. Document containment, annotation membership,
semantic relationships and analytical alternatives remain distinct.

The operator approved this authoring scope on2026-11-10, including the enriched-document framing,
and chose baseline delivery plus triggered conditional branches. The source is the
[functional review](../functional_reviews/text-characterization_2026-11-10.md) at `59eee893c`, O01–O07
and its full feature crosswalk, supported by the
[library collection](../library_leverage/libraries/text-characterization/briefing.md). This plan
refines the review's semantic product into document-owned layers; it does not replace the source
document with a detached text graph. [Coverage](text-characterization/coverage.md) routes every
feature row, including Supporting, Conditional and Rejected entries.

Source baseline: `59eee893c7ed7839a1aaed8a11aa12faf03a232e`, main,2026-11-10. Concurrent CLI/admission
reporting docs and evidence repairs are excluded and preserved. Existing native receipts keep their
original scope; no product/provider test, model fitting, runtime probe or benchmark was run during
plan authoring. Pinned spaCy3.8.18/en_core_web_sm3.8.0, Lark1.3.1 and SymPy1.14.0 remain the starting
selection. Provider artifact/runtime profiles are discovered from current executable declarations and source.

Use [standard.toml](../design_review/design_principles/standard.toml): core3.3, efficient-architecture
heuristics, code-intelligence1.4 and binding. Source fidelity and unknown states constrain the
semantic model; native composition and shared preparation constrain its physical realization.
The proving corpus is all 518 Grinstead–Snell physical pages under
[ADR-0070](../adr/0070-full-book-method-development.md), plus the existing second-vocabulary fixture.

## Foundation assessment and shared decisions

At the 2026-11-10 authoring baseline, annotation products retained exact token layout, morphology, dependencies, sentences and
availability; native views reconstruct them without model inference. HanLP/Maverick/Dipo and
GLiNER/d1 have existing provider operation owners. `SourceObservationBatch` and
`SourceContributionOperation` in the released observation model already retain identity, question,
outcome, coverage and zero-output operations. Reuse these owners rather than create another store
or workflow runtime. [Model/retention](text-characterization/model-and-retention.md) develops the
delivered extensions beyond that baseline frame/cue vocabulary.

At that baseline, native SQL reconstructed candidate roles and reading layout as well as authenticating
source support. The implemented replacement moves language-producing policy to
primary characterization; native custody, endpoint, coordinate and declared-invariant checks
remain independently enforced. Producer agreement alone is not an independent semantic oracle.
[Migration](text-characterization/consumer-migration-and-integration.md) owns the cutover.

The full profile attempts every selected characterization family over eligible natural sections.
It preserves native scheme disagreements, partial products, supported readings and unknowns.
Completeness describes operation/profile/scope coverage, never every conceivable English meaning.
The baseline includes new modal, scope, attribution and function tasks; current finite statistics
prompts do not already supply them. Failed required tasks remain failed/partial rather than being
silently replaced by an unselected model. Cheaper boundary-only profiles remain explicitly weaker.

A document view binds an immutable base pin and exact layer revisions. Identified cross-boundary
annotations have separately anchored members, not copied tree parents. One group over pages3–4
has one group ID and two distinct membership/source occurrences. Index membership by qualified
annotation ID; matching IDs retrieves recorded association, while the producing operation establishes
its meaning. A later topic grouping uses the same view mechanism with different semantic authority.

No new default model, graph service, generic constraint solver or task per annotation is selected.
Native Docs/trees/forests are operation-shaped working forms. Persist the useful semantics and
positions under generated released contracts, with native evidence/report bytes retained as needed.

## Reading route and execution dependencies

| Supporting plan | Responsibility |
| --- | --- |
| [Model and retention](text-characterization/model-and-retention.md) | TC-01/02: shared model, identity, release, storage, document/layer reads |
| [Native evidence](text-characterization/native-evidence.md) | TC-03/04: positioned linguistic and formal inputs |
| [Constructions and interpretation](text-characterization/constructions-and-interpretation.md) | TC-05/06: reusable constructions, forests, symbolic and contextual semantics |
| [Contextual characterization](text-characterization/contextual-characterization.md) | TC-07/08: reference/discourse and baseline model tasks |
| [Consumer migration and integration](text-characterization/consumer-migration-and-integration.md) | TC-09: consumers, native admission, ingest scheduling and retirement |
| [Assessment and investigations](text-characterization/assessment-and-investigations.md) | TC-10 and TC-I01–09: independent expectations, native/corpus assessment and conditional decisions |

```mermaid
flowchart TD
  A[TC-00 authority] --> B[TC-01 model]
  B --> C[TC-02 retention and readers]
  C --> D[TC-03 linguistic evidence]
  C --> E[TC-04 early positioned input]
  D --> F[TC-05 constructions]
  E --> F
  F --> G[TC-06 phase one symbolic terms]
  D --> H[TC-07 context evidence and hypotheses]
  G --> I[TC-08 model characterization]
  H --> I
  C --> J[TC-09 integration and migration]
  G --> M[TC-06 phase two contextual evaluation]
  H --> M
  I --> M
  M --> J
  I --> J
  B --> K[TC-10 assessment]
  J --> L[TC-11 qualification and adoption]
  K --> L
```

TC-04's early positioned atom/constituent readers unblock TC-05; ambiguous-formal packing closes
after the TC-06 symbolic slice. TC-07 produces context evidence and hypotheses; TC-06 alone owns
semantic-node/environment evaluation. TC-08 candidate questions use frozen symbols and hypotheses,
not TC-06's final contextual answers. Source-first TC-08 work can run independently from candidate
production. Final TC-06 evaluation consumes these explicit revisions once; unresolved results remain
unknown rather than trigger an automatic fixed-point loop.

This graph describes working integration prerequisites. Independent expectation authoring starts
with settled semantics, and provider preparation can begin from an agreed input contract. TC-09's
consumer changes participate in earlier packages when needed; its completion reconciles the whole
inventory. Documents and graph nodes are not mandatory synchronization or process boundaries.

## Execution queue and current state

The authorized TC-03–09 implementation and TC-01/02 integration prerequisites are delivered on
shared `main`, 2026-11-11. Native integration is deployed through
`semantic_tc03_09_literals`, release
`release:81dd8c0986138654fe434c1742072585ed968d70a4973961b6e89aa6e2713371`.
The default remains `/10`; the project remains unselected. No activation or promotion occurred.
The [integration evidence](../design_review/evidence/2026-11-11_text-characterization-integration/README.md)
retains deployments, original failures and the final test-identity union. **Tested:** the functional
claim covers the selected contracts, real-provider/native integration, reuse, migration and fault
behavior. It makes no claim of exhaustive linguistic meaning, measured benefit or full-book quality.

| Package | Required capability | Delivered behavior and closure |
| --- | --- | --- |
| <a id="TC-00"></a>TC-00 · Target authority | Approved implementation scope; relevant current owners | **Complete:** [ADR-0081](../adr/0081-enriched-document-analysis-layers.md), D1/D2/D3/D4/D6/D8 authority and [entry review](../design_review/reviews/design_review_text-characterization-entry_2026-11-10.md) Accept scoped. No source/admission rule reversal. |
| [TC-01](text-characterization/model-and-retention.md#TC-01) | TC-00 decision | **Complete, Tested:** released contracts, exact source/analysis identity, private-product classification, DAG/choice/coverage validation, original-release closure and independent examples |
| [TC-02](text-characterization/model-and-retention.md#TC-02) | TC-01 | **Complete, Tested:** protected native products/projections/completion, indexed reads, CLI/MCP, composition and detached closure. All native foundation cases and the final required functional union are covered below. |
| [TC-03](text-characterization/native-evidence.md#TC-03) | Working TC-02 input/layer contract | **Complete, Tested:** all 13 native families, exact native columns/schemes, runtime/artifact custody and explicit weaker profiles; actual-provider and native admission controls covered in the final union |
| [TC-04](text-characterization/native-evidence.md#TC-04) | Working TC-02 | **Complete, Tested:** direct shared SPPF syntax, normalized/literal/recognized correspondence, separately reported symbol outcomes and source-first inline nominations; scientific assessment separate |
| [TC-05](text-characterization/constructions-and-interpretation.md#TC-05) | TC-03 plus early TC-04 positioned-input slice | **Complete, Tested:** spaCy named/source constructions, Lark direct packed reduction and primary navigation/naming/math-scope facts; downstream recognizers retired |
| [TC-06](text-characterization/constructions-and-interpretation.md#TC-06) | TC-05 for symbolic slice; TC-07/08 evidence for contextual closure | **Complete, Tested:** explicit choice sites, shared terms and environment evaluation; transitive external selection and witness conservation implemented, native controls covered in the final union |
| [TC-07](text-characterization/contextual-characterization.md#TC-07) | TC-03 and context/source maps, relevant constructions | **Complete, Tested:** raw Maverick/Dipo populations, linear cluster membership, private hypotheses, exact context/gaps and retained-native mode; actual-provider admission covered in the final union |
| [TC-08](text-characterization/contextual-characterization.md#TC-08) | TC-06 symbolic slice/TC-07 hypotheses for candidates; source-only route independently | **Complete, Tested:** eight released question families, source-first and frozen-candidate stages, declaration/request identity and explicit missing/none/insufficient outcomes; actual-provider checks covered in the final union |
| [TC-09](text-characterization/consumer-migration-and-integration.md#TC-09) | Required primary layers available | **Complete, Tested:** primary-only consumers, current native guards, demand/ingest and view bindings, detached analytical closure, current-only retirement, explicit zero-input coverage and bounded provider residency |
| [TC-10](text-characterization/assessment-and-investigations.md#TC-10) | TC-01 semantics; delivered producers for execution | Independent source/output assessment and faithful native/retained controls |
| <a id="TC-11"></a>TC-11 · Assembled qualification | TC-01–10 and selected conditional outcomes | Working native full-profile pipeline, full-book coverage account, named semantic assessments, current-only cutover and complete required check union |

## Authorized TC-03–09 continuation

**2026-11-10.** Execute complete selected baseline scope in coherent batches: native evidence and
early positioned formal inputs; constructions with direct packed symbolic reduction; contextual
evidence and all eight model question families; packed formal completion; one contextual evaluator;
complete consumer/native/ingest/read migration. TC-09 consumer slices accompany producers.
TC-10 assessment infrastructure and TC-11 complete-book qualification/adoption remain separate.

Foundation command `uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py python/corpus-structure/tests/semantic/test_characterization.py python/corpus-structure/tests/methods/test_characterization_composition.py python/corpus-structure/tests/semantic/test_characterization_replay.py python/corpus-structure/tests/semantic/test_characterization_completion.py`
**passed**,78 selected cases, `710bab42df304f469ecf4c628401a5a4`,2026-11-10. This verifies the strict
receipt, joint completion and cross-release corrections; it does not establish full qualification.
Full `uv run ci test --json` receipt `47a15226cae2486f8b81e8ec5b0b7de8` was interrupted and
settled at exit130. It selected 6119 ordinary identities: 4263 passed, 943 failed, 2 blocked,
16 incomplete and 895 not_run; fault/Rust not_run. The early stale operation-report schema defect
was diagnosed independently; later failures were contaminated by edits made while that campaign
ran. Preserve this failed/interrupted evidence; it is not final-source qualification. The owning
operation-report and call generators have since run successfully, with their generated outputs
covered by the final functional union and repository checks.

The [producer target review](../design_review/reviews/design_review_text-characterization-producers_2026-11-10.md)
accepts the revised target only, with these implementation obligations:

| Finding | Responsible package / component | Current disposition and closure evidence |
| --- | --- | --- |
| Producer review F01 | TC-03/04, released characterization model | Closed, Tested in the final required union: typed tokens/native run columns and formal inputs/nodes/correspondence, kind-specific requirements and independent retention/refusal controls |
| Producer review F02 | TC-06, native validation and live/detached readers | Closed, Tested in the final required union: typed qualified upstream choices, transitive joint selection and original released-contract validation through live/detached paths |
| Producer review F03 | TC-06, packed algebra/codec/reading | Closed, Tested in the final required union: explicit child choice sites, single-valued root selection, unresolved partial sites and site/root cycle edges; packed diamond/native cycle controls |
| Producer review F04 | TC-05/09, construction declarations/native guards | Closed, Tested in the final required union: released mechanical witness constraints and wrong-host/source/choice refusals; current primary-only consumers and retirement of duplicate SQL language production |

Native producers obtain per-unit determinants from the execution-owned port and retain exact provider
costs at protected completion. Native controls exercise changed-cost replay refusal. Model/runtime
preparation and inference remain outside publication transactions. These prerequisites and their native refusal controls are covered by the final required functional union.

<a id="stopped-checkpoint-and-bulk-continuation"></a>

## Functional qualification · 2026-11-11

The stopped 2026-11-10 foundation checkpoint is resolved. Its original failed native receipt
`3f98a01daa9b4059ad066da42ca6c2f7` and interrupted retry
`0a008697b02d4616b51f71a57133536f` remain evidence of that checkpoint, alongside the
[native foundation record](../design_review/evidence/2026-11-10_text-characterization-native/README.md).
The strict receipt conversion, producing-layer preload and distinct cross-release realization
corrections passed the 78-case foundation selection and the subsequent integrated selection.
The five frozen foundation migrations and all forward producer migrations remain immutable.

| Command / managed result | Outcome and acceptance scope |
| --- | --- |
| `CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json` · `71e97b485e59479b80b9d5e086f48570` | **failed**, ordinary: 6,399 selected:6,394 passed, four failed, one blocked; fault: 8/8 **passed**. Production source was frozen. Rust selected zero, **not_run**. |
| `CORPUS_GLINER_DIAGNOSTIC=1 uv run ci test --json -- python/corpus-structure/tests/methods/test_contextual_characterization.py python/corpus-structure/tests/methods/test_m1_review_repairs.py python/corpus-structure/tests/semantic/test_analysis_resources.py python/corpus-structure/tests/methods/test_gliner.py` · `2e2d74eb026b42b78068d523ce6ca5da` | **passed**,82/82. Whole affected modules plus the actual opt-in GLiNER Base2.5 diagnostic; this replaces all four failures and the blocked diagnostic. |
| `uv run ci test coverage 71e97b485e59479b80b9d5e086f48570 2e2d74eb026b42b78068d523ce6ca5da --view unresolved --limit 20 --json` | **covered**, required: 6,407, covered: 6,407, unresolved: 0; no missing lanes, unknown contexts or unsettled attempts. Original failed attempt remains **failed**. |

**Final-source/context applicability judgment:** the only source changes after the full campaign
were three module-local test doubles: explicit source-view lookup, the capture/characterize/consume
preflight fixture, and finalization's retained run-options lookup. No production, SQL, dependency,
shared fixture or harness bytes changed. Each complete affected module passed in the 82-case rerun;
all other ordinary and fault results remain applicable. The reported native-binding difference
comes from the scoped selection's isolated native fixtures; both applicable native observations are
complete. The diagnostic was explicitly enabled and executed, rather than treated as a mock pass.
The earlier full selection exercised installed PM2 assets, all primary family providers and exact
repeated-demand reuse. Thus the required functional/provider union for the authorized implementation
is satisfied. This is a composite qualification, not a claim that the original full receipt passed.
Rust context: `rustc 1.101.0-nightly (2d20b42b8 2026-11-04)`; no Rust tests are in this selection.

`uv run ci check --view steps --json` **passed**, `16c68b4634774b619f59110c779a85a2`;
empty rule lanes are **not_run**. `uv run ci docs check --json` **passed**,
`45a282ed4379434d84d4a2dbda836824`,872 canonical pages, zero link errors.
The integration evidence preserves the earlier failed publication check and anchor correction.
Implementation is committed as `e9025e949`, with the independent SQL inspection repair in `088cf9fdd`.
Independent semantic assessment and all 518 physical-page qualification remain TC-10/11 work.

## Review disposition

| Review item | Component and intended correction | Disposition/dependency | Closure evidence |
| --- | --- | --- | --- |
| [O01](../functional_reviews/text-characterization_2026-11-10.md#O01) | Source/document and native-evidence owners preserve positioned units and schemes | Delivered, functional scope Tested · TC-01–04 | Exact source/atom maps and native availability through combined reads |
| [O02](../functional_reviews/text-characterization_2026-11-10.md#O02) | Shared primary construction owner replaces scattered recognizers | Delivered, functional scope Tested · TC-05/09 | Reused construction outputs and retired duplicate production |
| [O03](../functional_reviews/text-characterization_2026-11-10.md#O03) | Explicit semantic terms, operators and correlated alternatives | Delivered, functional scope Tested · TC-01/02/06 | Independent scope/choice expectations, packed retention and replay |
| [O04](../functional_reviews/text-characterization_2026-11-10.md#O04) | Context and model operations enrich the same document | Delivered, functional scope Tested · TC-07/08 | Cross-boundary support, source-first discovery and native provider evidence |
| [O05](../functional_reviews/text-characterization_2026-11-10.md#O05) | Released operation/storage/read owners serve retained primary products | Delivered, functional scope Tested · TC-02/09 | Indexed membership, partial layers, invalidation and detached reads |
| [O06](../functional_reviews/text-characterization_2026-11-10.md#O06) | Enrichment/admission consumers use primary semantics | Delivered, functional scope Tested · TC-09 | Complete migration inventory and independent native support refusals |
| [O07](../functional_reviews/text-characterization_2026-11-10.md#O07) | Evaluation/model lifecycle owners extend granular assessment | Planned · TC-10/11; triggered TC-I branches | Source-first/output-first results, task-specific supervision and actual qualification |

The operator directed this series to stand on its own on2026-11-10. Existing plans are not
inputs, prerequisites or sequencing authorities for this series, and none is edited. Current
implementation, architectural contracts, the functional review and library documentation supply
the baseline. TC-00–11 own the complete new target and its implementation dependencies.

## Conditional branch state

TC-I01–09 are conditional and unscheduled at publication; none is silently adopted. Their
[decision contracts](text-characterization/assessment-and-investigations.md) define triggers,
evidence and consequences. A baseline package encountering a stated trigger activates only the
relevant bounded decision, whose outcome and affected prerequisites are recorded here. Baseline
family delivery remains required even when an optional replacement is deferred.

## Rule changes and decision route

The operator explicitly selected the enriched-document target and baseline/conditional split on
2026-11-10; this authorizes this plan's scope, not a waiver of an existing source or admission rule.
No RC-numbered rule reversal is supplied by the review, and this plan selects none. Preserve
observation-versus-knowledge authority, original source custody, protected evaluation, current-only
migration and immutable old evidence. TC-00 records the new primary meaning/producer boundary through
an ADR and owning sections. If implementation reveals an actual rule conflict, present the exact
rule and consequence for explicit disposition before depending on its reversal.

Use [ADR-0067](../adr/0067-witnessed-current-only-cutover.md) for current-contract replacement:
faithfully migrate sufficient evidence, otherwise regenerate derived closures while preserving raw
source and plans/evidence. Do not add legacy semantic execution to simplify transition. Follow the
binding's required design/target reviews before substantial ownership changes and at assembled scope;
focused authoring assessment is not a substitute. No extra recurring audit or alignment gate is added.

## TC-11 completion, adoption and next work

Complete all selected family and consumer obligations, accounting separately for source coverage,
operation settlement, semantic quality and provider failure. Do not certify English completeness
from a successful forest or model call. A full-book run must account for all selected source regions
and each family; unassessed regions remain explicit and cannot count as successful empty. Freeze
independent semantic expectations and permissible alternatives before grading. Native compatibility,
source closure, cross-boundary membership, retained replay, failure/cancellation and model/rule change
invalidation must cover the actual released profile.

Run focused tests during delivery. After complete functional scope and final maintenance, use
`uv run ci test` and `uv run ci check`, plus the applicable real-provider/native selections and
retained test-identity union. A mocked provider never qualifies native behavior. Record rustc context
for Rust results. Use `uv run ci docs check` for publication. Conditional branches close with an
adoption decision or explicit deferral; they do not force every optional producer into the baseline.
Resource experiments address actual ambiguity/residency risks, without an invented numerical target.

TC-11 prepares a qualified candidate release and regeneration from authentic source. Activation or
selection requires explicit effect authority after qualification; private staging and source capture
remain separate outcomes. Unavailable required evidence
keeps qualification open. Publication of this plan does not execute these effects.

**Next for this series:** TC-10 independent expectation and semantic assessment, then TC-11 full-book qualification and adoption under their separate execution authority. No dependency on another plan is selected. The original authoring-only outcomes below retain their 2026-11-10 scope; current functional qualification is recorded above.

## Authoring handoff and publication · 2026-11-10

Created this coordinator and seven new supporting documents only. No existing plan or checkpoint
was edited; existing plans supplied no scope/dependency/priority decisions. Source and focused
independent design advice informed the new series. Integration corrections established one
contextual evaluator, early formal-input readiness, mandatory native attachment support checks
and baseline-plus-conditional feature routes. This advice is not the formal TC-00 target review.

- `uv run ci docs check --json`: **passed**, result `b16ad9debdea43e48aca9dc1e9b559ec`,
  866 canonical pages and zero link errors.
- `just turn-end`: **passed**; final receipt-only edits do not change the target or links.
- Read-only feature correspondence: **passed**, all164 source-review feature rows retained in
  [coverage](text-characterization/coverage.md), with package/branch routes.
- Product/provider tests, runtime probes, model training and benchmarks: **not_run**, because this
  engagement creates implementation plans. All implementation and qualification obligations remain
  planned in TC-00–11; conditional branches remain untriggered at publication.


## Authorized remaining-scope execution · 2026-11-11

The operator approved TC-10/11 execution and selected a chapter-and-facet independent reference
panel, with exhaustive source/family coverage accounting over all518 physical pages. Semantic
reference authoring is not exhaustive annotation of every eligible passage. Source-first frames
freeze before corresponding producer-output inspection; output-first frames bind exact retained
output populations. Fresh Sol/high A/B authoring and separate C adjudication preserve existing
protected reference custody and exposure provenance.

The immediate integration package extends operation frames to V3, native output membership and
independent facet matching, plus bounded evaluator inspection. Source-first V3 frames must not
require a producer layer/view that does not yet exist; evaluation binds predictions separately.
Whole-document selection explicitly bypasses narrow pack defaults; direct section membership and
root residual preserve full source coverage. Exact retained input selection authenticates its
registered original rather than inheriting another corpus's configured originals. Combined-view
composition must avoid simultaneous hydration of all book layer payloads.

Baseline is `b7cf3f1a2`, native head `semantic_tc03_09_literals`. The retained integrated source
pin is task1627/product`integrated`/digest`35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`,
project `nce-grinstead-snell-full-book`; original digest is
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
Its source report says display recognition partial and inline/cell coverage unknown. Preserve
or resolve these limits through the existing source-demand owners; do not claim complete
recognition from conversion success. No new qualification is established by this authorization.

### Execution findings and acceptance refinements

This table owns findings revealed by TC-10/11 execution; the earlier producer-review IDs retain
their original owners and bounded closure claims.

| Finding | Responsible component | Current disposition and closure evidence |
| --- | --- | --- |
| TC-E01 | Protected reference admission | Corrected, bounded Tested2026-11-11: initially uninspected opportunities permit independent source-state authoring; known frozen states remain exact. Native12 receipt`ff28f9ed40754f9ba377194e6a28faa4`. |
| TC-E02 | Output-first author packets | Corrected, bounded Tested2026-11-11: exactly pinned witness closure is separate from the frozen assessed population; native12 receipt above. |
| TC-E03 | Combined view and detached consumers | Implemented, bounded Tested2026-11-11: streaming/lazy closure, bounded node and exact coverage pages,64MiB document metadata versus8MiB layers. Pure89 receipt`46b3d8a087dd45219d03925911bf8630`; native2 receipt`401fc5c94a7241f598a05f2b996768bb` publishes/reads a valid composed view beyond8MiB. Actual full-book consumer qualification remains open. |
| TC-E04 | Construction lexical projection | Corrected, bounded Tested2026-11-11: native layout-only tokens remain evidence without participant terms; multiline interpreted lexical labels declare whitespace normalization while original spelling remains retained. Construction41 receipt`edac73abd9be47deb03fbf9ec824df15`. Authentic workload replay remains open after failed stage504. |
| TC-E05 | Independent source-semantic comparison | Implemented, bounded Tested2026-11-11: versioned source-anchored task projections declare role scheme, witness/complete named slots and correlated choice constraints. Pure149 receipt`7a4cf5560f684e0f9f81d1b6eef76cf7`; native11`949f73df6d744b8a8ccec1f8eb110175`; full typing`23c0444400b24135ac496c75031f96e7`. Actual source/output grades remain open. Preserve exact native/retained graph checks, original set40/C210–230 and all failed attempts. Unsupported comparison contracts are unavailable, not linguistic errors. |

Set40 froze26 source opportunities across21units/all12chapters before the relevant producer
outputs. Fresh independent A/B/C passes are retained; C210–230 cover28 cases, including13 native
references. They establish references, not producer quality. Both authors and the adjudicator
identified TC-E05 independently. Focused design advice confirmed that task projections must read
declared retained meanings across the relevant family population; permissive graph matching alone
cannot equate arbitrary decompositions or establish complete scope/choice correctness. The
[assessment companion](text-characterization/assessment-and-investigations.md#implementation-and-library-route)
owns this refinement's target contract. Revised task-wire references require explicit version and
source/question applicability; they cannot overwrite the original passes or follow producer answers.
