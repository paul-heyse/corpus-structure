# UDM focused design advice: compiled centre, declaration grammar, lowered operation facts, integrity vocabularies

Focused advice for plan authoring (not a formal review), 2026-11-19. Source: frozen snapshot of
`cb4e09667` (production source = `5139eaba3`); paths are relative to `python/corpus-structure/`
unless rooted at `docs/`. Source facts are **Interface-checked by source inspection, 2026-11-19**;
every remedy is **Proposed**; LinkML facts are **observed in installed linkml 1.12.1 source**
(project `.venv`, read-only). Nothing was run.

**Coverage.** Read in full: review §§1–3, R01, R02, R03, R07, R08, R15, R16, §§12–14; the
recommendation-audit companion; audit DA-070. Read at the decisive lines: every guard and
validator named below; `data_operation_compiler_native.py:468–560, 660–680, 760–960, 1040–1100`;
`data_validity_native.py:87–300`; `data_completion_settlement_native.py:540–600, 650–700, 740–806`;
`data_operation_compilation.py:75–360, 806–830, 1040–1110, 1460–1580`; `data_operation_model.py:289, 495–620`;
`data_derivation_native.py:112–330, 455–640`; `support_trust_native.py:95–360`;
`data_operation_projections.py:150–300`; `change_impact.py:300–445`; `schema/relational.py:395–560, 690–740`;
`prepare.py:250–375, 477–531, 970–990, 1350–1365`; the physical declarations; ADR-0024, 0092, 0103,
0131 decisions; DESIGN §B4/§B5 heads; DDO `products-and-support.md:300–318, 415–460`,
`contracts-and-compilation.md:265–300`. The DDO plan was **searched** for these terms, not read
in full. Not read: generator bodies beyond the cited lines, `rule_views.py`, `conditional_rules.py`.

## 1. The compiled centre (R01)

**Verified.** Seventeen `SchemaView(` constructions in 11 modules: three near-identical
closure routines (`semantic/prepare.py:362–374`, `semantic/native_call_sources.py:111–117`,
`semantic/projection_analysis_products.py:98–107`: seed importmap → `merge_imports` → re-view);
the physical closure (`schema/physical.py:166–197`); single-purpose views
(`semantic/companion_projection.py:552` from a disk path; `rule_views.py:402`;
`conditional_rules.py:178`; `ontology.py:159, 260, 626`; `source_value_native.py:56`); the earlier
model (`schema/model.py:235`, `schema/pack.py:232`; retire with R13). `compile_physical` is called
at 15 sites outside `schema/relational.py` (`metadata.py:33, 46`; `data_operation_storage.py:137,
1877`; `data_operation_projections.py:2745`; `data_operation_source_native.py:30`;
`companion_projection.py:587`; `pdf_lowering.py:193`; `pdf_record_model.py:86`;
`pdf_publication_native.py:460`; `projection_analysis_products.py:141`; `authored_sql.py:350`;
`schema/model_change.py:505, 689, 1096`). `semantic/metadata.py:32–51` compiles two `MetaData` at
import; 63 modules import it.

**What the compiled object holds.** An immutable `CompiledModel` built from one *capture*: the
named source bytes (LinkML schemas, the pinned `linkml:types`, the native protocol, catalogs) with
no filesystem fallback (the guard `prepare.py:355–359` already enforces this). Lazily derived and
held on the object, each with its own sub-identity: merged view per root (`physical.yaml`,
`read-projections.yaml`, the release bundle root, the operation-calls root); physical and read
`MetaData` (via `schema/relational.py`, unchanged); expanded value sets (`ontology.py:328`
`expand_enum`); typed annotation access (DA-004; structured values for `ph:`/`cs:` keys); the
**declaration validator** (§2); the **vocabulary table** (§2: members, openness, status,
structured member annotations); the role/grant matrix (§6); the support-edge table (§5).

**Who builds it; how consumers obtain it.** One composer function takes a capture and returns the
object; one holder (T1 of `cache-design.md`, cachetools `cached` with `condition`) keys it by the
capture's identity: a framed digest over sorted `(name, sha256)` pairs, the same framing as
`physical_sources_id`. Consumers call `compiled_model(capture)` and then a projection; the running
package model is one capture read once through file custody. A candidate (model preview,
`model_change.py`), the PDF domain contract's captured sources (`companion_projection.py:561–617`)
and a release bundle are other captures and other entries. Projection sub-identities keep custody
granularity (the physical id stays the physical id).

**Migration scope** ("build my own" → "ask for it"): the three closure routines and
`schema/physical.py:166–197` become the composer's internals; the 15 `compile_physical` sites and
the seven single-purpose views ask for a projection; `metadata.py` globals become accessors over
the running capture (63 importers; mostly `metadata.table(...)`/`tables[...]`, a mechanical
change); `data_operation_storage.py:123–137` takes the projection instead of recompiling.
`schema/model.py`/`schema/pack.py` stay until R13 after R15 lands. Acceptance: generated native
bytes are identical before and after (compare against the frozen N29 desired objects); a candidate
and the running model coexist under two keys; a byte-identical edit yields no new entry.

## 2. Declaration grammar and vocabularies in LinkML (R02, RC04, R15)

**Today (retirement scope, exact).** The Python route's literals are `__data_operation__`
assignments in **62 modules** (`grep` for the assignment). The hand grammar is interleaved with
compilation in `semantic/data_operation_compilation.py` (2,622 lines). Its *structural* part:
`_PROFILES` (`:85`), `_BINDING_OPERATORS` (`:86–103`), `_METADATA_FIELDS` (`:104–140`) checked by
`_mapping(raw, …, _METADATA_FIELDS)` (`:1068`) and the profile test (`:1072–1073`); `_mapping`/
`_strings`/`_text` (`:166–188`) with literal field-name sets passed at 30 call sites (for example
roles `:1077–1094`, capabilities `:1479–1489`); `_KIND_UNIVERSES` (`:341`, test `:347`) and
`_PROJECTION_FAMILIES` (`:342`); role direction (`:1102`); forms (`:1491–1493`); free text
`preparation`, `cancellation`, `ownership` (`:1561–1563`). The *semantic* part stays a compiler
pass: role-kind resolution (`:1099–1101`), binding-field validation, stream-settlement consistency
(`:1494–1516`), transition mappings (`:1460–1478`), duplicate identities, captured-method
resolution (`:1518–1547`). `ImplementationCapabilities.forms` and `EffectiveOperation.profile` are
already `Literal`s (`data_operation_model.py:290, 497`).

**Vocabularies module.** One LinkML module of enums only, imported by the declaration schema and
(for the members SQL checks need) by the physical closure, so the compiled model sees one
definition. Members and openness:

| Vocabulary | Openness | Notes |
|---|---|---|
| `Profile`, `KindUniverse`, `Form`, `BindingOperator`, `ProjectionFamily`, `RoleDirection` | closed | each drives compilation; today's sets |
| `ValidityFamily` | closed | seven members today; member annotations: `validator`, `completion_guard`, requirements (§3); `status: provisional` allowed |
| `SupportEdgeKind` | closed | §5 |
| `Purpose`, `Role` | closed | §6 |
| `Ownership` | open with known members | known: `immutable` (tested at `characterization_ports.py:1059`, `sentence_products.py:1403`, `formal_products.py:986`) |
| `Preparation` | **open with known members** | the review calls it free text, but `pdf-native` (`pdf_completion_native.py:138`), `resource` (`contextual_admission_native.py:255`, `definition_admission_native.py:364`) and `native-publication` (`structural_admission_native.py:826`) are tested by kernels; those members carry declared meaning |
| `Cancellation` | unconstrained text | no tester found (searched generator modules for the four values) |

**Openness representation** (LinkML 1.12.1 has no enum openness slot): an enum-level annotation
(successor of `ci:lifecycle`, `model/core.yaml:1034–1040`) with values `closed`,
`pack-extensible`, `open`; admitted deliberately in the preparation profile (`prepare.py:259`
`_SAFE_ANNOTATIONS`). A slot whose vocabulary is open takes `any_of: [{range: <Enum>}, {range:
string}]`; a closed one takes the enum range directly. Provisional members use the permissible
value's native `status` (`common_metadata`). Recommended-but-optional declarations use
`recommended: true`. One model-preparation consistency check (internal inconsistency, not a lint):
an `open` enum used as a plain range, or a `closed` enum inside `any_of` with `string`, refuses;
a pack schema that `inherits`/`include`s a `closed` enum refuses (the rule of `schema/pack.py:1–22`,
moved to the released model before R13 deletes it); a `pack-extensible` enum's pack members become
per-release vocabulary rows as `prepare.py:485–531` already snapshots.

**The declaration class.** `DataOperationDeclaration` with one slot per `_METADATA_FIELDS` entry,
nested classes for roles, coverage, capabilities, effects, binding nodes; closed field names at
every nested record; ranges from the vocabulary module. New slot `validity_family`:
multivalued, optional, `recommended: true`, range `ValidityFamilyClaim` = `ValidityFamily` members
∪ {`none`, `undetermined`}. Operator-specific binding-expression shapes stay in the compiler pass
(they are cross-record checks); LinkML `rules` may express some later, not required.

**Validation.** `linkml.validator.Validator(schema, validation_plugins=[JsonschemaValidationPlugin(closed=True), RecommendedSlotsPlugin()])`, built
once and held on `CompiledModel` (the Validator memoizes its context, `validator/validator.py:120`;
the generated JSON Schema sits in a module-level LRU of 32 keyed by `id(schema)`,
`validation_context.py:16–41`, unlocked; holding one Validator per compiled model makes the key
stable). Each literal is validated with `target_class="DataOperationDeclaration"` before the
semantic pass. Results map to `Diagnostic` (`types.py:71–80`): `ERROR` → `outcome="invalid"`
(refusing, as today); `WARN` (recommended slots) → `outcome="unchecked"`.

**A non-refusing diagnostic** is `Diagnostic(code="validity_undetermined", location=<operation
id>, message="validity family not declared; conservative validity applies", outcome="unchecked",
remedy="declare validity_family: [<family>…] or [none]")`, emitted by the compiler from the
*compiled* state (so an explicit `undetermined` and a provisional family produce it too, not only
the plugin's absence warning), plus `ownership_unknown_term` for an open-vocabulary value outside
known members. `compile_data_operations` (`data_operation_compilation.py:806–814`) today can only
refuse (`PreparationError`); it gains a diagnostics return that preparation appends to
`PreparedRelease.diagnostics` (`prepare.py:1361`). They surface in the preparation validation report
as category `unassessed`, `complete=false` (`operation_reporting.py:372–410`), and durably through
the lowered columns (§3), so a release inspection can list unclassified operations without the
in-memory report.

**Retires** (with the grammar package): `_PROFILES`, `_METADATA_FIELDS`, `_KIND_UNIVERSES`,
`_PROJECTION_FAMILIES`, `_BINDING_OPERATORS`, the field-name sets passed to `_mapping`, the
form/direction/profile tests, and the purpose sets in `data_operation_wire.py:288` and
`runtime.py:14` (become checked `Literal` copies, the `source_value_native.py:55–66` pattern).

## 3. Lowered per-operation facts (R02 revised, R07 step A, R16)

**Lead verified, with corrections.**
- Lowering runs with the archived operation in scope: the `operation` record's `effects`,
  `capabilities` etc. are read into `expected_support` (`data_operation_compiler_native.py:775–820`),
  dependencies are lowered from it (`:905–911`), and `validity_family` is set by calling
  `ops.ddo_classify_validity(operation_id)` (`:916–926`; classifier `:483–529`, `CASE` without
  `ELSE`). The column is `validity_family: {range: string, required: false}`
  (`model/semantic/data-operation-physical.yaml:88`).
- Dispatch: `data_validity_native.py:272–288`, `case(..., else_=True)`.
- "Two guards select by a declared effect" is **slightly generous**: rich admission selects by id
  (`rich_admission_native.py:1186`) and refuses a *foreign* claimant of
  `native-rich-knowledge-admission` (`:1135–1145`); policy authorization selects by `command_class`
  (from eligibility predicates, `data_operation_compiler_native.py:530–550`) and refuses a foreign
  claimant (`record_policy_completion_native.py:425–441`); structural admission does the same
  (`structural_admission_native.py:1475–1494`). The pure precedents of *selection by a declared
  attribute* are two others: PDF completion selects on `capabilities.preparation == 'pdf-native'`
  and refuses PDF evidence otherwise (`pdf_completion_native.py:137–146`); external completion
  selects on `support_contract.external` and refuses external receipts otherwise
  (`external_execution_native.py:893–899`). That "select by declaration, refuse the family's
  evidence when not selected" shape is the target guard shape.
- Effects declared by four families: `methods/record_policy.py:70–71`,
  `methods/operation_events.py:326–330` (only `authorize`; `frame`/`fit` have `"effects": []`,
  `:97, :225`), `methods/rich_knowledge.py:405`, `methods/structural_admission.py:130–139`.

**Lowered per-operation facts.** (a) Validity: preparation compiles the claim into an archived
record `{declared: [...], families: [ready members], conservative: bool}`: `none` →
`([], false)`; named ready families → `(F, false)`; absent/`undetermined` → `([], true)`; a claim
including a provisional member → `(ready part, true)`. Mixing `none`/`undetermined` with names
refuses (inconsistency). (b) Entry point, profile, forms, preparation, effects, external,
dependencies, role kinds: already in the definition row/`support_contract`; the typed read
boundary (`native_definition_projection.py:31–42`) takes its shape from the effective model's
dataclasses. (c) New only if needed: an execution-evidence expectation (CPU receipt count; §3 open
premise P2).

**Physical representation.** Replace the optional string with `validity_families` (multivalued
`ValidityFamily`, required, may be empty) and `validity_conservative` (boolean, required). The
three states are `(∅,false)`=none, `(F,false)`=named, `(·,true)`=undetermined (with any ready
part). Both required, so absence no longer means anything. Compiler gap: the enum CHECK in
`schema/relational.py:512–517` renders `col IN (...)`, wrong for an `ARRAY` column; multivalued
enum ranges need `col <@ ARRAY[...]`. The archive gains the validity record on each operation, and
`definition_identity` includes it while `recipe` excludes it (`data_operation_model.py:529–566`
vs `:594–620`), so classifying later changes neither results nor reuse (native owner confirms;
the review's open premise).

**Migration and old releases.** Any native revision already forces re-preparation: the generated
release guard requires the archived `native_digest` to equal the installed descriptor
(`native_admission_release.py:516–533`), and release ids hash the native capture
(`prepare.py:975–986`). So this needs no re-lowering data step of the `ddo_n1_relower` kind
(`schema/data_steps.py:115–160`): the default release(s) are re-prepared and admitted under the
new kernel; older releases stay inert rows, not deployable. Existing `sem.data_operation_definition`
rows are converted by the revision's migration: non-null string `f` → `({f}, false)`; null →
`(∅, true)` (conservative, because legacy null conflates the two states). Published derivations of
old releases therefore re-validate conservatively, never permissively. Since the development
database is regenerable, regeneration is an acceptable alternative to the conversion.

**Every selection by hand list, and its replacement** (the audit's twelve plus seven sites found
by a search for operation-id literals in generator modules):

| Site | Today | Becomes |
|---|---|---|
| `data_operation_compiler_native.py:483–529` | classifier, 27 ids | retired; lowering copies the archived record and refuses a family name the kernel has no validator for |
| `data_validity_native.py:272–288` | dispatch `else_=True` | generated from ready `ValidityFamily` members: AND of `f = ANY(validity_families) → validator(node)` plus `validity_conservative → conservative(node)`; no `else` |
| `data_completion_settlement_native.py:548–563` | 14 guards each self-selecting | chain generated: family guards under `f = ANY(...)`; attribute guards (PDF, external, command class) keep their declared selectors; generic checks unconditional; guard name list moves to R04's registry |
| `…settlement_native.py:576–587` | evaluator authorization for 3 ids | derived: an operation whose output kind universe is `evaluator` or whose declared effect authorization includes `native-purpose:evaluator` (frame, fit by universe per `operation_event_native.py:1277`; authorize by effect; score by neither) — inferred from those lines, native owner confirms |
| `…settlement_native.py:744–806` | live-completion chain by literal ids | generated per family member (`completion_live` annotation) |
| `contextual_admission_native.py:188–201, 215, 568, 736` | 12-key factory dict; early returns | dict retires (implementation slice authenticates, `:225–236`); returns removed (reached through chain/dispatch only) |
| `contextual_admission_native.py:234–259, 571, 635, 686` | per-id profile, forms, receipt count, sub-behaviours | family requirements (allowed profiles `{derivation, discovery}`, forms `{[scalar],[batch]}`, preparation `resource`, effects `[]`) checked against the lowered row; sub-behaviour by declared input roles; receipt count: open premise P2 |
| `contextual_admission_native.py:291–310, 369` | required roles and producers per role by id | read lowered dependencies and role kinds |
| `contextual_definition_native.py:51–57, 140–170` | lineage producer ids (not in DA-070) | same: lowered dependencies of the consumer |
| `contextual_witness_native.py:136, 240–251` | producer ids (not in DA-070) | same |
| `definition_admission_native.py:33–44, 345–372, 386, 418` | `_OPERATIONS`/`_FACTORIES`; returns | family requirement; returns removed |
| `artifact_admission_native.py:112, 147, 217` | one id ×3 | same pattern |
| `rich_admission_native.py:606–622, 816–823, 903–910` | three lists | family membership; the `rich.admit` owner pin (`:1186`) becomes the effect member's declared owner |
| `rich_admission_native.py:582, 676, 920, 944, 951, 1219, 1278` | further per-id branches (not in DA-070) | read declared roles/effects per branch; owner's review of each |
| `operation_event_native.py:55–60, 350, 1287, 1359` | `_OPERATIONS`; returns | family membership; returns removed |
| `operation_event_native.py:1277` | universe by id | lowered output kind contract's `universe` |
| `record_grade_native.py:534, 702, 1445`; `record_policy_completion_native.py:1140, 1170, 1471–1476` | owner constant / literal; returns | family membership |
| `structural_admission_native.py:1058` | `structure.dossier/declared` by id (not in DA-070) | needs a home: a `ValidityFamily` member or a command class (open premise P3) |
| `structural_admission_native.py:824–831`, policy and PDF eligibility | owner id inside eligibility predicate | privileged-effect owner declared on the effect vocabulary member (generator input); other claimants refuse |

**"A family names its validator program."** Each non-provisional `ValidityFamily` member carries
structured annotations `validator: ops.ddo_<x>_dependencies_valid` and optional
`completion_guard`, `completion_live`, and member requirements. At generation, every named program
must exist among the kernel's rendered `CREATE FUNCTION` statements with the expected signature
(`(text) → bool` for validators); a non-provisional member without one refuses. Until R04's
registry exists, the check reads the parsed statements generation already holds
(`data_operation_storage.py:1890–1897` walks `CreateFunctionStmt`). Lowering refuses a family name
outside the kernel's generated ready set, so a release cannot claim a family the installed kernel
cannot validate.

**Keeping the kernel digest free of per-operation edits.** Three conditions: (1) no generator
reads operation ids (the table above); (2) the kernel capture stops including operation-owner
modules it captures only for their constants: `semantic/declared_structural_admission.py`
(`data_operation_storage.py:362–365`, `ADMISSION_OPERATION`), `semantic/record_policy_authority.py`
(`:391–394`), `evaluate/selected_operation_events.py`, `evaluate/declared_record_policy.py`
(`:368–378`), and `methods/operation_events.py` plus `evaluate/declared_operation_events.py`
(`operation_event_native.py:231–238`), which hold operation literals; keep a capture only where a
generator renders from it (check each before removing); (3) the vocabulary module is a generator
input and does move the kernel: adding a family is a kernel change, adding an operation to one is
not. Acceptance below perturbs a declaration and asserts the descriptor's `source_digest` is
unchanged while the release id changes. R05/RC15 later replace the whole-capture digest.

## 4. The conservative check (R16)

**Meaning.** Generic validity today is: producer definition admitted, outcome `success|empty`,
family validity, no revocation matching the episode's scope and selectors
(`data_validity_native.py:290–330`), plus support propagation through AND-edges. The family
validators' mutable premises are kernel digest and cut trust for grade, fit and event
(`products-and-support.md:451–452`). "Over-invalidates rather than under-invalidates" means:
for every state change after publication that could make *any* family validator judge the
derivation invalid through a recorded mutable premise (a trust epoch in the project; the
validating kernel), the conservative check judges it invalid; it may also invalidate where no
family would. Residual risk: premises outside trust and kernel (the contextual linguistic premise,
DA-070) are not covered; the diagnostic makes that visible.

**Premise settled from source.** Every published derivation has exactly one publication receipt
(`ops.data_publication_receipt`, unique `intent_id`; `ops.data_derivation` unique `intent_id`;
`model/semantic/data-operation-physical.yaml:403–420, 475–490`) with a required `trust_snapshot`
and the generated `validating_kernel_digest` (`data_derivation_native.py:604–615`). The snapshot is
the epoch map of the scopes locked at completion (`:329`), which are the ordinary support scopes
plus, for grade, fit and event only, their cut scopes (`support_trust_native.py:208–231`).
Support rows also record scope and epoch (`:483–496`). So **every run is tied to a snapshot**,
but for an undetermined operation that snapshot covers only its declared support's scopes; a
trust-bearing input it consumes outside declared support (a cut, as grade does) is not recorded.
Comparing that snapshot alone would *under*-invalidate.

**Design.** For `validity_conservative` operations, completion locks and records **all trust
scopes of the request's project** (`ops.data_trust_scope` has `project_id`), extending
`ddo_lock_completion_support`'s scope union with a conservative branch selected by the lowered
flag. The conservative validator (one generated program, its own validator identity under R05):
valid iff generic validity holds, `ddo_trust_snapshot_meaning(receipt.trust_snapshot)` equals the
current project epoch map's meaning (absent = zero, so lazily created scopes do not count;
`support_trust_native.py:126–160`), and `validating_kernel_digest` equals the installed kernel
(until R05 gives a validator identity). Cost: share locks on a project's scopes at completion of
unclassified operations, contending with revocation's exclusive lock; few scopes per book-scale
project. Invalid derivations are recomputed on demand, as today.

**Early returns become** nothing: validators and guards are reached only through the generated
dispatch and chain. An undetermined operation receives the generic completion checks, any
attribute-selected guard it declares (PDF, external, command class), no family guard, and the
conservative validator. **Preparation reports** `validity_undetermined` per operation (§2) and,
for a claim including a provisional family, `validity_family_provisional`.

**Order.** Step A can land with `validity_conservative` lowered but the conservative program not
yet present only if dispatch maps the flag to today's generic treatment plus the diagnostic; batch
both into one native revision to avoid an interim.

## 5. Support-edge meaning (R08)

**Four encodings, verified.** (1) `ddo_validity_edges` (`data_validity_native.py:87–240`): node
kinds episode, use, population, original and a `producer` pseudo-node; OR-groups by `choice` for
value substitution; inline reference classification at `:179–200`. (2) `_support_walk`
(`data_operation_projections.py:171–270`, six callers `:396, 466, 530, 1157, 1685, 2232`) with
`_reference_node` (`:156–169`, `else_` → episode) and an `authority` leaf kind for public reads;
its population edge requires both `admission_use_id` and `derivation_id` (`:245–255`).
(3) `change_impact._revocation_causes` (`change_impact.py:332–441`): Python, its own
`reference_node` (`:346–351`), a `selected-episode` kind, a population edge to an episode
(`:381–382`) the others lack, and the trust scope recomputed in Python (`:427`, versus
`ops.ddo_scope`, `support_trust_native.py:99–119`). (4) Source admission's lineage CTE over
`support_derivation_id` only (`source_admission_native.py:1129–1135`).

**Target.** `SupportEdgeKind` members, each with structured annotations: source node kind, relation
and key columns, target node kind, group (AND, or OR-alternative with its activation condition:
value substitution under a value-strength demand), and the traversal profiles it belongs to
(`validity`, `scope` superset, `public` with the authority leaf, optionally `lineage`). One
reference-to-node mapping, declared once: `kind ∈ {original-source, authored}` → original by
`admission_id`; `admission_use_id` present → use; `derivation_id` present → episode; otherwise
**refuse**. Generated from the table: the validity edge program, `_support_walk` (Core CTE),
the lock-scope walk, and an explanation output of the validity closure (per reached node: valid,
or the revoking edge and selector) that change impact consumes; `_revocation_causes`, its mapping
and the Python scope key retire. The population→episode edge disagreement is settled by the native
owner before generation (one of the encodings is wrong). The lineage walk becomes a profile if its
owner confirms it must agree with validity; otherwise it stays a named single-purpose walk.
Knowledge relations and pack predicates are untouched.

## 6. Roles, purposes and the physical profile (R03, R07 step B, RC12)

**Verified.** 198 `"corpus_sem_*"` literals in 46 modules (`grep`; the challenge's 199/47 within
counting noise); constants `alembic_privileges.py:24–33` (`PUBLISHER`, `DEFAULT_READ_ROLES`,
`PURPOSE_ROLES`); restated tuples `native_admission_tables.py:27–32`, JSON default `:176–184`;
`native_admission_principals.py:8–16` (principals, application schemas, private kernels); the
purpose→role map written four times (`data_operation_storage.py:1899–1907`;
`closure_native.py:174–181` without `fit`; `runtime.py:34–40` with `maintenance → None`;
`PURPOSE_ROLES`); per-function grant special cases (`data_operation_storage.py:1908–1927`). Public
native operations already declare `purposes` in the protocol
(`model/semantic/data-operation-native.yaml:2810–2870`). Physical schemas are LinkML subsets with
empty bodies (`model/semantic/physical.yaml:18–23`) and the schema set is a code literal again at
`schema/relational.py:413, 430`, `closure_native.py:130`, `native_admission_principals.py:10`.
84 relations declare `ph:read_roles: '[]'`; undeclared ones get the code default
(`alembic_privileges.py:75`), which contradicts ADR-0103's "exact … SELECT grants" being
declared. Effect authorizations spell the purpose `native-purpose:evaluator` (five sites) while the
purpose vocabulary says `evaluate`: a vocabulary drift to resolve in the `Purpose` declaration.

**Target.** `Role` (closed): members with annotations `login`, `member_of`, `owner` (publisher).
`Purpose` (closed): members with `role` (`maintenance` declares none). Schema defaults on the subset
definitions: `ph:read_roles` and `ph:frontier_guard: guarded|exempt`, plus a marker that the subset
is a physical schema (the compiler derives the schema set from it). Per-relation overrides with
the same annotations. Execute grants from each program declaration's purposes (R04 registry; until
then from the protocol `purposes` and a purposes field on the special-cased programs). Frontier
guard membership (`data_operation_storage.py:1952–1965`) becomes "relations of guarded schemas not
declared `exempt`". The TEMP grant (`target_installation.py:623–637`) becomes a typed program with
the database name as the one dynamic part.

**Closed and complete; what refuses.** At generation: a role or purpose name not in its
vocabulary (anywhere: grant, program purpose, effect authorization, read-role override); a purpose
with no role unless it declares none; a physical schema without declared defaults; an override on
a relation outside a physical schema. A forgotten exemption fails safe (an over-guarded write
refuses visibly). Migration: every literal reads the vocabulary through the compiled model;
interim consolidation onto the existing constants first is cheap and makes step B a one-source
move (`native_admission_functions.py:149` already does it). Independent control SQL takes role
names as data arguments.

## 7. Supersession (exact passages the new plan replaces or amends)

| Owner | Passage | Replaced by |
|---|---|---|
| `docs/plans/declared-data-operations/products-and-support.md:422–423` | "`validity_family` (null when no per-kind validator applies)" | two required columns; `none` explicit; undetermined conservative (RC05) |
| same, `:451–452` | "its per-kind check runs only when its lowered `validity_family` is non-null and checks only mutable premises (kernel digest, and cut trust …)" | generated dispatch over the family set plus the conservative validator |
| same, `:429–432` | "Validity compares `native_kernel_digest` …; a successor that changes the lowering re-lowers every admitted release" | kept until R05; this series re-prepares instead of re-lowering (§3) |
| ADR-0092 Decision (`docs/adr/0092-ddo-operation-authority.md:25–28`) | "implementation-owned typed Python definitions are admitted frontends" (grammar unstated, hand-validated) | RC04: grammar and vocabularies declared in LinkML with stated openness, closed field names, descriptive fields open; supersede ADR-0092 (accepted ADRs are immutable) carrying its decision forward |
| ADR-0131 Decision (`0131-model-owned-postgresql-programs.md:32–42`) | "…govern physical types and call correspondence"; "Convert remaining maintained owners forward" | RC01: facts programs dispatch on have one declared home; per-operation facts reach programs through lowered release rows; vocabularies are generator inputs; generation refuses only inconsistency and integrity omissions; the conversion clause becomes extraction |
| DESIGN §B4 head (`DESIGN.md:505–508`) | "Maintained native PostgreSQL behavior compiles from model-owned relations, call contracts and typed Python programs … Full source conversion remains open." | add declared vocabularies and lowered operation facts; drop the open-conversion sentence |
| DESIGN §B4, ADR-0122 paragraph (`DESIGN.md:513–518`) | "reusable only under its actual validator identity; … mutable family checks" | unchanged in substance; add the conservative validator as a family-like identity |
| DESIGN §B5 head (`DESIGN.md:853–855`) | "One captured LinkML closure supplies physical types, slot and value-set facts" | RC03: one composer and one compiled model per model-sources identity, projections with sub-identities |
| ADR-0024 (`0024-semantic-release-preparation.md:46`) and D2 preparation contract | "Unsupported required semantics refuse" | RC14: non-refusing `unassessed` diagnostics for undetermined declarations; operator decision 2026-11-19: no promotion boundary |
| `alembic_privileges.py:75` vs ADR-0103 Decision (`0103-ddo-privilege-policy.md:27–29`) | code default read roles | declared schema defaults (RC12) |
| `model/core.yaml:1034–1040`; `schema/pack.py:1–22` | `ci:lifecycle` and the pack rule | R15 openness annotation; then R13 retires both |
| R02 review text "the free-text `preparation` … stays unconstrained" | — | `Preparation` is open with known tested members (§2) |

## 8. Order and packages

Labels are placeholders. Native revisions: **two** for this scope (A and B below), batched by
capability; a third only if the conservative program cannot ship with step A.

| Pkg | Delivers | Needs | Migrates / removes | Native |
|---|---|---|---|---|
| L1 Compiled centre (R01, DA-004) | composer, `CompiledModel`, T1 holder, typed annotations | — | §1 sites; `metadata.py` globals | none (bytes identical) |
| L2 Vocabularies and openness (R15) | enums module, openness annotation, provisional status, pack rule in released model | L1 | `ci:lifecycle` consumers move; `schema/pack.py` rule moved | none |
| L3 Declaration grammar (R02, RC04) | `DataOperationDeclaration`, held Validator, diagnostics route, `Literal` checks | L2 | structural hand checks (§2 list) retire | none |
| L4 Family declaration and lowering (R02 rev., R07 A, RC05, RC01) + L5 conservative check (R16) | validity record in declaration/archive; two columns; lowering; generated dispatch and chain; family requirements; producer narrowings from dependencies; privileged owners; evaluator subset by declaration; owner-module captures removed; plus the "already declared" connections (state, universe, codec, shared-stream triggers) and the typed `support_contract` boundary | L3 (vocab and field); the 27 current literals gain explicit `validity_family` in the same package | the 19 sites in §3; classifier; `else_=True`; `_FACTORIES`, `_OPERATIONS`, factory dicts | **A** |
| L6 Integrity vocabularies (R03, R07 B, RC12) | `Role`, `Purpose`, schema defaults, overrides, grants from purposes, frontier guard by schema, TEMP grant typed | L2; independent of L4 | 198 literals; four purpose maps; schema-set literals | **B** |
| L7 Support-edge table (R08) | `SupportEdgeKind` table, one mapping, generated walks, explanation output | L2; native owner's population-edge ruling | `_revocation_causes`, Python scope key, `_reference_node` default | **B** |

**Acceptance evidence** (expectations independent of the code under test; hand-written
expected values, not outputs of the compiler or lowering):
- L1: frozen N29 desired-object bytes equal regenerated bytes; two captures held concurrently
  return distinct objects; an edit changing only comments in YAML that leaves bytes equal yields
  the same entry. A wrong composer changes bytes or merges captures and fails.
- L2: a hand-written pack that `inherits` a closed enum refuses; the same against a
  pack-extensible enum adds per-release rows (expected rows written by hand); a provisional
  member is accepted and reported.
- L3: a table of hand-written literals with expected outcomes: unknown field → invalid; profile
  outside the enum → invalid; ownership `experimental-shared` → accepted + `unchecked`; absent
  `validity_family` → accepted + `validity_undetermined`; `[none, contextual]` → invalid. All 62
  real modules compile with the diagnostics list equal to a hand-kept expected list.
- L4/L5: a small hand-authored model and fixture database with four operations whose ids appear in
  no former list: P claims two real families; Q declares `none`; R declares nothing; S claims a
  family whose requirement it violates. Expected, written by hand: lowered rows
  (`P: ({f1,f2},false)`, `Q: (∅,false)`, `R: (∅,true)`); S refuses at preparation naming the
  requirement. Then: a revocation in an unrelated scope of the same project invalidates R and
  not Q; a cut-trust change invalidates P through its grade-family premise; a completion of P runs
  both family guards (each guard's refusal provoked once by a violating completion). Perturbation:
  edit R's declaration to `none` and re-prepare: the descriptor `source_digest` is unchanged, the
  release id changes, R's next revocation-unrelated change leaves it valid. A dispatch that still
  defaulted to valid, a guard that still selected by id, or a lowering that copied the classifier
  each fails one of these.
- L6: a program declaring purpose `audit` refuses at generation; a role literal not in `Role`
  refuses; a new relation in a guarded schema without annotation gets the guard trigger and the
  schema's read roles (expected grants written by hand against `pg_class.relacl`); an `exempt`
  override removes the trigger only.
- L7: a fixture support graph (one OR-group under value substitution, one population chain) with
  hand-computed validity and scope sets per traversal profile; a reference lacking
  `derivation_id` refuses; change impact's causes equal the hand-computed revoking edges.

Test work follows the test series' contracts; these are the cases the design needs.

## 9. Flexibility check

| Design | Keeps cheap | Newly closed | Narrowing of today? |
|---|---|---|---|
| Compiled centre | trying a candidate model beside the running one; a model edit without restart | nothing | none |
| Vocabularies with openness | a pack adds members to a pack-extensible set; an unsettled term as a provisional member; an open `Ownership`/`Preparation` value | only what is closed today | none; `Preparation` stays open (the review's "unconstrained" understated its tested members) |
| Declaration grammar | descriptive fields stay free; recommended fields warn | field names (closed today) | none; an identity-excluded notes field remains an operator option |
| Validity three states | adding an operation with unknown validity semantics (declare nothing); claiming two families; a family before its validator (provisional) | a family name the kernel cannot validate (inconsistency) | none; today's undeclared case moves from permissive to conservative, which is the intent |
| Family requirements | a new member that meets the family's declared requirements needs no kernel edit; a third query encoder admitted by declared roles | requirements per family (integrity of the claim) | **watch**: requirements written as single values would close what the per-id pins vary (contextual profiles, forms, receipts); write them as allowed sets |
| Integrity vocabularies, guard defaults | a new native relation is guarded and readable by schema default | roles, purposes, grants, guard classification (closed by ADR-0103 already) | none |
| Support edges | knowledge relations and pack predicates untouched | an unrecognised support reference now refuses (today: episode) | intended; affects only native provenance rows |

## 10. Open premises and what settles each

- **P1** Whether `definition_identity` must cover the validity record: native owner's reading of
  every `definition_identity` consumer (recipe stays clean either way).
- **P2** The contextual CPU-receipt count (0 for scores, 1 otherwise, `contextual_admission_native.py:255–258`;
  `definition_admission_native.py:366–369`) has no declared source. Settle by tracing what produces
  CPU receipts; if not derivable from forms/preparation, add a declared execution-evidence field to
  the grammar.
- **P3** `structure.dossier/declared` (`structural_admission_native.py:1058`): is it a validity
  family member, a command class, or generic? Owner decision before L4.
- **P4** The evaluator-authorization derivation (§3 table) is inferred from the universe-by-id
  branch (`operation_event_native.py:1277`) and the declared effects; native owner confirms that
  "writes an evaluator-universe kind" implies the evaluator purpose for every operation.
- **P5** Population→episode support edge (`change_impact.py:381–382`) versus its absence in the
  validity edges: native owner rules which encoding is wrong before L7.
- **P6** Cut scopes of grade/fit/event lie in the request's project (assumed by the project-wide
  conservative snapshot): read `ddo_record_grade_completion_scopes` before L5.
- **P7** The rich module's further per-id branches (`rich_admission_native.py:582, 676, 920, 944,
  951, 1219, 1278`) were located, not read; each needs a declared selector or a family requirement.
- **P8** Whether the vocabulary module can be imported into the physical closure without the
  physical compiler refusing non-physical content (`physical_model_documents`, `schema/physical.py:154–163`);
  after L1 this is moot because both read the compiled model.
