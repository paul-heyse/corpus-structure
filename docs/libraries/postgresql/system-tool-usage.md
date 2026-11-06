# PostgreSQL system tools used by corpus-structure

**Verified 2026-11-06.** Repository usage inventory, covering application/deployment tooling,
operator workflows and testing. This is repository-specific, unlike the general
[Ubuntu tooling capability overview](PostgreSQL_System_Tooling_for_Ubuntu.md).

“Production” below means application/runtime or deployment/operational responsibility. It does
not assert a separately deployed production service. Normal development uses the persistent
`corpus_structure_dev` database on dedicated PostgreSQL `18/corpus`, Unix socket
`/var/run/postgresql`, port **5434**. Tests normally use isolated databases on that same cluster.
Other clusters are outside these commands' authority.

A tool being installed is not evidence that we use it. The tables distinguish direct invocation,
indirect platform use, documented operator options and retained test/investigation use. They do
not enumerate every general-purpose Unix command or PostgreSQL internal subprocess.

## Application and shared operational tools

The current application and `ci db` commands use PostgreSQL client libraries and SQL; they do
**not** invoke `psql`, `pg_dump`, `pg_restore` or a PostgreSQL server executable as subprocesses.
The following executables support deployment, operations and retained data workflows.

| Tool or service | Where and how we use it | Testing relationship |
|---|---|---|
| `psql` | Directly invoked by [pg_provision.sh](../../../scripts/pg_provision.sh) for roles, databases, extensions, status and checksums, and [pg_semantic_roles.sh](../../../scripts/pg_semantic_roles.sh) for purpose roles, peer mappings and configuration reload/validation. | Also directly invoked by the testing-only authentication helper; not a testing-only executable. |
| `pg_lsclusters` | Directly invoked by both provisioning scripts to identify the dedicated cluster and check its port/state; also used by `just db-status`. | Test prerequisite/setup depends on the same provisioned cluster. |
| `pg_createcluster` | Directly invoked by `pg_provision.sh` only when `18/corpus` does not exist. Establishes the Ubuntu-managed cluster rather than an application-managed server process. | Shared cluster is reused by ordinary tests; private-cluster testing is a separate route below. |
| `pg_ctlcluster` | Directly invoked for start/restart by `pg_provision.sh`, and start/stop through `just db-up` / `just db-down` in the [justfile](../../../justfile). | Also used in the retained private-cluster interruption probe. Not exclusive to testing. |
| `pg_wrapper` | Indirect Ubuntu client dispatcher: `/usr/bin/psql` resolves to `/usr/share/postgresql-common/pg_wrapper`. Versioned client commands can instead be addressed explicitly. | Shared client infrastructure, not a separate test runner. |
| `initdb`, `pg_ctl`, `postgres` | Indirect server lifecycle components behind Ubuntu's cluster tools: initialization, server control and the running PostgreSQL backend. We do not have an application or normal pytest fixture that directly launches these commands. | Same server machinery underlies private-cluster tests, but ordinary fixtures clone databases rather than initialize clusters. |
| systemd `postgresql@18-corpus.service` | Actual dedicated-cluster service. Read-only inspection found it active, with `ExecStart=/usr/bin/pg_ctlcluster --skip-systemctl-redirect 18-corpus start`. | Tests depend on its availability; ordinary tests do not start a separate system service per worker. |
| `pg_dump` | Directly invoked for retained source/reference database archives, including custom-format source-population dumps. See [intake_populations.py](../../design_review/evidence/2026-11-04_m1-source-populations/intake_populations.py) and [prepare_development_references.py](../../design_review/evidence/2026-11-03_m1-qualification/prepare_development_references.py). | Archive verification and restore controls exercise these products; their purpose is not limited to synthetic test databases. |
| `pg_restore` | Directly invoked to inspect custom archive contents (`--list`) and restore retained source databases with `--exit-on-error`. [restore_source_dump.py](../../design_review/evidence/2026-11-04_m1-source-populations/restore_source_dump.py) explicitly selects `/usr/lib/postgresql/18/bin/pg_restore`. | The recorded restore round trip is a bounded assurance workflow, not a fixture run before every test. |

The dump/restore usage is concrete, but **does not establish an automated backup service**.
The [source-population evidence](../../design_review/evidence/2026-11-04_m1-source-populations/README.md)
records the archive and successful round trip, including earlier failed attempts. Roles and
database-level ownership/grants/settings require explicit handling; the restore owner replayed
the captured/reconstructed bootstrap policy rather than assuming a plain dump preserved everything.
Do not equate these archives with cluster-wide role backup, WAL archiving or point-in-time recovery.

## Strictly testing-only tooling and workflows

### Current test infrastructure

| Tool or mechanism | Actual use | Boundary |
|---|---|---|
| `psql` through [native_auth.py](../../../scripts/native_auth.py) | Testing-only invocation of the shared executable, through `sudo -n -u postgres`, with a tagged `PGAPPNAME`, connection/statement/lock timeouts and `ON_ERROR_STOP`. Reads exact cluster/role identity, provisions owned alternate authentication effects, reloads configuration and recovers those effects. | The **helper's role** is testing-only; `psql` itself is also used operationally. Real shared-cluster fault controls run in the exclusive serial lane. |
| PostgreSQL database templates and SQL lifecycle | [PgAdmin](../../../scripts/native_test_support.py) leases owned names, creates/clones databases, replays database ACL/default settings and disposes only acknowledged owned databases. [Fixtures](../../../python/corpus-structure/tests/conftest.py) maintain sealed session templates and independent committed/rollback lifetimes. | Native PostgreSQL SQL through drivers, not `createdb`, `dropdb`, `pg_virtualenv` or a GUI. This `PgAdmin` is our Python helper, not the pgAdmin desktop/web administration product. |
| Native inspection, locking and transaction controls | Real-purpose clients use catalogs, advisory locks, row/transaction locks, rollback/savepoints and independent connections for privileges, fencing, races, publication, cleanup and acquisition provenance. | Engine capabilities, not standalone command-line programs. Actual native errors remain distinct from Python preparation refusals. |
| pytest / pytest-xdist / receipt runner | Executes the PostgreSQL tests and records actual per-item acquisition identity. Default ordinary lane has 16 workers; `just test-native-faults` runs the eight shared-cluster controls separately with `-n 0`. | Python testing infrastructure, not PostgreSQL server tooling. Per-worker templates and live database leases still govern isolation. |

The shared PostgreSQL server, provisioned extensions and operational cluster commands are
**not** testing-only just because tests depend on them. Conversely, test-only authentication
recovery is not an application startup or normal database-migration requirement.

### Retained testing-only comparisons, not the default harness

| Tool | Recorded use | Current adoption |
|---|---|---|
| `pg_virtualenv` | Private PostgreSQL 18 cluster with owned temporary/config/socket paths for real deployment, isolation and interruption/cleanup comparisons. | Executed in the bounded TA-01 comparison; not selected as the default test backend. |
| `pg_dropcluster` (indirect) | The installed `pg_virtualenv` wrapper invokes it in its owned private-cluster cleanup path, after `pg_ctlcluster` shutdown. | Testing-only private-cluster machinery in the recorded pilot; no normal deployment script deletes the dedicated cluster. |
| `pgTAP` server extension, version 1.3.4 in the probe | `plan`, `results_eq`, `throws_ok` and `finish` compare restricted-role posture and exact SQLSTATE refusals, including an intentionally incorrect expectation. | Installed into the private probe database; not in the four-extension shared deployment contract. |
| `pg_prove` | Runs the positive and deliberately failing TAP files, demonstrating that TAP results must be interpreted rather than inferred from a successful SQL client exit. | Executed in the bounded comparison; not called by ordinary pytest fixtures. |

Sources: [TA-01 result and selection](../../design_review/evidence/2026-11-02_ta-native-arrangement/README.md),
[native_controls.py](../../design_review/evidence/2026-11-02_ta-native-arrangement/native_controls.py)
and [private_owner.py](../../design_review/evidence/2026-11-02_ta-native-arrangement/private_owner.py).
The selected default remains shared-cluster `PgAdmin` ownership and actual purpose credentials.
The private-cluster pilot's recorded limitations must not be promoted into production recovery guarantees.

## Server extensions and modules used by both application infrastructure and tests

These are server-side components, not separate executable commands. The version contract is
[ops/postgresql/extensions.txt](../../../ops/postgresql/extensions.txt); provisioning installs
it, application startup checks it, and fixtures verify it before native work.

| Component | Expected version | Current responsibility and source |
|---|---|---|
| `pg_jsonschema` | 0.3.4 | Active native JSON Schema enforcement through `public.json_matches_schema`, for example [structural_publication.sql](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_publication.sql) and [record_publication.sql](../../../python/corpus-structure/src/corpus_structure/semantic/sql/record_publication.sql). This differs from client-side Python `jsonschema`. |
| `vector` / pgvector | 0.8.7 | Active vector storage and distance operations, including [source_contributions.sql](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql), [contextual_retrieval.py](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) and the relational type adapter. |
| `pg_textsearch` | 1.5.1 | Provisioned, preloaded and checked as part of the deployment contract; D3 retains BM25 capability/evidence. Current serving/contextual lexical code also uses **built-in** PostgreSQL full-text search, so do not describe every lexical query as a pg_textsearch call. |
| `pg_stat_statements` | 1.12 | Provisioned/preloaded statement-statistics support. Current application startup verifies its version; this inventory found no application query of its statistics view. |
| `auto_explain` | PostgreSQL module; no separate `extversion` here | Preloaded and configured in [corpus.conf](../../../ops/postgresql/corpus.conf) to log slow query plans. It is not installed through the four-entry `CREATE EXTENSION` contract. |
| `plpgsql` | 1.0 observed in the working database | Procedural language used by native functions/guards. Standard server language, not an optional testing framework. |

Read-only observation on 2026-11-06: the working database reported PostgreSQL **18.6**, all four
contract extensions at those versions, plus `plpgsql`; `shared_preload_libraries` was
`pg_textsearch,pg_stat_statements,auto_explain`. This establishes installed/active configuration,
not a claim that every extension is used by every application request or test.

## SQL capabilities that replace additional system commands

| Responsibility | Current mechanism |
|---|---|
| Reachability and prerequisites | Driver connection plus actual `SELECT`/catalog checks; no checked-in `pg_isready` call found. |
| Database creation/removal | `CREATE DATABASE … TEMPLATE …`, `DROP DATABASE`, acknowledged ownership and advisory leases; no normal fixture invocation of `createdb`/`dropdb` found. |
| Native deployment/migrations | `ci db init` / `ci db migrate`, SQLAlchemy connection and in-process Alembic API; not an `alembic` CLI or `psql` subprocess in application code. |
| Role/authentication verification | `pg_roles`, `pg_auth_members`, `pg_hba_file_rules`, `pg_ident_file_mappings`, actual logins and exact acquired identities. |
| Configuration reload | SQL `pg_reload_conf()` in role provisioning and authentication tests, rather than a separate reload utility per test. |
| Provenance and liveness | Catalog database OIDs, `pg_postmaster_start_time()`, `pg_control_system()` and `pg_stat_activity`; these are not calls to the `pg_controldata` executable. |
| Query inspection/search | SQL `EXPLAIN`/catalog access and built-in `to_tsvector`, `websearch_to_tsquery`, `ts_rank_cd`; these are distinct from `pg_activity`, pgBadger and the pg_textsearch extension. |

Normal application access uses [Psycopg](psycopg.md), [psycopg-pool](psycopg-pool.md),
[SQLAlchemy](sqlalchemy.md), [ADBC PostgreSQL](adbc-driver-postgresql.md),
[pgpq](pgpq.md) binary COPY encoding and [Alembic](alembic.md). These are client libraries or
in-process tooling, not PostgreSQL administration executables. See
[store.py](../../../python/corpus-structure/src/corpus_structure/core/db/store.py),
[runtime.py](../../../python/corpus-structure/src/corpus_structure/semantic/runtime.py),
[analytics.py](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py) and
[arrow_transfer.py](../../../python/corpus-structure/src/corpus_structure/semantic/arrow_transfer.py).
The installed Psycopg implementation reported `binary` with bundled libpq version **180006**;
do not assume it uses the same shared-library file as the host's `psql` executable.

## Documented operator options and available tools without adopted callers

[D3 §13](../../design/D3-database.md#13-operating-postgresql-on-this-machine) names the following
operator options. They are distinct from checked-in automation and confirmed test execution.

| Tool | Status |
|---|---|
| `pg_activity` | Installed and documented for interactive live-session inspection (`pg_activity -p 5434`). No automated application/test invocation found. |
| pgBadger (`pgbadger`) | Installed; cluster logging is configured for on-demand log analysis. No automated report job or application/test invocation found. |
| `pg_upgradecluster` | Documented Ubuntu cluster-upgrade route; no checked-in project invocation or completed upgrade receipt established by this inventory. |
| pgBackRest (`pgbackrest`) | Installed; D3 retains it as a future backup/WAL-archiving option. Not an adopted backup service in the inspected project tooling. |

The host also has tools that **must not be listed as utilized just from their presence**:

- `pg_config`, `pg_conftool`, `pg_isready`, `createdb`, `dropdb`, `pgbench`, `pg_receivewal`, `pg_repack`.
- Versioned `pg_amcheck`, `pg_checksums`, `pg_controldata` and `pg_waldump` under `/usr/lib/postgresql/18/bin`.
- `pg_regress` and `isolationtester` under `/usr/lib/postgresql/18/lib/pgxs/src/test/…`.
  TA-01 explicitly records their execution as **not_run**; they remain candidates, not active test runners.
- `plpgsql_check` is an evaluated SQL-analysis candidate, not an adopted application or test validator.

No current automated caller was found for those names in the inspected application, scripts,
ops, test trees or retained probe source searches. A historical FK-cost probe emits a sample
`createdb` restore instruction; that is not evidence that the command was executed or became a
normal fixture dependency. Installed Ubuntu wrappers can have additional internal helper paths;
this list does not claim to trace their complete conditional implementation.

## How this inventory was checked

Source scope: current application/CLI/native migration facades, `scripts/`, `ops/postgresql/`,
`justfile`, root/package tests, D3 and retained tool-calling evidence sources. Current sources and
recorded outcomes take precedence over the broad capability overview or a package's availability.

Read-only checks: executable discovery, PostgreSQL client `--version`, `pg_lsclusters`, systemd
service metadata, installed wrapper source, Psycopg's libpq implementation/version, and a
read-only query of the working database's server version/extensions/preloads. No cluster, role,
configuration, database contents or test was changed or executed to compile this inventory.
Repository source was inspected while unrelated WCE implementation/evidence work was in progress.
This is an inventory, not fresh production/test qualification or backup/recovery certification.

Primary documentation: [PostgreSQL 18 client applications](https://www.postgresql.org/docs/18/reference-client.html),
[server applications](https://www.postgresql.org/docs/18/reference-server.html),
[pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html),
[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html),
[preloading](https://www.postgresql.org/docs/18/runtime-config-client.html#RUNTIME-CONFIG-CLIENT-PRELOAD),
[auto_explain](https://www.postgresql.org/docs/18/auto-explain.html),
[pg_virtualenv](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html)
and [pgTAP](https://pgtap.org/documentation.html). Context7 was the first upstream documentation lookup;
installed source and repository consumers settled actual usage.
