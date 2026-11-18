# Semantic model and authority

**Interface-checked by source inspection.** The page was read as a whole on 2026-11-17 at
source `fbd3f2a98` ([baseline and limits](README.md#baseline)). Every finding that carries a
"Refresh, 2026-11-18" paragraph was re-read at source `d78c98765`
([refresh](README.md#refresh-2026-11-18)), and DA-085 and DA-086 were established there; text
without such a paragraph keeps its 2026-11-17 date. Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`; `domains/` is at
the repository root. The current model owners are described in the
[domain model map](domain-model-map.md).

The findings below share a shape: a fact the declared model already holds, or could hold, is
written a second time by hand in code or SQL. They differ in what goes wrong when the copies
drift, so they are separate findings.

The hand-written file `semantic/sql/data_operations.sql`, which the 2026-11-17 text cited, was
deleted in commit `2910d9817`. Its programs are now produced by generator modules named
`semantic/*_native.py`. The conversion moved the hand lists described here into those
modules, often word for word, as tuples and `CASE` mappings in Python; none of them is read
from a declaration.

<a id="da-070"></a>

## DA-070 — Validity families and family contracts are assigned from hand-written operation-id lists, and an unlisted operation is treated as valid

**Refresh, 2026-11-18, source `d78c98765`.** Stands, with a changed footprint. The
classification list is now a Python tuple inside the generator
`semantic/data_operation_compiler_native.py:468–529` (moved by `937d98415` and `555e28d59`), and
the dispatch is a second Python tuple in `semantic/data_validity_native.py:272–288` (moved by
`d422c48e7`). Both lists already existed in the deleted SQL, as the classification function and
the dispatch `CASE`; the conversion transcribed both into Python tuples, and both fail open. The guard and validator lists of the contextual, definition and rich families are
unchanged hand-written SQL text inside Python strings; `contextual_admission_native.py` has no
commit in `fbd3f2a98..d78c98765`. The condition recorded on 2026-11-17 for closing this finding,
that the compiler takes family membership from the model and refuses an undeclared operation,
is not met: the conversion delivered a transcription.

**FP-04/A2; DP-01, DP-03, DP-06.**

Lowering stores each operation's `validity_family` by calling `ops.ddo_classify_validity`. The
generator `_classify_programs(model)` holds the seven families and their 27 operation ids as a
Python tuple and renders the function as a `CASE` over `operation IN (...)` with no `ELSE`, so
it returns `NULL` for anything not listed
(`semantic/data_operation_compiler_native.py:468–529`); the `model` argument is not used for
this. Release lowering stores the result (`:916–926`). The archived effective operation is in
scope at that point, and the operation's dependencies are lowered from it in the same block
(`:905–911`). The column itself is declared as an optional string with no enumeration and no
check (`model/semantic/data-operation-physical.yaml:88`), so any string or `NULL` is accepted.

Producer validity then dispatches on that column through a second tuple that maps the seven
family names to validator owners, and anything else takes `else_=True`
(`semantic/data_validity_native.py:272–288`): an operation with no family, or with a family
name the dispatch tuple lacks, never has its family's dependency premises evaluated.

The contextual family repeats its full twelve-id list in the completion guard and in the
dependency validator, beside a per-operation table of Python entry points, profile and forms
(`semantic/contextual_admission_native.py:16–21, 23–44, 214–219`). The model already holds
those facts for each operation (`EffectiveOperation.profile`, `capabilities.forms`,
`capabilities.prepared_factory.entrypoint`; `semantic/data_operation_model.py:288–296, 495–526`).
Further per-operation literals sit in `ops.ddo_require_completion_live`, a chain of conditions
on literal operation ids (`semantic/data_completion_settlement_native.py:712–800`), and an
operation-event id list is written inline in the completion sequence (`:570–576`).

**Consequence.** An omission fails open, silently, at both points:

- an operation that belongs to a family but is missing from the classification tuple (a new
  member, a rename, a split) has that family's dependency validity skipped; so does every
  member of a family that is present in the classification tuple and absent from the dispatch
  tuple;
- the family completion guards have the shape `IF operation_id NOT IN (...) THEN RETURN`, and
  completion calls every guard unconditionally from a tuple of fourteen names, each guard
  selecting itself by its own list (`semantic/data_completion_settlement_native.py:537–590`;
  `contextual_admission_native.py:16–21`; `definition_admission_native.py:83, 106, 124`;
  `rich_admission_native.py:183`; the record-grade validator, now typed, selects itself by
  comparing with one operation id, `record_grade_native.py:691`). An operation omitted from a
  guard's list skips that family's completion checks as well. Only a listed id whose
  attributes disagree is refused.

What an omitted member loses depends on the family. The generic support walk and revocation
still apply to every operation. For the artifact, definition and rich families, and for
contextual operations other than scores, the family validator adds only the digest-gated
replay of [DA-068](execution-fit.md#da-068). Changing premises are lost for record grade,
record fit and operation events (cut trust; the generators are `record_grade_native.py`,
`record_policy_completion_native.py` and `operation_event_native.py`, whose premise lines were
not re-located on 2026-11-18) and for contextual scores (the linguistic premise,
`contextual_admission_native.py:227–233`): for those, an omitted operation's derivations stay
valid and reusable after their premises change.

The plan defines the column as null "when no per-kind validator applies"
(`docs/plans/declared-data-operations/products-and-support.md:422–423`), so a missing entry is
indistinguishable by design from an operation that needs no validator. No compile-time or
admission-time check ties family membership to the model. Every such edit is also a native
source edit, so it changes the kernel digest.

**Contrary evidence.** The contextual guard's per-operation table is compared with the
admitted definition, so it acts as an independent pin on that definition. Taking the table
from the effective model would keep a meaningful check only if the kernel's captured model and
the admitted release remain distinct inputs. Runtime dispatch reads a lowered column rather
than matching names on each call. `ops.ddo_classify_command`, generated by the same function, classifies by
eligibility predicates, not by an id list (`data_operation_compiler_native.py:530–550`), which
shows the alternative is already in use.

**Footprint.** Established for the classification, the dispatch and the guard shape. All 27
listed ids existed in source on 2026-11-17 and no commit changed the list's membership, so no
member is known to be missing today. Whether a dispatch entry naming a validator function that
does not exist would fail when the kernel is installed or only at first call was not
established.

**Note for the next conversion step (2026-11-18).** The contextual, definition, rich and
artifact guards and validators, which hold these lists, are among the modules that are still
hand-written PL/pgSQL text ([DA-084](boundaries-and-composition.md#da-084)). Converting them to
typed programs in the way record grade was converted would transcribe the lists a second time
unless family membership is declared first. That conversion is scheduled, open work under
ADR-0131 and the DDO plan, so this ordering observation bears directly on it. It is not a
finding of its own.

**Lead (not a selected remedy).** Lowering already carries the archived effective operation
beside `validity_family`; a per-operation family declared in the model could be lowered the
way dependencies are, with an install-time check that the dispatch covers every declared
family.

<a id="da-071"></a>

## DA-071 — Support-graph meaning is encoded three times and the change-impact copy disagrees

**Refresh, 2026-11-18, source `d78c98765`.** Stands. All three encodings are now Python, and
the disagreement is unchanged. The validity copy became a typed program
(`semantic/data_validity_native.py:88–240`) rather than being derived from anything, so the
count stayed at three, where the 2026-11-17 delta expected two at best. `semantic/change_impact.py`
has no commit in `fbd3f2a98..d78c98765`. Each encoding also carries its own mapping from a
support reference to a graph node, so that mapping is now written three times as well.

**FP-04/A2; DP-01, DP-03, DP-07; CI-03.**

What a support edge means (use, episode, population, original) and how a trust scope is keyed
are not declared anywhere. They are written three times:

- validity: `ops.ddo_validity_edges`, generated by `semantic/data_validity_native.py:88–240`,
  with the reference-to-node mapping inline (`:171–190`); the scope key is `ops.ddo_scope`
  (`semantic/support_trust_native.py:100–118`);
- locks, read scopes and access universes: `_support_walk`
  (`semantic/data_operation_projections.py:132–242`), a deliberate superset, with its own
  `_reference_node` (`:117`) and four consumers (`:363, 468, 1071, 1586`);
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
equivalent graph by hand from the dependency lists (`change_impact.py:157–193`). Operation
dependencies themselves are authored as id lists that the compiler only checks for resolution
(`semantic/data_operation_compilation.py:1830–1838`); by search on 2026-11-17, nothing checks
that a computed input role's kind is produced by a declared dependency.

**Consequence.** Change impact is the planner-facing answer to "what does this change affect".
Where a use reuses an episode from another demand, causes reached only through that episode are
missed and members are reported `unknown` instead of `revoked`; revocations in a project scope
never match; and a consumer linked to a changed producer only through a kind or discovery
relation is reported `unknown` rather than `potential`. These are wrong or weaker explanations,
not wrong admission: native validity remains the authority. A new edge kind has to be added in
three places, and so does a new reference kind.

**Footprint.** The divergence is established. That it shows through cross-demand reuse is
likely. Whether any current operation has a project-scoped subject was not established.

<a id="da-072"></a>

## DA-072 — The earlier core and system model is still live beside the released model, with the same closed sets declared in both

**Refresh, 2026-11-18, source `d78c98765`.** Stands; cited lines moved and no commit in
`fbd3f2a98..d78c98765` touched these owners. `model/core.yaml` (1,096 lines),
`model/system.yaml` (2,023) and `model/revisions.yaml` (1,118) are still generated into
`core/vocab.py` and `core/_model/*` by `schema/generate.py:540–578`, and read through two
schema views at `schema/model.py:235`; the earlier pack loader is `schema/pack.py:232`. 39
modules still import `core.vocab`, `core._model` or `core.keys` (dotted-path search,
2026-11-18). One of
them is a generator of the released model: `semantic/native_call_generation.py:106` writes
`from corpus_structure.core.vocab import TaskUnitType` into a generated facade, so the earlier
model feeds the released model's generated code. Every model-change preview still loads the
earlier model (`schema/model_change.py:590, 633–670`). The six value sets named in the table's
first two rows are each still declared in both core files (search, 2026-11-18).

The wider observation that the released model is itself held in several formalisms with no
single compiled authority is a different cause and has its own finding,
[DA-085](#da-085): retiring the earlier model would not give the released model one compiled
form, and unifying the released model would not retire the earlier one.

**FP-04/A2; DP-01, DP-06, DP-16; H27.**

`model/core.yaml`, `model/system.yaml` and `model/revisions.yaml` are still generated into
`core/vocab.py`, `core/_model/*` and `core/keys.py`, with their own change classifier
(`schema/change.py`), revision log and pack loader (`schema/pack.py`, `schema/lookup.py`). The
released semantic model declares the same value sets again with no derivation between them:

| Value set | Declared in |
|---|---|
| `StatementKind`, including the `claim_bearing` subset | `model/core.yaml`; `model/semantic/core.yaml` |
| `ClaimModality`, `StatementRole`, `EvidenceRole`, `Establishment`, `ScopeExtent` | both core files |
| `Relation` / `ComparisonRelation`; `ParseOutcome` / `RuleReadingOutcome`; `MeasurementScope` / `SourceMeasurementScope`; `DocumentSplit` / `ReferenceSplit` | earlier / released |
| `PdfObservationOutcome` / `DdoPdfObservationOutcome` | `model/semantic/pdf-products.yaml`; `data-operation-pdf-capture.yaml` (both inside the released model) |

The statistics pack is also declared twice: `domains/statistics/schema/statistics.yaml` imports
the earlier core, and `domains/statistics/semantic.yaml` imports the released one. On
2026-11-17 the two shared nine classes, 23 slots and two enums, and same-named classes in the
two core files had different shapes (`IntervalValue`).

**Consequence.** The pairs agree today. An edit to one side changes behavior only for that
side's consumers: `core.vocab` users such as `semantic/formal_evidence.py` and the generated
native calls (`semantic/native_call_generation.py:106`) on one side, released-model consumers
on the other. Every model-change cycle also reads and carries the earlier model
(`schema/model_change.py:590, 633–670`).

**Contrary evidence.** Some earlier-model consumers are live (`ParseOutcome`, `TaskUnitType`,
`CaseRule`, `core.keys.symbol_form`, `core.values`), so this is not simply dead code. D2 states
that superseded model interpreters retire. Whether any test asserts the pairs equal was not
examined, and some equal value sets may name different meanings.

**Relation to DA-012.** DA-012 asked, as a bounded question, whether operational values
correspond to a declaration. This is the first enumerated answer: these values correspond to
two.

<a id="da-073"></a>

## DA-073 — Which operations a release contains is composed by hand-written flag logic that restates family dependencies

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. None of
`semantic/primary_operations.py`, `semantic/data_operation_preparation.py`,
`semantic/canonical_sentences.py`, `semantic/characterization_ports.py`,
`semantic/hanlp_products.py` or `domains/` has a commit in `fbd3f2a98..d78c98765`, so the line
references below stand.

**FP-04, FP-06; DP-01, DP-06, DP-16.**

The acquisition manifest names no operations, only flags (`downstream`, `visual`,
`source_bindings`, `pdf_contracts`, `protected_references`, `protected_record_policy`;
`domains/statistics/operations.yaml:28–66`). `primary_operation_inputs` turns the flags into
about thirty paired bundle transformers and source collections
(`semantic/primary_operations.py:118–392`). Which family needs which upstream family is then
restated in each family's source function (`semantic/canonical_sentences.py:263–268`;
`semantic/hanlp_products.py:631`; `semantic/characterization_ports.py:316, 1152–1177`) and
again in `semantic/data_operation_preparation.py:235–236`. Target operation ids are built by
string concatenation (`primary_operations.py:26–57`).

**Consequence.** Adding or reshaping a family means editing several conditional sites that must
agree with the compiled dependency edges. An omission is refused at compile or at demand
freeze, so the cost is change locality, not a wrong result. The compiled model holds operation
dependencies, but nothing maps an operation back to the source family that must be acquired.

**Contrary evidence.** Acquisition has to precede compilation, and the module states that the
compiled demand closure, not this composition, decides what executes
(`primary_operations.py:1–6, 82–86`).

<a id="da-081"></a>

## DA-081 — The native program set and its generated outputs have no typed registry: they are listed by hand in several places and their facts are recovered from text

**Refresh, 2026-11-18, source `d78c98765`.** Stands, with a much wider footprint; the title
was widened to match. The facade registration found on 2026-11-17 is unchanged apart from
moved lines (last touched in `708c119a6`). The refresh read the typed-program layer as new
scope and found the same cause there in two forms: the native program set is listed by hand
in six places, one of which already disagrees with another, and once a program is rendered
its name, signature and grants are recovered by parsing text. A draft of this refresh held
the second form as a separate finding; the independent challenge showed it is the same missing
thing, and it was merged here before publication.
The refresh also established that the self-checking registry of `schema/generate.py:540–578`
covers only the earlier core and system model ([DA-072](#da-072)), so the released model has
no generator registry at all. The 2026-11-17 delta's remark that
`semantic/target_installation.py` dispatches on a stale `scientific_layout.sql` name is
withdrawn: the name is a label that selects a generated artifact, like `closure-native.sql`
beside it (`semantic/target_installation.py:214–218, 230, 235–236`;
`semantic/archive_projection_native.py:74`; `semantic/native_products.py:179`).

**FP-03, FP-04, FP-07; A3; DP-01, DP-02, DP-16; H27.** Found in the delta of 2026-11-17 at
`1afa63f88` ([delta](README.md#delta-1afa63f88)); new in commit `708c119a6`.

A native program is a generated PostgreSQL routine. Nothing carries a program as an object,
with its name, schema, purposes, grants and place in the installation order, from the
generator to the installer. Three things follow.

*Facades are registered twice.* The native preview re-renders seven generated Python facades
from the candidate model. Their paths are one tuple (`schema/model_change.py:53–61`) and their
generator calls a second, positional tuple (`:538–548`), paired by `zip(strict=True)`
(`:550–552`). Each owner also names its own path and writer
(`semantic/typed_generation.py:87, 105, 113–117`; `semantic/pdf_call_generation.py:27, 32–35`;
`semantic/original_document_contracts.py:229, 243`), and `_pdf_native_ids.py` and
`_pdf_native_calls.py` are listed a third time in the PDF lowering list
([DA-082](execution-fit.md#da-082)). The canonical generator checks that its declared
ownership equals its emitted paths (`schema/generate.py:563–578`); these facades are outside
it.

*The program set is listed by hand in six places.* Adding a program means editing each of
them, and they must agree on names and order:

- the `(name, module file, generator)` triples and about ninety further artifact lines in
  `native_protocol_sources`, each pairing a literal artifact name with a literal module file
  name (`semantic/data_operation_storage.py:139–191` and onward to `:567`);
- the required set that the capture is checked against (`:573–682`);
- the concatenation order in `native_sql`, which joins 37 named artifacts and then appends two
  more (`:756–802`);
- the module-file list in `capture_native_authoring_inputs`
  (`semantic/native_products.py:131–153`);
- the `(label, schema, name, roles)` table in `target_native_definitions`
  (`semantic/target_installation.py:209–231`);
- a hand-ordered provider list (`target_installation.py:302–314`).

Two of these already disagree. Six artifacts that `native_sql` concatenates are not in the
required set: `data-attempt-release.sql`, `data-claim-batch.sql`, `data-claim.sql`,
`data-completion-settlement.sql`, `data-operation-renewal.sql` and `data-read-boundary.sql`
(`:573–682` against `:758–796`).

*After rendering, a program is text, and its facts are recovered by parsing.* Inside a
program, statements are typed objects. From the moment it is rendered, later steps work on
SQL text:

- the PL/pgSQL body is assembled with formatted strings, and each rendered statement is parsed
  again to assert that it is exactly one statement
  (`semantic/native_program.py:155–159, 342–455`);
- `native_sql` replaces two digest markers in the joined text
  (`semantic/data_operation_storage.py:804–808`), renames entry points by parsing, reprinting
  and re-parsing the whole text (`:715–748, 811`) and appends generated wire wrappers
  (`:814–862`); the wrapper and the rename must agree on the `ddo_impl_` naming convention
  (`:840`);
- the assembled kernel is parsed again to find its function definitions, and execute grants
  are then assigned by matching function names in the parsed text (`:1873–1914`);
- target installation parses a concatenated script once per selected function name
  (`semantic/native_authoring.py:171–199`), takes the excerpt and parses it again to build the
  definition (`semantic/native_objects.py:381–440`);
- the function inventory is rebuilt by parsing generated text
  (`semantic/native_inventory.py:83–158`), not from the program objects;
- scratch tables for authoring are produced by string replacement on compiled `CREATE TABLE`
  and `CREATE INDEX` statements (`semantic/native_authoring.py:293–313`).

**Consequence.** A facade that an owner writes but the tuple does not list is not re-rendered
from the candidate, so a preview could approve SQL whose Python call surface is the working
tree's copy, which is the drift ADR-0131 sets out to remove. The strict pairing catches a
length difference, not a reordering. A program added to one list and not another is caught
only where a later step happens to need it: if one of the six unrequired artifacts were
missing, the failure would be a `KeyError` inside `native_sql`, not the capture's classified
refusal. Identity, signature and grant facts are carried by naming conventions and markers
instead of by the objects that knew them, so each transform has to verify afterwards that it
changed only what it meant to, and the same text is parsed many times, more often as a script
gains owners. The facade and missing-artifact consequences are inferred; the duplication, the
disagreement and the text handling are established.

**Contrary evidence.** Seven facade entries, all current facades listed, count checked. The
capture's required-set check refuses a missing or duplicated artifact
(`data_operation_storage.py:570–572, 683–684`); an extra one is accepted, and the required set
is itself one of the hand lists. For the provider order there is a reason a derived order
cannot simply replace it: SQL-language bodies bind their callees when created, and the
catalog-based ordering cannot see objects that are not yet installed. Each text transform
verifies exact preservation, and each template checks its tokens. PostgreSQL needs text in the
end, and reading the server-normalized catalog back (`semantic/native_objects.py:950–1121`) is
the right final authority. Replacing the digest markers after the digest is computed is a
necessary self-reference, since a digest cannot cover its own value. The parsing cost falls on
authoring, preview and preparation; deployment uses frozen statements and imports no
generator. Whether a freshness check elsewhere catches a stale facade was not examined.

**Footprint and uncertainty.** Established for the sites listed. Whether authoring latency is
material is unknown, and whether native deployment refuses on the six unrequired artifacts
before `native_sql` runs was not examined. Related findings with other causes: the
hand-written bodies that some text is spliced into are
[DA-084](boundaries-and-composition.md#da-084), and the repeated rebuild of the whole set is
[DA-083](execution-fit.md#da-083).

<a id="da-085"></a>

## DA-085 — The LinkML part of the released model is composed separately by each consumer, holds its physical constraints as JSON strings, and is not one object with the effective operation model

**FP-04/A2; DP-01, DP-02.** Established in the refresh of 2026-11-18 at source `d78c98765`,
and narrowed by the independent challenge before publication.
**Interface-checked by source inspection, 2026-11-18.** The full inventory behind this finding
is the [domain model map](domain-model-map.md).

LinkML is the modelling language the project uses for classes, value sets and physical tables.
A `SchemaView` is LinkML's in-memory view of a schema and its imports. The finding has three
parts.

*Each consumer composes its own view of the LinkML model.* 43 LinkML schema files sit under
`model/semantic/` (counted by schema header, 2026-11-18). No single compiled object holds
them. Each consumer builds its own import closure and its own `SchemaView`:

| Consumer | Site |
|---|---|
| Physical tables | `schema/physical.py:166–197` |
| Semantic release | `semantic/prepare.py:350–373` |
| Operation call sources | `semantic/native_call_sources.py:95–117` |
| Projection analysis | `semantic/projection_analysis_products.py:85–107` |
| Companion projection (read from disk) | `semantic/companion_projection.py:552` |
| Rule views, conditional rules, ontology, source values | `semantic/rule_views.py:402`; `semantic/conditional_rules.py:178`; `semantic/ontology.py:159, 260, 626`; `semantic/source_value_native.py:56` |

Three of these (release, call sources, projection analysis) are near-identical copies of one
routine that seeds an import map, merges imports and wraps the result again. The call-sources
copy also keeps a hand map between file names and schema names
(`semantic/native_call_sources.py:57–64`).

*Physical constraints are JSON strings inside annotations.* Foreign keys, checks and indexes
are encoded as JSON text in `ph:foreign_keys` (117 occurrences), `ph:checks` (68) and
`ph:indexes` (32), decoded by custom code (`schema/relational.py:297, 548–563`). LinkML
tooling cannot see them, and foreign keys are not expressed as slot ranges.

*The other formalisms restate some of the same facts.* The model directory also holds a JSON
Schema protocol, custom YAML catalogs and JSON files (listed on the map). Their existence is
not the finding. What source shows is restatement between them and the LinkML part in
specific places: the kind-universe values are a check predicate in the physical model
(`model/semantic/data-operation-physical.yaml:71`), a literal set in the operation compiler
and a typed literal in the effective model ([DA-086](#da-086)); and two JSON value codecs
take their vocabulary from two authorities, one from LinkML and one from Python types
([DA-086](#da-086)). In the other direction a derivation exists and works: physical value
sets are taken from the protocol through `ph:values_from`
(`model/semantic/data-operation-physical.yaml:11–14`).

**Consequence.** Each generator sees its own LinkML view, and the LinkML views and the
effective operation model are not one object that a generator reads together. A fact that
crosses them (a role, the relation between an operation and a kind, the class of a relation)
has no shared object to be derived from, which is one reason membership facts fall back to
Python lists ([DA-070](#da-070), [DA-074](native-integrity.md#da-074), [DA-086](#da-086)).
A change to the composition rule has to be made in three copies.

**Contrary evidence.** That operations have two authoring routes is an accepted decision, not
a defect. [ADR-0092](../../adr/0092-ddo-operation-authority.md) rejected making Python the sole
authoring source and selected "Compile both admitted authoring routes into one effective
model", with declaration-owned protocols and implementation-owned typed Python definitions as
admitted front ends (`:19–25`). About 62 Python modules declare an operation (85 mention the
attribute name), and they are compiled with the protocol into one effective operation model
per release, with tracked origins and refusal of conflicting owners
(`semantic/data_operation_compilation.py:806–1864`). Operations and the protocol are outside
LinkML by that design; questioning it would be a revisit of ADR-0092, not an audit finding.
Separate closures per artifact also partly serve custody: each captured closure is what that
artifact's identity covers, so some separation is by design. Each closure routine refuses an
unresolved import and has no filesystem fallback (`semantic/prepare.py:354–360`;
`semantic/projection_analysis_products.py:88–91`), and the physical closure is
content-identified and pins the LinkML types bytes (`schema/physical.py:142–197`).

**Footprint and uncertainty.** Established for the composition sites, the copied routine and
the annotation encoding. Whether the separate closures ever differ in result was not tested.
That the separate views cause the hand lists is an inference from their co-occurrence, not
established. The LinkML features that the model does and does not use are listed on the
[map](domain-model-map.md#linkml-features); an unused feature is not a finding.

**Relation to DA-072.** Separate cause. DA-072 is an earlier generation of the model that was
not retired. This finding is about the current generation.

<a id="da-086"></a>

## DA-086 — Generators and analytical modules restate as Python literals facts that the model declares or that a typed source already carries

**FP-02, FP-04; DP-01.** Established in the refresh of 2026-11-18 at source `d78c98765`.
**Interface-checked by source inspection, 2026-11-18.** Counts marked "survey" are regular
expression counts by the generator lane and include some benign matches.

This differs from [DA-070](#da-070), [DA-073](#da-073) and
[DA-074](native-integrity.md#da-074), where no declaration exists and the hand list is the
only statement of the fact. Here a declaration or a typed source exists and the code does not
read it.

- **Task states.** The protocol declares the task lifecycle, with its initial, running and
  terminal states and its transitions (`model/semantic/data-operation-native.yaml:5–14`), and
  the task guard trigger is rendered from it (`semantic/data_operation_protocol.py:116–160`).
  The kernels test string literals instead: the claim program compares the status with
  `"running"` (`semantic/data_claim_native.py:77`). The count of such literals depends on the
  method: quoted `pending` or `running` alone appears about 22 times in the generator modules, and
  all six state names appear 62 times in sixteen modules, a figure that includes uses of
  `empty` and `failed` as outcomes (the independent challenger's counts).
- **Value-codec vocabulary.** The data-operation value codec takes its tags from Python
  `Literal` types and adds a hand tuple of text-like tags
  (`semantic/data_operation_value_native.py:44–50`). The SourceValue codec beside it takes its
  variants from the LinkML observations schema and refuses on drift
  (`semantic/source_value_native.py:55–66`). Two JSON value codecs in PostgreSQL therefore have
  two different authorities.
- **Field kind to type.** The model declares this mapping: each LinkML type carries a `uri`
  and, where needed, a `ph:sql_type` annotation (for example `json_payload` at
  `model/semantic/physical.yaml:33–36`), and the physical compiler resolves them
  (`schema/relational.py:79–89, 437–440`). Beside that declared fact and its resolver, the
  mapping is written four more times: PostgreSQL names and SQLAlchemy constructors as strings
  (`semantic/native_call_contracts.py:16–25`), Python names
  (`semantic/native_call_sources.py:28–37`, with a reverse map at `:133–136`), SQLAlchemy
  classes (`semantic/pdf_search_native.py:98–104`), and a special case for `int4`
  (`semantic/native_program.py:621–622`).
- **Profiles and kind universes.** `_PROFILES` and `_KIND_UNIVERSES` are literal sets
  (`semantic/data_operation_compilation.py:85, 341`) beside the typed `Literal` that already
  carries the profiles (`semantic/data_operation_model.py:497`). The universe values are
  written a third time as a check predicate in the physical model
  (`model/semantic/data-operation-physical.yaml:71`).
- **Analytical relation shapes.** Three DuckDB modules declare their Arrow input schemas by
  hand: the rich-rule views (`semantic/analytical_kernels.py:21–60`, with projected attribute
  names at `:62`), candidate boxes (`ingest/pdf_candidate_geometry.py:60–72`) and the
  recognition replay (`ingest/pdf_stream_reconciliation.py:233–241`). The companion export
  restates family grouping columns and excluded provenance columns
  (`serve/companion_export.py:419–424, 557–589`) that the projection's role annotations
  describe.

**Consequence.** A change to a declared state, tag, field kind or column does not propagate to
these sites, and compilation does not refuse; each is a place where a model change has to be
remembered. ADR-0131 states that a model field or type change "propagates to its generated SQL
and calls, or compilation refuses"
(`docs/adr/0131-model-owned-postgresql-programs.md:46`); that holds for relations and columns
and does not hold for these facts.

**Contrary evidence.** Relations and columns are resolved against compiled metadata, so a
missing relation or column fails at generation. The pattern that would close several items is
already in use: the trust-scope program reads its universe values from the typed `Literal`
with `get_args(get_type_hints(...))` (`semantic/support_trust_native.py:91`), the SourceValue
codec checks its closed set against LinkML, and Arrow schemas for PDF records and exports are
derived from compiled metadata (`semantic/pdf_record_model.py:103–122`;
`semantic/arrow_types.py:13`).

**Footprint and uncertainty.** Established for the sites cited. The rich-rule view relations
and the two ingest schemas have no declared counterpart to derive from, so for those the
restatement is of shapes the code builds elsewhere, and whether they belong in the model is an
owner question. The same survey counted about 160 native function names called as free
`func.<schema>.<name>` references in seventeen sampled generators, bound only when PostgreSQL
installs the program; that was not examined further. A related item with its home elsewhere:
shared-stream trigger membership is chosen by relation name although the model declares the
class that would select it ([DA-074](native-integrity.md#da-074)).

## Lower-weight observations

- The token-to-type table is duplicated between the writer and the reader
  (`semantic/prepare.py:93–104`; `semantic/archive_reader.py:40–51`), and compact-encoding
  defaults for the effective model are restated in three places
  (`semantic/data_operation_model.py:133–149, 1000–1027, 1275–1287`). Most drift is caught by a
  digest or round-trip check.
- Enforcement claims are typed as documentation or as checked. By search, about 245 records are
  `documentation` and three are explicitly contract- or native-checked. This is the current
  form of DA-027's limit: the claims are honest about what they are, and the correspondence of
  each body remains unexamined.

## Prior identities on this page

<a id="da-001"></a>
<a id="da-002"></a>
<a id="da-003"></a>
<a id="da-004"></a>
<a id="da-005"></a>
<a id="da-006"></a>
<a id="da-007"></a>
<a id="da-008"></a>
<a id="da-009"></a>
<a id="da-010"></a>
<a id="da-011"></a>
<a id="da-026"></a>
<a id="da-027"></a>
<a id="da-028"></a>
<a id="da-034"></a>
<a id="da-046"></a>
<a id="da-048"></a>
<a id="da-049"></a>
<a id="da-062"></a>
<a id="da-065"></a>

Earlier text is in Git at `fbd3f2a98`. "Not re-examined" means the last evidence keeps its
original date and may describe sources that no longer exist.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-001 | Changed footprint, not re-verified | `comparison_projection` is still compiled (`semantic/prepare.py:940–945`); the cited consumer is gone |
| DA-002 | Not re-examined | Cited `consolidation.py` and `contracts.py` are gone |
| DA-003 | Changed footprint | `display_properties` now at `semantic/types.py:398`; cited consumers gone |
| DA-004 | Not re-examined | Cited `domain_operations.py` is gone; the question stays open |
| DA-005 | Not re-examined | Evaluator site gone |
| DA-006 | Not re-examined | — |
| DA-007 | Not re-examined | Cited owners gone; the current owner of identity decisions was not located |
| DA-008 | Correction stands | Casefold only where a property declares it (`semantic/types.py:426–429`) |
| DA-009 | Stands, not re-verified | `semantic/types.py:427` consumes `unicode_identity` |
| DA-010 | Changed footprint | Explicit acquisition is `semantic/data_operation_preparation.py:136–268` |
| DA-011 | Correction stands | Compiler 24 / boundary 13 agree with D2 |
| DA-026 | No longer applicable | Replaced by the compiled effective model and generated call artifacts |
| DA-027 | Standing limit, changed footprint | See lower-weight observations above |
| DA-028 | No longer applicable | Query plugins are gone; the successor concern is [DA-076](served-claims.md#da-076) |
| DA-034 | Correction stands | One shared scientific owner; the new identity issue is [DA-077](served-claims.md#da-077) |
| DA-046 | Standing question | `domains/toy/semantic.yaml:36–44`; see DA-072 for the duplicated core vocabulary |
| DA-048 | Changed footprint | One root per acquisition manifest |
| DA-049 | Stands | Current-only reading (`semantic/data_operation_model.py:1211–1216`) |
| DA-062 | Not re-examined | Cited `record_publication.sql` and replay module are gone |
| DA-065 | Not re-examined | Cited replay module is gone |
