# Boundaries and composition

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
Every finding on this page was re-read at that source and carries an "Update, 2026-11-18"
paragraph that states its status. Source paths omit
`python/corpus-structure/src/corpus_structure/`; `docs/`, `scripts/` and `STATUS.md` are at the
repository root. "No caller" and "no consumer" rest on searches over `src`, `tests` and
`scripts`; dynamic imports were not excluded.

<a id="da-079"></a>

## DA-079 — The process execution host refuses a second concurrent run with an unclassified error

**Update, 2026-11-18, source `5139eaba3`.** Stands unchanged. No commit in
`d78c98765..5139eaba3` touched `orchestrate/execution_host.py`, `intervene/` or
`semantic/data_operation_service.py`. The lock is still taken without blocking
(`orchestrate/execution_host.py:91–92`, and likewise on `close`, `:457–458`), the tool wrapper
still converts only `ValueError`, `KeyError` and `OSError`
(`intervene/native_render_tools.py:93`), and a search for a typed busy refusal finds only the
error message. Overlap is still inferred, not observed.

**FP-05, FP-07; DP-20; H21, H25.**

`ProcessExecutionHost.run` takes its run lock without blocking and raises
`RuntimeError("process execution host already has an active run")` when it is held
(`orchestrate/execution_host.py:91–92`). The MCP server installs one host for its lifetime
(`intervene/runtime_engines.py:16–31`). `render_source_region` reaches `host.run` through
`execute_native_intent`, and its refusal wrapper converts only `ValueError`, `KeyError` and
`OSError` (`intervene/native_render_tools.py:93`).

**Consequence.** If two agent renders overlap, the second fails with a generic tool error. It
neither waits nor receives a typed refusal that says "busy, retry". This is one current
instance of the wider cause recorded as [DA-013](structure-and-invariants.md#da-013): refusals
raised as plain errors that the boundary cannot classify.

**Contrary evidence.** ADR-0125 deliberately allows one active run per host, and one run serves
all of its claims concurrently. Provider residency itself waits on a condition instead of
refusing (`methods/native_host.py`, as read on 2026-11-17).

**Limit.** Overlap is likely, not observed: the installed MCP framework runs synchronous tools
in worker threads by default (installed source read 2026-11-17), and ADR-0125 itself
anticipates concurrent MCP calls sharing one budget. Concurrency at the transport level was
not checked.

<a id="da-080"></a>

## DA-080 — Superseded machinery remains in the production tree, kept alive only by tests or by nothing

**Update, 2026-11-18, source `5139eaba3`.** Partly corrected, with a changed footprint. Three
groups were removed in `d78c98765..5139eaba3`, six groups stand, and six items were added,
three of them found by re-reading an earlier identity and one by the independent challenge of
this update.

| Group | State at `5139eaba3` | Evidence |
|---|---|---|
| Six SQL files with no loader | **Corrected.** Deleted with the whole `semantic/sql/` directory | `c25cada3f` (see the note under [DA-084](#da-084) about that commit) |
| `semantic/published_address_migration.py` | **Corrected.** Deleted with its mechanism tests | `54a232131` |
| Scalar encoder kernels (not listed before) | **Corrected.** `contextual_encoder.py` deleted (151 lines) | `93b7141ec` |
| Evaluation modules | Stands | `evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`, `sampling.py`, `split_decisions.py`, `split.py` and `sets.py` are present with no production importer; `split.py` is imported only by `split_decisions.py` |
| Rendition keying and translation | Stands | `core/keys.py`, `core/translations.py` and `core/candidates.py` are present; `KeyContext` appears only in `candidates.py` and `keys.py`. The legacy `LocatorIndex` branch of `semantic/proposals.py:21, 290, 325–329` sits behind an `index` parameter that no caller passes (`:614`); this is what remains of [DA-014](structure-and-invariants.md#da-014) and [DA-025](execution-fit.md#da-025) |
| Earlier pack loader | Stands | `schema/pack.py` and `schema/lookup.py`; outside `schema/` only a path constant refers to them (`orchestrate/project.py`, `orchestrate/source_operation.py`); see [DA-072](semantic-model-and-authority.md#da-072) |
| Analytical kernels with no production caller | Stands | `disagreements` and `fuse` (`semantic/analytical_kernels.py:150, 170`; `semantic/rich_relations.py:112, 115`); `FileRelation` (`capture_storage.py:78`) has no caller. Files unchanged in the range |
| Settings that nothing reads | Stands; its home is now [DA-020](#da-020) | `settings.py` is unchanged in the range |
| Two migration trees with no consumer | Stands | Below |
| `pdf_shape_guard_sql` | **New item** | A hand-written PL/pgSQL fragment (`semantic/pdf_contracts.py:578–588`) with no caller in `src`, `tests` or `scripts` at either commit |
| The SQL change explanation of the model preview | **New consequence** | Below |
| Release-side authored-SQL machinery with no supplier | **New item**, from the re-read of [DA-047](#da-047) | Below |
| Two LLM producer modules with no production importer | **New item**, from the re-read of DA-047 and [DA-052](#da-052) | Below |
| A native fitting path with no caller | **New item**, found by the independent challenge | Below |
| A Unicode parity check with no caller | **New item**, from the re-read of [DA-009](semantic-model-and-authority.md#da-009) | `require_unicode_identity_release` (`semantic/unicode_identity.py:233–246`) has had no production caller since `bcff594c2` |

**FP-01, FP-03, FP-05; DP-01, DP-16; H27; CI-04.** This is the production home for a cause
that also shows in the test account ([DTA-035](../test-audit/retirement-transfer.md#dta-035)).

**The model preview's SQL change explanation still walks the removed directory.**
`capture_sql_changes` builds its roots from `semantic/sql` and the named packs
(`schema/model_explanation.py:413–460`, the prefix at `:423`), and it runs on every
`model.preview` (`cli/model.py:1465–1468`). That directory no longer exists, and every
maintained SQL body is now generated. The explanation therefore reports deletions against a
baseline that still had the directory, and otherwise nothing: a change to generated SQL is
never explained, and an empty explanation reads as "no SQL change". This presents "not
examined" as "absent" (FP-05; CI-04). The preview already holds both snapshots of the generated
SQL, which is what a reader would expect the explanation to compare (inferred). The fingerprint
suffix set still includes `.sql` (`schema/model_change.py:390–397`), which is harmless now.

**Release-side authored-SQL machinery has no supplier.** Archival, admission and retention
consume release dependencies named `authored-sql/…` (`semantic/authored_sql.py:299–369`;
`semantic/native_admission_release.py:461–500`; `cli/model.py:361–385`). Nothing supplies
them: pack acquisition reads no such files (`semantic/regeneration.py:60–130`), and a search of
`src`, `scripts` and `domains` finds the prefix only in its consumers. So each admission call
runs a generated check over an input population that is always empty
([DA-033](execution-fit.md#da-033) lists it among the per-call work). The submitted-SQL
analyser `admit_sql` is separate and live: the database-description endpoint uses it to analyse
a submitted query without executing it (`serve/database_description.py:165–200`).

**Two LLM producer modules have no production importer.** `methods/llm/producer.py`
(`SUPPORTED_PRODUCERS`, `producer_binding`) is imported only by a test
(`tests/ingest/test_managed_recognition.py:11`), which is the case this finding's title
describes. `methods/llm/agent_opus.py` (`AgentOpusConfig`, whose docstring says it is for
historical interpretation only) is imported by nothing in `src` or `tests`.
`domains/*/methods.yaml` still hold an `agent.opus` configuration section; whether anything
reads that section was not checked.

**A native fitting path has no caller and calls functions the deployed tree does not define.**
`read_native_frame`, `fit_native_operation_event` and `read_native_fit`
(`evaluate/operation_fitting.py:530–620`) have no caller in `src`, `tests` or `scripts`
(search). They call `eval.operation_event_fit_frame`, `eval.record_operation_event_fit`,
`eval.read_operation_event_fit` and `ops.read_operation_event_parameters` through `text(...)`
with bound parameters. Those functions are defined only in `semantic_alembic/` revisions and
appear nowhere in the deployed `target_alembic/` tree (search). The module is nevertheless
inside a hand-listed implementation boundary (`_PATHS`,
`evaluate/declared_operation_events.py:46–57`), so the dead code is part of an identity. A
draft of this update listed these calls as a residue of the SQL conversion under
[DA-084](#da-084); the challenge showed they are superseded machinery, and they were moved
here. Whether the `eval` functions still exist in any deployed database was not examined.

**Two migration trees have no consumer, and the deployed tree grows by a full snapshot per
revision.** The deployed tree is `target_alembic/` (`semantic/migrations.py:14`).
`semantic_alembic/` (1,013 files, about 1.8 GB on disk) and the three-revision `alembic/` tree
are named by no script location or path in `src`, `tests` or `scripts`; only the version-table
name `semantic_alembic_version` survives (`migrations.py:15`). Their file counts are unchanged
in the range. A separate fact, for the lifecycle owner: `target_alembic/` grew from 31 to 47
revisions (N14 to N29) and from about 353 MB to about 550 MB on disk. Each new revision
freezes the full desired catalog state again as a `*_native.json` file of 8.5 to 10.6 MB (N29
holds 585 objects: 449 functions, 132 triggers and 4 views), beside an upgrade script of 2.2 to
4.4 MB and a generated admission file of about 0.6 MB. Revisions N14 to N29 add 206 MB of
catalog snapshots as ordinary Git blobs: `.gitattributes` routes only evidence through LFS, and
the filter attribute of these files is unspecified (the generator lane's figures; nothing was
measured here beyond file sizes).

**Consequence.** These read as current authority. Passing tests over them look like assurance
for paths that do not run, they are carried in every run, and they stand in the way of the
removal that the project's design-stage rule asks for. The empty SQL explanation is the one
item that can mislead an operator about a change being made now.

**Contrary evidence.** `target_alembic/` is a frozen tree with a consumer and is a legitimate
exception under ADR-0131; exact frozen bytes with digests and catalog snapshots are a sound
design, and the size is its cost, not a defect. The repository rule that plans and evidence are
never deleted does not name migration trees, and `semantic_alembic/` might be wanted for
historical recovery; that is the operator's decision, and only its lack of a code consumer is
established here.

**Limits.** "No consumer" is by search over the named trees; a loader that builds file names
dynamically was searched for and not found. Parts of `core/keys.py` and `core/locators.py` are
live. Whether the rendition half is meant to return is an owner question. Whether the frozen
`semantic_alembic` chain is still deployed anywhere was not checked.

<a id="da-084"></a>

## DA-084 — The conversion of hand-written PostgreSQL under ADR-0131: statement text is almost all converted, and the hand-held facts moved into Python lists

**Update, 2026-11-18, source `5139eaba3`.** Partly corrected, and its consequence moved. The
finding was recounted from scratch.

*Two counting methods, which agree.* Both walk the syntax tree of every production module,
exclude docstrings, and measure a matching string constant (or the literal parts of a
formatted string) by the lines it spans. The generator lane's method counts a string that
holds at least two distinct uppercase SQL or PL/pgSQL keywords from a fixed set. The
independent challenge used a different test, a case-insensitive pattern for statement shapes
(`select … from`, `insert into`, `create function`, `grant`, `do $` and others). Neither
counts `.sql` files, which are counted separately by listing the tree at each commit.

*The counts.*

| Population | `d78c98765` | `5139eaba3` |
|---|---|---|
| Hand-written SQL inside Python modules, lane method | 2,423 lines | 183 lines |
| The same, challenge method | 2,431 lines in 38 files | 182 lines in 17 files |
| `.sql` files under `src/` | 16 files, 1,293 lines (ten loaded, 1,008 lines) | none |
| Together | about 3,700 lines | about 180 lines |

The fourteen modules this finding named hold **0 lines** by both methods, from about 2,100.
String splices into hand-written bodies fell from eleven to none. 73 of the 78 `*_native.py`
modules import the program compiler (57 of 73 before), and the five that do not hold no SQL
text. Correcting commits: `9364a5b88` (`admission.sql`), `260d81f28` (source admission),
`67ce99670` (visual read), `32ec30618` (contextual neighborhood and task checks, and the task
guard as a typed program), `c25cada3f` (the last eleven files) and the generation commits of
native revisions N17 to N25.

*A note on one of those commits.* The last eleven files of `semantic/sql/`, among them the
loaded `closure.sql`, `identity.sql`, `source_originals.sql`, `source_record_recognition.sql`
and `pdf_descriptor.sql`, were removed in commit `c25cada3f`, whose message describes a
documentation change; the deletion was another session's staged work.

**FP-02, FP-03; A2; DP-01, DP-16; H27.**

[ADR-0131](../../adr/0131-model-owned-postgresql-programs.md) replaces hand-written PostgreSQL
with programs generated from the model. It keeps three kinds of hand-written SQL permanently:
frozen migrations, independent control SQL and explicitly submitted read-only SQL (`:41–42`).

**What remains, by category** (183 lines by the method above, classified by reading):

| Lines | Where | What it is | Category |
|---|---|---|---|
| 84 | `schema/model_deployment.py` (30), `semantic/alembic_indexes.py` (19), `semantic/unicode_identity.py` (16), `semantic/authored_sql.py` (15), `semantic/storage_target.py` (3), `core/db/extensions.py` (1) | Catalog and server observation, admission observation, a qualification probe, the submitted-SQL validator's own catalog reads | Permitted: independent control SQL. None of these files changed in the range |
| 59 | `serve/selected_source.py` (16), `semantic/pdf_payload_validation.py` (15), `semantic/data_operation_read_index.py` (10), `semantic/pdf_certification.py` (9), `serve/demand_export.py` (8), `semantic/pdf_publication.py` (1) | SQLite statements for local stores and spools; 58 execute sites, identical to `d78c98765` | Outside ADR-0131, which is about PostgreSQL. Maintained hand-written SQL, unchanged |
| 16 | `semantic/native_program.py:351–460` | Procedural framing written as formatted strings | Generated: the compiler's own renderer |
| 14 | `semantic/native_admission_principals.py:88–208`, `semantic/closure_native.py:102–136`, `semantic/native_admission_tables.py:200–203`, `semantic/alembic_privileges.py:349–354` | Privilege-name lists passed as values to `has_table_privilege` | Not statements; a false positive of the method. They do restate the privilege matrix in four modules ([DA-074](native-integrity.md#da-074)) |
| 4 | `semantic/native_admission.py:58, 64, 67, 70` | Literal text anchors that locate catalog checks inside frozen guards | Text handling on frozen bytes ([DA-081](semantic-model-and-authority.md#da-081)) |
| 2 | `semantic/target_installation.py:623–637` | See below | Hand-written PL/pgSQL |
| 4 | `semantic/pdf_contracts.py:578–588` | `pdf_shape_guard_sql` | Dead code ([DA-080](#da-080)) |

**The one real item of hand-written PostgreSQL** outside the permitted kinds is
`target_database_privileges_sql` (`semantic/target_installation.py:623–637`). It builds a `DO`
block by string concatenation that revokes and grants the TEMP privilege on the current
database, with quote escaping by `.replace("'", "''")`. The plan names it as remaining.

Other text entry points, counted over the syntax tree at both commits: `text(` calls fell from
29 to 17 (the rest are control SQL, submitted SQL, four calls in a fitting path with no caller
([DA-080](#da-080)) and one descriptor read at
`semantic/data_operation_storage.py:1135`); `exec_driver_sql` calls fell from 38 to 25, most of
which execute generated or frozen text; `literal_column(` appears at 37 sites in 16 files,
mostly local names, with three small SQL literals. That last form is the way past the
compiler's refusal of raw text (`semantic/native_program.py:128–129`); its uses are small and
identifier-shaped.

**The consequence moved.** The previous refresh recorded two consequences. One is now
corrected: a renamed or retyped relation or column reaches every converted body, because
`model.tables[...]` and `.c.<name>` fail at generation. The ADR's stated benefit (`:46`) holds
for relations and columns in these modules (established from construction; no rename was run).

The other consequence was that these bodies held the operation-family and role lists, and that
converting them before family membership and roles were declared would transcribe the lists
again. That prediction is now observed. The hand-held facts are Python lists and literals
inside generated modules: family membership and the early-return guards are the footprint of
[DA-070](semantic-model-and-authority.md#da-070), role and privilege sets are the footprint of
[DA-074](native-integrity.md#da-074), and state and tag literals are
[DA-086](semantic-model-and-authority.md#da-086). They are not part of this finding any more.
What stays here is the conversion's own residue: the one item above and the record of what
was removed.

**Contrary evidence: the plan's own account of what remains.** The
[PostgreSQL companion plan](../../plans/declared-data-operations/postgresql-realization-and-retirement.md)
narrates the conversion by stage and ends at N29 with "Remaining authoring includes the
fresh-root current-database TEMP grant framing and the typed replay and installation
boundaries already identified above" (`:463–464`). That matches the recount for the TEMP grant
and the frozen-guard text handling. By the plan's own account, then, the conversion of
statement text is done apart from named framing sites, and this finding agrees. ADR-0131 has
not changed since `d78c98765` and still says the conversion is open (`:40–41, 51`).

What that account omits: the SQLite statements (outside the ADR, but maintained hand-written
SQL); the dead `pdf_shape_guard_sql`; and, above all, the facts
that typed programs carry by hand and the early-return family guards. No owner document
records that last residue. Two other owner texts are now behind the source: the DDO
coordinator still carries two sentences dated 2026-11-17 that list broad remaining owners
(`docs/plans/declared-data-operations_2026-11-12.md:100–103, 191–195`) while its status line
no longer does, and `STATUS.md:7–9` says the last standalone SQL template was removed at N18.

Further contrary evidence: generated and remaining bodies share one custody path (generation,
server normalization, `plpgsql_check`); some literals are deliberate pins of an exact
implementation (the contextual guard refuses a definition whose factory differs,
`semantic/contextual_admission_native.py:222–236`).

**Footprint and uncertainty.** Established for the counts by the two stated methods, the one
remaining item and the plan's statements. All counts are lexical. Test-harness SQL
(`scripts/native_test_support.py` and siblings) belongs to the test account.

<a id="da-020"></a>

## DA-020 — Analytics resource settings are declared and read nowhere, and the DuckDB limits are literals

**Update, 2026-11-18, source `5139eaba3`.** Changed footprint: the original cause recurs at a
new site. The 2026-10 finding covered cluster coordinates, principal names and resource
settings that were repeated or unconsumed. The 2026-11-03 correction forwarded the settings
into an analysis scope, and that code was removed with `64455a0f1`. The principal-name part
has moved to [DA-074](native-integrity.md#da-074). This section is the home for unread
settings; [DA-080](#da-080) points here.

**FP-01, FP-03; DP-01.**

`AnalyticsSettings` declares `capture_mode`, `batch_size`, `resident_limit_bytes`, `threads`,
`memory_limit` and `scratch_path` (`settings.py:129–139`), described in its docstring as
execution resources. None of those six is read anywhere in `src` (search for
`analytics.<field>`: no hit). Only `adbc_driver_path` and `batch_size_hint_bytes` are read
(`serve/companion_export.py:139, 178`; `serve/database_description.py:236`). The DuckDB sites
set their own limits as literals: the rich-relation kernel takes `threads=1` and
`memory_limit="2GB"` (`semantic/rich_consolidation.py:405–412`), and the two ingest modules do
the same (`ingest/pdf_candidate_geometry.py:87`; `ingest/pdf_stream_reconciliation.py:301`,
files unchanged in the range).

**Consequence.** An operator who sets analytics threads or memory changes nothing. The limits
that do apply cannot be changed without editing code.

**Contrary evidence.** The literal limits are conservative and the same at each site. Whether
the settings are meant to return with a later consumer is an owner question.

## Prior identities on this page

<a id="da-018"></a>
<a id="da-019"></a>
<a id="da-045"></a>
<a id="da-047"></a>
<a id="da-052"></a>
<a id="da-059"></a>
<a id="da-060"></a>

Statuses were established on 2026-11-18 at `5139eaba3` by reading the code that replaced each
cited subject. Earlier text is in Git at `fbd3f2a98` and before.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-018 | Corrected, holds | Extension versions are pinned and reconciled (`core/db/extensions.py:3–17, 32–71`; `core/db/host_bootstrap.py:315–319`; a row in `docs/pins.md`). Read from source; nothing was provisioned |
| DA-019 | No longer applicable to this account | Test-database sweeping is owned by the [test account](../test-audit/README.md); not checked here |
| DA-020 | Changed footprint | [Section above](#da-020); principal names are DA-074 |
| DA-045 | Changed footprint | The legacy packages the finding named (`consolidate`, `validate`, `pool`, `orchestrate.phase0`) are gone. Upward imports of the same kind recur at new sites, all but one as lazy imports: `semantic` imports `orchestrate` (`semantic/data_operation_service.py:233–234`; `semantic/visual_requests.py:664`; `semantic/pdf_capture.py:195`; `semantic/pdf_transforms.py:804`); `methods` imports `cli` (`methods/characterization_resources.py:481–482, 759`); `core` imports `methods` and `semantic` (`core/text_structure.py:212, 223`; `core/db/host_bootstrap.py:20–26`, at module level). The half about contracts living in the earlier model is [DA-072](semantic-model-and-authority.md#da-072). The raw-connection `Reader` defect does not recur |
| DA-047 | Superseded by [DA-080](#da-080) | The cited views, tools and the empty `fuse` are gone. The same cause, a surface kept with no consumer, recurs at two sites (release-side authored SQL with no supplier; two producer modules with no production importer), which are recorded as footprint of DA-080 |
| DA-052 | No longer applicable | No Python source names `agent.opus` except `methods/llm/producer.py:10`, which has no production importer (one test imports it); external execution uses declared packet and result operations. The leftover modules are footprint of DA-080 |
| DA-059 | Corrected, holds | `OperationAccount` carries the acquired target, predecessor, reached revision, known effects and cleanup state, and records a failure with kind, code, message and reason (`cli/managed.py:63–96, 341–378, 429–442`) |
| DA-060 | Corrected, holds | Evidence promotion refuses unless custody is settled (`cli/operations.py:410–415`; `cli/managed.py:92–97`) |
