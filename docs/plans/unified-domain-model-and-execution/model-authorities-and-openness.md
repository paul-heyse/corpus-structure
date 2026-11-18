# Model authorities and openness: the compiled model, the declaration grammar, integrity vocabularies and the earlier model's retirement

**Status:** Not started.
**Created:** 2026-11-19. Writing this plan authorizes no implementation.

This companion owns the designs of **UDM-01** (one composer and one held compiled model),
**UDM-02** (the operation declaration grammar and its vocabularies in LinkML, each stating its
openness), **UDM-03** (role and purpose vocabularies, the typed physical profile with declared
per-schema defaults, and grants from program declarations) and **UDM-04** (retirement of the
earlier core and system model). It contributes to findings
[DA-085](../../design_review/audit/semantic-model-and-authority.md#da-085),
[DA-004](../../design_review/audit/semantic-model-and-authority.md#da-004),
[DA-086](../../design_review/audit/semantic-model-and-authority.md#da-086),
[DA-074](../../design_review/audit/native-integrity.md#da-074),
[DA-072](../../design_review/audit/semantic-model-and-authority.md#da-072) and review finding F05,
and it depends on rule impacts RC03, RC04, RC09, RC12 and RC14, which the operator accepted as
revised on 2026-11-19 and whose required content is stated under
[What this supersedes](#what-this-supersedes). Package state, the queue, finding dispositions, the
shared contracts (**fact authority**, **compiled model**, **declared openness**, **lowered
operation attribute**, **conservative validity**, **program declaration**, **the flexibility
frame**) and the decision records of UDM-00 are the
[coordinator's](../unified-domain-model-and-execution_2026-11-19.md). This document uses those
names and does not redefine them. Terms of the system that are not defined here at first use
(the kernel, a native revision, the frontier guard, a release) are in the coordinator's
[glossary](../unified-domain-model-and-execution_2026-11-19.md#glossary).

**Baseline and evidence.** Section references such as R02 or §3.2 mean the
[design review of 2026-11-18](../../design_review/reviews/design_review_unified-domain-model-and-execution_2026-11-18.md)
as revised at `5139eaba3`, and "the recommendation audit" means its
[companion on intentional flexibility](../../design_review/reviews/audits/design_review_unified-domain-model-and-execution_2026-11-18_audit.md).
The plan was authored against commit `cb4e09667` (the authoring baseline; its production source
is identical to `5139eaba3`). Source facts are **Interface-checked by source inspection,
2026-11-19** at that commit, and line citations are to it. LinkML facts were observed in the
installed linkml 1.12.1 source by the investigation named below. Nothing was run. Every design
statement is **Proposed**. No speedup is claimed. The investigations this companion draws on are
the [lowering and declaration advice](../../design_review/evidence/2026-11-19_udm-plan-authoring/lowering.md)
(compiled model, grammar, vocabularies, roles and purposes, supersession) and the
[cache and retirement map](../../design_review/evidence/2026-11-19_udm-plan-authoring/caches.md)
(the earlier model's importers and the model-change preview). `src/…` and `tests/…` are relative
to `python/corpus-structure/`. Every other bare path, a module such as `semantic/prepare.py` or
a model file such as `model/semantic/physical.yaml`, is relative to `src/corpus_structure/`.

Where an investigation corrects the review, the investigation governs. Three corrections apply
here. The `preparation` description is open with known members, not unconstrained: kernels test
three of its values. The earlier model has 56 importing modules, not 39 or 41, and the
model-change preview is built on it. The purpose-to-role map is written four times, not twice.

## Why this work exists

The system's domain model is LinkML, and PostgreSQL programs, relational metadata, wire
validators and Python types are derived from it. Four things stand between that statement and
the code.

1. **Nobody holds the model once.** Each consumer composes its own view of the LinkML sources,
   and the relational metadata is compiled at import in every process. A candidate model cannot
   sit beside the running one, a model edit needs a restart, and facts that span two views have
   no object to live on, which is one reason membership facts fell back to Python lists.
2. **The operation declaration grammar is a hand validator.** The Python authoring route writes
   an operation as a literal beside its callable. What fields the literal may have, and which
   values its closed fields take, is known only to a 2,622-line module that interleaves
   structural checks with compilation. The vocabularies those fields draw on are Python sets, so
   neither SQL checks nor generators can read them from the model.
3. **Integrity memberships have no model owner.** Role names, the mapping from a caller's
   purpose to a role, default read roles and the list of write-guarded relations are literals
   repeated across modules. The privilege decision record says grants are declared; a default in
   code supplies them.
4. **A second, older model is still live.** It is the only place that declares whether a
   vocabulary may be extended by packs, and 56 modules import it.

The work is ordered so that each package supplies the capability the next one reads. UDM-01
supplies the one object. UDM-02 puts the grammar and vocabularies on it, with each vocabulary
saying how open it is. UDM-03 puts the integrity memberships there, closed and complete. UDM-04
removes the earlier model once the openness distinction has a home in the released model. The
[lowered operation facts companion](lowered-operation-facts-and-validity.md) then reads the
vocabulary table to generate dispatch (UDM-05 to UDM-07), the
[programs and identity companion](programs-identity-and-revisions.md) reads the compiled model to
build the program registry (UDM-09), and the [cache companion](cache-system.md) owns the tier
that holds the compiled model (UDM-13).

## Baseline at `cb4e09667`

### Composition

There are sixteen `SchemaView(` constructions in eleven modules. (The investigation's headline
says seventeen; its own enumeration, and a search of the snapshot, give sixteen. UDM-01's first
step re-counts.) Three are near-identical closure routines that seed an import map, merge
imports and build a second view (`semantic/prepare.py:362–374`,
`semantic/native_call_sources.py:111–117`, `semantic/projection_analysis_products.py:98–107`).
One is the physical closure (`schema/physical.py:166–197`). Seven are single-purpose views
(`semantic/companion_projection.py:552` from a disk path, `semantic/rule_views.py:402`,
`semantic/conditional_rules.py:178`, `semantic/ontology.py:159, 260, 626`,
`semantic/source_value_native.py:56`). Two belong to the earlier model (`schema/model.py:235`,
`schema/pack.py:232`).

The relational compiler `compile_physical` is called at fifteen sites outside
`schema/relational.py`: `semantic/metadata.py:33, 46`; `semantic/data_operation_storage.py:137,
1877`; `semantic/data_operation_projections.py:2745`; `semantic/data_operation_source_native.py:30`;
`semantic/companion_projection.py:587`; `semantic/pdf_lowering.py:193`;
`semantic/pdf_record_model.py:86`; `semantic/pdf_publication_native.py:460`;
`semantic/projection_analysis_products.py:141`; `semantic/authored_sql.py:350`;
`schema/model_change.py:505, 689, 1096`. `semantic/metadata.py:32–51` compiles the physical and
the read metadata as module globals at import, and 63 modules import it (the cache companion
counts 64 files; re-counted at entry). The companion
projection added a content-keyed holder for its own captured sources
(`semantic/companion_projection.py:561–617`); its key is sound and it is a fourth per-consumer
composition. The preparation closure already refuses an import that was not supplied, so there
is no filesystem fallback to preserve (`semantic/prepare.py:355–359`). Release annotations under
the `cs:` prefix are decoded from raw strings at 36 consumer sites (DA-004).

Two further restatements of declared facts belong with composition (DA-086). Four maps restate
the database and Python type of each field kind (`semantic/native_call_contracts.py:16–25`;
`semantic/native_call_sources.py:28–37, 133–136`; `semantic/pdf_search_native.py:98–104`;
`semantic/native_program.py:621–622`), which the physical compiler already resolves from the
LinkML type and `ph:sql_type` (`schema/relational.py:79–89, 437–440`). The companion export
writes its grouping and provenance columns as literals (`serve/companion_export.py:419–424,
557–589`) beside the `cp:` annotations that the companion projection reads.

### The hand grammar and its vocabularies

Operation literals are `__data_operation__` assignments in 62 modules. The grammar is in
`semantic/data_operation_compilation.py`. Its structural part is: `_PROFILES` (`:85`),
`_BINDING_OPERATORS` (`:86–103`), `_METADATA_FIELDS` (`:104–140`) checked by `_mapping` at
`:1068` with the profile test at `:1072–1073`; the helpers `_mapping`, `_strings` and `_text`
(`:166–188`) with literal field-name sets passed at 30 call sites; `_KIND_UNIVERSES` (`:341`) and
`_PROJECTION_FAMILIES` (`:342`); the role direction test (`:1102`); forms (`:1491–1493`); and
three free-text descriptions, `preparation`, `cancellation` and `ownership` (`:1561–1563`). Its
semantic part resolves role kinds (`:1099–1101`), validates binding fields, checks
stream-settlement consistency (`:1494–1516`) and transition mappings (`:1460–1478`), refuses
duplicate identities and resolves captured methods (`:1518–1547`). The compiled dataclasses
already type `forms` and `profile` as `Literal` (`semantic/data_operation_model.py:290, 497`).
`compile_data_operations` (`semantic/data_operation_compilation.py:806–814`) returns only the
effective model: it can refuse, through `PreparationError`, and has no way to report without
refusing.

The free-text descriptions are not all equally free. Consumers test `ownership` for the value
`immutable` only (`semantic/characterization_ports.py:1059`, `semantic/sentence_products.py:1403`,
`semantic/formal_products.py:986`). Kernels test `preparation` for `pdf-native`
(`semantic/pdf_completion_native.py:138`), `resource`
(`semantic/contextual_admission_native.py:254`, `semantic/definition_admission_native.py:364`)
and `native-publication` (`semantic/structural_admission_native.py:826`). No tester of
`cancellation` was found.

### Openness lives only in the earlier model

The earlier model declares per enum whether a set changes only with code or may be extended by
packs: the `Lifecycle` values `static` and `schema_version` (`model/core.yaml:1034–1040`), with
`ci:lifecycle` annotations at 72 places under `model/`. Its pack loader enforces the rule: a pack
enum may extend a core set only when that set is declared `schema_version`
(`schema/pack.py:1–22`, enforced at `:438–449`). The released model has no successor. Its value-set
expansion composes `inherits`, `include`, `minus`, `concepts` and ontology `reachable_from`
members without an openness property (`semantic/ontology.py:328`), and the preparation profile
refuses any annotation outside its safe list (`semantic/prepare.py:259`). Preparation does record
vocabulary terms it could not check as non-refusing diagnostics and snapshots vocabulary rows per
release (`semantic/prepare.py:485–531`), and the validation report maps `unchecked`, `unsupported`
and `unresolved` outcomes to the category `unassessed` (`semantic/operation_reporting.py:372–377`).

### Roles, purposes and the physical profile

There are 198 `"corpus_sem_*"` literals in 46 modules. The constants are at
`semantic/alembic_privileges.py:24–33` (`PUBLISHER`, `DEFAULT_READ_ROLES`, `PURPOSE_ROLES`);
they are restated as tuples at `semantic/native_admission_tables.py:27–32` and as a JSON default
at `:176–184`, and `semantic/native_admission_principals.py:8–16` lists principals, application
schemas and private kernels. The purpose-to-role map is written four times: for execute grants
(`semantic/data_operation_storage.py:1899–1907`), in the closure kernel without `fit`
(`semantic/closure_native.py:174–181`), in the runtime with `maintenance` mapped to no role
(`semantic/runtime.py:34–40`) and as `PURPOSE_ROLES`. Five programs receive execute grants by
name (`semantic/data_operation_storage.py:1908–1927`). Public native operations already declare
their purposes in the protocol (`model/semantic/data-operation-native.yaml:2810–2870`).

Physical schemas are LinkML subsets with empty bodies (`model/semantic/physical.yaml:18–23`),
and the schema set is written again as a code literal at `schema/relational.py:413, 430`,
`semantic/closure_native.py:130` and `semantic/native_admission_principals.py:10`. Eighty-four
relations declare `ph:read_roles: '[]'`; a relation that declares nothing receives
`DEFAULT_READ_ROLES` from code (`semantic/alembic_privileges.py:75`). The write guard (the
frontier guard) is applied to twelve relations named in a tuple
(`semantic/data_operation_storage.py:1952–1965`). Physical annotations that hold structure (`ph:foreign_keys`, `ph:checks`, `ph:indexes`) are JSON
strings decoded in the relational compiler. Effect authorizations spell the evaluator purpose
`native-purpose:evaluator` at five sites while the purpose vocabulary says `evaluate`.

### The earlier model's consumers

The earlier model is `model/core.yaml` (1,096 lines), `model/system.yaml` (2,023) and
`model/revisions.yaml` (1,118), loaded by `schema/model.py:235`, with `core/vocab.py`,
`core/_model/*`, parts of `core/keys.py`, and `schema/change.py`, `schema/pack.py`,
`schema/lookup.py` and `schema/model.py`. The cache and retirement map counts importers per
module (`core/vocab.py`: 40 source and 37 test files; `core/_model`: 11 and 5; `core/keys.py`: 5
and 8; `schema/change.py`: 2 and 2; `schema/pack.py`: 3 and 14; `schema/lookup.py`: none and 2;
`schema/model.py`: 16 and 38), 56 importing source modules in all, re-counted at entry. The generated native facade
emits an import of `core.vocab.TaskUnitType` (`semantic/native_call_generation.py:106`). The
model-change preview is built on the earlier model: it writes the two canonical declarations and
the revision log to a temporary directory, loads both sides with `model.load`, and computes the
change with `change.diff` (`schema/model_change.py:622–636`). Its change records carry an
`alembic_revision` field, and the preview refuses a native change unless the change record or
the request names a revision (`:651–660`), so the earlier model also gates native authoring.

## Target design

### The compiled model

**Proposed.** One composer function takes a *capture*, meaning the named source bytes of LinkML
schemas, the pinned `linkml:types`, the native protocol and the catalogs, and returns an
immutable compiled model. Nothing else composes. The capture's identity is a framed digest over
its sorted name and content-digest pairs, the framing the physical sources identity already uses,
and the cache tier that holds compiled models (owned by UDM-13) is keyed by it. The running
package model is one capture, read once through file custody. A candidate under preview, the PDF
domain contract's captured sources and a release bundle are other captures and therefore other
entries.

The object exposes *projections*, each derived on first use, held on the object, and carrying
its own sub-identity so that custody keeps today's granularity (the physical sources identity
remains the identity of the physical projection). The projections are: the merged view for each
root (`physical.yaml`, `read-projections.yaml`, the release bundle root, the operation-calls
root); the physical and read relational metadata, produced by `schema/relational.py` unchanged;
expanded value sets through the project's one `expand_enum`; typed annotation access, so that a
boolean annotation is read as a boolean and a case policy as its enumeration in one place
(DA-004); the type resolution for field kinds, which gives each kind its database and Python
type from the resolution the physical compiler already performs; the companion's grouping and
provenance columns, read from the `cp:` annotations; the declaration validator and the
vocabulary table (UDM-02); the role and grant matrix (UDM-03); and the support-edge table
(UDM-07).

Consumers change from building to asking. The reasoning for one object rather than a shared
helper function is that facts spanning two projections (a purpose that names its role; a
relation that names its read roles) need one place where both sides are known to come from
the same sources. The reasoning for laziness is that a command that needs only relational
metadata should not pay for a JSON Schema it never uses.

*Preserved:* generated bytes, the refusal of an unsupplied import, per-artifact custody
identities. *Deliberately changed:* a changed model source yields a new compiled model on next
use instead of a refusal that demands a restart (RC09); Python code drift still refuses.
*Rejected:* keeping per-consumer composition (every new consumer adds a closure and cross-view
facts have no home); a single eager module global, which is today's `metadata.py` (every command
pays, and a candidate cannot coexist); a materialized derived schema file as the one artifact
(useful later as a disk form, but each consumer would still compose its projections).
*Reopens the choice:* if execution shows the lazy physical projection is the dominant cost of
short commands, a materialized form on disk becomes worth its invalidation rule; that measurement
would settle whether a disk tier is added, and nothing else.

### Vocabularies that state their openness

**Proposed.** One LinkML module of enumerations only holds the vocabularies of the operation
grammar and of the integrity layer. The declaration schema imports it, and so does the physical
closure for the members SQL checks need, so the compiled model sees one definition of each.
Each enumeration carries an openness annotation, the successor of `ci:lifecycle`, with one of
three values defined by the shared contract **declared openness**: `closed`, `pack-extensible`,
or `open` (open with known members).

| Vocabulary | Openness | Why |
|---|---|---|
| `Profile`, `KindUniverse`, `Form`, `BindingOperator`, `ProjectionFamily`, `RoleDirection` | closed | each drives compilation; the members are today's Python sets |
| `ValidityFamily` | closed; members may be provisional | programs dispatch on it (UDM-05); seven members today |
| `SupportEdgeKind` | closed | validity, revocation and lock scope must know every kind (UDM-07) |
| `Purpose`, `Role` | closed | integrity memberships (UDM-03) |
| `Ownership` | open with known members | the known members are the values in use today: `immutable`, the only one a consumer tests, and the others as provisional members with no meaning attached, so only a new term is reported |
| `Preparation` | open with known members | known members `pdf-native`, `resource`, `native-publication`, which kernels test |
| `Cancellation` | unconstrained text, no enumeration | no consumer interprets it |

The representation follows what LinkML 1.12.1 offers. A slot whose vocabulary is closed takes the
enumeration as its range. A slot whose vocabulary is open takes a range of `any_of` the
enumeration and `string`, so any value validates and only known members carry meaning. A
provisional member uses the `status` slot every permissible value already has. A declaration
that should be made when known and may be absent uses `recommended: true`.

One consistency check runs when a model is prepared. It is a check of internal consistency
inside preparation, not a lint, and it adds nothing to `ci check`: an `open` enumeration used as a plain range refuses, because the declaration and the
validation would disagree; a `closed` enumeration inside `any_of` with `string` refuses for the
same reason; a pack schema that extends a `closed` enumeration through `inherits` or `include`
refuses, which is the rule `schema/pack.py` enforces today, moved to the released model. A
`pack-extensible` enumeration's pack members become per-release vocabulary rows, as preparation
already snapshots them.

The design principle is that the model checks only what a consumer interprets. `Cancellation`
has no interpreter, so declaring members for it would be a constraint with no beneficiary. If a
kernel or a consumer later tests a cancellation value, that value becomes a known member of an
open vocabulary, with no change to any literal.

### The declaration class and its validator

**Proposed.** A LinkML class `DataOperationDeclaration` has one slot per entry of
`_METADATA_FIELDS`, with nested classes for roles, coverage, capabilities, effects and binding
nodes. Field names are closed at every nested record, as they are today. Ranges come from the
vocabulary module. The class also declares the new optional `validity_family` slot, whose
meaning and lowering are owned by UDM-05; this companion supplies the slot, its range and the
structural diagnostic for its absence, and nothing about what programs do with it.

Operation literals stay in Python, beside their callables, which is the route ADR-0092 accepts.
What changes is who checks them. The compiled model holds one LinkML validator, built once per
compiled model, with the closed JSON Schema plugin and the recommended-slots plugin. Each literal
is validated against the declaration class before the semantic pass. Errors map to the refusing
outcome `invalid`, as today. Warnings, which the recommended-slots plugin produces for an absent
recommended declaration, map to the non-refusing outcome `unchecked`.

The semantic pass stays a compiler pass, because its checks span records: role-kind resolution,
binding-field validation, stream-settlement consistency, transition mappings, duplicate
identities and captured-method resolution. Operator-specific binding-expression shapes stay
there too. LinkML `rules` could express some of them later; nothing here requires it.

`compile_data_operations` gains a diagnostics return beside the effective model. Preparation
appends those diagnostics to the prepared release's diagnostics (`semantic/prepare.py:1361`),
and they surface in the preparation validation report under the category `unassessed`, with the
report marked incomplete, through the mapping that already exists. Two kinds of non-refusing
diagnostic use this route. The first is `ownership_unknown_term` (and its `preparation`
counterpart) for a value of an open vocabulary outside its known members. The second is the
structural diagnostic for an absent `validity_family`: the recommended-slot warning is
reported once, under the code `validity_undetermined` and with the consequence text that
[UDM-06](lowered-operation-facts-and-validity.md#the-diagnostic-and-where-the-operator-sees-it)
states. One absent declaration produces that one diagnostic; UDM-05 switches it on, and UDM-06
refers to it and adds no second one for it. UDM-06 uses the same route for the cases the grammar
cannot see, among them its own non-refusing report `validity_claim_unprotected`, for an operation
that declares `none` while consuming an input a family protects. This is RC14: preparation distinguishes refusing diagnostics from
non-refusing ones, and the operator has decided there is no promotion boundary at which an
undetermined declaration refuses.

The compiled dataclasses keep `Literal` fields for the closed vocabularies and check them against
the enumeration members at import, the pattern `semantic/source_value_native.py:55–66` already
uses. The purpose sets in `semantic/data_operation_wire.py:288` and `semantic/runtime.py:14`
become checked copies of the same kind. An open vocabulary's field stays a string.

*Rejected:* a pydantic-authored metamodel, which is lighter for the structural grammar alone but
loses on the vocabularies, since SQL and generators read families, edge kinds, roles and purposes
from the model (the operator chose LinkML for both); annotations on schema elements, which are
wrong for operations because operations are instances, not schema elements; a closed `Ownership`
enumeration, which would require a vocabulary edit before an experimental operation could
describe its resource behaviour. *Reopens the choice:* if LinkML validation of the 62 real
modules cannot reproduce a refusal the hand validator gives today, that field's check stays in
the compiler pass and the plan records which and why.

### Integrity vocabularies and the typed physical profile

**Proposed.** `Role` is a closed vocabulary whose members carry structured annotations for
whether the role can log in, which roles it is a member of, and whether it is the owner (the
publisher). `Purpose` is a closed vocabulary whose members name their role; `maintenance`
declares that it has none. The role and grant matrix is a projection of the compiled model, and
every consumer of a role name or of the purpose map reads it.

Physical schemas declare themselves. Each subset definition that is a physical schema carries a
marker saying so, from which the compiler derives the schema set, and two defaults: the schema's
read roles and its frontier-guard default, `guarded` or `exempt`. A relation may override either
with the same annotations. A relation therefore always has a declared classification, and no
default lives in code. Frontier-guard membership becomes "the relations of guarded schemas that
are not declared `exempt`". A forgotten exemption fails safe: an over-guarded write refuses
visibly, where a forgotten guard today is silent.

Physical annotations that hold structure take structured values instead of JSON strings, typed by
profile classes written as ordinary LinkML classes (`PhysicalRelation`, `PhysicalColumn`,
`ForeignKey`, `Check`, `Index`). Each element's annotation dictionary is validated once per
compiled model as an instance of its profile class. The reader resolves inheritance by walking
class ancestors, because class annotations are not inherited and `slot_usage` replaces inherited
slot annotations rather than merging them.

Execute grants come from each **program declaration**'s purposes. The program registry that
holds program declarations is UDM-09's; the section on UDM-03 below states what is delivered
before it and what waits. The grant of TEMP on the database is a bootstrap operation and not an
installed program; it belongs to UDM-17 and is not part of this design.

Integrity declarations fail closed. At generation the following refuse, and nothing else in
this area does: a role or purpose name that is not in its vocabulary, wherever it appears (a
grant, a program's purposes, an effect authorization, a read-role override); a `Role` member
without its login and membership annotations; a purpose with no role unless it declares that
it has none; a program with neither declared purposes nor the explicit internal marking that
[UDM-09](programs-identity-and-revisions.md#the-program-declaration-and-what-is-derived-from-it)
defines for a program no purpose may execute; a physical schema without declared
defaults; an override on a relation outside a physical schema. These are omissions in the
integrity layer, which **the flexibility frame** reserves refusal for. Absence never means
"any role".

*Rejected:* `in_subset` membership for the guard, which has no declared default and leaves an
unlisted relation unguarded; a required per-relation classification, which is equally safe and
adds ceremony to every new native relation for no further protection; keeping JSON-string
annotations, which keeps the constraints invisible to LinkML tooling. *Reopens the choice:* a
physical schema whose relations are mostly exempt would suggest its default is wrong, not that
defaults are wrong.

### The earlier model retires after its distinction is carried forward

**Proposed.** The earlier model's one piece of intended flexibility, the declaration of whether
packs may extend a vocabulary, moves to the released model in UDM-02. After that, its consumers
move to released-model types and the earlier model is deleted. The order is a real barrier and
not a convenience: deleting first would remove the only representation of pack extensibility.

## Pivotal library capabilities

- **linkml-runtime 1.12.1, composition.** `SchemaView(schema, importmap=...)`,
  `imports_closure()` and `merge_imports()` build the merged view. `induced_enum` and the JSON
  Schema and Pydantic generators do not expand `inherits`, `include` or `minus`, which is why the
  project's own `expand_enum` remains the one expansion (probed on synthetic schemas;
  [data-model library report](../../design_review/evidence/2026-11-18_production-review-inputs/library-data-model.md)
  F6, F7). LinkML's SQL generators read three annotations and know no PostgreSQL schemas, checks,
  triggers or grants (F10), so `schema/relational.py` stays the relational compiler.
- **linkml 1.12.1, instance validation.** `linkml.validator.Validator(schema,
  validation_plugins=[JsonschemaValidationPlugin(closed=True), RecommendedSlotsPlugin()])`,
  called with `target_class="DataOperationDeclaration"`. The validator memoizes its validation
  context (`linkml/validator/validator.py:120`), and the generated JSON Schema sits in a
  module-level cache of 32 entries keyed by `id(schema)` with no lock
  (`linkml/validator/validation_context.py:16–41`). Holding one validator per compiled model
  keeps that key stable and is why the validator is a projection and not a per-call
  construction. `RecommendedSlotsPlugin` reports with warning severity, not as an error
  (`linkml/validator/plugins/recommended_slots_plugin.py:9–29`).
- **LinkML enumerations.** Permissible-value annotations take structured values and load as
  Python lists and dictionaries (F1). Permissible values carry `status` through
  `common_metadata`, so a provisional member needs no custom annotation. There is no openness
  slot on an enumeration in 1.12.1 (the metamodel's `enum_expression` slots are `code_set`,
  `pv_formula`, `permissible_values`, `include`, `minus`, `inherits`, `reachable_from`, `matches`
  and `concepts`), which is why openness is a project annotation plus the `any_of` range.
  Limits: annotations are untyped by default and `instantiates` is not enforced (F5), which is
  why the physical profile validates annotation dictionaries as instances explicitly;
  cross-record checks are not a stock plugin.
- **cachetools `cached` with `condition`** holds the compiled model; the bound, the lock and the
  move to 8.0.1 are [the cache companion's](cache-system.md).

## What this supersedes

UDM-00 writes the decision records and amends the design sections. This companion states what
they must say for its packages. The validity passages of the declared-data-operations (DDO) plan
are listed in the [lowered operation facts companion](lowered-operation-facts-and-validity.md#what-this-supersedes).

| Owner and passage | Says today | Replaced by |
|---|---|---|
| DESIGN §B5 head (`docs/design/DESIGN.md:853–855`) | "One captured LinkML closure supplies physical types, slot and value-set facts" | RC03: one composer and one compiled model per model-sources identity, with projections that keep their sub-identities (UDM-01) |
| ADR-0124 and file custody | drift refuses and requires a restart | RC09: kept for Python code; a changed model declaration yields a new compiled model. ADR-0124 is superseded by a record that carries its decision forward (UDM-01) |
| [ADR-0092](../../adr/0092-ddo-operation-authority.md) Decision (`:25–28`) | implementation-owned typed Python definitions are admitted front ends; the grammar is unstated and hand-validated | RC04: both routes kept; the Python route's grammar and vocabularies are declared in LinkML, each vocabulary states its openness, descriptive fields stay open, literals are validated against the declaration with closed field names. Accepted records are immutable, so ADR-0092 is superseded by a record that carries its decision forward (UDM-02) |
| [ADR-0024](../../adr/0024-semantic-release-preparation.md) (`:46`) and the D2 preparation contract | "Unsupported required semantics refuse" | RC14: preparation distinguishes refusing diagnostics from non-refusing `unassessed` ones for undetermined declarations and unknown terms of open vocabularies; operator decision of 2026-11-19: no promotion boundary. UDM-00 writes the record at whichever of the two owns the rule (UDM-02 supplies the route; UDM-05 and UDM-06 use it) |
| `model/core.yaml:1034–1040` and `schema/pack.py:1–22` | `ci:lifecycle` and the pack rule | The openness annotation and the consistency check in the released model (UDM-02); both then retire (UDM-04) |
| `semantic/alembic_privileges.py:75` against [ADR-0103](../../adr/0103-ddo-privilege-policy.md) Decision (`:27–29`) | read roles default in code, while the record says exact SELECT grants are declared | RC12: role and purpose vocabularies in the model; read roles declared per schema with per-relation overrides; no code default (UDM-03) |
| Review R02, §3.2: "the free-text `preparation` … stays unconstrained" | — | `Preparation` is open with known members, because kernels test three of its values (UDM-02) |

## UDM-01 — One composer and one held compiled model

**Implementation vision.** The composer is a new module in the model's own package. Its input is
a capture; its product is the compiled model described above; the decisions it owns are the
capture's identity framing and the list of projections. It fails the way preparation fails
today: an import that was not supplied refuses and names the import, and a deterministic compile
error is a value held under the capture's identity so that a broken candidate is not recompiled
on every request. Two captures never share an entry and never see each other's projections.

The first step is to re-read the composition sites at the entry commit, because the count
matters to completeness and the investigation's headline and its enumeration differ by one.

**Complete consumer scope.** The three closure routines and the physical closure
(`schema/physical.py:166–197`) become the composer's internals. The seven single-purpose views
ask for a projection. The fifteen `compile_physical` call sites listed in the baseline ask for
the physical or read metadata projection; among them, `semantic/data_operation_storage.py:123–137`
takes the projection instead of recompiling when it was not handed metadata, and the three sites
in `schema/model_change.py` compile the candidate as a second capture. The site at
`semantic/authored_sql.py:350` lies in the lines UDM-19 deletes, so whichever of the two
packages lands second drops it. The module globals of `semantic/metadata.py` become accessors
over the running capture, for all 63 importing modules;
most uses are `metadata.table(...)` or `tables[...]`, a mechanical change, and the tests that
import the globals move to the accessor. The companion projection's holder
(`semantic/companion_projection.py:561–617`) becomes a projection of the compiled model for its
captured sources. The 36 raw-string decodings of `cs:` annotations move to typed annotation
access. The four field-kind type maps named in the baseline read the type-resolution
projection, and the companion export's column literals read the `cp:` projection. The two views of the earlier model (`schema/model.py:235`, `schema/pack.py:232`) are not
migrated; they go with UDM-04. That is the complete scope; the paths in the baseline are the
whole list of composition sites, not examples.

**Removed.** The three closure routines as separately maintained code; the import-time
compilation in `semantic/metadata.py`; the companion projection's private `lru_cache`; the
`str(...).lower() == "true"` decoding pattern; the four field-kind type maps; the grouping and
provenance column literals of the companion export.

**Prerequisites.** None for the composer. The holder is the compiled-model tier of UDM-13; until
that package lands, UDM-01 holds the running capture's object in one module-level reference with
a lock and passes candidates explicitly, and UDM-13 replaces that reference with the tier
without touching consumers. This is stated so that neither package waits for the other.

**Native revision.** None. Generated bytes must be identical; if they are not, the composer is
wrong. The one exception is a type map that a kernel generator reads and that disagrees with
the physical compiler's resolution: connecting it would change a generated byte, so that
connection is delivered by UDM-05 in revision A and the disagreement is recorded.

**What this keeps open.** Trying a candidate model beside the running one becomes ordinary.
Editing a model declaration without restarting a serving process becomes ordinary with UDM-13,
which adds the observation of changed sources once per request scope; UDM-01's interim single
reference does not observe changes. Nothing is newly closed.

**Acceptance evidence.**

- The desired objects frozen for native revision N29 are compared with objects regenerated
  through the compiled model, statement by statement. The frozen revision is the independent
  expectation: it was produced before this code existed. A composer that merges imports in a
  different order, drops an induced slot or expands a value set differently changes at least one
  statement.
- A candidate capture that differs from the running capture in one enumeration member is
  compiled while the running one is held. The test asserts, from hand-written expectations, that
  each object reports its own member list and that the running object is the same object before
  and after. A holder keyed by anything coarser than the capture's identity fails.
- A source file is rewritten with identical bytes: the identity and the held object are
  unchanged. A source file is rewritten with one changed byte in a comment: the identity changes
  (the identity is over bytes, by design), and the physical projection's sub-identity changes
  only if the physical sources changed.
- An import that the capture does not supply refuses, with the import named; the test removes
  one schema from a hand-built capture.
- A typed-annotation table written by hand for a small schema (a boolean, a case policy at class
  level, a case policy at property level) is compared with the projection's values.
- A hand-written table of the database and Python type of each field kind in use is compared
  with the type-resolution projection, and a search finds none of the four former maps.
- For a small hand-written schema with `cp:` annotations, the companion export's grouping and
  provenance columns equal a hand-written list; changing one annotation in a copy changes the
  corresponding column. An export that still reads its literals does not change.

## UDM-02 — The declaration grammar and its vocabularies, each stating its openness

**Implementation vision.** The package adds the vocabulary module and the declaration schema to
the released model, admits the openness annotation in the preparation profile's safe list
deliberately, adds the model-preparation consistency check, exposes the declaration validator and
the vocabulary table (members, openness, status and structured member annotations) as
projections, and gives `compile_data_operations` its diagnostics return. It owns the decision of
which checks are structural (declared) and which are semantic (compiler pass), and the mapping
from validator results to diagnostics. It does not own what any program does with a vocabulary
member: `ValidityFamily`'s member annotations for member requirements are added by UDM-05
(which program validates a family is stated on the program declaration, not on the member), `SupportEdgeKind`'s traversal annotations by UDM-07, and `Role` and `Purpose`
annotations by UDM-03. UDM-02 declares those four enumerations with their members and openness
so the later packages have a home to annotate.

Failure behaviour is today's for a malformed literal (it refuses and names the operation and the
field) and new for two cases: an unknown value of an open vocabulary and an absent recommended
declaration are reported and do not refuse. The `recommended` marking on `validity_family` is
switched on by UDM-05 in the change that writes the existing operations' claims, so there is
no interval in which every existing operation is reported for a declaration it could not yet
make.

Its first step settles an open premise from the investigation: whether the vocabulary module can
be imported into the physical closure without the physical compiler refusing content that is not
physical (`schema/physical.py:154–163`). With UDM-01 in place both the declaration schema and the
physical projection read the same compiled model, which should make the question moot; the step
is to confirm that by reading the refusal and, if it still applies, to give the vocabulary module
its own root.

**Complete consumer scope.** All 62 modules that assign `__data_operation__` are validated
against the declaration class; none of them is edited by this package, because the grammar
describes what they already say. Declaration-owned model protocols, the second authoring route,
are unchanged. The readers of the closed sets inside the compiler read the vocabulary table. The
`ci:lifecycle` rule's two enforcement points (`schema/model.py:459–460`, `schema/pack.py:438–449`)
gain their released-model counterpart, the consistency check; the earlier ones stay until UDM-04.
The released route for pack extension (pack schemas imported by the release) is confirmed to
cover what the earlier pack loader allowed for the two sets the earlier model declares
extensible, `StatementKind` and `ClaimModality`. Two duplicated value sets from the review's
fact-authority table are closed here: the pair of PDF outcome sets, of which one retires after
the entry step reads both, and the Python `Literal` copy of the value-codec tags, which becomes
a checked copy of the observations vocabulary.

The finding DA-086 concerns facts the model already declares that programs restate as literals.
UDM-02 gives those facts a readable home on the compiled model (the vocabulary table, and the
task lifecycle as a projection of the protocol) and moves the Python-side copies to checked
`Literal`s. The kernel-side reads change program bytes, so they are delivered with native
revision A by [UDM-05](lowered-operation-facts-and-validity.md#udm-05--validity-declarations-lowered-per-release-and-selection-by-the-lowered-attribute),
not here. The field-kind type maps and the `cp:` columns are UDM-01's.

**Removed.** `_PROFILES`, `_METADATA_FIELDS`, `_KIND_UNIVERSES`, `_PROJECTION_FAMILIES`,
`_BINDING_OPERATORS`; the field-name sets passed to `_mapping` at 30 call sites; the form,
direction and profile tests; the purpose sets in `semantic/data_operation_wire.py:288` and
`semantic/runtime.py:14` as independent statements. The helpers `_mapping`, `_strings` and
`_text` retire where no semantic check still uses them.

**Prerequisites.** UDM-01 supplies the object that holds the validator and the vocabulary table.

**Native revision.** None. The vocabularies exist in the model after this package, and no
installed program reads them yet.

**What this keeps open.** Descriptive fields stay free: an experimental operation describes its
ownership, preparation and cancellation in its own words and is reported, not refused. A pack
adds members to a pack-extensible vocabulary in its own schema. A term that is not settled is
declared as a provisional member. A declaration that may be unknown when an operation is first
written is recommended, not required, and its absence yields one diagnostic. Newly closed: nothing that is not closed today. Field
names, profile, forms and kind universe are closed in the hand validator now; this package moves
the closure to a declaration.

**Acceptance evidence.** Expectations are hand-written and never produced by the validator or
the compiler under test.

- A table of hand-written literals with expected outcomes: a field outside the declaration is
  `invalid`; a profile outside `Profile` is `invalid`; an ownership of `experimental-shared` is
  accepted with one `unchecked` diagnostic naming the term; a preparation of `resource` is
  accepted with no diagnostic; a nested role record with an extra key is `invalid`. With the
  `recommended` marking switched on in the test's copy of the declaration schema, an absent
  `validity_family` is accepted with exactly one `unchecked` diagnostic, and an explicit `none`
  with no diagnostic.
- All 62 real modules compile, and the diagnostics list equals an expected list produced
  independently, by a plain text search of the literals for their `ownership` and `preparation`
  values and not by running the validator. With the values in use declared as known members
  the expected list is empty unless that inventory finds a value outside them. A validator
  that silently accepts unknown fields passes the first clause and fails the table above; one
  that refuses a descriptive value fails this clause.
- Perturbation of the declaration in the test (the test series' correspondence rule): a member
  is added to `Form` in a copy of the vocabulary module, and a literal using it then validates;
  the same literal against the unmodified module is `invalid`. A validator that still reads a
  Python set fails.
- The consistency check: a hand-written pack schema that `inherits` a closed enumeration
  refuses; the same against a pack-extensible enumeration yields per-release vocabulary rows
  equal to rows written by hand; an open enumeration used as a plain range refuses; a provisional
  member is accepted and reported.
- The checked `Literal` copies: removing a member from the enumeration in a copy makes the import
  check fail and name the member.

## UDM-03 — Role and purpose vocabularies, the typed physical profile, grants from program declarations

**Implementation vision.** The package annotates `Role` and `Purpose`, adds the physical-schema
marker and the two per-schema defaults to the subset definitions, adds the profile classes and
their validation, exposes the role and grant matrix as a projection, and moves every reader. It
owns the decision of each schema's defaults, which must reproduce today's effective grants and
guard membership exactly, and it owns the resolution rule for an override. It fails at
generation for the integrity omissions listed in the target design, and nowhere else.

An interim consolidation is cheap and is the recommended first step: every role literal reads the
existing constants (`PUBLISHER`, `DEFAULT_READ_ROLES`, `PURPOSE_ROLES`), as
`semantic/native_admission_functions.py:149` already does, so the move to the vocabulary has one
source to change.

**What is delivered before the program registry, and what waits.** This package's second
prerequisite is a capability, not a whole package: a declared purposes field on each program
declaration. That field is the product of the typed program registry, UDM-09. The identity
layers of UDM-10 are not needed for grants.

*Delivered without the registry:* the two vocabularies and the matrix; all 198 role literals
reading the vocabulary; one purpose-to-role mapping in place of four; the schema set derived
from the marker; per-schema read roles and guard defaults with overrides; the typed physical
profile; and execute grants generated from purposes for every program that already declares
them. Public native operations declare purposes in the protocol
today. The five programs granted by name (`semantic/data_operation_storage.py:1908–1927`) receive
their purposes from one interim table in the generator, validated against `Purpose`, in place of
the `elif` chain; `ddo_field` and `data_binding_rows` are granted to roles that no single purpose
names, so the interim table states a set of purposes for each. The registry absorbs the
interim table: its seven entries become the purposes of those programs' declarations.

*Waits for the registry:* grants generated from each program declaration's own purposes field;
removal of the interim table; and UDM-09's completeness rule that a program with neither declared
purposes nor the internal marking refuses at generation, which only a registry that enumerates
programs can enforce.
When the registry arrives, the grants it generates must equal the grants this package
produced, so the step installs no differing byte and needs no revision of its own.

**Complete consumer scope.** The 198 `"corpus_sem_*"` literals in 46 modules; the constants
module `semantic/alembic_privileges.py` (its `table_policy` default at `:75` is removed, not
moved); the restated tuples and JSON default in `semantic/native_admission_tables.py:27–32,
176–184`; `semantic/native_admission_principals.py:8–16`; the four purpose maps; the schema-set
literals at `schema/relational.py:413, 430`, `semantic/closure_native.py:130` and
`semantic/native_admission_principals.py:10`; the 84 `ph:read_roles: '[]'` annotations, which
remain as overrides where the schema default differs and are deleted where it does not; the
frontier-guard tuple (`semantic/data_operation_storage.py:1952–1965`); the JSON-string physical
annotations and their decoder in `schema/relational.py`; the host bootstrap that reads the role
constants; the hand-written role SQL of the private test bootstrap
(`tests/native_private_bootstrap.py:30–106`), which the test series records as production
context and which takes its role names from the vocabulary; and independent control SQL, which
keeps its hand-written form and takes role names as data arguments. The disagreement between `native-purpose:evaluator` in effect authorizations
(five sites) and the purpose `evaluate` is resolved here once the open premise below is settled.

**Removed.** `DEFAULT_READ_ROLES` as a default; the three copies of the purpose map; the
by-name grant chain; the frontier-guard tuple; the schema-set literals; JSON-string decoding of
structured physical annotations.

**Prerequisites.** UDM-02 supplies the vocabulary module, the openness annotation and the
vocabulary table. The program registry (UDM-09) supplies declared purposes per program for the
part that waits.

**Native revision.** B, shared with [UDM-07](lowered-operation-facts-and-validity.md#udm-07--one-declared-support-edge-meaning-and-one-reference-to-node-mapping).
The intent is that grants and guard membership are unchanged in effect; the bytes that may
differ are any guard trigger that a schema default adds. Whether this package contributes to
revision B is answered by a statement-by-statement comparison of the generated objects and
privileges with the head frozen revision, which is possible today (the comparison UDM-09's
acceptance performs; before UDM-09, a comparison of the generated script with the frozen
statements). If they are equal, the package contributes nothing to revision B.

**What this keeps open.** A new native relation in a guarded schema is guarded and readable by
its schema's declared default, with no extra annotation, so trying a new relation is cheap and
safe. Domain packs add classes and properties as registry rows without physical definitions and
touch none of this profile. Newly closed, in the integrity layer: a new relation in a guarded
schema is write-guarded unless it is declared exempt, where today an unlisted relation is not
guarded. Roles, purposes and grants are closed by ADR-0103 already; the package moves their
home into the integrity layer of the model and makes omissions refuse.

**Acceptance evidence.**

- The grant and guard matrix before and after. Expected grants per relation and per program, and
  expected guard triggers, are written by hand from the decision record and the current tuple,
  and compared with the installed catalog (`pg_class.relacl`, `pg_proc.proacl`, `pg_trigger`) on
  a database deployed from the new generation. The catalog of a database deployed from the
  current head is a second oracle beside the hand-written matrix, so that "unchanged in effect"
  is checked against the code that produced today's grants. A schema default chosen wrongly
  changes a grant and fails.
- Integrity omissions, each provoked in a copy of the model: a program declaring purpose `audit`
  refuses at generation and names the purpose; a role literal not in `Role` refuses; a `Role`
  member stripped of its membership annotation refuses; a physical schema with no declared
  defaults refuses; an override on a relation outside a physical schema refuses.
- Safe default: a new relation is added to a guarded schema with no annotation. The expected
  result, written by hand, is the guard trigger and the schema's read roles. An `exempt` override
  on it removes the trigger and leaves the grants.
- The typed profile: a foreign key, a check and an index written as structured annotations yield
  relational metadata equal to the metadata from today's JSON-string form (the N29 frozen objects
  are the independent expectation); an annotation with an unknown key refuses.
- The purpose map: `fit` resolves to the fitter role in every consumer, including the closure
  kernel that omits it today; `maintenance` resolves to no role and does not refuse.
- When the registry lands: the grant matrix generated from program declarations equals, entry
  by entry, the frozen `privileges` of the revision this package installed, and a program
  declaration stripped of its purposes, and carrying no internal marking, refuses at generation.

## UDM-04 — The earlier core and system model retired

**Impact contract (I08).** This package owns the comparison of two compiled model captures and
the removal of the old preview's second account of model changes. Return typed changes to
authoritative facts, including vocabulary openness and membership. UDM-09–12 add the program and
validator effects and UDM-26 projects the combined impact through the existing model-change
commands. Preserve the earlier revision log's genuine audit or apply prerequisites through the
operator's existing UDM-04 premise. Verify the compiled comparison without requiring a native
revision for a model-only change. The report can distinguish a changed producer, reconfirmation,
and retained work, with unresolved live support reported as conditional.

**Implementation vision.** The package moves every consumer of the earlier model to
released-model types and then deletes the earlier model. It owns the mapping from each earlier
type to its released counterpart and the design of the model-change preview's successor. It has
no run-time failure behaviour of its own; a consumer that cannot be mapped is a finding to
record, and the earlier module it needs stays until the finding is settled.

The preview is the consequential part, and the review understated it. Today the preview operates
on the earlier model's two canonical declarations and its revision log: it loads both sides with
`model.load`, diffs them with `change.diff`, and checks the log (`schema/model_change.py:622–660`).
With UDM-01 in place a preview is a comparison of two captures: the running compiled model and
the candidate's. **Proposed:** the preview's change account is derived from the two compiled
models' projections (the physical metadata, which the preview already compiles at
`schema/model_change.py:505, 689, 1096`, and the vocabulary table), and the earlier change
records are not carried forward. What the earlier revision log gives an operator that this
comparison does not is the open premise below. It blocks the package until the operator
decides, and it includes the preview's check that a native change names a revision
(`schema/model_change.py:651–660`), which reads the earlier change record and needs a successor
of its own. [UDM-11](programs-identity-and-revisions.md) changes how a revision request is
judged on the same path, so this package's replacement of the preview lands first.

**Complete consumer scope.** The 56 source modules that import the earlier model, by module:
`core/vocab.py` (40 source files, 37 test files); `core/_model/*` (11 and 5); `core/keys.py`
(`methods/math/scope.py`, `methods/math/spans.py`, `schema/lookup.py`,
`semantic/alias_policy.py`; 8 test files), of which only the parts not live retire, and whose
fifth importer `evaluate/equivalence.py` is deleted by UDM-19 and not migrated here; `schema/change.py` (`schema/model_change.py`, `schema/preparation.py`; 2 test files);
`schema/pack.py` (`orchestrate/project.py`, `orchestrate/source_operation.py`,
`schema/lookup.py`; 14 test files); `schema/lookup.py` (no source importer; 2 test files);
`schema/model.py` (16 source files, among them `cli/model.py`, `cli/schema.py`,
`schema/model_change.py`, `schema/model_deployment.py`, `semantic/arrow_types.py`,
`semantic/companion_projection.py` and `semantic/native_call_sources.py`; 38 test files). The
generated native facade's import of `core.vocab.TaskUnitType`
(`semantic/native_call_generation.py:106`) is retargeted to the released vocabulary, which
changes a generated Python output and no installed program. The counts are the cache and
retirement map's; the entry step lists the modules by name.

**Removed.** `model/core.yaml`, `model/system.yaml`, `model/revisions.yaml`; `core/vocab.py`;
`core/_model/*`; the parts of `core/keys.py` that are not live; `schema/change.py`,
`schema/pack.py`, `schema/lookup.py`, `schema/model.py`; the statistics pack's earlier schema;
the earlier-model `cached_property` holders; the tests whose only subject is the earlier model.
The two migration trees, the evaluation modules with no production importer and the stale
preview explanation are UDM-19's, and nothing there waits for this package: a module that
imports the earlier model can be deleted before the earlier model is, and the
`alembic_revision` values in `model/revisions.yaml` are identifiers that nothing resolves
against the `alembic/` tree. Tests of modules UDM-19 deletes go with those modules.

**Prerequisites.** UDM-02 supplies the openness declaration and the released pack rule, without
which this package would delete an intended distinction. UDM-01 supplies the second capture that
the preview's successor compares. The operator's decision on the revision log is the third.

**Native revision.** None.

**What this keeps open.** Pack extension of a shared vocabulary keeps a declaration (carried by
UDM-02) and a released route. Nothing is newly closed. The package removes a second statement of
closed sets that the released model also declares, so a set can no longer be closed in one model
and extended in the other.

**Acceptance evidence.**

- A search of the source and test trees finds no import of the earlier modules and no load of
  the three declarations; the package imports and the whole test collection succeeds.
- The model-change preview on a hand-made candidate (one added column, one added member of a
  pack-extensible vocabulary, one changed check) reports exactly those three changes, from an
  expected list written by hand. A preview that still reads the earlier declarations cannot run,
  because they are gone; one that compares the wrong pair of captures reports no change.
- A pack that extends a pack-extensible vocabulary prepares, and one that extends a closed
  vocabulary refuses, on the released route alone (the UDM-02 control, re-run after deletion).
- The generated facade imports no earlier-model name and is byte-identical otherwise.

## Open premises

| Premise | Evidence that settles it | Work it constrains |
|---|---|---|
| The count and list of composition sites (sixteen by search and enumeration, seventeen in the investigation's headline) | A search at the entry commit | Completeness of UDM-01 |
| The vocabulary module can be imported into the physical closure without the physical compiler refusing non-physical content (`schema/physical.py:154–163`) | Reading that refusal after UDM-01; if it applies, the vocabulary module gets its own root | First step of UDM-02 |
| LinkML validation reproduces every structural refusal of the hand validator for the 62 real modules and the negative table | The UDM-02 acceptance table | Which checks stay in the compiler pass |
| The role-name disagreement: effect authorizations say `native-purpose:evaluator`, the purpose vocabulary says `evaluate` | The native owner's or the operator's choice of the one spelling; the other becomes a refusal | Blocks the `Purpose` declaration's final members in UDM-03; UDM-05's evaluator-authorization derivation reads the result |
| Each physical schema's defaults reproduce today's effective grants and guard membership | The hand-written matrix of UDM-03's first acceptance item | UDM-03's defaults and which of the 84 empty read-role annotations remain |
| What the earlier revision log and change records give the model-change preview that a comparison of two compiled models does not: declared change records, the `alembic_revision` link, log consistency checks, and the check that a native change names a revision (`schema/model_change.py:651–660`) | Reading `schema/model_change.py`, `schema/change.py` and the preview's command-line consumers in full, then the operator's decision on what must be provided | **Blocking** for UDM-04, and for deletion of `schema/change.py` and `model/revisions.yaml` |
| LinkML generation of the declaration schema changes no field name that a SQL reader of the effective-model archive depends on (a risk the review names) | Reading the archive's SQL readers at UDM-02's entry | The pace of UDM-02's declaration schema, not its direction |
| The released pack route covers what the earlier pack loader allowed | The two extensible sets (`StatementKind`, `ClaimModality`) exercised through a release | UDM-02's pack rule; UDM-04's deletion of `schema/pack.py` |

## State

| Package | State |
|---|---|
| UDM-01 | Not started |
| UDM-02 | Not started |
| UDM-03 | Not started |
| UDM-04 | Not started |
