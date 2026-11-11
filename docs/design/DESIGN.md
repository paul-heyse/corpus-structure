# corpus-structure — design

**Current design guidance:** pair the [design principles](../design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md).
Apply relevant qualitative reasoning early to physical organization, interfaces, preparation,
assurance and lifecycle choices. Material open execution choices or revealed mismatches warrant
attention; settled reviews remain reusable. The companion introduces no checklist, cost model,
proof machinery or change to review cadence.

**This file plus `docs/design/sections/` is the architectural authority**; the
[architecture map](README.md) routes each responsibility to its owner. This file holds scope
(§1), the binding decisions (§2, §B1…) and durable deferrals (§13); focused owners hold the
rest. Labels distinguish implemented behavior from accepted targets: an accepted target is not an
implementation claim. Current ADRs say why and what was rejected ([index](../adr/README.md)); the
active plan in [plans](../plans/README.md) owns execution and the disposition of known defects.

**Changing a section.** Change a governed section in the same commit as the ADR that decides it
and keep its `> Decision: ADR-NNNN` line. Section IDs are never renumbered or reused: insert
`§3.2.1` rather than shifting `§3.3`, and a moved live section leaves a relocation pointer. Keep
sections current rather than appending history (ADR-0001). There is no line budget: the detail the
design needs comes before length. Column- and field-level contracts live in executable
declarations and their tests; they are not repeated here.

**Labels.** Every claim carries a principles §D label (`Proposed`, `Interface-checked`,
`Implemented`, `Tested`, `Measured`, `Formally established`). A section's label applies unless a
line says otherwise. `Interface-checked` means the named library surface was read at the locked
version (skill brief, probe or source at that version), not that our code uses it yet.

---

<a id="section-1"></a>

## §1 Scope

<a id="section-1-1"></a>

### §1.1 Objective

**Proposed.** Produce a structured, evidence-backed representation of the knowledge a set of
documents states: entities, statements and claims with qualifiers, conditions and spans, under a
declared domain schema, queryable by typed questions. The first corpus is the statistics corpus
(Siegrist's *Probability, Mathematics and Statistics*, first-pass chapters), used as calibration;
the target is any domain, eventually business documents and email, as a commercial product.

Consumers: the operator and downstream tools through typed queries and exports; Opus in the
Claude Code session through MCP tools, as the agent tier that fills gaps, adjudicates and writes
goldens; later, hosted services.

The pipeline improves incrementally: encoders and deterministic methods first, a local LLM, then
Opus; every intervention is recorded; goldens and guidelines evolve under the operator's
direction; measured reliability lets policies scale interventions back. The target design is
[D0–D9](README.md#the-design-set).

<a id="section-1-2"></a>

### §1.2 Out of scope for now

**Proposed.** Corpora other than statistics until phase 5; hosted LLM endpoints; multi-tenant
service; RDF publication; the methods D0 lists as deliberately left out until a measured gap
asks for them; per-item human verification of goldens (the operator steers through guidelines,
[D7 §8](D7-evaluation-goldens-outer-loop.md#8-the-operators-outer-loop)).

**Accepted method-development scope,2026-11-07.** The full Grinstead–Snell book,
physical pages 1–518, supplies the current shared benchmark. The WCE 120-page
results retain their original scope. Separate source populations, held-out
origins and group counts do not gate this exploratory benchmark. Progressive grounded structure
and granular failure/capture assessment are the objective; complete records are a stronger outcome.

> Decision: [ADR-0070](../adr/0070-full-book-method-development.md)

<a id="section-1-3"></a>

### §1.3 Generality check

**Proposed.** The core holds nothing statistics-specific. Anything designed in `core`, `schema`,
`consolidate`, `orchestrate`, `evaluate` or `serve` is checked against constructs statistics never
exercises (from the old repository's transfer fixtures, kept in reserve, D9 §7):

| Example | Construct |
|---|---|
| ORG-101 "Harbor Systems Ltd", distinct from ORG-202 despite a shared trading name | Multi-attribute identity (Splink), cannot-link |
| "ORG-101 owns P-17, valid 2026-01-01 to 2026-06-30, per ownership.html" | `valid_time` qualifier, attribution, evidence |
| A table cell "High flow · 300" with its header, unit, caption and Note P | Table segments, quantities with units and gauge qualifiers (kPa(g)), notes as conditions |
| An inspection duty with a three-part exception | Conditions with `or` and `not`, evaluable against facts |
| Email threads | `email_message`, `quoted_block` and `signature` segments; attribution to senders |

The design/target reviews use these as change scenarios.

<a id="section-2"></a>

## §2 Binding decisions

**Development process** (ADR-0001). The checkout holds a current working set: architecture owns
contracts and targets, current ADRs own reasons and open choices, the active plan owns execution
and scheduled finding disposition, STATUS the checkpoint. A reader never needs a supersession
chain or retired plan; retired records, reviews, plans and evidence are recovered from Git
([historical recovery](../README.md#historical-recovery)). Governing references must resolve,
historical `supersedes` entries need not, and ADR ids are never reused. Work happens on `main`;
compile checks and targeted tests are the loop, and `just test-all` (functional) follows once all
functional scope is implemented, with every non-functional check (`just hygiene`) beside it; the
agent fixes what fails. The root agent runs `just turn-end` (formatting, generators) at the end of a
turn that changed files (ADR-0001).

**Design review** (ADR-0002/0006). The repository owns core 3.3 of the design standard and declares
it in `docs/design_review/design_principles/standard.toml`. The seven foundations organize review
of responsibilities, contracts, composition, explicit domain models and scoped semantic
authority, constraints, local reasoning and physical execution fit. Requested and scheduled reviews assess whether an
adequate domain model governs behavior. Ordinary implementation does not initiate a separate
domain-model review; flow tracing is optional when it resolves a concrete question. Owned concepts
and operation contracts govern behavior; ordinary domain functions can suffice. A2 assesses both
model adequacy and authoritative behavior; an in-scope MUST gap cannot be waived for supported behavior.
A1–A4 judge architecture independently of correctness and domain-fidelity gates. The
corpus-structure binding maps §B decisions to the standard and owns review cadence and finding
disposition. Changing a §B decision needs an ADR and a design/target review. Acceptance,
implementation and verification remain distinct facts. FP-07/A4 require qualitative assessment
of a credible physical route for the functional workload, including relevant growth, skew, concurrency and failure. Compare
necessary versus repeated work, composed library/optimizer capabilities, locality, working sets,
reuse, assurance placement, publication/recovery scope and total runtime/operator machinery.
A bounded response or safe refusal alone does not establish workload fit. Explain material
tradeoffs in plain language. No numerical estimates, cost models, estimators,
runtime cost accounting, execution-planning machinery, instrumentation, formal cost proofs or
additional proof artifacts follow from this consideration; they need a separate concrete functional
or operational requirement. Quantitative performance/capacity claims still need measurements, and
semantic correctness obligations remain. No ordinary-implementation review follows.

**Agent workflow — Implemented** (ADR-0006/0007). [Shared role contracts](../../.agents/roles/README.md)
define six reusable worker responsibilities, while native Codex adapters own model settings
only; no role file restricts tools or sandbox, so the contracts alone bound each role's effects.
The coordinator remains accountable for design coherence,
integration and acceptance; workers exercise delegated judgment within accepted outcomes and
contracts. Shape contributions around useful results, shared decisions and readiness for the
requested result. Investigations can resolve open contracts; consumer preparation and working
integration need different prerequisites. Reconcile changes affecting other contributions or
semantic owners, and follow AGENTS.md for write isolation, publication and shared-resource rules.
Shared roles own task-specific context, concrete briefs and evidence-based escalation. Paired skills prepare and perform reviews, plan creation and
execution. Plan creation includes focused assessment of foundations and schedules necessary
improvements before dependent work. Existing plans own execution and scheduled finding disposition;
planning companions ordinarily remain conversational. Resource savings remain Proposed.
**Audit-led workflow — Implemented policy** (ADR-0007). Before a new diagnostic review of
production or broad system scope, the [diagnostic audit](../design_review/audit/README.md) is refreshed,
using prior findings and source changes to focus investigation. The operator selects solution
focus; methods and depth remain reviewer judgment. A requested recommendation audit publishes
[net changes](../design_review/reviews/audits/README.md) and integrates a newly attributed review
at its original path, preserving its input in Git. A completion audit reconstructs accepted scope
and corrects the same owning plan. Reviews own reasoning, plans own scheduled disposition; ordinary
implementation does not load the broad audit. Optional repo-agnostic library overviews and current
documentation replace active central library skills. These are deliberate boundaries, without
automatic per-slice audit gates or new agent roles.

Test-only diagnostic engagements use [the test audit](../design_review/test-audit/README.md)
and the [test-assessment companion](../design_review/design_principles/core/test-assessment.md).
The binding selects applicable accounts for mixed scope. Each retains its own baseline,
and findings one primary home; installing the process performs no audit.

**Library leverage — Implemented guidance** (ADR-0008). The
[framework](../library_leverage/README.md) separates codebase opportunity identification,
focused library applicability and comparative review of complete options. Each has a distinct
evergreen output location. Useful library types and additional output patterns persist after
current matches retire; all stages use base and output patterns together, and promotion into
base guidance is manual. Plans retain execution disposition and existing review cadence remains.
Optional library-led discovery owns contextual usage briefings and proposed research priorities.
It can start from a library family and repository objective before an opportunity is identified.
Discovery and design-quality benefits remain Proposed.

> Decision: ADR-0072

**Evidence records — Implemented and Tested** (ADR-0010; `tests/evidence`, 2026-10-28). A finalized result of an investigation gets one
typed record in its evidence folder (`records/<id>.json`: question, informed items, method,
agents, hashed inputs and outputs, headline results, outcome, conclusion, consumers); revisions
supersede. `just evidence` derives the README indexes, a rebuildable DuckDB catalog with
per-folder views and report figures from queries; none of these is an authority, and records
retire with their folder (ADR-0001).

**Documentation publication** (ADR-0071). Focused architecture pages retain stable section IDs;
a moved live section leaves a relocation pointer. One resolver drives ADR references and the
generated section directory. Publication derives navigation and search from sources; it does not
prove implementation. The docs workflow retains the checked artifact and deploys
it from eligible main builds to GitHub Pages. [Publishing operations](../publishing.md) owns the commands.

**CLI workflow and custody — Accepted target (2026-11-07).** Installed `ci` exposes routine
operations through owned recipes and application services. Invocation results have explicit
settlement and retention. Native deployment, activation and selection require explicit intent.
[D8 CLI](D8-agent-and-query-interfaces.md#4-cli) and [D9](D9-repository-and-phase0.md#3-conventions)
own the integration contract.

Safe operation observations remain within managed invocation custody: bounded owner-written
journals distinguish live prefixes from sealed authenticated replay, with scoped safe logging and
child transfer. Native settlement, purpose roles, effects and raw disclosure retain their owners.
[D8](D8-agent-and-query-interfaces.md#safe-operation-observation-custody) owns the interface detail;
the CLI plan owns implementation and qualification separately from the accepted decision.

> Decision: ADR-0001, ADR-0002, ADR-0071, ADR-0006, ADR-0007, ADR-0008, ADR-0010, ADR-0069, ADR-0079, ADR-0080


Product binding decisions follow. Each is `### §Bn <decision stated as a sentence>` with a
committed anchor, a label and its `> Decision:` line, in the same commit as the ADR that decides
it. Changing one needs an ADR and a design/target review.

<a id="section-b1"></a>

### Audit-closure contract qualification

**Accepted target; implementation and qualification Proposed (2026-11-03).**
The audit-closure correction qualifies §B1/§B2/§B3/§B5/§B6 with attributed source
attributes, complete versioned rule values, separate representative policies, executable policy
applicability, owned reader operations, compatible producer bindings and truthful trust strength.
Ordinary answers retain independent standing and scoped coverage; evidence/payload retrieval and
walk execution are bounded and pinned. Split effects retain actual immutable decision provenance.
Existing native fencing, per-task durability, original occurrences and historical reading remain.
The [audit-closure coordinator](../plans/audit-closure_2026-11-03.md) owns remaining work.

> Decision: [ADR-0054](../adr/0054-audit-closure-contracts.md)

### §B1 Qualified assertion occurrences and semantic facts have distinct identities

**Accepted target, Proposed until implemented · 2026-11-10.** Enriched-document views bind a
full exact published document and immutable analysis-layer pins. SourceViews are scoped
projections beneath the base. Source occurrences preserve original native/projection coordinates
independently of analysis identity; layer-local annotation/member/term/choice IDs are externally
qualified by their product pin. D1 owns distinct source containment, grouping, semantic operators,
analytical alternatives and family coverage. Exact text or matching endpoints do not merge them.

> Decision: [ADR-0081](../adr/0081-enriched-document-analysis-layers.md)

**Accepted target; implementation tracked separately,2026-11-06.** Witnessed components
retain exact operation questions and source bases. Independent component assessment and scoped
eligibility remain separate from private production and whole-report standing. WCE owns adoption;
statistics qualification uses domain-owned contracts, without an enterprise corpus prerequisite.
The operator-directed WCE04–WCE05 cutover uses current-only semantic contracts; affected historical
readers and legacy decision routes are removed. Insufficient derived evidence is regenerated from
authenticated sources rather than converted into invented witnesses.

> Decision: [ADR-0067](../adr/0067-witnessed-current-only-cutover.md)


**Implemented; bounded native/publication Tested, 2026-11-05.** Cross-source structural
products retain original source occurrence, typed report envelope, complete raw task result,
source-resolved public claim and admission witness as distinct identities. Numeric retrieval
spelling and display choices do not redefine the scoped public statement. Definition applicability,
qualified comparison and dossier assembly retain separate claims; member truth and scientific
truth are not implied by assembly support.

> Decision: [ADR-0065](../adr/0065-cross-source-structural-products.md)

**Implemented; bounded native and actual publication Tested,2026-11-05.** Local public claim
identity binds its event, physical occurrence and complete scoped semantic statement. Its
admission-witness identity separately binds exact producer/cut, policy and applicable assessment.
A curated-target denotation establishes neither a canonical entity nor scientific truth.

> Decision: [ADR-0064](../adr/0064-local-semantic-admission.md)

**Accepted target; implementation Proposed, 2026-11-05.** Independently addressable structural
contributions preserve source occurrence separately from type/role/link/attachment proposals.
A complete-record parent is not required. PCE-01/02 own compiled/native/read adoption.

> Decision: [ADR-0062](../adr/0062-progressive-contributions.md)


**Implemented; selected native124 controls Tested2026-11-04.** Source-reading field support
is reported through existing D5/D8 custody. Positive metadata facts and author polarity are not
scientific support/opposition. Broader proposition comparison remains explicitly unmodeled until
a released mapping defines identity, qualifications and opposition.

> Decision: [ADR-0059](../adr/0059-source-reading-support.md)


**Implemented; scoped contract controls Tested2026-11-04.** Native table/cell custody supplies
structural row location; quoted row labels are separate source content. Missing native header flags
cannot establish that an author label is absent. D1 and the statistics release own the exact role
contract; unchanged table+cell occurrence membership does not imply global row identity.

> Decision: [ADR-0058](../adr/0058-native-row-location.md)

**Accepted target, Proposed until implemented (2026-11-03).** M1 source evidence preserves
per-anchor selected-view or captured-recognition attribution, distinct text/provider precision and
versioned real-piece readings across permitted whitespace. Native enforcement and prepared context
composition adopt the same released meanings; old frames and native100 remain frozen.

> Decision: [ADR-0051](../adr/0051-m1-attributed-source-evidence.md)

**Accepted target, Proposed until implemented (2026-11-03).** M1 extends the released occurrence model with source-record identity, named field evidence sets
and common record membership across lowered assertions. Private candidate validation does not
establish admitted knowledge, source fidelity or scientific truth.

> Decision: [ADR-0049](../adr/0049-m1-qualified-source-records.md)

**Proposed · accepted target, 2026-10-29.** Source occurrences preserve independent evidence,
conditions, modality, polarity, attribution and typed values. Semantic facts group compatible
occurrences under a release-scoped meaning key; confidence/support do not erase occurrences.
Repetition and retry are distinct. D1 owns this contract. The selected pre-pivot runtime still
uses its frozen claim form until scheduled consumer migration.

> Decision: ADR-0024

<a id="section-b2"></a>


**Accepted target,2026-11-06.** Remaining WCE producers and consumers pivot to current
contracts; preserve source custody and regenerate insufficient derived data, with no historical
semantic decoder fallback.

> Decision: [ADR-0070](../adr/0070-full-book-method-development.md)

### §B2 Methods write observations; only consolidation writes knowledge, per run

**Accepted target, Proposed until implemented · 2026-11-10.** Characterization layer/view
publication provides immutable private analysis through protected task completion. It confers no
knowledge admission. A valid layer can retain actual failed/partial/unavailable family outcomes
and useful independent siblings; actual task failure keeps its native terminal meaning. D4/D6
own production and lifecycle; source-only composition is a real weaker method, not evidence that
later NLP producers or full-profile coverage exist.

> Decision: [ADR-0081](../adr/0081-enriched-document-analysis-layers.md)

**Accepted target; implementation tracked separately,2026-11-06.** Witnessed components
retain exact operation questions and source bases. Independent component assessment and scoped
eligibility remain separate from private production and whole-report standing. WCE owns adoption;
statistics qualification uses domain-owned contracts, without an enterprise corpus prerequisite.
The operator-directed WCE04–WCE05 cutover uses current-only semantic contracts; affected historical
readers and legacy decision routes are removed. Insufficient derived evidence is regenerated from
authenticated sources rather than converted into invented witnesses.

> Decision: [ADR-0067](../adr/0067-witnessed-current-only-cutover.md)


**Implemented; bounded native/publication Tested, 2026-11-05.** Original-project source guards
remain intact. Finite RUN-unit structural reports use the existing immutable task lifecycle;
independent multi-source assessments bind exact original pins. Supplemental structural assertions
publish through the common PublicationBatch/realization with exact current whole-statement
witnesses and selected-cut upstream semantic participants. Automatic model proposals remain
private unless their own exact policy evidence qualifies them.

> Decision: [ADR-0065](../adr/0065-cross-source-structural-products.md)

**Accepted target; implementation in qualification, 2026-11-05.** Local captured-source
assertions and independently assessed semantic assertions use common consolidation. A later
ordinary run can freeze protected grade dependencies and reuse the exact immutable assessed
producer origin. Completed results remain immutable. Deterministic extent checks, semantic
judgments, canonical identity and scientific truth retain distinct authority.

> Decision: [ADR-0064](../adr/0064-local-semantic-admission.md)

**Accepted target; implementation Proposed, 2026-11-05.** Typed local products remain private
until their declared publication policy admits them. Failed later assembly preserves earlier
sealed contributions without granting knowledge authority or weakening whole-record admission.

> Decision: [ADR-0062](../adr/0062-progressive-contributions.md)

**Accepted target, Proposed until implemented (2026-11-03).** M1 adds an explicit CPU extraction route producing private source observations and record
candidates. Existing policy/consolidation remains the sole knowledge publication owner; uncertain
interpretation remains upstream of finite rule closure.

> Decision: [ADR-0049](../adr/0049-m1-qualified-source-records.md)

**Accepted operation target (2026-10-29).** Bound operations retain source occurrences, typed
assessments and immutable effective-input cuts. Finite positive inference preserves exact
qualification and requires source-grounded proof authorization at protected publication.
Automated grading/adjudication does not require human input. Migration status belongs to SP-06/SP-07.

> Decision: ADR-0027

**Proposed** (accepted, not yet built). Every method, the agent included, writes append-only
observations; consolidation alone writes entities, claims and links, rebuilt per pass and
materialized per run, immutable once the run finishes; promotion picks the run queries read
([D5](D5-consolidation-identity-confidence.md), [D1 §10.2](D1-knowledge-representation.md)).

> Decision: ADR-0014

**Accepted target clarification (2026-10-29).** ADR-0024 preserves instance authority and
consolidation policy ownership while separating pure release preparation, protected publication
and later consumer adoption. SP-01 deploys no database or engine change.

> Decision: ADR-0024

<a id="section-b3"></a>

### §B3 Agents work the semantic queue through supervised or interactive MCP sessions

**Implemented, 2026-10-30; full SP-09/SP-10 qualification remains separately owned.** A supervisor
may invoke the configured model in a fresh run-bound stdio MCP session. PostgreSQL owns the
recorded release, tasks, leases, attempts and completion; provider exit does not imply semantic
success. Interactive sessions use the same bounded packets and protected proposal operations.
Source extraction has no reference access; independent automated authoring/grading uses evaluator
credentials. No human grading is required. Current semantic execution refuses the unimplemented
legacy wait barrier rather than implying that every old option is supported.
([D6](D6-orchestration-metrics-policies.md), [D7](D7-evaluation-goldens-outer-loop.md),
[D8](D8-agent-and-query-interfaces.md)).

> Decision: ADR-0034

<a id="section-b4"></a>

### §B4 PostgreSQL 18 is the transactional authority for instances; the model is the authority for their structure

**Accepted target, Proposed until implemented · 2026-11-10.** D3 extends generated physical
storage for canonical analysis products and indexed relationship projections. Native completion
checks exact source/input custody, payload/projection agreement and declared endpoint/term/choice
closure under existing run/task/attempt/holder fences before coherent visibility. D8's bounded
pin-native reads select before hydration; detached export streams a settled view independently
of whole-run completion, retaining original coverage and statuses.

> Decision: [ADR-0081](../adr/0081-enriched-document-analysis-layers.md)

**Implemented; scoped native and identity controls Tested,2026-11-05.** Semantic meaning and
executable provenance have distinct immutable owners. `sem.runtime_binding` archives exact
runtime inputs; each new run pins a same-release runtime identity. Native custody and deployed
operation/effect enforcement remain authoritative. Historical runs keep their producing provenance.

> Decision: [ADR-0063](../adr/0063-semantic-runtime-identity.md)

**Implemented development workflow,2026-11-04.** Agents use persistent corpus_structure_dev and
the operator's administrative authority on dedicated18/corpus. Native candidate authoring can
run transactionally on that working database; disposable storage is not a prerequisite. Normal
application purpose roles and semantic publication/evaluation authority remain explicit.

> Decision: [ADR-0056](../adr/0056-persistent-development-database.md)


**Accepted target, Proposed until implemented (2026-11-04).** M1 derives scoped source-reading
field assertions from effective family roles and applies a whole-record admission cap through
common consolidation. Native direct record/field/set support and exact public overlay retain
sealed candidate custody and private-product fences. Release-defined finite fitted instances
bind immutable run inputs and evaluator-authorized calibration, without reference rebinding.
Annotation and raw-extraction determinants refine reuse consistently; retained CPU products
feed separately configured reading resolution. Other methods retain the full-binding default. D1/D5/D6/D7 own the detailed target and M1 owns implementation evidence.

> Decision: [ADR-0060](../adr/0060-m1-reference-applicability.md)

**Accepted target, Proposed until implemented (2026-11-03).** Declared source-product ancestry
retains complete report schemas while excluding graph applicability/identity lowering. Native graph
membership/datatype and graph-range fences enforce that distinction; ordinary graph regex
constraints remain unsupported. Accepted record projections remain derived M1 publication work.

> Decision: [ADR-0050](../adr/0050-source-product-placement.md)

**Accepted unified-operation target, Proposed implementation (2026-11-02).** Model-derived Core and structured PostgreSQL products extend the existing native authoring/admission route. Protected database enforcement and restricted writers remain mandatory; versioned body profiles preserve frozen predecessors.

> Decision: [ADR-0047](../adr/0047-current-only-domain-runtime.md)

**Accepted PDF target; Proposed implementation (2026-10-31).** PostgreSQL retains original
PDF bytes, immutable native Docling content and separate conversion health. Application
contracts govern conversion-qualified occurrences, ordered relationships, source regions and
purposeful derived indexes/text views. Native document schema authority is scoped to Docling;
LinkML/trusted execution definitions govern application operations, dependencies, states and
cross-product/domain relationships. Shared Core metadata and forward native migrations realize
instance integrity; existing protected publication remains the only ordinary write authority.
Original bytes survive conversion failure, and derived hierarchy/corrections never mutate the
native conversion. [D3](D3-database.md#parsing-product-custody) owns the target realization.

**Accepted integrated target (2026-10-31).** Select one document contract after Docling/RapidOCR
and true Nemotron triple pass: Docling content with mandatory typed input lineage, correspondence,
selection and coverage. Governed replacement preserves original observations. PDF-scoped identity
and immutable direct-input relations connect raw recognition and document products; downstream
consumers do not independently merge providers. PDF-13–16 own implementation; provider success,
operational adoption and qualification do not follow from accepting the target.

**Confirmed retirement boundary (2026-10-31).** Historical HTML-derived outputs no longer require
reader/API or replay compatibility. Remove their active adapters, contracts and compatibility-only
gates after migrating maintained PDF users; preserve current PDF pinning, generic text/math kernels
and inert databases/frozen migration/evidence records. No destructive data cleanup is implied.

> Decision: ADR-0040

**Accepted relational streaming target (2026-11-01); implementation maturity is owned by the PDF coordinator.**
One logical Docling content graph plus mandatory companions is realized through lossless typed
records, ordered membership, qualified native addresses and bounded artifact parts. Docling owns
native content; the semantic release owns lowerings, identity and behavior; PostgreSQL owns
instance custody and enforcement. Private append/freeze/validation precedes atomic publication.
Logical identity and exact byte/serialization identities remain distinct; historical SHA-256
content_digest pins retain their original meaning. A named bounded fold cannot impersonate them.
The PDF coordinator owns deployed revision and tested scope; foundations alone do not establish
book-scale publication, complete streaming integration or adopted consumer qualification.

> Decision: ADR-0045

**Accepted segmented-byte identity (2026-11-01).** New artifact streams require independently
verified parts, lengths and canonical byte folds. Whole-stream serialization SHA is optional
export metadata; original/raw/historical digest custody is unchanged.

> Decision: ADR-0043

**Accepted structured-payload placement (2026-11-01).** The semantic release governs a page-scoped
OCR/candidate Arrow IPC profile, its logical identity and required SQL projections. The finite
frozen validator checks actual stored payloads and complete cross-field semantics; PostgreSQL
checks custody, relational invariants, exact bytes and matching validation/projection contracts
before publication. Other metadata retains native JSON Schema checks. Current-realization
rebuilds preserve compatible evidence without mandatory historical reader/layout support.
[D3](D3-database.md#native-pdf-metadata-validation) owns the mechanism and provisioning boundary.

> Decision: ADR-0045

**Retained HTML implementation boundary.**

The following source/layered guarantees describe the installed HTML route and its dated evidence,
not a constraint that forces PDF documents into HTML partitions or canonical-only identities.


**Accepted parsing target; PP-00–PP-04 source scope implemented and scoped Tested (2026-10-30).** PostgreSQL `bytea` owns
immutable original bytes once per source content identity, separately linked to document/acquisition
identity. Representations, partitions, structures, transformations and interpretations have
immutable build/product custody independent of full canonical rendition-content identity.
Protected publication and forward native migrations enforce declared custody and completeness;
[D3](D3-database.md#parsing-product-custody) owns layout and pinned readers. Complete original and
canonical partitions are required separately. Rooted `canonical_output` lineage is qualified
through admitted transformations/synthetic production; exact copying and repaired-node attribution
remain distinct. [Scoped execution evidence](../plans/parsing-pipeline_2026-10-30.md#pp0004-execution)
covers source capture, native storage, publication and readers, not the whole series.

**Accepted target; implementation in progress (2026-10-30).** Deferred parsing results are
immutable product layers with explicit root source-build and dependency custody. Weak lexical,
structure and syntax requests do not implicitly construct symbolic values. Existing protected
publication and archived read authority govern the layers; PP-05–PP-10 own implementation and
qualification. Method/output versions migrate with their consumers.

> Decision: ADR-0040


> Decision: ADR-0040

**Proposed accepted target (2026-10-30).** Analytical ownership and preparation contracts use existing release-scoped rows and immutable products; physical capture may be resident or detached spooled under one snapshot/custody contract.

> Decision: [ADR-0035](../adr/0035-model-governed-analysis.md)

**Accepted analytical target (2026-10-29).** Read operations share a PostgreSQL snapshot across
Core control reads and ADBC columnar reads. A DuckDB operation scope owns derived analytical
execution; publication remains protected PostgreSQL admission, including stale-analysis fencing.

> Decision: ADR-0026

**Implemented semantic persistence boundary (2026-10-29; package verification is scoped).**
The trusted physical LinkML module derives shared Core metadata. A separate frozen Alembic
history deploys the new schema and protected publication routines/grants on fresh databases.
The application authenticates as a restricted writer; publisher-owned staging, native checks
and a caller-owned SERIALIZABLE transaction establish atomic admission. Exact receipts retain
batch identity across retry and commit uncertainty. The regenerable-data asynchronous-commit
policy does not promise crash-durable acknowledgements. [D3](D3-database.md) owns the route and
the [pivot package](../plans/semantic-model-pivot/postgresql-and-publication.md) owns acceptance.

**Implemented relational execution realization (2026-10-29; qualification remains scoped).**
Fixed release-scoped operation, transition, edge and effect requirements feed stable protected
kernels; property-role and scientific-decision projections feed their real consumers. The shared
Core model and complete retained authoring route emit frozen forward products. [D3](D3-database.md#release-scoped-execution-projections)
owns the detailed compatibility and authority boundaries.

> Decision: ADR-0031, ADR-0033

**Native test contract implemented (2026-10-30; scoped verification owned by SP-I08).**
Fresh consumer databases clone a session-built frozen semantic deployment, with explicit
database ACL/default replay and equality checks. Actual restricted logins and commits remain.
Cold bootstrap and era-shaped forward upgrades still execute deployment from bare. One leased
test lifecycle owns acknowledged nonce/OID/owner cleanup without forced termination, including
reserved CLI initialization; [D3](D3-database.md) owns this boundary.

> Decision: ADR-0032

**Implemented, 2026-11-02; qualification is scoped at the test-architecture coordinator.**
Named default serving readers clone a sealed session-local populated source through that same
native lifecycle. Each consumer retains fresh committed isolation, policy replay and actual
purpose authentication; recipe/preparation mismatch refuses reuse. Varied and producer/lifecycle
cases retain independent preparation. This extends preparation without changing native ownership.

> Decision: ADR-0048

**Implemented; scoped Tested (2026-10-29).** The transitioned composed-model boundary now
uses finite trusted lifecycle/conditional guards and protected terminal effects. Completed output
is a relationship, enforced atomically with run completion; measurement rows derive from immutable
source results with source-position identity. Frozen revisions semantic_0023–0026 enforce exact
execution/native/physical compatibility, restricted privileges and authored-SQL admission before
construction/activation. Operational deployments retain their existing revision; the pivot coordinator owns their checkpoint. The
[completeness coordinator §10](../plans/semantic-model-pivot_2026-10-29.md#10-domain-model-completeness-integration)
owns receipts and the later SP-08–SP-10 boundary; this is not whole-series qualification.

**Tested** for the store in spike S6 (2026-10-28: DDL, trace rows, queries, BM25, halfvec and the
queue on smoke data); the split of authority, the generated relational projection and the
in-process engine are **Proposed** (accepted 2026-10-28; migration 0001, the pool and the engine not
yet built). One PostgreSQL 18 database holds every instance of knowledge, operations and
evaluation, so one transaction links a task, its observations and the claims they change, with
pgvector and BM25 text search in the same planner. The structure and meaning of those rows
(tables, closed sets, relationships, invariants, payload classes) are projections of the model
(§B5): relationships that queries join on or invariants constrain are relational, decision-relevant
scalars are columns, and other values are typed JSONB under the payload-schema registry. The
consolidation pool is a set of model-typed Arrow relations whose set-based steps run in an
in-process DuckDB engine with no persistent state, set-equal with a Python reference
implementation; identity and canonical forms stay in Python. DuckDB also serves analytics and
exports; neither it nor files hold authoritative data ([D3](D3-database.md)).

> Decision: ADR-0021

**Accepted target clarification (2026-10-29).** ADR-0024 preserves instance authority and
consolidation policy ownership while separating pure release preparation, protected publication
and later consumer adoption. SP-01 deploys no database or engine change.

> Decision: ADR-0024

<a id="section-b5"></a>

### §B5 One LinkML semantic release governs interpretation and generated representations

**Accepted target, Proposed until implemented · 2026-11-10.** The trusted characterization
module is explicitly acquired and archived with release inputs. D2's typed declarations govern
occurrences, membership/roles, terms, choices, coverage and their operation contracts. Generated
boundaries, native mechanical support checks and read projections consume that same authority;
neither native validation nor a reader supplies an independent linguistic policy.

> Decision: [ADR-0081](../adr/0081-enriched-document-analysis-layers.md)

**Implemented; scoped Tested, 2026-11-10; the DMC coordinator owns acceptance.** Attributed source interpretations remain private
released contributions with independent evidence, review selection and vocabulary pins.
Correction presentation and raw/managed evidence custody remain explicit.
The completion repairs provide attributed before-side update surveys, whole-report bounds and
structured native wrapper meanings. The [DMC coordinator](../plans/domain-data-model_2026-11-10.md#completion-repair-acceptance)
owns qualification and the assembled review disposition; these reads confer no selection authority.

> Decision: [ADR-0077](../adr/0077-attributed-interpretations-and-correction-custody.md)

**Implemented; scoped Tested, 2026-11-10; DMC-06 owns the acceptance receipt.** Qualified terminology source projections
and descriptive metadata retain source custody without becoming another enforcement authority.

> Decision: [ADR-0076](../adr/0076-qualified-terminology-products.md)

**Implemented; scoped Tested, 2026-11-10; DMC-01/02 own scoped acceptance.** Immutable inspection artifacts
retain source contributors while existing definitions, boundaries and operations own executable
meaning. D2 owns preparation/archive custody and D8 owns the shared CLI/MCP read.

> Decision: [ADR-0075](../adr/0075-immutable-contract-inspection.md)

**Implemented; scoped functional/native controls Tested,2026-11-09.** Checked recipe occurrences
own value/membership/ordering explanations; archived unavailable detail remains unavailable.
Model-change SQL diagnostics and native operation views consume retained source/frozen facts;
failed diagnostics confer no effect authority. D8 owns presentation and the PTD series owns delivery.

> Decision: [ADR-0074](../adr/0074-attributed-projection-explanations.md)

**Implemented; selected generated/native controls Tested, 2026-11-09.** Selected generated calls,
Core columns and companion results reuse explicit semantic correspondence and existing nominal
anchors. Type-only correspondence preserves local physical constraints. D2 §3.4 owns the declaration
contract; the PostgreSQL typed-domain series owns implementation and verification.

> Decision: [ADR-0073](../adr/0073-generated-type-correspondence.md)

**Accepted target; implementation tracked separately,2026-11-06.** Witnessed components
retain exact operation questions and source bases. Independent component assessment and scoped
eligibility remain separate from private production and whole-report standing. WCE owns adoption;
statistics qualification uses domain-owned contracts, without an enterprise corpus prerequisite.
The operator-directed WCE04–WCE05 cutover uses current-only semantic contracts; affected historical
readers and legacy decision routes are removed. Insufficient derived evidence is regenerated from
authenticated sources rather than converted into invented witnesses.

> Decision: [ADR-0067](../adr/0067-witnessed-current-only-cutover.md)


**Implemented; bounded native/consumer controls Tested, 2026-11-05.** Finite released
structural variants, original-source references, group frames and operation-specific public
policies govern producer completion and common atomic publication. The captured review carries
current operation contracts and each referenced original source release's archived declarations;
readers do not reinterpret old source bytes under only the new registry. Operational envelope
repairs retain semantic release identity while exact runtime archives remain separately bound.

> Decision: [ADR-0065](../adr/0065-cross-source-structural-products.md)

**Implemented; bounded native and actual publication Tested,2026-11-05.** Released local
eligibility policies, typed assertion rows and native guards extend the same generated model
and PublicationBatch. Protected assessment preparation returns selected admissible statements,
without exporting raw reference labels to producers. Publication-only grade bindings remain
immutable run provenance while compatible source-producer reuse excludes that setting.

> Decision: [ADR-0064](../adr/0064-local-semantic-admission.md)

**Implemented; scoped native and identity controls Tested,2026-11-05.** Semantic identity
includes data/model/output contracts, declared behavior versions and parsing grammar/model assets.
Incidental executable-source changes have a separate runtime identity. A budget-only repair must
preserve semantic release/data identity; execution, caches and task reuse retain exact runtime
compatibility. The one-time compiler17/execution27 transition preserves historical archives.

> Decision: [ADR-0063](../adr/0063-semantic-runtime-identity.md)

**Accepted target; implementation Proposed, 2026-11-05.** The progressive milestone uses
operation/population capability claims and independent source-first/output-first judgments.
Whole-record grades remain stronger scoped claims. The Sol authoring profile, frozen source
frames, origin partitions and protected evaluator survive; whole-reading labels cannot become
local correctness. PCE-03 owns new protocol integration and its actual evidence.

> Decision: [ADR-0062](../adr/0062-progressive-contributions.md)


**Accepted target, Implemented with native qualification open (2026-11-04).** The statistics
release separates native table/cell row location from the meaning-changing quoted `row_label`.
Its source-reading support ledger reports the existing selected field facts and their custody;
scientific proposition comparison remains explicitly unmodeled without a released projection.
The M1 coordinator owns current verification and remaining adoption evidence.

> Decision: [ADR-0058](../adr/0058-native-row-location.md), [ADR-0059](../adr/0059-source-reading-support.md)

**Accepted target, Proposed until implemented (2026-11-04).** M1 derives scoped source-reading
field assertions from effective family roles and applies a whole-record admission cap through
common consolidation. Native direct record/field/set support and exact public overlay retain
sealed candidate custody and private-product fences. Release-defined finite fitted instances
bind immutable run inputs and evaluator-authorized calibration, without reference rebinding.
Annotation and raw-extraction determinants refine reuse consistently; retained CPU products
feed separately configured reading resolution. Other methods retain the full-binding default. D1/D5/D6/D7 own the detailed target and M1 owns implementation evidence.

> Decision: [ADR-0060](../adr/0060-m1-reference-applicability.md)

**Implemented; bounded Tested (2026-11-04).** M1 native pack-v2 maps explicitly declared
exact source fragments through the existing Text/TextSequence policy and uses latent assertion
grouping. Native formatter confidence order cannot define source order; fragment ordering,
custody, states and cues remain checked. Source policy6 routes whole-block contexts while
retaining coverage and bounded inputs.147focused controls and actual native interface settlement
pass. The changed physical frontend still requires fresh affected predictions/fitting/calibration;
original references remain immutable and these controls establish no extraction quality.

> Decision: [ADR-0061](../adr/0061-m1-native-record-frontends.md)

**Accepted target, Proposed until implemented (2026-11-03).** M1 source evidence preserves
per-anchor selected-view or captured-recognition attribution, distinct text/provider precision and
versioned real-piece readings across permitted whitespace. Native enforcement and prepared context
composition adopt the same released meanings; old frames and native100 remain frozen.

> Decision: [ADR-0051](../adr/0051-m1-attributed-source-evidence.md)

**Accepted target, Proposed until implemented (2026-11-03).** Declared source-product ancestry
retains complete report schemas while excluding graph applicability/identity lowering. Native graph
membership/datatype and graph-range fences enforce that distinction; ordinary graph regex
constraints remain unsupported. Accepted record projections remain derived M1 publication work.

> Decision: [ADR-0050](../adr/0050-source-product-placement.md)

**Accepted target, Proposed until implemented (2026-11-03).** M1 field roles/states, typed values, evidence membership and interpretation contracts extend
the same effective release and generated/native boundaries. Unsupported enforcement refuses
admission; an opaque record payload does not establish public field-addressable support.

> Decision: [ADR-0049](../adr/0049-m1-qualified-source-records.md)

**Accepted unified-operation target, Proposed implementation (2026-11-02).** Resolved semantic contracts govern comparison roles, typed operation binds/results, relationship endpoints and qualified implementation compatibility. Generated structural representations share those inputs; specialized algorithms remain admitted implementations.

> Decision: [ADR-0047](../adr/0047-current-only-domain-runtime.md)

**Accepted PDF target; Proposed implementation (2026-10-31).** One admitted application semantic
release governs interpretation-changing behavior and cross-product relationships. It binds the
versioned native Docling schema rather than re-authoring it. New ingestion is PDF-only through
StandardPdfPipeline/RapidOCR plus Nemotron3.5 true triple-pass interpretation and governed integrated
selection. The content graph preserves formula/table recognition and heading hierarchy. Sections and
subsections remain intact; no section chunking is planned. PDF geometry, recognized LaTeX and
derived text spans are distinct qualified representations; recognition is not exact original
TeX recovery or mathematical truth. Rich native items/relations reach actual packet/frame,
method, consolidation, placement, query/export and evaluator contracts through versioned migration.

Immutable custody, pinned producing products, independent grading and protected publication
survive. Weak source demands do not construct stronger mathematical results. Formula recognition
health and inline/table coverage remain explicit; failed enrichment cannot imply successful
LaTeX or complete absence. [D1](D1-knowledge-representation.md#311-representation-qualified-source-products)
owns the concepts and D2–D8 their realization. The
[PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) owns implementation and qualification;
accepted target does not establish conversion, deployment or performance/fidelity benefits.

> Decision: ADR-0040

**Accepted metadata realization (2026-11-01).** Native metadata validation consumes contracts
derived from the same application release. Selected page interiors use model-derived Arrow IPC
and frozen runtime semantic validation; other JSON families retain the native extension. Neither
encoding nor evaluator is another schema authority. Envelope locators, diagnostic references,
logical identity and validation placement are model-governed contracts.

> Decision: ADR-0045

**Retained HTML implementation boundary.**

The following implemented clauses apply to the installed HTML route until its active consumers
are replaced; existing historical evidence and identities retain their meanings.


**Implemented; scoped Tested parsing target (2026-10-30).** Trusted LinkML/execution
definitions govern representation-qualified source ranges, occurrence relationships, mappings,
coverage and discrete parsing operations. Existing canonical evidence anchors and full rendition
identity remain unchanged. Library algorithms implement finite admitted contracts without a
general workflow interpreter. Retain html5lib HTML5 semantics; version M09/M11/M13 boundary/output
changes with complete producer and consumer migration. Computation lifecycle, semantic outcomes
and completeness remain distinct, with independent reference preparation and grading unchanged.
[D1](D1-knowledge-representation.md#311-representation-qualified-source-products) owns the concepts;
[D2](D2-schema-and-guidelines.md#parsing-contract-compilation), [D4](D4-method-catalog.md#parsing-operations-and-versioned-method-adoption)
and D5–D8 own their compilation and consumption. Immutable source/text/interpretation/assessment
layers, explicit weak/strong demands, scoped source declarations, actual scope coverage and
protected native consumers are implemented. The [parsing coordinator](../plans/parsing-pipeline_2026-10-30.md#remaining-scope-execution)
owns required-union qualification and fresh operational adoption; these claims do not imply
universal grammar support or exact attribution of every repaired HTML node.

> Decision: ADR-0040

**Implemented (2026-10-30).** One admitted interpretation authority governs distinct qualified physical frontends and model-bound context, demand, result and dependency projections. Source declarations are prepared independently of downstream resolution, and each native stage consumes its admitted capability contract.

> Decision: [ADR-0035](../adr/0035-model-governed-analysis.md)

**Implemented with scoped Tested evidence (2026-10-29).** Independent-reference grades use separate protected
LinkML reference/pass/frame/evaluation definitions; completed knowledge output retains its existing
meaning. A project selects an immutable completed result separately from its active interpretation,
with the same generation CAS. Queries, explanations and qualified columnar exports bind that
result's archived release and revision. Purpose-specific authentication shares one declared storage
endpoint. Regeneration uses actual sources and a fresh restricted automated MCP extractor, with
archived-run resumption and no reference inputs. Existing databases and running MCP processes
are not migrated in place. [Pivot coordinator §12](../plans/semantic-model-pivot_2026-10-29.md#12-sp-08sp-10-implementation-checkpoint-2026-10-29)
owns native/provider acceptance and limitations. Statistics/transfer journeys completed on
semantic_0030; a fresh frame journey exposed a native guard that does not consume the explicit
release statement binding. Its correction and assembled qualification remain open.

> Decision: ADR-0030, ADR-0031

**Accepted target refinement (2026-10-29).** Typed evidence-backed identity exclusions constrain
existing key/label resolution and protected publication. Exclusions retain their scoped source and
input lineage; mandatory-key conflicts refuse atomically. D5 owns the detailed contract.

> Decision: ADR-0029

**Accepted operation target (2026-10-29).** Producers and domain operations consume one pinned
release and resolved dependencies. Semantic scope, normalized rule declarations and operation
boundaries are derived products; runtime settings cannot rebind an existing operation.

> Decision: ADR-0027

**Implemented; scoped Tested (2026-10-29).** Trusted LinkML execution contracts and immutable
domain releases remain distinct authorities in one compatible operation binding. Compiler 8
archives finite conditional rules, native guard bindings, typed outcomes and named projections;
unsupported required semantics refuse. Existing frozen dataclasses use cattrs only for strict
representation conversion, with LinkML/Pydantic retaining semantic/boundary ownership. Current
source, decision/inference, graph, query and analytical consumers use those contracts. An analysis
scope can own many borrowed and detached results simultaneously; borrowing depends on a live
open owner, while detached values survive closure. Concrete supported profiles and library
choices are retained in the [realization plan](../plans/semantic-model-pivot/domain-model-realization.md#7-implemented-mechanisms-2026-10-29).

**Accepted analytical target (2026-10-29).** Release-derived projections bind source selections,
Arrow types and output adapters. Analytical profiles explicitly govern decimal rounding (default
38 digits, 12 fractional places, HALF_EVEN); original values and canonical identities remain intact.
Runtime resource settings do not change semantic policy.

> Decision: ADR-0026

**Implemented release persistence boundary (2026-10-29; package verification is scoped).**
Exact source/dependency bytes, explicit ontology-source selection and generated products are
archived immutably. Offline reload compares the recorded compiler stack and products. Activation
compares parent plus generation, performs required native/authored-SQL admission, and leaves
existing realization bindings intact. Unsupported required native semantics refuse activation;
new admitted class/property definitions change registry rows without physical DDL.

Effect requirements have authored identity and version, resolved against owned bounded
implementation support. Exact immutable projections preserve operation/transition context;
unknown or incompatible requirements refuse. Supported finite variation becomes additional
release rows, while archived read compatibility remains separate from new write admission.

> Decision: ADR-0031, ADR-0033

**Proposed · accepted target, 2026-10-29.** Local LinkML and pinned external ontology dependencies
prepare an immutable binding of types, scoped constraints, identities and operations. Dynamic
domain definitions become registry data over a stable relational core. SQLAlchemy metadata,
Pydantic boundaries, RDF/SHACL and Arrow schemas are derived, not independently editable meanings.
Preparation is explicit and separate from persistence/activation and transactional publication.
The currently selected installed projection remains until its dependent packages migrate.

> Decision: ADR-0024

<a id="section-b6"></a>

**Accepted target, Proposed until native qualification (2026-11-03).** M1 source-record references
freeze source-ready membership independently of predictions in the existing protected reference
store. A distinct released protocol preserves empty/missing denominators, immutable credible
origin partitions and guideline/source closure. Actual fitting authentication exposes only
adjudicated feature-fit references; extraction and held-out labels remain isolated. Legacy
Agent reference operations retain their completed-result contract and historical meaning.

> Decision: [ADR-0052](../adr/0052-m1-independent-record-references.md)

**Accepted target, Proposed until exercised (2026-11-03).** M1 source-record reference authoring
and adjudication use GPT-6.1 Sol with existing pass/grade authorities; no new independence
infrastructure is required. Legacy grades and non-M1 profiles retain their meanings. Quality
qualification concerns a frozen held-out source cut, using exhaustive source references and
census or exact finite-population sampling bounds; unseen-origin performance is unestablished.

> Decision: [ADR-0062](../adr/0062-progressive-contributions.md)


**Accepted method-development target,2026-11-07.** One shared Grinstead–Snell
full-book corpus supplies development, fitting, debugging, regression and repeated assessment. Single-origin
in-sample event fitting is permitted; independent source labels and numerical validity remain.
Separate held-out/calibration populations are later generalization work, not readiness gates.

> Decision: [ADR-0070](../adr/0070-full-book-method-development.md)

### §B6 Escalation is routed by versioned policies over measurements

**Accepted target, Proposed until implemented (2026-11-03).** M1 selects a separate CPU extraction allowlist and run-owned resident admission policy,
retaining parent task fencing, cancellation and database custody. A qualified NONDEFAULT release
and adoption/rollback procedure precede any later reviewed operational default switch.

> Decision: [ADR-0049](../adr/0049-m1-qualified-source-records.md)

**Interface-checked** in spike S4 (2026-10-28: the rule syntax compiles and refuses errors at compile
time); accepted, routing not yet built. Ordered policy chains compiled to
rule-engine `Chain`s decide routing; every task records the rule and trigger values; conditional
methods enter only through gap proposals and experiments ([D6 §7](D6-orchestration-metrics-policies.md)).

> Decision: ADR-0018

<a id="section-13"></a>

## §13 Deferred

**Accepted deferrals.** Capabilities outside the current architecture on purpose; each returns
by ADR when a named consumer needs it. The active plan owns the scheduling triggers. None yet.

### Semantic execution closure

**Accepted target, 2026-10-29; implementation partial.** Effective immutable contracts govern actual
validation purposes, operations and projections. Archive-backed reads preserve supported historical
boundaries; full verification remains mandatory for admission. Restricted admission owns complete
protected archive/finalization/activation operations; maintenance credentials stay administrative.
Native integrity supports shape and accepted-value placement; required patterns and occurrence/context
placement refuse explicitly. The owning [execution package](../plans/semantic-model-pivot/model-execution-closure.md)
records implementation and qualification independently. Existing publication and reference guarantees remain.

> Decision: ADR-0031
