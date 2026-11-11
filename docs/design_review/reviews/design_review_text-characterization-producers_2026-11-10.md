# Enriched-document producer target review

## Judgment and scope

**Design / target · combined library-targeted primary characterization, typed fidelity, packed
interpretation and consumer/native replacement · 2026-11-10. Decision: Accept scoped, Proposed,
for the revised target specified below.**

The revised TC-03–09 target supplies a coherent route from positioned native/formal evidence
through shared construction and contextual interpretation to retained consumer products.
Acceptance includes the explicit native/formal payloads, qualified required-choice references,
packed choice sites and finite witnessed-support constraints agreed during this review. The
present implementation does not yet supply these capabilities.

[ADR-0081](../../adr/0081-enriched-document-analysis-layers.md)'s immutable document/layer/view
foundation remains applicable. This review extends its producer and consumer boundary; it does
not reopen source custody, private publication, knowledge admission or the selected PostgreSQL
lifecycle.

Source inspected: clean `6c50a847fa4da2864c98a569d5cf97da8e7ab9c0`. Subsequent root qualification
fixes and generated-product regeneration are outside this baseline. Inputs are ADR-0081, the
[foundation entry review](design_review_text-characterization-entry_2026-11-10.md), the
[TC coordinator](../../plans/text-characterization_2026-11-10.md) and its
[native-evidence](../../plans/text-characterization/native-evidence.md),
[construction/interpretation](../../plans/text-characterization/constructions-and-interpretation.md),
[contextual](../../plans/text-characterization/contextual-characterization.md) and
[consumer-migration](../../plans/text-characterization/consumer-migration-and-integration.md)
companions. Standard: core3.3, heuristics1.0, code-intelligence1.4 and repository binding, applied
through `design-review` and `design-review-code-intelligence`.

The workload is the complete 518-page proving document, source-aligned natural sections,
repeated bounded inspection, overlapping analyses, ambiguous local constructions and detached
export on the existing single-operator host. Universal English completeness, scientific truth
and quantitative performance improvement are excluded.

The audit input is the
[producer reconciliation](../audit/README.md#text-characterization-producer-reconciliation),
published at `5b4f0b8f6` against source `6c50a847fa4da2864c98a569d5cf97da8e7ab9c0`, carrying the
earlier [entry refresh](../audit/README.md#text-characterization-entry-refresh) within its original
scope. No whole-system or test-architecture audit is claimed.

## Responsibility and fidelity

**Proposed.** Primary characterization is one semantic responsibility with family-specific
operations, rather than one universal grammar or provider. TC-03 retains native evidence;
TC-04 owns positioned formal syntax; TC-05 authors construction meaning; TC-07 produces
contextual evidence/hypotheses; TC-08 owns explicit model questions; TC-06 alone evaluates
symbolic nodes under inherited environments. Domain consumers add their own domain conclusions.

| Fact or relationship | Authority and fidelity | Identity, coverage and consumer constraint |
| --- | --- | --- |
| Document/native placement | Existing source owner; captured source facts | Exact base/projection and occurrence pins; analytical grouping does not alter containment |
| Native token, dependency, constituent or SRL evidence | Selected provider/run and scheme | Container/index and exact source correspondence; missing columns and disagreements survive |
| Formal constituent | Selected input representation, grammar/start and derivation | Input-local positions plus literal parent/correspondence; recognition does not establish glyph fidelity or scientific validity |
| Construction/role | Released construction operation | Named premise bindings and support; native syntactic labels do not silently become semantic roles |
| Contextual proposal | Named provider/question or contextual hypothesis operation | Exact examined context, offered population and choice premises; unknown does not mean absent |
| Evaluated meaning | TC-06 node/environment operation | Local result DAG plus exact upstream support and selected context revisions |
| Witnessed downstream attachment | Released support contract, independently enforced at native boundary | Producer authenticity is necessary but insufficient; declared endpoint/member/choice relationships must hold |

The task-bound `ctx.characterization_operation(ref)` port is appropriate if it retrieves the
exact producing task's archived operation determinants and authenticated inputs. It must not
reconstruct history from current defaults or allow a payload to nominate its own authority.
Resolve it once per operation or compatible batch, rather than per annotation.

## Required target corrections and binding constraints

<a id="F01"></a>

### F01 — Native and formal evidence require typed durable representations

**Interface-checked diagnosis, 2026-11-10.** The current `CharacterizationAnnotation` declaration
in [characterization.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/characterization.yaml)
has labels, scores and references but no adequate native-token or formal-input payload. The
existing [annotation producer](../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
retains useful native columns and execution identity outside that central contract.

**Proposed correction.** Accept optional typed `Annotation.native_token`, native-run metadata,
root-only `Annotation.formal_input` and positioned `Annotation.formal` payloads. Their optionality
accommodates other annotation kinds; executable kind-specific constraints must require the
payloads where their meaning depends on them.

Binding constraints:

- Native token identity includes its container and index; sentence, head and subword references
  resolve in declared populations and schemes. Preserve exact text and whitespace, native
  morphology/columns and per-column availability. Boolean spacing cannot substitute for
  arbitrary whitespace.
- Native-run metadata retains actual provider/runtime/model/configuration/artifact identity
  through typed values or authenticated references, with an explicit configuration codec.
  Unavailable columns are not silently encoded as ordinary empty values.
- A formal-input record identifies its exact input text, representation, grammar/start, literal
  parent occurrence, recognition/recovery outcome and correspondence.
- Recognized or normalized LaTeX positions remain a distinct coordinate space. Parent source
  anchoring does not justify invented character correspondence to PDF text; unavailable
  correspondence remains explicit.
- Formal nodes retain required token/rule positions, visible and container positions,
  synthetic/epsilon distinctions and typed normalized values. Exact numbers do not become
  lossy floating-point values.
- Membership and reader indexes retrieve these records through ordinary pinned layer operations.
  No native JSON hidden in `provenance`, parallel arbitrary inventory or new report decoder
  becomes the authoritative semantic representation.

This correction addresses FP-02/04/05, DP-02/04/08/15/24, CI-01/02/04 and G2/G6/CI-G1.
Closure belongs to TC-03/04 with model/retention integration and independently authored
native/formal roundtrip expectations.

<a id="F02"></a>

### F02 — Citation closure does not establish cross-layer choice support

**Interface-checked diagnosis, 2026-11-10.** Current required-choice fields are local strings,
while `external_premises` validates references to arbitrary inventory members. Neither
representation expresses that a downstream result requires a particular upstream analytical
choice. See the released
[choice declarations](../../../python/corpus-structure/src/corpus_structure/model/semantic/characterization.yaml)
and [layer validation](../../../python/corpus-structure/src/corpus_structure/semantic/characterization.py).

**Proposed correction.** Add typed layer-qualified required-choice references, distinct from
citations.

Resolve targets specifically as choice members under their own archived layer authorities.
Validate selections jointly and transitively, including exclusive/unknown compatibility, exact
source/dependency pins and required selections. Qualify group identities by layer; equal local
IDs in separate layers remain distinct. A citation, compatible source text or authentic upstream
layer must never imply that its choice was selected.

TC-06's local evaluated DAG preserves exact upstream requirements without relabelling upstream
choices as newly authored local evidence. Readers, native guards and detached replay consume
the same selection contract. This correction addresses FP-04/05, DP-02/07/08/09/12,
CI-02/05/11/13 and G2/G6/CI-G2.

<a id="F03"></a>

### F03 — Packing needs explicit choice sites, beyond ordinary DAG children

**Interface-checked diagnosis, 2026-11-10.** `CharacterizationTermEdge` currently has an ordinary
target. `project_reading()` in
[characterization.py](../../../python/corpus-structure/src/corpus_structure/semantic/characterization.py)
traverses every child. Attaching rival roots as ordinary children would require incompatible
branches together or encourage enumeration of parent combinations.

**Proposed correction.** A child site has exactly one of an ordinary term target or a local
choice-group reference. Ordinary child sites remain conjunctive; a choice site resolves the
selected member root.

For a single-valued site, a complete supported reading requires exactly one selected member.
Any supported multi-root site needs an explicit composition meaning; group compatibility alone
must not turn alternatives into conjunction. An unresolved site remains explicit in a partial
projection, rather than disappearing or masquerading as a complete reading.

Include choice-site/root edges in acyclicity validation. Keep source semantic disjunction as
an ordinary semantic operator, distinct from analytical uncertainty. Preserve shared children
without constructing parent cross-products. Independent shared-child, nested-site,
incompatible-selection, cycle and unresolved-site expectations establish this correction.
It addresses FP-04/05/07, DP-02/07/08/12, CI-05/08 and A2/A4/G6.

<a id="F04"></a>

### F04 — Native support must enforce witness relationships, not only basis shape

**Interface-checked diagnosis, 2026-11-10.** Current `compile_attachment_policies()` and
`validate_released_attachment_rule()` authenticate released basis schemas. The
[native characterization guard](../../../python/corpus-structure/src/corpus_structure/semantic/sql/characterization.sql)
checks that schema and reference existence. Those checks alone do not establish that the
supplied host/member corresponds to the rule's actual witness bindings. Existing
[`predicate_argument_inventory`](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql)
instead reconstructs a substantial predicate/argument inventory.

**Proposed correction.** TC-05/09 supplies finite released endpoint/source/member/role/choice
constraints, with a generated or otherwise single-authority mechanical realization at native
publication/admission. Remove superseded SQL linguistic recognition when affected consumers
migrate.

The native guard must reject an authentic producer's attachment when its host or members
disagree with its retained witness bindings. It need not independently solve English or prove
every coherent construction linguistically correct; independent semantic assessment owns that
question. This distinction preserves meaningful native protection without a second NLP
implementation.

Closure requires the authentic wrong-host control alongside foreign-layer, invalid-extent,
forged-origin and incompatible-choice controls, plus the complete TC-09 call-site/retirement
inventory. Model-only predictions retain private proposal standing unless a separately declared
support contract qualifies stronger use. This correction addresses FP-01/03/04/05,
DP-01/03/05/08/23, CI-01/02/11/12 and G1/G3/CI-G1/CI-G2.

Current disposition of F01–F04 belongs only to the
[TC coordinator](../../plans/text-characterization_2026-11-10.md#review-disposition).

## Library composition, alternatives and execution fit

**Interface-checked, 2026-11-10.** Installed spaCy3.8.18 and Lark1.3.1 sources support the
selected integration surfaces. Lark's `ForestTransformer` supplies bottom-up
symbol/intermediate/packed/token callbacks; its `_visit_node_out_helper()` passes results to
the active parent and deletes its temporary result entry. `single_visit=True` therefore does
not by itself provide reusable results to every parent. The plan correctly requires an
operation-local immutable result map or equivalent qualified callback adaptation. The matching
[tagged forest implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py)
and the existing
[capability account](../../library_leverage/libraries/text-characterization/ambiguity-and-alternative-interpretations.md)
preserve the enabling mechanisms and limitations.

**Proposed.** Keep spaCy `Language.pipe` and prepared matchers, HanLP's existing multitask
worker, direct Lark forest reduction and ordinary typed environment-aware evaluation. Lark
supplies packing/traversal; the application supplies choice semantics, stable IDs, support and
inherited environments.

Enumerated trees are suitable only for deliberately bounded projections. A generic constraint
solver, graph service, provider framework or durable per-node evaluator lifecycle adds no
necessary capability here. Raw JSON and consumer reconstruction lose the distinctions required
by F01–F04.

A new construction revision can reuse native evidence; a context revision can reuse
context-independent symbolic terms. A provider replacement preserves its actual scheme and
maps explicitly, rather than relabelling outputs. One node evaluated under two inherited
environments remains two evaluation states.

Execution fit is credible through coarse native batches, prepared grammars/matchers, natural
source regions, factorized choices, indexed hydration and release of live native objects after
detachment. No per-kind task, per-term transaction or automatic refinement loop is needed.
HanLP's actual subword limits and grammar ambiguity still require population reconciliation
during implementation: honest unsupported labels alone cannot qualify ordinary required
full-book work. These choices apply H2/4/5/10/11/12/15/16/17/18/20/22/23/25 qualitatively.
No numerical speed or capacity claim follows.

## Judgments and acceptance limits

**Proposed judgments for the revised target.**

| Judgment/gate | Result and basis |
| --- | --- |
| A1 | Satisfied: family owners, semantic evaluator and downstream domain responsibilities are explicit |
| A2 | Satisfied by the revised target: typed native/formal evidence, choice sites and enforceable support govern operations |
| A3 | Satisfied: existing provider, release, task, publication and reader mechanisms compose without another lifecycle |
| A4 | Satisfied qualitatively for the declared route; full-book envelope and ambiguity qualification remain implementation obligations |
| G1–G3 | Satisfied by the revised single-authority model and native constraint boundary |
| G4–G5 | Satisfied: inference precedes publication; existing cancellation/fencing and explicit partial outcomes survive |
| G6 | Satisfied by explicit packing, transitive selections and node/environment determinants |
| G7–G8 | Satisfied: claims remain Proposed; selected native capabilities cover their stated responsibilities and residual application semantics are explicit |
| CI-G1 | Satisfied: provider schemes, coordinate spaces, proposals, unknowns and source disjunction remain distinct |
| CI-G2 | Satisfied by exact source/layer/choice closure through reads and detached export |
| CI-G3 | Satisfied at target level: independently authored semantic/source expectations remain outside production inputs |

FP-01–07 are satisfied within this proposed boundary. Implementation, provider efficacy, native
deployment, complete consumer cutover and assembled qualification remain unestablished.

**Rule impacts:** none requiring reversal. The revisions elaborate ADR-0081's typed fidelity
and witnessed-support obligations. TC-09 changes implementation ownership while preserving
source custody, protected publication and consolidation-only knowledge admission. Discovery
of an actual conflicting current rule requires explicit disposition before reliance.

Product/provider/database tests and benchmarks: **not_run**; static review only. Review
acceptance does not establish implementation acceptance, linguistic efficacy or enclosing
pipeline qualification.
