# Lane: generators, remaining SQL, DA-079/080/084 and the analytical delta (baseline `5139eaba3`)

Diagnostic audit contribution, read-only. Source facts come from the frozen snapshot `snap6/` at
`5139eaba3`. `src/…` paths are relative to `snap6/python/corpus-structure/`, with
`src/corpus_structure/` shortened to the module path (`semantic/…`, `schema/…`). Root paths
(`docs/…`, `scripts/…`, `STATUS.md`) are under `snap6/`. History comes from read-only
`git log/diff/show d78c98765..5139eaba3`.

**Coverage.**
- Read fully: `native_admission.py:17-130`, `data_operation_storage.py:48-200, 712-830`,
  `data_operation_source_native.py`, `target_installation.py:20-130, 600-640`,
  `semantic/metadata.py`, the N29 revision `.py`, ADR-0131.
- Read in part (relevant functions): structural `:1-170, 786-1000, 1161-1760`; contextual
  `:170-310, 555-580`; rich (grep, `:556-620, 940-955`); definition `:30-40, 380-420`;
  `native_admission_release.py:25-60, 340-410`; `native_admission_tables.py:20-35, 176-184`;
  `native_admission_principals.py:1-30`; `native_authoring.py:177-202, 271-350, 880-960`;
  `alembic_privileges.py:20-40, 520-526`; `native_program.py:116-200, 351-460`;
  `pdf_contracts.py:578-588`; `schema/model_explanation.py:413-460`; `cli/model.py:1440-1475`;
  companion plan `:354-483`; coordinator `:1-5, 96-106, 186-200`; `STATUS.md`.
- Surveyed by script at both baselines, every `.py` under `src/corpus_structure`: SQL-bearing
  literals, `text(`, `exec_driver_sql`, `.execute(str)`, `.replace(`, imports. Scripts:
  `…/scratchpad/lanegen2/` (`survey.py`, `calls.py`, `frag.py`); nothing else written.
- Not read: most regenerated module bodies beyond those functions; revision bodies other than
  N29; `semantic_alembic/` contents. Ran nothing from the project.

**Counting method A (every "SQL text lines" figure).** An AST walk over each module, excluding
docstrings. A string constant (or an f-string's literal parts) counts when it holds at least two
distinct uppercase SQL/PL keywords from a fixed set (SELECT, INSERT, UPDATE, DELETE, CREATE,
FROM, WHERE, BEGIN, END, RETURN(S), RAISE, DECLARE, PERFORM, THEN, LANGUAGE, GRANT, REVOKE,
ALTER, JOIN, EXECUTE, VALUES, plpgsql, TRIGGER, FUNCTION); its size is the lines it spans. On
`d78c98765` the same script reproduces the challenger's figures exactly (474, 444, 229, 136,
132, 130, 99; 1,826 in the eleven non-compiler modules; 2,100 with the three extras, challenger
2,090), so the baselines compare like for like.

---

## Scope A — DA-084 recounted from scratch

### A1. Every place production still holds hand-written SQL or procedural text (at `5139eaba3`)

**Headline (method A).**
- Production SQL text fell from **2,423 lines** (all modules, `d78c98765`) to **183 lines**.
- The fourteen modules DA-084 named now hold **0 lines** (from 2,100): rich 474, structural
  444, contextual 229, pdf_spool 136, contextual_witness 132, definition 130, archive 99,
  artifact 62, contextual_definition 64, companion_projection 30, contextual_linguistics 27;
  extras `pdf_publication_native` 57, `data_operation_cpu_basis` 167,
  `execution_evidence_leaf` 49 — all now 0.
- 73 of 78 `*_native.py` modules (77 in `semantic/` plus `methods/pm2_native.py`) import the
  program compiler (57 of 73 at `d78c98765`). The five that do not (`alembic_native`,
  `data_operation_source_native`, `data_operation_wire_native`,
  `data_operation_binding_native`, `pm2_native`) hold no SQL text.

**`.sql` files.**
- None remains under `src/`, nor anywhere outside the migration trees and evidence folders
  (`find`; `git ls-tree -r 5139eaba3`).
- `semantic/sql/` was removed by `9364a5b88` (`admission.sql`), `260d81f28` (source admission),
  `67ce99670` (visual read), `32ec30618` (`contextual_neighborhood`, `task_checks`) and
  `c25cada3f` (the other eleven, including the loaded `closure`, `identity`,
  `source_originals`, `source_record_recognition`, `pdf_descriptor`, and the six orphans).
  Process note: `c25cada3f` is titled "docs(review): recommendation audit …" yet deletes 621
  lines of production SQL.
- The former loaders now take generated programs: `target_installation.py:28-38`
  (`foundation_programs` → `closure_foundation_sql`, `canonical_identity_sql`); `:92-116`
  `authoring/*.sql` names label generated artifacts.

**Remaining SQL text: 183 lines by method A, classified by inspection.**

| Lines | Where | What it is | Class |
|---|---|---|---|
| 84 | `schema/model_deployment.py` 30 (`:899, 921, 963`), `semantic/alembic_indexes.py` 19 (`:44`), `semantic/unicode_identity.py` 16 (`:71, 114`), `semantic/authored_sql.py` 15 (`:194, 242, 262`), `semantic/storage_target.py` 3 (`:93`), `core/db/extensions.py` 1 (`:17`) | Catalog and server observation, admission observation, the qualification probe, and the submitted-SQL validator's own catalog reads | ADR-0131 exception: independent control SQL. None of these files changed in the window |
| 59 | `serve/selected_source.py` 16, `semantic/pdf_payload_validation.py` 15, `semantic/data_operation_read_index.py` 10, `semantic/pdf_certification.py` 9, `serve/demand_export.py` 8, `semantic/pdf_publication.py` 1 (`:619`) | SQLite statements for local stores and spools: 58 `.execute(str)` calls, identical to `d78c98765` | Outside ADR-0131 (PostgreSQL only). Still-maintained hand SQL, unchanged |
| 16 | `semantic/native_program.py:351-460` | Procedural framing written as f-strings (`f"IF ({cond}) THEN…"`, `"PERFORM" + sql[6:]` at `:391`) | Generated: the compiler's own renderer |
| 14 | `native_admission_principals.py:88-208`, `closure_native.py:102-136`, `native_admission_tables.py:200-203`, `alembic_privileges.py:349-354` | Privilege-name lists such as `'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'`, passed as values to `has_table_privilege` | Not statements. They are false positives of method A, but they restate the privilege matrix in four modules (A2) |
| 4 | `native_admission.py:58, 64, 67, 70` | Literal text anchors (`" IF NOT EXISTS(SELECT FROM sem.deployment_admission "`) that locate catalog checks inside **frozen** guards | Text surgery on frozen bytes (B2) |
| 2 | `target_installation.py:623-637` | `target_database_privileges_sql`: hand `DO $target_database$ BEGIN EXECUTE format('REVOKE TEMP …')…` with `.replace("'", "''")` quote escaping (`:634, 636`); consumed at `:951` | Still-maintained hand PL/pgSQL. The plan names it as remaining |
| 4 | `semantic/pdf_contracts.py:578-588` | `pdf_shape_guard_sql`: a hand PL/pgSQL fragment (`IF product ? 'document_json' THEN RAISE …`) | **Dead**: no caller in `src`, `tests` or `scripts` at either baseline. A new DA-080 item |

**Other text entry points (AST count, `calls.py`, `d78c98765` → `5139eaba3`).**
- `text(`: **29 → 17**; removed from `native_authoring` (4), `native_sql_body` (3),
  `target_installation` (4), `execution_admission` (1). Remaining: `model_deployment` 4 and
  `authored_sql` 5 (controls, submitted SQL); `evaluate/operation_fitting.py:539-594` 4
  (`SELECT eval.*(…)`, unchanged, trivially convertible); one each in `alembic_indexes`,
  `execution_admission`, `cli/db.py`; `data_operation_storage.py:1135`
  (`SELECT sem.data_operation_native_descriptor()`).
- `exec_driver_sql`: **38 → 25** (`native_authoring` 10 → 1, `target_installation` 6 → 2); the
  rest mostly executes generated or frozen text (e.g. `native_authoring.py:905`).
- `literal_column(`: 37 sites in 16 files, mostly local/CTE/parameter names; three tiny SQL
  literals (`pdf_publication_native.py:273-275` `"'null'::jsonb"`, `"'[]'::jsonb"`;
  `data_operation_projections.py:1115` `"'{}'::text[]"`). This is the escape hatch past the
  `TextClause` refusal (`native_program.py:128-129`); small and identifier-shaped.

**String splices.**
- The eleven DA-084 splice sites in seven modules are **all gone** (grep over every
  `.replace(` call). The task guard is a typed program over the model lifecycle
  (`data_operation_protocol.py:117-128`); source admission inserts its capture program by
  locating the parsed `ops.read_selected_pdf_source` declaration, with no marker
  (`data_operation_source_native.py:69-77`).
- Remaining, on **generated** text (DA-081): `data_operation_storage.py:815-817` replaces
  `__DDO_SOURCE_DIGEST__`/`__DDO_LOWERING_DIGEST__`, which generators emit as typed literals
  (`data_read_boundary_native.py:98`, `data_completion_settlement_native.py:47`,
  `data_operation_compiler_native.py:49-50`); `_rename_native_entrypoints` (`:725-758`) parses,
  renames, reprints, re-parses and slice-replaces.
- On **frozen** text: `frozen_catalog_verification` (`native_admission.py:85-125`, new in
  `1b643e7ed`) extracts the catalog-check substring from a frozen
  `data.require_execution_release` body by text markers (`catalog_checks`, `:42-82`) and
  concatenates it into a generated `DO` (`content.sval … + checks + "\nEND"`, `:122`).
  Arguably within the frozen-migration exception.
- On **hand** text: the TEMP-grant quote escaping (`target_installation.py:634-636`).

**Root scripts and provisioning.** Unchanged in the window (`git diff --stat` over `scripts/`,
`ops/`, `justfile` empty). `pg_provision.sh`/`pg_semantic_roles.sh` hold no SQL and run
pglast-built `host_bootstrap` output (generated). Test-harness hand SQL remains in
`native_test_support.py`, `pgtap_batch.py`, `native_auth.py`, `native_scenario_seeds.py` and
`native_deployment_build.py:16` (consumed by `tests/semantic/test_native_deployments.py`): test
account scope.

**DuckDB.** The six DuckDB modules are unchanged; no string `con.sql`/`con.execute`.

### A2. The regenerated admission modules: construction, typed share, model reach

**Construction.** Every listed module builds statements from SQLAlchemy Core over compiled
`MetaData` tables and procedural bodies from the compiler forms (`Block`, `Local`, `Parameter`,
`Assign`, `If`, `SelectInto`, `Raise`, `Return`, `ForQuery`, `CatchStrictLookup`, new
`Comment`); pglast nodes for types, ACL and DDL (e.g. `archive_native.py:242-281` builds
`CREATE TEMP TABLE … LIKE`, `ALTER … OWNER`, `GRANT` as `ast.*Stmt`). The three
`native_admission_*` modules are Core selects over `native_catalog` relations.

| Module | Lines | Hand SQL lines (A) | Relations by name | `.c.` refs | Callees `func.<schema>.*` | Hand facts held in Python (examples) |
|---|---|---|---|---|---|---|
| structural_admission_native | 2,067 | 0 | `model.tables[...]` in name tuples (`:965-980, 1170-1180, 1738-1752`) | 217 | 32 | Producer families and factories from `declared_structural_admission.py:11-14, 276` (`STRUCTURAL_REPORT_PRODUCERS`); disclosure field set checked against a **pydantic** model's `model_fields`, not LinkML (`:1680-1694`); one role literal (`:1502`) |
| rich_admission_native | 1,933 | 0 | `p.table`/`p.row` by name | 155 | 65 | Operation ids and factory entrypoints as literals, restated within the module: `rich.consolidate` → factory at `:617` and `:1219`; `locate.external_extraction` at `:613` and `:944`; `prepare.external_extraction` at `:608` and `:951`; `rich.admit` at `:582-587` and `:1278`; `record_policy.authorize` at `:1387` |
| contextual_admission_native | 793 | 0 | `p.table` by name (`:177-186`) | 46 | 27 | A twelve-entry operation-id → factory dict (`:188-201`); batch subset (`:205-209`); role subsets (`:303-309`); more literals at `:573-607, 759` |
| contextual_witness_native | 453 | 0 | via contextual | 42 | 16 | Three operation ids (`:240-251`) |
| definition_admission_native | 436 | 0 | 7 | 40 | 12 | `_OPERATIONS` tuple of four ids (`:33-37`) |
| artifact_admission_native | 239 | 0 | 4 | 10 | 5 | `"structure.artifact_identity/declared"` three times (`:112, 147, 217`) |
| source_admission_native (new) | 1,289 | 0 | 7 | 124 | 25 | Mostly structural; no operation-id literals found |
| record_policy_completion_native | 1,682 | 0 | 1 | 135 | 41 | `record_policy.fit/authorize/grade` literals (`:430, 553, 990, 1011, 1140, 1170`); one role literal (`:449`) |
| operation_event_native | 1,428 | 0 | 6 | 157 | 48 | `_OPERATIONS` (`:55-58`) and the same ids at `:295-1386` |
| data_product_admission_native | 961 | 0 | 3 | 90 | 28 | None by the operation-id grep |
| native_admission_release | 859 | 0 | 18 | 206 | 5 | Role tuple restated (`:400-404`); catalog-check comment markers (`:35-38, 371, 382`) |
| native_admission_tables (new) | 275 | 0 | — | 67 | 0 | `_ACTORS` role tuple (`:27-32`); JSON default role list as a string literal (`:181`) |
| native_admission_principals (new) | 229 | 0 | — | — | — | `_SOURCE_PRINCIPALS`, `_RUNTIME_PRINCIPALS`, `_APPLICATION_SCHEMAS`, and four hand kernel signatures as text (`:8-16`) |
| pdf_spool_native | 605 | 0 | 5 | 79 | 5 | One grant role (`:598`) |
| archive_native | 526 | 0 | 2 | 52 | 6 | Owner and admitter roles (`:99, 257, 277, 519-522`) |
| visual_read_native (new) | 684 | 0 | 7 | 68 | 8 | None found by grep |
| original_document_native (new) | 276 | 0 | 6 | 30 | 4 | One writer role (`:123`) |

*Counts:* relations by `tables[`/`p.table` grep; `.c.` occurrences; distinct
`func.(ops|data|sem|kb).name` references; operation ids by the regex
`"(retrieve|structure|rich|record_policy|operation_event)\.…"`.

**Typed share.** Statement construction is essentially 100% typed: 0 SQL-text lines across the
sixteen modules; the remaining strings are error messages and identifiers (`frag.py`). The
**facts** are mixed: relations and columns come from compiled model metadata; operation
membership, factory entrypoints, role and privilege sets, JSON payload paths and state values
are Python literals.
- Across `*_native.py`: 32 factory-entrypoint literals (`…acquire_port`) in 9 modules; 68
  task/record state literals in 17 modules (the same number as at `d78c98765`, when they sat in
  SQL text); 1,113 `func.<schema>.<name>` callee references, 260 distinct (887 before).
- Role-name occurrences in `src`: 176 in 39 files → **199 in 47 files**. The four-role set is
  restated as tuples in `native_admission_tables.py:27-32`, `native_admission_principals.py:8-9`,
  `native_admission_release.py:400-404` and as a JSON string (`native_admission_tables.py:181`),
  while `native_admission_functions.py:6` imports `alembic_privileges.DEFAULT_READ_ROLES`
  (`alembic_privileges.py:24-33`).
- The model gained no family or role declarations: the `data-operation-native.yaml` diff adds
  only `public_demand_selection`, `read_demand_selection` and `authority_selection`.

**Does a model change reach these modules?**
- *Renamed or retyped column or relation:* **yes, generation fails.** `model.tables["x.y"]`
  raises `KeyError` and `.c.name` raises `AttributeError` at generation; types flow through
  `column_type`, `relation.c[...].type` and `core_relation_row`. This is the ADR-0131 consequence
  (`:46`), and it now holds for these modules. Established from construction; no rename was run.
- *Renamed JSON property inside a modeled JSON shape* (the protocol `definitions` in
  `data-operation-native.yaml`): **no.** Paths are Python literals, for example
  `support["capabilities"]["prepared_factory"]` (`structural_admission_native.py:809`) and
  `_field(value, "name")`. PL/pgSQL evaluates them at run time; a wrong key yields NULL, and the
  outcome then depends on whether the guard treats NULL as a refusal.
- *New enum or family member* (a new operation in a family, role or lifecycle state): **no,
  and some guards fail open.** Family guards begin `If(op.not_in(<hand list>), (Return(),))`:
  `contextual_admission_native.py:215, 568`; `definition_admission_native.py:386` (and `:418`,
  returning TRUE for non-members); `operation_event_native.py:350, 1287, 1359`. A new member
  declared in the model is neither refused at generation nor checked at run time; it skips the
  guard (established at those sites; other layers not traced). Exception:
  `structural_admission_native.py:1680-1694` refuses at generation when the disclosure field
  set differs from its pydantic contract — a sound closed-set check, but against Python, not
  LinkML.
- *Renamed native function:* a free string; `plpgsql_check` and install-time binding during
  authoring catch it before freeze (unchanged).

**Assessment.** DA-084's ordering observation was a prediction: converting these bodies before
family membership and roles are declared "would transcribe the lists again". It is now
**observed**. The conversion moved the DA-070 lists and the DA-074 role literals from SQL strings
into Python literals in typed programs, at the same or greater multiplicity.

### A3. The owners' own account of remaining conversion work

- **ADR-0131** has not changed since `d78c98765`. It still says "Convert remaining maintained
  owners forward…" (`:40-41`) and "This decision records the target while conversion is open"
  (`:51`). Its consequence statement (`:46`) is now true for relations and columns in the
  converted modules (A2), not for the Python-held facts.
- **The companion plan** (`docs/plans/declared-data-operations/postgresql-realization-and-retirement.md`)
  narrates by stage: N19 (`:419-421`) "Maintained inline SQL remains in PDF publication and
  spool custody, archive, and specialized DDO admission"; N23–N24 (`:427-441`) convert them
  ("The written routine bodies they supersede are removed"); N25 (`:446-448`) "The remaining
  inline statements are in replay framing, installation and runtime adapters"; N29
  (`:463-464`) "Remaining authoring includes the fresh-root current-database TEMP grant framing
  and the typed replay and installation boundaries already identified above". This matches A1
  (`target_installation.py:623-637`; `native_admission.py:42-125`). The plan does **not**
  mention SQLite statements, the dead `pdf_shape_guard_sql`, the `operation_fitting` `text(`
  calls or the Python-held facts. Its claim that runtime principal queries are structured
  (`:378-379`) holds.
- **The coordinator** still carries two dated 2026-11-17 sentences listing broad remaining
  owners (`declared-data-operations_2026-11-12.md:100-103`, `:191-195`: "general native
  admission, scientific scoring and native fixture provisioning"); its status line (`:3`) now
  says only "Whole-view composition and DDO-12 qualification remain open".
- **STATUS.md:7-9**: "N18 source removes the last maintained standalone SQL template … The
  PostgreSQL companion owns remaining inline authoring."

**Framing.** By the plan's own account, the conversion of statement text is done apart from two
named framing sites. What none of the owners records is the residual described in A2: the hand
facts that typed programs carry, and the fail-open family guards.

### A4. Frozen migration trees

- **`target_alembic/`** (550 MB on disk, from 353 MB): 47 revisions (31 at `d78c98765`), N14–N29
  added; the deployed tree (`semantic/migrations.py:14`).
- **N14–N29 content.** Each `.py` is a fixed template (after normalizing names and digests 15
  are identical; N14 differs in its predecessor line) that SHA-256-verifies three artifacts:
  `*_native.json` (8.5–10.6 MB; N29 `desired` = 585 objects — 449 functions, 132 triggers, 4
  views — each with `catalog/identity/role_bindings/source/statements`, plus `operations` 9,
  `privileges` 113, `predecessor`, `version: 2`); `*_upgrade.txt` (2.2–4.4 MB, Alembic Python;
  N29 has only 9 `op.native_transition(` calls); `*_admission.sql` (~0.6 MB, the generated
  descriptor and guard, 2 `CREATE FUNCTION`s). So: generated bytes with a full
  server-normalized catalog snapshot, no raw `op.execute`. Each revision re-freezes the full
  desired state; N14–N29 add **206 MB** of plain Git blobs (`.gitattributes` routes only
  evidence through LFS; `git check-attr filter` = unspecified).
- **Frozen revisions run live code.** Each calls `native_objects.admit_native`,
  `NativeObject.from_payload` and `alembic_privileges.admit_privileges`; `upgrade.txt` imports
  `alembic_native`, `alembic_privileges`. `alembic_privileges.py` changed in the window
  (`4760982d8`, `9364a5b88`, ~110 lines), so replaying N2–N13 runs a different privilege
  verifier than at their freeze. Same template at `d78c98765` (N13 `.py:9, 39-42`). Contrary:
  these are verifiers, not effects; effects come from frozen bytes.
- **`semantic_alembic/`** (1,013 files, 1.8 GB) and **`alembic/`** (three phase-0 revisions):
  unchanged (same file counts); no `script_location` or path reference in `src`, `tests` or
  `scripts`; only the table name `semantic_alembic_version` survives (`migrations.py:15`).

### A5. DA-084 status

**Status: partly corrected, changed footprint.**
- *Corrected* (`9364a5b88`, `260d81f28`, `67ce99670`, `32ec30618`, `c25cada3f` and the N17–N25
  generation commits): hand PL/pgSQL in "native" modules 2,100 → 0 lines; loaded `.sql` files
  10 → 0; splices into hand bodies 11 → 0; relation and column references fail at generation.
- *Remaining hand PostgreSQL outside ADR-0131's exceptions:* the TEMP-grant `DO`
  (`target_installation.py:623-637`, named by the plan); `evaluate/operation_fitting.py:539-594`
  (`text(`); the dead `pdf_contracts.py:578-588`.
- *Changed:* the "hand lists" half stands and has moved — family membership, factory
  entrypoints, role/privilege sets and state literals are Python literals in typed programs,
  and membership-gated guards skip unlisted members (A2). Re-frame around facts, not SQL text;
  overlaps DA-070 and DA-074.
- *Consequence now:* field or type changes reach the converted bodies; family, role or state
  changes do not, and new family members pass some guards silently.
- *Contrary evidence:* one custody path (generation, server normalization, `plpgsql_check`);
  some literals deliberately pin an exact implementation (the guard refuses a definition whose
  factory differs, `contextual_admission_native.py:222-236`); the structural closed-set check.
- *Uncertainty:* method A undercounts lowercase or fragmented SQL (`frag.py` sampled 16 modules
  and found only messages); fail-open established at guard sites, not end to end.

---

## Scope B — The generator layer re-read

**Size** (line counts of `.py` files, both baselines, same script):

| Family | `d78c98765` | `5139eaba3` |
|---|---|---|
| `semantic/*_native.py` | 72 modules, 41,581 lines | 77 modules, 53,225 lines (+28%) |
| `semantic/native_*.py` infrastructure | 18, 7,476 | 21, 9,059 (new: `native_admission_functions` 161, `native_admission_principals` 229, `native_admission_tables` 275) |
| `semantic/alembic_*.py` | 5, 1,036 | 5, 1,104 |
| `target_installation`, `typed_generation`, `pdf_call_generation`, `prepared_sql` | 4, 1,074 | 4, 1,175 |
| `relational`, `generate`, `model_change`, `data_step_programs`, `host_bootstrap` | 5, 3,430 | 5, 3,430 (unchanged) |
| Generated facades (`semantic/_*.py`) | 9,390 | 9,409 |

New `*_native.py` modules: `source_admission_native` (1,289 lines), `visual_read_native` (684),
`original_document_native` (276), `pdf_descriptor_native` and `source_record_recognition_native`.
None was removed.

**Handoff from generation to installation: G-3 stands, with a smaller footprint.**
- Text is still the handoff. Generators return strings joined by `native_sql_script`
  (`native_objects.py:43-45`; 62 uses in 46 modules); `native_sql` concatenates ~33 named
  artifacts in hand order (`data_operation_storage.py:761-812`), text-replaces digests
  (`:815-817`), renames entrypoints by parse/reprint/re-parse (`:725-758`) and appends wire
  wrappers (`:822`). `_task_call_definitions` parses whole scripts once per selected name and
  each excerpt again (`native_authoring.py:177-202`); `prepare_sql` has no cache
  (`prepared_sql.py:52`); the compiler re-parses each rendered statement
  (`native_program.py:143, 157, 383`); twelve `*_native.py` modules re-parse their own output to
  mutate the AST (15 calls, e.g. `contextual_scoring_native.py:34, 219`,
  `pdf_integrated_native.py:232`).
- **New: a comment form used as a text locator.** `native_program.Comment` (`:177`) emits
  `-- native catalog checks begin/complete` into the generated guard
  (`native_admission_release.py:35-38, 371, 382`); `native_admission.catalog_checks` later finds
  them by substring and splices the span into a generated `DO` (`native_admission.py:42-125`,
  via `verify_frozen_catalog`, `native_authoring.py:888-907`), with literal SQL anchors for
  older guards (`:58-70`). The program objects know the boundary; the handoff recovers it from
  text.
- *Corrected:* scratch by string replacement. `native_authoring.py:299-346` renders Core DDL,
  parses it and replaces the `RangeVar` with `pg_temp.semantic_candidate_catalog`; `759dd837f`
  derives archive scratch from captured types. A small text check remains (`:340`).

**Work repeated per call or per process: G-6 stands.**
- `native_protocol_sources()` without arguments still recompiles physical metadata and
  regenerates every program (`data_operation_storage.py:48-200`, 98 `SourceArtifact(` entries).
  No-argument callers: `data_operation_storage.py:707, 713, 764, 883, 1018, 1857`,
  `data_operation_preparation.py:261`, `primary_operations.py:403`, and
  `serve/demand_export.py:281` (the whole set for one JSON schema). No memo was added in the
  storage, products, installation, authoring or program modules (grep `lru_cache`/`cache`).
  Contrary: `companion_projection.py:71, 547, 561, 620` gained `lru_cache`s (`3d5364c89`,
  `9c9f7c7e4`); the wire caches remain.
- `semantic/metadata.py:33-50` still compiles both projections at import; 63 importers (56).
- The set grew 28% in lines, so per-regeneration cost grew with it (inference; not measured).

**Registries: G-4 stands.** Hand-ordered lists remain: `native_protocol_sources` programs and
artifacts (`data_operation_storage.py:139-200`); `native_sql` order (`:766-812`); 32 module
file names in `capture_native_authoring_inputs` (`native_products.py:134-180`); the
`(filename, schema, name, roles)` table with role literals (`target_installation.py:226-235`);
`_NATIVE_OUTPUTS` (`schema/model_change.py`, unchanged).

**What the regeneration improved.** No statement text in deployed generators — above all the
admission kernel and privilege comparison (`native_admission_release.py`, `native_admission_*`);
shared typed catalog observation (`native_catalog.py`, new `function_body_fingerprints`); no
`.sql` sources and no marker splices into hand bodies; the task guard derives states from the
model lifecycle; AST-built scratch DDL; archive scratch shared by authoring and runtime (N25).

---

## Scope C — DA-079 and DA-080

**DA-079: stands, unchanged.**
No commit touched `orchestrate/execution_host.py`, `intervene/` or
`semantic/data_operation_service.py` (`git log` empty). `execution_host.py:91-92` still takes
the run lock non-blocking and raises `RuntimeError("process execution host already has an
active run")` (`:457-458` likewise on `close`); `native_render_tools.py:93` is still
`@tool_refusals(ValueError, KeyError, OSError)`; a `busy|HostBusy` grep finds only that message.
Overlap is still inferred, not observed.

**DA-080: partly corrected, changed footprint.**

| Group | Now | Evidence and commit |
|---|---|---|
| Orphan SQL files (6) | **Corrected.** All deleted, together with the directory | `c25cada3f` (mis-titled commit) |
| SQL change explanation | **New consequence.** `capture_sql_changes` still walks `semantic/sql` (`schema/model_explanation.py:413-460`, `prefix` at `:423`) and runs on every `model.preview` (`cli/model.py:1465-1468`). That directory no longer exists and every maintained SQL body is now generated, so the explanation reports deletions only against old baselines and otherwise nothing. Generated SQL changes are never explained, and an empty explanation reads as "no SQL change" | Unknown is presented as absent (FP-05; CI-04) |
| Fingerprint input | `.sql` is still in the suffix set (`schema/model_change.py:390-397`); harmless now | — |
| Evaluation modules | **Stands.** All seven present; no production importer; `split.py` imported only by `split_decisions.py` | grep over `src` |
| Rendition keying | **Stands.** `core/keys.py`, `translations.py`, `candidates.py` present; `KeyContext` only in `candidates.py` and `keys.py` | grep |
| Earlier pack loader | **Stands.** `schema/pack.py` and `lookup.py`; outside `schema/` only the path constant (`orchestrate/project.py`, `source_operation.py`) | grep |
| `published_address_migration.py` | **Corrected.** Deleted with its mechanism tests | `54a232131` |
| Analytical kernels without a caller | **Stands.** `analytical_kernels.py:150, 170`; `rich_relations.py:112, 115`; `FileRelation` (`capture_storage.py:78`) has no caller | grep; files unchanged |
| Unread analytics settings | **Stands.** `settings.py` unchanged in the window | `git diff` empty |
| Two unconsumed migration trees | **Stands.** `semantic_alembic/` (1.8 GB) and `alembic/` | A4 |
| Unused scalar encoder kernels | **Corrected** (not previously listed) | `contextual_encoder.py` deleted (151 lines) in `93b7141ec` |
| `pdf_shape_guard_sql` | **New item.** Dead hand PL/pgSQL fragment, dead at both baselines | `pdf_contracts.py:578-588` |

---

## Scope D — Analytical inventory delta since `d78c98765`

Method: each row owner in `analytical-inventory.md` was checked against the diffstat and its
`git log`; changed files were read at the diff hunks. **Unchanged (no commit):** D1–D5 (all six
DuckDB modules), X1–X8 (except the cache below), G1, G4–G6, G8, G10, S1, S3, S4, S6, E1–E7, SC,
I1–I8 (including the SQLite spools), M1, T1 (`arrow_transfer.py`), ADBC
(`core/db/adbc_lifetime.py`) and all pyarrow/Parquet sites. `MATERIALIZED` CTE prefixes in
`semantic/`: 47 → 55.

**Changed rows.**
- **G7 contextual neighborhood**: hand `sql/contextual_neighborhood.sql` → generated Core
  (`contextual_neighborhood.py:70-300`: pgvector `op("OPERATOR(public.<=>)")` `:180`,
  `row_number() OVER (PARTITION BY … ORDER BY distance, id COLLATE "C")` `:195`, `LIMIT` from
  `NeighborhoodNumericalPolicy.directed_limit` `:187`). Same computation (`32ec30618`,
  `df0cb85b8`).
- **G2 support walk**: `_support_walk` (`data_operation_projections.py:171`) is parametrized; a
  second walk seeds from the page's public uses (`page_public_support_seed`, `:2231`) after an
  `access_scoped_obligations` CTE (`:452`), so public reads carry one more recursive closure per
  page (`ed410b80f`, `6d699ab46`).
- **G3 watermark prerequisites** (`:2081`): role-matched (`_watermark_role_matches` `:1781`,
  `_unconstrained_watermark_uses` `:1919`); whole-demand frontiers include discovery
  (`110e8aa1e`).
- **X1**: captured projection inputs `lru_cache`d (`companion_projection.py:71, 547, 561, 620`).
- **Operation-event numerics** (section 2): the numpy/scipy `expit` scorer moved into a declared
  scorer port's `run` (`operation_policy.py:362, 380-391`; `04f542206`); same computation.

**Added rows** (set-wise work not inventoried before).
- **B1 binding population selection** (`data_operation_bindings.py:1028-1055`): independent
  optional roles are selected per role from the anchor instead of joining all optional roles and
  projecting `DISTINCT` (`1d3640990`); a cross product removed.
- **P1 PDF inventory completeness** (`pdf_publication_native.py:1925, 2160-2210`): parent→child
  access edges `MATERIALIZED` once and used for both missing-child and wrong-parent directions
  (`66c36d4c8`); previously `jsonb` children were expanded per probe.
- **A1 archived class matching** (`record_grade_native.py:150-175`): archived
  `data_operations.json` parsed to `jsonb` once per call (`bound_model`), complete classes
  filtered once (`complete_classes`) (`a31503daf`). The whole archived model is still parsed in
  PostgreSQL on each grading call.
- **M2 captured document composition**: inputs declared `collection: set`
  (`methods/captured_document_composition.py`), ordered canonically in Python by authenticated
  source coordinate without asserting reading order (`enriched_document_products.py:174-193`;
  `590b67b7a`, `1fab40234`, `67a6e7a51`).

**Removed rows.** `sql/contextual_neighborhood.sql` as a hand owner (G7 now Core);
`sql/source_record_graph.sql` (inventory "Source record graph"; deleted in `c25cada3f`); the
scalar encoder kernels (`contextual_encoder.py`, `93b7141ec`; not inventoried explicitly).

---

## Findings summary (diagnostic; no remedy selected)

| ID | Status | Decisive evidence | Changing commit(s) | Consequence now | Contrary evidence | Uncertainty |
|---|---|---|---|---|---|---|
| DA-084 | Partly corrected, changed footprint | A1 counts; `contextual_admission_native.py:188-215`; `definition_admission_native.py:33-37, 386, 418`; `target_installation.py:623-637` | `9364a5b88`, `260d81f28`, `67ce99670`, `32ec30618`, `c25cada3f`, N17–N25 generation commits | SQL text is gone. Family, role and state facts are Python literals in typed programs; new family members skip guards | Implementation pinning is deliberate; one closed-set check | The fail-open consequence was not traced end to end |
| G-3 (text handoff) | Stands, smaller | `data_operation_storage.py:725-822`; `native_admission.py:42-125`; `native_program.py:177` | `1b643e7ed` added comment-marker extraction; `759dd837f` removed scratch `str.replace` | Repeated parsing; boundaries recovered from text | Each transform verifies preservation; authoring time only | — |
| G-4 (registries) | Stands | `data_operation_storage.py:139-200, 766-812`; `native_products.py:134-180`; `target_installation.py:226-235` | — | Adding a program means editing three to five lists | — | — |
| G-6 (regeneration) | Stands, larger | eight no-argument `native_protocol_sources()` callers; `demand_export.py:281`; `metadata.py:33-50` | — | Cost grows with the 28% larger program set | New projection `lru_cache`s | Not measured |
| DA-079 | Stands | `execution_host.py:91-92`; `native_render_tools.py:93` | none | Unchanged | ADR-0125 | Overlap inferred |
| DA-080 | Partly corrected, changed footprint | the Scope C table | `c25cada3f`, `54a232131`, `93b7141ec` | Evaluation, keying, pack, kernels, settings and trees remain; SQL explanation now vacuous; `pdf_shape_guard_sql` dead | — | Dynamic imports not excluded |

**Really new structural causes.**
1. **Typed construction without a fact owner** (FP-02, FP-03; A1/A2; DP-01). Statements are
   generated, but family membership, factory entrypoints, role/privilege sets and state values
   have no model declaration and are transcribed per module (A2). Generation cannot refuse a
   missing family member, and membership-gated guards return silently for non-members. This is
   the cause DA-084 predicted, now realized; better recorded once with DA-070/DA-074.
2. **Boundaries recovered from text through emitted comments** (A3; DP-16; FP-07). The new
   `Comment` form exists so later substring search can find the catalog-check span
   (`native_admission_release.py:371, 382` → `native_admission.py:51-82`).
3. **Change explanation bound to a retired layout** (FP-05 unknown-is-not-absent; CI-04).
   `capture_sql_changes` explains only `semantic/sql/*.sql` and pack files, so the operator
   preview now explains no maintained SQL change; the generated-SQL diff is the natural subject
   and the preview already holds both snapshots (inference).
4. **Frozen revisions not hermetic; each re-freezes the full state** (FP-07; CI-10). Revisions
   call live `admit_native`/`admit_privileges` and store ~12 MB of desired state each; 16
   revisions added 206 MB of non-LFS blobs (A4). Contrary: verifiers, not effects; exact by
   design. Low severity; a fact for the lifecycle owner.

**Sound designs to preserve.** The compiler's `TextClause` and unresolved-bind refusals
(`native_program.py:128-131`); security definer requires a search path; relation/column
resolution against compiled metadata at generation; the typed lifecycle task guard
(`data_operation_protocol.py:117-128`); AST scratch DDL (`native_authoring.py:299-330`);
marker-free insertion (`data_operation_source_native.py:69-77`); the closed-set field check
(`structural_admission_native.py:1680-1694`); shared typed catalog observation
(`native_catalog.py`); frozen bytes with digests and catalog snapshots; the submitted read-only
SQL route (`authored_sql.py`); binding cross-product avoidance and single materialization of
access edges and the archived model (Scope D).

**Limits.** All counts are lexical/AST and state their method; "no caller/consumer" rests on
grep over `src`, `tests`, `scripts`; nothing executed or timed; execution fit is qualitative.
