# Boundaries and composition

**Interface-checked by source inspection.** The page was read as a whole on 2026-11-17 at
source `fbd3f2a98` ([baseline and limits](README.md#baseline)). DA-079 and DA-080 were re-read
on 2026-11-18 at source `d78c98765` ([refresh](README.md#refresh-2026-11-18)), and DA-084 was
established there; the earlier-identity table keeps its 2026-11-17 date. Source
paths omit `python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`.

<a id="da-079"></a>

## DA-079 — The process execution host refuses a second concurrent run with an unclassified error

**Refresh, 2026-11-18, source `d78c98765`.** Stands unchanged. No commit in
`fbd3f2a98..d78c98765` touched `orchestrate/execution_host.py` or
`intervene/native_render_tools.py`. The lock is still taken without blocking
(`orchestrate/execution_host.py:90–92`), the tool wrapper still converts only `ValueError`,
`KeyError` and `OSError` (`intervene/native_render_tools.py:93`), and a search for a typed busy
refusal over `orchestrate`, `intervene` and `semantic/data_operation_service.py` found none.
Overlap is still inferred, not observed.

**FP-05, FP-07; DP-20; H21, H25.**

`ProcessExecutionHost.run` takes its run lock without blocking and raises
`RuntimeError("process execution host already has an active run")` when it is held
(`orchestrate/execution_host.py:90–92`). The MCP server installs one host for its lifetime
(`intervene/runtime_engines.py:16–31`). `render_source_region` reaches `host.run` through
`execute_native_intent` (`semantic/data_operation_service.py:237`), and its refusal wrapper
converts only `ValueError`, `KeyError` and `OSError` (`intervene/native_render_tools.py:93`).

**Consequence.** If two agent renders overlap, the second fails with a generic tool error. It
neither waits nor receives a typed refusal that says "busy, retry".

**Contrary evidence.** ADR-0125 deliberately allows one active run per host, and one run serves
all of its claims concurrently. Provider residency itself now waits on a condition rather than
refusing (`methods/native_host.py:842–863`), which corrects the earlier ready-execution
observation about non-blocking provider borrowing.

**Limit.** Overlap is likely, not observed: the installed MCP framework runs synchronous tools
in worker threads by default (installed source read 2026-11-17), and ADR-0125 itself
anticipates concurrent MCP calls sharing one budget and states that it trades away concurrent
entry-point execution. Concurrency at the transport level was not checked.

<a id="da-080"></a>

## DA-080 — Superseded machinery remains in the production tree, kept alive only by tests or by nothing

**Refresh, 2026-11-18, source `d78c98765`.** Partly corrected, and the footprint changed. Of
the fourteen unreferenced SQL files recorded on 2026-11-17, ten were deleted; four remain, and
two more lost their loaders, so six files (285 lines) now have no loader. The other three
groups are unchanged. The 2026-11-17 delta's remark about a stale `scientific_layout.sql`
dispatch key is withdrawn: the name is a label that selects a generated artifact
(`semantic/target_installation.py:230, 235–236`; `semantic/archive_projection_native.py:74`;
`semantic/native_products.py:179`), and nothing is stale. The conversion work added new items
with no consumer: a migration helper
module, two migration trees, analytical kernels with no production caller, and settings that
nothing reads. The finding stays open; the groups below are the current state.

**FP-01, FP-03; DP-01, DP-16; H27.** This is the production home for a cause that also shows
in the test account ([DTA-035](../test-audit/retirement-transfer.md#dta-035)).

Groups with no current production consumer:

- **Native SQL files.** `semantic/sql/` now holds 16 files (1,293 lines). Ten are loaded
  ([DA-084](#da-084)). Six are named by no loader in `src`, `tests` or `scripts`:
  `validation.sql` (104 lines), `exclusions.sql` (102), `data_operation_identity.sql` (34; its
  own header says it is deliberately unregistered), `source_record_graph.sql` (29),
  `selection.sql` (8) and `fact.sql` (8). Their last loaders were removed in `47dc7b873`,
  `29f569875` and `c98046a8d`. They still enter the model-change compilation fingerprint, which
  takes every `.sql` file (`schema/model_change.py:390–397`), and the SQL change explanation's
  directory walk (`schema/model_explanation.py:423–456`), so editing them invalidates previews
  and nothing else. The ten files deleted since 2026-11-17 are `characterization`,
  `current_operation_guards`, `definition_declaration`, `native_finalization`, `record_policy`,
  `record_references`, `source_anchor_coordinates`, `source_record_coordinates`,
  `source_record_report` and `split_decisions`.
- **Evaluation modules.** `evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`,
  `sampling.py`, `split_decisions.py`, `split.py` and `sets.py` are all present and have no
  production importer; `split.py` is imported only by `split_decisions.py:16`.
- **Rendition keying and translation.** `core/keys.py`, `core/translations.py` and
  `core/candidates.py` are present. `KeyContext` is referenced in `src` only by a docstring
  (`core/candidates.py:9`). On 2026-11-17 the rendition-index branch of
  `semantic/proposals.py:286–300` was unreachable from its one caller, and six test files and
  about 3,300 test lines exercised this half; neither was re-read.
- **Earlier pack loader.** `schema/pack.py` and `schema/lookup.py` have no production importer
  outside `schema/` other than a path constant (`orchestrate/project.py:149`;
  `orchestrate/source_operation.py:41, 111`); see
  [DA-072](semantic-model-and-authority.md#da-072).
- **A migration helper.** `semantic/published_address_migration.py` has no importer in `src`
  or in the migration trees; only its own test imports it.
- **Two migration trees.** The deployed tree is `target_alembic/`
  (`semantic/migrations.py:14`). `semantic_alembic/` (285 revisions, about 1.8 GB on disk by
  the generator lane's count) is named by no path in `src`, `tests` or `scripts`; only the
  version-table name `semantic_alembic_version` survives (`migrations.py:15`). The three-revision
  `alembic/` tree also has no loader and was not examined further.
- **Analytical kernels with no production caller.** `disagreements` and `fuse`
  (`semantic/analytical_kernels.py:150, 170`; `semantic/rich_relations.py:112, 115`) are called
  only from a test, and `FileRelation` (`capture_storage.py:78`) has no caller in `src`. The
  rich consolidation computes value disagreement in Python instead
  (`semantic/rich_consolidation.py:336–372`).
- **Settings that nothing reads.** `AnalyticsSettings` declares `capture_mode`, `batch_size`,
  `resident_limit_bytes`, `threads`, `memory_limit` and `scratch_path`
  (`settings.py:129–139`); the only fields read anywhere in `src` are `adbc_driver_path` and
  `batch_size_hint_bytes` (`serve/companion_export.py:139, 178`;
  `serve/database_description.py:236`). The DuckDB sites set `threads=1` and `"2GB"` as
  literals (`semantic/rich_consolidation.py:409–410`; `ingest/pdf_candidate_geometry.py:87`;
  `ingest/pdf_stream_reconciliation.py:301`).

**Consequence.** These read as current authority. Passing tests over them look like assurance
for paths that do not run, they are paid for in every run, and they stand in the way of the
removal that the project's design-stage rule asks for. The unread settings give an operator a
control that has no effect.

**Contrary evidence.** `target_alembic/` is a frozen tree with a consumer and is a legitimate
exception under ADR-0131. The repository rule that plans and evidence are never deleted does
not name migration trees, and `semantic_alembic/` might be wanted for historical recovery;
that is the operator's decision, and only its lack of a code consumer is established here.

**Limits.** "No consumer" is by search over the named trees; a loader that builds file names
dynamically was searched for and not found, and dynamic imports were not excluded. Parts of
`core/keys.py` and `core/locators.py` are live. Whether the rendition half is meant to return
(archive reading, prompts) is an owner question.

<a id="da-084"></a>

## DA-084 — Hand-written PostgreSQL that ADR-0131 schedules for conversion is still deployed, is not inventoried by the plan, and holds the family and role lists; model changes do not reach it

**FP-02, FP-03; A2; DP-01, DP-16; H27.** Established in the refresh of 2026-11-18 at source
`d78c98765`. **Interface-checked by source inspection, 2026-11-18.**

**The conversion is not complete, and no owner says it is.**
[ADR-0131](../../adr/0131-model-owned-postgresql-programs.md) replaces hand-written PostgreSQL
with programs generated from the model. It says "Convert remaining maintained owners forward
and remove their superseded SQL sources and fallbacks" (`:40–41`) and "This decision records
the target while conversion is open" (`:51`). The
[DDO plan](../../plans/declared-data-operations_2026-11-12.md) at `d78c98765` records the
remainder as open work: its status line says "residual SQL authoring" stays open (`:3`); it
lists what the remaining authoring conversion covers, including "native admission and
privileges, scientific routines and administrative paths" (`:100–103`); and it says "The
authoring conversion remains open", naming "general native admission, scientific scoring and
native fixture provisioning" among the outstanding owners (`:191–195`). The residue described
here is therefore scheduled work. The plan names it by category only.

**What this finding adds** is the inventory the plan does not have, and two facts about it.

ADR-0131 keeps three kinds of hand-written SQL permanently: frozen migrations, independent
control SQL and explicitly submitted read-only SQL (`:41–42`). The typed route is real and
principled where it is used: 57 of the 72 `*_native.py` modules import the program compiler,
statements never pass through text inside a program, and raw SQL text is refused there
(`semantic/native_program.py:126–131`). Beside it, hand-written PostgreSQL that belongs to none
of the three permanent kinds reaches deployment through three routes:

- **PL/pgSQL written as Python strings.** Eleven `*_native.py` modules hold hand-written
  PL/pgSQL and import nothing from the program compiler: `rich_admission_native.py` (474
  lines of SQL text), `structural_admission_native.py` (444), `contextual_admission_native.py`
  (229), `pdf_spool_native.py` (136), `contextual_witness_native.py` (132),
  `definition_admission_native.py` (130), `archive_native.py` (99),
  `artifact_admission_native.py`, `contextual_linguistics_native.py`,
  `contextual_definition_native.py` and `companion_projection_native.py`. Together they hold
  about 1,830 lines; with the hand-written SQL in `pdf_publication_native.py` (46 lines,
  `:394–564`), `data_operation_cpu_basis.py` (166, `:463–543`) and
  `execution_evidence_leaf.py` (49) the total is about 2,090. None of the eleven has a commit
  in `fbd3f2a98..d78c98765`. They are deployed through the native capture
  (`semantic/data_operation_storage.py:249–352`) and through
  `semantic/pdf_staging_native.py:168–170`. Further hand-written statements are the task guard
  template (`semantic/target_installation.py:38–54`) and trigger strings
  (`target_installation.py:330–386`; `data_operation_storage.py:1929–1931, 1954–1956`).
- **Loaded `.sql` files.** Ten files, 1,008 lines and 87,447 bytes: `admission.sql` (186 lines,
  the enforcing function `data.require_execution_release`),
  `data_operation_source_admission.sql`, `data_operation_visual_read.sql`, `closure.sql`,
  `identity.sql`, `source_originals.sql`, `source_record_recognition.sql`,
  `contextual_neighborhood.sql`, `data_operation_task_checks.sql` and `pdf_descriptor.sql`.
  Loaders: `semantic/target_installation.py:28–34, 93, 104–107`;
  `semantic/native_products.py:186, 390`; `semantic/data_operation_source_native.py:14, 43–72`;
  `semantic/data_operation_visual_read.py:16, 100–111`;
  `semantic/original_document_contracts.py:19, 126–214`;
  `semantic/data_operation_storage.py:498`; `semantic/data_operation_protocol.py:125–129`.
- **String templates that splice into hand-written bodies.** Eleven splice sites in seven
  modules, nineteen text replacements counting chained calls:
  `semantic/native_admission.py:419, 428, 439, 444` (typed fragments spliced into
  `admission.sql`); `semantic/data_operation_protocol.py:129, 156` (task states into the guard
  trigger); `semantic/alembic_privileges.py:589`;
  `semantic/data_operation_source_native.py:72`;
  `semantic/contextual_linguistics_native.py:49–51` (two);
  `semantic/pdf_publication_native.py:562–564` (two); and
  `semantic/structural_admission_native.py:482–494` (seven). Two further patches act on
  generated text and belong to [DA-081](semantic-model-and-authority.md#da-081).

*How the figures were counted.* The line figures are the independent challenger's recount:
lines spanned by string constants or formatted strings that contain at least two SQL keywords,
found by a syntax-tree walk over each module. The count depends on the method (the generator
lane's survey gave about 1,940 lines in thirteen modules), so the range of about 1,800 to
2,100 lines is the supported statement. The eleven modules, the ten loaders and the splice
sites were checked in the snapshot.

**Consequence.** Two facts follow from the inventory.

- *Model changes do not reach this residue.* ADR-0131 states its benefit as "A model field or
  type change propagates to its generated SQL and calls, or compilation refuses" (`:46`). That
  does not yet hold for these bodies: a rename or type change in the model does not propagate
  to them and compilation does not refuse. PostgreSQL authoring catches only what binds when
  the routine is installed, and PL/pgSQL defers most name resolution to first execution.
- *This is where the hand lists now live.* The contextual, definition, rich and artifact
  admission modules hold the operation-id lists of
  [DA-070](semantic-model-and-authority.md#da-070), and `admission.sql` and the privilege
  templates hold role names of [DA-074](native-integrity.md#da-074). Converting these bodies to
  typed programs before family membership and roles are declared would transcribe the lists
  again, as happened for the two lists already converted. The order of the remaining work
  therefore matters, and the plan's category list does not show it.

**Contrary evidence.** The work is scheduled: ADR-0131 and the DDO plan both record it as
open, so this is remaining conversion, not a defect outside the decision. These bodies are
installed, normalized by the server and checked with `plpgsql_check` on the same custody path
as generated programs, in a rollback-only scope (`semantic/native_objects.py:950–1121`). Each
template checks that its tokens are present and fully resolved. Some bodies manipulate only
JSON payloads and reference no relation or column. Hand-written SQL of the three permanent
kinds was found and is not part of this finding: the frozen `target_alembic/` tree; the
independent catalog controls (`schema/model_deployment.py:921, 963`;
`semantic/execution_admission.py:102–140`; the catalog introspection in `native_authoring.py`
and `alembic_indexes.py`), whose independence from the generators is their purpose; and
submitted read-only SQL, which is admitted through a parsed allowlist and bound by PostgreSQL
in a read-only transaction (`semantic/authored_sql.py:120–219, 274–279`), a sound design.

**Footprint and uncertainty.** Established for the three routes, their loaders and the
plan's and ADR's open-work statements. Which of the hand-written bodies reference relations or
columns, and so carry the propagation risk, and which only handle JSON, was not determined.
Whether this identity should remain in the audit or pass to the plan's findings table as
scheduled work is the coordinator's decision; it is kept here because the inventory and the
ordering fact are not in the plan. Adjacent and outside this finding: five modules write
SQLite SQL text for local stores and exports (`serve/selected_source.py`,
`semantic/pdf_payload_validation.py`, `semantic/data_operation_read_index.py`,
`semantic/pdf_certification.py`, `serve/demand_export.py`; about 56 execute sites by the
generator lane's survey). ADR-0131 is about PostgreSQL and does not own them; they are
recorded as a fact for the review that follows.

## Prior identities on this page

<a id="da-018"></a>
<a id="da-019"></a>
<a id="da-020"></a>
<a id="da-045"></a>
<a id="da-047"></a>
<a id="da-052"></a>
<a id="da-059"></a>
<a id="da-060"></a>

Earlier text is in Git at `fbd3f2a98`.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-018 | Not re-examined | Historical correction |
| DA-019 | Not re-examined | Test-sweep leasing is covered by the [test account](../test-audit/README.md) |
| DA-020 | Not re-examined | Cited `domain_operations.py` and `orchestrate/commands.py` are gone |
| DA-045 | Not re-examined | — |
| DA-047 | No longer applicable | `orchestrate/commands.py` is gone |
| DA-052 | Not re-examined | — |
| DA-059 | Not re-examined | Last evidence 2026-11-10 |
| DA-060 | Not re-examined | Last evidence 2026-11-10 |
