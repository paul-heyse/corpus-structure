# Lane: typed-program and generator layer, and remaining SQL (baseline `d78c98765`)

Audit contribution (diagnostic, read-only). Source facts come from the frozen snapshot `snap5/`. Paths are relative to `snap5/python/corpus-structure/` unless they start with `docs/` or `scripts/`. History comes from read-only git (`fbd3f2a98..d78c98765`, 197 commits).

**Coverage.** Read fully: `src/corpus_structure/semantic/native_program.py`, `typed_generation.py`, `native_inventory.py`, `native_source_view.py`, `pdf_call_generation.py`, `data_operation_wire_native.py`, `target_installation.py:20-408`, `767-855`, and `native_admission_release.py`. Read in part (the relevant functions): `native_objects.py` (definition, observation, normalization, admission), `data_operation_storage.py:48-420`, `690-880`, `1835-1860`, `schema/model_change.py:51-555`, `640-720`, `native_products.py:54-391`, `alembic_privileges.py:1-120`, `540-590`, `native_admission.py:395-452`, `native_authoring.py:153-320`, `data_operation_protocol.py:100-160`, `data_claim_native.py:1-140`, `data_operation_value_native.py:1-80`, `source_value_native.py:1-110`, `pdf_publication_native.py:459-566`, `pdf_staging_native.py` (outline), `pdf_search_native.py:96-120`, `binding_admission_native.py:40-56`, `data_step_programs.py:1-60`, `core/db/host_bootstrap.py:1-52`, `schema/physical.py:150-199`, `semantic/metadata.py`, and `prepared_sql.py`.

**Surveyed by script** (counts below come from regex or AST passes over the snapshot): every `.py` under `src/corpus_structure`. The script found SQL-bearing string constants and f-strings, `text(`, `.replace(`, Core DML calls, pglast parse calls, `native_program` imports, `tables["…"]` lookups, `func.<schema>.<name>` references and role-name literals.

**Delegated** to two sub-lanes, whose results I checked and integrated: the DuckDB modules and the SQL inventory of Scope B.

**Not read:** the bodies of most of the 73 `*_native.py` modules, `native_call_generation.py` beyond its header, `schema/relational.py` beyond its outline, `model_deployment.py`, and the migration revision bodies (sampled only through the sub-lane).

**Run:** I ran nothing from the project and made no timing measurements. Execution-fit claims below are qualitative.

---

## Scope A. Typed-program and generator layer

### A1. Architecture as built

**Layers (observed).**

1. **Model capture.**
   - `schema/physical.py:81-199` resolves the trusted LinkML import closure. It is named bytes plus the pinned LinkML types, with value-set populations resolved into the documents.
   - It builds one `SchemaView` and compiles SQLAlchemy `MetaData` (`compile_physical`). The `MetaData.info` carries `physical_model_id`, `physical_sources` and `physical_linkml_types`.
   - `semantic/metadata.py:32-50` does this at import, twice: once for the physical model and once for `read-projections.yaml`.
2. **Typed metadata.**
   - `schema/relational.py` (819 lines) maps LinkML slots and `ph:` annotations to `Table` and `Column` objects, including checks, defaults, generated columns, indexes, nominal types and enum info.
   - Call contracts resolve separately. `semantic/native_call_sources.py` (647 lines) builds its own `SchemaView` from logical and physical sources. `native_call_contracts.py` holds `OperationCallBinding` and the field-kind map `NATIVE_FIELD_TYPES`.
3. **Statements and programs.**
   - Relational statements are SQLAlchemy Core over the compiled `Table` objects, plus pglast AST nodes for PostgreSQL-only syntax such as types, `ColumnRef` and `ParamRef`.
   - Procedural framing comes from the program compiler, `semantic/native_program.py` (635 lines). A program is a frozen-dataclass tree: `Block(statements, locals)` with `Local` (scalar `TypeName` or `%ROWTYPE` of a `Table`) and `Parameter`.
   - **Finite forms** (`native_program.py:176-320`): `Sql`, `Assign`, `GetRowCount`, `Perform`, `PerformQuery`, `SelectInto [STRICT]`, `Raise` (explicit SQLSTATE and optional DETAIL), `If/ELSE`, `While`, `ForQuery`, `ForRelation` (dynamic `EXECUTE format(...)` over a regclass with model-named columns), `ReturnQuery`, `Return`, `ReturnNext`, `Continue`, `Exit`, and three fixed exception handlers (`CatchCheckViolation`, `CatchDataConversion`, `CatchDependencyInvalidity`).
   - Set-returning routines use `ReturnQuery` / `ReturnNext` with `table_columns`. Recursive CTEs are Core `cte(recursive=True)` inside a statement; `_render` de-duplicates shared CTE nodes at `:119-132`. There is no loop or CTE form beyond these.
   - Routine constructors are `function` (plpgsql), `sql_function`, `Do` and `void_call_function`. The last derives its signature from a resolved `OperationCallBinding` (`:594-635`).
   - Options are emitted as pglast `CreateFunctionStmt` options: language, volatility, strict, security definer, and `SET search_path`. Security definer without a search path is refused (`:538`).
4. **Rendering.**
   - Core is compiled with the PostgreSQL dialect and `literal_binds`. `TextClause` and unresolved binds are refused (`:128-131`).
   - pglast nodes print through `RawStream`. The subclass `_NativeStream` quotes COL_NAME_KEYWORDS in TABLE parameters (`:93-113`).
   - The PL/pgSQL **body is assembled by f-strings** (`:342-455`), for example `f"IF ({cond}) THEN ..."` and `"PERFORM" + sql[6:]`. Every rendered statement is **re-parsed** with pglast to assert there is exactly one statement (`_statement`, `:155-159`). `column_type` renders and parses one `SELECT CAST(NULL AS t)` per column (`:140-152`).
5. **Assembly into a program set.** Generated SQL text is gathered as `SourceArtifact(name, bytes)` in three hand-ordered registries:
   - `native_protocol_sources` (`data_operation_storage.py:48-420`, about 97 `SourceArtifact` entries). It pairs each generated `.sql` with the generator module's own source bytes, for example `native/demand-intent.py`.
   - `capture_native_authoring_inputs` (`native_products.py:54-195`), which also captures 18 Python modules and two hand `.sql` files.
   - `capture_target_installation` (`target_installation.py:65-112`).

   `native_sql` (`data_operation_storage.py:753-812`) concatenates about 33 named artifacts in a hand-ordered list. It then splices digests into `__DDO_SOURCE_DIGEST__` and `__DDO_LOWERING_DIGEST__` markers (`:804-808`), renames entrypoints with a pglast round trip (`_rename_native_entrypoints`, `:715-748`), and appends generated wire wrappers (`:813-862`).
6. **Normalization and custody.**
   - `target_native_definitions` (`target_installation.py:189-405`) turns text into `NativeDefinition`s. It re-parses the concatenated text once per selected function name (`_task_call_definitions`, `native_authoring.py:171-199`), takes the excerpt, and parses it again in `definition_from_sql` (`native_objects.py:381-440`). That second parse asks the server for canonical argument types (`to_regtype` / `format_type`).
   - `prepare_native_authoring` (`native_objects.py:950-1121`) installs everything in a rollback-only savepoint on an owned authoring database, with optional `plpgsql_check`. It reads the server-normalized catalog back and produces `NativeObject`: the exact statements plus a sorted-JSON catalog snapshot.
   - `prepare_target_candidate` (`target_installation.py:767-855`) freezes these into an Alembic revision as `NativeTransitionOp` / `ExecuteSQLOp`.
   - `admit_native` (`native_objects.py:1124-1137`) and the in-database guard `data.require_execution_release` later compare the observed catalog with the frozen expectation.
   - The function inventory is recovered by re-parsing generated text (`native_inventory.py:83-158`) rather than from the program objects.
7. **Python facades.**
   - `schema/model_change.py:_native_facades` (`:525-552`) renders seven generated Python files from the same snapshot: `_source_admission_calls.py` (436 lines), `_typed_columns.py` (179), `identifiers.py` (12), `_data_operation_fates.py` (62), `_pdf_native_calls.py` (6,202), `_pdf_native_ids.py` (15) and `_data_operation_wire.py` (2,328).
   - The preview keeps them as exact file effects (`prepare_preview` → `check_preview` / `apply_preview`, `:1066-1143`).
8. **Model-change use.**
   - Preview compiles the requested physical closure (`:681`), prepares data steps through the typed `schema/data_step_programs.py`, renders facades, and fingerprints the inputs (`compilation_fingerprint`, `:322-451`).
   - The fingerprint hashes the request, the physical closure, every `.py/.sql/.yaml/...` file of both the selected and running packages except generated outputs, Python and compiler versions, and about 25 library versions.
   - Candidate preparation authors on an owned empty target. Registration and deployment use the frozen Alembic revision and catalog admission. No generator runs at deployment (`native_objects.py:1-5`).

**Size.**
- 73 `*_native.py` modules (41,794 lines).
- Plus the program and authoring infrastructure (18 `native_*.py`, 6 `alembic_*.py`, `target_installation.py`, `typed_generation.py`, `pdf_call_generation.py`, `prepared_sql.py`; 9,817 lines).
- Plus `schema/relational.py`, `generate.py`, `model_change.py`, `data_step_programs.py` and `core/db/host_bootstrap.py` (about 3,430 lines).
- Plus about 9,230 lines of generated facades.
- Of the 69 `*_native.py` modules that hold SQL or statements, 57 import `native_program`.

**Sound designs (observed).**
- `TextClause` is refused inside programs.
- Every routine statement is checked to be single.
- Security definer requires a search path.
- Server-side normalization and `plpgsql_check` run in rollback-only scope.
- Exact frozen statements and catalog snapshots go to Alembic custody.
- Deployment never imports generators.
- Facades are generated from the snapshot that produced the SQL and applied only as approved exact bytes.

### A2. What generators take from the model versus hold in Python

Method: I read representative functions and counted patterns per module with a script. `tables["x.y"]` means a relation is named by a Python string and resolved against compiled metadata, so a missing relation fails at generation time. `.c.name` columns are checked the same way. `func.ops.name` and enum or state literals are not checked at generation.

| Family / generator | From the model / compiled metadata | Held in Python |
|---|---|---|
| DDO claim `data_claim_native.py` | Relations via `target.tables[...]` (`:39-44`). Column types via `relation.c[name].type` (`:52-53`). Required/optional payload keys from protocol YAML `definitions.claim_data_request_request` (`:38`, `:117-127`). Row types `pg_type(schema, name)`. | Relation names as strings. Payload JSON keys `p["task_id"]`, `["attempt"]`, `["holder"]`, `["lease_seconds"]`. Task state `"running"` (`:79`), although the model declares the lifecycle (`model/semantic/data-operation-native.yaml:7-14`). Function names `ops.ddo_claim`, `ops.ddo_authorize_request`, `ops.ddo_request_useful`. SQLSTATEs. `search_path`. |
| DDO binding `binding_admission_native.py` | 7 relations by name list (`:45-56`). 80 `.c.` column references. | Dimension literals `("provider","alternative")` (`:513`), JSON witness keys, 19 `func.<schema>.<name>` callees. |
| DDO completion `data_completion_settlement_native.py` (1,122 lines) | Columns through `.c.` (64). | 50 free callee names. JSON-pointer decoding in SQL (`:130`). |
| DDO validity `data_validity_native.py` | 17 relations by name, 112 columns. | Callees, JSON keys. |
| DDO closure `closure_native.py` | 4 relations by name. | Callee names. Wrapped in hand `sql/closure.sql` and `sql/identity.sql` (below). |
| DDO value codec `data_operation_value_native.py` | Tags from **Python** `Literal` types in `data_operation_identity.py` (`:44-49`), not LinkML. | `_TEXT = ("string","date","datetime","float","integer","decimal")` (`:50`). Tag tests `tag.in_(("boolean","string",...))` (`:337`, `:391`, `:405`). |
| SourceValue codec `source_value_native.py` | Variant tags and payload slots from the captured observations LinkML through its own `SchemaView` (`:55-66`). Drift raises an error. | Closed variant list `("Text","Integer",...,"Object")` (`:57`) and `SourceField` slot set (`:63`). This is a **closed-set check against the model**, a sound pattern. |
| PDF staging `pdf_staging_native.py` | 22 relations by name, 217 columns. Scratch tables from shared scratch specs. | Role literals `corpus_sem_writer` / `corpus_sem_publisher` in GRANT nodes (`:149`, `:337`, `:1072`, `:1517`). Parameter-name lists. |
| PDF publication `pdf_publication_native.py` (2,460 lines) | 57 relations by name, 534 columns. | 14 hand SQL strings, including two views and two `read_pdf_published_*` declarations (`:394`, `:459`, `:493-560`). A hand signature list driving f-string `REVOKE`/`GRANT` (`:547-560`). Placeholder rewrites `'{pdf_payload_profile}'` / `'{pdf_payload_family}'` (`:562`). 19 role literals. |
| PDF certification `pdf_certification_native.py` | 7 relations by name, 70 columns. | Profile strings such as `"pdf-record-lowering-contract-v1"` (`:173`). |
| PDF search `pdf_search_native.py` | Reader callees and result fields from the captured call bindings (`_reader`, `:96-118`). Text-search configuration from the generated vector slot. | Its own kind→SQLAlchemy map (`:98-104`), a fourth copy (see A3). |
| Admission `native_admission.py` + `sql/admission.sql` | Release and receipt preconditions are typed over `sem.release*` (`native_admission_release.py:9-63`). | The enforcing function `data.require_execution_release` is **hand SQL** (`sql/admission.sql`, 186 lines). Typed fragments and generated comparisons are spliced in by **string markers** (`native_admission.py:415-444`). The schema USAGE ACL adds a literal `corpus_sem_publisher` CREATE (`:412`). |
| Privileges `alembic_privileges.py` | Per-table `read_roles` from `relation.info` (`:72`). | `PUBLISHER`, `DEFAULT_READ_ROLES`, `PURPOSE_ROLES` constants (`:25-34`). The admission comparison is a hand PL/pgSQL string with `__PURPOSE_ROLES__` replaced (`:567-589`). |
| Wire admission `_wire_wrapper_sql` (`data_operation_storage.py:815-862`) | Operation names and input JSON schemas from the captured protocol. Contract digest. | Wrapper naming `ddo_impl_` + name, applied through a pglast rename of already-generated text (`:715-748`). |
| Task guard `target_installation.py:37-54` + `data_operation_protocol.py:116-160` | Lifecycle states and transitions from the protocol model. | The trigger body is a hand PL/pgSQL string. The states are rendered by `__DDO_TASK_*__` token replacement with hand quoting. A second hand file, `sql/data_operation_task_checks.sql`, is spliced at a comment marker. |

**Facts never in the model (observed).**
- **Roles.** 175 literal occurrences of `corpus_sem_*` across 39 modules, and none in `model/**/*.yaml` apart from `ph:read_roles: '[]'` annotations.
- **The execute-grant matrix for native functions.** This is per-call Python, for example `target_installation.py:212-278` and `native_authoring.py:159`.
- **Native function names** called across programs. These are bound only when PostgreSQL installs the program.
- **Task or record state literals.** About 37 sites of `pending|running|failed|...` across 12 generators.

**Residual text sites in the generator layer** (excluding SQL `func.replace`, `os.replace` and quote escaping):
- **SQL-text `.replace` sites: 15 in 9 modules**
  - `alembic_privileges.py:589`
  - `contextual_linguistics_native.py:49`
  - `data_operation_protocol.py:129,156`
  - `data_operation_source_native.py:72`
  - `data_operation_storage.py:804,805`
  - `native_admission.py:419,428,439,444`
  - `native_authoring.py:297,311`. This rewrites compiled `CREATE TABLE` / `CREATE INDEX` into temp scratch by string.
  - `pdf_publication_native.py:562`
  - `structural_admission_native.py:482-494`, one chain of 7 tokens.
- **Python-source `.replace` sites: 2.** `relational.py:765` and `native_call_generation.py:598-600`, which edit rendered class text.
- **SQLAlchemy `text(` calls: 29 across `src`, plus 38 `exec_driver_sql` calls.** The 29 comes from the sub-lane's AST scan. My regex found 38 matches, but that count includes `record.text()`-style calls, which are not SQL. The per-module breakdown is in Scope B.
- **Hand SQL string literals inside `*_native.py`: about 1,940 lines in 13 modules.** The largest are `rich_admission_native.py` (474), `structural_admission_native.py` (444), `contextual_admission_native.py` (229), `pdf_spool_native.py` (136), `contextual_witness_native.py` (132), `definition_admission_native.py` (130) and `archive_native.py` (124).
  - Eleven of these were **not touched** in `fbd3f2a98..d78c98765` (git log: 0 commits).
  - They are still deployed through `native_protocol_sources` (`data_operation_storage.py:249-352`) and `pdf_staging_native.py:170`.

**Core versus program-compiler boundary.**
- The stated rule (`native_program.py:1-5`, ADR-0131) is: Core and pglast own statements and expressions, and the compiler owns only procedural framing. Where it is applied, the rule holds and is principled. Statements never pass through text inside programs.
- The boundary is **not the only route** to the database. Three other authoring routes coexist:
  - hand PL/pgSQL strings in Python, with or without token templating;
  - hand `.sql` files spliced by markers (admission, task checks, closure and identity foundation);
  - post-generation text transforms (digest markers, entrypoint rename, scratch DDL rewrite, trigger f-strings at `target_installation.py:330-386`).
- ADR-0131 names only three exception classes: frozen migrations, independent controls and submitted read-only SQL. The plan's residual sentence ("Remaining catalog, scientific, public-read and maintenance routines follow their owning boundaries", `docs/plans/declared-data-operations/postgresql-realization-and-retirement.md:401-403`) does not classify the residue. It is still-maintained hand SQL (FP-02/FP-03 below).

### A3. Duplication and consistency

- **Hand registries of the program set.** Each of these must be kept in step with the generator imports, names and order:
  - The `(name, module filename, generator)` triples in `native_protocol_sources` (`data_operation_storage.py:139-180`), plus about 90 more `SourceArtifact(...)` lines pairing literal artifact names with literal module filenames.
  - The concatenation order in `native_sql` (`:756-797`).
  - The module-file list in `capture_native_authoring_inputs` (`native_products.py:133-153`).
  - The `(filename, schema, name, roles)` table in `target_native_definitions` (`target_installation.py:212-249`). It still dispatches on the name `"scientific_layout.sql"` (`:230`, `:236`), although that file no longer exists. This was already noted in the DA-080 delta.
  - The provider pre-ordering list (`:302-314`). Contrary evidence: SQL-language bodies bind their callees at CREATE time, and catalog-based `native_dependency_order` cannot see objects that are not yet installed.
- **Facade output registry.**
  - `_NATIVE_OUTPUTS` (`schema/model_change.py:53-61`) is zipped `strict=True` against a hand-ordered `values` tuple (`:538-552`). Length is checked; correspondence is not.
  - The same paths are restated in `typed_generation.py:__main__` (`:113-117`) and `pdf_call_generation.py:__main__` (`:32-35`), and as the first argument of each `_format` call.
  - The canonical generator (`schema/generate.py:563-578`) does check that emitted paths equal its registry. The native facades lack that check.
- **Field-kind → type maps (four copies).**
  - `NATIVE_FIELD_TYPES` holds PostgreSQL names and SQLAlchemy constructors **as strings** (`native_call_contracts.py:16-25`).
  - `_PRIMITIVES` holds Python names (`native_call_sources.py:28-37`).
  - `pdf_search_native.py:98-104` holds SQLAlchemy classes.
  - `native_program.void_call_function` special-cases `int4` (`:621-622`).
  - The reverse map `"jsonb": "json_payload"` is at `native_call_sources.py:135`.
- **Role set.**
  - Defined once in `alembic_privileges.py:25-34` and reused by `host_bootstrap.py:20-50`.
  - Restated as literals in generators: 175 occurrences, including `native_admission.py:412-416`, which locates its splice point by the literal text `rolname='corpus_sem_evaluator'`.
- **Model aliases.**
  - `native_call_sources.py:59-64` maps `pdf-records` ↔ `pdf_records` and similar module names by hand.
  - `_TRANSFORMS` (`:38-41`) holds two `physical:` correspondences by hand.
  - `typed_generation.TYPED_RELATIONS` (`:10-17`) is a hand selection. Its comment marks it as operation selection only.
- **Task lifecycle declared once, used twice.** The guard trigger reads the model lifecycle, but kernels test the literal `"running"` (`data_claim_native.py:79`, and 37 state literals across 12 generators).
- **Naming conventions held only by convention.**
  - `ddo_impl_` + operation name: the rename at `data_operation_storage.py:735` and the wrapper call at `:839` must agree.
  - `__DDO_*__` and `__OPERATION__` tokens. Each template checks that its tokens are present and fully resolved, which partly mitigates this.
  - `native/<name>.sql` ↔ `native/<name>.py` artifact pairing.
- **Two SourceValue/value codec families.** The DDO value codec takes its vocabulary from Python `Literal` types. The SourceValue codec takes it from LinkML. Both are JSON-value codecs in PostgreSQL, with separate authorities (inference: worth unifying in the domain model).

### A4. Execution fit

**Import time (observed).**
- `semantic/metadata.py` reads the physical closure twice (`:32` id, `:33-37` compile) and compiles two `SchemaView`→`MetaData` projections at import (`:46-50`).
- 56 modules import it, so every CLI or MCP process that touches `semantic` pays one LinkML resolution and two compiles.
- Inference: this is acceptable as one-per-process work, but it is not lazy. It also makes the compiled model a module global, which generators then default to (`native_products.py:84-87`, `pdf_call_generation.py:12`).

**No memoization of the program set (observed).**
- `native_protocol_sources()` with no arguments regenerates about 40 programs. That means compiling physical metadata, building additional `SchemaView`s (call sources, SourceValue), rendering, and one pglast parse per statement plus per typed column. It also reads about 50 module files.
- Its no-argument callers are:
  - `primary_operations.py:403`
  - `data_operation_preparation.py:261`
  - `serve/demand_export.py:281` (export, for one JSON schema)
  - `data_operation_storage.py:_protocol`, `native_source_digest`, `native_sql`, `native_operation_calls` and `native_operation_declarations`, whenever they are called without `sources`.
- One model-change preview reaches a full rebuild at least twice: `acquire_data_operation_inputs` (`model_change.py:603`) and `_native_facades` → `capture_native_authoring_inputs`. A third happens if `compilation_fingerprint` runs in the same command (`cli/model.py:1676`, `:1925`; `model_deployment.py:592`).
- The only caches in the layer are the wire protocol's `lru_cache`s, keyed by content bytes (`data_operation_wire.py:46-485`), and `serve/selected_source.py:39`. These are sound designs and the natural place for a content-keyed cachetools cache.
- Generators run only on authoring, preview and preparation paths. Deployment and admission read frozen payloads. No generator is reached from read acquisition. `selected_source` uses the cached ambient protocol.

**pglast cost paths (observed).** The same text is parsed repeatedly:
- every rendered statement (`_statement`);
- `PerformQuery` twice;
- whole concatenated scripts once per selected function name (`_task_call_definitions`). For example, `closure.sql` is parsed for 4 names and runtime bindings for 3, in `target_installation.py:212-278`;
- each excerpt again in `definition_from_sql`;
- the inventory again (`native_inventory.py:88`);
- the rename pass, which parses, reprints and re-parses (`data_operation_storage.py:726-744`).

Inference: this is bounded authoring cost, but it is quadratic in owners per script. It comes from the text-first handoff between generation and normalization: programs become text before identity is assigned.

**Identity breadth (observed).**
- `native_source_digest` hashes every `native/*` artifact, including generator **Python source bytes** (`data_operation_storage.py:703-713`). It is embedded in every completion guard (`:804`).
- `compilation_fingerprint` hashes every implementation file of both package copies.
- Consequence: a comment edit in any captured generator changes the attested kernel digest. Contrary evidence: this is deliberately conservative custody, and identity is coarse on the safe side.

### A5. The DuckDB modules (sub-lane, checked against source)

Correction to the brief: no operation moved from PostgreSQL to DuckDB. The DuckDB uses already existed at `fbd3f2a98` as DuckDB SQL strings. Commits `ef6a7b13f`, `048d5ab17` and `dbe22b899` rewrote them onto the DuckDB 2.0 relational/expression API, and ADR-0131 does not mention DuckDB. All six modules now make **no `con.sql` / `con.execute` calls**. Function names still pass as strings (`fn("unnest")`, `.cast("DOUBLE")`).

| Module | Computes | Inputs and schema origin | Connection | Results | Model facts restated |
|---|---|---|---|---|---|
| `semantic/analytical_kernels.py` + `rich_relations.py` | Rich-rule views: same-slot, alternative-of and declared projections (`analytical_kernels.py:204-309`). `disagreements` and `fuse` have **no production caller**. | Python objects → `pa.Table.from_pylist` (`rich_rule_evaluation.py:551-596`). **Hand** Arrow schemas `VIEW_*` (`analytical_kernels.py:21-60`). | One per consolidation (`rich_consolidation.py:405-410`), with private spill dir, threads=1, `memory_limit="2GB"` literals, and cancellation checks (`rich_relations.py:60-110`). | Arrow → `to_pylist` dicts. | Column names, projected attributes `("id","key","types","label","symbol")` (`:62`). |
| `serve/companion_export.py` | Inventory and multiset compare of exported Parquet (`:403-606`). The export itself is PostgreSQL → ADBC COPY → Parquet, without DuckDB. | Parquet. The export schema is **model-derived** (`companion_projection.py:452-529`). | `duckdb.connect()` per inventory and per compare; compare also runs two inventories (3 connections). | `fetchall` → JSON via CLI. | Family→grouping columns (`:419-424`), dimension lists, excluded provenance/source columns (`:557-589`). These duplicate the `cp:role` annotations. |
| `ingest/pdf_candidate_geometry.py` | Candidate geometry, inline matching with window ambiguity, cell overlap (`:96-307`). | Spool IPC batches with a model-derived payload schema. Boxes use **hand** `_BOX_SCHEMA` (`:60-72`). | One per `CandidateGeometry`, threads=1 (`:87`). | Reader. Only single-match rows are hydrated. | Struct edge names, `"BOTTOMLEFT"`, Docling labels (`:196`). |
| `ingest/pdf_stream_reconciliation.py` | Disk-backed external sort of recognition replay (`:290-337`). | **Hand** `_OBSERVATION_SCHEMA` (`:235-243`). | Per call, `memory_limit="2GB"`, `threads=1` literals. | Reader → `json.loads` per row. | `pin_json` duplicates `input_key` (`:260-261`, defect). |
| `semantic/artifact_identity.py` | Splink backend only (`:481`, `:579`). | Python dicts. | Per call. | Splink. | None. |

**Assessment.**
- DuckDB clearly pays for itself in the companion compare (file-scoped `EXCEPT ALL` that keeps multiplicity), the geometry joins and the bounded external sort.
- The rich kernels pay a Python → Arrow → DuckDB → Arrow → Python round trip and a fresh connection and temp directory on small per-subject data. The benefit there is declarative set semantics, not speed.
- Three of the five modules hand-declare their Arrow schemas, so the "model propagates" consequence of ADR-0131 does not reach them.
- Resource settings are call-site literals rather than `settings.analytics`.

### A6. Findings (diagnostic; no remedy selected)

**G-1. The conversion left a fourth authoring route: hand PL/pgSQL inside "native" Python modules, still deployed and unclassified.**
- Principles: FP-02, FP-03; A2; DP-01, DP-16; H27.
- Sites:
  - about 1,940 string lines in 13 `*_native.py` modules, 11 of them untouched since `fbd3f2a98`;
  - `sql/admission.sql` with marker splicing (`native_admission.py:415-444`);
  - the task guard template (`target_installation.py:37-54`);
  - trigger f-strings (`:330-386`);
  - `pdf_publication_native.py:394-562`.
- Consequence: a model rename or type change does not propagate to these bodies. PostgreSQL authoring catches only what binds at install. ADR-0131's consequence ("propagates … or compilation refuses") is not true for them, and the "conversion complete" status overstates it.
- Contrary evidence: these are installed, normalized and `plpgsql_check`ed on the same custody path, and some touch only JSON payloads.
- Uncertainty: I did not check which of these bodies reference relations or columns rather than only JSON.

**G-2. Security-relevant facts are held in Python, not the model.**
- Principles: FP-01, FP-02; A1; DP-01.
- Facts: role set, execute grants per native function, schema USAGE/CREATE policy, and the publisher owner (175 role literals in 39 modules; `alembic_privileges.py:25-34`).
- The admission kernel finds its own insertion point by literal role text (`native_admission.py:412-416`).
- Consequence: a role change is a multi-site Python edit, and the privilege policy that admission enforces has no model owner.
- Contrary evidence: table `read_roles` is modeled (`relation.info`). The constants are centralized for host bootstrap and privileges.

**G-3. Text is the handoff between generation and normalization.**
- Principles: A3, FP-07; DP-16; H on parse once.
- Sites:
  - generated ASTs and Core statements are rendered to text, concatenated, re-parsed per selected name, excerpted and parsed again;
  - the inventory is re-derived from text;
  - digests and entrypoint names are patched into text after generation;
  - scratch DDL is produced by `str.replace` on compiled DDL (`native_authoring.py:297-311`).
- Consequence: identity and ABI facts are recovered from text instead of being carried by the program objects. This brings repeated parse cost and brittle markers. For example, `_rename_native_entrypoints` must verify after the fact that it did not change bodies.
- Contrary evidence: each text transform verifies exact preservation, and the cost stays at authoring time.

**G-4. Program-set and facade registries are hand-kept in parallel.**
- Principles: FP-03; DP-01; H27.
- Sites: `native_protocol_sources`, `native_sql` order, `capture_native_authoring_inputs` module list, `target_native_definitions` table (with the stale `scientific_layout.sql` key), `_NATIVE_OUTPUTS` zip, `__main__` path restatements.
- Consequence: adding a program means editing three to five lists. The facade zip checks length, not correspondence.

**G-5. Model facts restated in generators beyond relation and column names.**
- Principles: FP-02; DP-01.
- Sites:
  - task-state literals versus the modeled lifecycle (about 37 sites);
  - the DDO value codec vocabulary from Python `Literal`s plus a hand `_TEXT`;
  - four field-kind type maps;
  - payload JSON keys;
  - DuckDB hand schemas and companion column lists;
  - about 160 free `func.<schema>.<name>` callees across the sampled 17 generators.
- Contrary evidence: relations and columns resolve against compiled metadata and fail at generation. The SourceValue codec checks its closed set against LinkML.

**G-6. Repeated whole-set regeneration with no content-keyed memo.**
- Principles: FP-07; A4; H on reuse.
- Sites: `native_protocol_sources()` default callers (A4), at least two rebuilds per preview, and the import-time double compile in `semantic/metadata.py`.
- Consequence: slower previews and CLI preparation commands. The cost grows with every converted owner.
- Contrary evidence: it is not on deployment, admission or read paths, and the wire protocol already caches by content.

**G-7. DuckDB kernels restate their inputs by hand, and two production entry points are dead.**
- Principles: FP-02; FP-07; DP-16.
- Sites: `analytical_kernels.py:21-62`, `pdf_candidate_geometry.py:60-72`, `pdf_stream_reconciliation.py:235-243`, `companion_export.py:419-589`, and the `disagreements`/`fuse` functions with no production caller.

---

## Scope B. Remaining hand-written SQL; DA-079 and DA-080

(SQL inventory below integrates the sub-lane's report, checked against the snapshot.)

**Search method.**
- `find` for `*.sql`, then a grep of every file stem and of the generic loaders (`with_name("sql")`, `files(`, `read_text`/`read_bytes`, `rglob`/`glob`).
- An AST scan of every module for `text(`, `exec_driver_sql`, SQL literals and f-strings, SQL `.replace`, string `.sql/.execute`, and pglast parses.
- Detection is lexical, so lowercase or heavily fragmented SQL may be undercounted. "Live" means reachable by import from the assembly hubs (`data_operation_storage.py:64-123`, `target_installation.py`). Runtime profile selection was not traced.

### B1. Inventory and classification

**`.sql` files in `src/corpus_structure/semantic/sql/` (16 files, 1,293 lines).**

- **Loaded and deployed: 10 files, about 88 KB. All still-maintained hand SQL.**

  | File | Size | Loader |
  |---|---|---|
  | `admission.sql` | 22.5 KB, 186 lines | `native_products.py:390` → parsed in `native_admission_release.py:74`, spliced in `native_admission.py:415-444` |
  | `data_operation_source_admission.sql` | 22 KB | `data_operation_source_native.py:43-72`, `__DDO_SOURCE_CAPTURE_PROGRAMS__` replaced |
  | `data_operation_visual_read.sql` | 11.8 KB | `data_operation_visual_read.py:100-111`, `__VISUAL_ARTIFACT_SCHEMA__` replaced |
  | `closure.sql` | 9.2 KB | `target_installation.py:28-34`. Its docstring calls these "maintained primitive programs" |
  | `identity.sql` | 7.5 KB | `target_installation.py:28-34` |
  | `source_originals.sql` | 4.2 KB | `original_document_contracts.py:126-214`, `__SOURCE_ADMISSION_ASSET__` replaced |
  | `source_record_recognition.sql` | 3.9 KB | `target_installation.py:104-107` |
  | `contextual_neighborhood.sql` | 3.2 KB | `data_operation_storage.py:498`, `contextual_neighborhood.py:77` |
  | `data_operation_task_checks.sql` | 2 KB | `data_operation_protocol.py:125`, spliced at a comment marker |
  | `pdf_descriptor.sql` | 1.2 KB | `target_installation.py:93` |

- **No loader: 6 files, about 30 KB, 285 lines. Converted and dead.**
  - `validation.sql` (104 lines), `exclusions.sql` (102), `data_operation_identity.sql` (34; its header says "Deliberately unregistered"), `source_record_graph.sql` (29), `selection.sql` (8) and `fact.sql` (8).
  - Their last loaders were removed in `47dc7b873`, `29f569875` and `c98046a8d`.
  - They still enter `compilation_fingerprint` (suffix `.sql`, `schema/model_change.py:390-397`) and the change explanation's `rglob` (`schema/model_explanation.py:423-456`).

**Hand SQL in Python (still maintained and deployed).**
- In total: 13 `*_native.py` modules (A2, G-1), plus `data_operation_cpu_basis.py` (12.4 KB r-string, `:463-543`) and `execution_evidence_leaf.py` (4.1 KB).
- Mixed modules:
  - `published_document.py`: Core `Select` bodies wrapped in f-string `CREATE FUNCTION` (`:372`).
  - `pdf_integrated_native.py:42-46`: hand ALTER/REVOKE/GRANT.
  - `target_installation.py`: guard trigger at `:43` and trigger f-strings at `:330-386`.
  - `data_operation_storage.py:1929,1954`: trigger prefixes.
  - `companion_projection_native.py`: `pin_guard_sql` f-string template.
  - `alembic_privileges.py:567-589`: the admission comparison.
- Taken together with the loaded `.sql` files, this is roughly **260 KB of still-maintained hand PostgreSQL** reaching deployment.

**Small hand SQL that is trivially convertible.**
- `evaluate/operation_fitting.py:539-594`: `SELECT eval.*(...)` call text through `text(`.
- Catalog, lock and `set_config` plumbing in `storage_target.py`, `migrations.py`, `native_sql_body.py` and `core/db/extensions.py:17`.

**Converted and dead Python.**
- `semantic/published_address_migration.py`: no importer in `src` or the migrations; only `tests/.../test_published_address_migration.py` uses it.
- `rich_relations.disagreements` / `fuse` (A5).

**Legitimate exceptions (independent controls).**
- `schema/model_deployment.py:921,963`: `observe_admission`.
- `semantic/execution_admission.py:102-140`: `DO $deployment_catalog$` and prosrc digests.
- The catalog introspection parts of `native_authoring.py` and `alembic_indexes.py`.
- `unicode_identity.py`: a qualification probe.
- These read the catalog independently of the generators. That independence is their purpose (DP on independent verification), so keeping them hand-written is principled.

**Outside ADR-0131's PostgreSQL scope.**
- Hand **SQLite** SQL for local stores and exports, about 4.4 KB in total:
  - `serve/selected_source.py` (18 `.execute`)
  - `pdf_payload_validation.py` (11)
  - `data_operation_read_index.py` (10)
  - `pdf_certification.py` (9)
  - `serve/demand_export.py` (8)
- The operator's goal ("application code kept away from writing SQL text") covers these too.
- Inference: DuckDB or SQLAlchemy Core over SQLite could hold them.

**DuckDB.** No SQL strings remain (A5).

**Shell and provisioning.**
- `scripts/pg_provision.sh` (148 lines) and `scripts/pg_semantic_roles.sh` (59 lines) contain no SQL. They run statements that `python -m corpus_structure.core.db.host_bootstrap` renders from pglast `CreateRoleStmt` / `GrantRoleStmt` / `CreatedbStmt` nodes and Core `select`. Classification: generated.
- `ops/postgresql/` (checked at `d78c98765` through git) holds `corpus.conf` and `extensions.txt` only. The `justfile` has no SQL.
- Test-harness Python in `scripts/` does carry hand SQL:
  - `native_test_support.py:451-664`: f-string `CREATE DATABASE … TEMPLATE`, `DROP`, `GRANT`, `ALTER ROLE`.
  - Smaller amounts in `pgtap_batch.py`, `native_auth.py` and `native_scenario_seeds.py`.
  - This is test infrastructure (test-audit scope).

**Frozen migration trees.**

| Tree | Revisions | Head / status | Content |
|---|---|---|---|
| `target_alembic/` (353 MB) | 31 | Root `semantic_ddo_current_root` (`down_revision=None`), head `semantic_tdm_pdf_stream_protocol`. **Deployed:** `semantic/migrations.py:14` sets `ALEMBIC_DIR = …/"target_alembic"`. It is also read as the S40 predecessor witness (`schema/data_step_programs.py:72-80`). | Each revision `.py` verifies the hashes of three frozen artifacts: `*_upgrade.txt` (`op.native_transition({...})` payloads, 1.9–8.9 MB each), `*_native.json`, and a generated `*_admission.sql` (30 files, 16 MB). Raw `op.execute` appears only in the 4 earliest roots (`DO $target_database$ … GRANT/REVOKE`). |
| `semantic_alembic/` (1.8 GB on disk) | 285 | Head `semantic_ddo_domain_v9`. **No path reference** in `src`, `tests` or `scripts`. It was switched out in `e6b99719b`, and only the version-table name `semantic_alembic_version` survives (`migrations.py:15`). | 257 `*_admission.sql`, 19 physical, 9 reconciliation and 9 kernel files (about 124 MB of SQL). 13 revisions use hand f-string `op.execute`. |
| `alembic/` | 3 (phase 0) | No loader found. | Not examined. |

`target_alembic` is a legitimate frozen exception with a consumer. `semantic_alembic` and `alembic/` are frozen trees **without a consumer**. ADR-0131 preserves frozen migrations, but these two are superseded machinery under the design-stage removal rule. Evidence and plans are protected from deletion; migration trees are not named in that rule.

**Submitted read-only SQL.**
- Owner: `semantic/authored_sql.py` (`admit_sql`, `:219`), reached from `ci db describe --query` (`cli/db.py:390-411` → `serve/database_description.py:176-198`). It also admits release-authored `authored/*.sql` SELECTs (`releases.py:584`).
- Validation uses pglast, not SQLGlot:
  - exactly one `SelectStmt` (`:157-168`);
  - a visitor allowlist of nodes, functions, types and operators, with INTO and locking refused (`:120-154`);
  - every relation must resolve to `MetaData` (`:175-180`);
  - PostgreSQL then binds names and types with `EXPLAIN (FORMAT JSON)` under a READ ONLY, REPEATABLE READ transaction, with `search_path=pg_catalog` and the restricted login (`:184-216`, `:274-279`);
  - describe only takes the output schema through ADBC (`database_description.py:468`).
- `query_knowledge` takes typed JSON, not SQL (`intervene/rich_query_tools.py:35`).
- SQLGlot is used for analysis only (`projection_analysis.py`; `model_explanation.py:362` diff).
- Classification: legitimate exception, and a sound design.

**Summary classification.**
- Still-maintained hand SQL, deployed: 10 `.sql` files plus about 21 Python modules.
- Converted and dead: 6 `.sql` files, `published_address_migration.py`, and the two unconsumed migration trees.
- Legitimate exceptions: `target_alembic`, the independent catalog controls, and `authored_sql`.
- Out of scope but within the operator goal: SQLite SQL in 5 modules.

### B2. DA-080: status at `d78c98765` (partly corrected)

| Group (as in DA-080) | Now | Evidence |
|---|---|---|
| 14 unreferenced `semantic/sql/*.sql` | **10 deleted**: `characterization`, `current_operation_guards`, `definition_declaration`, `native_finalization`, `record_policy`, `record_references`, `source_anchor_coordinates`, `source_record_coordinates`, `source_record_report`, `split_decisions`. **4 remain unreferenced** (`exclusions`, `fact`, `selection`, `validation`). **2 more became unreferenced** (`source_record_graph`, `data_operation_identity`). Total 6. | `ls semantic/sql/`; grep of `<stem>.sql` over `src`, `tests` and `scripts` found no loader. |
| Stale `scientific_layout.sql` dispatch | **Unchanged.** | `target_installation.py:230`, `:236`. |
| Evaluation modules | **Unchanged.** `evaluate/equivalence.py`, `affine.py`, `artifact_pilot.py`, `sampling.py`, `split_decisions.py`, `split.py` and `sets.py` are all present. No production importer; `split.py` is imported only by `split_decisions.py:16`. | grep over `src`. |
| Rendition keying / translation | **Unchanged.** `core/keys.py`, `core/translations.py` and `core/candidates.py` are present. `KeyContext` is referenced in `src` only by a `core/candidates.py:9` docstring. | grep over `src`. |
| Earlier pack loader | **Unchanged.** `schema/pack.py` and `schema/lookup.py` are present. Outside `schema/`, only the `DOMAINS` path constant is imported (`orchestrate/project.py:149`, `source_operation.py:41,111`), the same as at `fbd3f2a98`. | `git show fbd3f2a98:` of the importers. |
| New in this window | Converted-and-dead `published_address_migration.py`; the unconsumed `semantic_alembic/` and `alembic/` trees; production-dead `rich_relations.disagreements`/`fuse`. | B1, A5. |

Conclusion: the SQL-file group improved substantially (14 → 6 files, 1,980 → 285 lines). The other three groups are unchanged, and the conversion added new dead items. The finding stays open.

### B3. DA-079: status at `d78c98765` (unchanged)

- `orchestrate/execution_host.py:89-92` still acquires `_run_lock` non-blocking and raises `RuntimeError("process execution host already has an active run")`.
- `intervene/native_render_tools.py:93` still converts only `ValueError`, `KeyError` and `OSError` (`@tool_refusals`).
- `git log fbd3f2a98..d78c98765` shows no commits to either file.
- No typed busy refusal exists: a grep for `busy|HostBusy` over `orchestrate`, `intervene` and `data_operation_service.py` found nothing.
- The finding's consequence and limits stand as written. Overlap is still inferred, not observed.

### B4. Scope B findings (diagnostic)

**S-1. Still-maintained hand PostgreSQL reaches deployment outside ADR-0131's three exception classes.**
- Principles: FP-02, FP-03; A2; DP-16.
- Scale: about 260 KB, made up of 10 `.sql` files and about 21 Python modules, including the admission kernel, the closure and identity foundation, source admission, the visual read, and the cpu basis.
- Several of these are spliced by text markers.
- This is the same root as G-1. Record it as one finding with the SQL inventory as evidence.

**S-2. Converted-and-dead SQL and migration machinery remain and still count as inputs.**
- Principles: FP-01, FP-03; DP-01; H27.
- Six dead `.sql` files sit in the preview fingerprint and the change explanation.
- `semantic_alembic/` (285 revisions, 1.8 GB) and `alembic/` have no consumer.
- `published_address_migration.py` survives only for its test.
- This continues DA-080. It belongs as a delta on DA-080, not a new finding.

**S-3. Application SQL text outside PostgreSQL (SQLite stores) is unowned by ADR-0131.**
- Principles: A2; the operator goal.
- Five modules, about 56 `.execute(str)` sites.
- Uncertainty: I did not judge whether these stores should move to DuckDB, to Core, or stay.

---

## Uncertainties and limits

- I sampled only the generator bodies named in A2. The "free callee", "state literal" and "role literal" counts are regex counts and include some benign matches.
- I did not determine which hand PL/pgSQL bodies reference relations or columns (and so carry propagation risk) and which only manipulate JSON.
- The cost claims (A4, G-6) are static, with no measurement. Whether preview latency is material is unknown.
- `semantic_alembic/` might be wanted as historical recovery. That is the operator's decision; only its lack of a code consumer is established here.
