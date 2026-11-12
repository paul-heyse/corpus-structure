# Native (PostgreSQL) test preparation lifecycle map

Baseline: `main` at `784d86f11`, clean tree. Read-only. No tests, no DB operations, no timing.
Paths are relative to `/home/paul/corpus-structure`. Abbreviations: `NTS` = `scripts/native_test_support.py`;
`PC` = `python/corpus-structure/tests/conftest.py`; `SC` = `python/corpus-structure/tests/semantic/conftest.py`;
`T` = `python/corpus-structure/tests/semantic/`. "Counted" = obtained by search or AST scan at baseline; test counts are
test-function definitions, not parametrize-expanded cases, unless stated.

Facts below are about the code. Lines marked **Obs.** are observations for the reviewer; none is a remedy.

---

## 1. The lifetime ladder as implemented

xdist: root `pyproject.toml:46-55` sets `-n auto --dist=loadgroup --max-worker-restart=0`. Every pytest "session" fixture below is
therefore one instance **per worker process**; names embed `os.getpid()`. The only `xdist_group` marks under the two test trees
are in `tests/math` preparation (root `conftest.py:27-37`) and the harness self-tests; none groups native-DB tests (search:
`grep xdist_group` over both test trees). `shared_cluster_fault` controls must run serially (`conftest.py:40-50`).

### Rung 0 - cluster template `cs_template` (not a test fixture)
- Created and marked `IS_TEMPLATE true` by `scripts/pg_provision.sh:~111-137` (extensions of `ops/postgresql/extensions.txt` only).
  Tests only check it: `PgAdmin.check()` `NTS:501-536` (`exists` + `installed()` which connects *to* `cs_template`, `NTS:495-499`).
- `semantic_bare_engine` (`SC:37-45`), `semantic_database_at` (`SC:48-57`) and `semantic_template` (`NTS:617`) clone it directly.

### Rung 0b - per-worker server session `native_server` (session, `PC:242-252`)
Per worker: `PgAdmin(...)` constructor resolves four purpose URLs (`NTS:145-155`), `check()` (2 maintenance connections: `names` then
`installed` on `cs_template`), `semantic_principals()` = `subprocess.run(bash scripts/pg_semantic_roles.sh --principals)` (`NTS:120-128`),
`check_roles` (1 connection, `NTS:252-262`), `sweep()` (1 connection held across all candidates, `NTS:554-610`), and
`record_server_context` (only when a receipt sink is active, `NTS:758-782`). Not dropped (no state).

### Rung 1 - per-process frozen head template `semantic_head_template` (session, `PC:255-260`)
- Creator: `PgAdmin.semantic_template(name)` `NTS:612-630`, name `cs_sem_head_<pid>_<hex12>`.
- Structure: `database(name, cs_template)` (full acquisition, no policy replay) -> one `engine.begin()` transaction: extension check
  query, namespace-absent assertion, Alembic `upgrade(conn)` to head (chain = 240 Python revisions, `ls
  python/corpus-structure/semantic_alembic/versions | grep -c`; DTA-024 quotes 240) -> `engine.dispose()` -> `self.policy(name)`
  (1 connection, 3 SELECTs) -> `ALTER DATABASE ... ALLOW_CONNECTIONS false IS_TEMPLATE false` (1 connection). Yields
  `SemanticTemplate(name, policy)` (frozen dataclass of owner, connection limit, ACL tuple, settings tuple; `NTS:99-118`).
- "Sealed" = connections disallowed and *not* marked `IS_TEMPLATE` (`NTS:627-629`). Nothing ever connects to it again; policy is read from
  the `postgres` database "never ... a connection to a clone source" (`NTS:264-265`).
- Dropped when the generator exits (`database()` cleanup, `NTS:478-493`) -> `_drop` with authenticated `OwnedDatabase`.
- Sweep recognises it by regex `cs_sem_(head|test|bare|revision|init)_\d+_[0-9a-f]{12}` (`NTS:587-591`); lock key = full name.

### Rung 1b - per-process session clones and seeds
| Fixture | Scope | Name | Source | Notes |
|---|---|---|---|---|
| `db_engine` (`PC:279-285`) | session | `ci_test_<pid>` | head template + policy | maintenance login; consumers 14 test functions in 4 files (AST count) |
| `serving_scenario_seed` (`T/serving_scenarios.py:288-297`) | session | `cs_sem_test_<pid>_<hex12>` | head template + policy | see section 3.9 |
| `semantic_head_template` | session | above | cs_template | |

### Rung 2 - per-test clone (function scope)
| Fixture | File:line | Name | Source | Policy replay |
|---|---|---|---|---|
| `semantic_db_engine` | `SC:27-34` | `cs_sem_test_<pid>_<hex12>` | head template | yes |
| `committing_db` | `PC:295-303` | `ci_test_<pid>_<n>` (`itertools.count`, `PC:276`) | head template | yes |
| `semantic_bare_engine` | `SC:37-45` | `cs_sem_bare_...` | `cs_template` | no (extensions-only; asserts no `sem/data/kb/meta` namespaces) |
| `semantic_database_at(rev)` | `SC:48-57` | `cs_sem_revision_...` | `cs_template` | no; runs `upgrade(conn, revision)` (real chain) |
| `semantic_absent_database` | `PC:263-267` | `cs_sem_init_...` | none (`reserved`, `NTS:417-441`) | only a leased absent name; drops only if CREATE was acknowledged |
| `serving_read_scenario` | `T/serving_scenarios.py:300-344` | `cs_sem_test_...` | the serving seed | yes, with seed's policy |
- All function clones come out of `PgAdmin.database()` (`NTS:443-493`): lease -> exists -> CREATE -> (replay) -> engine. The yielded
  engine is the **maintenance login** (superuser per `pg_provision.sh:106-110`, `CREATE ROLE ... LOGIN SUPERUSER CREATEDB CREATEROLE`)
  with `NullPool` (`NTS:460`) - every checkout is a new physical connection.
- Consumer counts (AST scan of `def test*` signatures, both trees): `semantic_db_engine` 419 functions/131 files; `semantic_writer_engine` 305/91;
  `semantic_reader_engine` 117/56; `semantic_evaluator_engine` 38/14; `semantic_admitter_engine` 3/2 plus `admitter` alias 10/3;
  `semantic_bare_engine` 19/9; `semantic_database_at` 5/5; `semantic_absent_database` 3/1; `db` 4/3; `db_engine` 14/4; `committing_db` 1/1.
  (4119 test functions in total in the two trees.) A test that requests only a purpose engine gets the clone transitively
  (`SC:60-101` depend on `semantic_db_engine`). `semantic_application_settings` (`PC:233-239`) also depends on it (14 functions/9 files).
- Marker side effect: `pytest_collection_modifyitems` adds `db` to any item whose fixturenames intersect `DB_FIXTURES` (`PC:71-88,122-138`).
  Autouse `refuse_unbound_application_target` (`PC:189-200`) sets `CORPUS_DATABASE__URL` to a refused sentinel per test, for every test.

### Purpose-role engines (function scope, `SC:60-101`; `NTS:633-649`)
- `principal_engine(settings, purpose, database)`: resolves credentials via `connection_settings(settings, purpose)`
  (`src/corpus_structure/semantic/runtime.py:21-65`) against the *original* session `Settings` (`native_settings`, `PC:183-186`), swaps only
  the database name, `create_engine(..., poolclass=NullPool)`, attaches `observe_engine`. No connection is opened at fixture time.
- Writer = base URL principal (`write` returns `settings` unchanged, `runtime.py:36-37`); reader/evaluator/admitter resolve to
  `corpus_sem_reader|evaluator|admitter` unless the settings declare URLs (`runtime.py:38-45`).
- Authentication: Unix-socket `peer` with ident map `corpus_semantic` for the five semantic logins (`scripts/pg_semantic_roles.sh:90-103`);
  cluster is socket-only (`ops/postgresql/corpus.conf:5`). No password round-trip is involved by that route (the files state `peer`).
- Teardown: `engine.dispose()` in `finally` (`SC:66-68` etc.); because they depend on the clone fixture they are finalized first.
- Each test additionally opens, per `engine.connect()/begin()`: one new backend (NullPool). The maintenance engine and each
  purpose engine are separate pools, so a test using clone + writer + reader holds up to three engines' connections.
  Builders (section 3) open many sequential connections through these engines.

### Rung 3 - transactions and savepoints
- `rollback_connection` (`NTS:53-61`): one connection, outer `begin()`, always `rollback()`; used only by `db` (`PC:288-292`), whose
  `db_engine` is the session clone `ci_test_<pid>`. Direct `db` consumers (AST): `tests/test_db_fixtures.py` (1), `core/test_method.py` (2),
  `db/test_store.py` (1). So the shared rollback rung exists but 4 test functions use it (`db_engine`: 14 more).
- `begin_nested()` / `SERIALIZABLE` transactions rolled back by the test body appear only inside individual tests (section 4).

### Sweep recognition summary (`NTS:554-610`)
Selects `pg_database` rows whose name starts `ci_test_`, `cs_tpl_` or `cs_sem_`; requires `datdba = current_user` and an ownership comment
(`owned_comment`, `NTS:244-250`: legacy literal, `STAMP` regex, or `is_owned_stamp(comment, oid)`). `cs_tpl_*` additionally aged by
`TEMPLATE_RETENTION` (1 day, `NTS:47`). Lock key = full name for `cs_sem_*`/`cs_tpl_*`, **`ci_test_<pid>` (group 1 of `TEST_DB`, `NTS:45,592-595`) for `ci_test_*`**.
Skips a name if `pg_try_advisory_lock` fails (a live session's shared lease). Run once per worker at `native_server` setup.
- **Obs. (names escaping sweep):** `T/test_native_attributed_evidence.py:50-56` `cs_sem_m1_attributed_<hex12>`; `T/test_serving_scenario_lifecycle.py:39` `cs_sem_test_<hex20>`
  (no `_<digits>_`); neither matches the `NTS:587-589` regex (the DTA-030 note names only the first).
- **Obs. (lease key vs sweep key):** `committing_db` clones are `ci_test_<pid>_<n>` and `database()` leases the full name (`NTS:452`), but the sweep takes the
  exclusive try-lock on `ci_test_<pid>` (`NTS:595`), the key only `db_engine` holds. `tests/test_db_fixtures.py:124-152` exercises the sweep with fabricated names.
- **Obs. (`cs_tpl_` branch):** nothing in the repo creates `cs_tpl_` names (DTA-030; I did not re-search beyond `grep cs_tpl_`: only `NTS` and `tests/test_db_fixtures.py`).

---

## 2. What a clone needs after `CREATE DATABASE ... TEMPLATE`

### What `replay_policy` re-establishes (`NTS:306-371`)
`CREATE DATABASE` copies objects but not owner (ADR-0032 Context), ACL, connection limit, database settings or role-in-database settings.
Replay (maintenance connection, autocommit unless noted):
1. `ALTER DATABASE <clone> OWNER TO <source owner>`; `ALTER DATABASE ... CONNECTION LIMIT <n>` (`NTS:317-320`).
2. Read the clone's current policy (`before = self.policy(name)`, `NTS:321`) - a **second** connection while the first is open.
3. `SET ROLE <owner>`; for each distinct grantee in `before.grants`: `REVOKE ALL ON DATABASE ... FROM <grantee>`; for each source grant (grantable first):
   `GRANT <priv> ON DATABASE ... TO <grantee> [WITH GRANT OPTION]`; `RESET ROLE` (`NTS:322-337`). Refuses non-owner-granted ACL atoms (`NTS:312-313`).
4. A **transactional** connection (READ COMMITTED, `engine.begin()`): `SET LOCAL ROLE owner`; `ALTER DATABASE ... RESET ALL`; for each all-role setting
   `set_config(key,value,true)` + `ALTER DATABASE ... SET key FROM CURRENT` (2 statements each) (`NTS:340-352`).
5. For each distinct role named in `before.settings U policy.settings`: one transactional connection, `pg_has_role(current_user, role, 'SET')`;
   if authorized: `SET LOCAL ROLE role`, `ALTER ROLE ... IN DATABASE ... RESET ALL`, then 2 statements per role setting (`NTS:354-363,373-387`);
   otherwise `_replay_role_self` (`NTS:389-415`): a new engine **as that purpose login** against `postgres`, one transaction, `SELECT current_user,session_user`, same role-settings statements.
6. Final `self.policy(name)` (1 connection, 3 SELECTs) and `actual != policy` -> `AssertionError` (`NTS:367-371`).
`policy()` itself: 3 SELECTs (owner+limit; `aclexplode(COALESCE(datacl, acldefault('d',datdba)))`; `pg_db_role_setting`) (`NTS:264-304`).

What the repository declares as policy content: migrations contain `REVOKE TEMP ON DATABASE <current_database()> FROM PUBLIC, corpus_sem_writer, ...; GRANT TEMP ... TO corpus_sem_publisher`
(`semantic_alembic/versions/*.sql`, e.g. `semantic_0033_physical.sql`; grep of `ON DATABASE` over `semantic_alembic/versions` finds the same REVOKE/GRANT TEMP pattern in about ten files). `scripts/pg_provision.sh` and `scripts/pg_semantic_roles.sh` contain no `ALTER DATABASE ... SET`,
`ALTER ROLE ... IN DATABASE` or `CONNECTION LIMIT` (grep). So the set of database/role *settings* declared by the repo is empty; the live cluster was not inspected, so the number of
grantees/grants and roles-with-settings (G, N, R below) is **not established**.

### Statement/connection tally for one clone acquisition (`database(name, source, policy=p)`, `NTS:443-493`), ordinary path
Every `PgAdmin.connect()` builds a new `NullPool` engine, attaches the observer, opens one connection, disposes (`NTS:165-179`).
| Step | Connection(s) | Statements |
|---|---|---|
| `lease(name)` `NTS:538-545` | 1 (held for the whole fixture life) | 1 (`pg_advisory_lock_shared`) |
| `exists` -> `names` `NTS:181-190` | 1 | 1 |
| `create` `NTS:192-203` | 1 | 3 (`CREATE DATABASE`, ownership `SELECT`, `COMMENT ON DATABASE`) |
| `replay_policy` step 1-3 | 1 + 1 nested (`policy()`) | 2 ALTER + 3 SELECT + SET ROLE + RESET ROLE + G REVOKE + N GRANT |
| step 4 | 1 (transaction) | 2 + 2 per database-wide setting |
| step 5 | R (role checks) + R_self (role-self, different login) | 1 + (2 + 2 per setting) each |
| step 6 final `policy()` | 1 | 3 |
| `create_engine(clone)` | 0 (lazy) | 0 |
Fixed part with G=N=R=0: 7 connections, 17 statements, plus G+N revoke/grant statements. Of these 7, one (the lease) is deliberately long-lived; the policy-read connections open inside `replay_policy`
because `policy()` calls `connect()`. Teardown adds `_drop`: 1 connection, 2 statements (`SELECT` ownership row, `DROP DATABASE`) (`NTS:213-242`), then the lease connection closes.
Ordinary path totals: **7 acquisition connections + 1 drop connection** (R=0), each a fresh backend process on the dedicated cluster (NullPool, socket).
Inherently separate: the lease (session lock must outlive the other connections); `_replay_role_self` (authenticates as another login - only when `pg_has_role(..., 'SET')` is false; the maintenance login is a superuser per
`pg_provision.sh:106-110`, for which PostgreSQL reports membership true - this is external knowledge, not stated in the repo, and role settings are empty by repo declaration). The autocommit-vs-transaction split between steps 3 and 4 is by engine isolation level
(`NTS:172`), not a privilege boundary. The nested `policy()` and the final `policy()` are separate connections because `policy()` calls `self.connect()`.
No `STRATEGY` clause is given to `CREATE DATABASE` (`NTS:200`); the strategy is whatever the server default is (not stated in the repo).

### Receipt-enabled path (`native_context_active()`, `scripts/qualification_plugin.py:37-40`: a receipt sink exists)
Extra, per **physical connection of any observed engine** (every `PgAdmin.connect()` engine, the clone engine, every purpose engine; the role-self engine at `NTS:398` and psycopg pools are not observed unless patched like `PC:306-321`):
`observe_connection` (`NTS:677-755`) runs in the `connect` event: 1 SELECT (7 columns incl. subquery on `pg_database`), 1 `to_regclass('public.semantic_alembic_version')`,
and when that table exists and is readable 2 more (`has_table_privilege`, `SELECT version_num`); `connection.rollback()` if not autocommit; one JSON event line written and flushed (`qualification_plugin.py:44-48,51-64`).
Additionally `database()` opens one extra throwaway connection to the clone "so a real consumer has deployment observations" (`NTS:466-468`). On `postgres`-database connections `to_regclass` is NULL, so 2 statements; on clone connections 4.
Deployment/policy attribution: `_DEPLOYMENTS[key]` is filled only when the observed connection carries a `policy` (`NTS:722-723`), i.e. the clone engine's first observed connection.
Per-clone, receipt path = ordinary path + about 8 maintenance observations x 2 statements + 1 clone connection x 4 statements + JSON events (per connection), and every later connection the test or its builders open to the clone
or via purpose engines is observed the same way. (Counts of connections are structural; the ~8 is 7 acquisition + 1 drop.)

---

## 3. Fixtures and helpers that build committed scenario state on a clone

All function-scoped except the serving seed. All write through NullPool engines, one committed transaction per `begin()`.

| # | Builder | Defined | Commits (in order) | Consumers (counted) |
|---|---|---|---|---|
| 3.1 | `prepare_operation_scenario(engine, **flags)` | `T/operation_scenario_support.py:10-156` | on the maintenance engine, one txn: `persist_release`, `data.project 'p'` (on-conflict-do-nothing), `data.realization` (`realization_id` default `"z"`). Preparation (`prepare_release`) precedes and is memoized (`src/.../prepare.py:544-580`, per DTA-025) | 70 occurrences of `prepare_operation_scenario` in tests (incl. its def and imports); flags vary (`observations`, `characterization`, `composed`, `evaluation`, `archive`, `realization_id`) |
| 3.2 | `prepare_record_source()` | `T/native_record_fixtures.py:208-286` | nothing: "Pure original inputs and prepared release; no database" | used by `private_preparation` (`:787`) and `private_source` |
| 3.3 | `build_record_source(admin, writer, ...)` | `:292-646` | (a) admin txn: `persist_release`, project, realization; (b) writer txn: `create_run`, `record_method`, `register_document`, `create_task`, `claim_tasks`, `store_pdf_original`; (c) `publish_native_record_fixture` (`:109-200+`): `begin_pdf_build` txn, then one txn per adopted Arrow record batch (loop over `write_record_batches`), one txn for companion/metadata + `freeze_pdf_build` + `prepare_pdf_build`, `validate_pdf_build(engine, frozen)`, then a seal txn (`:196-201`); (d) writer txn: 2 source views (`store_source_view`), `complete_task` of the ingest task, a second method config + `create_task` + `claim_tasks` for the record task (lease 5 min), reads of `view_row`/`task_row`. Writes a PDF file under `tmp_path`. Returns a mutable `SimpleNamespace` | 4 call sites of `build_record_source(` (counted); reached through `private_source` |
| 3.4 | `private_source` fixture | `:791-819` | wraps 3.2 + 3.3 on `semantic_db_engine` + `semantic_writer_engine`; `private_source_options` (`:781`) is an overridable dict fixture, and `request.param` merges via indirect parametrization | 85 test functions in 28 files (AST). `project_id`, `include_blank_cell`, `sibling_*`, `additional_methods`, `bundle_transform` etc. select different inputs |
| 3.5 | `reference_source` | `T/reference_scenarios.py:202-208` | on `private_source` (options `bundle_transform=reference_inputs`): `complete(case, conn, ())` and `seal_cut(..., final=False)` in one writer txn; **assigns `case.cut`** on the shared namespace | 12 functions in 3 files |
| 3.6 | `private_build` / `create_private_build` | `T/pdf_staging_support.py:135-146`; factory `:60-128` | one writer txn: `create_run`, `record_method`, `register_document`, `create_task`, `claim_tasks`, `store_pdf_original`, `begin_pdf_build`; writes a (sometimes rasterised) PDF to `tmp_path`; **runs on `prepare_operation_scenario`-style release, not `private_source`** | `private_build` 50 functions/19 files; `create_private_build` 1 |
| 3.7 | `pdf13_db` | `T/pdf_integration_support.py:326-416` | `prepare_operation_scenario(observations=True, composed=True)` + a `create()` closure (run, method, document, task, claim, `store_pdf_original`), then `_publish_record_document` and two observation `publish(db, product)` calls (each several txns); returns namespace with a `create` closure that tests re-call | 21 functions/6 files |
| 3.8 | `characterization_source` | `T/test_characterization_native.py:34-` | on `private_build`: `publish_selected(...)`, reads, drafts, further writes | 18 functions/1 file |
| 3.9 | `build_resubmission_case(admin, engine, path, ...)` | `T/agent_scenarios.py:36-171` | admin txn: `persist_release` + project + (if `composed`) `activate_release` + realization; engine txn: `create_run`, `register_document`; `publish_controlled_pdf_views`; txn: `bind_primary_agent_run`, `queue_agent` (agent task). Returns `(prepared, run, task, locator)` (immutable tuple) | 34 occurrences of `build_resubmission_case(` (counted; includes calls by `build_completed_serving_case` and defs). DTA-018 cites "32 other" |
| 3.10 | `build_domain_case(admin, writer, path, ...)` | `T/domain_scenarios.py:65-` | domain release + run + sealed cut with ~30 option flags; returns `(prepared, run, cut)` | 40 occurrences (counted); 3 tests in the DTA-025 table call it parametrized |
| 3.11 | `seed(engine, scope=..., **model_options)` | `T/domain_scenarios.py:763-776` | one admin txn: `persist_release`, `data.project 'p'`, `data.realization Z` | 42 occurrences across 7 files (`grep -rn "\bseed("`, minus defs/`.seed`) |
| 3.12 | `inference_fixture(admin, writer)` | `T/test_arrow_publication.py:87-90` -> `test_inference.setup` (`:47-`) + `compute` (`:189-194`) | `setup` persists a release and publishes a base batch (the refusal tests then assert `SELECT count(*) FROM data.batch == 1`, `test_arrow_publication.py:489-490`); `compute` is a REPEATABLE READ read-only derivation, not a publish | 4 call sites |
| 3.13 | `completed_component_case(case, tmp_path)` / `completed_relationship_case(case, monkeypatch, tmp_path, ...)` | `T/witnessed_scenario_support.py:93-`, `:297-` | on a `private_source` case: `complete_contributions` txn, `finalize_bound_run(case.writer, case.run, ...)` (seals and finalizes), then a controlled producer run for relationship tasks (new run, tasks, publications). Mutates the database, not the `case` namespace | 7 call sites in 6 files (counted) |
| 3.14 | `judged_source`, `applicable` | `T/test_local_semantic_admission_native.py:52-`; `T/test_witnessed_applicability_native.py:~30-126` | both build on 3.4 + 3.13 + `finalize_bound_run`; `judged_source` adds evaluator-login `assign_origin`, reference set, passes/grades, new run and `seal_cut`; `judged_source` copies `SimpleNamespace(**vars(original_case))` before overriding `run/task_row/task` | `judged_source` 8 functions (all one file); `applicable` 2 |
| 3.15 | `local_cut(case)` | `T/test_local_admission_native.py:26-30` | helper called **inside each test**: `complete(case, conn, drafts(case))` + `seal_cut(..., final=True)` in one committed writer txn | called per test in that file |
| 3.16 | `curated_case(original, ...)` | `T/native_record_fixtures.py:923-981` | helper called inside tests: commits a *second* method config (`record_method`), `create_task`, `claim_tasks` for the same run/view/unit key; returns a **new** namespace (`vars(original) | dict(...)`), leaves `original` untouched | called per test in contextual families |

### 3.17 Serving seed (the in-repository seed-and-clone precedent) - `T/serving_scenarios.py`
- **Scope and consumers.** `serving_scenario_seed` is session-scoped (`:288-297`) (per worker). Consumers (AST): `serving_read_scenario` in 3 functions of `T/test_serving.py` (`:43,282,559`); `T/test_serving_scenario_lifecycle.py` has 3 tests
  (`:25` seed recipe refusal; `:31` two isolated clones; `:73` failed seed build releases the database, using `_serving_seed_lifecycle` with a failing builder).
- **Build** (`_serving_seed_lifecycle`, `:241-285`): `native_server.database("cs_sem_test_<pid>_<hex12>", head.name, policy=head.policy)` (full acquisition, section 2) -> `principal_engine(native_settings, "write", name)` -> builder
  `build_completed_serving_case(admin, writer, tmp)` (`:38-158`) = `build_resubmission_case(composed=True, domain="statistics", query_inputs=acquire_query_inputs(domains/statistics))` (3.9), then `anyio.run(submit)` over an in-process FastMCP `Client(build_semantic_server(SemanticAgentSession(writer, run)))`:
  `lease_and_read` (`agent_scenarios.py:184-`, `queue_next`, `read_instructions`, `read_unit` MCP calls), `propose_claims` of three claims expecting `completed_accepted`; optional coverage witness; `finalize_bound_run(writer, run, "served-result")`.
- **Seal and identity.** After the builder: `writer.dispose()`, `admin.dispose()`; `seed_policy = native_server.policy(name)` must equal the head policy (`:264-266`); `ServingScenarioSeed` (frozen, `:161-182`) records database name, **database OID**, policy, `recipe_id`
  (sha256 over version tag + manifest digest + `inspect.getsource` of `build_completed_serving_case`, `build_resubmission_case`, `lease_and_read`; `:195-205`), manifest digest, `prepared`, `run`, `task`, `locator`. Then `ALTER DATABASE ... ALLOW_CONNECTIONS false` (`:281-283`; not `IS_TEMPLATE`)
  and `_validate_serving_seed`.
- **Validation** (`:218-238`; run at seed creation `:284` and at **every** clone acquisition `:307`): re-read OID (1 connection), re-read policy (`policy()`, 1 connection / 3 SELECTs), recompute recipe id (source inspection), and one connection querying `datallowconn` and `count(pg_stat_activity)` for the seed (must be disallowed and client-free).
  The recipe hash does not include source of other helpers the builder calls (`publish_controlled_pdf_views`, `bind_primary_agent_run`, `queue_agent`, `persist_release`, ...) - what the hash covers is exactly the three `inspect.getsource` calls (`:198-200`).
- **Clone** (`serving_read_scenario`, `:300-344`): validate; new name; `native_server.database(name, seed.database, policy=seed.policy)` (full acquisition with source = seed, section 2 tally); `native_server.policy(name) == seed.policy` re-check (`:310`; a duplicate of replay step 6); `_database_oid` (1 conn) must differ from the seed's;
  one SELECT through the maintenance engine proving the seeded `data.realization (resubmit, served-result)` carries `seed.prepared.release_id`; `principal_engine(read, name, scenario_seed=seed.origin)`; a connect asserting `current_user = session_user = reader login`. Yields a frozen `ServingReadScenario` (reader engine + seed identifiers).
- **Cleanup.** Reader engine disposed in `finally`; clone dropped by `database()` exit. Seed dropped when the session generator unwinds (the `with native_server.database(...)` at `:252` stays open across `yield seed`, `:285`), so the seed holds its shared lease for the worker's session. `native_server` sweep key `cs_sem_test_<pid>_<hex12>` matches.
- **Consumer shape.** The clone gives a *reader* only; the 3 serving tests and lifecycle tests use `ServingReadScenario.reader` plus the seed identifiers. The lifecycle test 2 (`:31-69`) additionally creates a second clone (name without pid -> escapes sweep, section 1) to prove isolation by committing a run on one clone and not seeing it on the other.

---

## 4. Rollback-only families (DTA-025 and others found)

Per-family facts. "Confined" = writes inside `begin_nested()` (rolled back by exception exit or `.rollback()`) or an outer transaction ended by exception/`rollback()`.
All writer/maintenance engines are `NullPool`, so **no connection-level state (plan cache, `SET`, temp tables, advisory locks) survives from one case to the next**; each `begin()`/`connect()` is a new backend.

| Family | Cases (literal list) | Fixture + what it commits | Case writes | Mutates fixture `case`? | Do cases differ in fixture inputs? |
|---|---|---|---|---|---|
| `T/test_private_records.py:62-131` `...refuses_forged_private_source_custody` | 12 (counted 12 `lambda c, r`) | default `private_source` (3.4) | `case.writer.begin()` outer txn commits at normal exit but contains only: positive control `bypass(...)` inside a `begin_nested()` that is explicitly `.rollback()`ed, and the refusal inside `pytest.raises(...), conn.begin_nested()` (exception exits the savepoint). Final asserts: no `ops.task_result`/`kb.observation` row | No. `candidate(case)` and `refresh_record_identities(case, record)` mutate a `deepcopy` of the record (`:649-707, 1078-1094`); `bypass` reads `case.held.attempt`, `case.task_row`, `case.view` | No: lambdas change only the record copy. Some lambdas read `c.sibling`, `c.table`, `c.source_task`, `c.other_view` |
| `T/test_private_records.py:~190-230` `...private_product_types_are_independently_refused...` | 8 | `private_source`, then `publish_batch(case.writer, batch)` inside `pytest.raises`; a refused standalone transaction | nothing committed if refused; a final connect asserts absence | No | No (form/datatype vary the batch) |
| `T/test_runtime_bindings_native.py:100-148` | 8 | `prepare_operation_scenario(semantic_db_engine)` (3.1, defaults) only - release/project/realization; no run/task | `with pytest.raises(DBAPIError), semantic_writer_engine.begin()` -> whole txn rolled back by exception | No (`prepared` frozen; binding JSON copied: `json.loads(binding.manifest)`) | No |
| `T/test_local_semantic_admission_native.py:505-660` | 10 | `private_source` (+`additional_methods=("private.contextual",)`) + `judged_source` (3.14, `{"cases":2,"grades":2}`) - 3.13 + finalize + evaluator rows + seal | one `SERIALIZABLE` writer txn; `SELECT data.begin_evaluation(...)`, a clean sibling publication in `begin_nested()` that is `.rollback()`ed, the forged one in `begin_nested()` under `pytest.raises`, then `transaction.rollback()` (`:645`). Case `unit` additionally does `SET LOCAL plan_cache_mode='force_generic_plan'` (`:546`) and 8 publish/refuse replays (`:633-643`); `stage_arrow` creates temporary staging objects inside the aborted txn | No: `judged_source` hands out a copy (`SimpleNamespace(**vars(original_case))`, `:63`); test uses `dataclasses.replace` | No (corruption name only) |
| `T/test_local_admission_native.py:73-` `...witness_refusals_rollback_receipt_and_all_rows` | 7 | `private_source` + **in-test** `local_cut(case)` (3.15) which **commits** `complete` and `seal_cut(final=True)` | `SERIALIZABLE` txn + `begin_evaluation` + nested publish; rolled back; trailing connect asserts absence | No | No |
| `T/test_witnessed_applicability_native.py:172-282` | 6 (`APPLICABILITY_CORRUPTIONS`, `assert len == 6`) | `applicable` (3.14): 3.4 + 3.13 + `finalize_bound_run` + metadata | **Not rollback-only:** inside `with case.writer.begin() as conn:` (no savepoint around it) the test commits a **new run, a new task and a `claim_tasks` claim** per case (`create_run`, `create_task`, `claim_tasks`, `:176-197`); only `complete_native` calls sit in `begin_nested()` (positive `.rollback()`, refusal under `pytest.raises`). The outer txn exits normally and commits | No (`deepcopy(a.body)`) | No (corruption varies `body`) |
| `T/test_arrow_publication.py:445-493` | 6 | `inference_fixture` (3.12): release + base batch committed | `SERIALIZABLE` writer connection, `conn.begin(), pytest.raises(DBAPIError)`: `stage_arrow` + `publish_derived_batch_v2` with `params.update(changes)`; exception rolls back; then asserts `data.batch` count `== 1` | No (`result.binding`, `result.batch` read; `params` is a local dict) | No |
| `T/test_contextual_enrichment_native.py:65-157` | 13 | `private_source` (with contextual method) + **in-test** `curated_case` (3.16) committing a second config/task/claim | `case.writer.begin()` outer txn (commits, empty) + refusal in `begin_nested()` under `pytest.raises`; asserts `kb.contextual_vector`/`kb.source_contribution` empty | No (`curated_case` returns a new namespace; `raw = envelope(...)`'s dict is edited) | No |
| `T/test_structural_native_replay.py:147-217` `...replays_same_source_route` | 14 | `private_source` where the module-level `private_source_options` (`:58-70`) sets `sibling_references` to each case's `left`/`right` text | **Not a refusal family:** `semantic_db_engine.connect(), conn.begin()` calling `ops.structural_compare_lexical` and `data.structural_public_statement` (SELECTs only; the txn commits nothing). `_captured_comparison_inputs` reads `load_source_view` | No | **Yes**: the source view text itself differs per case via `private_source_options`; scenarios are genuinely different here |
| `T/test_structural_native_replay.py:486-` `...groups_exact_occurrences` | 3 | same options override (connector text) | not examined beyond signature | - | yes (as above) |

Others found with the same *shape* (a parametrized test that requests a scenario fixture or builder; AST scan lists 61 such tests, 244 cases counted from literal parameter lists; non-literal lists count as 0 in that sum, so it is a lower bound). Not classified as above except where noted:
`T/test_operations.py:576` `test_native_role_cannot_forge_reuse_binding` (9; builds `prepare_operation_scenario`, then in-test commits a run, method config, task, claim and `complete_task` before the forgery - **not rollback-only**),
`T/test_alternative_groups.py:155` (6; `seed(semantic_db_engine)` then `publish_batch` expected to fail as its own transaction; asserts empty `data.alternative_group`/`data.fact`),
`T/test_domain_operations.py:867` (6; `build_domain_case(..., graph=True, membership_subtype=True, unselected_report=forgery == "source_cut")` - **one builder flag depends on the case**, so the "source_cut" case has a different scenario),
`T/test_native_attributed_evidence.py:256` (6; `pdf13_db` then `publish(db, prepare(values, db.source))` committed in test, refusal under `begin_nested()`),
`T/test_pdf_owner_counts.py:35` (6; `private_build`), `T/test_pdf_reference_preparation.py:24` (7; `private_build` + `stage_complete_native` + per-case committed `adopt_pdf_batch` transactions),
`T/test_execution_native.py` `test_conditional_kernel_reaches_protected_publication` (7, `seed`), `T/test_contributions_native.py` (4+3), `T/test_pdf_staging.py`, `T/test_pdf_publication_identity.py` (5), `evaluate/test_record_references_native.py` (4+3, `reference_source`).

### Premises a shared committed scenario would have to satisfy (facts about the code; "open" where not established)
- **Task leases.** `ops.claim_tasks` sets `lease_until = clock_timestamp() + interval '5 minutes'` (`src/corpus_structure/semantic/sql/execution_projection.sql:86`); a `running` task with `lease_until < clock_timestamp()` is re-claimable (`:82`) and re-claim bumps `attempt` (guard `execution_guards.sql:36-40`). Lease checks against `clock_timestamp()` live in `execution_projection.sql:101,103` (renew),
  `pdf_observation.sql:154`, `src/.../pdf_staging_native.py:56`, `pdf_publication_native.py:441,466`, `claim_lifetime.py:149`; `native_task_completion.sql` (the `complete_task` body, `:97`) *clears* `lease_until` and I found no `clock_timestamp()` lease comparison in it by grep. The private-records and contextual families complete a claimed task (`bypass`/`complete`) after the fixture claimed it: whether any
  completion path they exercise checks the lease is **open** for the paths not grepped (`complete_task` wrapper in `src/.../operations.py` not read). A scenario that outlives 5 minutes (a session-scoped seed in a long worker) has expired leases at the point of reuse.
- **Case object.** `private_source` returns a mutable `SimpleNamespace`; `reference_source` assigns `case.cut` (3.5); `judged_source` and `curated_case` copy before overriding. No DTA-025 family above assigns to the case it receives (searched the listed test bodies).
- **Sequences / generated ids.** Positive controls and refusals that insert then roll back consume identity/sequence values (not rolled back by PostgreSQL); `private_source` tests reference `c.source_task + 10000` (`test_private_records.py:~98`), a literal offset from a task id, not a stored id. Whether any assertion depends on exact generated ids is **open** (not searched).
- **Advisory locks.** Tests in these families take none; PgAdmin leases are on `postgres` connections, not clones. (search: `pg_advisory` in the listed files - no hits; hits elsewhere: `native_test_support.py`, `test_db_fixtures.py`.)
- **`plan_cache_mode`.** Only `test_local_semantic_admission_native.py:546` (`SET LOCAL`, transaction-scoped; the `unit` case intentionally relies on replay in one backend). Safe under sharing because each case opens its own connection.
- **`CREATE OR REPLACE` / role settings / temp objects.** In the listed family files: none in the refusal cases (search: `CREATE OR REPLACE|ALTER ROLE|ALTER DATABASE|CREATE TEMP|DROP FUNCTION|plan_cache_mode|pg_advisory` over the eight family modules - hits only `plan_cache_mode` above and three `CREATE OR REPLACE FUNCTION` at `test_structural_native_replay.py:324,333,445` in other tests of that module that redefine functions on their own clone). Temporary staging relations from `stage_arrow` are created inside the aborted transactions.
- **In-test commits that a shared scenario would collide with:** `test_witnessed_applicability_native.py` (new run/task/claim per case), `test_local_admission_native.py` (`local_cut` commit + final seal), contextual family (`curated_case` second task for the same `(run, config?, unit_key)` - identical across cases, so a second invocation on a shared scenario would re-create the same logical task; uniqueness behaviour **open**).
- **Distribution.** `--dist=loadgroup` with no group mark: cases of a family go to different workers (README/DTA-025), so any shared scenario is per worker.

---

## 5. Pure native-function tests

Search (heuristic, not proof of "writes nothing"): AST scan of every `def test*` that requests `semantic_db_engine` and whose source has no scenario/writer/transaction markers (`private_source`, `prepare_operation_scenario`, `build_*_case`, `seed(`, `persist_release`, `semantic_writer_engine`, `.begin()`, `insert(`, `INSERT`, ...): **29 test functions in 18 files**
(`acceptance/test_regeneration.py` 3, `semantic/test_nce02_native_scope.py` 5, `semantic/test_local_semantic_admission.py` 3, `semantic/test_contextual_workflow_native.py` 2, `semantic/test_native_closure.py` 2, `semantic/test_postgresql_capability_adoption.py` 2, and 1 each in 12 other files). Parametrization expands these.
Established by reading:
- `T/test_local_semantic_admission.py:121-147`: `native_match(engine, values)` = `engine.connect()` + `SELECT data.local_semantic_case_matches(CAST(:c AS jsonb)...)` with canonical JSON arguments; `test_supported_label_cannot_bypass_applicability` has **17** parameters (`:121-139`), plus a base case and the wrong-statement test; no writes.
- `T/test_contextual_workflow_native.py:29-87,104-135`: parametrized literal-argument calls (carrier JSON, 4 + 6 literal params counted from the file); `semantic_db_engine.connect()` + `pytest.raises(DBAPIError, match=...)`. DTA-025 records ten.
- `T/test_structural_native_replay.py:147` family (section 4) is also literal-argument SQL, but its fixture inputs differ and need `private_source`.
What the existing shared rungs offer them:
- `db` (`PC:288-292`): rollback connection on the session clone `ci_test_<pid>` (`db_engine`, the **maintenance** login, policy-replayed head clone). It supplies a head-deployed database with no per-test clone; consumers now are 4 functions (+14 on `db_engine`). It is created lazily at first use per worker and would carry whatever a test commits.
  A function call under `db` runs as the superuser maintenance login, as `semantic_db_engine` does.
- `semantic_bare_engine` (`SC:37-45`): a per-test clone of `cs_template` with extensions only, **no semantic schema**, so it cannot serve head SQL functions; its 19 consumer functions assert bootstrapping/extension behaviour. (It is therefore not an alternative for these tests; stated only because the assignment asked.)
- **Obs.:** the heuristic list above was not cross-checked for `db`; the AST count of `db` consumers (section 1) shows none of the named modules among them.

---

## 6. Cluster and server configuration (what the files state)

`ops/postgresql/corpus.conf` (installed to `/etc/postgresql/18/corpus/conf.d/` by `scripts/pg_provision.sh:20,93-101`; header comment in the file):
- `listen_addresses = ''` (socket only), `port = 5434`, `max_connections = 256`, `max_locks_per_transaction = 1024` (comment: "Concurrent native test bootstrap holds temporary validation relation locks across all auto-selected xdist workers").
- Memory: `shared_buffers = 8GB`, `effective_cache_size = 64GB`, `work_mem = 64MB`, `maintenance_work_mem = 8GB`, `autovacuum_work_mem = 1GB`; comment "host: 32 cores, 188 GB RAM shared with GPU work and the main cluster".
- I/O/WAL ("NVMe" comment): `io_method = io_uring`, `effective_io_concurrency = 256`, `maintenance_io_concurrency = 256`, `random_page_cost = 1.1`, `wal_compression = zstd`, `max_wal_size = 8GB`, `min_wal_size = 1GB`, `checkpoint_timeout = 15min`, `checkpoint_completion_target = 0.9`.
- `synchronous_commit = off` ("data is regenerable (operator, 2026-10-28)").
- `jit = off`, `max_worker_processes = 16`, `max_parallel_workers = 8`, `max_parallel_workers_per_gather = 4`, `max_parallel_maintenance_workers = 4`.
- Observability: `shared_preload_libraries = 'pg_textsearch,pg_stat_statements,auto_explain'`, `compute_query_id = on`, `track_io_timing = on`, `pg_stat_statements.track = all`, `auto_explain.log_min_duration = '1s'`, `log_min_duration_statement = 250ms`, `log_checkpoints`, `log_lock_waits`, `log_temp_files = 0`, `log_autovacuum_min_duration = 1s`, parameter logging suppressed.
- **Not stated anywhere under `ops/`:** `fsync`, `full_page_writes`, `wal_level`, data-directory location or filesystem, tablespaces, `max_wal_senders`, autovacuum settings beyond `autovacuum_work_mem`, `createdb` strategy. `grep -rn "tmpfs|fsync|full_page|data_directory|ramdisk" ops scripts/pg_*.sh justfile` returns only the `synchronous_commit` line. The cluster is created by `pg_createcluster 18 corpus --port ... --start-conf auto --locale C.UTF-8 --encoding UTF8` (`pg_provision.sh:93`) with no `-d` data-directory argument, i.e. Debian's default location (an external convention, not stated in the repo).
- **Test-specific durability relaxation:** no test-only override file or `ALTER SYSTEM`/`ALTER DATABASE ... SET synchronous_commit` was found (search: `synchronous_commit|ALTER SYSTEM|PGOPTIONS` over `ops`, `scripts`, `justfile`, `.envrc*`, both test trees: only `corpus.conf:30` and a statement/lock-timeout `PGOPTIONS` in `scripts/native_auth.py:97`). `synchronous_commit = off` is cluster-wide, so it already applies to test traffic. The cluster is shared with non-test use (`corpus` database, `ops/postgresql` comments; AGENTS.md: dev database `corpus_structure_dev` on the same cluster).
- Provision also creates the role `$OWNER` as `SUPERUSER CREATEDB CREATEROLE` and the `corpus_ro` role (`pg_provision.sh:106-116`); semantic logins `NOSUPERUSER` etc. (`pg_semantic_roles.sh:69-74`).
- Cross-reference: `max_connections = 256` against worker count `-n auto`: each worker holds at least the lease connection per live clone plus sequential NullPool connections; the files contain no explicit per-worker connection budget (search: `max_connections` in tests/scripts: none).

---

## 7. Teardown

- **Clone drop** (`database()` finally, `NTS:478-493`): list of cleanups: `engine.dispose()` (clone engine; NullPool, so no idle connections), then `_drop(name, owned=creation.owned)` only if CREATE was acknowledged (`creation.owned`, `NTS:483`). Exceptions are collected into a `BaseExceptionGroup`; the primary failure is kept first.
- **`_drop`** (`NTS:213-242`): up to 2.0 s deadline; each attempt opens a maintenance connection, reads `oid`, owner, comment, `current_user` for the name, returns if absent, refuses unless owner == current_user and (when `owned` is given) OID+owner match the acknowledged creation or (name route) `owned_comment` matches;
  executes plain `DROP DATABASE` (**no `FORCE`, no backend termination**, ADR-0032 Decision). On SQLSTATE `55006` (object in use) sleeps 0.05 s and retries until the deadline, else re-raises. Comment at `NTS:214`: "libpq close can precede the backend's final exit. Never terminate other logins."
- **Lease release:** the lease connection is the outer `with self.lease(name)` (`NTS:452`); leaving it closes the connection and with it the session-level shared advisory lock. No explicit `pg_advisory_unlock` for leases (the sweep unlocks its own exclusive try-locks, `NTS:603-607`).
- **Order:** purpose engines (dependent fixtures) dispose first; then the clone fixture; so by the time of `DROP` the NullPool connections are closed, apart from backends still exiting (the reason for the retry).
- **Per-test cleanup beyond drop:** pytest `tmp_path` directories (under `build/tmp/pytest`, `PC:93-100`, `conftest.py:10-18`) holding the generated PDFs and Arrow spool files; `monkeypatch` undo (env sentinel, `ConnectionPool.check_connection` patch in `observed_store_checkouts`, `PC:306-321`; `build_record_source` monkeypatches `contracts.analysis_implementation_inputs` when `sibling_originals` is used). No fixture truncates or resets data in a clone.
- **Session end per worker:** serving seed drop (if used), `ci_test_<pid>` drop (if `db_engine` used), head template drop. `semantic_template` yields inside `database()` so the template's drop is the same path.
- **Failure/interruption:** residue is reclaimed only by a later worker's `native_server.sweep()` (section 1), and only for the recognised names and owned comments.

---

## Observations collected for the reviewer (not remedies)

1. `semantic_head_template` is a pure function of the migration chain and `cs_template`, rebuilt by every worker that receives any native test (DTA-024); ADR-0032 revisit trigger is quoted at `docs/adr/0032-...md:10`. Nothing in the code shares it across processes; the sweep's lease keys would let concurrent workers coexist but each worker's sweep treats other workers' leased names as live.
2. One clone acquisition = 7 acquisition connections + 1 drop connection (no role settings, no receipt sink) because `PgAdmin.connect()` creates and disposes an engine per call; only the lease and (conditionally) role-self replay are inherently distinct connections.
3. The serving seed is the only in-repo seed-and-clone; its clone path re-validates the seed (3 maintenance connections) and re-reads policy twice per clone; it is built per worker, not per run.
4. `PgAdmin.database()` and the serving clone both lease only the *new* name; the seed's liveness rests on its own shared lease for the session.
5. Overlap: `semantic_db_engine` (function), `committing_db` (function, one consumer: its own self-test), `db`/`db_engine` (session, 18 consumers), `serving_read_scenario` (function) all go through `PgAdmin.database()`; `semantic_bare_engine`/`semantic_database_at` bypass the head template deliberately.
6. Unused/near-unused: `committing_db` (1 consumer), `cs_tpl_` sweep branch and `STAMP`/`stamp()` (DTA-030), `semantic_admitter_engine` (3) with its `admitter` alias (10), `create_private_build` (1), `db` (4). The shadowing fixture in `test_native_attributed_evidence.py:50-72` repeats `SC:27-34` plus an unreachable branch (DTA-030).
7. DTA-025's "rolled back" description holds for private_records custody, runtime bindings, judged-semantic rows, local-witness refusals, arrow derived-binding and contextual-enrichment families; it does not hold for `test_witnessed_applicability_native.py` (commits a run/task/claim per case, section 4) and `test_operations.py:576`.
8. The structural-replay family (14) is not a same-scenario family: the module's `private_source_options` feeds each case's text into the committed source view.

## Limits
- No DB, collection or test run; the live ACL/role-settings content of the head policy (G, N, R) is unknown, so per-clone REVOKE/GRANT/settings statement counts are symbolic.
- Counts are AST/grep scans at the baseline; `parametrize` expansion was only summed for literal lists.
- Not read in full: bodies of `pdf_acceptance_support`, `publish_controlled_pdf_views`, `validate_pdf_build`, `complete_task` wrapper in `operations.py`, `seal_cut`, `finalize_bound_run`; their connection/transaction counts and any lease checks are therefore open.
- `test_native_faults` / `shared_cluster_fault` controls and `native_auth.py` alternate-principal machinery were not mapped.
