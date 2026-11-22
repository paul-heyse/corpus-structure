# Semantic model and authority

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
Every finding on this page was re-read at that source and carries an "Update, 2026-11-18"
paragraph that states its status; body text was corrected where cited code moved, and a
sentence that keeps an earlier date says so. Source paths omit
`python/corpus-structure/src/corpus_structure/`; `domains/` is at the repository root. Counts
are search or script counts and state their method. The current model owners are described in
the [domain model map](domain-model-map.md).

The findings below share a shape: a fact the declared model already holds, or could hold, is
written a second time by hand in code. They differ in what goes wrong when the copies drift,
so they are separate findings.

**What "generated from the captured model" means on this page.** Native programs (generated
PostgreSQL routines) are produced by generator modules named `semantic/*_native.py`. In every
admission module regenerated in `d78c98765..5139eaba3`, the generator receives the captured
SQLAlchemy `MetaData` (the compiled description of the physical tables) and resolves each
relation and column name against it; a missing relation or column fails at generation
(`semantic/contextual_admission_native.py:87–93`). The generator signatures take only
`MetaData` (`operation_event_native.py:208`, `record_policy_completion_native.py:206`,
`data_product_admission_native.py:127`, `structural_admission_native.py:1677`,
`contextual_admission_native.py:175`, `definition_admission_native.py:47`,
`artifact_admission_native.py:29`, `rich_admission_native.py:1927`,
`source_admission_native.py:1278`, `native_admission_release.py:343`), and none imports or
receives the effective operation model or the protocol (search for the model's entry points in
the nine modules: no hit). So statements are typed and relations are model-derived, while every
fact that identifies *which operation* (family, producer, entry point, profile, role) is a
string written in the generator. No operation fact can be derived there, because the object
that holds operation facts is not an input.

<a id="da-070"></a>

## DA-070 — Validity families and family contracts are assigned from hand-written operation-id lists, and an unlisted operation is treated as valid

**Update, 2026-11-18, source `5139eaba3`.** Stands, with a changed footprint that is also
wider. The contextual, definition, artifact, rich and operation-event guards were converted
from hand-written PL/pgSQL to typed programs (`fc6df4742`; `1556c7638`; `d4d62e410`,
`b834ddfdb`, `084f02980`, `c024010b8`; `4760982d8`, `6d5f45920`). In every case the text
`NOT IN ('…')` became `.not_in(tuple)` or `.is_distinct_from("…")` with the same ids. No list
was removed, no guard selects itself any other way, and the model gained no family
declaration: the classification, lowering and dispatch files have no commit in the range, and
the column is still an optional string (`model/semantic/data-operation-physical.yaml:88`). The
"note for the next conversion step" that this section carried on 2026-11-18 at `d78c98765`
predicted that converting these modules before family membership was declared would transcribe
the lists a second time. That is what happened.

**FP-04/A2; DP-01, DP-03, DP-06.**

**Twelve lists or literal chains now hold family membership** (counted by reading each guard):

| # | List | Site | Shape for an unlisted operation |
|---|---|---|---|
| 1 | Classification: seven families, 27 operation ids | `semantic/data_operation_compiler_native.py:470–529` | A `CASE` with no `ELSE`: returns null |
| 2 | Dispatch from family to validator | `semantic/data_validity_native.py:272–288` | `else_=True`: valid |
| 3 | The guards that completion calls (fourteen names) | `semantic/data_completion_settlement_native.py:548–563` | Every guard is called; each selects itself |
| 4 | Evaluator-authorization subset (three ids) | `data_completion_settlement_native.py:576–587` | No authorization step |
| 5 | Live-completion chain of literal ids | `data_completion_settlement_native.py:744–803` | Falls through |
| 6 | Contextual: one twelve-key dictionary of ids and entry points, used three times | `semantic/contextual_admission_native.py:188–201`; used at `:215, 568, 736` | Guards return; validator returns true |
| 7 | Definition: `_OPERATIONS` with a positional `_FACTORIES` | `semantic/definition_admission_native.py:33–44`; used at `:345–350, 386, 418` | Guard returns; validator returns true |
| 8 | Artifact: one literal id, three times | `semantic/artifact_admission_native.py:112, 147, 217` | Guard returns; validator returns true |
| 9 | Rich: three separate lists (validator, four ids; preparation dictionary, three; preparation guard, three) | `semantic/rich_admission_native.py:816–823, 606–622, 903–910` | Validator returns true; guard returns |
| 10 | Operation event: `_OPERATIONS` (four ids) | `semantic/operation_event_native.py:55–60`; used at `:350, 1287, 1359` | Guards return; validator returns true |
| 11 | Record grade: the constant `GRADE_OPERATION`, imported from the operation's owner module | `semantic/record_grade_native.py:55, 534, 702` | Guard returns; validator returns true |
| 12 | Record fit: one literal id | `semantic/record_policy_completion_native.py:1140, 1170, 1471` | Guards return |

The lists agree today. A scripted set comparison of the classifier's contextual segment with
the keys of the contextual dictionary gives twelve of twelve; definition (four), rich (four),
operation event (four) and artifact (one) agree by reading. The operation-event authorization
subset deliberately omits the score operation. Inside the contextual module the duplication
fell from two inline copies to one dictionary; in the rich module one inline list became three
separate lists.

Lowering stores each operation's `validity_family` by calling `ops.ddo_classify_validity`
(list 1); the generator's `model` argument is not used for this. Release lowering stores the
result (`data_operation_compiler_native.py:916–926`). The archived effective operation is in
scope at that point, and the operation's dependencies are lowered from it in the same block
(`:905–911`). Producer validity then dispatches on the stored column through list 2: an
operation with no family, or with a family name the dispatch lacks, never has its family's
dependency premises evaluated.

**The early-return guards (confirmed at the guard sites, not end to end).** Every family guard
begins with a test of the shape `If(operation.not_in(<hand list>), (Return(),))`, and every
family validator returns true for an operation not on its list:

- contextual: `contextual_admission_native.py:215` and `:568` (return), `:736` (return true);
- definition: `definition_admission_native.py:386` (return), `:418` (return true);
- operation event: `operation_event_native.py:350` and `:1287` (return), `:1359` (return true);
- artifact: `artifact_admission_native.py:147` (return), `:217` (return true);
- rich: `rich_admission_native.py:903–910` (return), `:816–823` (return true);
- record grade and record fit: `record_grade_native.py:534, 702`;
  `record_policy_completion_native.py:1140, 1170`.

An operation meant to belong to a family but absent from its lists is therefore neither
refused at generation nor checked at run time; it skips the guard. Nothing outside the lists
records the intent that it belongs. These lines were read in the snapshot, and the independent
challenge of this update found no upstream check that refuses a null family or makes these
returns unreachable: lowering stores the classification with no refusal on null
(`data_operation_compiler_native.py:916–960`). `ddo_require_definition_producer` does refuse an
unlisted operation (`definition_admission_native.py:358`), but it is reached only after the
completion guard's early return at `:386`. What other layers do with such an operation
afterwards was not traced, so the consequence is established at the guard sites only.

**Consequence.** An omission fails open, silently, at three levels: classification (null
family), dispatch (valid by default) and each guard (early return). What an omitted member
loses depends on the family. The generic support walk and revocation still apply to every
operation. For the artifact, definition and rich families, and for contextual operations other
than scores, the family validator adds only the digest-gated replay of
[DA-068](execution-fit.md#da-068). Changing premises are lost for record grade, record fit and
operation events (cut trust) and for contextual scores (the linguistic premise): for those, an
omitted operation's derivations stay valid and reusable after their premises change.

The plan defines the column as null "when no per-kind validator applies"
(`docs/plans/declared-data-operations/products-and-support.md:423, 452`), so a missing entry is
indistinguishable by design from an operation that needs no validator. No compile-time or
admission-time check ties family membership to the model. Every edit to one of these lists is
also a native source edit, so it changes the kernel digest.

**The kernel also narrows variability that the declaration allows** (inferred from two texts,
not run). The scoring operation declares its `query` input by kind and declares dependencies
only on the vector selection (`methods/contextual_scoring.py:99–130`), while the kernel admits
a query only from two listed producer ids (`contextual_admission_native.py:301–310, 369`). A
third query encoder that the declared roles admit would be refused at completion. Profile,
forms and the number of CPU receipts are likewise fixed per id
(`contextual_admission_native.py:234–259`; `definition_admission_native.py:358–372`).

**Contrary evidence.** Three patterns already select by something other than a hand list of
ids.

- *Selection by a declared effect, in two guards.* Rich admission refuses any operation that
  declares the effect `native-rich-knowledge-admission` unless it is `rich.admit`: it reads the
  lowered `support_contract` of the admitted definition at run time
  (`rich_admission_native.py:1136–1145, 1186–1192`). Policy authorization does the same: for an
  operation not classified as a policy command it refuses one that is `record_policy.authorize`
  or that declares the effect `native-evaluator-policy-authorization`
  (`semantic/record_policy_completion_native.py:425–441`).
- *Four families already declare a native effect per operation.* Record policy, operation
  events, rich knowledge and structural admission each name one in the operation's `effects`
  (`methods/record_policy.py:70`; `methods/operation_events.py:328`;
  `methods/rich_knowledge.py:405`; `methods/structural_admission.py:132`). For those four the
  attribute that a guard could select by is declared today, read by two guards, and not used
  for the family lists. Contextual, definition and artifact operations declare none (for
  example `methods/contextual_scoring.py:130–131` has `"effects": []`).
- *Owner-module constants.* The structural, record-grade and operation-event guards take an
  operation constant from the operation's own owner module (`ADMISSION_OPERATION`,
  `GRADE_OPERATION`, `AUTHORIZATION_OPERATION`).

The guards also compare a listed operation's admitted definition (entry point, profile,
recipe, forms), so a listed id whose attributes drifted is refused; in that role the
per-operation table is an independent pin on the admitted definition. Runtime dispatch reads a
lowered column instead of matching names on each call. `ops.ddo_classify_command`, generated
by the same function, classifies by eligibility predicates and not by ids
(`data_operation_compiler_native.py:530–550`), and the policy guard's `command_class` comes
from it. ADR-0131 does not promise that family or role membership comes from the model: its
decision governs physical types and call correspondence
(`docs/adr/0131-model-owned-postgresql-programs.md:32–33, 46`). The transcription recorded
here is the consequence, predicted in the previous refresh, of converting before declaring; it
is not a divergence from that decision.

**Footprint and uncertainty.** Established for the twelve lists, their agreement today and the
guard shapes. Whether a dispatch entry naming a validator function that does not exist would
fail when the kernel is installed or only at first call was not established. The refusal of a
third query encoder is inferred.

**Lead (not a selected remedy).** There is a design reason the generators should not simply
read the operation model: one native kernel serves many releases, and operations are lowered
per release into `sem.data_operation_definition` rows that the guards already look up. Reading
the model at generation time would also put every operation edit into the kernel digest
([DA-068](execution-fit.md#da-068)), which the id lists already do today. An alternative that
exists in the code is selection at run time by a lowered, declared attribute. Rich admission
already does this with a declared effect, as does policy authorization, and `validity_family` was meant to be such an
attribute: lowering already carries the archived effective operation beside it, so a family
declared per operation could be lowered the way dependencies are. For four of the seven
families a per-operation declaration (the native effect) is already in place.

<a id="da-071"></a>

## DA-071 — Support-graph meaning is encoded three times and the change-impact copy disagrees

**Scoped refresh, 2026-11-21, source `d918a09ea`.** The earlier three-way
classification has changed. Native support uses declared edge and reference variants and
one scope function. Change-impact revocation consumes the resulting native witness rows.
The separate preview of changed operation definitions uses a projection of declared
potential dependencies on both release sides. It reports operation-level candidates.
It does not carry selected role occurrence or readiness evidence. The native validity
closure and the preview therefore establish different facts.
[Native support edges](../../../python/corpus-structure/src/corpus_structure/semantic/support_edges.py#L41) ·
[Preview projection](../../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L157) ·
[Native witness consumption](../../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py#L329)

**Update, 2026-11-18, source `5139eaba3`.** Stands. `semantic/data_validity_native.py`,
`semantic/change_impact.py` and `semantic/support_trust_native.py` have no commit in
`d78c98765..5139eaba3`, so the disagreement is unchanged. `semantic/data_operation_projections.py`
changed in four commits (`32ec30618`, `6d699ab46`, `110e8aa1e`, `ed410b80f`): `_support_walk`
(`:171`) keeps its edge semantics and its own `_reference_node` (`:156`), takes a name
parameter, hides authority leaves unless the read boundary declares public disclosure
(`:84–89`) and adds disclosure checks by kind universe (`:91–103`). Its callers rose from four
to six (`:396, 466, 530, 1157, 1685, 2232`). A fourth, narrow traversal that was hand-written
SQL is now a typed program: the episode lineage walk in source admission follows only
`support_derivation_id` edges (`semantic/source_admission_native.py:1129–1135`). It serves one
purpose; whether it must agree with validity is an owner question, and it is not counted as a
fourth encoding.

**FP-04/A2; DP-01, DP-03, DP-07; CI-03.**

What a support edge means (use, episode, population, original) and how a trust scope is keyed
are not declared anywhere. They are written three times:

- validity: `ops.ddo_validity_edges`, generated by `semantic/data_validity_native.py:88–240`,
  with the reference-to-node mapping inline (`:171–190`); the scope key is `ops.ddo_scope`
  (`semantic/support_trust_native.py:100–118`);
- locks, read scopes and access universes: `_support_walk`
  (`semantic/data_operation_projections.py:171`), a deliberate superset, with its own
  `_reference_node` (`:156`) and six consumers;
- change impact: `_revocation_causes` (`semantic/change_impact.py:332–441`), with a third
  `reference_node` (`:345–350`) and its own copy of the scope formula (`:427`).

The change-impact copy differs from validity in two ways. For a `use`, validity follows the
producer, populations and episode, and follows the selected support only under value
substitution (`data_validity_native.py:171–190`). Change impact follows the episode without
expanding it, deliberately by its own comment, and follows the selected support always
(`change_impact.py:358–375`). So it misses causes validity sees and follows edges validity
does not. And it always builds `"source:" + sha256([project, source])` (`:427`), where
`ops.ddo_scope` builds a `project:` key when the source is null
(`support_trust_native.py:109–116`).

Separately, the compiler produces `potential-producers` and `selected-dependencies` projections
of operation dependencies (`semantic/data_operation_model.py:713–725`). The planner consumes
the second; the first is consumed only by graph inspection. `changed_operations` rebuilds an
equivalent graph by hand from the dependency lists (`change_impact.py:157–193`).

**Consequence.** Change impact is the planner-facing answer to "what does this change affect".
Where a use reuses an episode from another demand, causes reached only through that episode are
missed and members are reported `unknown` instead of `revoked`; revocations in a project scope
never match; and a consumer linked to a changed producer only through a kind or discovery
relation is reported `unknown` rather than `potential`. These are wrong or weaker explanations,
not wrong admission: native validity remains the authority. A new edge kind has to be added in
three places, and so does a new reference kind.

**Contrary evidence.** Public reads now see authority leaves only when the read boundary
declares disclosure, which is a declared attribute and a sound addition.

**Footprint.** The divergence is established. That it shows through cross-demand reuse is
likely. Whether any current operation has a project-scoped subject was not established.

<a id="da-072"></a>

## DA-072 — The earlier core and system model is still live beside the released model, with the same closed sets declared in both

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. No commit in
`d78c98765..5139eaba3` touched `model/core.yaml`, `model/system.yaml`, `model/revisions.yaml`,
`schema/` or the statistics schemas. Modules importing `core.vocab`, `core._model` or
`core.keys`: 41 at both commits, the identical set (regular-expression search over `*.py`; the
39 published earlier came from a narrower pattern). `semantic/native_call_generation.py:106`
still writes `from corpus_structure.core.vocab import TaskUnitType` into a generated facade.
This finding is now also the home of two earlier identities: the duplicated closed sets of
[DA-002](#da-002) and the operational closed sets of
[DA-012](structure-and-invariants.md#da-012).

The observation that the released model is itself held in several formalisms with no single
compiled authority is a different cause and has its own finding, [DA-085](#da-085).

**FP-04/A2; DP-01, DP-06, DP-16; H27.**

`model/core.yaml` (1,096 lines), `model/system.yaml` (2,023) and `model/revisions.yaml` (1,118)
are still generated into `core/vocab.py`, `core/_model/*` and `core/keys.py` by
`schema/generate.py:540–578`, with their own change classifier (`schema/change.py`), revision
log and pack loader (`schema/pack.py`, `schema/lookup.py`), and are read through two schema
views at `schema/model.py:235`. Every model-change preview still loads the earlier model
(`schema/model_change.py:590, 633–670`). The released semantic model declares the same value
sets again with no derivation between them:

| Value set | Declared in |
|---|---|
| `StatementKind`, including the `claim_bearing` subset | `model/core.yaml`; `model/semantic/core.yaml` |
| `ClaimModality`, `StatementRole`, `EvidenceRole`, `Establishment`, `ScopeExtent` | both core files |
| `Relation` / `ComparisonRelation`; `ParseOutcome` / `RuleReadingOutcome`; `MeasurementScope` / `SourceMeasurementScope`; `DocumentSplit` / `ReferenceSplit` | earlier / released |
| `PdfObservationOutcome` / `DdoPdfObservationOutcome` | `model/semantic/pdf-products.yaml`; `data-operation-pdf-capture.yaml` (both inside the released model) |

The statistics pack is also declared twice: `domains/statistics/schema/statistics.yaml` imports
the earlier core, and `domains/statistics/semantic.yaml` imports the released one.

**Consequence.** The pairs agree today. An edit to one side changes behavior only for that
side's consumers: `core.vocab` users such as `semantic/formal_evidence.py`, the generated
native calls and `methods/llm/producer.py:7` on one side, released-model consumers on the
other. Every model-change cycle also reads and carries the earlier model.

**Contrary evidence.** Some earlier-model consumers are live (`ParseOutcome`, `TaskUnitType`,
`CaseRule`, `core.keys.symbol_form`, `core.values`), so this is not simply dead code. D2 states
that superseded model interpreters retire. Whether any test asserts the pairs equal was not
examined, and some equal value sets may name different meanings.

<a id="da-073"></a>

## DA-073 — Which operations a release contains is composed by hand-written flag logic that restates family dependencies

**Update, 2026-11-18, source `5139eaba3`.** Stands, slightly wider.
`semantic/primary_operations.py`, `semantic/canonical_sentences.py`,
`semantic/hanlp_products.py` and `domains/statistics/operations.yaml` are unchanged in
`d78c98765..5139eaba3`. Two owners changed. `semantic/data_operation_preparation.py` now
requires an `asset_custody` key in a native selection and verifies file custody over a closed
key set (`:305–330`, `188ec73c2`), which is fail-closed and sound.
`semantic/characterization_ports.py:1141–1155` adds `enriched_document_products.py` to the
captured-composition family's sources by hand (`590b67b7a`, `1fab40234`, `67a6e7a51`): one more
conditional site in the family source functions, and a hand statement of "which code determines
this family" shared with [DA-069](execution-fit.md#da-069). The same change reads the declared
role collection (`:746–749`), which is a sound derivation.

**FP-04, FP-06; DP-01, DP-06, DP-16.**

The acquisition manifest names no operations, only flags (`downstream`, `visual`,
`source_bindings`, `pdf_contracts`, `protected_references`, `protected_record_policy`;
`domains/statistics/operations.yaml:28–66`). `primary_operation_inputs` turns the flags into
about thirty paired bundle transformers and source collections
(`semantic/primary_operations.py:118–392`). Which family needs which upstream family is then
restated in each family's source function (`semantic/canonical_sentences.py:263–268`;
`semantic/hanlp_products.py:631`; the family source functions of
`semantic/characterization_ports.py`, whose lines shifted in the range) and again in
preparation. Target operation ids are built by string concatenation
(`primary_operations.py:26–57`).

**Consequence.** Adding or reshaping a family means editing several conditional sites that must
agree with the compiled dependency edges. An omission is refused at compile or at demand
freeze, so the cost is change locality, not a wrong result. The compiled model holds operation
dependencies, but nothing maps an operation back to the source family that must be acquired.

**Contrary evidence.** Acquisition has to precede compilation, and the module states that the
compiled demand closure, not this composition, decides what executes
(`primary_operations.py:1–6, 82–86`).

<a id="da-081"></a>

## DA-081 — The native program set and its generated outputs have no typed registry: they are listed by hand in several places and their facts are recovered from text

**Update, 2026-11-18, source `5139eaba3`.** Stands, and wider. New modules joined the hand
lists by hand, one text transform was corrected, and one new dependency on text was added.

- *Counts* (scripted extraction at both commits): `native_protocol_sources` holds 91 literal
  artifact names (90 before); the required set holds 94 (93 before); both gained
  `native/contextual-neighborhood.py` by hand (`semantic/data_operation_storage.py:505, 608`).
  `native_sql` still joins 39 named artifacts, and the six it joins that the required set lacks
  are the same six. The module list of `capture_native_authoring_inputs` grew from 18 to 28
  names, ten added by hand (`semantic/native_products.py:134–164`). The install table still has
  eleven rows and the provider list seven. The facade tuple in `schema/model_change.py` is
  unchanged.
- *Corrected.* Authoring scratch tables are now retargeted on the parse tree: the compiled
  `CREATE TABLE` and `CREATE INDEX` statements are parsed and their relation node is replaced
  (`semantic/native_authoring.py:303–328`, `759dd837f`), where string replacement was used
  before.
- *New.* The program compiler gained a `Comment` statement (`semantic/native_program.py:177`).
  The generated admission guard uses it to emit boundary comments around its catalog checks
  (`semantic/native_admission_release.py:35–38, 371, 382`), and `catalog_checks` later finds
  those comments by substring and takes the text between them, with literal SQL fragments as
  fallback anchors for older frozen guards (`semantic/native_admission.py:42–82`, `1b643e7ed`).
  The result is concatenated into a generated `DO` block for frozen catalog verification
  (`:85–125`). The program objects know where the catalog checks begin and end; the handoff
  recovers that boundary from comment text.

**FP-03, FP-04, FP-07; A3; DP-01, DP-02, DP-16; H27.**

A native program is a generated PostgreSQL routine. Nothing carries a program as an object,
with its name, schema, purposes, grants and place in the installation order, from the
generator to the installer. Three things follow.

*Facades are registered twice.* The native preview re-renders seven generated Python facades
from the candidate model. Their paths are one tuple (`schema/model_change.py:53–61`) and their
generator calls a second, positional tuple (`:538–548`), paired by `zip(strict=True)`
(`:550–552`). Each owner also names its own path and writer, and `_pdf_native_ids.py` and
`_pdf_native_calls.py` are listed a third time in the PDF lowering list
([DA-082](execution-fit.md#da-082)). The canonical generator checks that its declared
ownership equals its emitted paths (`schema/generate.py:563–578`), but it covers only the
earlier model ([DA-072](#da-072)); these facades are outside it, and the released model has no
generator registry.

*The program set is listed by hand in six places.* Adding a program means editing each of
them, and they must agree on names and order:

- the `(name, module file, generator)` triples and the further artifact lines of
  `native_protocol_sources`, each pairing a literal artifact name with a literal module file
  name (`semantic/data_operation_storage.py:139–200` and onward to `:575`);
- the required set that the capture is checked against (`:581–692`);
- the concatenation order in `native_sql` (`:761–812`);
- the module-file list in `capture_native_authoring_inputs`
  (`semantic/native_products.py:134–164`);
- the `(label, schema, name, roles)` table in `target_native_definitions`
  (`semantic/target_installation.py:227–249`);
- a hand-ordered provider list (`target_installation.py:317–328`).

Two of these disagree. Six artifacts that `native_sql` concatenates are not in the required
set: `data-attempt-release.sql`, `data-claim-batch.sql`, `data-claim.sql`,
`data-completion-settlement.sql`, `data-operation-renewal.sql` and `data-read-boundary.sql`.

*After rendering, a program is text, and its facts are recovered by parsing.* Inside a
program, statements are typed objects. From the moment it is rendered, later steps work on
SQL text:

- generators return strings joined by `native_sql_script` (`semantic/native_objects.py:43–45`;
  62 uses in 46 modules by search), the PL/pgSQL framing is assembled with formatted strings,
  and each rendered statement is parsed again to assert that it is exactly one statement
  (`semantic/native_program.py:143, 157, 351–460`);
- `native_sql` replaces two digest markers in the joined text
  (`data_operation_storage.py:815–818`), renames entry points by parsing, reprinting and
  re-parsing the whole text (`:725–758`) and appends generated wire wrappers (`:822`);
- the assembled kernel is parsed again to find its function definitions, and execute grants
  are then assigned by matching function names in the parsed text (`:1887–1928`);
- target installation parses a concatenated script once per selected function name and each
  excerpt again (`semantic/native_authoring.py:177–202`);
- the function inventory is rebuilt by parsing generated text (`semantic/native_inventory.py`,
  unchanged in the range), not from the program objects;
- twelve `*_native.py` modules parse their own rendered output again to change the parse tree
  (fifteen calls by search, for example `semantic/contextual_scoring_native.py:34, 219`);
- the catalog-check boundary is recovered from comment text, as described above.

**Consequence.** A facade that an owner writes but the tuple does not list is not re-rendered
from the candidate, so a preview could approve SQL whose Python call surface is the working
tree's copy. The strict pairing catches a length difference, not a reordering. A program added
to one list and not another is caught only where a later step happens to need it: if one of
the six unrequired artifacts were missing, the failure would be a `KeyError` inside
`native_sql`, not the capture's classified refusal. Identity, signature, grant and boundary
facts are carried by naming conventions, markers and comments instead of by the objects that
knew them, so each transform has to verify afterwards that it changed only what it meant to,
and the same text is parsed many times. The facade and missing-artifact consequences are
inferred; the duplication, the disagreement and the text handling are established.

**Contrary evidence.** Seven facade entries, all current facades listed, count checked. The
capture's required-set check refuses a missing or duplicated artifact; an extra one is
accepted, and the required set is itself one of the hand lists. For the provider order there
is a reason a derived order cannot simply replace it: SQL-language bodies bind their callees
when created, and the catalog-based ordering cannot see objects that are not yet installed.
Each text transform verifies exact preservation. PostgreSQL needs text in the end, and reading
the server-normalized catalog back is the right final authority. Replacing the digest markers
after the digest is computed is a necessary self-reference. The docstring of the comment-based
recovery states its purpose as the replay of authenticated frozen guard bytes, which does need
text; for a guard generated in the current process the program objects are available. The
parsing cost falls on authoring, preview and preparation; deployment uses frozen statements and
imports no generator.

**Footprint and uncertainty.** Established for the sites listed. Whether authoring latency is
material is unknown, and whether native deployment refuses on the six unrequired artifacts
before `native_sql` runs was not examined. The repeated rebuild of the whole set is
[DA-083](execution-fit.md#da-083).

<a id="da-085"></a>

## DA-085 — The LinkML part of the released model is composed separately by each consumer, holds its physical constraints as JSON strings, and is not one object with the effective operation model

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. The sites that construct a
`SchemaView` are identical at both commits (16 sites by search), and the two model edits in the
range add no annotation encoding. The regenerated admission generators strengthen the finding:
they see only the compiled `MetaData`, never the effective operation model or the protocol
([above](#da-070)), so even the facts the effective model holds per operation (entry point,
profile, forms, effects) could not be read by them.

**FP-04/A2; DP-01, DP-02.** The full inventory behind this finding is the
[domain model map](domain-model-map.md).

LinkML is the modelling language the project uses for classes, value sets and physical tables.
A `SchemaView` is LinkML's in-memory view of a schema and its imports. The finding has three
parts.

*Each consumer composes its own view of the LinkML model.* 43 LinkML schema files sit under
`model/semantic/` (counted by schema header at `d78c98765`; the directory's file list is
unchanged). No single compiled object holds them. Each consumer builds its own import closure
and its own `SchemaView`:

| Consumer | Site |
|---|---|
| Physical tables | `schema/physical.py:166–197` |
| Semantic release | `semantic/prepare.py:350–373` |
| Operation call sources | `semantic/native_call_sources.py:95–117` |
| Projection analysis | `semantic/projection_analysis_products.py:85–107` |
| Companion projection | `semantic/companion_projection.py` (now held by a content-keyed cache, `:561, 620`) |
| Rule views, conditional rules, ontology, source values | `semantic/rule_views.py:402`; `semantic/conditional_rules.py:178`; `semantic/ontology.py:159, 260, 626`; `semantic/source_value_native.py:56` |

Three of these (release, call sources, projection analysis) are near-identical copies of one
routine that seeds an import map, merges imports and wraps the result again. The call-sources
copy also keeps a hand map between file names and schema names
(`semantic/native_call_sources.py:57–64`).

*Physical constraints are JSON strings inside annotations.* Foreign keys, checks and indexes
are encoded as JSON text in `ph:foreign_keys`, `ph:checks` and `ph:indexes`, decoded by custom
code (`schema/relational.py:297, 548–563`). LinkML tooling cannot see them, and foreign keys
are not expressed as slot ranges.

*The other formalisms restate some of the same facts.* The model directory also holds a JSON
Schema protocol, custom YAML catalogs and JSON files (listed on the map). Their existence is
not the finding. What source shows is restatement between them and the LinkML part in specific
places: the kind-universe values are a check predicate in the physical model
(`model/semantic/data-operation-physical.yaml:71`), a literal set in the operation compiler
and a typed literal in the effective model ([DA-086](#da-086)); and two JSON value codecs take
their vocabulary from two authorities ([DA-086](#da-086)). In the other direction a derivation
exists and works: physical value sets are taken from the protocol through `ph:values_from`.

**Consequence.** Each generator sees its own LinkML view, and the LinkML views and the
effective operation model are not one object that a generator reads together. A fact that
crosses them (a role, the relation between an operation and a kind, the class of a relation)
has no shared object to be derived from, which is one reason membership facts fall back to
Python lists ([DA-070](#da-070), [DA-074](native-integrity.md#da-074), [DA-086](#da-086)).
A change to the composition rule has to be made in three copies.

**Contrary evidence.** That operations have two authoring routes is an accepted decision, not
a defect: [ADR-0092](../../adr/0092-ddo-operation-authority.md) selected "Compile both admitted
authoring routes into one effective model" (`:19–25`), and questioning it would be a revisit of
that decision, not an audit finding. Separate closures per artifact also partly serve custody:
each captured closure is what that artifact's identity covers. Each closure routine refuses an
unresolved import and has no filesystem fallback, and the physical closure is
content-identified and pins the LinkML types bytes (`schema/physical.py:142–197`). There is
also a reason not to hand the whole operation model to kernel generators (see the lead under
[DA-070](#da-070)).

**Footprint and uncertainty.** Established for the composition sites, the copied routine and
the annotation encoding. Whether the separate closures ever differ in result was not tested.
That the separate views cause the hand lists is an inference from their co-occurrence. The
LinkML features that the model does and does not use are listed on the
[map](domain-model-map.md#linkml-features); an unused feature is not a finding.

**Relation to DA-072.** Separate cause. DA-072 is an earlier generation of the model that was
not retired. This finding is about the current generation.

<a id="da-086"></a>

## DA-086 — Generators and analytical modules restate as Python literals facts that the model declares or that a typed source already carries

**Update, 2026-11-18, source `5139eaba3`.** Stands, wider in count. A draft of this update
recorded the task guard as a correction of this finding; the independent challenge showed that
it is not, and the status was withdrawn before publication.

- *The task guard is not a correction here.* At `d78c98765` the guard was already rendered
  from the protocol's declared lifecycle (`render_data_task_guard` called
  `data_task_lifecycle` and substituted the declared states into a template), and this finding
  already cited it as the sound counter-example. What `32ec30618` changed is the form: the
  guard is now a typed program whose `ops.task` and `ops.data_request` columns resolve against
  captured metadata (`semantic/data_operation_protocol.py:117–128`), replacing a template and a
  loaded SQL file. That is part of the conversion recorded under
  [DA-084](boundaries-and-composition.md#da-084). The guard remains the one place where a
  declared fact governs a kernel check.
- *Unchanged.* The kernels still test state literals: quoted `pending` or `running` appears 21
  times in eight `*native*.py` files at both commits (the challenge's recount agrees), and all
  task and record state literals appear 68 times in seventeen modules, the same number as at
  `d78c98765`, when many of them sat in SQL text. The value-codec tag tuple, the field-kind
  maps, `_PROFILES`, `_KIND_UNIVERSES` and the Arrow schemas are in files with no commit in the
  range.
- *Wider, because the conversion made the literals visible to search.* Kind-universe literals
  in `semantic/*.py` rose from 33 to 43 lines (pattern: `universe` followed within forty
  characters by one of the four universe names); the new lines are in the rich (3) and
  structural (6) generators, formerly SQL text, and one new rule in
  `data_operation_projections.py:97`. Codec tags and operation role names appear as literals in
  every regenerated module (0 to 13 tag literals and 0 to 12 role comparisons per module by
  survey). Paths into the lowered `support_contract`, such as
  `["capabilities"]["prepared_factory"]["entrypoint"]`, are free strings: the typed read
  boundary types that column as `dict[str, Any]`
  (`semantic/native_definition_projection.py:31–42`), while the effective model holds
  `capabilities` as a typed dataclass. A renamed property inside a modelled JSON shape does not
  fail at generation; PL/pgSQL evaluates the path at run time and a wrong key yields null.
- *Newly identified, not new code.* Product member families restate field names and required
  sets that the protocol declares (`semantic/data_product_admission_native.py:56–90` against
  the protocol's `coordinate`, `role_member`, `endpoint`, `coverage`, `choice` and
  `product_member` definitions). Encoder failure codes restate a Python set
  (`contextual_admission_native.py:653–660` against `semantic/contextual_encoder_batch.py:19–26`).
  Prepared-factory entry points, which the effective model holds per operation, are written in
  53 lines across 15 files (51 in 14 at `d78c98765`; search for `acquire_port` entry-point
  strings in `semantic/` and `evaluate/`). Operation-event ids are written inline
  (`operation_event_native.py:295, 315, 1206`); only the authorize id has an owner-module
  constant, and the frame and fit ids have none.

**FP-02, FP-04; DP-01.** Counts marked "survey" are regular-expression counts by a contributor
and include some benign matches.

This differs from [DA-070](#da-070), [DA-073](#da-073) and
[DA-074](native-integrity.md#da-074), where no declaration exists and the hand list is the
only statement of the fact. Here a declaration or a typed source exists and the code does not
read it.

- **Task states.** The protocol declares the task lifecycle, with its initial, running and
  terminal states and its transitions (`model/semantic/data-operation-native.yaml:5–14`). The
  task guard reads it, as it did before the range. The kernels test string literals instead,
  for example in the claim program (`semantic/data_claim_native.py`).
- **Value-codec vocabulary.** The data-operation value codec takes its tags from Python
  `Literal` types and adds a hand tuple of text-like tags
  (`semantic/data_operation_value_native.py:44–50`). The SourceValue codec beside it takes its
  variants from the LinkML observations schema and refuses on drift
  (`semantic/source_value_native.py:55–66`). Two JSON value codecs in PostgreSQL therefore have
  two different authorities.
- **Field kind to type.** The model declares this mapping: each LinkML type carries a `uri`
  and, where needed, a `ph:sql_type` annotation, and the physical compiler resolves them
  (`schema/relational.py:79–89, 437–440`). Beside that declared fact and its resolver, the
  mapping is written four more times: `semantic/native_call_contracts.py:16–25`;
  `semantic/native_call_sources.py:28–37`; `semantic/pdf_search_native.py:98–104`; and a
  special case for `int4` (`semantic/native_program.py:657`).
- **Profiles and kind universes.** `_PROFILES` and `_KIND_UNIVERSES` are literal sets
  (`semantic/data_operation_compilation.py:85, 341`) beside the typed `Literal` that already
  carries the profiles. The universe values are written again as a check predicate in the
  physical model (`model/semantic/data-operation-physical.yaml:71`) and in the kernel literals
  counted above.
- **Analytical relation shapes.** Three DuckDB modules declare their Arrow input schemas by
  hand: the rich-rule views (`semantic/analytical_kernels.py:21–60`), candidate boxes
  (`ingest/pdf_candidate_geometry.py:60–72`) and the recognition replay
  (`ingest/pdf_stream_reconciliation.py:233–241`). The companion export restates family
  grouping columns and excluded provenance columns that the projection's role annotations
  describe. These files are unchanged in the range.

Two earlier identities are current instances of the same shape on the semantic side and keep
their own homes: the per-predicate qualifier lists that are compiled and validated and govern
nothing ([DA-001](#da-001)), and release annotations decoded from raw strings by each rich
consumer ([DA-004](#da-004)). The three-times-written identity-resolution outcome set
(`semantic/rich_knowledge.py:66`; `semantic/rich_decisions.py:12`;
`semantic/rich_rule_evaluation.py:479–481`) and the evidence role `"primary"` used as a literal
([DA-003](#da-003)) are low-weight instances.

**Consequence.** A change to a declared state, tag, field kind, member field or column
property does not propagate to these sites, and compilation does not refuse; each is a place
where a model change has to be remembered. ADR-0131 states that a model field or type change
"propagates to its generated SQL and calls, or compilation refuses"
(`docs/adr/0131-model-owned-postgresql-programs.md:46`). That now holds for relations and
columns in every converted module and does not hold for these facts.

**Contrary evidence.** Relations and columns are resolved against compiled metadata, so a
missing relation or column fails at generation. The pattern that would close several items is
already in use: the trust-scope program reads its universe values from the typed `Literal`
(`semantic/support_trust_native.py:91`), the SourceValue codec checks its closed set against
LinkML, the structural generator refuses at generation when its disclosure field set differs
from its contract (`semantic/structural_admission_native.py:1680–1694`; the contract is a
pydantic model, not LinkML), and Arrow schemas for PDF records and exports are derived from
compiled metadata. Some entry-point literals are deliberate: the guard compares them with the
admitted row, so they act as an independent pin.

**Footprint and uncertainty.** Established for the sites cited. The rich-rule view relations
and the two ingest schemas have no declared counterpart to derive from, so whether they belong
in the model is an owner question; the same holds for the partition values and failure codes.
Native function names called as free `func.<schema>.<name>` references number 1,113 across
`*_native.py`, 260 distinct (887 references at `d78c98765`; search); they are bound when
PostgreSQL installs the program and checked by `plpgsql_check` during authoring. A related
item with its home elsewhere: shared-stream trigger membership is chosen by relation name
although the model declares the class that would select it
([DA-074](native-integrity.md#da-074)).

## Lower-weight observations

- The token-to-type table is duplicated between the writer and the reader
  (`semantic/prepare.py:93–104`; `semantic/archive_reader.py:40–51`), and compact-encoding
  defaults for the effective model are restated in three places. Most drift is caught by a
  digest or round-trip check (2026-11-17; not re-read).
- Enforcement claims are tagged records resolved against binding, schema, implementation slice
  or captured native asset (`semantic/data_operation_compilation.py:1903–1990`). By string
  count at `5139eaba3`, `"kind": "documentation"` occurs 334 times in 55 files, and the checked
  interpretations a handful of times each. This counts literals, not resolved claims; it is
  consistent with the earlier note of about 245 documentation claims and three checked claims.
  It is the current form of [DA-027](#da-027)'s limit: the claims are honest about what they
  are, and the correspondence of each body remains unexamined.

## Earlier identities with current sites

These sections were written on 2026-11-18 at `5139eaba3`. Each earlier identity keeps its own
home here because the same structural cause was found in the code that replaced its original
subject.

<a id="da-028"></a>

### DA-028 — The source-demand path reads the working tree's `slices.yaml`, matched to the release by name only, while the release archives its own copy

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint; the cause stands at a new site.
The query-plugin part of the 2026-10 finding no longer applies (`bcff594c2`). The previous
table row said "no longer applicable"; that was true of the plugins only.

**FP-04; DP-02, DP-04; CI-10, CI-11, CI-13.**

A release is the prepared, archived form of a domain pack. Preparation archives the pack's
`slices.yaml`, the file that names document scopes and slices, as the release artifact
`operation/slices.yaml` (`semantic/regeneration.py:110–118`). Nothing reads that archived name
(search of `src` for `operation/slices`: no reader).

The production source-demand path reads the working-tree copy instead. `prepare_source_demand`
receives the loaded release and then selects document scopes from
`(domains or DOMAINS)/<domain>/slices.yaml` on disk (`orchestrate/source_operation.py:160–176`).
It is reached from native execution (`orchestrate/native_execution.py:38–42`). The domain
directory is itself chosen by matching the `name` in the live pack's `semantic.yaml` against
the archived module names, without comparing bytes (`source_operation.py:54–60`).

**Consequence.** A release that archived slices X can execute a source demand under live slices
Y: the documents and scopes a demand covers are decided by a file that the release identity
does not cover, and the result is attributed to the release. Because the pack is edited in the
same working tree as the code, the two can differ in the ordinary edit loop. This is an
integrity question for what is served, since downstream reads report results against the
release.

**Contrary evidence.** The release does archive the file, so the bytes needed to close the gap
exist. A named scope that the live file does not define is refused. Whether a later step
compares the selected documents with anything release-bound was not traced.

**Footprint.** Established for the read site and the absence of a reader of the archived copy.
No run was made, so a divergent execution was not observed.

<a id="da-001"></a>

### DA-001 — Per-predicate qualifier lists are compiled and validated but govern nothing

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint. The 2026-10-29 finding was two
declarations of which qualifiers distinguish facts, with opposite defaults and nothing relating
them. Both declarations still exist. The per-predicate lists (`cs:qualifiers`,
`cs:identity_qualifiers`) are now validated by `compile_comparison_projection`: names must
exist on the qualification class, provenance properties are refused, and the identity list
must be a subset of the qualifier list (`semantic/comparison_projection.py:92–171`). The result
is archived as `comparison_projection.json` (`semantic/prepare.py:941–950, 1077`) and re-read
with checks (`semantic/archive_reader.py:169–171`).

Nothing uses its partition. `ComparisonProjection.partition`
(`comparison_projection.py:66–84`) has no caller (search of the package), and `RichRulePolicy`
stores the projection without reading it (`semantic/rich_rules.py:58–60`). Scientific grouping
keys instead on `fact.qualification_meaning`, which is derived from the per-property
`key_role` (`semantic/rich_scientific.py:205–217`). The statistics pack still declares a
non-trivial partition for `transformation_of` (`domains/statistics/semantic.yaml:461–462`), the
same example the original finding cited.

**Consequence.** The earlier silent disagreement has become a validated declaration that
governs nothing. The effect is latent today: that predicate is multivalued and not functional,
so it never reaches scientific comparison. A pack author who edits the lists changes an
archived artifact and no behavior. **FP-04; DP-01, DP-03.** Cross-referenced from
[DA-086](#da-086).

<a id="da-004"></a>

### DA-004 — Each rich consumer decodes raw release annotation strings for itself

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint for the annotation half; the
conversion half was withdrawn on 2026-11-05. The originally cited sites are gone. Release
annotations are still raw strings in the registry metadata, and each consumer decodes them
itself: 36 `.get("cs:…")` sites in `semantic/` and `serve/` (search), among them
`semantic/rich_scientific.py:210–211`, which keeps the `str(...).lower() == "true"` pattern the
original finding cited, `semantic/rich_knowledge.py:238, 244, 279, 303, 361`,
`semantic/rich_rule_evaluation.py:432, 867, 881`, `semantic/rich_queries.py:303` and
`semantic/rich_graph_validation.py:602`. The class-level `cs:case` and the property-level
`case_policy` remain separate notions under similar names (`rich_knowledge.py:238` against
`:264`).

**Consequence.** A new annotation value or a changed spelling has to be handled at each
decoding site, and two sites can read the same annotation differently. This partly overlaps
[DA-085](#da-085), whose subject is the physical `ph:` annotations, not the semantic `cs:`
ones. **FP-02, FP-04; DP-01.** Cross-referenced from [DA-086](#da-086).

<a id="da-065"></a>

### DA-065 — The witness of a named or geometry definition basis is no longer verified independently: assurance moved to producer attestation

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint; not a regression. A draft of
this update recorded it as possibly regressed; the independent challenge settled it as far as
static reading allows.

*What was lost.* Commit `9e04d04d1` (2026-11-08) bound named and geometry bases to an exact
annotation witness and enforced that in three places: native admission in a hand-written SQL
file, a detached replay module and a review-bundle module. All three were removed, the SQL in
`200e396fc` and the other two in `ee940a5ef`, and no production or test source at `5139eaba3`
contains the refusal message of that check (search). So nothing now verifies the witness
against retained annotations independently of the producer.

*What still holds.* The declared type never required the witness: at the enforcing commit it
already allowed `witness=None`, with the same one-way check as today
(`semantic/structural_products.py:601–616, 950–967`). The production producer always attaches
one: its only production call path builds a `witnesses` dictionary and never passes `None`
(`semantic/definition_component_products.py:519–573`), and with a dictionary a component is
qualified only when its match is in it (`methods/definition_applicability.py:466, 572–577`).
A `matched_cue` or `native_geometry` basis without a witness is reachable only through the
default that tests use. Admission then checks the published output against the attested
producer: it must equal the CPU reply bound to the exact input basis
(`semantic/definition_admission_native.py:386–400`; `semantic/data_operation_cpu_basis.py:1095–1150`,
the latter as cited by the challenge).

**Consequence.** The unwitnessed scenario is not reachable through production admission today.
The guarantee now rests on producer attestation instead of an independent native check (CI-01
weakened, not breached). A low-weight residue: the type binds a `declaration_chain` basis to
its witness in both directions (`structural_products.py:956–964`) and the other two bases in
one direction only. Nothing was executed. **FP-04, FP-05; CI-01.**

## Prior identities on this page

<a id="da-002"></a>
<a id="da-003"></a>
<a id="da-005"></a>
<a id="da-006"></a>
<a id="da-007"></a>
<a id="da-008"></a>
<a id="da-009"></a>
<a id="da-010"></a>
<a id="da-011"></a>
<a id="da-026"></a>
<a id="da-027"></a>
<a id="da-034"></a>
<a id="da-046"></a>
<a id="da-048"></a>
<a id="da-049"></a>
<a id="da-062"></a>

Statuses were established on 2026-11-18 at `5139eaba3` by reading the code that replaced each
cited subject. "Corrected, holds" means a recorded correction was checked and still describes
the code. Earlier text is in Git at `fbd3f2a98` and before. No probe was rerun.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-001 | Changed footprint | [Section above](#da-001): the second declaration is validated and inert |
| DA-002 | Superseded by [DA-072](#da-072), with [DA-086](#da-086) and [DA-085](#da-085) | The same cause, one closed set held by several owners, is DA-072. The reference-split divergence no longer applies: no `reference_set` relation exists, and `ReferenceSplit` is LinkML-only with an `executable` subset (`model/semantic/reference.yaml:220–224`). Value-kind correspondence between CHECK, writer and reader was not re-traced |
| DA-003 | Partly corrected | Roles are declared and read through `enum_members(subset=…)` (`semantic/types.py:346, 361, 363–364`; `semantic/rule_views.py:332–335`; `semantic/statement_types.py:213`; `semantic/proposals.py:113`). Remaining: the `ClaimModality` subsets `conflict_bearing`, `reserved` and `attribution_identifying` (`model/semantic/core.yaml:676–698`) have no reader outside the earlier model, and the evidence role `"primary"` decides behavior as a literal (`semantic/rich_knowledge.py:209`; `semantic/rich_identity_exclusions.py:91`; `semantic/rich_proposal_lowering.py:41`). Nearest current finding: DA-086 |
| DA-004 | Changed footprint | [Section above](#da-004) |
| DA-005 | Corrected, holds | Context translations are owned by `semantic/rule_views.py` |
| DA-006 | Corrected, holds | References are typed by `cs:reference_role` and foreign keys |
| DA-007 | Corrected, holds | Decisions are typed with a basis and an outcome (`semantic/rich_knowledge.py:61–70, 371–407`) and retained as members that rule evaluation consumes. The outcome set is a literal written three times, a low-weight instance of DA-086 |
| DA-008 | Corrected, holds | Case is folded only where a property declares it |
| DA-009 | Partly corrected | Determinants have one owner (`semantic/determinants.py:1–34`). Two parts remain. `require_unicode_identity_release` (`semantic/unicode_identity.py:233–246`) has had no production caller since `bcff594c2`; the one native fold found folds both sides inside PostgreSQL, so no cross-language parity is needed there (inferred from a search), and the dormant check is footprint of [DA-080](boundaries-and-composition.md#da-080). Canonical JSON still has two implementations: native `data.canonical_json` (used at `semantic/runtime_binding_native.py:125–128`) and Python `canonical_bytes` (`semantic/identity.py:13`); the numeric-rendering difference of the 2026-10 probe was not rerun |
| DA-010 | Corrected, holds | Closed acquisition manifest |
| DA-011 | Corrected, holds | For the version restatement: D2's opening and code agree (compiler 24, boundary 13). The whole design collection was not examined |
| DA-026 | Partly corrected | Binding is a compiled release product (`semantic/statement_types.py` through `semantic/prepare.py:887–950`), and no `*_native.py` names `SourceStatement`. Remaining: the raw-YAML inference that matches `is_a` against `"Qualification"` and `"SourceStatement"` on direct children and refuses a second one (`semantic/regeneration.py:129–142`, defaults at `:245–248, 292–294`), and name defaults at `semantic/statement_types.py:87–88` and `semantic/proposals.py:49–50` |
| DA-027 | Stands, as a limit | See the lower-weight observations above |
| DA-028 | Changed footprint | [Section above](#da-028) |
| DA-034 | Corrected, holds | One scientific owner, `semantic/scientific_evidence.py`; the successor identity issue is [DA-077](served-claims.md#da-077) |
| DA-046 | Stands | An open boundary question. `model/semantic/core.yaml:614–713` still declares `StatementKind` with theorem, lemma, exercise and solution, and `proves` (`:526`), `family_param` (`:265`), `exemplified` (`:689`) and `example_value` (`:711`). The toy pack's `ToyStatementKind` inherits it (`domains/toy/semantic.yaml:36–39, 65–69`), so the toy schema still offers theorem and exercise. DESIGN §1.3 still says the core "holds nothing statistics-specific" (`docs/design/DESIGN.md:74`). The duplicated closed sets are DA-072 |
| DA-048 | Changed footprint, partly corrected | Shared rule and scientific inputs of composed packs are coalesced at the root name and conflicts are refused (`semantic/regeneration.py:189–211, 225–233`), and some consumers accept pack-scoped names. The cause recurs for inputs that are not shared: every other operation input is renamed `pack/<name>/…` (`:234`), `operation/rich-analysis-context.json` is read only under its root name (`semantic/rich_policy_binding.py:12, 24`), and its validity check runs only when that root name is present (`semantic/prepare.py:1406–1414`). A composed release would skip the check silently (inferred from source, not executed). Only single-pack preparation is exercised today |
| DA-049 | Corrected, by decision | ADR-0047 declares current-only operation. Exact version equality (`semantic/releases.py:489–499`) and refusal of old encodings (`semantic/data_operation_model.py:1211–1216`) are that declared limit |
| DA-062 | Corrected, holds | The native codec is generated from the LinkML layout and requires the `name`/`position`/`value` contract, contiguous ordered positions and unique names (`semantic/source_value_native.py:64–66, 241–335`; `f3f2d1ca5`, regenerated in `366a5458d`) |
| DA-065 | Changed footprint | [Section above](#da-065): independent witness verification was retired; assurance rests on producer attestation |
