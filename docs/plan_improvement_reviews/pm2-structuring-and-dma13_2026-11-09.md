# Improve Milestone Two structuring and qualification under DMA-13

**2026-11-09 · Source-inspected; recommendations Proposed.** Reviewed the
[PM2 coordinator](../plans/production-milestone-two_2026-11-08.md), its source/runtime,
parser, interpretation, retrieval/delivery, learned extraction and assessment companions,
and [DMA-13](../plans/domain-model-alignment_2026-11-08.md#dma-13) at `37c357357`.
The supplied ChatGPT Pro input, `docs/target-pipeline-design/production-milestone-two-improvements.md`,
was untracked, SHA-256 `662965cb73e9fd84b4c08cfcdbfca432ba0a7d2abcbb0a5643c1bfc855c1bb08`.
Pro reviewed `e55bcfc54`; the intervening commit changed acceptance documents, not product
code. Section references below refer to that exact input. The
[earlier extraction review](pm2-extraction-gliner2-spacy_2026-11-09.md) retains its I01–I10
identities and the PM2 coordinator retains their disposition.

The remaining footprint spans source-to-observation mapping, local structure, bounded decisions,
retrieval, release-scoped delivery and assessment, plus materially affected runtime and proof
paths. The review used source, selected tests and dated retained results. It did not rerun
recognition, inference, protected grading, training or qualification. It used the seven guides
and their supplements for capability discovery, with effective versions checked against
declarations and worker code; undocumented internals remain version-specific hypotheses.
The [design standard](../design_review/design_principles/standard.toml) informs the judgments
below, especially FP-02/03/04/06/07, A2/A4, CI-01–04 and CI-10–13, and H18–20/H22–24.
The [test assessment](../design_review/design_principles/core/test-assessment.md) calls for
independent expected meaning and checks that discriminate the suspected failures.
The [knowledge, assessment and query owners](../design/README.md#responsibility-map) retain their authority.

**Recommendation.** Keep the current model roster. Stage a private full-book candidate from the
retained Standard/Nemotron source when its execution contracts are ready. Improve a small number
of source-backed workflows by fixing result visibility and composing evidence already produced.
Select improvements only where a paired workflow demonstrates value and preserves source fidelity.
Treat model extensions, fitted ranking, and larger runtime changes as separate decisions with
specific triggers. Private staging does not confer public standing or selection.

## What the results establish

| Retained evidence | Judgment for the next change |
| --- | --- |
| [Variance condition](../design_review/evidence/2026-11-09_pm2-public-condition/README.md), run 477/cut 594 | Ordinary Reader, CLI, fresh MCP and detached verification agreed on the released assumption and exact roles. The earlier narrower-cue rubric refused; a separately authored role-anchor frame later passed. Preserve both. This is a publication control, not evidence of improvement across four models. |
| [HanLP layout diagnostic](../design_review/evidence/2026-11-09_pm2-definition-hanlp/README.md) and [native definition](../design_review/evidence/2026-11-09_pm2-native-definition/README.md) | The layout repair restored an orphan role; a subsequent chain produced a bounded private target and detached proof. Producer availability and proof transport do not establish independent semantic qualification. Repeating the earlier split experiment alone cannot resolve this. |
| [Protected d1 pair](../design_review/evidence/2026-11-09_pm2-interpretation-pair/README.md) | Exact fair-coin normalization improved; roulette quantity, condition host and local referent remained unsupported. The host and antecedent were available in the reviewed-candidate diagnostic. This narrows the cause to interpretation/consumption on those cases; it does not prove a rendering defect. |
| [Competitive retrieval](../design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md#native-competitive-comparison) | All three positives already ranked first, eight targets fit inside top ten, and Dipo changed context on two cases. Both d1 arms missed exponential density despite rank 1, and correctly left the negative unlinked. Keep `/10`. |
| [GLiNER boundary diagnostics](../design_review/evidence/2026-11-09_pm2-gliner-boundary/README.md) | Nineteen of 24 supplied spans were scoreable and 126 shared scores agreed under individual injection. Some needed endpoints were present but weakly scored; no ordinary definition attachment decoded. This does not qualify jointly packed spans or identify every decoder loss. |
| [DMA capture](../design_review/evidence/2026-11-09_dma-source-rule-capture/README.md) and [origin inventory](../design_review/evidence/2026-11-09_pm2-adoption-preflight/README.md#dma-13-origin-availability) | Evaluations 42/43 remain regression evidence. Bounded Preface and subsection capture improved privately; no new protected grade exists. Unreadable formulas and missing fit/calibration populations limit those outputs or claims. They do not gate private staging under revised DMA-13. |

## Amendments recommended for PM2

<a id="I01"></a>
### I01 · Deliver every attempted, completed d1 question

**Observed defect; recommended first.** Pro §2.1, [PM2-07](../plans/production-milestone-two/gliner-and-d1-interpretation.md#PM2-07),
[PM2-08](../plans/production-milestone-two/retrieval-composition-and-delivery.md#PM2-08)
and [PM2-11](../plans/production-milestone-two/textbook-assessment-and-adoption.md#PM2-11).
[`pm2_native`](../../python/corpus-structure/src/corpus_structure/methods/pm2_native.py)
settles all-missing span replies as `empty`; [`pm2_unit_result`](../../python/corpus-structure/src/corpus_structure/methods/pm2_result.py)
only constructs products on `succeeded`, although the
[typed projector](../../python/corpus-structure/src/corpus_structure/methods/pm2_interpretation_products.py)
can describe a missing read. Keeping raw replies alone requires each consumer to infer the
same missing product. Reuse the released family and authenticated source mapping to deliver
unresolved typed results on completed valid empty requests. Preserve operation `empty`,
question identity, scope, native `found`, and absence of an answer location; do not create
an occurrence. Apply the same rendered-state, question-population and source validation to both
paths. Reject inconsistent empty replies, and distinguish failed, limited, cancelled and
unattempted requests. Check whether release/product versioning is required for changed output
identity; preserve the meaning of archived empty results and regenerate only affected products.
Closure: the same absent question has the same typed outcome in a mixed and all-empty native
reply, with a tampered source or question rejected and ordinary reads agreeing. This restores
CI-04 without a second interpretation path. Extend the
[existing unresolved decision controls](../../python/corpus-structure/tests/semantic/test_pm2_interpretation.py)
through completed result projection; a direct projector test alone would miss this defect.

<a id="I02"></a>
### I02 · Show current assessment state alongside the paired transition

**Observed reporting gap; recommended with I01.** Pro §§2.2, 6; PM2-11.
[`compare_assessments`](../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py)
treats `unsupported → unsupported` as unchanged; the
[managed evaluator CLI](../../python/corpus-structure/src/corpus_structure/cli/eval.py)
and [review view](../../python/corpus-structure/src/corpus_structure/serve/review_views.py)
share this comparison. Keep the old transition categories. Derive an orthogonal revised
state view (supported, unsupported, ambiguous, unassessed) and retain non-comparability as
a separate pairing judgment. Identify persistently unsupported cases from both sides, so
newly unsupported cases are not mislabeled. Reuse exact unit/case IDs and version output
meaning where consumers require it. Display the observed stage/reason from existing evidence
when available; show an unknown reason otherwise. Do not infer “missing candidate” when
the authenticated offered list contains it. A compact summary plus existing detail is
preferable to a new stored assessment ledger or changing past grade semantics.
Closure: mixed transitions including regression, persistent failure and non-comparability
agree with existing protected case details on both delivery paths. Reuse the existing
source-first and output-first frames rather than introducing an additional grader (FP-02/06).
Retain the [native exact-arm control](../../python/corpus-structure/tests/evaluate/test_operation_assessment_native.py);
a summary extension must not admit a changed configuration or semantic grain.

<a id="I03"></a>
### I03 · Compose located parts before asking another model

**Recommended; completes and sharpens earlier [I02](pm2-extraction-gliner2-spacy_2026-11-09.md#I02)
and [I07](pm2-extraction-gliner2-spacy_2026-11-09.md#I07).**
Pro §§3.3, 4–5; PM2-03/04/07/08/11. Extend the existing
[returned-group adapter](../../python/corpus-structure/src/corpus_structure/methods/contribution_adapter.py)
only where a reader needs attributed predicate-to-subject/object, qualifier, attribution or
quantification candidates. Today the generic association pass handles definition/table roles;
an assertion group already preserves its fields. A model-grouped association is one native
observation, with no fabricated relationship score or independent confirmation. Preserve
partial groups and competing readings. Compare native group association, ordinary released
local composition and d1-assisted selection on the same question. A d1 disagreement is
evidence about the decision, not a universal veto on independently inspectable proposals.

Use [HanLP’s retained products](../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py)
for located temporal, purpose, manner and causal modifier candidates and clause containment
where it resolves a real scope question. Keep native scheme labels and exact predicate
members. A temporal modifier is not necessarily a deadline; a causal label is not
a published claim. The existing narrow [condition constructor](../../python/corpus-structure/src/corpus_structure/methods/m1_source_capture.py)
assumes a unique active host and complete roles. Prefer a versioned qualifier-to-host
proposal independent of an SVO record; qualify passive, copular, intransitive and
coordinated/multiple-qualifier cases separately. For the binomial definition distinguish
source sentence layout, predicate/role recovery, declaration identity and the released
use-to-definition edge. Reuse the existing native chain and test competing declarations
and the constant-density no-gain control. HanLP 2.1.7’s [MTL and alignment facilities](../libraries/parsing/HanLP.md)
justify syntax-only versus added SRL ablation. The punctuation-sensitive sentence detector
is a boundary challenger only if needed; separately loaded SDP/AMR or other heads need a
named unresolved relation and asset/label/offset qualification.

The [Maverick adapter](../../python/corpus-structure/src/corpus_structure/methods/pm2_maverick_products.py)
already delivers mentions and local clusters. Prefer deriving a located local referent
proposal from them over duplicating raw cluster products. Compare the current nearest member
with an informative earlier name or nominal using retained POS/phrase data; test both if the
second signal helps. Keep representative choice separate from cluster membership and global
identity. [Maverick 1.0.7](../libraries/parsing/maverick-coref.md) supplied mentions isolate the
candidate inventory, not the whole native detection computation. Reuse PM2-06 controls for
nested mentions and missing boundaries; only investigate segmented joint clustering after
observed cross-partition misses, with false-merge, exact-map and resource controls. Internal
segmented modes and seeded clusters are not a public cannot-link or confidence contract.

Use [spaCy 3.8.18](../libraries/parsing/spacy.md) named rules, overlapping span groups,
`DependencyMatcher` and bounded ancestor/conjunct traversal for exact attachment and coordination
alternatives. Keep native token/dependency authority and never turn expand/contract alignment
into an exact anchor. Closure for the first slice: correct role, direction and citation across
the ordinary Reader, CLI and fresh MCP, with a failed sibling, a competing host or antecedent
and an alternate vocabulary. Require independent admission for public delivery and exact
detached proof where selected. This keeps one reusable ownership path (FP-03/04, CI-01–03/11).

<a id="I04"></a>
### I04 · Diagnose GLiNER loss at the seam where it occurs

**Recommended bounded experiment; refines earlier [I03](pm2-extraction-gliner2-spacy_2026-11-09.md#I03)
and [I04](pm2-extraction-gliner2-spacy_2026-11-09.md#I04).** Pro §§3.1–3.2, 3.4–3.6, 5;
PM2-03/07/11. Use the current [boundary diagnostic](../../python/corpus-structure/src/corpus_structure/methods/gliner.py)
on the pinned GLiNER2 local 2.1.0/Base profile. Compare native discovery, fixed independently
produced exact spans, and their bounded union in the same role/binding consumer. Distinguish
source coordinate refusal, proposal absence, weak role score, threshold or NULL/count effect,
overlap suppression, and instance assignment. Retain only inspected diagnostics. The
[boundary guide and supplement](../libraries/parsing/gliner2.md) distinguish auxiliary
start/end/inside logits from NULL/count outputs; do not infer the latter from the diagnostic
names. If an exact version-specific forward/decoder observation cannot be captured or reproduced,
leave the rejection cause unknown. Evaluate packed order, capacity, overlapping and repeated
extents, known wrong-role candidates and independent role/attachment evidence. Reviewed
injection diagnoses the decision; do not count it as ordinary discovery.

After that, compare a single predicate-local polarity or modality attribute to no attribute.
Use a released vocabulary, applicable mention type and qualified labels; preserve the mention,
literal cue and model prediction separately. Attribute labels can change shared proposal
competition, and a single-label winner is not abstention. Check neighboring opposite
statuses, a missing mention and an unrelated cue; report both mention recovery and label
correctness. Prefer natural anchored records with appropriate optional fields. Introduce
cardinality/exclusivity only where valid (one actor or qualifier may govern several events).
Reserve latent/anchorless grouping, constrained `Classifier` and JointIE for diagnosed
grouping failures; graph feasibility is not source support. Long classification aggregates
window scores and may suit a named document-level classification; it cannot locate a witness
or establish that two cues occur together.

Keep the [learned extraction route](../plans/production-milestone-two/learned-extraction-investigations.md)
conditional: spaCy preset spans plus `SpanCategorizer` for label loss, `SpanFinder` for
proposal loss, typed occurrence pairs for binding loss, lightweight models before a custom
`TrainablePipe`. Require independently judged pairs or complete/masked span supervision.
For recurring GLiNER loss, validate exact nested/repeated annotations and capacity,
use injection-free proposal recall (`dry_run_recall_steps`), then test an adapter (LoRA/DoRA)
against the unchanged checkpoint before full tuning. Neither a six-window panel nor scores
on injected gold establish a training case. Earlier I05/I06/I09 remain the owners.

<a id="I05"></a>
### I05 · Give d1 a precise decision and keep the literal parts independently useful

**Recommended paired investigation; prior I04 and PM2-07/11.** Pro §§4, 6.
The [question compiler](../../python/corpus-structure/src/corpus_structure/semantic/interpretation_questions.py)
already uses explicit Noul criteria and stable local aliases; dynamic Choice descriptions
are generic. Compare those with release-owned task-specific descriptions: exact qualifier
plus each host predicate and clause, focal mention plus candidate phrase in context, exact use
plus defining content and scope. Keep identical authorized source and candidate inventories,
durable IDs and native payloads out of the model-facing view unless relevant. Compare order
and paraphrase controls, wrong-role/ambiguous options, genuine no-match, and the exponential
case on its fixed offered list. Test separately whether a useful parser-derived answer is
available without d1. Do not treat ordinal separation or candidate-relative probabilities as
calibration. Native abstention settings described in the
[d1 guide](../libraries/parsing/Liquid_AI_d1-2B.md) have layer-specific behavior; retain
explicit alternatives, no-match, insufficient evidence and withholding in the released contract.

For the [roulette quantity](../design_review/evidence/2026-11-09_pm2-quantity-span/README.md),
grade the written literal, positive magnitude, written unit, loss role and exact normalization
separately. Use authorized pointers and the original span when parsing fails. Numeric unit hints
do not authorize conversion; a role is not a sign and native endpoint gating can fail before
application thresholds. Preserve the fair-coin exact normalization control. Group independent
questions when supported; a dependent follow-up needs its own bound request. Closure is an
independently supported structural improvement with unchanged source authority and meaningful
unresolved cases, not a better model score.

<a id="I06"></a>
### I06 · Qualify discourse-aware retrieval on a frame that can distinguish it

**Conditional improvement.** Pro §§4, 6; PM2-05/06/09/11. The
[existing selector](../../python/corpus-structure/src/corpus_structure/methods/pm2_dipo_products.py)
chooses the smallest fully mapped bounded sibling and reports omissions. The
[query recipe](../../python/corpus-structure/src/corpus_structure/methods/contextual_query.py)
renders only its first EDU as a generic neighbor. Reuse the selector. Compare current literal,
current neighbor, complete mapped sibling plus focal side, relation, nuclearity and exact ranges,
and a size-matched contiguous control. Explore an eligible ancestor branch only for cases where
a local subtree omits useful context. Bind omitted ranges and any budget truncation; keep native
rhetorical labels as context, not authority for semantic relations. The
[Dipo guide](../libraries/parsing/dipo.md) supports separating raw end-to-end and supplied-EDU
comparisons: `predict_both()` uses reconstructed input. Grade boundaries, ordered child split
on a matched parent yield, then relation/nuclearity, then context use. Keep failed and unmapped
cases in coverage accounting. A DMRST error-cascade diagnostic is more direct than changing
parsers to address unexplained topology loss. Tree equality or grammar-valid decoding is not
exact source fidelity; generative and wider modes stay conditional under PM2-06.

For a top-10 claim, freeze more than ten eligible and actually competitive definitions with
neighboring concepts, senses and definition/use negatives. Report producer exclusions, context
actually rendered, ranking conditional on eligibility, and downstream selection conditional on
offer. Use the existing Sentence Transformers encoders and configuration-bound paired arms;
do not change corpus, ranking recipe and selection prompt together. When a meaningful eligible
inventory is unavailable, use bounded ordering or fixed-offer comparisons and make no recall
claim. A tie retains the incumbent. This makes assurance proportionate to the claim (H20).

<a id="I07"></a>
### I07 · Qualify workflows on the staged candidate, not the entire model roster

**Recommended plan reconciliation.** Pro §§1, 6 and sequence; PM2-11/12 and DMA-13.
The coordinator still describes completion in terms of a qualified four-profile release.
Keep per-profile technical qualification for profiles actually relied on; distinguish that
engineering objective from selecting a useful workflow and from closing every PM2 obligation.
Update the coordinator and assessment companion only in a subsequent plan revision. Keep
Standard/Nemotron source identity, physical coverage, migration and current-only contracts,
prior selected results where present, and archived evidence. Chandra stays excluded.
No separate analytical predecessor, complete formula coverage or independent calibration
population is required to stage. Preserve availability and limits through ordinary Reader,
managed CLI, fresh MCP and exact detached proof where portable closure is claimed.

| Workflow | Compatible starting point and gain | Material preservation and refusal |
| --- | --- | --- |
| Find a definition and cite it | Retained literal/`/10` results and compatible cut 517 components; compare only on exact corresponding source and question. Use the private binomial target as a transport control. Look for an additional correct definition or corrected use-to-definition link with a usable citation. | Exact term/content/cue, negative binomial, definition versus use/explanation; no cross-sense link. A top-ranked unsupported target stays unselected. |
| Follow a claim to a condition or exception | Current ordinary located route; use p289 cut 594 as an exact positive preservation control. Add an independently reviewed qualifier construction where the incumbent misses or misbinds the host. | Preserve premise and lexical host, attribution, scope and the admitted sibling under failure. Use a business instruction with different released vocabulary on the same path. A claim that there are no exceptions is refused or scoped if coverage cannot support it. |
| Resolve a local reference or inspect a stated quantity | Current nearest-member route and fixed-offer d1 comparison; preserve fair-coin normalization and separately target gambler identity or roulette roles. Grade reference and quantity as separate questions. | Same occurrence and local scope, unknown rather than no match when evidence is incomplete, no global identity or fabricated literal. Preserve useful magnitude/unit/role fragments independently. |

Freeze independent source opportunities before inspecting candidate outputs. Use the existing
protected evaluator and distinct semantic relation, role membership, exact extent, completeness,
and admission judgments. A rubric change creates a new reference and comparable arms; preserve
the older refusal. Reuse compatible historical controls without treating them as unseen data.
Check coverage and emitted fidelity separately. An unresolved reading blocks the workflow only
if the workflow depends on it. For formulas retain the exact written expression/location,
stated binding and qualification, or an image/literal and unresolved status. Optional algebra
does not qualify ordinary structuring. A fitted policy requires valid labeled fit evidence;
calibration and held-out evidence govern those claims only. A small reproducible consumer
journey suffices for a scoped usefulness claim; no general agent benchmark is needed.

## General and conditional improvements

<a id="I08"></a>
### I08 · Prevent repeated evidence from acting as independent support

**Recommended diagnostic; numerical changes conditional.** Pro §§7.1–7.3; PM2-08/11 and
[interpretation owner](../design/D5-consolidation-identity-confidence.md).
The [finite interpreter](../../python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py)
uses dependence scopes for connectivity; they do not numerically down-weight summed
log potentials. Keep candidate-relative meaning, unknown omitted mass and event-union
semantics; one feasible candidate is not certainty. When the same source/group recurs in
overlapping windows, deduplicate equivalent attributed evidence in the operation that assembles
it, not by string or occurrence alone. Keep genuinely distinct roles, derivations and
disagreement. Compare independent versus grouped potentials only after demonstrating duplicated
support or a changed decision; the [table path](../../python/corpus-structure/src/corpus_structure/methods/table_interpretation.py)
supplies a local pattern, not a generic correlation model. Test duplicate replay, independent
corroboration, conflicting readings and union accounting on fixed cases. Add inspectable clause,
cluster and role agreement diagnostics before [fitting](../../python/corpus-structure/src/corpus_structure/semantic/record_policy.py);
structure-quality features alone can reward a well-located wrong answer. Keep pgmpy for an
observed exact-inference bottleneck and Pyro for a specified latent/hierarchical model and
data. Neither is a PM2 staging dependency.

<a id="I09"></a>
### I09 · Make runtime and portable evidence cheaper where staging shows the burden

**Parallel measurement candidates.** Pro §8; PM2-02/08/12 and earlier I08.
Compare singleton with the [existing GLiNER microbatch worker](../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py)
on compatible profile/schema/policy and mixed input lengths. Preserve per-window order,
source maps, admission limits and outcomes. Compare healthy worker reuse across compatible
fallback waves with current [wave custody](../../python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py).
Do not reuse after a failed worker or across an incompatible profile; preserve cancellation,
claim settlement, exclusive GPU ownership and incumbent restoration. Measure throughput,
peak memory and load counts with parity, refusal and recovery controls before claiming benefit.
The [Transformers guide](../libraries/parsing/transformers.md) targets 5.22.2; current PM2
profiles pin 5.22.1. Verify offsets/overflow and tokenizer/model/runtime identity before
any batching change. HanLP token-budget batching and d1 packed-row/group limits are separate
contracts; d1 already batches natively. Native forward batching and bounded reuse come before
compile, quantization, attention/cache alternatives, continuous generation or serving changes.
Generic Transformers System One does not establish parity with d1's pointer-backed extraction,
abstention or source custody. Reopen it only as a bounded closed-choice comparator with
compatible artifacts and semantics. Do not homogenize provider pins on the basis of an overview.

The [affine detached witness](../design_review/evidence/2026-11-09_pm2-affine-ordered-source/README.md)
carried about 336 MB of relation files; the [bounded live read](../design_review/evidence/2026-11-09_pm2-bounded-retrieval/README.md)
returned two rows in 5,463 bytes. They establish amplification worth investigating, not
equal proof workloads or an expected savings ratio. Trace which relations exact offline replay
actually needs. Prefer existing owner projections and immutable shared evidence; use
item-addressable reports or a versioned completeness witness only if they can authenticate
the selected item and the required population, including omission/substitution and sibling
mutations. Preserve the existing exact mode until parity; measure bytes, read and replay
cost. Keep ordinary output claims unchanged (FP-07, H18–20/H24).

Additional repeat work is visible in the [spaCy rule preparation](../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py):
matchers are prepared per variant and negation scans repeat per match; the
[definition route](../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)
can prepare rules per call. If staging shows material repeated work, reuse the task-local
preparation pattern from M1, group native pattern IDs by mechanism and identical required
columns, and index negation once per source block. Check stable order, per-variant unavailable
annotations and exact witnesses. Avoid a durable cache. Use component error context only
if batch failure warrants it; a partially mutated Doc is not a settled output.

<a id="I10"></a>
### I10 · Keep artifact identity refinement separate unless a real miss warrants it

**Deferred outside the immediate amendment.** Pro §7.4. The
[artifact identity route](../../python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py)
uses exact controlled-code/title comparisons; graded lexical similarity in nomination is
not the same as evidence for an accepted identity. For demonstrated title-variation misses,
compare versioned graded title and optional alias agreement against the exact baseline on
the same blocked pair population, including near-duplicate unrelated titles, missing values,
and correlated title/alias signals. Keep identity, reference, revision and supersession
distinct. Do not add a fitted policy without applicable labels, or make this a prerequisite
for local PM2 structuring.

## Adoption order and limits

Start I01/I02 in parallel with identifying the exact staged workflow scopes in I07.
I03 can begin from retained observations; I04 and I05 isolate errors before larger changes
to the same consumer. Pursue I06 only on a discriminating frame. Stage compatible full-book
derivations independently of optional model work; use the staged candidate for the named
assessments and operational qualification before selection. I08/I09 can use actual staged
workload evidence without holding up semantic work. I10, learned modes, new inference engines
and unneeded heads remain separate or conditional. Preserve existing finding IDs and route
any changed rule through the plan and architectural decision owners. No default, accepted
plan, release, runtime or completion status changes from publishing this review.
