# CACHES: map of current code for the cache system (R09), DuckDB (R12/F03), SQLite (F04/RC02), retirement (R13), F02

Baseline: frozen snapshot of `cb4e09667` (production source equal to `5139eaba3`). Paths are relative to
`snap7/python/corpus-structure/` unless marked `root:` (under `snap7/`). `S/` = `src/corpus_structure/`.
Read in full: `cache-design.md`; review sections R07 table, R09, R12, R13, §5 DuckDB table, F02-F04 rows.
Facts are from source (path:line); inference is marked "inferred". The snapshot has no `uv.lock`, no
`pyproject.toml` at `root:`, no `domains/`, no `build/` (they exist only in the live tree, not read).

## 0. Facts that change the shape of the cache work

1. All process pools and workers use **spawn**; there is no fork: `S/semantic/cpu_execution.py:697`
   (`multiprocessing.get_context("spawn")`, `ProcessPoolExecutor(mp_context=…)` at :724),
   `S/semantic/pdf_publication.py:662`, `S/ingest/pdf_worker.py:141`, `S/ingest/pdf_chandra.py:258`.
   Subprocess hosts (`Popen`): `S/methods/native_host.py:140`, `S/ingest/pdf_recognition.py:497`,
   `S/semantic/source_navigation.py:143`, `S/cli/recipes.py:75`. Children start with empty caches.
2. MCP tool calls: FastMCP servers (`S/intervene/semantic_server.py:56`, `external_server.py:68`,
   `server.py`, `selected_assessment_server.py:49`) register 40 `@server.tool` functions and only 3
   `async def` exist under `intervene/`; the tools are synchronous, so FastMCP runs them on worker threads
   (`S/intervene/mcp_observations.py:11` says so: "carries this context into sync tool threads").
3. The math grammar (the F02 named holder) **refuses off the main thread**: `require_main_thread()` raises
   `OffMainThread` (`S/methods/math/grammar.py:517-519`), called at entry of `parse` (:1005), `syntax` (:1086),
   `syntax_forest` (:1112), `deadline`/`_deadline` (:469, :513) and in `S/semantic/formal_forest.py:416`,
   `scientific_evidence.py:1027, 1244`, `formal_products.py:909`, `evaluate/affine.py:68`,
   `evaluate/equivalence.py:119`. Every reader of `_PARSERS`, `_FOREST_PARSERS`, `_MEMO`,
   `_STANDALONE_CONTEXTS` that I traced (`parser_for` callers :1033, :1094, :1175; `forest_parser_for` :1119 and
   `formal_forest.py:557`) sits under one of those guards. I did not find a path where an MCP worker thread
   mutates them (the callers of `_interpret_reading` :1175 were not all traced). F02's "tool threads reach them"
   is therefore "likely, not observed" and in source is closer to "refused by construction on the grammar's own
   entry points". The holders are still unlocked and unbounded (`_PARSERS`/`_FOREST_PARSERS`), and `_MEMO` is a
   hand `OrderedDict` capped at `MEMO_SIZE = 8192` (:103).
4. `SelectedQueryCache` stores `DerivedRows` encoded with **pickle** (`S/semantic/selected_query_cache.py:9,
   132-156`; class docstring says pickle is used to keep exact Decimal scale and float kinds). The design's D4
   (disk result pages) says canonical JSON lines and "never pickle" (`cache-design.md` §6): the disk row encoding
   is a different codec from today's in-process entry bytes, so D4 is not a file dump of T4 entries.
5. `AnalyticsSettings` fields read nowhere (grep over `S/`, `tests/`, `root:scripts/`): `capture_mode`, `batch_size`,
   `resident_limit_bytes`, `threads`, `memory_limit`, `scratch_path` (`S/settings.py:129-139`). Read:
   `adbc_driver_path` (`serve/companion_export.py:139`, `serve/database_description.py:236`) and
   `batch_size_hint_bytes` (`serve/companion_export.py:178`). No cache settings of any kind exist in `settings.py`.
6. No production caller of any `cache_clear()`/`cache_info()`; only tests (section D).
7. `ALEMBIC_DIR` is `target_alembic/` (`S/semantic/migrations.py:14`); nothing in `S/`, `scripts/`, `tests/`
   reads `semantic_alembic/` or `alembic/` as a directory (section F-iii).

## A. Per-tier holders today

Counts over `S/` (exhaustive grep): 96 `@lru_cache`/`@cache` decorators (23 of them unbounded `@cache`/
`@functools.cache`), 2 inline `lru_cache(maxsize=256)(…)` (`S/semantic/pdf_payload_validation.py:32`,
`S/semantic/pdf_record_reader.py:268`), 78 `@cached_property`, 1 cachetools `LRUCache`. Size classes: S small
value, M compiled model/validator/grammar, P program set, H open file/connection, W weights/pipeline, T Arrow table.

### T0 custody (kept, generalized)

| Holder | path:line | Key / bound | Size | Callers | Threads / processes |
|---|---|---|---|---|---|
| file custody `_records`, `_observed` | `S/semantic/file_custody.py:79, 96` | `(path, digest)` / path; unbounded; one `RLock` `_lock` :80 | S | `verified_file`/`observed_file` 28 refs in 16 files | locked; any thread; per process; worker receives receipt via `accept_file_receipt` :132 |
| query custody `_EXECUTED` | `S/_query_custody.py:134` | module to `(path, digest)`; import-time loader; `_EXPECTED` ContextVar :135 | S | `install()` :198; hand module lists :17-127; used by `installed_read_implementation` (`S/serve/rich_queries.py:109`) in 9 serve/semantic files | `_EXECUTED` unlocked, written only inside import execution; refuses reload |
| other hand lists to replace | `S/semantic/demand_queries.py:117-124`, `S/semantic/pdf_lowering.py:33-104`, `S/semantic/data_operation_storage.py:184-191` (capture reads module bytes fresh from disk) | | | | |

### T1 compiled model (and what it absorbs)

| Holder | path:line | Key / bound | Size | Callers | Notes |
|---|---|---|---|---|---|
| physical `MetaData` module globals `PHYSICAL_MODEL_ID`, `metadata`, `tables`, `SCHEMAS`, `_read_metadata`, `table()` | `S/semantic/metadata.py:32-50, 53-58` | none; compiled at import (2 `compile_physical` calls :33, :46) | M | 19 modules import it at module scope, 59 imports are inside functions, 64 files in all by my pattern (audit says 63); `metadata.table(...)`/`.tables`/direct refs: 240 refs in 71 files; 109 test files import it | any importer pays the compile; the CLI's own commands import it lazily (`cli/schema.py:457`, `cli/operations.py:501`) |
| 13 `SchemaView(` sites | `schema/physical.py:191`; `semantic/rule_views.py:402`; `conditional_rules.py:178`; `native_call_sources.py:111, 117`; `ontology.py:159, 260, 626`; `prepare.py:362, 374`; `companion_projection.py:552`; `source_value_native.py:56`; `projection_analysis_products.py:98, 107`; plus earlier-model `schema/pack.py:232`, `schema/model.py:235` | none | M | | the design lists eight composers; code shows four merge-routines (`prepare.py:350-374`, `native_call_sources.py:95-117`, `projection_analysis_products.py:85-107`, `companion_projection.py:552`) and single-purpose views |
| `compile_physical(` sites | `schema/model_change.py:505, 689, 1096`; `semantic/pdf_record_model.py:86`; `companion_projection.py:587`; `pdf_publication_native.py:460`; `data_operation_storage.py:137, 1877`; `pdf_lowering.py:193`; `data_operation_source_native.py:30`; `projection_analysis_products.py:141`; `data_operation_projections.py:2745`; `authored_sql.py:350`; `metadata.py:33, 46` | none (`schema/physical.py:166` uncached) | M | 17 sites | |
| wire protocol caches | `S/semantic/data_operation_wire.py:47 (ambient content, 1), 53 (prepare, 16), 262 (checked, 16), 489 (prepared protocol, 16), 525 (ambient, 1), 560 (validator, 256)` | whole captured `SourceArtifact` tuple or content bytes | M | `_prepared_protocol` 2 refs; 7 test `cache_clear` calls reach them (`tests/semantic/test_data_operation_wire.py`) | content-keyed, sound; key requires hashing the capture tuple |
| companion projection (added recently) | `S/semantic/companion_projection.py:71 (`installed_projection_id`, 4), 547 (`projection`, 4, key includes `target_metadata` object), 561 (`_captured_projection_inputs`, 4), 620 (`captured_projection`, 8)`; 6 `cached_property` | PDF domain contract (content) | M | 4 files import it | composes own view :552 and compiles physical again :587 |
| no-arg process singletons reading package files | `S/semantic/pdf_contracts.py:81 (`trusted_pdf_context`, 13 refs in 9 files)`, `pdf_lowering.py:107, 259`, `operation_reporting.py:63, 93, 118`, `pdf_records.py:33, 159, 165, 198`, `pdf_staging.py:118`, `serve/selected_source.py:39`, `declared_math_analysis.py:68`, `data_operation_model.py:1219`, `data_operation_admission.py:99` | none (`maxsize=1` or `@cache`) | M | | "first read in the process wins" |
| scientific recipe | `S/semantic/scientific_evidence.py:58 (`_scientific_model` 4), 66, 133, 333, 192-255`; `rich_policy_binding.py:22-30` | content bytes | M | | R14 owns the derivation |
| earlier-model `cached_property` on `View` | `S/schema/stage_b.py` (11), `schema/model.py:223`, `schema/rulelang.py:219` | per object | M | | die with the earlier model (R13) |

### T2 program set (no holder today)

`native_protocol_sources()` (`S/semantic/data_operation_storage.py:48-575`) has no decorator. About 46 generator calls
(inferred from audit DA-083) and reads of ~110 files per call. Nothing holds the result. Callers are in section B.
Existing disk artifacts that hold program text: `target_alembic/versions/` (185 files: 46 `.json`, 46 `.sql`,
46 `.txt`, 47 `.py`).

### T3 releases and archives

| Holder | path:line | Key / bound | Size | Callers | Threads |
|---|---|---|---|---|---|
| `_prepare_release_cached` | `S/semantic/prepare.py:600` (`lru_cache(8)`; `prepare_release` :571) | `(bundle, dependencies, profile, stack)` | M, up to 8 artifact sets | `prepare_release(` 15 refs / 14 files (`releases.py:318, 502`; `model_change.py:755, 908`; `pdf_lowering.py:195`; `pdf_contracts.py:57`; `analysis_policies.py:156`; `scientific_evidence.py:63`; `operation_reporting.py:122`; `serve/selected_source.py:45`; `regeneration.py:354`; `data_operation_preparation.py:539`; `cli/schema.py:187`; `cli/model.py:1538`) | `lru_cache` is structurally thread-safe, no single-flight |
| `_boundary` (PDF boundary release) | `S/semantic/pdf_contracts.py:55` (16) | `SourceBundle` | M | 3 refs / 2 files | same |
| `_prepared_lowering_sources` | `S/semantic/pdf_lowering.py:168` (4) | boundary sources | M | | same |
| archive open cache `_OPEN_CACHE` | `S/semantic/archive_reader.py:34-40` (`WeakKeyDictionary[engine -> OrderedDict]`, cap 8 per engine at :429, `_CACHE_LOCK` RLock), filled at :394-434 inside `open_archived_release_inputs` :371 | `(tuple(archive header), runtime versions)` per engine object | M (prepared release) | `open_archived_release_inputs` reached via `semantic/releases.py:426` (`load_release`) and `archive_reader.py:368` | locked; CLI creates one engine per command (`open_runtime_engine` 61 refs / 23 files), so the cache never hits across commands; MCP holds one engine per purpose for the lifespan (`S/intervene/runtime_engines.py:9-55`) |
| CPU worker releases `_WORKER_RELEASES` | `S/semantic/cpu_execution.py:226`; `_worker_release` :150 hydrates from shared memory | `"shared-capsule:" + sha256(reference)` | M | worker only | spawned worker process, task runs on its main thread (receipt records `main_thread` :219); unbounded within worker life; ADR-0125 owner |
| execution host bases | `S/orchestrate/execution_host.py:46` (`_bases` `OrderedDict`, byte budget), `_PROCESS_HOST` :468 with `_PROCESS_LOCK` | verified basis key | H/M | `execution_host_scope()` used by CLI root callback (`S/cli/app.py:21-24`) and MCP lifespan (`runtime_engines.py:26`) | one per process |
| engine/pool holders | `S/semantic/runtime.py:75 (`open_runtime_engine`)`, `S/core/db/store.py:170 (psycopg pool + NullPool engine)`, `S/intervene/runtime_engines.py:7-55` (`McpRuntimeEngines._engines` per purpose) | purpose | H | | |

### T4 served results

| Holder | path:line | Key / bound | Size | Callers | Threads |
|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`SelectedQueryCache`, `LRUCache(maxsize=32 MiB, getsizeof=len(key)+byte_size)`, hand cap `max_entries=128` via `popitem` loop) | `S/semantic/selected_query_cache.py:15-86` (`RLock` :60); constants :15-19; `bounded_rows` :122-160 (entry ≤ 8 MiB, ≤ 4,096 rows) | `json_bytes([kind, cut.identity, implementation, …])`, e.g. `S/semantic/demand_queries.py:198-212`, `S/serve/rich_queries.py:224` | rows as pickle bytes | `.get`/`.put`: 12 refs in 6 files: `semantic/demand_queries.py:213, 232`; `serve/rich_queries.py:226, 259`; `identity_exclusion_comparison.py:156, 177`; `contribution_facets.py:264, 278`; `interpretations.py:208, 336`; `structural_products.py:283, 326`. Also `tests/conftest.py:103-111` clears it per test; `tests/semantic/test_selected_query_cache.py` | locked, no single-flight; MCP worker threads and CLI |
| read-basis identity | `S/serve/rich_queries.py:66 (`_library_version`, `@cache`), :71 (`_installed_read_basis`, 64)` | `(contract, sources, profile, extra_libraries)` | S | `installed_read_implementation` :109 called from 9 files (rich_queries, identity_exclusion_comparison, contribution_facets, selected_structural, selected_structural_review, structural_products, interpretations, demand_queries, tests) | |
| rich graph index per query; change-impact comparison per page | `S/serve/rich_queries.py:222-262` (`RichQueryIndex` built inside the miss path); `S/semantic/change_impact.py:506-510, 687-777` | not cached beyond the T4 entry | M | | |
| scalar result views | `cached_property` `S/semantic/demand_results.py:86` (4), `native_source_view.py:128-212` (11) | per object | S | | die with object |

### T5 CPU runtimes

| Holder | path:line | Key / bound | Size | Callers | Context |
|---|---|---|---|---|---|
| spaCy pipeline | `S/ingest/sentences.py:58` (`@functools.cache`, unbounded) | `SentenceConfig` | W | 3 refs in 3 files (`ingest/hosted_spacy.py`, `semantic/sentence_products.py`, `sentences.py`) | long-lived process |
| spaCy vocab and matchers | `S/semantic/constructions/retained_rules.py:32 (1), 191 (4), 257 (1), 1216 (4)` | `Vocab` object | W | | |
| Lark prototype and grammar resource | `S/semantic/constructions/forest.py:36 (`_grammar_resource`, unbounded `@cache` returning `observed_file`), 83 (`_grammar_prototype`, 64)` | `(grammar, resource_digest)` | M | `_grammar_prototype` 1 ref; tests `tests/semantic/test_construction_grammar_custody.py:92, 108` clear it | |
| GLiNER compiled pack | `S/methods/native_host_adapters.py:111` (nested `lru_cache(64)` inside the host adapter function) | pack | M/W | | lives in the spawned native-host subprocess (`methods/native_host.py:140`) |
| CPU encoder | `S/methods/contextual_embeddings.py:356` (`lru_cache(1)`) | `(profile, model_path, artifact_hashes)` | W | | |
| CPU descriptors | `S/semantic/data_operation_cpu.py:189` (64) | content | S | `_load_descriptor` 2 refs | per CPU worker; tests clear it (`tests/semantic/test_definition_cpu_authority.py:34-36`) |
| installed policy | `S/methods/model_observation.py:36` (`@cache`) | none | S | 2 refs | |
| GPU residency (stays) | `S/methods/native_host.py:646-944` (`NativeHostResidency`: `Condition`, idle timer, quarantine); constructed at `S/orchestrate/execution_host.py:300-304`; `NativeHostGroup` `native_host.py:448` also built at `semantic/hanlp_products.py:381`, `sentence_products.py:711`, `methods/native_host_clients.py:50`, `ingest/hosted_spacy.py:90`, `characterization_resources.py:612` | | H/W | | own lifecycle |

### T6 memos

| Holder | path:line | Key / bound | Locked? | Reached from |
|---|---|---|---|---|
| `_PARSERS`, `_FOREST_PARSERS` | `S/methods/math/grammar.py:309-327` | `classes.key`; unbounded dicts | no | main thread only (section 0 item 3) |
| `_MEMO` | `grammar.py:966, 1014-1022` | `(latex, kind, table key, ctx key)`; `OrderedDict`, 8,192 | no | same |
| `_STANDALONE_CONTEXTS` | `grammar.py:980-993` | `(table key, kind)`; 8,192 | no | same |
| `_classify`, `_shipped`, `drop_ignore` | `grammar.py:181, 227, 235` (`@functools.cache`) | | built in | |
| formal grammar | `S/semantic/structural_parsing.py:57 (len(FIELD_STARTS)), 94, 104, 175`; `formal_evidence.py:295, 313, 350 (16), 374` | | built in | |
| per-instance report cache | `S/semantic/pdf_record_reader.py:587-625` (`OrderedDict` in `__dict__`, 256) and `:268` (inline `lru_cache(256)`) | `local_id` | no | instance lifetime |
| per-instance validator | `S/semantic/pdf_payload_validation.py:32` | | | instance lifetime |
| external-packet holder | `S/semantic/data_operation_external.py:148-150` (`OrderedDict` with `_packet_lock`) | | locked | |

Unlocked mutable module-level state found (exhaustive grep for module-level `dict/OrderedDict/list = …` and `global`):
`grammar.py:309, 310, 966, 980`; `_query_custody.py:134` (import time); `cpu_execution.py:226-229` (spawned worker);
`ingest/pdf_capacity.py:19-20, 43` (GPU quarantine); `cli/observation_logging.py:55` (`_ROUTES`, has `_ROUTE_LOCK` :43);
`orchestrate/execution_host.py:469-476` (has `_PROCESS_LOCK`). Only the grammar group is a memo in the F02 sense.
Other unbounded long-lived holders: `ingest/sentences.py:58`, `semantic/constructions/forest.py:36`,
`grammar.py:309-310`, `file_custody._records`, `_WORKER_RELEASES`.

### Keep as `functools` (small pure memos; design §7)

Spot-checked, not all 96 read: `S/semantic/types.py:165` (512), `refusals.py:70`, `finite_interpretation_products.py:125, 134`,
`unicode_identity.py:44, 59`, `contextual_numerics.py:72`, `contextual_neighborhood.py:53`, `core/batch.py:119`,
`ingest/pdf.py:178`, `cli/app.py:25, 51`, `serve/rich_queries.py:66`, content-keyed parsers
(`alias_policy.py:113`, `reference_positions.py:31`, `comparison_projection.py:176`, `projection_analysis.py:454`,
`m1_products.py:47`, `python_module_projection.py:110`, `data_operation_model.py:1206`,
`data_operation_static_preparation.py:66`, `execution_admission.py:270, 348, 378, 405`, `declared_math_products.py:128`,
`pdf_payloads.py:398, 415`, `analysis_policies.py:152, 161`, `data_operation_admission.py:65, 108`).
Note `execution_admission.py:405` keys on `(path, digest, mtime, ctime)`, an object-stat key.

## B. Repeated work the tiers remove

All counts from exhaustive grep over `S/`.

- **`native_protocol_sources()` with no argument**: 9 literal call sites. `serve/demand_export.py:281`;
  `semantic/primary_operations.py:403`; `semantic/data_operation_preparation.py:261`;
  `semantic/data_operation_storage.py:707, 713, 764, 883, 1018, 1857`. Five of them are `if sources is None` fallbacks
  inside `_protocol` :704, `native_source_digest` :712, a projection :764, `native_operation_declarations` :878,
  `native_operation_calls` :1012. The audit counts eight; the difference is how the :713 default is counted (inferred).
  With arguments: `semantic/regeneration.py:331`, `semantic/native_products.py:110`, `data_operation_storage.py:1865`.
- **`native_source_digest()` with no argument**: `data_operation_storage.py:1139, 1142, 1571`. Each rebuilds the capture.
- **Execution path**: `require_data_operation_native` (`data_operation_storage.py:1127-1142`) calls it twice per call;
  called from `semantic/data_operation_admission.py:285` (port acquisition), `:354` (cached-port recheck), `:390`
  (publication port), and `data_operation_storage.py:1561` (definition admission, then :1571: three rebuilds). Reached from
  `orchestrate/data_operations.py:718, 754, 784` (inferred from audit DA-083; not re-traced). The SQL guard already
  compares an archived digest (`semantic/native_admission_release.py:531`, audit fact).
- **Authoring path**: preparation `data_operation_preparation.py:261`; regeneration `regeneration.py:331`; native products
  `native_products.py:110`; primary operations `primary_operations.py:403`; candidates `data_operation_storage.py:1857, 1865`;
  demand export `serve/demand_export.py:281`.
- **Model-change preview** (`S/schema/model_change.py`): `compilation_fingerprint` :322 and `generator_fingerprint` :313;
  `acquire_data_operation_inputs` :350, :603 (which reaches `data_operation_preparation.py:261`); `compile_physical`
  :505, :689, :1096; `_native_facades` :525-552 (called :705) via `capture_target_installation`; `prepare_release` :755, :908.
  The preview also depends on the earlier model (`model.load`, `change.diff`, :622-660). Facade generation includes
  `generated_wire_source` (`data_operation_wire.py`).
- **Compiled model rebuilds**: section A T1 (17 `compile_physical` sites, 13 `SchemaView` sites, 2 import-time compiles).
- **Archive reopen**: `open_archived_release_inputs` (`archive_reader.py:371`) per `load_release`; cache keyed by engine
  object (:394, :422); `activate_release` (`semantic/releases.py:569`) calls `load_release` then
  `admit_data_operation_release` (the capture paths above).
- **Read snapshots**: `read_snapshot(`/`selected_read_snapshot(` 24 refs in 16 files (`semantic/read_snapshot.py:19`,
  `semantic/demand_results.py:52, 417-431`); each borrows a `REPEATABLE READ` read-only connection; the CLI
  `ci query` path opens `open_runtime_engine` then `engine.begin()` per command (`S/cli/selected_results.py:99-112, 122-126`).
- **CLI start**: `S/cli/app.py:main` builds only the selected command family (`build_command_app` :53-70); `root` :20-24
  enters `execution_host_scope()` per command. `semantic.metadata` is compiled only when first imported by one of 19
  module-scope importers (list in the table row above), by the lazy imports at `cli/schema.py:457`,
  `cli/operations.py:501`, or by a serve/semantic module that imports them.

## C. On-disk tiers: what exists

- **Paging in the CLI**: `ci query NAME` (`S/cli/selected_results.py:25-135`; `--cursor`, `--limit`, `--max-bytes`, rich
  names with `--parameters`), `ci … contributions` (`selected_results.py:~350-413`, `--cursor`, `--read-id`, `--cut-id`
  → `expected_cut`). Each opens `open_runtime_engine(…, purpose="read")` and a snapshot, so a page is a new process,
  engine, pool, snapshot and release open. Other paged commands pass a native continuation JSON file: `cli/demands.py:108-131`,
  `cli/status.py:73-102`, `cli/orchestrate.py:353-372`, `cli/visual_route.py:21-39`, `cli/source.py:320`;
  integer `--after` pagers in `cli/testing.py`, `cli/model.py` (`--after`, `--after-hunk`), `cli/observations.py`,
  `cli/recipe_output.py:96`. Files importing a cursor: `cli/{visual_route,observations,source_inspection,selected_results,source,status,orchestrate,schema,managed,model}.py`.
- **Where the cut rides**: the cursor is opaque and built in serve code; the cache key already contains `page.cut.identity`
  (`S/semantic/demand_queries.py:198-212`; `S/serve/rich_queries.py:224`: `["rich", selected.cut.identity, implementation, reference, selection]`),
  and the rich cursor carries `reference` and `ordinal` (`rich_queries.py:215-222`). Authority is rechecked per request
  before cache lookup (module docstring of `selected_query_cache.py`). I did not trace the encoding of the cursor in `semantic/demand_results.py:431-473`.
- **Generated program sets written today**: frozen per-revision artifacts under `target_alembic/versions/` (185 files, 46
  revisions with `*_native.json`, `*_admission.sql`, `*_upgrade.txt`, `*.py`); `cli/schema.py` `native-candidate --out build/native-candidate`
  (help text `cli/schema.py:641`) and `publish_native_candidate` (`cli/schema.py:629`); preview writes into
  `TemporaryDirectory(prefix="cs-model-preview-")` (`schema/model_change.py:622`); `cs-schemas-` (`schema/generate.py:602`);
  `ci-model-migration-` (`schema/model_deployment.py:566`); `ci-native-base-` (`semantic/migration_chain.py:144`).
  Where a D2 store would read: `acquire_data_operation_inputs` and `native_protocol_sources` callers (section B).
- **State conventions to reuse**:
  - `build/` under the checkout: `build/ci/` managed results (`cli/managed.py:1131-1143`, `CORPUS_CI_RESULTS` override via
    `Settings.ci_results`), `build/ci/.model-writer.lock` (`schema/preparation.py:20-23`, `fcntl.flock(LOCK_EX)`),
    `build/data`, `build/models` (`settings.py:102-103`), `build/recognition` (:119), `build/tmp/analytics` (:138, unread).
  - `ResultStore` (`cli/managed.py:490-530`): root created mode 0700, uid/mode check (`st_uid`, `0o022`), `.namespace` flock,
    32-hex result ids, `_write_file` with `O_EXCL` temp + `os.replace` through a dir fd (:178-190), `O_NOFOLLOW` reads
    (:171-175). It is invocation-scoped (ids are random), not content-addressed.
  - atomic write helpers: `ingest/pdf_streaming.py:30-41` (`xb` temp, `fsync`, `replace`, dir `fsync`), `ingest/pdf_chandra_document.py:44`,
    `schema/model_change.py:1129-1137` (`NamedTemporaryFile` + `os.replace`), `serve/demand_export.py:403`/`selected_structural_review.py:141`
    (`root.rename(destination)` of a hidden temp dir), `ingest/pdf_assets.py:119-128`.
  - flock users: `ingest/pdf_capacity.py:61`, `ingest/pdf_build_spool.py:151-157, 453`, `cli/managed.py:504, 540, 569, 697, 980`.
  - content-addressed naming: only `serve/demand_export.py:228` (`source-artifacts/<digest>.bin` inside one export), and
    `ingest/pdf_build_spool.py`/`pdf_stream_types.py:47` (spools keyed by build, not store-wide). No general
    content-addressed store, no `cache_store`, no user cache directory convention (`ingest/pdf_methods.py:35` uses `~/.cache/docling/models`, a library default).
  - "Manifest with per-file digests": `FileCustody` (`semantic/file_custody.py`) re-hashes on stat change and refuses; no equivalent for directories.

## D. Settings and invalidation hooks

- Settings: `S/settings.py`; `Settings(BaseSettings)` :208-240 with sections `database`, `deployment`, `paths`, `llm`,
  `nemotron`, `gpu`, `analytics`, `characterization_execution`, `runtime`, `ci_results`. Env prefix `CORPUS_`, nesting `__`,
  `extra="forbid"`; every section extends frozen `_Section` :57-58. `PathSettings` :99-103; `AnalyticsSettings` :129-139
  (six unread fields, section 0 item 5). No cache section. "Settings are built once at an entry point (the `ci` callback, the MCP
  lifespan) and passed down" (module docstring :3-5); `settings_report` lists unmatched `CORPUS_*` names. Two modules read
  `PathSettings()`/`NemotronSettings()` directly: `semantic/hanlp_products.py:381, 541`, `semantic/sentence_products.py:711`.
- Events and where they occur in code:
  - release activation: `S/semantic/releases.py:569` (`activate_release`; SQL `sem.activate_release` :558); caller `S/cli/operations.py:621`.
  - release archive publication: `S/semantic/archive_native.py:72` (`publish_release_archive`); PDF publication `S/semantic/pdf_publication.py:163`,
    `S/cli/schema.py:629` (native candidate).
  - model-change apply: `S/schema/model_change.py:1106` (`apply_preview`, under `preparation.writer_lock`); CLI `S/cli/model.py:1725`.
  - model/kernel deployment: `S/schema/model_deployment.py:678` (`deploy_candidate`); CLI `S/cli/model.py:2126`. Kernel descriptor
    check `require_data_operation_native` (`data_operation_storage.py:1127`).
  - revocation: a database fact (native tables and guards, e.g. `semantic/change_impact.py:332 _revocation_causes` computes
    causes in Python; `established_validity.py:334 revoke(...)` is generated SQL grant revocation, unrelated). No Python function publishes a revocation event.
  - These all run in the CLI process that performs the command; the long-lived MCP server does not run apply or deploy (those are `ci model …`
    commands), so an in-process event from them reaches only the same short-lived process (inferred; the MCP servers register read tools,
    `intervene/semantic_server.py` docstring "Expose current pinned readers").
- Existing `cache_clear()`/`cache_info()` callers: production none. Tests: `tests/semantic/test_data_operation_wire.py:39-40, 57-58, 70-71, 96, 292`;
  `test_operation_reporting.py:314, 325-326`; `test_prepare.py:528, 559`; `test_data_operation_ports.py:1301-1393` (also asserts
  `cache_info().hits/misses` on `_prepared_python_sources`); `test_definition_cpu_authority.py:34, 36`;
  `test_construction_grammar_custody.py:92, 108`. `tests/conftest.py:103-111` clears `SELECTED_QUERY_CACHE` per test (fixture
  `clear_selected_query_cache`). These seven test files would have to follow any holder replaced by a `cached(...)` wrapper (8.0 wrappers
  expose `cache_clear` and, only with `info=True`, `cache_info`).

## E. cachetools move

- Pin: `python/corpus-structure/pyproject.toml:65` `"cachetools==7.2.7"`. `uv.lock` is not in the snapshot (it is at the repository root in the live tree).
  `docs/pins.md` also not in the snapshot.
- Imports (exhaustive grep): one: `S/semantic/selected_query_cache.py:12` (`from cachetools import LRUCache`); API used: `LRUCache(maxsize, getsizeof)`,
  `.get`, `.popitem`, `.maxsize`, `len`, `in`, `__setitem__`, `.clear`. The string `"cachetools"` appears as a distribution name at `S/serve/rich_queries.py:81`.
- Identity that includes the version: `_installed_read_basis` (`S/serve/rich_queries.py:71-100`) hashes `libraries` = pydantic, **cachetools**,
  pydantic-core, python-rapidjson, regex, PyYAML, jsonschema, referencing, jsonschema-specifications (+ networkx for `relations_between`),
  plus `unicodedata.unidata_version`, source digests and the query contract schema. The bump changes this digest once for every served-read
  implementation identity (9 callers of `installed_read_implementation`), and with it every cache key and outstanding cursor that embeds it.
  `semantic/determinants.py:34-36` lists `BOUNDARY_LIBRARIES`, `DEPLOYMENT_LIBRARIES`, `ANALYSIS_LIBRARIES`: none include cachetools, so release,
  deployment and analysis identities do not move.
- Tests that touch it: `tests/semantic/test_query_custody.py:153, 162`, `tests/semantic/test_selected_structural_readers.py:35-39` use
  `installed_read_implementation`; I found no literal hash of the read basis in tests (grep `"implementation"` hits are unrelated).

## F-i. DuckDB (R12, F03)

Modules importing duckdb (exhaustive): `serve/companion_export.py`, `semantic/artifact_identity.py`, `semantic/rich_relations.py`,
`semantic/analytical_kernels.py`, `ingest/pdf_stream_reconciliation.py`, `ingest/pdf_candidate_geometry.py`.

| Connection site | Config literal today |
|---|---|
| `serve/companion_export.py:410` and `:552` (`duckdb.connect()`) | library defaults (no threads, memory, time zone, temp dir) |
| `semantic/artifact_identity.py:481` and `:579` (`duckdb.connect()` for Splink `DuckDBAPI`) | library defaults |
| `semantic/rich_relations.py:71-77` (`RichRelationKernel`) | `threads`, `memory_limit` constructor args; `temp_directory` = fresh `TemporaryDirectory(prefix="corpus-rich-")` :68; caller `semantic/rich_consolidation.py:405-412` passes `threads=1`, `memory_limit="2GB"` |
| `ingest/pdf_stream_reconciliation.py:301-305` | `memory_limit="2GB"`, `temp_directory=str(path.parent / "sort-scratch")`, `threads=1` |
| `ingest/pdf_candidate_geometry.py:87` | `config={"threads": 1}` only |

No `TimeZone` setting anywhere (grep `TimeZone`/`SET threads`/`pragma` over `S/`); `AnalyticsSettings.threads/memory_limit/scratch_path` unread.
Settings defaults today: `threads=4`, `memory_limit="2GB"`, `scratch_path="build/tmp/analytics"` (`settings.py:136-138`).
Hand-declared Arrow schemas (`pa.schema(`, exhaustive): `serve/native_source.py:944`; `serve/demand_export.py:76`; `semantic/pdf_publication.py:455`;
`semantic/rich_relations.py:24, 27` (`RICH_MEANINGS`, `RICH_FUSION_INPUT`); `semantic/analytical_kernels.py:18 (helper), 54, 60`;
`semantic/companion_projection.py:528`; `semantic/archive_transport.py:68`; `semantic/pdf_record_model.py:108`;
`ingest/pdf_stream_reconciliation.py:36, 235`; `ingest/pdf_candidate_geometry.py:60`; `semantic/pdf_payloads.py:345, 421`.
Review calls out as operation-local: `pdf_candidate_geometry.py:60-72`, `pdf_stream_reconciliation.py:233-241`, `analytical_kernels.py:21-60`;
entity attributes `("id","key","types","label","symbol")` at `analytical_kernels.py:62`.
Two kernels with no production caller: `disagreements` (`semantic/analytical_kernels.py:150`, `rich_relations.py:112`) and `fuse`
(`analytical_kernels.py:170`, `rich_relations.py:115`); callers are `tests/semantic/test_rich_relations.py:40, 52, 64, 163-186` only.
`RICH_MEANINGS` and `RICH_FUSION_INPUT` serve only these methods (inferred from grep; used in `rich_relations.py` `_checked` calls).
`FileRelation`: defined `semantic/capture_storage.py:78`; the only other reference is `tests/semantic/test_capture_storage.py:9, 48`.
Certification folds (I8): SQLite staging `FrozenPayloadStore` (`semantic/pdf_payload_validation.py:51-68`, `sqlite3.connect`) feeds ordered folds in
`semantic/pdf_certification.py:241` (`SELECT body FROM entry WHERE family='artifact_stream' ORDER BY key COLLATE BINARY`) and `:330`
(`ORDER BY family COLLATE BINARY,key COLLATE BINARY` over `identity_frame`, filled at :235-236). Key-ordering condition in the review: DuckDB's
default string comparison must equal `COLLATE BINARY` (this review says "verify once"); both are string keys (`key` text, `family` text). Companion
sites in the same module use `IdentityFold` (:241-250). Nothing else in `S/` uses COLLATE on SQLite.

## F-ii. SQLite SQL text (F04, RC02)

Modules with `sqlite3.connect` (exhaustive): `semantic/data_operation_read_index.py:53`, `semantic/pdf_payload_validation.py:58`,
`serve/selected_source.py:476`, `serve/demand_export.py:158`. Plus `semantic/pdf_certification.py` (uses `FrozenPayloadStore.db`, no own connect).
Execute-call counts (`.execute(`/`.executemany(`/`.executescript(`): `serve/demand_export.py` 12; `serve/selected_source.py` 19;
`semantic/data_operation_read_index.py` 13; `semantic/pdf_payload_validation.py` 15; `semantic/pdf_certification.py` 10 = 69 raw. The review counts
58 execute sites and "59 lines" in five modules; I did not reconcile (some raw hits may not be SQLite, or the review's module set differs).
Concatenated statements: `data_operation_read_index.py:22-25` (`"json_extract(payload, '$.record." + field + "')=?"` and `"SELECT … AND " + predicates`),
`:72-79` (`CREATE INDEX record_` + joined field names + expression); `pdf_payload_validation.py:151-168` (WHERE assembled from fragments and
`",".join("?" …)` placeholders, values bound; no field-name interpolation); no f-string SQL found in the five.
Field names come from a fixed tuple at `data_operation_read_index.py:63-69` and constructor args `fields` (caller-supplied in `__getitem__` :19-30).
No SQLAlchemy over SQLite exists today.

## F-iii. Retirement (R13): state at this commit

| Item | Exists? | Importers / consumers (exhaustive grep over `src`, `tests`, root `tests`, `scripts`) |
|---|---|---|
| `model/core.yaml` (1,096 lines), `system.yaml` (2,023), `revisions.yaml` (1,118) | yes | loaded by `schema/model.py:235`; `revisions.yaml` carries `alembic_revision` fields (e.g. `:64, 119, 162`) and `system.yaml:434` defines the field |
| `core/vocab.py` (1,123) | yes | 40 `src` files, 37 test files by my pattern `core.vocab`/`from .vocab` (includes core-internal and `schema/*`); audit's wider pattern says 41 |
| `core/_model/*` (7 files, 2,219 lines) | yes | 11 `src`, 5 test files |
| `core/keys.py` (1,473) | yes | `evaluate/equivalence.py`, `methods/math/scope.py`, `methods/math/spans.py`, `schema/lookup.py`, `semantic/alias_policy.py`; 8 test files; rendition keying with `core/translations.py`, `core/candidates.py`, `KeyContext` |
| `schema/change.py` (490), `schema/pack.py` (481), `schema/lookup.py` (545), `schema/model.py` (718) | yes | `change`: `schema/model_change.py`, `schema/preparation.py` (+2 tests); `pack`: `orchestrate/project.py`, `orchestrate/source_operation.py`, `schema/lookup.py` (+14 tests, pattern may over-match `from .pack import`); `lookup`: no `src` importer (2 tests); `model`: 16 `src` incl. `cli/model.py`, `cli/schema.py`, `schema/model_change.py`, `schema/model_deployment.py`, `semantic/arrow_types.py`, `semantic/companion_projection.py`, `semantic/native_call_sources.py` (+38 tests) |
| `domains/statistics/schema/statistics.yaml` | not in snapshot (no `domains/`); `model_explanation` and tests name the "statistics" pack (`tests/schema/test_model_explanation.py:167`) | |
| `semantic/native_call_generation.py:106` facade emitting `core.vocab.TaskUnitType` | yes | listed under `semantic/native_call_generation.py` in `core.vocab` importers |
| `evaluate/equivalence.py` (351) | yes | no `src` importer; `tests/evaluate/test_equivalence.py` |
| `evaluate/affine.py` (240) | yes | none; `tests/evaluate/test_affine.py` |
| `evaluate/artifact_pilot.py` (250) | yes | none; `tests/semantic/test_artifact_identity.py:433-463` |
| `evaluate/sampling.py` (113) | yes | none; `tests/evaluate/golden/test_sets.py:10`, `tests/semantic/test_trace_reference_fixture.py:11` |
| `evaluate/split_decisions.py` (94), `split.py` (140) | yes | `split` imported by `split_decisions` only (`semantic/prepared_sql.py` match is pglast `split`); tests `evaluate/test_split_decisions.py`, `evaluate/golden/test_split.py`, `tests/math/test_scope.py` |
| `evaluate/sets.py` | yes, one docstring line | no importer, no test |
| `evaluate/operation_fitting.py` (604) | yes | **whole module has importers**: `selected_operation_events.py:34` (types) and `declared_operation_events.py:425, 441` (`fit_operation_event`), plus 3 test files. The native fitting path is `read_native_frame` :530, `fit_native_operation_event` :552, `read_native_fit` :585: 3 functions, no caller in `src`, `tests`, `scripts`; they select `eval.operation_event_fit_frame`, `eval.read_operation_event_fit`, `ops.read_operation_event_parameters`, defined only in `semantic_alembic/versions/*` (grep: 3 files), none in `target_alembic`. The module is also named in the hand boundary list `declared_operation_events.py:46-57` (`_PATHS`) |
| `semantic/analytical_kernels.py:150, 170`, `semantic/rich_relations.py:112, 115`, `FileRelation` | yes | section F-i |
| six unloaded `.sql` files, `semantic/sql/` | gone (no `semantic/sql` in snapshot) | `schema/model_explanation.py:413-460` still builds the root `PACKAGE_PATH / "semantic" / "sql"` |
| `semantic/published_address_migration.py` | gone | |
| `pdf_shape_guard_sql` (`semantic/pdf_contracts.py:578-588`) | file present (588 lines) | not re-verified for callers |
| release-side authored SQL (`semantic/authored_sql.py:299-369`, `semantic/native_admission_release.py:461-500`) | yes (527, 859 lines) | `admit_archived_sql`, `prepare_release_sql`, `analyze_release_sql` still called by `releases.py:569-` (`activate_release`) and `schema/model_deployment.py:678-` |
| `methods/llm/producer.py` (58), `agent_opus.py` (54) | yes | `producer`: only `tests/ingest/test_managed_recognition.py:11`; `agent_opus`: none |
| `semantic/unicode_identity.py:233-246` parity check | yes (246 lines) | caller not searched |
| `capture_sql_changes` (model preview SQL explanation) | yes `schema/model_explanation.py:413-460` | runs `git ls-files/ls-tree/show` over `PACKAGE_PATH/semantic/sql` plus `domains/<pack>`; called `cli/model.py:1465-1468`; tests `tests/schema/test_model_explanation.py:146-200`, `tests/test_cli_model_inspect.py:679`. Because the directory no longer exists the result is empty (inferred) |
| `semantic_alembic/` | yes, 1,013 files in `semantic_alembic/versions` + `env.py`, `script.py.mako` | **no code, script or test reads the directory**. Greps for the name outside `docs/` and the trees themselves find only the database table `public.semantic_alembic_version` (`S/semantic/migrations.py:15 VERSION_TABLE`; `semantic/target_installation.py:855`; `cli/db.py:489-491`; `root:scripts/native_test_support.py:1183-1191`; tests `test_database_description.py:423-447`, `test_pdf_record_native.py:166`, `test_releases.py:213-217`, `test_current_native_lifecycle.py:251-254`) and `root:tests/scripts/test_native_deployment_key.py:170` which **asserts** the deployment key's `chain` has no `semantic_alembic/` entries. `chain=ALEMBIC_DIR` (`root:scripts/native_test_support.py:907`; `test_native_deployment_key.py:156`) is `target_alembic` via `S/semantic/migrations.py:14`. The deployment key hashes `.py`/`.mako` of the chain (`root:scripts/native_deployment_key.py:132-135`), not `semantic_alembic`. Historical docs only: `docs/design/D3-database.md:413` etc. |
| `alembic/` | yes: `script.py.mako` + `versions/0001..0003` | no reader found (only the pip library `alembic==1.20.1`, `pyproject.toml:8`, used by `semantic/alembic_*.py`, `native_authoring.py`, `migrations.py` against `target_alembic`). `model/revisions.yaml` still names revisions `'0002'`, `'0003'` as `alembic_revision` of earlier-model change records (`:64, 119`) |
| `target_alembic/` | **live** (185 files) | `semantic/migrations.py:14`, `schema/data_step_programs.py:72`, `native_authoring.py`; not part of R13 |

Cautions: the alembic library (pinned) and `semantic/alembic_{checks,defaults,indexes,native,privileges,environment}.py` are live (authoring and
`target_alembic`), so R13 retires directories, not the library. `ChangeRecord.alembic_revision` (`schema/change.py`, `model_change.py:164, 652`)
is the field linking earlier-model change records to `alembic/` and `target_alembic` revision ids.

## Scanned exhaustively vs sampled

Exhaustive (grep over `S/`, `tests/`, root `tests/`, `scripts/`): `lru_cache`/`@cache`/`cached_property` decorators and inline calls; `cachetools`;
`cache_clear`/`cache_info`; `OrderedDict|WeakKeyDictionary|RLock|Lock(|global`; module-level mutable dicts; `Thread|ThreadPoolExecutor|ProcessPoolExecutor|get_context|Popen`;
`duckdb|pa.schema(|sqlite3.connect|COLLATE`; `SchemaView(`, `compile_physical(`, `native_protocol_sources(`, `native_source_digest(`;
`semantic_alembic`, `alembic` outside docs; `SELECTED_QUERY_CACHE`; `AnalyticsSettings` fields; importers of each R13 module (patterns above; counts
differ by up to a few from the audit's wider pattern).
Sampled or inferred: which cache is touched by each MCP tool (derived from the synchronous-tool fact, not traced tool by tool); the 55 "cheap" memos
(spot-checked ~35); `cached_property` roles (78, listed by file counts and a keyword sample); DA-083 execution-path rebuild counts (taken from the audit,
call lines re-read for `data_operation_admission.py` and storage only); cursor encoding in `semantic/demand_results.py`; exact SQLite statement count;
callers of `unicode_identity` parity check and `pdf_shape_guard_sql`; whether apply/deploy ever runs inside an MCP server (inferred no).
Not read: `uv.lock`, `docs/pins.md`, root `pyproject.toml`, `domains/`, `build/` (absent from the snapshot).

## Summary table: tier or item to holders, callers, context, what migration touches

| Tier / item | Holders today | Callers | Thread / process context | Migration touches |
|---|---|---|---|---|
| T0 custody | `file_custody.py:79-96` (locked), `_query_custody.py:134` + hand lists `:17-127`, `demand_queries.py:117-124`, `pdf_lowering.py:33-104`, capture reads `data_operation_storage.py:184-191` | 28 custody refs / 16 files; 9 `installed_read_implementation` callers | locked; refuse reload; workers get receipts | derive module closure; test seam `test_query_custody.py` |
| T1 compiled model | `metadata.py:32-58` globals; 13 `SchemaView` sites; 17 `compile_physical` sites; wire caches `data_operation_wire.py:47-560`; companion `companion_projection.py:71-620`; 20 no-arg singletons | 64 importers (19 module-scope), 240 refs; 109 test files | any thread, every process incl. CLI; spawned workers rebuild | move `metadata` consumers to accessor; 7 test files calling `cache_clear` on wire/report/prepare holders; model-change preview |
| T2 program set | none; `native_protocol_sources` 9 no-arg sites, `native_source_digest()` 3 | admission `:285, :354, :390`, storage `:1561`, authoring 6 sites, `model_change.py` ~4 paths | execution path (MCP threads, CLI) and authoring (CLI) | R06 removes execution-path callers; `tests/semantic/test_data_operation_ports.py` (`_prepared_python_sources` stats) |
| D2 program store | `target_alembic/versions` frozen files; temp dirs `cs-model-preview-`, `build/native-candidate` | `cli/schema.py:629`, `cli/model.py` preview | CLI only | new `cache_store` (reuse `ResultStore` 0700/flock/`os.replace` pattern); no CAS exists |
| T3 releases/archives | `prepare.py:600`, `pdf_contracts.py:55`, `pdf_lowering.py:168`, `archive_reader.py:34-40, 371-434`; engine holders `runtime_engines.py`, `store.py:170` | `prepare_release` 14 files; `load_release` | `lru_cache` safe, no single-flight; archive cache locked, per-engine so CLI never hits | key change to database identity; PE-F16 residual |
| T4 served results | `selected_query_cache.py:15-86` (pickle rows, RLock) | 6 serve/semantic files, 12 get/put refs; `tests/conftest.py:103` | MCP worker threads and CLI; no single-flight | `SizedLRU`, future single-flight, ServedKey (authorization scope, basis); 6 key builders; D4 needs a non-pickle codec |
| D4 result pages | none; CLI page = new process (`cli/selected_results.py:25-135`, 5 other cursor CLIs) | `ci query`, contributions, interpretations | CLI | new store; rechecks authority first |
| T5 CPU runtimes | `sentences.py:58`, `retained_rules.py:32/191/257/1216`, `forest.py:36/83`, `native_host_adapters.py:111`, `contextual_embeddings.py:356`, `data_operation_cpu.py:189` | few (1-3 each) | long-lived main/MCP process; native-host and CPU workers are spawned | bytes-bounded declare; GPU residency and worker releases stay |
| T6 memos / F02 | `grammar.py:309-327, 966-993`; `pdf_record_reader.py:587-625` | grammar: `parse`/`syntax`/`syntax_forest` | main-thread only by guard (`grammar.py:517`); unlocked, unbounded parsers | convert to `cached(..., condition=...)`; `tests` for grammar custody |
| `functools` stay | ~55 pure memos (96 decorators total, 23 unbounded) | | | none |
| Owner module + settings | none (`settings.py` has no cache section; `AnalyticsSettings` 6 unread fields) | | | new `CacheSettings`; events at `releases.py:569`, `model_change.py:1106`, `model_deployment.py:678`, `archive_native.py:72`; 0 production `cache_clear` |
| cachetools bump | pin `pyproject.toml:65` = 7.2.7; one import `selected_query_cache.py:12` | | | read-basis digest `rich_queries.py:71-100` changes once (cachetools in `libraries`); cursors refuse once |
| R12/F03 DuckDB | 8 connect sites (4 default, 3 literal limits, 1 with temp dir arg); 14 `pa.schema` sites | 6 modules | CLI exports; MCP only via rich kernel | wire `AnalyticsSettings`; model-derived entity attrs `analytical_kernels.py:62`; retire 2 kernels + `FileRelation` (tests `test_rich_relations.py`, `test_capture_storage.py`) |
| I8 certification fold | `pdf_payload_validation.py:51-68` SQLite staging; `pdf_certification.py:241, 330` `COLLATE BINARY` | certification path | CLI/publication | move to DuckDB sort; verify binary ordering equality |
| F04 SQLite | 4 connect modules + certification; 69 raw execute sites; concatenation at `data_operation_read_index.py:22-25, 72-79` | | per-request scratch | Core `Table` declarations; RC02 scope |
| R13 earlier model | `model/{core,system,revisions}.yaml`, `core/vocab.py`, `core/_model`, `core/keys.py`, `schema/{change,pack,lookup,model}.py` | 40/11/5/2/3/0/16 `src` importers; 37/5/8/2/14/2/38 test files | | move importers to released types; `model_change.py` preview depends on it; `cli/model.py`, `cli/schema.py` |
| R13 evaluate/LLM/dead | 7 `evaluate/*` modules, `operation_fitting.py:530-620`, `methods/llm/{producer,agent_opus}.py` | no `src` importers (except `operation_fitting` module-level); tests for each except `sets`, `agent_opus` | | delete modules with tests; keep `operation_fitting` types and `fit_operation_event`; drop `_PATHS` entry if module retired |
| R13 migration trees | `semantic_alembic/` (1,013 files), `alembic/` (3 versions) | none read them; `target_alembic` is `ALEMBIC_DIR` | | delete dirs; keep `semantic_alembic_version` table name; `test_native_deployment_key.py:170` assertion becomes vacuous; docs refs only |
| Preview SQL explanation | `model_explanation.py:413-460` | `cli/model.py:1465`; 2 test files | CLI | retarget to two generated-SQL snapshots; tests `test_model_explanation.py:146-200` |
