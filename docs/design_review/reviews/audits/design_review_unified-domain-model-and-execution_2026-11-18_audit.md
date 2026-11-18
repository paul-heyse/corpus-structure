# Unified domain model and execution — recommendation audit (intentional flexibility)

**2026-11-18 · independent design-reviewer audit, on one operator-selected concern.** The auditor
wrote neither the review, the diagnostic audit it consumed, nor the code. The first reviewer did
not conduct this audit and is not taken to agree with its revised judgments.

| Field | Value |
|---|---|
| Principal review audited | [design_review_unified-domain-model-and-execution_2026-11-18.md](../design_review_unified-domain-model-and-execution_2026-11-18.md) with its supporting pages `unified-domain-model-and-execution/cache-design.md` and `dispositions.md` |
| Exact input revision | Repository commit `b4eb74f67` (all three files as committed there; recoverable from Git) |
| Source baseline | Frozen snapshot of commit `d78c98765` (the review's own baseline). The `domains/` packs, which the snapshot omits, were read from the same commit with `git show d78c98765:domains/...` |
| Diagnostic audit consumed | Broad audit publication `90467bde0` (unchanged since the review), with the 2026-11-18 independent challenge in the review inputs |
| Standard | Core 3.3, efficient-architecture heuristics 1.0, code-intelligence profile 1.4, corpus-structure binding (`docs/design_review/design_principles/standard.toml`) |
| Focus | Inherited from the review: combined (unified domain data model; execution fit; no hand-managed SQL; libraries as hypotheses with cachetools prioritised). Within it, the operator's concern of 2026-11-18: whether each facet of validation the review proposes takes away intentional flexibility that reflects the exploratory, progressively structuring nature of the work |
| Integrated output | The revised principal review and its two supporting pages at their original paths |
| Evidence | Static reading. Source facts: **Interface-checked by source inspection, 2026-11-18**. LinkML facts: **observed in installed source** (linkml and linkml-runtime 1.12.1 in the project environment, 2026-11-18). Remedies: **Proposed**. No probe, test, provider or database was run (all **not_run**) |

## 1. Outcome in brief

The review's diagnoses stand. There are genuine forgotten decisions that fail open: the validity
dispatch treats any family name it lacks as valid (`semantic/data_validity_native.py:272–288`,
`else_=True`); family membership lives in lists that must agree and do not have to
(`semantic/data_operation_compiler_native.py:468–520` against the guard lists); support-edge
classification falls back to "episode" for anything unrecognised
(`semantic/data_operation_projections.py:117–129`); guards and roles are code lists. Those
belong to the system's integrity, and closing them costs no exploratory freedom.

The remedy over-reaches in one consistent way. It reads every absence as a forgotten decision
and answers with a *required total classification*, a closed vocabulary and refusal at compile.
The source and the accepted design show that much of the absence in the declared space of
behaviours is intended latitude: operations that deliberately belong to no validity family, a
free-text ownership description, partial releases, vocabulary terms used before they settle,
and a vocabulary-openness declaration that the review's own retirement list would delete. At the
content layer the model already represents incompleteness explicitly and richly; the target
should extend that habit to the declared space of behaviours, not replace it with closure.

The revised design keeps one declared home for every governing fact, keeps refusal for internal
inconsistency (a name with no definition, a dispatch with no handler) and for integrity
(authorization, guards, support-edge kinds, custody), and replaces forced classification of
operations with **declared openness and graded consequences**: an operation may be left
unclassified, and the model says what that means (conservative validity, a non-refusing
diagnostic, and an operator-chosen promotion boundary).

Dispositions: of fourteen recommendations, nine are retained (R01, R04, R06, R09, R11, R14; R08
and R10 with sharpened wording; R12 with one sentence improved), four improved (R03, R05, R07,
R13), one corrected (R02, which also carries the review's §3.2), and none omitted. All
four review findings are retained; one finding (F05) and two recommendations (R15, R16) are
added. Of thirteen rule impacts, two are corrected (RC01, RC05), two improved (RC04, RC12), nine
retained, and RC14 is added. The overall decision (Revise) and the A1–A4 verdicts are unchanged;
the reasons for the A2 verdict are restated.

## 2. Where flexibility is intentional: a cited account

Three layers are distinguished throughout: **(a)** the knowledge content the pipeline discovers
and progressively structures; **(b)** the declared space of possible behaviours and links
(operations, products, support relations, vocabularies, packs, releases); **(c)** system
integrity and authority (who may read or execute, which relations are write-guarded, identity,
custody, publication).

### 2.1 Knowledge content (layer a): open by design, represented explicitly

The functional target is progressive. "Progressive grounded structure and granular
failure/capture assessment are the objective; complete records are a stronger outcome"
(`docs/design/DESIGN.md:62–66`, ADR-0070). ADR-0062 makes an independently attributable
structural contribution a useful unit that needs no complete-record parent, keeps "raw confidence,
interpretation disposition, field state, execution outcome, independent judgment and publication
standing" separate, and states that "missing output support is not inspected absence"
(`docs/adr/0062-progressive-contributions.md`, Decision). ADR-0024 says "repeated occurrences,
independent sources and disagreements survive fusion" and "cardinality one on selected values
cannot prohibit recording conflicting sources"; imported axioms outside the executable profile
"remain explicitly unexecuted" (`docs/adr/0024-semantic-release-preparation.md`, Decision).
ADR-0077 requires that "competing decisions require selection rather than latest-wins" and that
"a lexical candidate establishes neither mapping equivalence nor accepted knowledge". ADR-0059
leaves broader proposition comparison "explicitly unmodeled until a released mapping defines"
it (`DESIGN.md:325–329`).

The model represents this variability as **declared explicit possibilities**, not as silence:

- missing-value reasons `absent`, `explicit_null`, `unknown`, `not_applicable` and coverage
  outcomes `complete`, `partial`, `unanalysed`, `failed` (`model/semantic/core.yaml:600–612`);
  an `UnresolvedBinding` expression binding (`:301–305`); a validity interval whose "absent
  inclusivity remains unknown" (`:328`);
- missing, null and populated kept distinct by explicit opt-in nullability (ADR-0120,
  `cs:nullable`);
- identity values with four states, `present`, `known-absent`, `unavailable`, `unknown`
  (`semantic/data_operation_identity.py:97–102, 124–131`);
- characterization dispositions `no_match`, `insufficient_evidence` and `missing_candidate`, the
  last for "a source-supported host ... absent from the frozen alternatives"
  (`model/semantic/characterization-questions.yaml:29–30, 111–113, 128–130`); an alias state
  `observed | known_empty | unknown` (`model/semantic/characterization.yaml:923`); a support state
  `unassessed` (`model/semantic/data-operation-contextual.yaml:180, 233`);
- proposals with standing `private_proposed`, competing `alternative` proposals with a
  `faithful` flag and reason, explicit `unsupported` proposals, and per-family coverage outcomes
  `produced | empty | partial` (`model/semantic/data-operation-rich-proposals.yaml:9–70`);
- structural gap reports `unresolved_binding`, `unknown_applicability_premise`,
  `unconnected_supported_comparison` (`serve/structural_gaps.py:22–26`).

None of the review's recommendations acts directly on this layer. Some of its wording ("closed
vocabularies (domain and operational)", "closed-set checks refuse drift") can be read as if it
did; the revision makes the boundary explicit.

### 2.2 The declared space of behaviours (layer b): partly open, partly by absence

- **Domain packs extend the model by inheritance.** The statistics pack defines record kinds as
  `is_a` extensions of core abstract classes (`domains/statistics/semantic.yaml` at
  `d78c98765`, for example `MeasurementValueRole is_a RecordClassification`), and a release
  composes the pack schemas it names (`domains/statistics/operations.yaml:1–12`). "New admitted
  class/property definitions change registry rows without physical DDL" and "dynamic domain
  definitions become registry data over a stable relational core" (`DESIGN.md:1208–1222`,
  ADR-0031, ADR-0033, ADR-0024). A relation or product kind tried in one pack therefore creates
  no physical relation and touches none of the review's physical closures.
- **Vocabulary openness was declared in the earlier model.** `Lifecycle` has two members:
  `static` ("Changes with code; enforced by a digest-named CHECK") and `schema_version`
  ("Extendable by packs; enforced by per-version member rows and FKs")
  (`model/core.yaml:1034–1040`), applied per enum (`:895, 913`). The pack loader enforces it: "a
  pack enum may extend a core set (`inherits` / `include`) only when the model declares that set
  `schema_version`; a static set refuses pack members" (`schema/pack.py:1–22`). The released
  model has no successor declaration: its `expand_enum` (`semantic/ontology.py:328–410`) composes
  `inherits`, `include`, `minus`, `concepts` and `reachable_from` without any openness property.
  The review's R13 retires `core.yaml` and `schema/pack.py` without carrying this distinction
  forward (finding F05 below).
- **Dynamic and partly checked vocabularies exist.** Released enums can take members from a
  pinned ontology through `reachable_from` (`semantic/ontology.py:381–395`), and preparation
  records members it could not check as non-refusing `unchecked_term` diagnostics
  (`semantic/prepare.py:485–530`), which the validation report maps to category `unassessed` and
  `complete=False` (`semantic/operation_reporting.py:372–410`). ADR-0076 gives optional
  terminology fields explicit permissible values that "describe attributed source
  interpretations, not global identity or selected knowledge".
- **Release composition is optional by design.** The acquisition manifest selects groups by flags
  and optional provider profiles (`visual: false`, `downstream: true`, optional learned
  selections; `domains/statistics/operations.yaml:28–66`), and `primary_operation_inputs` adds
  collections conditionally (`semantic/primary_operations.py:131–200`). An omission is refused at
  compile or demand freeze (audit DA-073), so the cost of the flag logic is locality, not
  correctness.
- **The operation grammar is closed in its field names and open in its descriptions.** The hand
  validator refuses any field outside `_METADATA_FIELDS` and any profile outside `_PROFILES`
  (`semantic/data_operation_compilation.py:85, 104–140, 1068–1073`), closes forms to scalar,
  batch, stream (`:1491–1493`) and the kind universe to ordinary, source, evaluator (`:341–348`).
  It leaves `ownership`, `preparation` and `cancellation` as free nonempty text
  (`:1559–1566`). A survey of literals at `d78c98765` found sixteen distinct ownership values
  (most used once to five times), six preparation values and four cancellation values; the only
  readers of ownership test for `"immutable"` (`semantic/characterization_ports.py:1059`,
  `semantic/sentence_products.py:1403`, `semantic/formal_products.py:986`).
- **"No validity family" is a designed state.** The plan defines the lowered column as "null when
  no per-kind validator applies" (`docs/plans/declared-data-operations/products-and-support.md:422–423`)
  and runs the per-kind check "only when its lowered `validity_family` is non-null" (`:451`). The
  review itself found that "several operations with family-like ids are deliberately outside every
  family". What the plan did not do is distinguish that designed state from a forgotten entry.
- **Reuse is withheld, not execution refused, when identity is incomplete.** ADR-0092: "Unknown
  required determinants refuse reusable identity"; the slice fingerprint refuses only
  *required* unknowns (`semantic/data_operation_identity.py:378–387`). This is an existing graded
  consequence: incompleteness costs a privilege (reuse), not the ability to run.

### 2.3 Integrity and authority (layer c): closed by intent

ADR-0103 declares table privileges completely: "PUBLIC and undeclared grantees have no rights",
and "desired policy never comes from reflected grants". The task lifecycle is a declared state
machine (`model/semantic/data-operation-native.yaml:5–14`). Support edges are provenance among
native rows (uses, episodes, populations, originals; `semantic/data_operation_projections.py:132–175`),
not knowledge relations. Custody refuses drift (ADR-0124). Closure here is the purpose.

### 2.4 Summary

| Kind of variability | Layer | How it is represented now |
|---|---|---|
| Partial, missing, unknown, competing or unsupported content | a | Declared explicit states (§2.1) |
| New record, product or relation kinds in a pack | b | Declared by inheritance in the pack; registry rows, no DDL |
| Pack extension of a shared vocabulary | b | Declared (`ci:lifecycle`) in the earlier model only; no released-model successor |
| Vocabulary terms not yet checked or settled | b | Non-refusing `unchecked` diagnostics; ontology-derived members |
| Operations with no validity family | b | Left open by absence (`NULL`), indistinguishable from a forgotten entry |
| Operation resource ownership, preparation and cancellation descriptions | b | Open free text |
| Releases containing only some operations | b | Profile flags in code; omissions refused at compile |
| Incomplete identity determinants | c | Declared graded consequence: reuse withheld |
| Roles, grants, guards, lifecycle, support-edge kinds | c | Closed; partly held in code lists |

## 3. Which layer each proposed constraint acts on

"Closed today" says whether the current system already closes the set and whether that closure
is recorded as intentional. "Newly closes" is what the first-round proposal adds.

| Proposed constraint (review location) | Layer | Closed today? | Newly closes | Legitimate exploratory move made harder | Audit judgment |
|---|---|---|---|---|---|
| Every operation declares `validity_family`; absence refuses at compile (R02, §3.2, RC05) | b, with a validity consequence in c | Open by absence; the null state is intentional in the plan, the conflation with "forgotten" is not | Every operation must classify itself before it can compile | Adding an operation whose validity semantics are not yet known; an operation in several families | Correct: three explicit states plus a conservative default (R02, R16) |
| Family dispatch generated with no open default; generation refuses a family without a validator (§3.2) | c (internal consistency) | Open default `else_=True` for a named but undispatched family: incidental | A dangling family name | None legitimate; a family whose validator is not written yet can be declared provisional | Retain, with a provisional status |
| Completion guards dispatch on the lowered family instead of id lists (§3.2) | c | Lists that must agree: incidental | Nothing new | None | Retain |
| Closed-world validation of operation literal fields (R02) | b | Closed today and deliberately so (`_mapping` refuses unsupported fields) | Nothing | None beyond today | Retain; an identity-excluded notes field is an operator option |
| `Profile`, `KindUniverse`, `Form` as LinkML enums (R02) | b | Closed today in Python; each drives compilation or execution | Nothing | None beyond today: a new profile or form needs compiler support anyway | Retain |
| `Ownership` as a closed enum (R02) | b | **Open** today (free text, sixteen values) | Every new ownership shape needs a vocabulary edit first | Describing the resource behaviour of an experimental operation | Correct: open vocabulary with known, checked members |
| `SupportEdgeKind` with a traversal table; one walk (R08) | c | Closed in code, but `_reference_node` defaults unknown references to "episode": incidental | Unknown reference kinds refuse | None in knowledge; a new provenance node kind is a native schema change anyway | Retain; state that knowledge relations are untouched |
| `Role`, `Purpose`; grants from purposes; explicit read roles (R02, R03, RC12) | c | Closed by ADR-0103 | Nothing semantically; moves the home | None | Retain; allow a declared schema-level default |
| Required frontier-guard classification per relation in guarded schemas (R03, §3.2) | c | Closed in a code tuple: location incidental | A classification on each native relation in guarded schemas | A new native relation needs one more annotation | Improve: declared schema-level default `guarded`, per-relation exemption |
| `acquired_by` on every operation (R02, DA-073) | b (release composition) | Omission refused today; the field does not exist | A new authored field on every literal | Every new operation must name a source family | Improve: derive from the capturing source collection; declare only to override |
| Task states from the protocol lifecycle (§3.2) | c | Closed | Nothing | None | Retain |
| Closed-set checks of Python `Literal` copies against enums (R02, §6) | internal consistency of code copies | Partly | Nothing beyond the declared set | None, provided open vocabularies check known spellings only | Retain, sharpened |
| Custom catalogs as LinkML-typed instance data (§6) | b | Unknown (consumers not traced) | Structural validation | Adding an experimental field to a catalog | Retain; closed-world where fields drive behaviour; disposition vocabularies keep their explicit open states |
| Program registry refuses an undeclared callee (R04) | c | Bound only at install today | A missing callee refuses at generation | None | Retain |
| Code-closure identity fails on an unresolvable dynamic import (R05) | c | Hand lists today | A served read with a dynamic import refuses | An exploratory served helper using a dynamic import | Improve: withhold reuse instead of refusing service, as ADR-0092 does |
| Each served query declares a reuse basis (R10) | b and c | Keyed by read instance | A declaration per query | None if absence means `cut` | Retain, with the safe default stated |
| DuckDB cast to `ENUM` where membership matters (R12) | b | No casts today | Analysis refuses values outside the enum | Analysing data that uses terms not yet in the vocabulary | Improve: cast only for vocabularies declared closed |
| Retire `core.yaml`, `schema/pack.py` (R13) | b | — | Removes the only declared openness distinction | Pack extension of a shared vocabulary loses its declaration | Improve: carry openness forward first (R15) |

## 4. Absence versus declared openness

**Where absence is a forgotten decision.** A family name with no dispatch entry; an operation
missing from one list of a family that is present in another; an unknown support reference
treated as an episode; a relation in a guarded schema missing from the guard tuple; a role
granted by name matching. In each case the system already *intends* a definite answer and the
code fails to look it up. These are integrity risks; the review's closures fix them and are
kept.

**Where absence is intended latitude.** An operation that needs no family-specific premise
check; an operation whose validity semantics nobody has worked out yet; a resource-ownership
description that is only prose to every consumer except the one value they test; a release that
omits optional groups; a vocabulary member that has been used before it was settled. Here the
right target is to **represent** the latitude, with stated consequences, rather than to force a
classification or keep the silence.

The model should be able to say, for any declaration in layer (b), one of: *declared* (a named
value); *declared none* (the possibility is positively ruled out); *undetermined* (not yet
decided, with a stated conservative consequence); and for vocabularies, whether the set is
*closed*, *pack-extensible* or *open with known members*, and whether a member is *provisional*.
This mirrors what the content layer already does with `MissingReason` (`unknown` distinct from
`not_applicable`), and what the identity layer does with `OptionalValue` and required versus
optional unknowns.

**Graded strictness.** Declare when known; record a non-refusing diagnostic when not; let the
operator choose a promotion boundary at which an undetermined declaration refuses. The
preparation report already supports this: `unchecked` diagnostics map to `unassessed` and make
the report incomplete without refusing (`semantic/operation_reporting.py:372–410`).

**What LinkML 1.12.1 offers** (observed in installed source, 2026-11-18):

- Enums are closed for validation; the metamodel's enum expression has no openness slot
  (`linkml_runtime/linkml_model/model/schema/meta.yaml`, `enum_expression` slots:
  `code_set`, `pv_formula`, `permissible_values`, `include`, `minus`, `inherits`,
  `reachable_from`, `matches`, `concepts`). Openness therefore needs either a project
  annotation (the earlier model's `ci:lifecycle` is the precedent; the released preparation
  profile refuses unsupported annotations, `semantic/prepare.py:259`, so a new annotation is a
  deliberate profile extension) or a slot range of `any_of` the enum and `string` (the metamodel
  documents `any_of` range expressions as a way to combine ranges).
- Permissible values carry `common_metadata`, which includes `status` and `deprecated`
  (`meta.yaml:3271–3296`, `2575–2614`), so a member can be marked provisional without a custom
  annotation.
- Slots can be `recommended` ("should be present ... applications must not treat this as an
  error", `meta.yaml:1758–1766`), and `linkml.validator.plugins.RecommendedSlotsPlugin` reports a
  missing recommended slot with `Severity.WARN`
  (`linkml/validator/plugins/recommended_slots_plugin.py:9–29`). Declare-when-known is
  therefore native.
- Dynamic enums by `reachable_from` are already used by the project (`semantic/ontology.py`).
  `pv_formula` with a `code_set` defines a set by external code system without listing members.
- `in_subset` membership is positive-only. The review rejected it because it "does not fail
  closed"; with a conservative default for absence (R16), positive-only membership is safe where
  it is convenient.

**Where the right answer is not to constrain.** The free-text `preparation` and `cancellation`
descriptions, the descriptive parts of `ownership`, and the knowledge content itself. The model
should check only what a consumer interprets.

## 5. Dispositions

### 5.1 Recommendations

| Ref | Disposition | Reason and consequence |
|---|---|---|
| R01 One composer and a held compiled model | Retain | Untouched by the concern. One factual sharpening: the released `expand_enum` is `semantic/ontology.py:328`; the earlier `schema/model.py:333` is the one that carries the openness rule and retires with R13 after R15 carries the rule forward. |
| R02 Declare the governing vocabularies and required classifications | **Correct or adjust** | Keep: one declared home for family membership; generated dispatch, guards and completion; a dangling family name refuses; LinkML-declared grammar with closed field names; `Profile`, `KindUniverse`, `Form`, `SupportEdgeKind`, `Purpose`, `Role` closed. Change: `validity_family` becomes an optional, set-valued declaration with three meanings (named families; `none`; absent or `undetermined`), absence receives conservative validity and a non-refusing diagnostic instead of a compile refusal (R16); a family member may be `provisional` (no validator yet; its members are treated conservatively); `Ownership` stays an open vocabulary with known checked members; `acquired_by` is derived from the capturing source collection and declared only to override. The review's §3.2 is rewritten accordingly. |
| R03 A typed physical profile | Improve | Integrity layer; keep. Replace "required slots so absence refuses" with declared schema-level defaults (guarded schemas default to `guarded`; read roles default to a declared schema value) and per-relation overrides, so forgetting is safe and there is no code default. |
| R04 Typed program registry | Retain | Integrity and internal consistency; no exploratory cost. |
| R05 Identity from declared dependencies | Improve | Keep the layering. Where a served read's code closure cannot be resolved (a dynamic import), withhold reuse (no cache entry, no resumable continuation) rather than refuse to serve, matching ADR-0092's treatment of unknown determinants; code custody's refusal of drifted code is unchanged. |
| R06 The execution path generates nothing | Retain | Untouched. |
| R07 Remaining conversion and its order | Improve | The ordering argument stands. The gate is narrowed: each module's conversion waits only for the facts it holds (its families' membership, the roles it grants), not for the whole declaration schema (ownership, grammar migration, release composition). Generated programs read the three-state family. |
| R08 One declared support-edge meaning | Retain (sharpened) | Support edges are provenance among native rows, closed by purpose; the `_reference_node` open default is a forgotten decision. Add that knowledge relations and pack predicates are not support edges and stay open in packs. |
| R09 Cache system | Retain | Untouched. |
| R10 Served-read reuse basis | Retain (clarified) | State that a query without a declaration uses `cut`, the safe basis; no exploratory served query needs to declare anything. |
| R11 Carried assurance | Retain | Untouched; the conservative validator of R16 has its own validator identity and is replayed like any family. |
| R12 Analytical placement | Retain, one sentence improved | Cast to a DuckDB `ENUM` only for vocabularies declared closed; open and pack-extensible vocabularies stay `VARCHAR`, so analysis does not refuse unsettled terms. |
| R13 Retirement | Improve | Before `core.yaml` and `schema/pack.py` retire, the openness declaration they carry (`ci:lifecycle`) moves to the released model (R15), and the released route for pack extension (pack schemas imported by the release) is confirmed to cover what the earlier pack loader allowed. |
| R14 Scientific policy from its declaration | Retain | Untouched; a numerical policy is integrity, not exploration. |

### 5.2 Review findings

| Ref | Disposition | Reason |
|---|---|---|
| F01 Per-acquisition check regenerates the capture | Retain | Untouched. |
| F02 Unlocked and unbounded memos | Retain | Untouched. |
| F03 DuckDB connections take defaults | Retain | Untouched. |
| F04 SQLite SQL by concatenation | Retain | Untouched. |

### 5.3 The review's §3.2 and the fact-authority table rows that require or refuse

| Item | Disposition | Revised content |
|---|---|---|
| §3.2 "Fail-closed classification" | Correct or adjust | Renamed "Declared homes, explicit openness and safe defaults": integrity memberships closed; operation classifications three-state with a conservative default; vocabularies declare openness; refusal reserved for inconsistency and integrity |
| Row: operational vocabularies | Correct or adjust | Split by declared openness: closed (profile, kind universe, form, support-edge kind, purpose, role, task state); open with known members (ownership); validity family closed in its named members, optional on operations |
| Row: validity family membership | Correct or adjust | Optional, set-valued; `none` explicit; absence means undetermined with conservative validity and a diagnostic |
| Row: family contract | Improve | A family member names its validator program, or is `provisional` |
| Row: release composition | Improve | Source collection derived from the capturing module; a manifest of requested operations or families; partial releases remain ordinary |
| Row: frontier-guard membership | Improve | Declared schema-level default with per-relation exemption |
| Row: table read grants | Retain (clarified) | Declared default per schema, explicit per relation where it differs |
| Row: domain value sets | Improve | Enums declare openness (closed, pack-extensible, open with known members); provisional members by `status` |
| Rows: roles, purposes, execute grants, task states, support-edge meaning, program set, code identity | Retain | Integrity layer |
| New rows | Added | Vocabulary openness and member status (R15); undetermined declarations and their consequences (R16) |

### 5.4 Rule impacts

| Ref | Disposition | Reason and revised content |
|---|---|---|
| RC01 | **Correct or adjust** | The original wording ("membership and governance facts ... come from declarations and generation refuses an undeclared member") is the line the operator objected to. Revised: facts that programs dispatch on have one declared home and programs read it instead of restating it; an undecided membership is declared as undetermined and programs apply its stated conservative consequence; generation refuses only internal inconsistency and omissions in the integrity layer; independent controls take expectations as data; the remaining conversion follows the declarations it consumes. |
| RC02 | Retain | Untouched. |
| RC03 | Retain | Untouched. |
| RC04 | Improve | Keep both ADR-0092 routes and a LinkML-declared grammar for the Python route; add that each vocabulary in that grammar declares its openness and that descriptive fields stay open. |
| RC05 | **Correct or adjust** | Instead of "required enum with explicit `none`": the plan's null stops meaning "no per-kind validator applies"; that meaning is declared as `none`; absence means undetermined and receives conservative validity; the field may hold several families. If the plan's rule is kept unchanged, the forgotten and the not-applicable cases stay indistinguishable and the A2 gap remains. |
| RC06–RC11 | Retain | Untouched by the concern. |
| RC12 | Improve | Roles and purposes move to the model as before; defaults are declared per schema in the model rather than as code constants. |
| RC13 | Retain | Untouched (R10's safe default is a clarification). |

## 6. Additional findings and recommendations

**F05 — The released model cannot say whether a vocabulary is open, and the target would delete
the only place that could.** The earlier model declares per enum whether a set is `static` or
pack-extensible (`model/core.yaml:1034–1040`, enforced by `schema/pack.py:1–22`). The released
model's vocabulary expansion (`semantic/ontology.py:328–410`) and preparation
(`semantic/prepare.py:480–530`) carry no such property: every released enum is closed in
validation, and pack extension of a shared set is neither declared nor refused. Consequence:
A2 model adequacy; an intentional distinction is not represented in the authoritative model, and
the review's R13 would retire its last representation. Correction: R15. Closure evidence: each
released enum declares its openness and preparation enforces it; R13's retirement leaves no
openness rule only in the earlier model.

**R15 — Declared openness of vocabularies.** Each released vocabulary declares one of: *closed*
(changes with code; programs may dispatch on it; checked at compile, in physical checks and in
analysis casts), *pack-extensible* (a pack may add members through `inherits` or `include`;
members are per-release vocabulary rows), or *open with known members* (any string is accepted;
known members carry meaning that consumers may test; unknown values carry none and are reported,
not refused). Individual members may be marked provisional through the LinkML `status` slot that
permissible values already carry. Realization: a released-model successor of `ci:lifecycle`,
admitted by the preparation profile; `any_of` an enum and `string` where a slot accepts an open
vocabulary; the existing `unchecked` diagnostic route for unknown values of open vocabularies.
Consumers: closed-set checks of Python `Literal`s, physical checks through `ph:values_from`,
DuckDB `ENUM` casts (R12), pack loading. Evidence: F05; §2.2. Label: Proposed.

**R16 — Graded consequences for undetermined declarations, starting with validity families.**
An operation's `validity_family` is optional and set-valued. Its states and consequences:

- *one or more named families*: each family's validator runs; validity is their conjunction;
- *`none`*: a positive claim that only generic validity applies (outcome, revocation, support
  propagation), so derivations survive changes of trust and kernel;
- *absent or `undetermined`*: the operation compiles and runs; preparation records a
  non-refusing diagnostic; validity is generic validity plus a **conservative premise check**
  under which a derivation is valid only while the trust snapshot and validator identity it was
  produced under are unchanged. This over-invalidates and never under-invalidates;
- a family member may be *provisional* (declared, validator not yet written); its members are
  treated as undetermined; generation refuses a non-provisional family without a validator.

The conservative check needs premises the store already records in part: publication receipts
hold `trust_snapshot` and an optional `validating_kernel_digest`
(`model/semantic/data-operation-physical.yaml:475–484`), each support row records the trust scope
and epoch it relied on (`:458–466`), and demand reads record a trust snapshot and kernel digest
(`:619–631`). Whether every episode can be tied to the snapshot it consumed is for the native
owner to confirm (Proposed; feasibility open). The residual risk the default cannot cover is a
family-specific premise outside trust and kernel, such as the contextual linguistic premise
(audit DA-070); that risk is why a family binding exists, and it is visible as an `undetermined`
diagnostic rather than silent. A **promotion boundary** at which undetermined declarations refuse
is the operator's choice (RC14): none; activation of the default release; or knowledge
publication. The auditor's recommendation is none, because the conservative default already
removes the integrity risk, with the diagnostic as the pressure to classify.

The same pattern is offered, not imposed, for other layer (b) declarations that may be unknown
when an operation is first written. The existing identity rule (unknown required determinants
withhold reusable identity) is its precedent.

**RC14 — ADR-0024 and the D2 preparation contract.** Add that preparation distinguishes
refusing diagnostics (unsupported or inconsistent semantics, integrity omissions) from
non-refusing `unassessed` diagnostics for undetermined declarations, and record the promotion
boundary the operator chooses. If kept unchanged, R16 still works through the existing
`unchecked` route but the boundary stays undecided.

## 7. Effects on the combined design

- **A2 is still violated, for a restated reason.** The MUST is met by an adequate model that
  governs behaviour. The revised target meets it by making "not applicable" and "not yet decided"
  distinct, declared states with governed consequences, not by forcing every operation into a
  class. The fail-open dispatch remains the violation in today's code.
- **Order of work.** Step 2 of the review's order shrinks: family membership with its three
  states, roles and purposes, guard defaults and vocabulary openness. Grammar migration of
  ownership, preparation and cancellation and the derivation of source collections no longer gate
  the PostgreSQL conversion.
- **Identity interaction.** R05's per-family validator identity extends to the conservative
  validator, which is one more program in the registry with its own identity; receipts of
  multi-family operations carry each family's identity.
- **Contextual pin.** Unaffected: it compares declared per-operation facts between distinct
  inputs.
- **No new machinery class.** The revision uses LinkML's own `status` and `recommended`, the
  project's existing diagnostic outcomes and identity states, and one conservative validator
  program. It removes the need for every literal to carry two new required fields.

## 8. What would change this judgment, and what the operator decides

- If the native owner finds that a conservative premise check is not realizable (episodes cannot
  be tied to the trust snapshot they consumed), undetermined operations must at least lose reuse
  across premise changes, or the review's required classification returns for operations that
  consume trust cuts.
- If family membership turns out to be derivable from declared inputs (an operation that consumes
  a trust-bearing cut or a linguistic premise is necessarily in the corresponding family), it
  should be derived and the field reduced to an override. The first reviewer's helper showed it
  is not derivable from today's compiled fields; whether it is derivable from declared input
  roles was not examined.
- If an operation needing two family validators never arises, the set-valued field can be
  simplified to a single value at no loss.

Operator decisions: the promotion boundary (RC14); whether `Ownership` stays open (the audit
recommends open with known members); whether operation literals get an identity-excluded notes
field for experimental metadata (closed field names otherwise stay); LinkML or pydantic for the
structural grammar (unchanged from the review); and the review's existing decisions (RC01–RC13,
deletion of the two migration trees, the trust decision of RC08).

## 9. Coverage

Read in full: the principal review and both supporting pages at `b4eb74f67`; ADR-0092, ADR-0062,
ADR-0120; the decisions of ADR-0017, 0022, 0024, 0076, 0077, 0093, 0103, 0108, 0109; DESIGN §1
and the §B passages on progressive contributions, release preparation and extension; D2
"Effective operation compilation and authoring"; the plan passages at
`products-and-support.md:405–470`; audit DA-070, DA-073, DA-074. Inspected at the cited lines:
the operation grammar validator, the family classification and dispatch, the support walk's
reference classification, the identity value states, vocabulary expansion and preparation
diagnostics, release composition, the rich-proposal, characterization and core models, the
structural gap request, the physical model's trust and kernel columns, and the LinkML metamodel
and recommended-slots plugin. Sampled: `domains/statistics/semantic.yaml` and `operations.yaml`.
Not read: `schema/rulelang.py` and the pack rule language, D1 and D5 in full, the remaining DDO
plan companions, generator bodies, and the challenge and lane reports beyond targeted searches.
Not run: any test, probe, provider or database. The cache, identity and execution
recommendations were assessed only for whether the concern touches them.
