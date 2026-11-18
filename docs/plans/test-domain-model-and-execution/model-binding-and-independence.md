# Model binding and independence

**Status:** Proposed companion of the
[test domain-model and execution plan](../test-domain-model-and-execution_2026-11-17.md); not started.
**Created:** 2026-11-17. Writing this plan authorizes no implementation.

This companion owns the designs of TDM-02 (the model-binding rule written into the
test-assessment companion), TDM-03 (scenarios bound to production acquisition and to the model
their release contains, one PDF recipe composer, one recipe-extension helper), TDM-04 (identity
vectors that carry their authored inputs, and a request-identity vector) and TDM-05
(generated-program tests that assert meaning, and the sites where an expectation is produced by
the code under test). Package state, the queue, finding dispositions, shared contracts, rejected
options and handovers are the [coordinator's](../test-domain-model-and-execution_2026-11-17.md).

**Baseline and evidence.** Section references written `§n` point to the
[source review](../../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
which read source at `1afa63f88`; this companion develops its §3, §5.1 and the model-change rows
of §8. Every design statement here is **Proposed**. The plan was authored against commit
`50827eb9f` (the authoring baseline, 2026-11-17) and revised against commit `12f57dc4d` (the
revision baseline, 2026-11-18), after the model-owned SQL conversion
([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was completed. The conversion is
under validation, so source may still move a little; TDM-00 re-reads what changed since
`12f57dc4d`. Source facts re-read at the revision baseline are **Interface-checked by source
inspection, 2026-11-18**, and line citations are to that commit. Facts that were not re-read keep
their 2026-11-17 label: in this document those are TDM-02's table of places that reference the
standard, the role-name file count in TDM-03 and the 41 inline-schema files. Nothing was run, and
where this page says a test cannot pass it says so "by reading, not run". No speedup is claimed.
The investigation reports behind the counts and site lists are in the evidence folder
`docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../../design_review/evidence/2026-11-17_test-plan-authoring/state.md) and the
[identity re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md), which re-read this companion's
sites at `12f57dc4d`. Each package below carries a short note of what the conversion delivered in
its area. `tests/…` and `src/…` are relative to `python/corpus-structure/`; repository-root paths
are written as root `scripts/…` or `docs/…`.

## Why this work exists

A test uses many values that also exist in the product: which files make up a domain pack, which
model a release runs, the bytes an identity is computed over, the text of a generated SQL
statement. For each such value the test author makes a choice, usually without noticing it: copy
the value by hand, obtain it from the product, or compute it by calling the product. Each choice is
right in some places and wrong in others, and the current tests have no stated rule for which is
which. The review found five different wrong answers to this one question (§2, item 1):

- support modules that type the statistics pack's file list by hand, so they describe a pack that
  production no longer necessarily acquires (DTA-042);
- one support module that prepares a release and, beside it, compiles a model the release does not
  contain (DTA-042);
- identity vectors that share the expected bytes but leave each consumer to rebuild the input, so
  one consumer's input went stale (DTA-033);
- tests of generated SQL whose expected text was copied from the generator's own output (F07);
- tests whose expectation is computed by the function under test (§3.3).

The remedy is one rule and its application. The rule is stated once in the coordinator and, through
TDM-02, in the standard the audits and reviews load. This companion applies it to the places where
a test restates a model fact by hand when it should bind to the owner (TDM-03), and to the places
where a test binds to the product when it should hold an independent expectation (TDM-04, TDM-05).

**What this companion consumes.** The operator's decision of 2026-11-17 that the rule goes into the
test-assessment companion as a change to the standard; production pack acquisition
(`src/corpus_structure/semantic/regeneration.py`); the release-bound model reader
(`src/corpus_structure/semantic/data_operation_admission.py:39`); the existing literal identity
vectors; pglast as already used by `tests/semantic/test_pdf_prepare_model.py`.

**What it produces.** Version 1.3 of the test-assessment companion; one owner for each scenario
fact that tests currently restate; vectors whose inputs cannot drift from their expected bytes;
generated-program tests that survive a renderer change which keeps meaning.

**Where its responsibility ends.** Two faults that the review places beside circularity are
corrected by other companions because they live at controlled boundaries: the copied reservation
formula (DTA-043, TDM-10) and the refusal a test double invents (DTA-045, TDM-11), both in
`controlled-boundaries-and-seams.md`. Production SQL read by path or sliced by text (DTA-047) is
TDM-16 in `declarations-retirement-and-execution.md`; the readers of deleted files
(`tests/semantic/test_native_sql_body.py:205–207`, `test_native_closure.py:268–290`) are repaired
at entry by TDM-01. The split of a
recipe from the place where it executes (DTA-040) is TDM-07 in `preparation-identity.md`; its
interaction with TDM-03 is described under [Sequencing](#sequencing-and-shared-surfaces). Reuse and
skip mechanisms other than the two sites named in TDM-05 are TDM-13 in
`reuse-and-refusal-evidence.md`. No production change is in scope here; production observations
are in the coordinator's [handover table](../test-domain-model-and-execution_2026-11-17.md#handovers).

## The rule

The coordinator's [shared contracts](../test-domain-model-and-execution_2026-11-17.md#shared-contracts) define the model-binding rule:
a value a test uses is an *expectation*, part of a *correspondence* claim, or *scenario
construction*, and its role decides its source. This page uses those three words in that sense.
The two clarifications matter most below: a name that selects something (a demand target such as
`"source.pdf_views/discovery"`) is a coordinate and stays literal; a set of names is enumerated
from the model when it only generates cases, and is authored by hand, with one member the
declaration lacks, when the set's correctness is the claim.

## Baseline at `12f57dc4d`

The conversion corrected one of these sites, the native identity consumer's missing input key,
and none of the others. The scenario support modules, the vector module, the kernel support and
production's acquisition and composition functions are unchanged since the authoring baseline, so
their citations hold. The conversion deleted `semantic/sql/data_operations.sql`; what this page
cited there now lives in generator modules, named below.

**Pack composition typed by hand (DTA-042).** Five support modules build a `SourceBundle` from
three files read from disk (the statistics pack's `semantic.yaml`, the model's `core.yaml`, the
pack's `terminology.yaml`): `tests/semantic/record_contracts_support.py:48–66`,
`tests/evaluation_record_alignment_support.py:45–63`,
`tests/methods/record_assembly_support.py:23–49`, `tests/methods/m1_producer_support.py:32–54` and
`tests/evaluate/declared_record_grading_support.py:34–48`. Production composes the same bundle in
`acquire_pack` (`src/corpus_structure/semantic/regeneration.py:60–110`), which reads the pack's
declared name, adds `core.yaml` under the name `semantic_core`, and obtains the terminology module
from `acquire_terminology`. One support module already binds to production:
`tests/statistics_pack_support.py:10–25` calls `prepare_packs((DOMAINS / "statistics",))` in a
session fixture. The same typed bundle also appears in three test modules
(`tests/semantic/test_declared_record_sources.py:201–205`, `test_m1_declared_products.py:34–38`,
`test_statistics_model.py:20–24`) and, for the toy pack, in
`tests/semantic/current_pdf_integration_support.py:63` onward,
`tests/orchestrate/test_source_demand_native.py:42`, `tests/semantic/test_native_definition_demand.py:63`
and `test_native_parser_demand.py:60`. One further file reads the statistics pack's files into a
bundle, `tests/semantic/test_data_operation_compilation.py:714–720`; compilation is its subject,
so it is probably a legitimate local use, and TDM-03's first step confirms that.

**A model compiled beside its release (DTA-042).** `tests/evaluate/declared_record_grading_support.py:34–57`
calls `prepare_release(bundle)` with no dependencies and then
`compile_data_operations(bundle, declarations=(reading_resolution_declarations(),), python_sources=reading_resolution_operation_sources())`.
The release therefore does not contain the model the tests use with it, and `cut()` (`:61–77`)
writes that release's id into a selection that the model's operations are then evaluated under.
Six modules import this support.

**Two functions named `current_pdf_recipe`.** `tests/semantic/current_pdf_source_support.py:46`
(`directory, *, math_context=False`) and `tests/semantic/current_pdf_integration_support.py:63`
(`directory, *, integration_policy=None`). They repeat the same spine: the literal `PdfRecipe`,
`PreparedPdfAssets(directory, b"{}", ())`, the capture sources under `directory / "owned"`,
`native_protocol_sources()`, `pdf_domain_dependencies`, `capture_port_generator_sources()`, one
call of `data_operation_dependencies`, and a `KernelRecipe` with `execution_profile="source-native"`
and `PreparationProfile(version="semantic-2")` (`current_pdf_source_support.py:103–124`,
`current_pdf_integration_support.py:131–150`). There are 23 call lines in 19 files.

**The recipe-extension sequence.** Fifteen sites in thirteen files (the review counted "about
twelve") repeat one sequence: read the recipe's captured inputs back with
`read_data_operation_inputs`, drop every dependency artifact whose name starts with
`"data-operations/"`, and call `data_operation_dependencies` again with more declarations and
sources. The sites are `tests/evaluate/declared_record_native_support.py:165`,
`declared_rich_native_support.py:55`, and under `tests/semantic/`:
`characterization_native_support.py:71`, `current_artifact_support.py:55`,
`current_contextual_support.py:143, 202`, `current_pm2_native_support.py:49, 176`,
`operation_event_native_support.py:46`, `rich_domain_external_support.py:56`,
`rich_domain_native_support.py:59`, `structural_admission_native_support.py:62`,
`structural_production_native_support.py:58`, `test_actual_e5_selected_context_native.py:128` and
`test_selected_native_scoring_native.py:70`. The prefix is production's private constant
`_DATA_PREFIX` (`src/corpus_structure/semantic/composed.py:14`); the filter is needed because
`data_operation_dependencies` refuses inputs that already carry packaged artifacts (`:30–31`).
`read_data_operation_inputs` (`composed.py:82`) is still the only production reader of packaged
inputs, and no production function reopens them.

**The admission order restated.** Production has no single release-admission operation; the
sequence of `persist_release`, `admit_data_operation_release` and `persist_runtime_binding`
appears in `src/corpus_structure/schema/model_deployment.py:994–1010` and
`src/corpus_structure/schema/releases.py:585–598`. `admit_kernel`
(`tests/semantic/data_operation_kernel_support.py:228–252`) restates it for tests. Five test
files restate it again, in whole or in part: `tests/orchestrate/test_data_operation_cross_release_native.py:96–100`
(all three steps), `tests/semantic/test_original_document_custody_native.py:34–37`,
`test_record_archive_guards_native.py:106–109` and `test_original_descriptor_registration.py:111–112`
(persist and admit; the last was added by the conversion), and `test_execution_release.py`
(`:40, 57, 119, 138, 153`), whose claims are about the individual steps.

**Identity vectors (DTA-033).** `tests/semantic/data_operation_identity_vectors.py:7–13` defines
`ContextualProductVector` with the fields `name`, `project`, `source`, `scope` and `literal`. The
authored literal includes `["subject_definition",["string","document"]]` (`:17–24`), but the record
has no such field. The Python consumer passes `subject_definition="document"` itself
(`tests/semantic/test_data_operation_identity.py:38, 48`). The native consumer builds its input
mapping by hand (`tests/semantic/test_data_operation_identity_native.py:23–41`); the conversion
added the missing key as a constant, `"subject_definition": "document"` (`:32`, commit
`d422c48e7`), so its five parametrized cases can now pass, by reading. Both consumers still
supply the value themselves. The native consumer also passes the scope through `json.loads`
(`:34`) and `json.dumps` (`:40`), so the case named `equal-json-number` no longer sends the
spelling `1.2500` that distinguishes it. The request identity
(`SemanticRequestKey`, `src/corpus_structure/semantic/data_operation_identity.py:502–530`) has no
literal vector, and its completeness test does not vary `subject_definition`
(`test_data_operation_identity.py:407–430`). The native side computes the same request identity
with the installed function `data.ddo_identity`, which is now a generated program
(`src/corpus_structure/semantic/data_operation_value_native.py`, the routine at about `:447`);
its callers under the tag `semantic-request` are
`src/corpus_structure/semantic/request_attachment_native.py:1526` and
`binding_admission_native.py:213`.

**Generated-program tests that assert spelling (F07).** Substrings of rendered text:
`CAST('english' AS REGCONFIG)` and `USING gin (search_vector)`
(`tests/semantic/test_pdf_source_search_projection.py:36, 40`), `CAST('simple' AS REGCONFIG)`
(`:124`), `REPEATABLE READ, READ WRITE` (`tests/semantic/test_companion_export.py:398`),
`LOCK ops.pdf_artifact_part` (`tests/schema/test_pdf_shared_stream_data_steps.py:55`) and
`kind = 'execution_model'` (`tests/semantic/test_target_installation.py:276`). One equality between
two production values: `tuple(relations) == RETIRED_PARTS` (`test_pdf_shared_stream_data_steps.py:98`,
with `:59–60`), where `RETIRED_PARTS` is `src/corpus_structure/schema/data_step_programs.py:52`.
The conversion added two assertions of the same kind:
`"float8send(CAST(kb.pdf_record_access.ordinal AS DOUBLE PRECISION))" in str(equality)`, with
`"ordinal DOUBLE PRECISION"` beside it (`test_target_installation.py:294–295`, rewritten from an
older spelling of the same expression), and `'"position" bigint' in program`
(`tests/semantic/test_native_program_table_outputs.py:35`).

**Expectations produced by the code under test (§3.3).** The lowering-identity test compares
`require_lowering_identity(context)` with the digest of the artifact the same context returns
(`tests/semantic/test_pdf_producer_certification.py:135–146`); the function returns that digest by
construction (`src/corpus_structure/semantic/pdf_lowering.py:276–310`). The scalar validity
function delegates to the set evaluator: both are generated in
`src/corpus_structure/semantic/data_validity_native.py`, the closure routine `ddo_valid_closure`
at about `:578` and `ddo_node_valid` at about `:643`, built as a selection from the closure
(`:624`). The scalar journeys are therefore no reference for the closure; one test addresses the
closure directly with duplicate seeds and a deliberate cycle
(`tests/semantic/test_data_operation_storage.py:2821–2847`). The expected search selection digest
is rebuilt by running the production projection (`tests/semantic/test_source_search.py:141–185`,
asserted at `:222–227`).

**What is deliberately independent today and stays so.** The record-contracts support authors its
fixture coordinates and role expectations by hand and finishes them through production identity
functions; the storage-posture test keeps a hand list of relations and purpose roles because
derived grants are its claim (`tests/semantic/test_data_operation_storage_posture_native.py:7–19`);
`tests/semantic/test_physical_checks.py` keeps hand-authored predicates on a throwaway schema;
`JSON_MEANING_VECTORS` and the framing vectors are literal; the golden evaluation sets and archived
source fixtures are authored inputs. TDM-03 changes how some of these modules obtain their
*scenario*; it changes none of their *expectations*.

## Target design

**One owner per scenario fact.** A test that needs a maintained domain pack obtains it from
production acquisition. A test that needs a model together with a release reads the model from that
release. A test that needs a PDF kernel recipe calls one composer. A test that needs a recipe with
more operations calls one helper. In each case the hand copy is deleted, not kept as a fallback.

**Independent expectations where the value is the claim.** An identity vector is an authored input
together with authored canonical bytes; the digest is computed with the standard library. A test of
generated SQL asserts what the statement means, through the parsed structure or through PostgreSQL's
behaviour. A test of a reuse or evaluation mechanism states the expected outcome as a literal for a
small case designed by hand.

**What is preserved.** Every hand-authored expectation listed above. Literal demand targets and
operation names used to select. Tests whose subject is pack composition itself
(`tests/schema/test_packs.py`, `tests/semantic/test_pack_acquisition.py`, `test_terminology.py`,
`test_alias_policy.py`, `test_schema_product_cli.py`, `tests/test_cli_schema_diagnostic_boundaries.py`)
keep calling acquisition as the code under test and keep their hand-written expected members.
Tests that author their own small domain schema keep doing so.

**What deliberately changes.** Scenario releases built from a maintained pack follow production
acquisition, so a change to what a pack contains reaches these tests without an edit, and a test
whose claim depends on the changed content fails for that reason. The grading scenario's release id
changes, because the release now contains its model. Renderer spellings stop being asserted.

**Alternatives rejected.** A shared test-side copy of the pack bundle would put the restatement in
one place but would still drift from acquisition (§5.1). Building the native vector input through
production's subject context would make the input follow production and hide a framing mistake made
the same way on both sides (§5.1). Keeping the spelling assertions and updating them on each
renderer change repeats F07's cause.

**What would reopen these choices.** If production moves pack composition into the model
([DA-073](../../design_review/audit/semantic-model-and-authority.md#da-073)), the acquisition call
in the scenario owner changes and nothing else does; that is the intended effect, not a reopening.
The choice to bind would reopen only if acquisition became too expensive to run once per worker
process for tests that need no database, which would be seen as a visible cost in the pure lanes
after TDM-03; the answer then is a narrower acquisition entry point in production, handed over, not
a return to hand copies.

**Credible changes the target accommodates (from §8).** Adding a modeled field: scenarios follow
through acquisition and only tests whose claim includes the field change. Adding a terminology or
rules file to a pack: no test-support edit. Changing the SQL renderer without changing meaning: no
generated-program test fails. Changing the framing of an identity on both the Python and the native
side: a vector fails.

## Pivotal library capability

**pglast `parse_sql` for the meaning of generated SQL.** TDM-05 uses pglast to read a generated
statement as a parse tree and assert the node that carries the meaning (a type cast's target type,
an index's access method, a transaction statement's options, a lock statement's relation). pglast
parses and does not execute, so it establishes structure and not behaviour; where behaviour is the
claim the test runs the statement on PostgreSQL in the rollback class. The repository already uses
it this way in `tests/semantic/test_pdf_prepare_model.py:17–51` and
`tests/semantic/test_target_installation.py:202–238`, and the conversion added
`tests/semantic/native_program_support.py`, whose `routine_declaration` parses a generated
program with `parse_sql` and returns one routine's declaration renamed into `pg_temp`. The pinned
version is the one in the lockfile and no new dependency is added. One limit matters: `parse_sql` does not look inside a
PL/pgSQL function body, which is a string constant to the SQL grammar. For a body, pglast offers
`parse_plpgsql`, already used at `test_target_installation.py:99–119`; it returns the PL/pgSQL
tree as plain dictionaries, with embedded SQL expressions as text, so an assertion on a statement
inside a body is coarser than one on top-level SQL. Whether the `LOCK` statement of the
shared-stream data step sits inside such a body is not established here (see TDM-05). Reference:
existing use at the lines above; [pglast documentation](https://pglast.readthedocs.io/). The shape
of the `parse_plpgsql` result is stated from the library's documentation and not confirmed against
the pinned version; confirming it is the first step for any site that uses it.

## TDM-02 — The model-binding rule in the test-assessment companion

**Needs.** Nothing. It is first among this companion's packages because TDM-03, TDM-04 and TDM-05
are applications of the rule and cite it.

**Where the rule goes.** The companion is
`docs/design_review/design_principles/core/test-assessment.md`, version 1.2 of 2026-10-23. Its §1,
"Independence relative to the claim", is organized by the *kind of production element* a test
reuses (types, builders, calculations, schemas). The rule is organized by the *role a value plays
in the claim*, which is the question a reviewer has to ask first. The rule therefore extends §1 as
a titled subsection placed after §1's closing paragraph on independent oracles (the paragraph that
ends "No universal second implementation is required"). It does not become a new numbered section
and no section is renumbered, because audit findings cite the companion by section number
("companion §1, §4, §5") and those citations must keep their meaning. Two one-sentence pointers to
the new subsection are added: in §2 after the paragraph on case-defining inputs, and in §5 after
the sentence on a double that introduces its own decision rules. §1's existing table is not
rewritten; the new text sharpens two of its rows (builders used for valid setup; schemas and
registries used for generated case selection) and contradicts none.

**What the text must establish.** This plan gives the content, not the wording.

- The question: for each value a test uses, what role it plays in the claim.
- The three roles and where each value comes from: an expectation is not produced by the code
  under test or read from its output; a correspondence claim takes its expected value from the
  declaration the test itself changed; scenario construction takes its values from the model's
  owner.
- The consequence for a derivation made beside the owner: compiling or composing a second copy of
  something the scenario already obtained from its owner is neither bound nor independent. It is a
  second authority that can diverge.
- The two clarifications: a name used to select is a coordinate and stays literal; a set of names
  is enumerated from the model when it only generates cases, and authored by hand for a small model
  with one undeclared member when the set's correctness is the claim.
- Two neighbouring faults the same question exposes: a test that re-implements production logic to
  compute its expectation, and a double that raises a refusal the real boundary does not have.
- An examples table with two columns, "bind to the model" and "keep independent", in generic terms.
  Its rows cover: what a configuration or package is composed of; the model a release runs; lists of
  operations or members; fixture and declaration names; column lists; scenario recipes; identities;
  generated program text; doubles. The review's §3.2 is the source for the rows.

**Two constraints on the text.** The companion states that it "adds no principle, MUST, gate,
score, coverage threshold" and that it is repository- and domain-agnostic. The new subsection is
written in the same register, as a question and the judgments that follow from it, and it names no
file, package, finding or pack of this repository. The repository's own instances stay in the
review's §3.2 and in this plan.

**The version change.** The version line becomes "Version 1.3" with the date of the change. The
purpose statement that the companion adds no principle remains true and stays.

**What else changes with the standard, and what does not.** Found by search of the repository at
`50827eb9f` for every reference to the companion (not re-read at `12f57dc4d`; the conversion does
not edit the standard):

| Place | State at baseline | Action |
|---|---|---|
| `docs/design_review/design_principles/standard.toml` | `[core].test_assessment` names the path; no key carries the companion's version (`version = "3.3"` is the core's) | None. The path does not change |
| The binding, `binding/corpus-structure.md` | Loads the companion through the manifest key (line 90); its "Standard applied" table has no companion row; lines 96–97 require the test account to record the companion version it applied | None required |
| Skills that load the companion: `design-principle-audit-tests`, `design-principle-audit`, `design-review`, `plan-improvement-review`, and `.claude/skills/README.md` | Each names the companion by manifest key or path; none cites a version number | None |
| `core/design-principles.md:19–22` | Describes the companion's subjects in one sentence | None. Editing it would be a change to the core at 3.3 |
| Audit accounts: `docs/design_review/test-audit/README.md:17`, `docs/design_review/audit/README.md:19` | Record "test-assessment 1.2" as the standard their baseline was audited against | Not edited by TDM-02. They state what was applied; the next audit refresh (returned through TDM-18) records 1.3 |
| Dated reviews and plan-improvement reviews that cite 1.2 | Historical statements | Not edited |
| `AGENTS.md` "Validators are shared" | Agrees with the rule (tests of a validator keep independent expectations) | None; the new text is checked against it for agreement |
| Publication | `scripts/docs.py:71–79` includes the companion in the published standard | Run `uv run ci docs check` after the edit |

**One thing to establish at entry.** `standard.toml` says template updates arrive through
`copier update`. Whether `test-assessment.md` is a file the template manages is not established
here. TDM-02's first step is to check; if it is, the next `copier update` would present the 1.3
text as a conflict, and the operator decides whether the change also goes to the template. This
does not block the package.

**Failure behaviour.** There is none at run time; the product is text. The failure to avoid is a
text that a reader applies differently from the review.

**Acceptance evidence.** The reading is done by a reader who has not seen the review: a fresh
delegated agent that receives only the amended companion and the source of a fixed sample of test
sites, and classifies each value the sample names as expectation, correspondence or scenario
construction. The sample is fixed in the package's first step, before the text is drafted, from
the sites the review classifies in its §3.2 and §3.3, and it contains at least these five: a
domain bundle typed in test support (scenario construction, bound to acquisition); a hand list of
relations and roles in a test whose claim is derived grants (an expectation, which stays); an
identity compared with the digest of the artifact the same function returns (an expectation
produced by the code under test); a literal demand target (a coordinate); and the expected
membership of a validity family (a set whose correctness is the claim, authored by hand with one
undeclared member). The agent's result is compared with the review's classification of the same
sites. A disagreement is resolved by amending the text and repeating the reading with a new
agent; the sample is not changed to fit the text. The classifications are recorded in the
package's commit message. `uv run ci docs check` passes.

**Delivered by the conversion.** Nothing; the conversion does not edit the standard.

## TDM-03 — Scenarios bound to production acquisition and the release's model

**Needs.** TDM-02, for the rule the classification below applies.

**Delivered by the conversion.** Nothing. The five support modules, the grading support, both
`current_pdf_recipe` functions, the fifteen extension sites and `admit_kernel` are as they were,
and production gained neither a function that reopens packaged inputs nor a single
release-admission operation. The conversion added one further restatement of the admission order
(`test_original_descriptor_registration.py:111–112`). The whole package remains.

**Implementation vision.** `tests/statistics_pack_support.py` becomes the one owner of "the
statistics pack as production acquires it". It exposes the acquisition as a plain process-cached
function that both its existing session fixtures and the five support modules call, because those
modules are imported as ordinary functions (by 23, 7, 15, 5 and 6 files respectively) and cannot
request a fixture. Two
levels are offered, and a consumer takes the smaller one that serves it:

- **The pack's bundle.** `acquire_pack(DOMAINS / "statistics").bundle` is the three-source bundle
  the five modules type today, composed by production. It reads files and compiles nothing. Each
  support module then applies the production extension it already applies
  (`observation_inputs`, `record_policy_inputs`, `source_product_inputs`, `m1_operation_inputs`) to
  that bundle. This is a substitution of the source of the bundle and nothing else.
- **The acquired release.** `prepare_packs((DOMAINS / "statistics",))` returns the bundle, the
  resolved dependencies, the preparation profile and the prepared release. A scenario whose claim
  needs "the statistics release as production builds it" takes this.

The second decision the package owns is the pairing of model and release. Where a scenario holds a
release and a model together, the model is `bound_data_operation_model(prepared)`, read from the
release, as `tests/semantic/data_operation_kernel_support.py:152` already does. The grading support
is rebuilt on that basis: its declarations and Python sources are packaged into the release's
dependencies with `data_operation_dependencies`, the release is prepared from the bundle and those
dependencies, and `current()` returns the release and the model the release contains. Its
hand-authored record contents, readings and references do not change.

The typed toy-pack bundles follow the same substitution through `acquire_pack(DOMAINS / "toy")`.
Two modules load a pack file and then deliberately alter it
(`tests/evaluate/declared_record_native_support.py:56–75` removes a class and renames modules;
`tests/semantic/rich_domain_native_support.py:44–52` rewrites the imports). These are local models
and stay; their starting bytes come from the acquired bundle's sources instead of a path, and the
alteration stays visible where it is.

**Telling restatement from a legitimately local model.** By search at `12f57dc4d`, 132 test files
call `prepare_release` (266 call sites) on a bundle they build. Most of them are not restatement.
Three questions decide, in order:

1. *Is pack composition the subject of the test?* Then acquisition is the code under test, the
   expected members are authored by hand, and nothing changes. (The six modules listed under "What
   is preserved".)
2. *Does the bundle's domain content come from a maintained pack directory*, that is, from files
   under root `domains/<pack>/` that `acquire_pack` also reads? Then the bundle is a restatement of
   acquisition and binds to it. If the test then alters that content on purpose, the alteration is
   a local model built on an acquired base.
3. *Is the domain schema authored by the test*, inline or in a file under `tests/`? Then it is a
   local model and is legitimate: the schema is a case-defining input and should stay visible.
   Reading the model's `core.yaml` to satisfy that schema's import is a coordinate, not a
   restatement: it names the one core every schema imports and fails loudly if it moves.

Applied to the search: nine of those files read the statistics pack's `semantic.yaml` or
`terminology.yaml` into a bundle (the five support modules, the three test modules named in the
baseline, and `tests/semantic/rich_domain_preservation_support.py:52`); seven further files
outside them type a statistics or toy pack file (the two altered copies, the four toy-pack sites
and `tests/orchestrate/test_m1_declared_native.py:66`). These sixteen files are the restatement
scope. `test_data_operation_compilation.py:714–720` is looked over under question 1. Of the
remaining files, 41 carry an inline schema and the rest build through other support; they are
local models by question 3. This plan did not open each of the remaining files; TDM-03's first
step applies the three questions to the full list and records any further restatement it finds.

The model pairing has its own scope. Thirty-nine files contain both `prepare_release(` and
`compile_data_operations(`; eight are support modules. A direct `compile_data_operations` call is
right where compilation is the subject or no release is involved. It is the DTA-042 fault only
where the compiled model is then used with a release prepared from different inputs. The confirmed
case is the grading support; the other seven support modules are read first, because a support
module's pairing reaches every consumer.

**One owner of the admission order.** Production offers no single release-admission operation
([DA-033](../../design_review/audit/execution-fit.md#da-033)), so `admit_kernel`
(`tests/semantic/data_operation_kernel_support.py:228–252`) restates the order: persist the
release, admit it, persist its runtime binding. That restatement is scenario construction held by
hand, and the rule tolerates it only in one place. This package makes `admit_kernel` the single
test-side owner of the order. The five files the baseline names are the known scope:
`test_data_operation_cross_release_native.py`, `test_original_document_custody_native.py`,
`test_record_archive_guards_native.py` and `test_original_descriptor_registration.py` move onto
the helper unless reading shows that one of the steps is the test's claim, and
`test_execution_release.py`, whose claims are the steps themselves, keeps calling them directly
with that reason recorded. The first step repeats the search for any further sequence. When
production offers the operation, the helper calls it and the restated order is deleted in that
one place.

**Role names and posture expectations.** Role names used to address rows or to connect are
coordinates and stay literal. Posture tests keep their hand-authored expected relations and roles,
because derived grants are their claim (DA-073,
[DA-074](../../design_review/audit/native-integrity.md#da-074)). No migration of the
48 files that carry role-name literals is scheduled.

**One PDF recipe composer.** The spine both `current_pdf_recipe` functions repeat becomes one
function in `tests/semantic/current_pdf_source_support.py`. It owns the literal `PdfRecipe`, the
prepared assets, the capture sources, the native protocol sources, the PDF domain dependencies, the
single `data_operation_dependencies` call and the `KernelRecipe` it returns. Its arguments are the
parts that differ: the base bundle, the operation sources to combine with capture, the extra
declarations, and the recipe's name, together with the `directory` it takes today, unchanged.
Separating the recipe's content from that location is TDM-07's change to this one composer
(see [Sequencing](#sequencing-and-shared-surfaces)). The source scenario and the integration scenario become two
thin callers with distinct names, so the same name no longer means two different functions in two
modules. The 23 call lines keep their meaning.

**One recipe-extension helper.** The helper lives beside `KernelRecipe` in
`tests/semantic/data_operation_kernel_support.py`. Given a recipe with captured inputs, added
declarations and added operation sources, it reads the packaged inputs back, removes the packaged
artifacts, composes again and returns the recipe with replaced captured inputs. It is the only
place in the tests that knows production's `"data-operations/"` prefix. It fails with an error that
names the recipe when the recipe has no captured inputs or no Python sources, replacing the bare
`assert` each site carries today. All fifteen sites call it.

**Complete consumer scope.** The sixteen restatement files; the grading support and its six
importing modules; any further mispaired support module found among the seven; the five files
that restate the admission order, and any further one the first step finds; the two
`current_pdf_recipe` definitions and their 23 call lines in 19 files; the fifteen extension sites
in thirteen files. The examples in this section are representative; the lists in the baseline are
the scope at `12f57dc4d`, and TDM-00's re-read of later changes is the scope at entry.

**Superseded machinery removed.** Every hand-typed pack bundle in the restatement scope; the
second `current_pdf_recipe`; the fifteen inline filter-and-recompose sequences; the
`compile_data_operations` call in the grading support.

**Failure behaviour.** If the acquired bundle is not byte-equal to a typed copy, the scenario's
release id changes. That is the drift DTA-042 describes, made visible; the package records which
copies had drifted and does not restore the old bytes. If a consumer pinned a literal that depends
on a typed copy's release id, it is updated deliberately in the same change.

**Acceptance evidence.** Each item is chosen so that a wrong implementation fails it.

- *The grading release contains its model.* A test reads `bound_data_operation_model` from the
  grading scenario's release and finds a reading-resolution operation named by a literal
  coordinate. At the baseline this read refuses with "release lacks an unambiguous target operation
  model" (by reading `data_operation_admission.py:41–48`, not run), so the check fails on the old
  pairing and on any pairing that compiles beside the release.
- *The extension helper removes what production refuses.* A helper test extends a small recipe
  twice with hand-named declarations and asserts, by authored names, that the result's manifest
  lists the original and both added declarations once each. An implementation that does not remove
  the packaged artifacts fails with production's own refusal ("data-operation inputs are already
  supplied or use a reserved name", `composed.py:30–31`).
- *The composer and the helper preserve recipes.* During the change, each migrated site's recipe
  identity (`recipe_id`, root `scripts/native_scenario_seeds.py:56`) is compared before and after
  with the same directory. This is a migration check recorded in the commit, not a kept test: the
  old function is the independent reference and is then deleted. The composer and helper
  consolidation lands, with this check, before the bundle substitution in the same modules; the
  identity changes that the substitution causes are then recorded separately under *Failure
  behaviour*.
- *The admission order has one owner.* A search finds the three admission calls in sequence only
  in `admit_kernel`, apart from the sites the first step recorded as claims about one step.
- *No typed pack remains.* A search finds no `SourceArtifact` built from a path under root
  `domains/` outside the composition-subject tests and the two altered copies. The search is closure
  evidence for this package and is not added as a check.
- Targeted runs: `uv run ci test -- PATH` for the five support modules' consumers, the grading
  consumers, and the PDF source and integration scenario consumers. The integration consumers'
  converter doubles now certify through production, so by reading they set up and are verified
  in this package; a consumer that still fails to set up is reported to the coordinator with its
  cause.

**If production later supplies the owners.** A production function that reopens packaged inputs
replaces the helper's body, and the prefix literal leaves the tests. A single release-admission
operation replaces the body of `admit_kernel`. A change to what `acquire_pack` composes changes
nothing here; that is the point of binding.

## TDM-04 — Identity vectors carry authored inputs

**Needs.** TDM-02.

**Delivered by the conversion; remaining scope below.** Commit `d422c48e7` added the missing
`subject_definition` key to the native consumer's hand-built mapping, so its five cases are no
longer unable to pass. That is a repair of the symptom at one consumer, made the way DTA-033
describes: each consumer still rebuilds the input, with the value as a constant of its own. The
conversion also moved `data.ddo_identity` and `data.ddo_json_meaning` from hand SQL into the
generated value program (`src/corpus_structure/semantic/data_operation_value_native.py`). The
vector record, the lost `1.2500` spelling, the missing cases and the request-identity vector all
remain.

**Implementation vision.** A vector record holds everything a consumer needs to form the input:
the kind, the body, the local subject, the project, the original source, the analyzed scope as the
exact JSON bytes the author wrote, and the subject definition; and beside them the authored
canonical bytes. `subject_definition` becomes a field of the record instead of a constant each
consumer supplies. The vector module, which is test code and calls no production function, also
offers the input in the one other shape a consumer needs: the JSON text of the complete mapping,
assembled from the same fields with the scope bytes inserted as written, so that a number's
spelling survives.

The Python consumer constructs `SubjectContext` from the record's fields and asserts the canonical
input and key against the literal. The native consumer sends the record's JSON text to
`data.ddo_identity('product', data.ddo_json_meaning(…))` and asserts the key against the
standard-library digest of the literal. Neither consumer contains a literal input mapping of its
own. Adding a field to the identity is then one edit to the record and its literals, and both
consumers follow or fail.

The package adds cases the audit found missing. The product vectors gain a case that varies
`subject_definition` and a case that varies the local subject, each with its own authored bytes. A
request-identity vector is added for `SemanticRequestKey`: authored input fields (recipe, subject,
inputs, parameters, inference policy, subject context) and authored canonical bytes under the
domain tag `semantic-request`, consumed by the Python test and by a native test that calls the
installed `data.ddo_identity('semantic-request', …)` by name on the head, the same call the
generated request-attachment and binding-admission programs make. The request completeness test
varies `subject_definition` alongside project, source and scope.

**Decisions the package owns.** The record's field set and the form of the native input. The
canonical bytes are authored from [ADR-0100](../../adr/0100-ddo-contextual-identities.md) and the
version-1 framing contract, as the existing header comment of the vector file says. When a newly
authored literal and production disagree on first run, the disagreement is investigated as a
possible product defect or a misreading of the contract. It is never settled by copying the
production output into the literal.

**Complete consumer scope.** `tests/semantic/data_operation_identity_vectors.py`;
`tests/semantic/test_data_operation_identity.py:35–63` and `:407–430`;
`tests/semantic/test_data_operation_identity_native.py:23–41`. No other module imports
`CONTEXTUAL_PRODUCTS` at `12f57dc4d`.

**Superseded machinery removed.** The hand-built input mapping in the native consumer, with its
`"subject_definition": "document"` constant; the `subject_definition="document"` constant in the
Python consumer.

**Acceptance evidence.**

- The five existing native vector cases and the new cases pass on the deployed head, with the
  input taken from the record. The new `subject_definition` case is the one a consumer-side
  constant cannot pass: its record carries a value other than `document`.
- The native `equal-json-number` case sends `1.2500` and obtains the base vector's key. An
  implementation that normalizes the number before sending cannot show this; the test asserts the
  sent text contains the authored spelling.
- Removing any one field from the record makes both consumers fail, because neither supplies it.
  This is established by reading the two consumers, which contain no input literal.
- A framing change made the same way in Python and in SQL (a different domain tag, a different
  nesting of the context) fails the literal in both consumers. This is the property the storage
  test that compares the two implementations with each other
  (`tests/semantic/test_data_operation_storage.py:2272–2299`) cannot have.
- Targeted run: `uv run ci test -- tests/semantic/test_data_operation_identity.py tests/semantic/test_data_operation_identity_native.py`.

**Neighbouring reads that belong elsewhere.** The native consumer calls installed functions by
name on the head, so the move of those functions into a generated program does not touch it. The
third test in the native module still installs `sql/data_operation_identity.sql` by path
(`:57–59`); that read belongs to TDM-16. The fourth test already takes `data.ddo_json_meaning`
from the generated program through `routine_declaration` (`:118–124`), the route TDM-16 extends,
and a native vector test that needs a temporary copy of a routine uses the same helper.

## TDM-05 — Generated-program tests assert meaning; circular sites corrected

**Needs.** TDM-02.

**Delivered by the conversion.** None of the sites below was corrected, and none was deleted. The
conversion rewrote one spelling assertion with a fresh spelling and added another (the last two
rows of the table), and it moved the validity functions into a generated program, which the
reference cases do not depend on because they call the installed function by name. The DuckDB
relational modules were converted before the authoring baseline and are unchanged since.

**Implementation vision.** Each site below is judged by the rule and given the expectation the
rule calls for. The package owns the choice, per site, between structure through pglast and
behaviour on PostgreSQL; behaviour is preferred where the meaning is what a statement does.

| Site | What the assertion is meant to establish | Replacement |
|---|---|---|
| `test_pdf_source_search_projection.py:36` (`CAST('english' AS REGCONFIG)`) | The stored search vector is built with the English configuration | Behaviour: in the rollback class, create the table from the generated DDL, insert text containing "running" and query it with the production query expression for the term "run" (the one asserted at `:124`); a match is expected. The counter-case builds the same table with the generated column's configuration replaced by `simple` and expects no match |
| `:40` (`USING gin (search_vector)`) | The search vector has a GIN index | Structure: the parsed `CREATE INDEX` names access method `gin` over that column |
| `:124` (`CAST('simple' AS REGCONFIG)`) | The query side uses the configuration the wire contract declares | Structure: the parsed call of `websearch_to_tsquery` casts the constant `simple` to `regconfig`. The wire constant asserted at `:122` is the declaration; this is a correspondence |
| `test_companion_export.py:398` | The export transaction is repeatable-read and writable | Structure: the recorded statement parses to a transaction-characteristics statement with those two options |
| `test_pdf_shared_stream_data_steps.py:55` | The step locks the retired relation before folding it | Structure if the lock is a top-level statement (a parsed lock statement naming that relation). If it sits in a PL/pgSQL body, behaviour is preferred: run the step in the rollback class and observe the lock on that relation in `pg_locks` before the transaction ends |
| `test_target_installation.py:276` | The guard selects the execution-model artifact kind | Behaviour: the installed guard refuses a release that has such an artifact and accepts one that does not, with the message asserted at `:277` |
| `test_pdf_shared_stream_data_steps.py:98` and `:59–60` | The step retires exactly the two predecessor part relations | An authored tuple of the two relation names in the test, compared with both production values |
| `test_target_installation.py:294–295` (`float8send(CAST(… AS DOUBLE PRECISION))`, `ordinal DOUBLE PRECISION`) | A changed physical type of the column reaches both the equality comparison and the published reader | Structure: the compiled equality parses to a call of `float8send` over a cast of that column to `float8`, and the reader's parsed column definition has type `float8`. The test's own counter-case, the unaltered `bigint` column, yields neither |
| `test_native_program_table_outputs.py:35` (`"position" bigint`) | A table-returning program declares an output column whose name is a reserved word, with its type | Structure: the parsed function's table-output parameter is named `position` with type `int8`. The test already runs the program on PostgreSQL afterwards, which is the behaviour half |

Three further sites carry an expectation produced by the code under test.

*Lowering identity* (`test_pdf_producer_certification.py:135–146`). The identity equals the digest
of the retained contract by construction, so the equality asserts nothing. The claim worth testing
is a correspondence: the identity is issued only when the captured sources match the contract. The
test presents a context whose domain returns altered bytes for one declared input and expects the
refusal "captured PDF lowering source differs from its contract"; it presents a context whose
retained contract differs from the current one and expects "PDF lowering contract differs from the
captured execution basis" (`pdf_lowering.py:303, 309`). The membership assertions at `:140–146`,
which name inputs by hand, stay. TDM-13's oracle-skip table builds on these two tests: it adds the
enumerated form, one altered-source case per input the contract declares, and the "other lowering"
row of its table.

*Set-wise validity* (`ops.ddo_valid_closure` and `ops.ddo_node_valid`, generated in
`src/corpus_structure/semantic/data_validity_native.py`). The closure needs a reference that does
not pass through itself. None of the reference graphs below exists at `12f57dc4d`; three
conversion tests replace `ops.ddo_node_valid` with a trivial function as a fixture stub
(`tests/semantic/test_record_policy_native_predicate.py:108`,
`test_pdf_validation_read_native.py:103`, `test_source_capture_native.py:53`), which is setup and
no reference. The test authors small support graphs and writes the expected `(kind, id,
valid)` rows by hand: several distinct seeds that share a descendant; a valid and an invalid seed
together; a two-node cycle; a population superseded by another. One property is asserted across
them: a node's validity is the same whether it is seeded alone or among other seeds. The existing
duplicate-seed and cycle test stays. The reference cases stay independent of whichever
encoding production keeps for support closures and read identities (DA-071, DA-076): they name
nodes and expected validity by hand and call only the installed function. The undeclared-member
case for validity *families* is not
written here; it fails today and is gated on
[DA-070](../../design_review/audit/semantic-model-and-authority.md#da-070) (see
`reuse-and-refusal-evidence.md`).

*Search selection digest* (`test_source_search.py:141–185`). The test rebuilds the expected digest
by running the production projection over the published sections, so it follows any change to that
projection. The claim is a correspondence: the cursor's selection binds the request, the cut and
the candidate set. The test already holds half of the right evidence: a cursor issued for one
request text is refused with `InvalidContinuation` when replayed with another (`:213–217`). The
replacement keeps that refusal, removes the recomputation loop and the equality on `selection` at
`:222–227`, and adds the missing perturbations: two requests that differ only in scope, and the
same request before and after the candidate set changes, each yield a different selection value
and each refuses the other's cursor. The cursor's key and score fields keep their literal
assertions. A literal vector with authored canonical bytes, in the style of TDM-04, needs the
digest as a pure production function of the three parts. No such function was found in
`src/corpus_structure/semantic/pdf_source_search.py` at `12f57dc4d`, so the framing of this
digest remains without an independent literal; that limit is recorded, and the production
observation is a row of the coordinator's
[handover table](../test-domain-model-and-execution_2026-11-17.md#handovers). If production adds the function, the vector is
added. This site is the part of DTA-033 that TDM-05 owns.

*Expected rows of the DuckDB relational modules: a confirmation.* The relational modules are the
rich evaluator (`src/corpus_structure/semantic/rich_relations.py` with `analytical_kernels.py`),
the companion export (`src/corpus_structure/serve/companion_export.py`), the PDF derived analysis
(`src/corpus_structure/ingest/pdf_stream_reconciliation.py` and `pdf_candidate_geometry.py`) and
`src/corpus_structure/semantic/artifact_identity.py`. They existed at the authoring baseline and
have not changed since. The re-baseline read a sample of their tests and found none that computes
its expected rows by running the relation or holds rows copied from its output:

| Tests | What was read | Finding |
|---|---|---|
| `tests/semantic/test_rich_relations.py` (four tests) | In full | Small hand-authored Arrow tables with literal expected rows, covering nulls kept distinct, duplicates, empty inputs and the order of supports and evidence. Conforms |
| `tests/semantic/test_rich_rule_evaluation.py` | Lines 148 to 330 of 945 | Literal statuses, rule names and severities over authored source values; a few expectations are taken from the result itself (a selected set compared with the decision's own occurrence). Mostly authored |
| `tests/semantic/test_companion_export.py` | The inventory, comparison and difference tests | Two-row authored inputs with literal distributions, endpoint tuples and removed-row counts. Conforms; it has no null or empty-input case |
| `tests/ingest/test_pdf_candidate_source.py:143`, root `tests/test_pdf_candidate_geometry.py` | In full | Hand-authored boxes and literal result lists; one case compares the range join with a simpler in-test oracle over a six-by-six grid of points. Conforms |
| `tests/semantic/test_pdf_stream_reconciliation.py` | Skimmed | Byte-preservation tests with literal tuples; they hold no relational expected rows |
| `tests/semantic/test_artifact_identity.py` and the rest of `test_rich_rule_evaluation.py` | Not read | Open |

The item is therefore a confirmation at entry, not a rewrite. This package reads the tests the
sample did not cover and records each module as conforming, or, where a test is found to take its
expected rows from the relation, replaces them with rows authored by hand for small inputs chosen
to discriminate (duplicate rows, nulls, an empty input, an input whose ordering matters), asserted
on the evaluator's public result. The expectations in `test_rich_rule_evaluation.py` that are
taken from the result are read first. Adding the null and empty-input cases the companion-export
tests lack is permitted where the reading shows a claim without a discriminating case; it is not
required.

**Complete consumer scope.** The nine rows of the table (six files); the lowering-identity test;
the closure reference cases, added to the module that holds the existing closure test; the search
selection assertions; the confirmation over the relational modules' tests, with replacement only
where it finds a circular expectation. A second `REGCONFIG` occurrence in
`tests/semantic/test_contextual_retrieval_numerics.py:131` is the test's own control SQL and is not
in scope. Two kinds of assertion on generated text were considered and are not in scope: the
checks that a template sentinel such as `__DDO_READ_BOUNDARY_PROGRAMS__` is absent from a rendered
program, which assert substitution and not spelling; and assertions on the order of two routines
in a generated body by text position (`body.index(a) < body.index(b)`, five files, one of them
new: `tests/semantic/test_data_read_boundary_native.py:259`), which the coordinator is asked to
place.

**Superseded machinery removed.** The substring assertions on rendered text that the table names; the equality
with `RETIRED_PARTS` as the only expectation; the equality of the lowering identity with its own
artifact digest; the recomputation loop in the search test; any expected rows the confirmation
finds computed by, or copied from, a relation under test.

**Failure behaviour.** A replacement that cannot be made to pass is information. If the English
configuration behaviour check fails, the generated column is not what the spelling test claimed.
The package reports such a result to the coordinator as a product finding and does not weaken the
assertion.

**Acceptance evidence.**

- *A renderer change that keeps meaning passes.* For each structural replacement, the assertion is
  shown to hold for two spellings of the same statement written by hand in the test's own
  parametrization (for example `CAST('simple' AS regconfig)` and `'simple'::regconfig`). The old
  substring assertion would fail one of them.
- *A meaning change fails.* For each replacement, the hand-written counter-case (the `simple`
  configuration where `english` is required; a B-tree index; a read-only transaction; a tuple with
  a third relation) fails the assertion.
- *The lowering refusals are reached.* Each of the two refusals is asserted by its message after a
  positive control that the unaltered context yields an identity.
- *The closure cases are independent.* Their expected rows are literals in the test; the scalar
  function is not called to produce them.
- *The relational expectations are independent.* The package's evidence lists every test module
  of the relational modules with the finding of its reading. In each test the confirmation
  rewrites, the expected rows are literals, and one hand-written wrong variant of the small
  input's expected rows (a dropped duplicate, a null treated as a value) fails the assertion. No
  expected row is produced by calling the relation.
- Targeted runs with `uv run ci test -- PATH` for the files touched.

**What validation of the conversion may still move.** A site that TDM-00's re-read finds deleted
since `12f57dc4d` is recorded as closed by removal. A further spelling literal on generated text
gets the same treatment as the rows above.

## Sequencing and shared surfaces

TDM-02 comes first and is small. TDM-03, TDM-04 and TDM-05 are independent of one another once the
rule is written, and can proceed in any order or together. They share no files except that TDM-03
and TDM-05 may both touch a PDF support consumer; neither changes the other's lines.

**TDM-03 and TDM-07.** Both edit `tests/semantic/current_pdf_source_support.py` and
`current_pdf_integration_support.py`. TDM-03 makes one composer; TDM-07, owned by
`preparation-identity.md`, makes a recipe location-free by moving the directory out of the recipe
into a binding. The coordinator orders TDM-03 before TDM-07, and the dependency is real: the
split of recipe from binding is made once, in one composer, instead of in two functions and their
thirteen-plus call patterns. TDM-03's composer keeps today's `directory` parameter and adds no
location handling of its own; TDM-07 replaces that parameter with a binding and changes what the
composer does with it. The integration composer's worker script, written into the directory
(`current_pdf_integration_support.py:86–89`), is a location-bound effect and is TDM-07's to move.
The extension helper needs no change for TDM-07: it derives a recipe from a recipe and carries
no location.

**TDM-03 and TDM-09.** The two packages no longer constrain each other. The consumers of the PDF
integration support build their scenario behind converter doubles that now certify through
production's shared emitter, so by reading they set up, and TDM-03 verifies them itself by the
recipe-identity migration check and by targeted runs. TDM-09 completes the converter seam in the
same support modules; neither package changes the other's lines.

## Open questions

| Question | Evidence that settles it | Work it constrains |
|---|---|---|
| Is `test-assessment.md` managed by the copier template? | Inspect the template at the commit in `.copier-answers.yml` | Whether the 1.3 text also goes upstream; does not block TDM-02 |
| Is the acquired statistics bundle byte-equal to each typed copy? | Compare release ids once at TDM-03 entry | Whether the bundle substitution changes any release id |
| Can the grading release be prepared from the pack bundle plus only the reading-resolution inputs, or does `prepare_release` need the full acquired dependencies? | Prepare it once at TDM-03 entry. Fallback: start from `acquire_packs` and add the inputs through the extension helper | The shape of the grading scenario |
| Which of the seven other support modules that both prepare a release and compile a model use them together with different inputs? | Read each at TDM-03 entry | TDM-03's pairing scope |
| Is the shared-stream `LOCK` a top-level statement or inside a PL/pgSQL body? | Read the generated step | Structure or behaviour for that row of TDM-05 |
| Do the relational modules' tests that the sample did not read (`test_artifact_identity.py`, most of `test_rich_rule_evaluation.py`) take any expected rows from the relation? | Read them at TDM-05 entry; none was found in the sample | Whether TDM-05's relational item replaces anything |
| In each of the four files that restate persist and admit, is one of the steps the test's claim? | Read each at TDM-03 entry | Which of them move onto `admit_kernel` |

The companion change to the standard needs no decision record of its own; the coordinator's
[rule-change section](../test-domain-model-and-execution_2026-11-17.md#rule-changes) records the operator's decision as its route.

**Production observations** this companion raised are rows of the coordinator's
[handover table](../test-domain-model-and-execution_2026-11-17.md#handovers): `LOWERING_FILES` as a hand-kept list, which the
conversion grew to about seventy entries (seventeen generator modules added, five `.sql` files
removed) and which nothing derives or checks; no public operation that reopens packaged
data-operation inputs; release admission not being one production operation; and the search
selection digest having no pure function.

## State

| Package | State |
|---|---|
| TDM-02 | Not started |
| TDM-03 | Not started |
| TDM-04 | Not started |
| TDM-05 | Not started |
