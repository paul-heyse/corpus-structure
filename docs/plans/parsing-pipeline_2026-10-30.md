# Domain-model-driven parsing pipeline

**Status:** In progress; PP-00 decisions and PP-02 bounded investigation delivered;
PP-01/03/04 implementation underway. **Created:** 2026-10-30.
**Basis:** [functional review](../functional_reviews/parsing-pipeline_2026-10-30.md) and
[target model](../functional_reviews/parsing-pipeline_2026-10-30_target-model.md), consumed at
`b3a8313`. Current production baseline remains `599d479`; intervening commits are review/audit
documentation. This coordinator owns PP-00–PP-10 and scheduled parsing-review O01–O07 disposition.

## 1. Purpose and boundaries

Deliver complete categorized decomposition of original and canonical document representations,
connected structures/provenance, model-governed parsing operations, native library adapters and
demand-driven interpretation used by real consumers. Retain html5lib's HTML5 tree-construction
semantics through lxml. Original files are never rewritten to match a repaired DOM.

LinkML and trusted execution definitions govern shapes, relations, behavior, states, dependencies
and effects. PostgreSQL holds immutable products and admitted release contracts; SQLAlchemy,
Pydantic, JSON Schema, RDF/SHACL and graph/analytical layouts derive from that authority. Generic
algorithms remain qualified library implementations behind discrete domain contracts.

This series adds capability rather than restarting the semantic pivot or production-efficiency
plans. Existing execution/qualification and F01 disposition stay at their current owners. Audit
accounts, grading policy, human review workflows and testing architecture are outside scope.
Independent automated evaluation remains isolated from extraction. Authoring approval does not
authorize implementation, deployment, deletion, or a claimed parser speedup.

## 2. Foundation and accepted planning envelopes

Useful foundations exist: generated SourceProfile, recursive Segment validation, complete TeX
lexical scanning, shared TextLayout, PreparedMathInput, release-derived OperationContract and
RelationshipDefinition, fixed Core metadata and protected publication. Extend these rather than
add a second workflow engine, global preparation service or independently authored graph schema.

The missing distinctions are complete original/canonical component coverage, durable transformation
links, parsing behavior beneath coarse operations, and consumer demands separated from eager
interpretation. A following-space flag is not a complete whitespace partition. A DOM path or
diagnostic line is not an exact original byte extent. A SymPy object is not an occurrence identity.

| Planning decision | Operator decision, 2026-10-30 | Implementation route |
|---|---|---|
| PP-RC01: representation-qualified coordinates | Original markup/text plus canonical decomposition explicitly selected; preserve canonical evidence coordinates while adding typed original/decoded/expanded spaces. | PP-00 reconciles D1's canonical-only wording; PP-01 defines coordinate types and PP-03 implements mappings. |
| PP-RC02: method boundary/output changes | Explicitly selected “Redesign boundaries”: M09/M11/M13 may change with versioned contracts and complete consumer migration. | PP-00 records affected D4/D5/D6 decisions; PP-06 and PP-10 migrate demands/results without weakening evidence. |
| HTML5 semantics | Explicitly retain html5lib, already used through lxml. | PP-02 investigates complementary source-location support; PP-03 retains the structural semantics. |

These are accepted planning envelopes, not accepted ADR amendments or qualified algorithms.
PP-00 identifies current successor decisions before altering a clause (ADR-0012/0019 are historical
inputs, not automatically current authorities). Additional binding-rule changes require explicit
confirmation; record and isolate dependent work rather than assume the review approved them.
Keep source/token identity, full rendition content identity, archived meanings and protected
publication unless a separately confirmed change explicitly replaces them.

## 3. Documents and packages

Package state and opportunity disposition are owned here. Supporting documents explain target,
mechanisms and acceptance rather than maintain a second mutable execution queue.

| Package | Owner / delivered capability | Required readiness | State |
|---|---|---|---|
| <a id="PP-00"></a>PP-00 | [Model](parsing-pipeline/model-contracts-and-storage.md#PP-00): decisions and enduring owners | Confirmed envelopes; current decision clauses | Implemented: ADR-0036 and D1–D8 owners; algorithm claims remain Proposed |
| <a id="PP-01"></a>PP-01 | [Model](parsing-pipeline/model-contracts-and-storage.md#PP-01): shared semantic contracts, states, ports and runtime enforcement | Relevant PP-00 decisions; native capability evidence | In progress: source-product contract slice; operation/interpretation integration remains |
| <a id="PP-02"></a>PP-02 | [HTML](parsing-pipeline/source-decomposition-and-html.md#PP-02): source-location feasibility and selected integration | PP-01 agreed coordinate/capability slice, not complete schema deployment | Bounded investigation delivered: native instrumentation selected; full producer qualification remains PP-03 |
| <a id="PP-03"></a>PP-03 | [HTML](parsing-pipeline/source-decomposition-and-html.md#PP-03): original/HTML/canonical decomposition and mappings | PP-02 qualified route; enforced relevant PP-01 contracts | In progress: native producer and canonical contribution capture |
| <a id="PP-04"></a>PP-04 | [Model/storage](parsing-pipeline/model-contracts-and-storage.md#PP-04): durable products, native integrity and readers | PP-01 meanings; PP-02 selected mapping requirements before final physical layout | In progress: native custody, relational products and protected readers |
| <a id="PP-05"></a>PP-05 | [Text/math](parsing-pipeline/text-and-mathematical-interpretation.md#PP-05): prose/TeX structure and macro custody | Relevant PP-01 contracts and PP-03 source products | Planned |
| <a id="PP-06"></a>PP-06 | [Text/math](parsing-pipeline/text-and-mathematical-interpretation.md#PP-06): lazy interpretation and migrated method contracts | PP-05 context/products; PP-04 for durable use; PP-08 ownership before publication | Planned |
| <a id="PP-07"></a>PP-07 | [Views](parsing-pipeline/extraction-and-relational-views.md#PP-07): source queries, graph/metadata/placement capabilities | PP-01/04 and the concrete PP-03/05/06 products each view consumes | Planned |
| <a id="PP-08"></a>PP-08 | [Runtime](parsing-pipeline/runtime-and-publication.md#PP-08): scope-bound preparation/workers/cancellation | Agreed PP-01 ownership; existing algorithms suffice for early work | Planned |
| <a id="PP-09"></a>PP-09 | [Publication](parsing-pipeline/runtime-and-publication.md#PP-09): coherent build publication and pinned read selection | PP-04; concrete producer contracts; PP-08 lifetimes | Planned |
| <a id="PP-10"></a>PP-10 | [Adoption](parsing-pipeline/adoption-and-acceptance.md#PP-10): complete migration, operational adoption and qualification | All selected functional scope integrated; PP-09 active | Planned |

The initial execution route is PP-00 plus the PP-01 coordinate/capability agreement, then PP-02.
Do not elaborate or deploy an exact-provenance implementation around an unsettled mechanism.
PP-01 enforcement, PP-04 design and PP-08 can progress independently where their input contracts
are settled. Production publication joins the producer, storage and runtime branches. Document
order is not a global barrier; shared model/compiler/native files still need one integrated writer.

## 4. Complete review coverage and disposition

IDs below are scoped to the [parsing review](../functional_reviews/parsing-pipeline_2026-10-30.md).
The mathematical review's same-numbered O-items are separate references, not merged identities.

| Item | Component / correction and value | Disposition and dependencies | Closure check |
|---|---|---|---|
| O01 | Source/HTML/model: complete partitions and explicit mapping/custody | Open; PP-01–05/09 | Every declared representation covered; exact/synthetic/unavailable mapping remains truthful and queryable. |
| O02 | Model/ports: owned parsing semantics and actual native consumers | Open; PP-00/01 plus all producers | New convention changes its authoritative definition and supported adapter, not repeated private classifiers. |
| O03 | Storage/views: independent edge/occurrence identity and useful layouts | Open; PP-01/04/07 | Parallel edges, order, isolates, shared nodes and relation-specific cycles survive read/analysis. |
| O04 | Preparation/math: demand-driven products and complete dependency keys | Open; PP-05/06/08 | Decomposition-only request performs no hidden interpretation; stronger consumers receive their required meaning. |
| O05 | Extraction: reusable text/markup, metadata and explainable placement | Open; PP-03/05/07 | Selected capabilities have real consumers and native mechanisms; optional candidates get explicit decisions/triggers. |
| O06 | Model/validation: one authority and complementary enforcement | Open; PP-01/04/09 | Independent invalid inputs fail at owned boundaries; no projection or schema silently becomes another policy owner. |
| O07 | Runtime: bounded useful execution and coherent failure | Open; PP-08/09/10 | Prepared state stays within valid lifetime; cancellation and retry preserve custody and publication. |

Target-model §§1–2 map to PP-00/01/03/04; §3 ports/demand/lifecycle to PP-01/05/06/08/09;
§4 native realizations to PP-02/03/05/06/07/08; §5 compatibility and consumers to PP-04/09/10;
§6 qualification questions to PP-02/04/06/07. Review scenario coverage belongs to PP-10 and
local package checks. Full guide candidates, including rejected defaults, remain explicit in
their owning designs; mere catalog presence creates no implementation obligation.

## 5. Open decisions and conditional capabilities

| Decision | Owner and required outcome | Dependent work / trigger |
|---|---|---|
| Exact HTML origin propagation | PP-02 selects a maintainable native/composed route with independent source cases; failure retains a named unresolved target, not a relabelled partial success. | PP-03 exact mapping and final PP-04 mapping layout. |
| Relational versus compact partition layout | PP-04 compares actual inspection/trace/edge-query needs and native integrity, then fixes layout before DDL. | Persistent readers/publication; no token-per-task requirement. |
| Early declarations and method demand | PP-05/06 establish non-circular authority and migrate actual M09/M11/M13 promises. | Lazy interpretation and correct source bindings. |
| Native frontend changes | PP-02/05/06 select only supported contracts: pylatexenc structural-only demand, Tokenizers replacing lexical/alignment work, direct forests/useful deterministic subset. | Evidence of a useful responsibility; no duplicate mandatory pass or automatic Earley rewrite. |
| Metadata/article and placement extensions | PP-07 selects bounded per-syntax/purpose capabilities or records rationale and a concrete revisit trigger. | Actual attributed extraction/query consumers; never source-custody substitutes. |
| Graph/ORM/compiled numerical views | PP-07/06 compare concrete questions against direct rows/native objects; conditional adoption only. | Required algorithm/navigation/repeated numerical workload, not library availability. |
| Memory zones/threading alternatives | PP-08 verifies lifetime and Python/library support before selecting. | Actual retained-memory or concurrency need; no 3.15-only assumptions. |

Mandatory decomposition/connected-model obligations cannot be deferred simply because a candidate
fails. Conditional library choices can be declined while implementing the same required capability
through a better supported route. No unmeasured latency or capacity claim completes an opportunity.

## 6. Completion and current state

Completion requires actual producers, enforcement, source/query consumers, protected persistence
and retained reads—not only model declarations or adapters. PP-10 separates functional scope,
qualification and any benefit measurements. Targeted checks run at coherent package endpoints;
assembled `just test-all` and applicable hygiene wait for all selected functional work. Existing
valid type/test evidence is not invalidated by lint-only maintenance.

**Current state:** execution of PP-00–PP-04 is authorized. ADR-0036 adds representation-qualified
coordinates and PostgreSQL original-byte custody while preserving existing canonical evidence,
rendition identity and grading. The [PP-02 investigation](../design_review/evidence/2026-10-30_parsing-source-provenance/README.md)
selects narrow instrumentation of pinned html5lib/lxml; nine cases retain native trees and
diagnostics and demonstrate positive cursor, attribute, mutation, buffered-text and decoder seams.
Its finalized record is partial: it establishes feasibility, not complete source provenance.
PP-03 must compose and qualify the actual producer before complete mapping claims are accepted.
Existing operational databases, earlier qualification and audit premises remain unchanged.
