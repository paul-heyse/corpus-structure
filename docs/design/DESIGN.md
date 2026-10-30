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
The collection entry pages are unassessed; discovery/design-quality benefits remain Proposed.


**Evidence records — Implemented and Tested** (ADR-0010; `tests/evidence`, 2026-10-28). A finalized result of an investigation gets one
typed record in its evidence folder (`records/<id>.json`: question, informed items, method,
agents, hashed inputs and outputs, headline results, outcome, conclusion, consumers); revisions
supersede. `just evidence` derives the README indexes, a rebuildable DuckDB catalog with
per-folder views and report figures from queries; none of these is an authority, and records
retire with their folder (ADR-0001).

**Documentation publication** (ADR-0003). Focused architecture pages retain stable section IDs;
a moved live section leaves a relocation pointer. One resolver drives ADR references and the
generated section directory. Publication derives navigation and search from sources; it does not
prove implementation. [Publishing operations](../publishing.md) owns the commands.

> Decision: ADR-0001, ADR-0002, ADR-0003, ADR-0006, ADR-0007, ADR-0008, ADR-0010


Product binding decisions follow. Each is `### §Bn <decision stated as a sentence>` with a
committed anchor, a label and its `> Decision:` line, in the same commit as the ADR that decides
it. Changing one needs an ADR and a design/target review.

<a id="section-b1"></a>

### §B1 Qualified assertion occurrences and semantic facts have distinct identities

**Proposed · accepted target, 2026-10-29.** Source occurrences preserve independent evidence,
conditions, modality, polarity, attribution and typed values. Semantic facts group compatible
occurrences under a release-scoped meaning key; confidence/support do not erase occurrences.
Repetition and retry are distinct. D1 owns this contract. The selected pre-pivot runtime still
uses its frozen claim form until scheduled consumer migration.

> Decision: ADR-0024

<a id="section-b2"></a>

### §B2 Methods write observations; only consolidation writes knowledge, per run

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

### §B3 The agent tier works a recorded queue; the pipeline never calls it

**Proposed** (accepted, not yet built). Policies create `awaiting_agent` tasks; the session pulls
bounded packets and submits through MCP tools; runs wait at a barrier or finish with those items
unresolved; golden passes go through the same tools by Sonnet subagents
([D6](D6-orchestration-metrics-policies.md), [D8](D8-agent-and-query-interfaces.md)).

> Decision: ADR-0015

<a id="section-b4"></a>

### §B4 PostgreSQL 18 is the transactional authority for instances; the model is the authority for their structure

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

**Native test contract with partial implementation (2026-10-29; scoped verification owned by SP-I08).**
Fresh consumer databases clone a session-built frozen semantic deployment, with explicit
database ACL/default replay and equality checks. Actual restricted logins and commits remain.
Cold bootstrap and era-shaped forward upgrades still execute deployment from bare. One leased
test lifecycle owns cleanup without forced termination. CA-21 retains the reserved-name ownership
gap; [D3](D3-database.md) owns this boundary.

> Decision: ADR-0032

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

### §B6 Escalation is routed by versioned policies over measurements

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
