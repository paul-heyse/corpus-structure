# Design review: one domain model, its derived forms, and execution in the production package

Formal design/target review, 2026-11-18. Supporting documents:
[cache-design.md](unified-domain-model-and-execution/cache-design.md) (the cache system, recommendation R09) and
[dispositions.md](unified-domain-model-and-execution/dispositions.md) (one disposition per consumed audit finding). Audit publication consumed: `90467bde0`.

**Revised recommendations · 2026-11-18.** The recommendations of this review were revised by an
independent recommendation audit on 2026-11-18, from input revision `b4eb74f67`, on the
operator's concern that the target should represent the pipeline's intentional flexibility and
optionality rather than govern it away. The revised judgments (chiefly R02, §3.2, R03, R05, R07,
R13, the new R15 and R16, finding F05 and rule impacts RC01, RC04, RC05, RC12 and RC14) are the
auditor's; the first reviewer did not author or endorse them. The companion
[audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md](audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md)
explains every change and its evidence; the original text is recoverable from Git at
`b4eb74f67`.

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | The production package `python/corpus-structure/src/corpus_structure/`, its model declarations (`model/`, packs), its generators, and the scripts that provision and deploy it, at commit `d78c98765` (frozen snapshot; committed tree, no dirty state) |
| Standard | Core principles, template and efficient-architecture heuristics 3.3 / 1.0; code-intelligence profile 1.4; corpus-structure binding (from `docs/design_review/design_principles/standard.toml`) |
| Tier and purpose | Design; target |
| Focus (operator, 2026-11-18) | Combined. Principles: a unified domain data model with scoped semantic authority (FP-04, A2); execution fit, meaning efficient and fast execution (FP-07, A4); application code kept away from writing or managing SQL text. Libraries as hypotheses: the data-model family (LinkML and relatives, SQLAlchemy, Alembic, pydantic, pyarrow, jsonschema, pglast, SQLGlot, valuesets) on equal footing, with unification allowed to come from connecting existing declarations; DuckDB 2.0 case by case; cachetools 8.0 given prioritized treatment as a cache *design* |
| Reviewer and date | Independent design reviewer (wrote neither the audit, the code nor earlier reviews), 2026-11-18. Recommendations revised by an independent recommendation auditor, 2026-11-18, on the operator's flexibility concern (see the attribution above) |
| Maturity and outcome | Design stage. The review should let the operator plan a separate series: which facts each authority owns and how consumers obtain them, an identity and cache design, the remaining-SQL conversion order, and the place of DuckDB |
| Supported scope and workload | Book-scale document processing through declared data operations, many operations per run; repeated focused reads from a long-lived MCP server (one process, tool calls on worker threads) and from the `ci` command line (one process per command and per page); model changes previewed, replayed and deployed; one operator, several coding agents, one host |
| Baseline | `d78c98765`. Audit revision consumed: the broad audit as refreshed on 2026-11-18 at that source (publication `90467bde0`), with the independent challenger's corrections of the same date ([independent challenge](../evidence/2026-11-18_production-review-inputs/challenge.md)) folded in. The coordinator records the publication commit |
| Excluded | Test code (owned by the test review of 2026-11-17; seams this design touches are named in one line each); the declared-data-operations plan's PE findings (read as current design, not re-owned); Chandra OCR (operator direction) |
| Method and coverage | Static reading. Read in full: the brief, the audit pages, the seven contributor reports, ADR-0131, DESIGN §2 and §B4/§B5 heads, ADR-0124 and ADR-0125 decisions. Inspected in source at the decisive lines: the native capture and its digest (`semantic/data_operation_storage.py:40–140, 695–815, 1095–1135, 1535–1562`), `semantic/metadata.py`, `schema/physical.py:130–200`, `semantic/prepare.py:340–375, 585–625, 950–990, 1015–1035`, `semantic/data_operation_admission.py:270–360`, `semantic/data_operation_identity.py:340–420`, `semantic/python_operation_sources.py` (outline and the slicer), `semantic/python_module_projection.py`, `semantic/file_custody.py`, `_query_custody.py`, `semantic/data_operation_wire.py:40–70`, `semantic/data_operation_read_index.py`, the DuckDB connection sites, `semantic/analytical_kernels.py:15–65`, `semantic/alembic_privileges.py:20–40`, `semantic/target_installation.py:345–356`, `semantic/support_trust_native.py:85–95`. Three bounded read-only helpers mapped (a) the hand-written PL/pgSQL residue, (b) whether validity families are derivable from compiled fields, (c) the cache and holder inventory; their results were checked at the lines this review relies on. Not read: generator bodies for equivalence; `schema/rulelang.py`; `semantic/ontology.py` beyond its use; `schema/stage_b.py`; migration revision bodies; `cli/` beyond the paging entry; `domains/` (not in the snapshot) |
| Evidence labels | Source facts: **Interface-checked by source inspection, 2026-11-18**. Every remedy: **Proposed**. Library facts: **documented**, **observed in installed source**, or **probed on synthetic data** (each says which). Nothing is Tested or Measured; no speedup is claimed. The audit's additions carry the same labels; its LinkML facts are observed in installed linkml and linkml-runtime 1.12.1 source, and the `domains/` packs it cites were read from commit `d78c98765` with `git show` |

## 2. The assessment in brief

The system's intent is a highly structured representation of documents produced by declared data
operations, with one explicit model from which storage, wire shapes, programs, validity,
authorization and analysis derive, and with work keyed, scoped and invalidated by what that model
declares.

Its core realizes that intent well and must be preserved. One effective operation model is
compiled per release from two authoring routes (ADR-0092), with tracked origins and refusal of
conflicting owners. The semantic request identity is built from the recipe, content-addressed
inputs and implementation slices and excludes the release and the runtime, so results survive a
new release (`semantic/binding_admission_native.py:213`). Typed native programs take relations and
columns from compiled metadata and refuse raw SQL text (`semantic/native_program.py:126–131`).
Generated bytes are kept in custody and deployment imports no generator. File and query custody
make a process refuse instead of silently mixing code.

The pipeline is also deliberately exploratory. Its objective is progressive grounded structure,
with complete records as a stronger outcome (`docs/design/DESIGN.md:62–66`, ADR-0070); useful
partial contributions, competing alternatives, unknowns and unsupported proposals are kept and
represented explicitly (ADR-0062, ADR-0024, ADR-0077; for example `MissingReason`,
`CoverageOutcome` and `UnresolvedBinding` in `model/semantic/core.yaml`, private and alternative
proposals in `model/semantic/data-operation-rich-proposals.yaml`). The target design must keep
that latitude and represent it, in the declared space of behaviours as well as in content. The
constraints this review proposes act on two layers only: the internal consistency of the declared
space of behaviours (a name must have a definition, a dispatch must have a handler) and system
integrity (authorization, guards, provenance, custody). They do not constrain the knowledge the
pipeline discovers, and where a behavioural declaration is not yet known the target says so
explicitly instead of forcing a classification.

Four structural causes explain the problems, and they are connected rather than one:

1. **Governing facts have no declared home.** Which validity family an operation belongs to,
   what a support edge means, which relations a guard covers, which roles exist and who may
   execute what are hand lists in Python and SQL, and an omission fails open
   ([DA-070](../audit/semantic-model-and-authority.md#da-070),
   [DA-071](../audit/semantic-model-and-authority.md#da-071),
   [DA-074](../audit/native-integrity.md#da-074)). Not every absence is an omission: some
   operations deliberately belong to no family. The defect is that the model cannot tell the
   designed state from the forgotten one, and that the forgotten one is treated permissively.
   Several facts that *are* declared are not read
   ([DA-086](../audit/semantic-model-and-authority.md#da-086)), and one intended distinction,
   whether a vocabulary may be extended by packs, is declared only in the earlier model that is
   due to retire (F05).
2. **There is no single compiled model object to read from.** Each consumer composes its own
   LinkML view; physical constraints sit in JSON strings; the effective operation model and the
   LinkML views are not one object generators read together
   ([DA-085](../audit/semantic-model-and-authority.md#da-085), narrowed by the challenger).
3. **Identity answers "which code" by hand or by everything.** One digest over every captured
   generator module and six library versions stands for "the kernel that validated this"; hand
   file lists stand for the code of PDF lowering and of served reads; release and preview
   identities hash whole trees ([DA-068](../audit/execution-fit.md#da-068),
   [DA-069](../audit/execution-fit.md#da-069), [DA-076](../audit/served-claims.md#da-076),
   [DA-082](../audit/execution-fit.md#da-082)). Coarse keys discard valid work; narrow keys
   let stale work through.
4. **Derived artifacts have no holder, and programs become text before their facts are
   recorded.** The native program capture is regenerated on the execution path at every
   admission-side call ([DA-083](../audit/execution-fit.md#da-083)), and the program set is
   listed by hand in several places, then handled as text that is concatenated, patched and
   re-parsed ([DA-081](../audit/semantic-model-and-authority.md#da-081), which now also
   carries the former DA-087).

Because the conversion to model-owned PostgreSQL is still open (ADR-0131 `:40–41, :51`; the DDO
coordinator lists native admission, privileges and scientific routines as remaining work), the
most consequential near-term point is an **ordering**: the remaining hand-written PostgreSQL holds
exactly the family and role lists of cause 1, so converting it before those facts have a declared
home would transcribe the lists a second time.

**Decision: Revise.** A2 is violated for supported behavior (an unlisted operation's family
premises are silently skipped, and the model cannot distinguish "no family check applies" from
"not yet classified"), A4 is violated (generation on the execution path, invalidation
far broader than its premise, no cross-process reuse for the command line), and gates G1, G2,
G3, G6, G7 and G8 fail in supported scope. The enclosing architecture needs revision around a
preserved core: the request identity, the typed program compiler, custody, and PostgreSQL's
authority over execution, locks and roles all stay.

## 3. The target design

This section states the target as one account. Section 4 gives the arguments, alternatives and
library mechanisms behind each part.

### 3.1 Authorities and the compiled centre

The target has five kinds of authority and nothing else that is authored:

1. **The LinkML released model** for domain shapes, vocabularies (domain and operational), each
   declaring whether it is closed, pack-extensible or open with known members (R15), physical
   declarations under a typed annotation profile, projections, and the schema of operation
   declarations and of the custom catalogs.
2. **Operation declarations as instance data**, through the two routes ADR-0092 accepts:
   implementation-owned `__data_operation__` literals beside their callables (about 62 modules)
   and declaration-owned model protocols. The Python literals stay where they are; what changes is
   that their grammar and vocabularies are declared in LinkML and checked against that
   declaration, instead of by a hand validator. Declarations that may not be known when an
   operation is first written (its validity family above all) are optional, with a declared
   meaning for their absence (R16).
3. **The native protocol** (JSON Schema draft-7) as a peer authority for wire encodings LinkML
   cannot express, the task lifecycle and the native operation ABI and purposes. It already feeds
   physical value sets through `ph:values_from`, a working cross-formalism derivation.
4. **Typed Python registries** for code-shaped facts: the native program declarations (name,
   schema, signature, language and volatility, purposes, callees, owning family) and the
   generated-output registry. These are authorities because programs and outputs are code
   artifacts, not domain data.
5. **Derived code identity**, computed from declared entry points, for "which code determines
   this artifact". It is not authored at all; it replaces every hand-kept file list.

Everything else is derived. The centre is not one object but three held ones, each identified by
its inputs:

- a **compiled model** per model-sources identity (the captured closure of LinkML schemas,
  protocol and catalogs), composed once by one composer and exposing lazily derived projections:
  merged `SchemaView`, physical and read SQLAlchemy `MetaData`, wire validators, expanded value
  sets, the type resolution for field kinds, Arrow schemas, the role and grant matrix, the
  support-edge traversal table and the operation-declaration validator;
- the **effective operation model** per release, as today, compiled from the compiled model plus
  the operation declarations;
- a **program set** per compiled model and generator code, holding program declarations,
  rendered bytes and identities.

The second, older model (`model/core.yaml`, `system.yaml`, `revisions.yaml` and what is generated
from them) retires after its live consumers move to released-model types.

### 3.2 Declared homes, explicit openness and safe defaults

Every governing fact has **one declared home**, and every dispatch over it is generated from the
declared members with no hidden default. What the declaration must say depends on the layer it
governs:

- **Integrity memberships are closed and complete.** Roles and purposes are LinkML vocabularies
  (`Role` with membership and login properties as member annotations; `Purpose` with its roles);
  table read roles and frontier-guard classification (`guarded` or `exempt`) are declared in the
  physical profile, each with a declared default per schema and per-relation overrides, so a new
  relation is safe without extra ceremony and no default lives in code; execute grants come from
  each program declaration's purposes; shared-stream triggers are selected by the already declared
  `ph:immutability: pending-content`; support-edge kinds form a closed set and an unrecognised
  support reference refuses; task states are read from the protocol lifecycle by every program
  that tests them.
- **Internal consistency is checked.** A named validity family must name its validator program
  unless the family is declared provisional; generation refuses a dangling name; completion
  dispatches on the lowered family instead of every guard selecting itself by an id list; a
  program's callees must be declared programs (R04).
- **Operation classifications are three-state, not total.** An operation's `validity_family` is
  optional and may name several families. Named families mean their validators run, in
  conjunction. An explicit `none` is a positive claim that only generic validity applies (outcome,
  revocation, support propagation). Absence, or an explicit `undetermined`, means "not yet
  classified": the operation compiles and runs, preparation reports a non-refusing diagnostic, and
  validity applies a **conservative premise check** that over-invalidates rather than
  under-invalidates (R16). The lowered column is an enum-checked set whose empty and undetermined
  states are distinct.
- **Vocabularies declare their openness** (R15): closed (programs may dispatch on it), pack-extensible
  (members are added per release by packs), or open with known members (any value is accepted;
  only known members carry meaning that consumers may test). Members may be marked provisional.
  `Profile`, `KindUniverse`, `Form`, `SupportEdgeKind`, `Purpose`, `Role` and the task lifecycle are
  closed, as they are today in code; the operation `ownership` description is open with known
  members (today it is free text with sixteen values, and consumers test only `immutable`); the
  free-text `preparation` and `cancellation` descriptions stay unconstrained.
- **Refusal is reserved** for internal inconsistency and omissions in the integrity layer. Where a
  behavioural declaration is undetermined, the stated consequence applies, and the operator decides
  whether some promotion boundary (default-release activation, knowledge publication) should
  refuse it (RC14).

None of these constraints acts on the knowledge content the pipeline discovers. Content keeps its
explicit states for partial, missing, unknown, competing and unsupported results, and a constraint
on selected values never prevents recording what a source says (ADR-0024).

### 3.3 Identity layered by purpose

- **Program identity**: the digest of one program's rendered bytes. **Kernel identity**: the digest
  over the sorted program names and identities that are installed. Generator source and library
  versions are *provenance*, recorded in custody, and key only the generation cache.
- **Validator identity** per validity family, and for the conservative validator that unclassified
  operations receive (R16): the digest over the identities of that family's validator programs and the
  programs they call. An operation in several families carries each family's identity. Receipts record it; replay is gated on it and its
  success is recorded.
- **Read-closure identity** for native reads; a native operation's declared behavior is its own
  program closure's identity, not the whole kernel.
- **Derived code identity** for Python artifacts (PDF lowering, served reads, opaque operation
  boundaries, generators): the static first-party import closure from declared entry modules,
  each module digested by its parsed syntax (comments and layout do not count), plus the versions
  of the distributions the closure actually imports. Function-level slices are used where the
  existing slicer resolves them without unknowns.
- The **release id** covers generated artifacts and the model capture, not generator source.
- The semantic request identity, the cut identity and the per-operation fingerprints stay as
  they are.

### 3.4 The cache system

Six in-process tiers and two disk tiers, keyed by those identities, coordinated with cachetools
8.0.1 `condition` single-flight (or a future-based single-flight where failures must be shared),
owned by one small registry module, with the command line crossing processes through
content-addressed files for generated program sets and continuation pages. The execution path no
longer generates anything. Full design: [cache-design.md](unified-domain-model-and-execution/cache-design.md).

### 3.5 SQL out of application code

PostgreSQL keeps execution, locks and roles. Application code does not write or maintain SQL text:
product logic is typed programs reading declared facts; independent controls stay hand-written but
take generated expectations as data arguments instead of spliced text; SQLite scratch stores use
SQLAlchemy Core tables; DuckDB use stays on the relational API with model-derived input schemas.
Frozen migrations and submitted read-only SQL remain exceptions.

### 3.6 Analytical placement

PostgreSQL keeps everything bound to its authority (validity, support walks, authorization,
paging, ranking). DuckDB keeps the three uses where set operations, spill and external sort pay
for themselves, gains certification folds over Arrow replay files, and loses its two uncalled
kernels. Python keeps small object-graph work and numerics. Change impact stops re-encoding
support semantics and consumes the authority's explanation.

### 3.7 Carried assurance

Established results are recorded once and carried while their premises hold: compiled-model
validation per model identity, release-content proof per release and kernel, binding facts from
admitted definition rows, validator reconfirmation per receipt and validator identity.

## 4. Corrective arguments

Each recommendation names its intended behavior, the alternatives considered and why they lose,
the library mechanisms it relies on, and a challenge case.

<a id="r01"></a>

### R01 — One composer and a held compiled model (Q2; DA-085, part of DA-083)

**Diagnosis.** Three near-identical closure routines (`semantic/prepare.py:350–373`,
`semantic/native_call_sources.py:95–117`, `semantic/projection_analysis_products.py:85–107`), a
separate physical closure (`schema/physical.py:166–197`) and further single-purpose views
(`semantic/companion_projection.py:552` from a disk path; `semantic/rule_views.py:402`;
`semantic/conditional_rules.py:178`; `semantic/ontology.py:159, 260, 626`;
`semantic/source_value_native.py:56`). `semantic/metadata.py:32–50` compiles two `MetaData`
projections at import in every importing process; `native_protocol_sources` compiles the physical
model again when not handed metadata (`semantic/data_operation_storage.py:123–136`).

**Target behavior.** One composer turns a model-sources capture into a `CompiledModel` (merged and
induced view, with the project's single `expand_enum` applied to value sets). Projections are
derived on first use and held on the immutable object. The object is held in cache tier T1 by
its model-sources identity, so a candidate and the running model coexist and a changed YAML
source yields a new entry instead of a restart (rule impact RC09). `semantic/metadata.py`'s globals
become accessors.

**Alternatives.** Keeping per-consumer composition loses: every new consumer adds a closure and
cross-view facts have no shared object, which is one reason membership facts fell back to Python
lists. (The value-set expansion kept is the released model's `semantic/ontology.py:328`; the
earlier model's `schema/model.py:333` carries the pack-extensibility rule and retires with R13
once R15 has carried that rule forward.) A single eager module global (today's `metadata.py`) loses: every command pays for it,
candidate and running models cannot coexist, and a model edit needs a restart. A materialized
derived schema file (`SchemaView.materialize_derived_schema`) as the one artifact is a useful disk
form later but leaves each consumer composing projections. The challenger notes that separate
closures partly serve custody (each artifact's identity covers its closure); in the target each
projection still has its own sub-identity (the physical sources id stays), so custody granularity
is kept without separate composition.

**Library mechanisms.** linkml-runtime `SchemaView(schema, importmap=...)`, `imports_closure()`,
`merge_imports()` (observed in installed source by the library contributor); the project's
`expand_enum`, needed because `induced_enum` and the JSON Schema and Pydantic generators do not
expand `inherits`, `include` or `minus` (probed on synthetic schemas by the library contributor,
[data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F6, F7); the project's `schema/relational.py` as the `MetaData` compiler (LinkML's
SQL generators read only three annotations and know no PostgreSQL schemas, checks, triggers or
grants, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F10, so they are not adopted); cachetools `cached` with `condition` for the
holder ([cache-design.md §4 T1](unified-domain-model-and-execution/cache-design.md#t1--compiled-model)).

**Challenge case.** A preview compiles a candidate model while the MCP server serves the running
one: both entries coexist under different identities; nothing pinned to the running model moves.
A model edit that leaves bytes identical produces no new entry.

<a id="r02"></a>

### R02 — Declare the governing vocabularies and classifications, with their openness (Q1, Q3; DA-070, DA-073, DA-074, DA-086)

**Diagnosis.** The validity family of 27 operations in seven families is a Python tuple rendered
as a `CASE` with no `ELSE` (`semantic/data_operation_compiler_native.py:468–520`); dispatch is a
second tuple with `else_=True` (`semantic/data_validity_native.py:272–288`); the column is an
optional string (`model/semantic/data-operation-physical.yaml:88`). Both lists already existed in
the deleted SQL; the conversion transcribed both. The helper's extraction of all 27 literals found
no compiled field that identifies a family: `profile` is `derivation` for 25 of them, `ownership`
does not separate families, and several operations with family-like ids are deliberately outside
every family. **Family is an authored choice**, so a declared field is needed; connecting an
existing declaration is not available here. The plan defines the lowered column as null "when no
per-kind validator applies" (`docs/plans/declared-data-operations/products-and-support.md:422–423`),
so "outside every family" is a designed state; the defect is that it shares its representation with
a forgotten entry, and that the forgotten entry is treated permissively.

**What is intentionally open here, and what is not.** The declared space of operations is meant to
grow by trying things: an operation may be written before anyone knows which native premises its
results depend on, may later turn out to need two families' checks, and may sit in a release that
includes only some groups. The current grammar already closes its field names, profile, forms and
kind universe (`semantic/data_operation_compilation.py:85, 104–140, 341–348, 1068–1073, 1491–1493`)
and leaves `ownership`, `preparation` and `cancellation` as free text (`:1559–1566`). The target
keeps those closures, keeps those descriptions open, and represents the not-yet-known family
explicitly instead of either refusing it or treating it permissively.

**Target behavior.** A LinkML schema for the Python authoring route's declaration grammar
(`DataOperationDeclaration`) and its vocabularies, each declaring its openness (R15): `Profile`,
`KindUniverse`, `Form`, `ValidityFamily`, `SupportEdgeKind`, `Purpose`, `Role` closed; `Ownership`
open with known members (the members consumers test, today `immutable`, carry declared meaning;
other values remain descriptive and are reported, not refused). Operation literals stay in Python
(ADR-0092's route); the compiler validates each literal against the declaration class with
closed-world validation of field names (as today), and records a warning for recommended but
absent declarations. `_PROFILES`, `_KIND_UNIVERSES` and the hand grammar validator
(`semantic/data_operation_compilation.py:85–188, 330–345`) retire. The compiled dataclasses keep
`Literal` fields for the closed vocabularies and check them against the enum members at import, the
closed-set pattern `semantic/source_value_native.py:55–66` already uses; the open `ownership` stays
a string.

The validity family follows R16: `validity_family` is an optional set of `ValidityFamily` members;
`none` is an explicit claim that only generic validity applies; absence (or `undetermined`) means
"not yet classified", compiles with a non-refusing diagnostic, and receives conservative validity.
Each `ValidityFamily` member names its validator program in a structured annotation, or carries
`status: provisional` while its validator is unwritten (its members are then treated as
undetermined). Dispatch, completion guards and the contextual and completion id lists are generated
from these declarations; a non-provisional member without a validator refuses at generation.

Release composition becomes "the closure of requested operations, mapped to source collections"
(DA-073). The source collection of an operation is derived by static extraction from the captured
collection that includes its literal (`semantic/python_operation_sources.py`), and an
`acquired_by` field is declared only to override that derivation. The manifest names requested
operations or families, so a release that includes only some operations remains the ordinary case.

**Where connecting existing declarations is the lighter route** (no new specification): shared-stream
trigger membership from `ph:immutability: pending-content` (`model/semantic/physical.yaml:1757,
1776`, already in `relation.info`, `schema/relational.py:492`); task-state tests from the protocol
lifecycle (`model/semantic/data-operation-native.yaml:5–14`, already read by the task guard,
`semantic/data_operation_protocol.py:116–160`); the four field-kind type maps from the type
resolution the physical compiler already performs on LinkML type `uri` and `ph:sql_type`
(`model/semantic/physical.yaml:33–36`; `schema/relational.py:79–89, 437–440`); the data-operation
value codec's tags from the LinkML observations vocabulary, as the SourceValue codec does; the
operation dependency graph from the compiled `selected-dependencies` projection
(`semantic/data_operation_model.py:713–725`); companion grouping columns from `cp:role`
annotations.

**The contextual per-operation contract.** `semantic/contextual_admission_native.py:23–50` restates
entry point, profile, forms and preparation that the effective model holds. The challenger notes
it acts as an independent pin when compared with the admitted definition. In the target it is kept
only as a pin between distinct inputs: generated from the declaration captured when the kernel is
authored, compared with the admitted release's definition. If kernel and release are generated from
the same input the comparison is circular and retires.

**Alternatives.** Deriving the family from existing fields is refuted by the extraction; whether it
is derivable from declared input roles (an operation that consumes a trust-bearing cut or a
linguistic premise) was not examined and would make the field an override. Annotations on schema
elements are wrong for operations, which are instances, not schema elements
([data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) A.2). A pydantic-authored metamodel is lighter for the structural grammar alone
and is an acceptable variant if the operator prefers it; it loses on the vocabularies, which SQL
reads through families and edge kinds, so those should be LinkML enums either way. A **required
total classification** with an explicit `none` and refusal of absence (this review's first round)
removes the fail-open state but makes every new operation decide its validity semantics before it
can compile, conflates "not applicable" with "not yet decided" in the other direction, and forbids
an operation in two families; it is not selected. Positive-only `in_subset` membership was rejected
in the first round because it does not fail closed; with the conservative default it becomes safe
where it is convenient.

**Library mechanisms.** LinkML enums with `permissible_values`, whose annotations take structured
values (annotation values are `AnyValue` and load as Python lists or dicts through `SchemaView`,
observed in installed linkml-runtime 1.12.1 by the library contributor, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F1);
permissible values also carry `status` and `deprecated` through `common_metadata`, so a provisional
member needs no custom annotation (observed in the installed 1.12.1 metamodel,
`linkml_runtime/linkml_model/model/schema/meta.yaml`, `permissible_value` and `common_metadata`);
validation of instance data with `linkml.validator.Validator(schema,
validation_plugins=[JsonschemaValidationPlugin(closed=True), RecommendedSlotsPlugin()])`, compiled once per schema and held in
T1 (documented and observed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) §D); `recommended: true` slots are reported by
`RecommendedSlotsPlugin` with `Severity.WARN`, not as errors (observed in installed source,
`linkml/validator/plugins/recommended_slots_plugin.py`); the JSON Schema plugin also enforces LinkML
`rules` while the Pydantic plugin does not (probed, F8). An open vocabulary uses a slot range of
`any_of` the enum and `string`, since the 1.12.1 metamodel has no openness flag on enums (observed).
Limits: annotations are untyped by default and `instantiates` validation is not enforced in 1.12.1
(F5); cross-record checks are a compiler pass, not a stock plugin.

**Challenge cases.** An operation that genuinely has no family validator declares `none`; it is no
longer indistinguishable from a forgotten one. A new operation whose validity semantics nobody has
worked out yet declares nothing: it compiles, runs and produces results, its derivations are
re-validated conservatively, and preparation lists it as unclassified. An operation that needs two
families' checks lists both. A renamed family member refuses at generation until its validator
program is named or the member is marked provisional.

<a id="r03"></a>

### R03 — A typed physical profile (DA-074, DA-085)

**Target behavior.** Physical annotations take structured values instead of JSON strings
(`ph:foreign_keys`, `ph:checks`, `ph:indexes`; decoded today at `schema/relational.py:297,
548–563`), typed by profile classes (`PhysicalRelation`, `PhysicalColumn`, `ForeignKey`, `Check`,
`Index`) written as ordinary LinkML classes, and checked once per compiled model by validating each
element's annotation dictionary as an instance of its profile class. The integrity
classifications (frontier guard; read roles) are declared for every relation in a guarded schema
through a **declared schema-level default** (guarded schemas default to `guarded`; each schema
declares its default read roles) with per-relation overrides (`exempt`; explicit read roles). A
relation therefore always has a declared classification, absence at the relation level means the
schema's declared default rather than a code default, and a forgotten exemption fails safe (an
over-guarded write refuses visibly). These are system relations: domain packs add classes and
properties as registry rows without physical DDL (`docs/design/DESIGN.md:1208–1222`), so trying a
new record, product or relation kind in a pack touches none of this profile.

**Alternatives.** Keeping JSON strings works but keeps the constraints invisible to LinkML tooling
and checkable only by custom code. `in_subset` for guard membership has no declared default and
leaves an unlisted relation unguarded. A required per-relation slot (the first-round proposal) is
equally safe but adds ceremony to every new native relation for no further protection.

**Library mechanisms and limits.** Structured annotation values (F1); validation through
`Validator` with a closed JSON Schema plugin; class annotations are not inherited and `slot_usage`
replaces rather than merges inherited slot annotations (probed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F2, F3), so the
reader resolves inheritance by walking `class_ancestors`. About fifty lines of glue
([data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) A.3, inference).

<a id="r04"></a>

### R04 — A typed program registry, carried from generation to installation (DA-081 including the former DA-087)

**Diagnosis.** The program set is held in several hand lists that must agree: `native_protocol_sources`
(`semantic/data_operation_storage.py:139–567`), the concatenation tuple in `native_sql` (37 named
artifacts plus two appended, `:753–812`), `capture_native_authoring_inputs`
(`semantic/native_products.py:131–153`), the installation table (`semantic/target_installation.py:209–231`)
and a provider order (`:302–314`). The required-set check refuses missing or duplicated artifacts
but accepts extras, and it already omits six artifacts that `native_sql` concatenates (challenger
§4), so a missing one surfaces as a `KeyError` rather than a classified refusal. After rendering,
facts the program objects held are recovered from text: grants assigned by matching names in a
re-parsed kernel (`:1873–1914`), the inventory re-parsed (`semantic/native_inventory.py:83–158`),
entry points renamed by a parse-and-reprint pass (`:715–748`), scratch DDL made by string
replacement (`semantic/native_authoring.py:293–313`).

**Target behavior.** Each generator registers program declarations: name, schema, signature (from
the call binding where one exists), language, volatility and security, purposes, callee names and
owning family. The registry is the one list. Generation renders each program once; its identity is
the digest of its bytes. Order is a topological sort over declared callees, refusing a callee that
no program declares; this also produces the provider order for SQL-language bodies, which bind
their callees when created. Installation consumes per-program text with a known name and signature,
so nothing re-parses a concatenated script to find functions. Grants are generated from purposes.
The wire wrapper and implementation names are generated from one declaration. Scratch tables are
produced from compiled `Table` objects. A descriptor program, generated last, carries the program,
kernel and validator identities as literals; guards call it instead of having a digest spliced into
their bodies. The facade outputs join a self-checking generated-output registry of the
`schema/generate.py:540–578` kind, retargeted to the released model.

**Typed forms to add.** The helper established that the compiler can already express trigger
functions (`semantic/closure_native.py:45–83`) and `GRANT`/`REVOKE` (`pglast.ast.GrantStmt` at
several sites) but not `CREATE TRIGGER` (only f-strings, `semantic/target_installation.py:326–374`,
`semantic/data_operation_storage.py:1929, 1954`) or `CREATE VIEW` (`semantic/pdf_publication_native.py:490–535`).
Two finite forms close the gap: a trigger statement built from `pglast.ast.CreateTrigStmt` with the
relation taken from compiled metadata, and a view built from `pglast.ast.ViewStmt` over a Core
`select`.

**Alternatives.** Keeping text with after-the-fact verification works (each transform verifies
preservation) but keeps several sources of truth and repeated parses that grow with owners per
script. Deriving the set by scanning modules for generator functions without a registry hides the
list instead of declaring it.

**Library mechanisms.** pglast AST nodes and `RawStream` printing (observed in the project's use);
SQLAlchemy `CreateTable` and `Table.to_metadata()` for scratch tables; networkx
`lexicographical_topological_sort`, already pinned and used (`semantic/graph_runtime.py`).

**Test seam.** Native authoring fixtures that assemble the kernel by name list move to the registry.

<a id="r05"></a>

### R05 — Identity from declared dependencies (Q4; DA-068, DA-069, DA-076, DA-078 part, DA-082, DA-083 custody)

**Diagnosis.** `native_source_digest()` hashes every captured `native/*` artifact including whole
generator modules and six library versions (`semantic/data_operation_storage.py:703–713`); it keys
seven consumers (descriptor check, release admission, read pin, completion seal, receipt
validator, each native operation's declared behavior, the readiness watermark). PDF lowering is a
hand list of 70 files and 14 libraries, too narrow and too broad (`semantic/pdf_lowering.py:15–104`).
Served reads use hand lists (`_query_custody.py:17–127`; `semantic/demand_queries.py:117–124`).
Opaque boundaries for construction and formal operations hash whole files and library versions
(`semantic/characterization_ports.py:47–193`; `semantic/formal_products.py:688–756`). The finest
existing identities are unused for this: each program's generated bytes are captured, and the
module meaning projection ignores formatting (`semantic/python_module_projection.py:110–120`).

**Target behavior.** The identity layering of §3.3. Concretely:

- the descriptor check, release admission and the read pin compare kernel identity (program bytes);
- the completion seal and receipts carry the validator identity of each of the operation's families, or of the
  conservative validator for an unclassified operation; the replay gate compares
  it, and a successful replay is recorded per receipt and validator identity by a routine that can
  write, outside the stable validity function (R11);
- each native operation's declared behavior names its own program closure's identity, so its
  recipe changes only when its programs change;
- the watermark's kernel component becomes the read-and-validity closure identity (the remaining
  watermark granularity question is R10's premise, not this one);
- PDF lowering identity is the identities of the PDF programs plus the derived code identity of the
  Python lowering entry modules; served-read identity is the derived code identity of the read entry
  modules plus the read programs' identities; opaque boundaries use derived code identity for code
  and content digests for grammars and rule data files;
- code custody (query custody generalized) loads the derived closure's modules, compiling exactly
  the hashed bytes, so recorded module bytes and imported code cannot diverge (DA-083's hermeticity
  gap);
- the release id covers generated artifacts and the model capture; generator provenance is
  recorded beside them.

**Alternatives.** Keeping the whole-capture digest is safe and fails A4 (every docstring edit or
library patch invalidates admission, reads, receipts and watermarks). Hand lists with completeness
tests stay hand lists. A runtime-recorded import closure misses modules imported earlier by other
code. Function-level slices everywhere are finest, but the existing slicer refuses unknowns on
dynamic code, so they are used where they resolve and the module closure is the fallback.

**Library mechanisms.** Python `ast` (the existing `admitted_operation_module_meaning` pattern);
the closed-source extractor (Griffe, LibCST, astroid) already used for operation slices
(`semantic/python_operation_sources.py:1063–1140`); `importlib.metadata.packages_distributions()`
and `version()` to map imported top-level packages to distribution versions (standard library,
documented).

**Challenge cases.** A generator change that changes semantics changes bytes, so it changes the
program identity; there is no semantic change without a byte change in what is installed. A
pglast or SQLAlchemy patch that changes rendering changes bytes and so identity; one that does not
changes nothing downstream. A served-read helper importing a module through `importlib` by string
would escape the static closure: such imports are refused by code custody's finder for covered
packages. Where the closure computation meets a dynamic import it cannot resolve, the served read
still runs but its identity is incomplete, so its result is neither cached nor offered as a
resumable continuation; this is ADR-0092's rule that unknown determinants withhold reusable
identity, and it keeps an exploratory served helper usable without letting it be reused on a
guessed identity. A docstring edit
in a closure module still changes the module's syntax projection (docstrings are syntax); stripping
docstrings is a possible refinement, not required.

<a id="r06"></a>

### R06 — The execution path generates nothing (DA-083; review finding F01)

**Diagnosis.** `require_data_operation_native(connection, prepared)` receives the prepared release
and ignores it: it calls `native_source_digest()` twice with no arguments, regenerating the whole
capture from the checkout, and compares the result with the installed descriptor
(`semantic/data_operation_storage.py:1116–1131`). Yet the release already records its kernel digest:
`native_digest_from_dependencies(dependencies)` computes it from the release's captured artifacts
(`:1069–1070`, used at `semantic/prepare.py:1024–1030`), the release row stores `native_kernel_digest`
(`model/semantic/data-operation-physical.yaml:22`), and release admission compares it with the
installed descriptor (`semantic/data_operation_compiler_native.py:998–1093`).

**Target behavior.** The per-acquisition check compares the installed descriptor with the kernel
identity the prepared release records, a value already in hand. No generator runs on port
acquisition, cached-port recheck, publication-port acquisition or definition admission. Working-tree
drift of Python code is detected by code custody (restart), as for served code; drift of the
installed kernel against the release is still refused. The demand export reads its wire schema from
the compiled model's protocol projection (`serve/demand_export.py:281`).

**Alternatives.** The audit's lead, a holder for the capture under file custody, would still make
every acquisition depend on generation and on the checkout; it is right for authoring (T2) and
unnecessary on the execution path.

**Challenge case.** A process that imported generator modules, then had them edited, then acquires
a port: the installed kernel still matches the release, so acquisition proceeds with the code the
release was prepared with; the edited generator is used only by authoring commands, which refuse
through code custody.

<a id="r07"></a>

### R07 — The remaining PostgreSQL conversion: what it produces and in what order (Q5; DA-084, DA-086)

The conversion is scheduled, open work under ADR-0131 and the DDO coordinator; the target says what
it should produce. Per category, with the helper's classification:

| Category | Today | Target | Order |
|---|---|---|---|
| Product logic as PL/pgSQL strings in the eleven `*_native.py` modules without the program compiler (about 1,830 lines; about 2,090 with `pdf_publication_native.py`, `data_operation_cpu_basis.py:463–543`, `execution_evidence_leaf.py`): rich, structural, contextual, contextual witness, definition admission, PDF spool, archive (product part) | Name relations and columns as free text; hold operation-id lists, family names, role names, factory paths and kind URNs as literals | Typed programs that read the lowered three-state family, roles and per-operation facts from declarations; relations and columns from compiled metadata | **After the facts each module holds have a declared home** (its families' membership and validator programs, the roles it grants, its guard classification), and after R04's trigger and view forms. The rest of R02 (ownership vocabulary, grammar migration, derived source collections) does not gate it |
| Loaded `.sql` files that are product logic: `identity.sql`, `data_operation_source_admission.sql`, `data_operation_visual_read.sql`, `source_originals.sql`, `source_record_recognition.sql`, `pdf_descriptor.sql`, `data_operation_task_checks.sql` | Hand bodies, some with token replacement | Typed programs; the task checks fragment becomes part of the typed task-guard trigger function reading the lifecycle | After the lists they hold have a declared home; task checks can proceed now |
| `contextual_neighborhood.sql` | Hand SQL function; a pure function of its JSON arguments using pgvector | A typed `sql_function` using a Core custom operator for `<=>`; stays in PostgreSQL because its numerical backend is pinned and checked (`semantic/contextual_numerics.py`) | Independent |
| Independent controls: `closure.sql` (runtime principal gate), the catalog comparison of `admission.sql`, `alembic_privileges.admission_comparison_sql`, the catalog part of `archive_native.py` (`:46–73`), `semantic/execution_admission.py:102–140`, `schema/model_deployment.py:921, 963` | Hand-written by design; generated fragments spliced at text markers (`semantic/native_admission.py:415–444`; `semantic/alembic_privileges.py:567–589`); role names as literals | Keep hand-written (their independence from generators is their purpose) but take the generated expectation and the declared role and schema names as **data arguments**, never spliced text | After R02 (role vocabulary); the splice removal can proceed now |
| String templates (eleven splice sites in seven modules) | Tokens and markers | Retire with the two rows above | With them |
| Text handoff after rendering | Concatenate, patch, rename, re-parse | R04 | R04 first |
| Free callee names (`func.<schema>.<name>`) | Bound only at install | Checked against the program registry's declared names at generation | With R04 |
| Small `text()` and plumbing sites (`evaluate/operation_fitting.py:539–594`; locks and `set_config` in `storage_target.py`, `migrations.py`, `native_sql_body.py`, `core/db/extensions.py:17`) | SQL text | Core `func.*` calls | Independent |
| SQLite scratch stores (`semantic/data_operation_read_index.py`, `serve/selected_source.py`, `serve/demand_export.py`, `semantic/pdf_payload_validation.py`, `semantic/pdf_certification.py`) | SQL text built by concatenation, including field names in `json_extract` paths (`data_operation_read_index.py:20–27, 66–74`) | SQLAlchemy Core over SQLite with private declared `Table`s (keyed lookups suit SQLite; DuckDB is wrong for point lookups); the certification fold moves to DuckDB (R12) | Independent (finding F04; rule impact RC02) |
| DuckDB | No SQL text today | Stays so; recursion, if ever needed, through a relational semi-naive loop, or failing that a SQLGlot-built statement in the DuckDB dialect | — |
| Frozen migrations (`target_alembic/`), submitted read-only SQL (`semantic/authored_sql.py`) | Exceptions | Unchanged; both sound | — |
| Unconsumed trees and files: `semantic_alembic/`, `alembic/`, six unloaded `.sql` files | No consumer | Retire (R13); the trees need the operator's decision | Independent |

**The ordering is the point.** Converting the residue first, as record grade was converted, would
put the family and role lists into typed programs as Python tuples, a third transcription. Declaring
the facts first makes the conversion a consumer of them. The gate is deliberately narrow: only the
facts a module reads must have their home first, so the declaration step does not hold the
conversion hostage to vocabulary questions it does not need settled.

**Alternatives.** Classifying the residue as a fourth permanent exception (cheapest; leaves
ADR-0131's consequence untrue for it and the lists hand-kept). Encoding PL/pgSQL in LinkML
(ADR-0131's rejected option 2) still loses.

<a id="r08"></a>

### R08 — One declared support-edge meaning and one walk (DA-071)

**Target behavior.** `SupportEdgeKind` (use, episode, population, original) is declared with a
structured traversal table per purpose (validity; lock and scope superset) and the reference-to-node
mapping and scope-key rule. The validity edge program (`semantic/data_validity_native.py:88–240`) and
the support walk (`semantic/data_operation_projections.py:117–242`) are generated from that table.
Change impact stops re-encoding the walk: revocation causes come from an explanation output of the
validity closure program (per reached node, valid or the revoking edge and selector), produced in the
acquisition transaction, and the operation-level "which operations changed" comes from the compiled
`selected-dependencies` projection instead of `semantic/change_impact.py:157–193`. The trust-scope key
has one definition, `ops.ddo_scope`. `_revocation_causes` and its two private mappings retire. The
reference-to-node mapping covers every declared reference kind and refuses an unrecognised one,
replacing today's open default that classifies any reference that is neither an original nor a use
as an episode (`semantic/data_operation_projections.py:117–129`).

**What this closes and what it leaves open.** Support edges are provenance among native rows (uses,
episodes, populations, originals); validity, revocation and lock scope must know every kind, so the
set is closed by purpose and a new kind is a native schema change in any case. Knowledge relations,
pack predicates, proposed links and alternatives are not support edges; they stay open in the packs
and in the content model and are untouched by this recommendation.

**Alternatives.** Moving change impact's walk to DuckDB over exported edges re-hosts the third
encoding rather than removing it (the DuckDB tie-breaker of [DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §G prefers removal).
Keeping three encodings with a cross-check test leaves three places to edit per edge kind.

**Challenge case.** The scope walk is deliberately a superset of validity; generating both from one
table with two traversal profiles keeps that distinction explicit instead of erasing it.

<a id="r09"></a>

### R09 — The cache system (Q7)

See [cache-design.md](unified-domain-model-and-execution/cache-design.md). Summary of choices: T1 compiled model and T2 program set as
count-bounded `LRUCache`s wrapped by `cached(..., condition=Condition(RLock()), info=True)` with
negative caching of deterministic build errors; T3 releases and archives bounded by retained bytes and
keyed by database identity instead of engine object; T4 served results as a byte-and-count bounded
`LRUCache` subclass with a future-based single-flight that shares failures, keyed by query,
implementation identity, authorization scope and a declared reuse basis; T5 CPU runtimes bounded by
declared footprint; T6 memos on `cachetools.func.lru_cache` and `cached` with `condition`; a sixty-line
owner module for registration, statistics, settings-driven sizes and event clears; and two
content-addressed disk tiers (program sets; continuation pages) for the command line. GPU residency and
the execution host keep their lifecycles (ADR-0125). About 55 cheap `functools` caches stay.

<a id="r10"></a>

### R10 — Served-read reuse basis and the watermark premise (DA-075, DA-078)

**Target behavior.** Each served query may declare its reuse basis, `cut` or `content`; a query that
declares nothing uses `cut`, the basis that is sound today, so a new or exploratory served query
needs no declaration. Continuation pages
reuse across CLI processes now (cut-keyed, sound because the cut pins frontier, trust snapshot and
visibility, and authority is re-acquired per call). A query may declare `content` (frontier content
stamp, release, runtime, selection, implementation, authorization scope, without the read instance)
only after the native owner establishes that its derived rows are a function of frontier content; the
identity-exclusion comparison already relies on that premise. The readiness watermark drops the kernel
component (R05); narrowing it from "every transitive prerequisite operation by source" to the declared
role producers is proposed, subject to the native owner's soundness argument, because binding remains
the authority and a conservative watermark cannot admit a wrong result.

**Alternatives.** Content keys everywhere now: unsound until the premise is settled. Keeping read-instance
keys only: the command line never hits.

<a id="r11"></a>

### R11 — Carried assurance (Q8; DA-033, DA-068 replay)

**Target behavior.**

- Release-content proof: admission checks the finalization receipt and the deployment-admission receipt
  for (release id, physical id, descriptor digest, kernel identity) and skips re-hashing every archive
  input on each acquisition; the full re-proof stays available as an explicit verification command and at
  activation. Lapse: any of the four identities changes. This needs the operator's trust decision (DA-029's
  premise that definer roles are trusted already applies) and is rule impact RC08.
- Binding: `ops.ddo_require_binding` and population selection read the admitted definition rows, which
  already hold the binding expression and identities, instead of parsing and hashing
  `data_operations.json` per call (`semantic/binding_admission_native.py:232–251`;
  `semantic/population_acquisition_native.py:906–921`).
- Validator replay: recorded per receipt and validator identity; lapses when the family's validator
  identity changes.
- Established product validity: keyed by the validator asset's content identity rather than the release
  (the audit's row; the PE item is owned by the DDO plan and is affected, not re-owned).
- Model validation (profile and consistency checks, declaration validation, the list of unclassified declarations) runs once per compiled model and is
  carried by the compiled-model object.

**Challenge case.** A superuser alters archive bytes despite immutability triggers: per-acquisition
re-hashing would detect it, the target detects it only at explicit verification or activation. That is the
trust trade the operator decides.

<a id="r12"></a>

### R12 — Analytical placement and DuckDB conditions (Q6)

**Conditions of use**, from the library contributor's decision rule, kept: inputs are an immutable
identified snapshot (exported Parquet, Arrow from the authorizing session, Arrow IPC files); the work is
set-shaped and large enough that fixed per-query cost does not dominate; it is built from expression objects
with model-derived input schemas; and the connection sets `TimeZone='UTC'`, threads, memory limit and an
absolute spill directory from `AnalyticsSettings`, with one cursor per thread. PostgreSQL inputs arrive by
exporting Arrow from the application's own session (ADBC or binary `COPY`), never by `ATTACH`.

**Typing from the model.** One bridge on the compiled model produces Arrow schemas: for physical relations
through `MetaData` and `semantic/arrow_types.sql_arrow_type`, for non-physical LinkML classes through the
slot-range mapping the companion projection already uses (`semantic/companion_projection.py:88–140, 165–216`).
DuckDB scans Arrow with its type mapping; outputs are finished with `table.cast(model_schema, safe=True)`.
Traps to handle (probed by the library contributor on synthetic data, [DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §D): dictionary
columns arrive as `VARCHAR` (cast to an `ENUM(...)` type string derived from the model only for
vocabularies declared closed, R15; open and pack-extensible vocabularies stay `VARCHAR`, so an analysis
over data that uses a term not yet settled does not refuse); `TIMESTAMPTZ` takes the session time zone; JSON typing ends at the boundary; a union can widen
silently.

**Keeping "no SQL text".** The relational API accepts strings in filters, conditions and `sql_expr`. The
convention is: expression objects only (`col`, `lit`, `fn`, `when`), column names taken from the
model-derived schema, no `sql`, `query` or `sql_expr`. A renamed column then refuses at relation
construction: DuckDB raises `BinderException` when a missing column is projected (probed by this reviewer,
§10). No new lint is proposed (the project rule against alignment linting stands); the convention rides on
code review.

**Where operation-local shapes are code.** An Arrow schema that only one kernel builds and reads (candidate
boxes `ingest/pdf_candidate_geometry.py:60–72`; the recognition replay `ingest/pdf_stream_reconciliation.py:233–241`;
the rich view relations `semantic/analytical_kernels.py:21–60`) is an implementation detail, not a domain fact,
and stays a local `pa.schema`. Names inside it that *are* model slots derive from the model: the projected
entity attributes `("id", "key", "types", "label", "symbol")` (`semantic/analytical_kernels.py:62`) come from
the rule-view `Entity` class (`model/semantic/rule-view.yaml:23`).

The judgment per computation is the table in §5.

<a id="r13"></a>

### R13 — Retirement (Q9; DA-072, DA-080)

The target removes: the earlier model (`model/core.yaml`, `model/system.yaml`, `model/revisions.yaml`,
`core/vocab.py`, `core/_model/*`, the parts of `core/keys.py` not live, `schema/change.py`, `schema/pack.py`,
`schema/lookup.py`, `domains/statistics/schema/statistics.yaml`) after its 39 importing modules move to
released-model types, including the generated facade that emits `core.vocab.TaskUnitType`
(`semantic/native_call_generation.py:106`); the per-consumer composition routines; the hand operation-grammar
validator, `_PROFILES`, `_KIND_UNIVERSES`; the validity tuples, guard id lists and the completion `If` chain;
the frontier-guard tuple and shared-stream name set; role literals outside the vocabulary; the four field-kind
maps; the hand program lists and facade tuples; text markers and the entry-point rename pass; `LOWERING_FILES`,
the query custody lists and the capture's module enumeration; the scientific recipe description; the two
uncalled DuckDB kernels (`semantic/analytical_kernels.py:150, 170`; `semantic/rich_relations.py:112, 115`) and
`FileRelation`; six unloaded `.sql` files; `semantic/published_address_migration.py`; the evaluation modules with
no production importer (`evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`, `sampling.py`,
`split_decisions.py`, `split.py`, `sets.py`) unless the operator names a consumer; and, by operator decision,
`semantic_alembic/` and `alembic/`. Unread `AnalyticsSettings` fields are wired (R12), not removed.

One prerequisite protects an intentional flexibility. The earlier model is the only place that
declares whether a vocabulary may be extended by packs (`Lifecycle`: `static` or `schema_version`,
`model/core.yaml:1034–1040`, enforced by `schema/pack.py`). Before `core.yaml`, `schema/model.py` and
`schema/pack.py` retire, that distinction moves to the released model (R15), and the released route
for pack extension (pack schemas imported by the release, `domains/statistics/operations.yaml`) is
confirmed to cover what the earlier pack loader allowed.

<a id="r14"></a>

### R14 — The scientific policy derives from its declaration (DA-077)

**Target behavior.** `scientific-policies.yaml` becomes instance data validated by a LinkML class; the
comparison kernel reads its parameters (for example the sampling bounds now written as `rng.uniform(0.25, 3, …)`
at `semantic/scientific_evidence.py:1301`) from that declaration; the archived recipe is the canonical
serialization of the same declaration, computed once per compiled model. A kernel edit then changes the recipe
or nothing, and a wording edit cannot refuse every release.

<a id="r15"></a>

### R15 — Declared openness of vocabularies (F05; added by the recommendation audit)

**Diagnosis.** The earlier model declares, per enum, whether a set changes only with code
(`static`, enforced by a digest-named check) or may be extended by packs (`schema_version`, enforced
by per-version member rows) (`model/core.yaml:1034–1040`, applied at `:895, 913`); its pack loader
refuses pack members for a static set and accepts them for an extensible one (`schema/pack.py:1–22`).
The released model has no successor: `semantic/ontology.py:328–410` composes `inherits`, `include`,
`minus`, `concepts` and ontology `reachable_from` members without any openness property, and every
released enum is closed in validation. R13 would retire the earlier model and with it the only
representation of this intended distinction.

**Target behavior.** Each released vocabulary declares one of three kinds of openness, with stated
consequences:

- **closed**: changes with code; programs may dispatch on it; checked at import (`Literal` copies),
  in physical checks through `ph:values_from`, and in analysis casts (R12);
- **pack-extensible**: a pack may add members through `inherits` or `include` in its own schema;
  members become per-release vocabulary rows; a program that dispatches on such a set names its
  handling of members it does not know;
- **open with known members**: any value is accepted; known members carry declared meaning that
  consumers may test; an unknown value carries none and is reported through the existing
  non-refusing `unchecked` diagnostic (`semantic/prepare.py:485–530`, category `unassessed`,
  `semantic/operation_reporting.py:372–410`), never refused.

Individual members may be marked provisional with the `status` slot permissible values already carry
in LinkML; a provisional member is accepted and reported. Ontology-derived vocabularies keep their
`reachable_from` membership and their `unchecked` reporting. Knowledge content is not governed by
this declaration: a source term outside a vocabulary is still recorded with its explicit state
(candidate, `missing_candidate`, unsupported proposal, validation error retained under ADR-0077).

**Library mechanisms.** No openness flag exists on LinkML 1.12.1 enums (observed in the installed
metamodel's `enum_expression` slots), so the declaration is a released-model annotation succeeding
`ci:lifecycle`, admitted deliberately by the preparation profile, which refuses unsupported
annotations (`semantic/prepare.py:259`). Open slots use a range of `any_of` the enum and `string`.
Provisional members use the native `status` slot of `common_metadata`.

**Challenge cases.** A pack tries a new measurement-role term: if the vocabulary is pack-extensible it
adds the member in its own schema and no core edit is needed; if it is closed, the refusal is the
declared intent and says so. An extraction yields an ownership-like label nobody has defined: for an
open vocabulary it is kept and reported. A program that dispatches on a vocabulary can only do so for a
closed one or with a declared handling for members it does not know, so a new pack member can
never reach a dispatch without a handler.

<a id="r16"></a>

### R16 — Graded consequences for undetermined declarations (DA-070; added by the recommendation audit)

**Diagnosis.** Today an operation outside the classification list gets the most permissive
treatment: its family premises are never evaluated (DA-070). The first-round remedy went to the
other extreme, refusing any operation that has not classified itself. The project already has a
middle course in two places: identity, where unknown required determinants withhold reusable
identity without forbidding execution (ADR-0092; `semantic/data_operation_identity.py:378–387`), and
preparation, where unchecked vocabulary terms are reported as `unassessed` without refusing.

**Target behavior.** An undetermined declaration is permitted and carries a stated conservative
consequence. For the validity family:

- *named families*: each family's validator runs; validity is their conjunction;
- *`none`*: a positive claim that only generic validity applies (outcome, revocation, support
  propagation); derivations survive later changes of trust and kernel;
- *absent or `undetermined`*: the operation compiles and runs; preparation reports it as
  unclassified; validity adds a **conservative premise check**, under which a derivation is valid
  only while the trust snapshot and the validator identity it was produced under are unchanged. This
  over-invalidates and never under-invalidates. The conservative check is one generated program with
  its own validator identity (R05, R11);
- *a provisional family*: its members are treated as undetermined until its validator exists.

A **promotion boundary**, at which undetermined declarations refuse, is the operator's choice
(RC14): none; activation of the default release; or knowledge publication. Because the conservative
check already removes the integrity risk, the recommendation is none, with the diagnostic as the
pressure to classify. The same graded pattern is available, not imposed, for other declarations
that may be unknown when an operation is first written.

**Feasibility and limits.** The store already records some of the premises the conservative check
needs: publication receipts hold `trust_snapshot` and an optional `validating_kernel_digest`
(`model/semantic/data-operation-physical.yaml:475–484`), support rows record the trust scope and
epoch they relied on (`:458–466`), and demand reads record a trust snapshot and kernel digest
(`:619–631`). Whether every episode can be tied to the trust snapshot it consumed is for the native
owner to confirm (Proposed). The default cannot cover a family-specific premise outside trust and
kernel, such as the contextual linguistic premise (DA-070); that residual risk is why family
bindings exist, and under this design it is visible as an unclassified diagnostic rather than silent.

**Challenge cases.** An exploratory operation is added and run on a book: no declaration is needed; its
results are kept; a trust revocation elsewhere invalidates them conservatively and they are recomputed
on demand. Once its semantics are understood it declares `none` or a family and stops paying for the
conservative check. A family is designed before its validator is written: it is declared provisional,
and its members behave as unclassified until the validator lands.

## 5. DuckDB judgment over the analytical inventory

IDs follow the analytical map ([analytical inventory](../evidence/2026-11-18_production-review-inputs/analytical-inventory.md) §10). "Bound" means the work needs PostgreSQL's transaction,
locks, principal or writes.

| ID | Computation | Verdict | Reason and condition |
|---|---|---|---|
| G1 | Validity closure and fixpoint | Keep in PostgreSQL | Bound: visibility by transaction id, revocation table, caller principal |
| G2, G3, R1 | Support walk, watermark prerequisites, tree and dependency walks | Keep in PostgreSQL | Bound; generated from the declared edge table (R08) |
| S4 | Full-text ranking | Keep in PostgreSQL | `ts_rank_cd` parity and dictionaries; DuckDB's BM25 differs (documented) |
| G7, C1 (database part) | Mutual exact-cosine neighbours over pgvector | Keep in PostgreSQL, as a typed program | Pure, but its numerical backend is pinned and checked (DP-11) |
| D1 | Rich-rule occurrence views (same slot, alternative of, declared projections) | Keep in DuckDB, conditional | Join-and-group shape over up to 100,000 members; round trip from Python objects costs per invocation. Revisit to plain Python if observed per-subject inputs are small. Derive model slot names (R12); connection settings from configuration |
| D1b | `disagreements`, `fuse` kernels | Retire | No production caller; the live disagreement grouping is Python (`semantic/rich_consolidation.py:336–372`) |
| D2 | Companion export inventory and multiset comparison | Keep in DuckDB | File-scoped `EXCEPT ALL` with multiplicity is its strength. Derive grouping and excluded columns from `cp:` annotations; set time zone and spill; bound the materialized difference (today unbounded, `serve/companion_export.py:582–600`) |
| D3 | PDF candidate geometry joins | Keep in DuckDB | Containment and intersection joins with windows; box schema is operation-local |
| D4 | Recognition replay external sort | Keep in DuckDB | Spilling sort of a large IPC file; fix the duplicated `input_key` in `pin_json` (returned to the audit) |
| D5 | Splink scoring | Keep | Library-owned SQL |
| I8 | Certification staging folds (SQLite staging, then ordered folds) | Move to DuckDB, conditional | Rows already arrive as Arrow IPC; a DuckDB sort by key streams to the Python digest fold and removes a per-row SQLite copy. Condition: binary key ordering matches today's `COLLATE BINARY` (DuckDB's default string comparison is binary; verify once) |
| X1 | Companion export (PostgreSQL to ADBC to Parquet) | Keep | Bound to the exported snapshot; already Arrow |
| X2 | Companion file verification | Plain Python, with carried status | Verification runs per path per inventory and twice per compare; carry the verified status per file identity (T0 custody) instead of moving it |
| X5 | Detached selected-result export (SQLite dedup, then Parquet per relation) | Plain Python with Core over SQLite | Keyed dedup and ordered batches; DuckDB adds JSON-to-typed conversion work for modest gain. Revisit if export size makes the per-row path material |
| X6, S6, S7, S8, S1 | Per-page joins and shaping of acquired pages; identity-exclusion comparison | Plain Python | Page-sized, after authority; S6's whole-admission index is held in T4 |
| S3 | Source catalog with one native read per row | Keep in PostgreSQL, set-wise | Push the per-row header read into the page's native read (an N+1, returned to the audit) |
| X7 | Model and release comparison | Plain Python | Small compiled models |
| X8 | Selected-source package verification | Plain Python with Core over SQLite | Replace per-row ancestry queries with one set-wise query; keyed |
| G4, G6, G8, G9 | Semantic graph, graph inspection, bounded rich walks, rich closures | Plain Python (networkx) | Small or explicitly budgeted; G4 held in T1 with the compiled model |
| G5 | Change impact | Remove the re-encoding (R08); the remaining classification is plain Python | Index revocations by node instead of scanning nodes against all revocations |
| G10 | Pairwise artifact candidates with string ratio | Plain Python | rapidfuzz scores are the numerical contract; DuckDB string functions differ |
| E1–E6, SC | Alignment, matching, bootstrap, fitting, sampling, scientific comparison, record interpretation | Plain Python numerics | numpy and scipy semantics; no set-shaped gain |
| I1, I2 | Page availability flags by per-row loop over Arrow | Plain Python with `pyarrow.compute` | Vectorize the loop; no engine needed |
| I3 | Candidate counts | Keep (`pyarrow.compute`) | Already vectorized |
| I6, I7, M1 | Docling graph selection, box merging, table interpretation | Plain Python | Object-graph work |
| T1, T2 | Arrow to PostgreSQL copy; row streaming into operation inputs | Keep | Bound |

**Where DuckDB should not be used:** anything needing PostgreSQL's snapshot, locks, principal or writes; read-side
paging served to clients; point lookups and small keyed reads (SQLite or a dict); tens to hundreds of rows already
in Python; full-text ranking; any route that would `ATTACH` PostgreSQL. DuckPGQ is not adopted (community research
extension, 2.0.0 binary unconfirmed, SQL text).

## 6. Fact-authority table

"Retires" lists what the target removes for that fact.

| Fact | Target authority | How consumers obtain it | Retires |
|---|---|---|---|
| Record and product shape | LinkML released model | Compiled model: merged view, `MetaData`, Arrow bridge, generated facades | Earlier-model copies; hand Arrow schemas for model relations |
| Field type and constraint | LinkML range, pattern, bounds; physical checks as structured annotations under the profile | Compiled `MetaData` checks | JSON strings in annotations; the universe check literal beside `_KIND_UNIVERSES` |
| Field kind to database and Python type | LinkML type `uri` and `ph:sql_type` (declared today, `model/semantic/physical.yaml:33–36`) | The physical compiler's type resolution (`schema/relational.py:79–89, 437–440`), exposed once on the compiled model | Four maps (`semantic/native_call_contracts.py:16–25`; `semantic/native_call_sources.py:28–37, 133–136`; `semantic/pdf_search_native.py:98–104`; `semantic/native_program.py:621–622`) |
| Domain value sets | LinkML enums, expanded once by the released `expand_enum`, each declaring its openness (closed, pack-extensible, open with known members; R15) and optionally provisional members | Compiled value sets; closed-set checks for Python `Literal` copies of closed sets; physical checks through `ph:values_from`; unknown values of open sets reported, not refused | Duplicates in the earlier core; one of the PDF outcome pair |
| Operational vocabularies (profile, kind universe, ownership, forms, validity family, support edge kind, purpose, role) | LinkML enums in a declaration schema with declared openness: profile, kind universe, forms, validity family, support edge kind, purpose and role closed; ownership open with known members; preparation and cancellation descriptions unconstrained | Compiler, generated dispatch, closed-set checks for closed sets | `_PROFILES`, `_KIND_UNIVERSES`, hand tuples |
| Operation (existence, roles, dependencies, capabilities) | Instance data through ADR-0092's two routes; Python literals validated against the LinkML declaration class | Effective operation model | Hand grammar validator |
| Validity family membership | Optional, set-valued field on each operation declaration: named families, explicit `none`, or absent/`undetermined` with conservative validity and a non-refusing diagnostic (R02, R16) | Lowered definition column distinguishing the three states; generated dispatch | Two tuples, guard id lists, completion chain, contextual id lists |
| Family contract (validator program, premises) | Enum member annotation naming the validator program, or `status: provisional` while it is unwritten | Program registry | Dispatch tuple |
| Per-operation contract facts (entry point, profile, forms, preparation, effects) | Effective operation model (exists) | Lowered definition rows; the contextual pin only between distinct inputs | Contextual `CASE` literals when circular |
| Support-edge meaning, reference-to-node map, scope key | Declared closed `SupportEdgeKind` with a traversal table per purpose (provenance edges only; knowledge relations stay in packs) | Generated validity and support walks; change impact through the validity explanation; unrecognised references refuse | `_support_walk`'s private map and its open `episode` default; `_revocation_causes`; change impact's scope formula |
| Operation dependency graph | Compiled `selected-dependencies` and `potential-producers` | Change impact, planner | `changed_operations` hand graph |
| Release composition | Source collection derived from the captured collection that includes each literal (an `acquired_by` field only to override), plus a manifest of requested operations or families; partial releases are ordinary | Closure over compiled dependencies mapped to source collections | Flag logic in `semantic/primary_operations.py:118–392` |
| Relation physical layout (keys, foreign keys, checks, indexes, immutability, archive role, search configuration) | LinkML physical declarations under the typed profile | `MetaData` and its `info` | JSON-string encodings |
| Frontier-guard membership | Declared schema-level default (`guarded`) with per-relation `exempt` overrides in the physical profile | `MetaData.info`; generated trigger | Twelve-name tuple |
| Shared-stream trigger membership | Existing `ph:immutability: pending-content` | `MetaData.info` | Name set |
| Roles (names, login, memberships, prohibitions) | LinkML `Role` vocabulary | Host bootstrap, grants, control expectations as data | Constants in `semantic/alembic_privileges.py:25–35`; 176 role-name occurrences in 39 modules; role JSON in `admission.sql` |
| Purpose to role | `Purpose` vocabulary member annotations | Protocol function grants; program grants | Literal dictionary in `semantic/data_operation_storage.py:1887–1893` |
| Table read grants | Declared default read roles per schema, explicit `ph:read_roles` where a relation differs | Alembic privilege operations | `DEFAULT_READ_ROLES` as a code default; restatement in `admission.sql` |
| Execute grants for native functions | Program declarations' purposes | Generated `GRANT` nodes; control expectations | Name-matching chain; installation tuples; default grants in helpers |
| Task states and transitions | Protocol lifecycle (retained) | Compiled lifecycle projection | State string literals in generators |
| Wire shape and native operation ABI | Protocol (retained peer) | Generated wire module; validators held in the compiled model | — |
| Value-codec vocabulary | LinkML observations vocabulary | Closed-set check at import | Python `Literal` plus hand `_TEXT` tuple |
| Native program set (existence, order, signature, grants, callees, family) | Typed program registry | Program set; topological order | Hand lists, naming conventions, markers |
| Generated outputs (facades) | Self-checking generated-output registry | Preview renders every registered output | `_NATIVE_OUTPUTS` zip and `__main__` paths |
| Code that determines an artifact | Derived code identity plus program identities | Identity computation | `LOWERING_FILES`, query custody lists, capture module enumeration, port generator list, opaque asset lists |
| Scientific policy parameters | Policy declaration validated by a LinkML class | Kernel reads it; recipe is its serialization | Hand recipe description; kernel literals |
| Custom catalogs (PDF actions, analysis policy, metrics, characterization questions) | Instance documents, each with a LinkML class; closed-world where fields drive behaviour; the explicit open states inside them (for example `insufficient_evidence`, `missing_candidate`) kept | Validated once per compiled model | Ad-hoc parsing (consumers not traced) |
| Operation-local analytical shapes | Local `pa.schema` beside the kernel; model slot names from the model | — | Hand restatement of model slot names |
| Companion grouping and provenance columns | `cp:` annotations | Companion projection | Literals in `serve/companion_export.py:419–424, 557–589` |
| Identity determinants | Compiled (sound); unknown determinants withhold reusable identity (ADR-0092), also for served reads whose code closure is unresolved (R05) | — | — |
| Vocabulary openness and member status | Released-model openness declaration succeeding `ci:lifecycle`; LinkML `status` on members (R15) | Preparation, closed-set checks, pack loading, analysis casts | `ci:lifecycle` in the earlier model |
| Undetermined declarations and their consequences | The declaration's own optional field with a declared meaning for absence; promotion boundary chosen by the operator (R16, RC14) | Preparation diagnostics (`unassessed`); conservative validator program | Permissive `else` defaults |
| Pack rule language | `schema/rulelang.py` (not examined) | — | Open; returned to the audit |

**Formalisms after the change:** LinkML (primary); the protocol as a peer for wire, lifecycle and native ABI;
Python literals as the storage form of one operation route; typed Python registries for code artifacts. The custom
catalogs stop being a separate formalism (they become LinkML-typed instance data), and the earlier LinkML model
retires.

**Derivations between retained authorities** (all existing or supported): LinkML to `MetaData` (project compiler);
`MetaData` to Arrow (`semantic/arrow_types.sql_arrow_type`); LinkML classes to Arrow (companion projection's slot
mapping, generalized); Arrow to DuckDB relation types (DuckDB scan mapping); protocol to physical value sets
(`ph:values_from`); protocol to wire module and validators (project generator); `MetaData` and the program registry
to typed programs (Core and pglast); closed LinkML enums to Python `Literal` checks (closed-set check); LinkML declaration
class to validation of operation literals (`linkml.validator` with the closed JSON Schema plugin for field names and
the recommended-slots plugin for warnings).

## 7. Change and failure scenarios

| Scenario and kind | Today | Target |
|---|---|---|
| Add a modeled field (domain concept) | LinkML slot; typed programs pick it up through compiled columns; hand bodies and hand Arrow schemas do not; the kernel digest and release id change; PDF certification refuses if a listed model file changed | LinkML slot; new model identity; only programs whose bytes change get new identities; Arrow schemas derived |
| Add a value-set member (instance) | Edit once, or twice where the set is duplicated in the earlier core; the value codec tuple may be missed silently | One enum; for a closed set, checks of code copies refuse drift at import; for a pack-extensible set, the pack adds the member; for an open set, nothing is required |
| Add a data operation (instance) | Literal, plus family tuples, guard lists, the contextual `CASE`, release flags and program lists as applicable; an omission fails open | Literal; its source collection is derived; its family is declared when known. An operation left unclassified compiles with a non-refusing diagnostic and conservative validity |
| Add a validity family or a guard (policy) | New tuples, validator, dispatch entry, guard tuple | Enum member naming its validator program, or provisional until it exists; generation refuses a non-provisional member without one; new relations in guarded schemas are guarded by the declared schema default unless exempted |
| Add a role or change a grant (policy) | Edits across 39 modules and SQL | Vocabulary member and purpose annotation; generated grants; controls receive expectations as data |
| Change one generator module (mechanism) | Kernel digest changes: every acquisition refuses until a new kernel is deployed; release id changes; receipts replay; reads reacquire; watermarks advance; PDF work may refuse | Program set regenerates; if no bytes change nothing else changes; otherwise only the changed programs, the kernel identity and families whose validator closure includes them |
| Bump a library the generators use (mechanism substitution) | As above, even if every byte is identical | Generation cache key changes; regeneration; identical bytes change nothing downstream |
| Evolve the model with existing data | Alembic from `MetaData` and data steps; the preview rebuilds the capture two or three times | Unchanged migration route; candidate and running models coexist in T1; one generation per preview |
| Add an analytical question over published products | Hand Arrow schema; per-site DuckDB settings | §5 rule; Arrow schema from the compiled model; Arrow from the authorizing session; settings from configuration |
| Identical read from CLI and long-lived process | MCP hits only on continuation; CLI never | Continuation hits across CLI processes (D4); fresh identical requests once the content basis is certified |
| Two concurrent identical cold reads | Both derive | Both re-acquire authority; one derives; the other shares the value or the failure |
| Model change published while caches are warm | Import-time model kept until restart | New model identity; new entries; old entries remain valid for pinned reads; memory freed by event |
| Interrupted run resumed | Request identity reuse (sound) | Unchanged; disk tiers write-once with atomic replace; replay reconfirmation records are idempotent |
| Try an operation whose validity semantics are not yet known (exploration) | Indistinguishable from a forgotten family entry; its derivations are never re-validated against changed premises | No declaration needed; conservative validity; listed as unclassified until it declares `none` or a family |
| Try a relation or product kind in one pack (domain extension) | A pack class inheriting from a core class; registry rows, no DDL | Unchanged; none of the physical, guard or support-edge closures applies |
| Use a vocabulary term before it is settled (exploration) | Refused by a closed enum, or reported `unchecked` for ontology-derived sets | Accepted and reported for an open or pack-extensible vocabulary, or as a provisional member; refused only by a vocabulary declared closed |
| Keep competing structures side by side (content) | Alternatives, private proposals and disagreements retained (ADR-0024, ADR-0062, ADR-0077) | Unchanged; no recommendation constrains content |
| A release that includes only some operations (composition) | Profile flags in code; omissions refused at compile | A manifest of requested operations or families; closure over declared dependencies |

The domain extension (a new family) and the mechanism substitution (a library bump; a generator rewrite) both stay
local in the target; today both propagate across unrelated consumers. The exploratory scenarios stay as cheap as they are today or become cheaper; none of
them acquires a new mandatory declaration.

## 8. Correctness and fidelity gates

| Gate | Verdict | Evidence | Required action |
|---|---|---|---|
| G1 Authority | Fail | Family, edge meaning, guard and role facts held as independent lists with no reconciliation (DA-070, DA-071, DA-074); earlier and released value sets (DA-072); vocabulary openness declared only in the earlier model (F05) | R02, R03, R08, R13, R15 |
| G2 Semantic fidelity | Fail | A `NULL` validity family means both "no validator applies" and "forgotten" (DA-070) | R02, R16 (explicit `none`; explicit undetermined state with its own consequence) |
| G3 Validity | Fail | An unlisted operation reaches validity with its family premises skipped (DA-070) | R02, R16 (conservative validity for unclassified operations; no permissive default) |
| G4 Hidden behavior | Pass, with one concern | No undeclared effects found; a capture can pair generated SQL with module bytes from different code in a long-lived process (DA-083) | R05 code custody |
| G5 Consistency and recovery | Pass | Refusals are fail-closed; unrecorded replay is cost, not inconsistency | — |
| G6 Transformation and reuse | Fail | Narrow identities let resumed pages and lowering certification survive edits to code they omit (DA-076, DA-082) | R05 |
| G7 Truthful capability claims | Fail, scoped | ADR-0131's consequence ("propagates or refuses") does not yet hold for the scheduled residue or for declared facts generators do not read (DA-084, DA-086) | R07, R02 |
| G8 Library leverage | Fail, moderate | Hand `OrderedDict` LRUs, a hand entry cap, no single-flight; JSON strings where structured annotations exist; a hand grammar validator where schema validation exists; per-consumer composition | R01, R02, R03, R09 |
| CI-G1 Fidelity | Fail, scoped to change impact | Change impact follows edges validity does not and misses causes it sees; project-scoped revocations never match (DA-071) | R08 |
| CI-G2 Evidence closure | Fail across processes | A resumed served page can come from code its implementation identity omits (DA-076) | R05 |
| CI-G3 Evaluation integrity | Not assessed | Outside the operator's focus | — |

## 9. Findings

Consumed audit findings keep their identities and live in the audit; their dispositions are in
[dispositions.md](unified-domain-model-and-execution/dispositions.md). Additional review findings:

| ID | Finding and consequence | Principles · gate | Evidence | Correction | Closure evidence | Disposition |
|---|---|---|---|---|---|---|
| F01 | The per-acquisition native check ignores the prepared release it receives and regenerates the checkout's capture to compare with the installed descriptor, although the release records its kernel digest. This is the direct cause of DA-083's execution-path rebuilds, and it ties execution to the checkout instead of to the release | FP-07, DP-10; A4 | `semantic/data_operation_storage.py:1116–1131`; `:1069–1070`; `semantic/prepare.py:1024–1030`; `model/semantic/data-operation-physical.yaml:22`; `semantic/data_operation_compiler_native.py:998–1093` | R06 | A traced port acquisition that runs no generator and refuses when the installed descriptor differs from the release | Deferred to plan creation; reopens DA-083's remedy |
| F02 | Process-global memos reached from MCP tool threads are mutated without a lock, and several caches in long-lived processes are unbounded (parsers, a spaCy pipeline, a grammar resource) | DP-20; A4; G5 (likely, not observed) | `methods/math/grammar.py:309–327, 966–993`; `ingest/sentences.py:58`; `semantic/constructions/forest.py:36`; tool threads per `intervene/mcp_observations.py:11` | R09 tiers T5, T6 | Inspection of the migrated holders | Deferred to plan creation |
| F03 | DuckDB connections at four sites take library defaults: machine time zone, 80 percent of memory, all threads, a working-directory-relative spill path; the settings meant to govern them are unread | DP-11, DP-20 | `serve/companion_export.py:410, 552`; `semantic/artifact_identity.py:481, 579`; library defaults probed by the library contributor ([DuckDB report](../evidence/2026-11-18_production-review-inputs/library-duckdb.md) §E) | R12 | Inspection of connection configuration | Deferred to plan creation |
| F04 | Application code writes SQLite SQL by concatenation, including field names in JSON paths, in five modules, outside any decision about SQL text | FP-02; operator concern | `semantic/data_operation_read_index.py:20–27, 66–74` and four further modules (audit fact under DA-084) | R07 | Inspection of the converted stores | Deferred to plan creation; rule impact RC02 |
| F05 | The released model cannot say whether a vocabulary is closed, pack-extensible or open. The earlier model declares it per enum (`Lifecycle`: `static` or `schema_version`) and its pack loader enforces it; the released vocabulary expansion and preparation carry no such property, so every released enum is closed in validation and pack extension of a shared set is neither declared nor refused. R13 would retire the only representation of this intended distinction (added by the recommendation audit) | FP-04/A2 (model adequacy) | `model/core.yaml:1034–1040, 895, 913`; `schema/pack.py:1–22`; `semantic/ontology.py:328–410`; `semantic/prepare.py:480–530` | R15, R13 | Each released enum declares its openness and preparation enforces it; no openness rule remains only in the earlier model | Deferred to plan creation |

## 10. Library fit, verdicts and probes

**Selected mechanisms** (each also named in its recommendation): LinkML `SchemaView` composition, enums with
structured annotations, `linkml.validator.Validator` with the closed JSON Schema plugin (R01, R02, R03);
LinkML `recommended` slots with `RecommendedSlotsPlugin` warnings, `status` on permissible values, and `any_of` an
enum and `string` for open vocabularies (R02, R15; observed in installed 1.12.1 source by the recommendation
auditor, 2026-11-18);
SQLAlchemy `MetaData`, Core, `CreateTable`, `Table.to_metadata` (R04, R07); pglast AST nodes including
`CreateTrigStmt` and `ViewStmt` (R04); pyarrow schemas and safe casts (R12); DuckDB relational and expression API
(R12); cachetools 8.0.1 `LRUCache`, `cached` with `condition`, `cachetools.func.lru_cache`, `keys.hashkey`
(R09); standard-library `ast` and `importlib.metadata` (R05); networkx topological sort (R04).

**Do not adopt**, with reasons:

- LinkML SQL, SQLAlchemy and Pydantic generators for the physical model: they honour three annotations and no
  PostgreSQL schemas, checks, triggers or grants (probed, [data-model library report](../evidence/2026-11-18_production-review-inputs/library-data-model.md) F10); the project compiler stays.
- linkml-map for retiring the earlier model: the problem is duplicated schema, not data to move; its SQL backend
  drops expressions silently (documented).
- linkml-datalog, pySHACL or an RDF store for support closure and change impact: alpha or open-world, no consumer
  needs RDF.
- Subclassing LinkML's `Generator` for output governance: it is a single-output visitor; the project's registry
  with an ownership check is the right owner.
- valuesets as a runtime import: vendored YAML capture is sufficient.
- DuckDB `ATTACH` to PostgreSQL: separate credentials and snapshot; text through `postgres_query`.
- DuckPGQ: research extension; SQL text; 2.0.0 binary unconfirmed.
- `duckdb-engine` for SQLAlchemy over DuckDB: predates 2.0.
- diskcache, asyncache, pickled cache persistence, a CLI daemon now, TTL expiry for content-identified results
  (reasons in [cache-design.md §6](unified-domain-model-and-execution/cache-design.md#6-crossing-processes)).
- A generic dependency-tracking cache framework: identity keys suffice.

<a id="probes"></a>

**Probes run by this reviewer** (synthetic data only, scratch directory outside the repository, 2026-11-18):

1. cachetools 8.0.1 from the downloaded sdist under CPython 3.14.10: nine threads over two keys with
   `cached(LRUCache(16), condition=Condition(RLock()), info=True)` ran the loader twice,
   `CacheInfo(hits=7, misses=2, maxsize=16, currsize=2)`; four threads calling a raising loader under
   `condition` ran it four times in 0.20 s (no shared exception); `cache_clear()` during an in-flight load was
   followed by the load's insert (`{(1,): 'old'}`); an `LRUCache` subclass's `__delitem__` saw both eviction and
   `pop` (`[1, 2]`) while `clear()` bypassed it.
2. DuckDB 2.0.0 with pyarrow 26.0.0 (project virtual environment, read-only use): projecting a missing column
   raised `BinderException` at relation construction; `union` returned six rows for three plus three
   (bag semantics) and two after `distinct()`; `columns` and `types` were available without executing.

Other library facts come from the contributor reports, labelled there.

## 11. Alternatives and tradeoffs

| Alternative | Change propagation | Semantic authority and composition | Total machinery and risk | Decision |
|---|---|---|---|---|
| Current baseline | Multi-site edits for families, roles, guards, programs; unrelated edits invalidate kernel, release and receipts | Hand lists beside a sound compiled operation model | No new machinery; fail-open omissions; repeated generation on the execution path | Not retained |
| Proposed design | Local: one declaration per governing fact; identity changes follow bytes and declared dependencies | Five authority kinds with supported derivations; one composer | New: declaration schema, profile check, program registry, derived code identity, cache owner and store (each small); removes more than it adds | Selected |
| Library-maximal variant (LinkML for operations and programs too; LinkML SQL generators) | Similar for domain facts | Pushes procedural and code facts into a schema language (ADR-0131's rejected option 2) | Larger and lossier; generators lack PostgreSQL features | Rejected |
| Simplest viable variant (transcribe nothing new; add completeness tests to the hand lists; hold the capture) | Still multi-site | Lists stay authorities | Least new code; tests mirror the lists and cannot refuse an inconsistency at compile | Rejected for A2; acceptable only as an interim guard |
| Required total classification (this review's first round: every operation declares a family with explicit `none`; closed vocabularies throughout; absence refuses) | Local | Removes the fail-open state but conflates "not applicable" and "not yet decided" by forcing a choice; closes descriptive fields that are open today | Small, but every new operation must decide its validity semantics before compiling, and an operation in two families needs a schema change | Not selected (recommendation audit, 2026-11-18) |
| Declared homes with explicit openness and safe defaults (selected) | Local | Integrity memberships closed; operation classifications three-state; vocabularies declare openness | Adds one conservative validator program and an openness declaration; removes two would-be mandatory fields | Selected |

What becomes easier: adding operations, families, roles and fields; trying operations and vocabulary terms before
they are settled; library bumps; previews; CLI paging. What becomes harder: the first conversion step (the facts each
module reads get their declared home before its programs), and unclassified operations pay for conservative
re-validation until they are classified.

## 12. Verification and uncertainty

| Claim | Label and date | How it would be settled |
|---|---|---|
| Family is not derivable from compiled fields | Interface-checked by source inspection, 2026-11-18 (all 27 literals extracted statically) | Already settled for the current set |
| The per-acquisition check can use the release's recorded kernel identity | Interface-checked, 2026-11-18 | A traced acquisition after R06 |
| Identical bytes after a library patch imply unchanged behavior of installed programs | Proposed (reasoning: installed behavior is the installed bytes) | — |
| Derived code identity covers what hand lists covered | Proposed | Compare the derived closure with `LOWERING_FILES` and the query custody lists once; the two known omissions must appear |
| Continuation pages are sound across processes keyed by cut | Proposed, from the in-process soundness argument | Native owner review of the cut's pins |
| Content basis for fresh requests | Open premise (DA-075) | Native owner's argument that derived rows depend only on frontier content |
| Role-granular watermark | Open premise (DA-078) | Native owner's soundness argument |
| Carrying release-content proof | Open trust decision (DA-033) | Operator decision |
| Materiality of each removed repetition | Unmeasured by design | Measure only if a plan step depends on the size |
| A conservative premise check can be realized for unclassified operations from recorded trust snapshots and validator identities | Proposed (recommendation audit; premises partly recorded, `data-operation-physical.yaml:458–484, 619–631`) | Native owner's confirmation that each episode can be tied to the trust snapshot it consumed |
| LinkML 1.12.1 has no openness flag on enums; `recommended` slots warn through `RecommendedSlotsPlugin`; permissible values carry `status` | Observed in installed source, 2026-11-18 (recommendation audit) | — |

**What would change the judgment.** If the conservative premise check proves unrealizable, unclassified operations
must at least lose reuse across premise changes, or classification becomes required for operations that consume
trust-bearing cuts. If family membership proves derivable from declared input roles, it is derived and the field
becomes an override. If no operation ever needs two families, the set-valued field can be simplified. Evidence that generated bytes depend on ambient state not captured in the generation
key (would require adding it to T2's key). A finding that the effective-model archive's SQL readers depend on field
names that LinkML generation would change (would slow the declaration-schema step, not reverse it).

**Unexamined breadth, not defects.** Generator bodies for equivalence; `schema/rulelang.py`; the ontology path;
migration bodies; the CLI beyond paging.

## 13. Rule impacts

The review does not change these rules; plan creation presents them for confirmation.

| ID | Rule and where recorded | Proposed change | Depends on it | If the rule is kept |
|---|---|---|---|---|
| review#RC01 | ADR-0131 and §B4/§B5: typed programs compose procedural forms; three exceptions | Add: facts that programs dispatch on have one declared home and programs read it instead of restating it; an undecided membership is declared as undetermined and programs apply its stated conservative consequence; generation refuses only internal inconsistency (a name without a definition, a dispatch without a handler) and omissions in the integrity layer (roles, grants, guards, support-edge kinds); independent controls take expectations as data, never spliced text; each module's conversion follows the declarations it reads (revised by the recommendation audit) | R02, R07, R16 | The remaining conversion transcribes the family and role lists again |
| review#RC02 | ADR-0131's scope is PostgreSQL only | Extend "no maintained SQL text in application code" to SQLite scratch stores and DuckDB use | R07, F04 | SQLite text remains an accepted, low-risk exception |
| review#RC03 | §B5 "one captured LinkML closure" with per-artifact closures | One composer and one compiled model per model-sources identity; per-artifact sub-identities kept | R01 | Per-consumer composition continues |
| review#RC04 | ADR-0092: two operation authoring routes compiled into one model | Keep both routes; add that the Python route's grammar and vocabularies are declared in LinkML, that each vocabulary declares its openness, that descriptive fields stay open, and that literals are validated against the declaration with closed field names | R02, R15 | Hand grammar validator remains; vocabularies stay Python literals |
| review#RC05 | DDO plan, products and support: `validity_family` null when no per-kind validator applies (`products-and-support.md:422–423, 451`) | Null stops meaning "no per-kind validator applies"; that meaning is declared as `none`; absence means undetermined and receives conservative validity; the field may hold several families (revised by the recommendation audit; replaces "required enum with explicit `none`") | R02, R16 | Forgotten and not-applicable stay indistinguishable and permissive; A2 MUST gap stays |
| review#RC06 | DDO plan: completion seal and receipts keyed by the kernel digest; full battery on mismatch (`products-and-support.md:428, 528, 534`) | Validator identity per family; recorded reconfirmation | R05, R11 | Replay amplification after any captured edit remains |
| review#RC07 | DDO plan: watermark over prerequisite operations and exact pins (`products-and-support.md:574–575`) | Drop the kernel component now; role granularity after the soundness argument | R10 | Waiting-obligation skip stays largely unrealized for the one-source workload |
| review#RC08 | Admission re-proves release content per acquisition (current native admission design; DA-029 trust premise) | Carry finalization and deployment-admission receipts; explicit verification command | R11 | Per-acquisition re-hashing of immutable content remains |
| review#RC09 | ADR-0124 and file custody: drift refuses and requires restart | Keep for Python code; for model declarations, a changed source yields a new compiled model | R01, R09 | Model edits require restarting the MCP server |
| review#RC10 | ADR-0124: serving identity names the listed running code | Derived import closure under the same custody mechanism | R05 | DA-076 stays |
| review#RC11 | Release id hashes generator sources and the whole native capture (`semantic/prepare.py:956–985`; native capture as dependencies) | Generated artifacts and model capture in the id; generator provenance recorded beside | R05 | Generator edits force new releases |
| review#RC12 | Role constants and default read roles in code (`semantic/alembic_privileges.py:25–35`); host bootstrap reads them | Role and purpose vocabularies in the model; read roles declared per schema with per-relation overrides, no code default | R02, R03 | Privilege policy keeps no model owner |
| review#RC13 | Production-efficiency realization of the query cache (process-local, keyed by cut; PE-F17, owned by the DDO plan) | Declared reuse basis; disk tier for CLI continuation | R09, R10 | CLI paging never reuses |
| review#RC14 | ADR-0024 and the D2 preparation contract: unsupported required semantics refuse; preparation diagnostics are refusing except unchecked terms | Add: preparation distinguishes refusing diagnostics (unsupported or inconsistent semantics, integrity omissions) from non-refusing `unassessed` diagnostics for undetermined declarations, and records the promotion boundary, if any, at which undetermined declarations refuse (none, default-release activation or knowledge publication; the operator chooses) (added by the recommendation audit) | R15, R16 | R16 still works through the existing `unchecked` route, but the promotion boundary stays undecided |

Not a rule change: moving cachetools from 7.2.7 to 8.0.1 is ordinary dependency judgment (it changes the served
identity once). Deleting `semantic_alembic/` and `alembic/` needs the operator's decision; the rule protecting plans
and evidence does not name migration trees.

## 14. Order of work

Priority by consequence: the fail-open validity families and the stale-code reuse across processes (correctness and
fidelity) first; then execution-path amplification; then cache reuse.

Prerequisite order by the capability each step supplies:

1. **Compiled model holder and cache owner (R01, part of R09).** Supplies the one object that every later
   derivation reads. Includes the cachetools 8.0.1 move.
2. **Declared homes and openness (R02, R03, R15, R16).** Supplies the three-state family declaration with its
   conservative validator, edge kinds, roles, purposes, guard and read-role defaults, and vocabulary openness. Needs
   step 1. The ownership vocabulary, the grammar migration and derived source collections belong here but do not
   gate step 5.
3. **Program registry and typed trigger and view forms (R04).** Supplies program objects with identities. Needs step
   1; independent of step 2.
4. **Identity layering and code custody (R05).** Needs step 3 for program identities.
5. **Remaining PostgreSQL conversion (R07) and the single support walk (R08).** Each module needs the step-2 facts it
   reads and step 3; this is the ordering the open conversion must respect.
6. **Carried assurance (R11).** Needs step 4 for validator identity and the operator's trust decision.
7. **Disk tiers and served reuse basis (R09, R10).** The content basis needs the native owner's premise.

Can proceed independently now: R06 (the execution path stops generating; small and high value); continuation-page
reuse for the CLI (cut-keyed); bounding and locking the unbounded and unlocked holders (F02); DuckDB connection
settings (F03); the retirements of R13 that need no decision and do not touch the earlier model's openness rule; R14.

**Test seams (one line each).** Tests importing the `semantic.metadata` globals move to the accessor; native
authoring fixtures move to the program registry; family dispatch, the three family states and the conservative
validator need independent tests, which the test review owns; deployment-key tests change if release dependencies change (R05).

## 15. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence | Action |
|---|---|---|---|
| A1 Localize change | Violated | Adding an operation, a family, a role, or editing a generator propagates across unrelated owners (§7) | R02, R04, R05 |
| A2 Encode domain meaning explicitly | Violated | Governing facts without model authority; an unlisted member fails open; "not applicable" and "not yet classified" share one representation; vocabulary openness is declared only in the retiring model; the earlier model duplicates value sets | R02, R03, R08, R13, R15, R16 |
| A3 Extend through composition | Violated | A new program or family needs three to five registry edits; each consumer composes its own model | R01, R04 |
| A4 Fit execution to the workload | Violated | Generation on the execution path; invalidation far broader than premise; no CLI reuse; no coalescing of identical misses | R05, R06, R09, R10 |

**Bounded decision: Revise.** **Enclosing architecture: needs revision**, around the preserved core named in §2.
Evidence strength: Interface-checked by source inspection, 2026-11-18; remedies Proposed. Review acceptance is
distinct from release qualification.

**Next decision and owner.** The operator confirms or rejects RC01 to RC14 in plan creation, including the promotion
boundary of RC14 and whether `Ownership` stays open; the first plan step is R06 alongside R01, with the declared
homes of the facts each conversion module reads (R02, R16) as the decision that gates the remaining conversion.

## 16. Returned to the audit (out of focus)

- DA-079 (typed busy refusal for a second concurrent run) is outside this focus; it stands as recorded.
- `schema/rulelang.py`, the packs' custom rule language, was not examined; whether it should become LinkML `rules`
  or stay is open.
- `ingest/pdf_stream_reconciliation.py:260–261`: `pin_json` duplicates `input_key` (a defect noted by the generator
  lane).
- `serve/source_catalog.py:117–129`: one native read per catalog row (N+1).
- `ingest/pdf_capacity.py:19–20`: sticky GPU quarantine globals with no clearing route.
- `serve/companion_export.py:582–600`: unbounded materialization of export differences.

---

## Coordinator publication note — 2026-11-18

The coordinator, who wrote the audit this review consumes, prepared the brief, the pinned
snapshot and the contributor reports now published as
[review inputs](../evidence/2026-11-18_production-review-inputs/README.md), and did not write
the review. The brief first described the model-owned SQL conversion as complete; the
independent challenge of the audit refresh corrected that, and the reviewer received the
correction before finishing. Before placing the review the coordinator checked the decisive
lines of finding F01 against the snapshot (`semantic/data_operation_storage.py:1116–1131`,
`:1069–1070`; `model/semantic/data-operation-physical.yaml:22`); they match. The review text
above is the reviewer's; only link targets were changed for placement.

**Reconciliation at publication.** `main` was at `90467bde0`, five commits after the baseline
`d78c98765`. None of them changes a file under the production package, so every source
citation above is as read. Uncommitted work by other sessions was not read.
