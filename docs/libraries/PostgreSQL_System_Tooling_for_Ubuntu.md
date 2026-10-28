# PostgreSQL System Tooling for Ubuntu

## Comprehensive ecosystem, capabilities, architecture, and primary-source reference

Research date: October 21, 2026 Primary version baseline: PostgreSQL 18.6 (current stable) Platform: Ubuntu Linux, including Ubuntu 26.04 LTS Scope: Native PostgreSQL utilities, Ubuntu system packages, extensions, standalone command-line tools, database lifecycle management, diagnostics, migrations, testing, replication, backup, security, and specialized execution infrastructure.

This is a revised edition of the original overview. All documentation references use explicit, complete URLs placed alongside the functionality they describe. The URLs are written as literal text in Markdown code spans so they remain intact when copied into another Markdown document.

## 1. Scope, conceptual model, and tooling landscape

PostgreSQL has an unusually extensive ecosystem of system-level tools, command-line utilities, server extensions, operational services, and development infrastructure. Taken together, these provide capabilities extending far beyond database administration: transactional state management, schema evolution, integrity verification, performance analysis, replication, data movement, workload simulation, automation, and specialized query execution.

For Ubuntu, the most useful way to understand the ecosystem is to distinguish what a tool provides, where its functionality executes, and how it integrates with the PostgreSQL engine.

The landscape encompasses five broad classes:

| Tooling class                              | What it provides                                                                                                 | Representative examples                                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Core PostgreSQL utilities                  | Native administration, backup, verification, maintenance, and diagnostics                                        | `psql`, `pg_dump`, `pg_basebackup`, `pg_amcheck`, `pg_upgrade`, `pg_waldump` |
| PostgreSQL server extensions               | Functionality executing inside PostgreSQL, frequently accessible through SQL                                     | `pg_stat_statements`, `pg_repack`, pgvector, PostGIS, HypoPG, pg_partman     |
| Standalone system tools                    | Independent processes for database operations, migrations, diagnostics, and testing                              | pgBackRest, Barman, pgBadger, Sqitch, Atlas, pgcopydb                        |
| Companion services                         | Persistent middleware for pooling, replication coordination, scheduling, and monitoring                          | PgBouncer, Patroni, pg_auto_failover, Prometheus, Debezium                   |
| Development and integration infrastructure | SQL validation, test environments, extension development, typed-code generation, and external engine integration | pgTAP, pg_virtualenv, sqlc, pgrx, DuckDB integrations                        |

The distinction matters because tools with similar interfaces can have different operational guarantees.

For example, `pg_dump` and `pg_basebackup` both produce database backups, but one operates at the logical database-object level and the other at the physical database-cluster level. Similarly, `pg_repack` and `VACUUM` both address physical storage maintenance, but they perform fundamentally different operations.

### 1.1 PostgreSQL version baseline

As of October 21, 2026:

- PostgreSQL 18.6, released August 13, 2026, is the latest stable minor release of the PostgreSQL 18 series.
- PostgreSQL 19 RC1 was released October 15, 2026 and is not yet the stable production baseline.
- Ubuntu 26.04 LTS supplies PostgreSQL through its distribution repositories.
- The PostgreSQL Global Development Group (PGDG) operates an additional APT repository for Ubuntu 22.04, 24.04, 26.04, and 26.10, with versioned servers and numerous extension packages.

This overview targets released PostgreSQL 18 functionality. Independently versioned tools and extensions are discussed according to their documented capabilities, with compatibility qualifications where meaningful.

Primary sources

- PostgreSQL versioning policy and current releases: `https://www.postgresql.org/support/versioning/`
- PostgreSQL 18.6 release notes: `https://www.postgresql.org/docs/release/18.6/`
- PostgreSQL 18 documentation: `https://www.postgresql.org/docs/18/`
- PostgreSQL release schedule: `https://www.postgresql.org/developer/roadmap/`
- Ubuntu PostgreSQL distribution and PGDG repositories: `https://www.postgresql.org/download/linux/ubuntu/`

## 2. Ubuntu packaging, cluster management, and extension infrastructure

### 2.1 PostgreSQL software distribution on Ubuntu

Ubuntu provides several different channels for installing PostgreSQL-related software.

| Distribution mechanism             | Typical components                                                                    | Important characteristics                                                 |
| ---------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Ubuntu APT repositories            | PostgreSQL server/client, `postgresql-common`, PgBouncer, administration utilities    | Distribution-maintained builds with Ubuntu lifecycle integration          |
| PGDG APT repository                | Multiple PostgreSQL major versions, development packages, many third-party extensions | Broad version selection and PostgreSQL-specific packaging                 |
| Vendor-maintained APT repositories | TimescaleDB, pgAdmin, Citus and other specialized components                          | Independently maintained version and compatibility policies               |
| Upstream binary releases           | Migration utilities, diagnostics, specialist proxies                                  | Tool-specific release schedules independent of Ubuntu                     |
| Python CLI environments            | pgcli, pg_activity, SQLFluff and similar utilities                                    | Installable through `pipx`, `uv tool`, or isolated Python environments    |
| Cargo and Go tooling               | pgrx, sqlx-cli, certain migration/database tools                                      | Often distributed as source packages or upstream binaries                 |
| PGXS / source builds               | Server-side PostgreSQL extensions                                                     | Requires compatibility with server development headers and PostgreSQL ABI |
| Container distributions            | Debezium, monitoring services, isolated test infrastructure                           | Runtime isolation with additional lifecycle and networking considerations |

The principal PGDG package families are:

| APT package                | Capability                                                                     |
| -------------------------- | ------------------------------------------------------------------------------ |
| `postgresql-18`            | PostgreSQL 18 server, engine, and server-side utilities                        |
| `postgresql-client-18`     | PostgreSQL 18 client programs and database maintenance utilities               |
| `postgresql-common`        | Debian/Ubuntu multi-version, multi-cluster infrastructure                      |
| `postgresql-client-common` | Shared PostgreSQL client wrappers                                              |
| `postgresql-contrib`       | Contributed extensions, according to the distribution's packaging arrangements |
| `postgresql-doc-18`        | Locally installed versioned documentation                                      |
| `postgresql-server-dev-18` | Headers and build infrastructure for server extensions                         |
| `libpq5`                   | PostgreSQL client-library runtime                                              |
| `libpq-dev`                | Client-library headers and development infrastructure                          |
| `libecpg-dev`              | Embedded SQL in C support                                                      |
| `postgresql-plpython3-18`  | Optional server-side PL/Python language                                        |
| `postgresql-plperl-18`     | Optional server-side PL/Perl language                                          |
| `postgresql-pltcl-18`      | Optional server-side PL/Tcl language                                           |

Specific package availability varies by Ubuntu release, architecture, and configured APT repositories. The PGDG documentation confirms support for current Ubuntu releases and versioned package conventions.

Primary sources

- PGDG official Ubuntu installation and repository instructions: `https://www.postgresql.org/download/linux/ubuntu/`
- PGDG package catalog and repository information: `https://wiki.postgresql.org/wiki/Apt/Packages`
- Ubuntu binary package index: `https://packages.ubuntu.com/`
- PostgreSQL server-side extension build infrastructure: `https://www.postgresql.org/docs/18/extend-pgxs.html`

### 2.2 `postgresql-common`: Ubuntu's multi-cluster management layer

Debian and Ubuntu supply an additional management abstraction through `postgresql-common`. This allows multiple PostgreSQL major versions and multiple independent clusters to coexist on a host.

| Utility                                 | Capabilities                                                                  |
| --------------------------------------- | ----------------------------------------------------------------------------- |
| `pg_createcluster`                      | Initialize a PostgreSQL cluster under Debian/Ubuntu configuration conventions |
| `pg_ctlcluster`                         | Start, stop, restart, reload, and control a versioned cluster                 |
| `pg_lsclusters`                         | Enumerate clusters, ports, data directories, versions, and status             |
| `pg_dropcluster`                        | Remove a registered cluster and its associated files                          |
| `pg_upgradecluster`                     | Coordinate major-version cluster upgrades                                     |
| `pg_renamecluster`                      | Rename a registered PostgreSQL cluster                                        |
| `pg_conftool`                           | Query and modify cluster-specific PostgreSQL settings                         |
| `pg_wrapper`                            | Select appropriate client binaries and cluster defaults                       |
| `pg_virtualenv`                         | Create temporary PostgreSQL clusters for tests and commands                   |
| `pg_buildext`                           | Build/test extensions against PostgreSQL versions                             |
| `pg_backupcluster`, `pg_restorecluster` | Debian cluster backup/restore utilities in versions providing them            |
| `pg_getwal`                             | Support WAL retrieval workflows in Debian's cluster infrastructure            |

A conventional Ubuntu-managed PostgreSQL 18 cluster named `main` typically has the following structure:

```
/etc/postgresql/18/main/          Configuration
/var/lib/postgresql/18/main/      Data
/usr/lib/postgresql/18/bin/       Version-specific binaries
/usr/share/postgresql/18/         Shared SQL and extension files
postgresql@18-main.service        systemd cluster unit
```

These are Ubuntu/Debian conventions rather than intrinsic requirements of PostgreSQL.

#### `pg_upgradecluster` versus native `pg_upgrade`

`pg_upgradecluster` handles Debian-specific registration, configuration migration, and service integration. Its default migration method can use dump/restore; specifying `--method=upgrade` selects an upgrade approach built around native `pg_upgrade`.

The distinction affects storage requirements, migration time, treatment of indexes, and the compatibility of binary extensions. Collation changes arising from Ubuntu libc/ICU upgrades require separate attention.

#### `pg_virtualenv`: ephemeral real-server environments

`pg_virtualenv` creates one or more disposable PostgreSQL clusters, establishes connection environment variables, executes a command, and destroys those clusters afterward.

It is useful for database extension regression suites, schema migration testing, integration tests, and cross-version compatibility checks. It provides real PostgreSQL execution without requiring an independently maintained server instance for each test.

Primary sources

- `postgresql-common` utility/manpage index: `https://manpages.debian.org/unstable/postgresql-common/index.html`
- Cluster creation: `https://manpages.debian.org/unstable/postgresql-common/pg_createcluster.1.en.html`
- Cluster control: `https://manpages.debian.org/unstable/postgresql-common/pg_ctlcluster.1.en.html`
- Cluster upgrades: `https://manpages.debian.org/unstable/postgresql-common/pg_upgradecluster.1.en.html`
- Disposable test clusters: `https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`
- PostgreSQL extension development: `https://www.postgresql.org/docs/18/extend-pgxs.html`

### 2.3 Extension packaging, activation, and lifecycle

A PostgreSQL extension can involve several separate operations:

1. Installing binaries, shared libraries, SQL definitions, and control files on the Ubuntu host.
2. Configuring server-level preloading where required, usually through `shared_preload_libraries`.
3. Activating SQL-visible functionality in an individual database with `CREATE EXTENSION`.
4. Upgrading installed extension versions through supported `ALTER EXTENSION ... UPDATE` operations.

Not all modules use all four operations. Logical decoding output plugins, background-worker libraries, procedural languages, and conventional SQL extensions may have different activation requirements.

Useful PostgreSQL catalogs and views include:

- `pg_available_extensions`: extensions available to install.
- `pg_available_extension_versions`: versions available from installed extension control/SQL files.
- `pg_extension`: extensions currently installed in the connected database.
- `pg_settings`: configuration state, including settings requiring a restart.

Extension installation is PostgreSQL-major-version-sensitive. Server-side C and Rust binaries must be built against compatible PostgreSQL headers, interfaces, and ABI requirements.

Primary sources

- PostgreSQL extension packaging: `https://www.postgresql.org/docs/18/extend-extensions.html`
- PostgreSQL extension build infrastructure: `https://www.postgresql.org/docs/18/extend-pgxs.html`
- `CREATE EXTENSION` command: `https://www.postgresql.org/docs/18/sql-createextension.html`
- Runtime loading and preloading: `https://www.postgresql.org/docs/18/runtime-config-client.html`
- PGXN community extension catalog: `https://pgxn.org/`
- PGXN client and installation source: `https://github.com/pgxn/pgxnclient`

## 3. Native PostgreSQL command-line utilities

PostgreSQL's standard distribution already includes a substantial operational toolkit. These utilities provide direct access to supported engine mechanisms and often eliminate the need for separate administration scripts or third-party packages.

### 3.1 Database administration and object lifecycle

| Utility                  | Capabilities                                                                                                                |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `psql`                   | Interactive SQL, command scripting, session variables, result formatting, catalog introspection, and meta-command execution |
| `createdb`, `dropdb`     | Database lifecycle operations                                                                                               |
| `createuser`, `dropuser` | Role creation and removal                                                                                                   |
| `vacuumdb`               | Run `VACUUM` and `ANALYZE` on selected tables or across databases, with parallel and staged options                         |
| `reindexdb`              | Rebuild indexes, including supported concurrent modes                                                                       |
| `clusterdb`              | Physically organize a table according to an index                                                                           |
| `pg_isready`             | Determine whether a PostgreSQL server is accepting connections                                                              |
| `pg_config`              | Query version-specific installation paths, build settings, libraries, and headers                                           |
| `ecpg`                   | Preprocess embedded SQL in C applications                                                                                   |

`psql` deserves particular attention because it is more than an interactive terminal.

Its advanced capabilities include `\gexec` for executing SQL dynamically generated by a query, `\gset` for assigning query results to variables, `\copy` for client-side file transfers, script conditionals, configurable error handling through `ON_ERROR_STOP`, and a substantial set of schema-inspection commands.

These mechanisms support compact administrative automation without requiring a general-purpose application to wrap every SQL operation.

Primary sources

- Complete native client-utility index: `https://www.postgresql.org/docs/18/reference-client.html`
- `psql` scripting and meta-commands: `https://www.postgresql.org/docs/18/app-psql.html`
- Database-wide vacuum and statistics: `https://www.postgresql.org/docs/18/app-vacuumdb.html`
- Database-wide index rebuilding: `https://www.postgresql.org/docs/18/app-reindexdb.html`
- PostgreSQL readiness checks: `https://www.postgresql.org/docs/18/app-pg-isready.html`

### 3.2 Cluster, storage, and WAL administration

| Utility             | Capabilities                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------- |
| `initdb`            | Initialize a cluster's foundational settings, encoding, locale, and authentication defaults |
| `pg_ctl`            | Direct server process lifecycle management                                                  |
| `pg_controldata`    | Examine cluster control metadata, checkpoint details, timelines, and WAL state              |
| `pg_checksums`      | Verify, enable, or disable page checksums on an offline cluster                             |
| `pg_upgrade`        | Upgrade a database cluster between compatible major PostgreSQL versions                     |
| `pg_rewind`         | Reconcile a divergent data directory with a surviving source after a timeline fork          |
| `pg_waldump`        | Inspect human-readable WAL records                                                          |
| `pg_walsummary`     | Inspect WAL summary files associated with incremental backups                               |
| `pg_archivecleanup` | Clean unneeded archived WAL files in suitable archive/recovery arrangements                 |
| `pg_test_fsync`     | Characterize supported filesystem synchronization methods                                   |
| `pg_test_timing`    | Assess timing/clock measurement overhead                                                    |
| `pg_resetwal`       | Last-resort recovery intervention for WAL/control information                               |

`pg_rewind` is a specialized recovery tool, not a general database synchronization utility. It can help a former primary rejoin another surviving timeline after failover, but only under PostgreSQL's documented prerequisites.

`pg_resetwal` is much more dangerous. It is intended for circumstances where normal recovery is impossible and its use may leave inconsistent database contents. It should not be treated as a routine repair mechanism.

Primary sources

- Native server utilities: `https://www.postgresql.org/docs/18/reference-server.html`
- Cluster upgrades: `https://www.postgresql.org/docs/18/pgupgrade.html`
- Diverged cluster synchronization: `https://www.postgresql.org/docs/18/app-pgrewind.html`
- WAL record inspection: `https://www.postgresql.org/docs/18/pgwaldump.html`
- WAL summary files: `https://www.postgresql.org/docs/18/app-pgwalsummary.html`
- Checksum verification and management: `https://www.postgresql.org/docs/18/app-pgchecksums.html`
- Emergency WAL reset: `https://www.postgresql.org/docs/18/app-pgresetwal.html`

### 3.3 Physical, logical, and replication-oriented utilities

| Utility               | Functional role                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `pg_dump`             | Produce a logically consistent export of database objects and data                               |
| `pg_dumpall`          | Export database-wide and cluster-global logical definitions                                      |
| `pg_restore`          | Selectively restore objects and data from PostgreSQL archive formats, including parallel restore |
| `pg_basebackup`       | Produce online physical cluster backups through the replication protocol                         |
| `pg_combinebackup`    | Reconstruct a synthetic full backup from full/incremental backup chains                          |
| `pg_verifybackup`     | Check a base backup against its manifest and associated WAL requirements                         |
| `pg_receivewal`       | Receive a continuous stream of WAL from a server                                                 |
| `pg_recvlogical`      | Consume logical decoding data using the replication protocol                                     |
| `pg_createsubscriber` | Convert a physical standby into a logical subscriber under supported conditions                  |

The architectural distinction is the representation being transferred:

- Logical backups capture database objects and rows, which supports selective restoration and some cross-version migration workflows.
- Physical backups preserve database-cluster files and are designed for recovery with compatible server binaries and WAL.
- Logical decoding transmits committed database changes, normally with application-specific or protocol-specific consumption semantics.

`pg_createsubscriber` is a less obvious native capability. It can convert an existing physical replica into a logical subscriber without copying the initial table contents through the ordinary logical-replication initial-copy mechanism. This can materially reduce migration effort for large datasets when its documented assumptions are satisfied.

Primary sources

- `pg_dump`: `https://www.postgresql.org/docs/18/app-pgdump.html`
- `pg_restore`: `https://www.postgresql.org/docs/18/app-pgrestore.html`
- `pg_basebackup`: `https://www.postgresql.org/docs/18/app-pgbasebackup.html`
- `pg_combinebackup`: `https://www.postgresql.org/docs/18/app-pgcombinebackup.html`
- `pg_verifybackup`: `https://www.postgresql.org/docs/18/app-pgverifybackup.html`
- `pg_receivewal`: `https://www.postgresql.org/docs/18/app-pgreceivewal.html`
- `pg_recvlogical`: `https://www.postgresql.org/docs/18/app-pgrecvlogical.html`
- `pg_createsubscriber`: `https://www.postgresql.org/docs/18/app-pgcreatesubscriber.html`

### 3.4 Native incremental physical backups

PostgreSQL 17 introduced native incremental physical backups, retained in PostgreSQL 18.

The principal mechanisms are:

1. `pg_basebackup` produces a full or incremental base backup.
2. PostgreSQL's WAL summarizer records information about which relation blocks changed.
3. `pg_combinebackup` combines the required full and incremental backups into a usable synthetic full backup.
4. `pg_verifybackup` provides manifest and supported WAL verification of backup contents.

This requires `summarize_wal` configuration and adequate retention of WAL summary information. An incremental backup also depends on the continued availability of the relevant earlier backups and manifests.

On Linux, `pg_combinebackup` can exploit supported filesystem cloning operations, notably on reflink-capable filesystems such as appropriately configured XFS or Btrfs. Its `--clone` and `--copy-file-range` modes have different storage-sharing and portability semantics.

This native functionality makes a third-party manager unnecessary merely to obtain the basic ability to generate incremental physical backups. External backup managers remain valuable for repository management, retention, scheduling, transfer, encryption, recovery orchestration, and operational reporting.

Primary sources

- Native incremental-backup operation: `https://www.postgresql.org/docs/18/app-pgbasebackup.html`
- Incremental-backup reconstruction and filesystem cloning: `https://www.postgresql.org/docs/18/app-pgcombinebackup.html`
- WAL summarization settings: `https://www.postgresql.org/docs/18/runtime-config-wal.html`
- WAL summary inspection functions: `https://www.postgresql.org/docs/18/functions-info.html`

## 4. Backup, recovery, and state preservation

Backup tooling should be evaluated against the recovery objective: full physical recovery, logical object reconstruction, restoration to a historical timestamp, cross-version migration, or repeated creation of isolated database states.

### 4.1 Dedicated backup and recovery products

| Tool                             | Key capabilities                                                                                                                           | Main distinction                                                                  |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| pgBackRest                       | Full, differential, and incremental backups; WAL archives; compression, encryption, parallelism, multiple repositories, retention and PITR | Comprehensive PostgreSQL physical backup and recovery manager                     |
| Barman                           | Centralized management of physical backups, WAL, retention, cloud storage, recovery, and multiple PostgreSQL hosts                         | Server- and repository-oriented backup management                                 |
| WAL-G                            | WAL shipping, cloud/object storage backup transfer, compression and incremental workflows                                                  | Cloud/object-storage-oriented backup tooling                                      |
| pg_probackup                     | Physical backup, incremental backup, verification, merge, restore and catalog operations                                                   | Dedicated physical backup alternative with independently maintained compatibility |
| Native PostgreSQL backup clients | `pg_basebackup`, `pg_combinebackup`, `pg_verifybackup`, `pg_receivewal`                                                                    | Underlying supported PostgreSQL backup mechanisms                                 |
| Logical dump utilities           | `pg_dump`, `pg_dumpall`, `pg_restore`                                                                                                      | Object-level export and selective restoration                                     |

### 4.2 pgBackRest

pgBackRest supplies a complete physical backup repository and recovery system.

Its major capabilities include:

- Full, differential, and incremental backups.
- Multiple repositories, including remote/object-storage arrangements.
- Parallelized backup and restore operations.
- Compression and repository encryption.
- WAL archive management.
- Point-in-time recovery to supported time, LSN, or recovery targets.
- Backup expiration, retention, checks, and metadata reporting.
- Repository and recovery workflows that can be operated independently of the application.

The stanza is a central pgBackRest organizational concept, describing a PostgreSQL database cluster and associated backup configuration.

The distinction from native `pg_basebackup` is that pgBackRest manages the backup lifecycle, not merely the data-transfer operation.

Primary sources

- pgBackRest official user guide, covering configuration, backup, restore, WAL, retention, and encryption: `https://pgbackrest.org/user-guide.html`
- pgBackRest configuration reference: `https://pgbackrest.org/configuration.html`
- pgBackRest command reference: `https://pgbackrest.org/command.html`

### 4.3 Barman

Barman provides PostgreSQL backup management with a particular emphasis on operating backup infrastructure independently from database hosts.

It supports physical backup catalogs, WAL collection, retention policies, recovery operations, multiple managed servers, and cloud storage integrations.

Its companion packages and utilities include `barman-cli`, `barman-cli-cloud`, and commands such as:

- `barman-wal-archive`
- `barman-wal-restore`
- `barman-cloud-backup`
- `barman-cloud-restore`
- `barman-cloud-wal-archive`
- `barman-cloud-wal-restore`

These utilities can be used in configurations where backup files and WAL are shipped to a Barman server or directly to supported object storage.

Primary sources

- Barman official documentation index: `https://pgbarman.org/documentation/`
- Barman upstream source and tooling: `https://github.com/EnterpriseDB/barman`
- Barman user and configuration documentation: `https://docs.pgbarman.org/`

### 4.4 WAL-G and pg_probackup

WAL-G is particularly oriented toward WAL archiving, backup upload/download, and cloud/object-storage workflows. Its PostgreSQL integration uses commands such as `wal-push`, `wal-fetch`, `backup-push`, and `backup-fetch`.

pg_probackup provides another independently developed backup system, including incremental and validation features. Its compatibility should be checked against specific PostgreSQL major releases, rather than inferred from its historical PostgreSQL coverage.

Primary sources

- WAL-G PostgreSQL-specific manual: `https://github.com/wal-g/wal-g/blob/master/docs/PostgreSQL.md`
- WAL-G project and general documentation: `https://github.com/wal-g/wal-g`
- pg_probackup capabilities, releases, and source: `https://github.com/postgrespro/pg_probackup`

### 4.5 Recovery distinctions

| Objective                              | Appropriate underlying mechanism                         | Important limitation                                                        |
| -------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------- |
| Recreate an entire compatible cluster  | Physical backup and required WAL                         | Not a cross-version logical conversion                                      |
| Recover to a point in time             | Base backup plus archived WAL                            | Requires a complete recoverable WAL history                                 |
| Restore selected objects               | Logical dump and `pg_restore`                            | Does not reconstruct a complete physical server image                       |
| Rejoin a former primary after failover | `pg_rewind`                                              | Requires suitable timeline and cluster prerequisites                        |
| Maintain an off-host backup repository | pgBackRest, Barman, WAL-G                                | Retention and recoverability require explicit policies                      |
| Verify backed-up files                 | `pg_verifybackup` / backup-manager checks                | Does not prove a restored application will function                         |
| Preserve independent historical states | Backup retention, filesystem snapshots, database cloning | Different mechanisms have different consistency and independence guarantees |

Backups and replication are not substitutes. Replication faithfully propagates changes, including accidental deletions and corruption arising at the logical level. Independent historical backups provide a different recovery capability.

Similarly, `pg_verifybackup` checks against manifests and, for supported formats, required WAL integrity. It does not perform all checks that a running PostgreSQL server would perform after restoration. PostgreSQL explicitly recommends actual recovery tests.

Primary sources

- Continuous archiving and PITR: `https://www.postgresql.org/docs/18/continuous-archiving.html`
- Physical backup limitations and procedures: `https://www.postgresql.org/docs/18/backup-file.html`
- Backup verification semantics: `https://www.postgresql.org/docs/18/app-pgverifybackup.html`

## 5. Replication, high availability, connection pooling, and CDC

Four related functions must be kept separate:

- Replication: moves database state or selected changes between PostgreSQL servers.
- High-availability coordination: elects/promotes a primary and manages failover.
- Connection pooling and routing: manages client connections and server destinations.
- Change-data capture: exports committed database changes to independent consumers.

### 5.1 PostgreSQL native physical replication

Physical streaming replication transmits WAL and maintains a physical standby.

Its capabilities include streaming and archive-based recovery, hot standby queries, synchronous/asynchronous replication, replication slots, cascading standbys, promotion, and physical timeline management.

Physical replication is the natural mechanism for maintaining byte-compatible standbys, but it does not inherently decide which instance should serve as primary after arbitrary failures.

Primary sources

- Warm standby and streaming replication: `https://www.postgresql.org/docs/18/warm-standby.html`
- Hot standby queries and behavior: `https://www.postgresql.org/docs/18/hot-standby.html`
- Replication and WAL sender configuration: `https://www.postgresql.org/docs/18/runtime-config-replication.html`
- Replication slots: `https://www.postgresql.org/docs/18/warm-standby.html`

### 5.2 Native logical replication

Logical replication operates using publications, subscriptions, logical replication slots, and output plugins.

It supports selectively replicating table changes rather than maintaining an identical physical cluster. Relevant capabilities include row filters, column lists, table synchronization, multiple subscriptions, and replication between compatible PostgreSQL versions.

Logical replication does not automatically recreate every database-level object: roles, extensions, arbitrary DDL, and global configuration require separate handling.

PostgreSQL also supports failover-capable logical replication slots. Their state may be synchronized to physical standbys so logical subscriptions can continue after a failover, but that synchronization is asynchronous and must be verified before promotion.

Primary sources

- Logical replication architecture and SQL interfaces: `https://www.postgresql.org/docs/18/logical-replication.html`
- Publication configuration: `https://www.postgresql.org/docs/18/sql-createpublication.html`
- Subscription configuration: `https://www.postgresql.org/docs/18/sql-createsubscription.html`
- Logical replication failover: `https://www.postgresql.org/docs/18/logical-replication-failover.html`
- Logical decoding and output plugins: `https://www.postgresql.org/docs/18/logicaldecoding.html`

### 5.3 High-availability coordination

| Tool             | Operating model                                                                       | Distinctive capability                                                           |
| ---------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Patroni          | PostgreSQL HA controller integrated with a distributed configuration/consensus system | Leader election, failover, switchover, cluster state, REST API, `patronictl`     |
| repmgr / repmgrd | PostgreSQL replication management plus optional management daemon                     | Standby creation, monitoring, follow operations, automated promotion, switchover |
| pg_auto_failover | Monitor/keeper architecture                                                           | PostgreSQL-focused cluster state machine and automated failover                  |
| HAProxy          | TCP proxy and health-checked routing                                                  | Routes client connections according to endpoint health/role information          |
| Keepalived       | Linux virtual IP management                                                           | Floating endpoint/failover behavior                                              |
| etcd / Consul    | Distributed coordination services                                                     | Leader-state coordination and configuration infrastructure for other tools       |

#### Patroni

Patroni coordinates PostgreSQL lifecycle and replication using a distributed configuration store (DCS) or another supported coordination integration.

It offers cluster initialization, replica creation, leader election, controlled switchover, REST endpoints for health/routing, and `patronictl` commands for administration.

The DCS serves an important consistency role. Patroni should not be understood as merely a script that runs `pg_ctl promote` when another instance stops responding.

Primary sources

- Patroni architecture and features: `https://patroni.readthedocs.io/en/latest/`
- Patroni installation and configuration: `https://patroni.readthedocs.io/en/latest/installation.html`
- Patroni REST API: `https://patroni.readthedocs.io/en/latest/rest_api.html`
- Patroni administration commands: `https://patroni.readthedocs.io/en/latest/patronictl.html`

#### repmgr

`repmgr` and `repmgrd` provide management for physical PostgreSQL replication and the operational lifecycle of standbys, failover, and switchover.

Compared with Patroni, the architecture is more centered on PostgreSQL-managed replication and its own node metadata and failover services rather than requiring a general external DCS.

Primary sources

- repmgr documentation and architecture: `https://www.repmgr.org/docs/current/`
- repmgr repository and release information: `https://github.com/EnterpriseDB/repmgr`

#### pg_auto_failover

`pg_auto_failover` uses a monitor service and keepers to coordinate node state transitions. It is a distinct HA approach that avoids deploying etcd or Consul purely for leader coordination, while making the monitor and its recovery semantics important system components.

Primary sources

- pg_auto_failover architecture: `https://pg-auto-failover.readthedocs.io/en/main/architecture.html`
- pg_auto_failover documentation: `https://pg-auto-failover.readthedocs.io/en/main/`
- Upstream source: `https://github.com/hapostgres/pg_auto_failover`

### 5.4 Connection pooling and PostgreSQL proxies

| Tool      | Principal capability                                                                         |
| --------- | -------------------------------------------------------------------------------------------- |
| PgBouncer | Lightweight connection pooling with session, transaction, and statement modes                |
| Pgpool-II | PostgreSQL-aware pooling, health checking, routing, load balancing and HA-related middleware |
| pgagroal  | Multithreaded connection pooling with metrics and administrative interfaces                  |
| Odyssey   | PostgreSQL protocol connection pooling and routing                                           |
| HAProxy   | TCP-level connection routing and health checking                                             |
| SPQR      | PostgreSQL-aware sharding/query routing                                                      |

#### PgBouncer pooling semantics

PgBouncer's pooling modes define different guarantees about the identity and duration of a PostgreSQL server-side connection.

| Mode        | Server connection ownership                           | Consequence                                                 |
| ----------- | ----------------------------------------------------- | ----------------------------------------------------------- |
| Session     | A client owns a backend for the connection's lifetime | Broad session-feature compatibility, less reuse             |
| Transaction | Backend assignment lasts only for a transaction       | Greater reuse but session-state assumptions must be avoided |
| Statement   | Backend assignment is limited to statement execution  | Disallows multi-statement transaction behavior              |

Transaction pooling can affect `LISTEN`, session-level advisory locks, temporary-table lifetimes, session parameters, and SQL `PREPARE`.

PgBouncer supports protocol-level prepared statements under configured conditions, including nonzero `max_prepared_statements`; this does not confer unrestricted SQL-level session state compatibility.

Primary sources

- PgBouncer features and pooling compatibility: `https://www.pgbouncer.org/features.html`
- PgBouncer configuration: `https://www.pgbouncer.org/config.html`
- PgBouncer administration commands: `https://www.pgbouncer.org/usage.html`
- PgBouncer FAQ and prepared-statement behavior: `https://www.pgbouncer.org/faq.html`
- Pgpool-II documentation: `https://www.pgpool.net/docs/latest/en/html/`
- pgagroal documentation: `https://pgagroal.github.io/`
- Odyssey source and configuration: `https://github.com/yandex/odyssey`
- SPQR sharding router: `https://github.com/pg-sharding/spqr`

### 5.5 Change-data capture and logical decoding tooling

| Tool                          | Capability                                                                             |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| Native `pgoutput`             | PostgreSQL logical replication output protocol                                         |
| `pg_recvlogical`              | Stream logical decoding messages to a consumer                                         |
| wal2json                      | JSON serialization of logical decoding changes                                         |
| pglogical                     | Advanced logical replication with selective replication and cross-version capabilities |
| Debezium PostgreSQL connector | Snapshot-to-change-stream coordination through Kafka Connect                           |
| pgcopydb                      | PostgreSQL migration with logical change capture and cutover support                   |

Raw logical decoding plugins are not complete event platforms. A robust CDC system also handles initial snapshots, positions/offsets, failure recovery, downstream consumer coordination, and event delivery semantics.

Debezium supplies much of this additional infrastructure, while remaining dependent on PostgreSQL replication slots, WAL availability, and connector configuration.

Logical decoding slots retain required WAL while consumers lag, making slot monitoring and appropriate retention limits essential.

PostgreSQL 18 also has an `output_plugin_libraries` configuration allowlist for logical output plugins, meaning installation of an external plugin does not necessarily make it usable by a replication client.

Primary sources

- PostgreSQL logical decoding concepts: `https://www.postgresql.org/docs/18/logicaldecoding.html`
- PostgreSQL replication configuration: `https://www.postgresql.org/docs/18/runtime-config-replication.html`
- wal2json plugin: `https://github.com/eulerto/wal2json`
- pglogical extension: `https://github.com/2ndQuadrant/pglogical`
- Debezium PostgreSQL connector: `https://debezium.io/documentation/reference/stable/connectors/postgresql.html`
- pgcopydb CDC and migration: `https://github.com/dimitri/pgcopydb`

## 6. Performance analysis, monitoring, and execution diagnostics

PostgreSQL performance tooling operates at several levels:

1. Individual query plans and measured execution.
2. Aggregated statements and database statistics.
3. Live processes, locks, and wait events.
4. Historical query and infrastructure metrics.
5. Physical storage, WAL, memory, and kernel-level behavior.

Each reveals different evidence. A complete performance investigation often combines multiple levels.

### 6.1 Native query execution diagnostics

| Feature                 | Capabilities                                                                        |
| ----------------------- | ----------------------------------------------------------------------------------- |
| `EXPLAIN`               | Query plan structure, estimated costs, cardinalities, join strategies, access paths |
| `EXPLAIN ANALYZE`       | Actual plan execution with measured row counts, loops, and execution metrics        |
| `EXPLAIN (BUFFERS)`     | Shared, local, and temporary-buffer usage                                           |
| `EXPLAIN (WAL)`         | WAL generation attributable to execution                                            |
| `EXPLAIN (SETTINGS)`    | Relevant nondefault planner settings                                                |
| `EXPLAIN (FORMAT JSON)` | Structured query plans suitable for further programmatic analysis                   |
| `auto_explain`          | Automatic plan logging for qualifying application statements                        |
| `pg_stat_statements`    | Query-level aggregated planning/execution statistics across workload history        |

PostgreSQL 18 also exposes additional execution instrumentation through `EXPLAIN` options such as `MEMORY` and `SERIALIZE`.

The most important distinction is estimated versus measured execution. Plain `EXPLAIN` reports the optimizer's selected plan and estimates; `EXPLAIN ANALYZE` actually runs the statement and collects execution evidence.

`EXPLAIN ANALYZE` itself adds instrumentation overhead, so timing measurements must be interpreted with that qualification. PostgreSQL explicitly documents the effect of node-level timing and the option to disable that timing while retaining other execution information.

`auto_explain` can capture plans from real application activity, including nested statements executed inside functions when configured appropriately. However, enabling per-node timing for all qualifying statements can introduce substantial overhead.

Primary sources

- SQL `EXPLAIN` syntax and options: `https://www.postgresql.org/docs/18/sql-explain.html`
- Detailed plan interpretation: `https://www.postgresql.org/docs/18/using-explain.html`
- Automatic execution-plan logging: `https://www.postgresql.org/docs/18/auto-explain.html`
- Query-level aggregate statistics: `https://www.postgresql.org/docs/18/pgstatstatements.html`

### 6.2 Native activity, wait, lock, and I/O statistics

| PostgreSQL facility             | Information exposed                                                              |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `pg_stat_activity`              | Current sessions, queries, state, backend identity, and waits                    |
| `pg_locks`                      | Lock types, requested modes, granted locks, and contention                       |
| `pg_blocking_pids()`            | Backend processes blocking another process                                       |
| `pg_stat_statements`            | Query frequency, planning/execution time, row counts, buffer I/O, WAL statistics |
| `pg_stat_io`                    | Database I/O grouped by backend type, object, and context                        |
| `pg_stat_wal`                   | WAL generation and related I/O activity                                          |
| `pg_stat_bgwriter`              | Background writing activity                                                      |
| `pg_stat_checkpointer`          | Checkpoint-related statistics                                                    |
| `pg_stat_database`              | Database-wide transactions, sessions, conflicts, and related counters            |
| `pg_stat_replication`           | Physical replication sender state                                                |
| `pg_stat_subscription*`         | Logical replication subscriber activity and statistics                           |
| `pg_stat_progress_vacuum`       | Vacuum progress                                                                  |
| `pg_stat_progress_create_index` | Index build progress                                                             |
| `pg_stat_progress_copy`         | COPY progress                                                                    |
| `pg_stat_progress_basebackup`   | Base backup progress                                                             |
| `pg_stat_progress_analyze`      | ANALYZE progress                                                                 |

PostgreSQL 18 extends its available statistics, including per-backend I/O information and richer WAL/I/O accounting.

These views expose engine-maintained metrics without requiring external instrumentation, but cumulative counters, resets, sampling intervals, and backend lifetimes affect interpretation.

Primary sources

- PostgreSQL statistics collector and monitoring views: `https://www.postgresql.org/docs/18/monitoring-stats.html`
- Lock monitoring: `https://www.postgresql.org/docs/18/view-pg-locks.html`
- System administration/statistics functions: `https://www.postgresql.org/docs/18/functions-admin.html`
- Runtime statistics configuration: `https://www.postgresql.org/docs/18/runtime-config-statistics.html`

### 6.3 Interactive and historical monitoring utilities

| Tool                 | Distinctive capabilities                                                                                             |
| -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| pg_activity          | Interactive terminal view of active PostgreSQL processes, queries, locks, CPU, memory and I/O information            |
| pgcenter             | Interactive terminal monitoring of PostgreSQL statistics                                                             |
| pg_top               | `top`-style PostgreSQL activity and process inspection                                                               |
| pgBadger             | PostgreSQL log analysis and interactive reports covering queries, waits, errors, sessions, and latency distributions |
| pgmetrics            | Structured collection of PostgreSQL metrics and diagnostic snapshots                                                 |
| postgres_exporter    | Export PostgreSQL metrics to Prometheus-compatible monitoring systems                                                |
| pgwatch              | PostgreSQL-specific metrics collection, storage, and dashboard ecosystem                                             |
| PoWA                 | Historical SQL workload analysis integrating multiple statistics extensions                                          |
| Prometheus + Grafana | Time-series metrics collection, historical queries, dashboards, and alerting                                         |

#### pgBadger

pgBadger reads PostgreSQL logs and generates reports describing query workload, durations, errors, connections, lock-related events, and related activity.

It supports multiple PostgreSQL logging formats, compressed logs, parallel analysis, and incremental report generation.

This makes it particularly useful for reconstructing historical behavior when there is no continuously running query profiler.

#### pgmetrics

pgmetrics collects detailed PostgreSQL metrics into structured output, making it useful for repeated diagnostic snapshots or comparison of database state at different points in time.

#### PoWA

PoWA integrates PostgreSQL query statistics with complementary instrumentation such as `pg_stat_kcache` and `pg_qualstats`.

It supports historical workload inspection and can help relate observed query behavior to index suggestions and predicate statistics.

Primary sources

- pg_activity: `https://github.com/dalibo/pg_activity`
- pg_activity detailed CLI reference: `https://github.com/dalibo/pg_activity/blob/master/docs/man/pg_activity.pod`
- pgcenter: `https://github.com/lesovsky/pgcenter`
- pg_top: `https://github.com/markwkm/pg_top`
- pgBadger: `https://github.com/darold/pgbadger`
- pgmetrics: `https://github.com/rapidloop/pgmetrics`
- Prometheus PostgreSQL exporter: `https://github.com/prometheus-community/postgres_exporter`
- pgwatch: `https://github.com/cybertec-postgresql/pgwatch`
- PoWA: `https://github.com/powa-team/powa`
- Prometheus documentation: `https://prometheus.io/docs/`
- Grafana documentation: `https://grafana.com/docs/`

The historical `pgwatch2` repository was archived; current pgwatch development uses the `cybertec-postgresql/pgwatch` project.

### 6.4 Advanced optimizer and query instrumentation

Several specialized extensions expose information not fully represented by ordinary PostgreSQL statistics.

| Extension         | Mechanism                                                | Engineering significance                                      |
| ----------------- | -------------------------------------------------------- | ------------------------------------------------------------- |
| HypoPG            | Session-local hypothetical indexes                       | Evaluate optimizer choices without constructing real indexes  |
| pg_qualstats      | Statistics on predicates and column combinations         | Identify frequently used predicates and potential index needs |
| pg_stat_kcache    | Kernel resource usage attributed to database work        | Analyze CPU and operating-system I/O effects                  |
| pg_wait_sampling  | Periodic sampling of backend wait events                 | Build profiles of database contention                         |
| pg_track_settings | Historical configuration change tracking                 | Correlate tuning changes with workload behavior               |
| pg_hint_plan      | Planner hints and plan-influence mechanisms              | Investigate or constrain planner choices                      |
| PoWA              | Integration/analysis of multiple instrumentation sources | Historical optimization investigation                         |

#### HypoPG

HypoPG creates virtual index definitions visible to the planner in the current session.

These indexes consume no actual table-index storage and can be evaluated through `EXPLAIN`. The resulting plan is an estimate of how PostgreSQL might behave with the index—not a runtime benchmark of a physically constructed index.

HypoPG is therefore useful for reducing the amount of experimental index creation and cleanup required during query tuning.

#### pg_qualstats

`pg_qualstats` tracks predicates from `WHERE` and `JOIN` clauses, including frequently combined or correlated columns.

This complements `pg_stat_statements`: the latter identifies expensive query shapes, while `pg_qualstats` provides information about predicates used within those queries.

#### pg_wait_sampling

PostgreSQL exposes the current wait event for each relevant backend. `pg_wait_sampling` periodically samples those events and accumulates in-memory histories/profiles. It can relate waits to query identifiers where appropriate.

The distinction is important: wait samples describe how often a backend was observed in a particular wait state. They are not necessarily exact per-query wall-clock durations.

Primary sources

- HypoPG: `https://github.com/HypoPG/hypopg`
- pg_qualstats: `https://github.com/powa-team/pg_qualstats`
- pg_stat_kcache: `https://github.com/powa-team/pg_stat_kcache`
- pg_wait_sampling: `https://github.com/postgrespro/pg_wait_sampling`
- pg_track_settings: `https://github.com/powa-team/pg_track_settings`
- pg_hint_plan: `https://github.com/ossc-db/pg_hint_plan`
- PoWA integration: `https://github.com/powa-team/powa`

### 6.5 Physical storage, memory, WAL, and corruption inspection

PostgreSQL's contributed modules include unusually capable low-level storage inspection tools.

| Tool/module         | Capability                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------- |
| `amcheck`           | Validate structural and selected logical invariants of supported access-method structures |
| `pg_amcheck`        | CLI automation of amcheck validation                                                      |
| `pageinspect`       | Examine physical heap and index pages                                                     |
| `pgstattuple`       | Measure tuple, dead-tuple, and free-space statistics                                      |
| `pg_freespacemap`   | Inspect free-space map information                                                        |
| `pg_visibility`     | Inspect visibility map information, relevant to vacuum and index-only scans               |
| `pg_buffercache`    | Examine PostgreSQL's shared-buffer contents                                               |
| `pg_prewarm`        | Populate relevant caches before query workloads                                           |
| `pgrowlocks`        | Inspect row-level lock information                                                        |
| `pg_walinspect`     | Inspect WAL contents through SQL                                                          |
| `pg_logicalinspect` | Inspect logical decoding-related internal information                                     |
| `pg_overexplain`    | Provide additional execution-plan inspection information                                  |
| `pg_waldump`        | Inspect WAL records from system files                                                     |
| `pg_surgery`        | Dangerous low-level emergency tuple intervention                                          |
| `pg_checksums`      | Verify or manage on-disk page checksums for an offline cluster                            |

`pageinspect` exposes raw database storage structures, including heap pages, B-tree pages, and other index types. This is a diagnostic mechanism rather than an abstraction for normal application data access.

`pg_visibility` is particularly relevant when investigating why index-only scans still require heap access, while `pg_freespacemap` can help understand page-space reuse. Free-space map values are approximate rather than exact.

Primary sources

- Complete PostgreSQL contributed module catalog: `https://www.postgresql.org/docs/18/contrib.html`
- amcheck: `https://www.postgresql.org/docs/18/amcheck.html`
- pg_amcheck: `https://www.postgresql.org/docs/18/app-pgamcheck.html`
- pageinspect: `https://www.postgresql.org/docs/18/pageinspect.html`
- pgstattuple: `https://www.postgresql.org/docs/18/pgstattuple.html`
- pg_freespacemap: `https://www.postgresql.org/docs/18/pgfreespacemap.html`
- pg_visibility: `https://www.postgresql.org/docs/18/pgvisibility.html`
- pg_buffercache: `https://www.postgresql.org/docs/18/pgbuffercache.html`
- pg_prewarm: `https://www.postgresql.org/docs/18/pgprewarm.html`
- pg_walinspect: `https://www.postgresql.org/docs/18/pgwalinspect.html`
- pg_logicalinspect: `https://www.postgresql.org/docs/18/pglogicalinspect.html`
- pg_overexplain: `https://www.postgresql.org/docs/18/pgoverexplain.html`
- pg_surgery: `https://www.postgresql.org/docs/18/pgsurgery.html`

### 6.6 Linux kernel and host-level instrumentation

PostgreSQL-specific diagnostics can be combined with Linux performance instrumentation to identify causes outside the database executor.

| Ubuntu tool/package family             | Relevant investigation                                                     |
| -------------------------------------- | -------------------------------------------------------------------------- |
| `sysstat` (`iostat`, `pidstat`, `sar`) | Storage throughput, latency, per-process CPU, and historical host activity |
| `procps` (`vmstat`, `top`, `ps`)       | Resource pressure, scheduling, and process inspection                      |
| `htop`, `atop`                         | Interactive resource utilization                                           |
| `linux-perf`                           | Native CPU sampling, instruction hotspots, call graphs                     |
| `bpftrace`                             | Kernel/user-space tracing through eBPF                                     |
| BCC tracing utilities                  | Predefined Linux tracing and profiling programs                            |
| `strace`                               | System-call and signal behavior                                            |
| `lsof`, `fuser`, `ss`                  | Open files, sockets, and networking                                        |
| `journalctl`, `systemctl`              | Service lifecycle, crashes, resource limitations, logs                     |
| `fio`                                  | Controlled filesystem/block-device performance testing                     |

Linux instrumentation becomes especially useful when PostgreSQL views indicate a problem but do not identify the host-level cause.

For example, `pg_stat_statements` might reveal a CPU-dominated query; `EXPLAIN` can describe the SQL executor's work, while `perf` can identify native functions consuming CPU. Similarly, `pg_stat_io` and `iostat` can help distinguish database I/O patterns from broader storage-device behavior.

Primary sources

- Linux perf documentation: `https://perf.wiki.kernel.org/`
- bpftrace reference: `https://bpftrace.org/docs/`
- BCC tracing tools: `https://github.com/iovisor/bcc`
- fio documentation: `https://fio.readthedocs.io/`
- sysstat utilities: `https://github.com/sysstat/sysstat`

## 7. Maintenance, bloat reduction, integrity, and partition lifecycle

### 7.1 Native maintenance

| Mechanism     | Functionality                                                            | Principal tradeoff                                                                  |
| ------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Autovacuum    | Automatic tuple cleanup, statistics maintenance, transaction ID freezing | Requires appropriate workload-specific tuning                                       |
| `VACUUM`      | Reclaim reusable tuple space and maintain visibility information         | Does not normally fully compact on-disk table files                                 |
| `ANALYZE`     | Refresh statistics used by the query optimizer                           | Statistics are estimates that may not represent every workload distribution         |
| `VACUUM FULL` | Rewrite a table into a compact physical representation                   | Disruptive locking and additional storage requirements                              |
| `REINDEX`     | Rebuild indexes                                                          | Lock behavior depends on operation and use of `CONCURRENTLY`                        |
| `CLUSTER`     | Physically reorder table contents according to an index                  | One-time physical ordering, not continuously maintained                             |
| `pg_amcheck`  | Database structure validation                                            | Detects supported corruption classes, not arbitrary application-level inconsistency |

Primary sources

- Routine vacuuming: `https://www.postgresql.org/docs/18/routine-vacuuming.html`
- Autovacuum configuration: `https://www.postgresql.org/docs/18/runtime-config-autovacuum.html`
- Vacuum command: `https://www.postgresql.org/docs/18/sql-vacuum.html`
- Reindexing: `https://www.postgresql.org/docs/18/sql-reindex.html`
- Table clustering: `https://www.postgresql.org/docs/18/sql-cluster.html`

### 7.2 pg_repack and pg_squeeze

pg_repack reorganizes tables and indexes while allowing most normal access to continue.

It typically creates replacement storage, captures concurrent changes, and performs a final swap. This allows major physical reorganization without the extended exclusive lock normally associated with `VACUUM FULL`.

Its important characteristics include:

- Table and index bloat reduction.
- Physical table ordering.
- Online rebuilding and replacement.
- Additional working-storage requirements.
- Final locking and concurrent-write overhead.
- Requirements concerning usable unique indexes/keys for certain operations.

`pg_repack` has a client CLI and server extension component; they must be compatible.

pg_squeeze provides another table-bloat reduction mechanism, oriented toward background or online maintenance using techniques including logical decoding.

Its locking, replication-slot, WAL, and storage characteristics differ from those of `pg_repack`, so the two should not be treated as interchangeable implementations.

Primary sources

- pg_repack overview and restrictions: `https://github.com/reorg/pg_repack/blob/master/doc/pg_repack.rst`
- pg_repack source and releases: `https://github.com/reorg/pg_repack`
- pg_squeeze source and documentation: `https://github.com/cybertec-postgresql/pg_squeeze`

### 7.3 Partition lifecycle with pg_partman

PostgreSQL's native declarative partitioning supplies range, list, and hash partitioned tables with pruning and partition-aware execution.

However, maintaining a changing population of partitions is a separate operational concern.

pg_partman supplies partition lifecycle management, including:

- Automatic creation of future partitions.
- Maintenance of time- and ID-oriented partition sets.
- Retention policies and older-partition cleanup.
- Partition maintenance procedures.
- Integration with external schedules or PostgreSQL job scheduling.

This can replace application-specific partition DDL generation and retention scripts.

Native partitions still retain normal PostgreSQL constraints concerning locks, indexes, referential relationships, planning, and data movement. Partitioning should not be assumed to improve performance for every query shape.

Primary sources

- Native declarative partitioning: `https://www.postgresql.org/docs/18/ddl-partitioning.html`
- Partitioning and pruning configuration: `https://www.postgresql.org/docs/18/runtime-config-query.html`
- pg_partman source, configuration and maintenance: `https://github.com/pgpartman/pg_partman`

### 7.4 Database and OS-level task scheduling

| Tool                                   | Scheduling capabilities                                                          |
| -------------------------------------- | -------------------------------------------------------------------------------- |
| pg_cron                                | Cron-like PostgreSQL job scheduling through a server extension/background worker |
| pgAgent                                | External job scheduler supporting SQL and other job steps                        |
| Ubuntu `cron`                          | General-purpose recurring commands                                               |
| `systemd` timers                       | Scheduled execution with service dependencies, logging, and resource settings    |
| PostgreSQL triggers/background workers | Event- or server-driven execution under PostgreSQL-specific semantics            |

pg_cron stores job metadata in PostgreSQL and uses a background worker to manage job execution. It can schedule recurring SQL maintenance directly in the database environment.

Combining pg_partman with pg_cron provides a database-managed partition lifecycle without separately implementing a maintenance daemon.

By contrast, systemd timers can run even when PostgreSQL is not accepting connections; their lifecycle is not owned by the database process.

Primary sources

- pg_cron architecture, syntax, installation and job management: `https://github.com/citusdata/pg_cron`
- pgAgent scheduler documentation: `https://www.pgadmin.org/docs/pgadmin4/latest/pgagent.html`
- systemd timer specification: `https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html`

## 8. Schema evolution, migrations, and database state management

Schema management spans several distinct capabilities:

- Versioned migrations: apply an ordered history of changes.
- Dependency-aware migrations: model prerequisites and reversible deployment steps.
- Declarative reconciliation: calculate DDL needed to transform one schema into another.
- Online schema evolution: manage DDL and data transformation while workloads continue.
- Versioned schema interfaces: expose different schema representations simultaneously.
- Ephemeral database states: create isolated copies for testing and validation.

### 8.1 Main schema and migration tools

| Tool                           | Model                                            | Major capabilities                                                           |
| ------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------------------- |
| Sqitch                         | Dependency-aware migration history               | Deploy, revert, verify, change dependencies, tags and plans                  |
| Flyway                         | Versioned and repeatable migration scripts       | Migration ordering, metadata, validation, checksums                          |
| Liquibase                      | Changelogs and database changeSets               | Schema changes, contexts, preconditions, rollback, diff and governance       |
| Dbmate                         | Lightweight sequential SQL migrations            | Schema versions, up/down SQL, schema dump                                    |
| Goose                          | Versioned SQL/Go migrations                      | Migration runner, embedded migrations                                        |
| golang-migrate                 | Versioned up/down migrations                     | CLI and library integration                                                  |
| tern                           | PostgreSQL-oriented migration management         | Migration tracking using the pgx ecosystem                                   |
| Atlas                          | Declarative and versioned migrations             | Schema inspection, desired-state reconciliation, planning, migration linting |
| pg-schema-diff                 | PostgreSQL schema diffing                        | DDL generation, online migration techniques, hazard analysis                 |
| pgroll                         | Expand/contract and simultaneous schema versions | Backfills, compatibility views, reversible schema transitions                |
| Native `pg_dump --schema-only` | Schema export                                    | Capture database object definitions, without transition planning             |

### 8.2 Sqitch: deployment, reversion, and verification

Sqitch models each database change with potentially three explicit scripts:

- Deployment.
- Reversion.
- Verification.

Changes also have dependency relationships and plan history.

`verify` checks whether deployed changes correspond to the plan and runs their associated verification scripts. This enables database state validation that goes beyond checking a migration-history version number.

However, Sqitch does not infer arbitrary application invariants. The quality of verification depends on the verification logic supplied.

Primary sources

- Sqitch complete command/manual reference: `https://sqitch.org/docs/manual/sqitch/`
- Deploy command and atomicity semantics: `https://sqitch.org/docs/manual/sqitch-deploy/`
- Reversion behavior: `https://sqitch.org/docs/manual/sqitch-revert/`
- Verification behavior: `https://sqitch.org/docs/manual/sqitch-verify/`

### 8.3 Flyway, Liquibase, Dbmate, Goose, and tern

These tools manage migration history with differing levels of sophistication and ecosystem integration.

Flyway and Liquibase provide broad database-platform support and mature migration management, while Dbmate, Goose, and tern are comparatively compact approaches.

Liquibase supports structured changelogs and preconditions, while Flyway has distinct versioned and repeatable migration concepts. Their advanced commercial and governance capabilities should be distinguished from features available in freely distributed editions.

Primary sources

- Flyway documentation: `https://documentation.red-gate.com/fd`
- Liquibase documentation: `https://docs.liquibase.com/`
- Dbmate: `https://github.com/amacneil/dbmate`
- Goose: `https://github.com/pressly/goose`
- golang-migrate: `https://github.com/golang-migrate/migrate`
- tern: `https://github.com/jackc/tern`

### 8.4 Atlas: desired-state schema reconciliation

Atlas supports a model where the desired database schema is declared and compared with the current schema.

It can:

- Inspect existing database structures.
- Represent desired schemas using SQL, HCL, database URLs, or supported external definitions.
- Generate candidate migration plans.
- Apply approved schema changes.
- Use advisory locks to coordinate migration executions.
- Produce machine-readable output for automation.
- Analyze some migration hazards.

A consequential edition distinction: Atlas Pro includes additional schema-object support and advanced analysis/governance functionality not universally available in its free edition. Its official reference identifies functions, views, triggers, roles, extensions, and other objects as requiring Atlas Pro for certain declarative workflows.

Primary sources

- Atlas declarative migrations: `https://atlasgo.io/declarative/apply`
- Atlas versioned migration concepts: `https://atlasgo.io/versioned/intro`
- Atlas PostgreSQL integration: `https://atlasgo.io/guides/postgres`

### 8.5 pg-schema-diff: PostgreSQL-aware migration plans

Stripe's `pg-schema-diff` compares PostgreSQL schemas and generates plans for converting one state into another.

It includes awareness of important PostgreSQL online DDL techniques:

- Concurrent index creation/rebuilding.
- Staged constraint creation and validation.
- Transaction/lock timing restrictions.
- Migration hazards such as access-exclusive locks, data deletion, or index build cost.
- Planning from database introspection or SQL schema definitions.

This is more than textual comparison of `pg_dump` outputs. The tool uses PostgreSQL schema understanding to generate transition statements and flag operations with important operational consequences.

It is not a guarantee that every migration can be executed without blocking writes.

Primary sources

- pg-schema-diff source and main usage guide: `https://github.com/stripe/pg-schema-diff`
- Migration hazard definitions and planner structure: `https://github.com/stripe/pg-schema-diff/blob/main/CLAUDE.md`

### 8.6 pgroll: simultaneous schema representations

`pgroll` addresses online schema compatibility by supporting multiple versions of a database schema during an ongoing migration.

Its mechanism uses versioned views over physical tables, together with supporting columns, triggers, and backfill operations when required.

This enables old and new clients to reference different schema representations while data transitions occur.

Important constraints include compatibility of application queries with views, data transformation semantics, and PostgreSQL row-security behavior.

A documented PostgreSQL 14 caveat is particularly important: `pgroll` versioned views cannot use `security_invoker` in PostgreSQL 14, so table RLS policies may not be honored as expected through these views. PostgreSQL 15 introduced the relevant view feature.

Primary sources

- pgroll concepts, operations, and limitations: `https://github.com/xataio/pgroll`
- pgroll documentation entry point: `https://github.com/xataio/pgroll/blob/main/docs/getting-started.md`
- pgroll project documentation: `https://pgroll.com/`

### 8.7 Ephemeral database state, cloning, and migration testing

| Mechanism                             | Capability                                                 | Main distinction                                                   |
| ------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `pg_virtualenv`                       | Create temporary real PostgreSQL clusters                  | Very lightweight for tests and CLI execution                       |
| Native `CREATE DATABASE ... TEMPLATE` | Clone another database in the same cluster                 | Uses PostgreSQL's database-template constraints                    |
| `pg_dump` / `pg_restore`              | Construct a new database from logical definitions and rows | Relatively portable, but potentially expensive for large datasets  |
| `pg_basebackup`                       | Create full physical cluster state                         | Cluster-oriented, version-sensitive                                |
| DBLab Engine                          | Copy-on-write thin database clones and branching           | Efficient isolated test states built on storage snapshotting       |
| pgcopydb                              | PostgreSQL copy, comparison, and migration cutover         | Database-to-database migration rather than filesystem thin cloning |

DBLab Engine uses copy-on-write storage technologies such as ZFS and LVM to create independent writable database clones without copying the complete dataset for each clone.

This changes the economics of repeated tests against large datasets, although storage setup, data sanitization, and snapshot consistency remain important.

DBLab documents PostgreSQL support through version 18 and distinguishes its ZFS and LVM behavior.

Primary sources

- DBLab Engine architecture and cloning: `https://github.com/postgres-ai/database-lab-engine`
- DBLab copy-on-write model: `https://postgres.ai/products/how-it-works`
- DBLab operational documentation: `https://postgres.ai/docs/how-to-guides/cloning`
- PostgreSQL temporary cluster tooling: `https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`
- Native database cloning and templates: `https://www.postgresql.org/docs/18/manage-ag-templatedbs.html`

## 9. Data transfer, database migration, federation, and external engines

PostgreSQL integration tooling operates through several distinct mechanisms:

- Bulk data transfer moves snapshots of rows.
- Database migration reconstructs schemas and data on another system.
- Foreign data wrappers expose external data as PostgreSQL relations.
- Change-data capture preserves a stream of subsequent changes.
- External execution engines process PostgreSQL data using another query engine.

### 9.1 Bulk movement and database migration

| Tool                     | Capabilities                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| `COPY` / `\copy`         | Native PostgreSQL high-throughput import/export and client/server-side transfer                   |
| `pg_dump` / `pg_restore` | Logical PostgreSQL export/restore with selective-object capabilities                              |
| pgcopydb                 | Parallel PostgreSQL-to-PostgreSQL migration, schema/data comparison and CDC-assisted cutover      |
| pgloader                 | MySQL, SQLite, SQL Server and structured-file migration into PostgreSQL with type transformations |
| pg_chameleon             | MySQL-to-PostgreSQL migration and replication                                                     |
| ogr2ogr                  | Vector geospatial import, transformation, and export                                              |
| osm2pgsql                | OpenStreetMap ingestion and update processing                                                     |
| pg_bulkload              | Specialized bulk-loading functionality                                                            |

#### pgcopydb

`pgcopydb` provides distinct phases for PostgreSQL-to-PostgreSQL migration: schema transfer, parallel table data copying, indexes, constraints, sequences, large objects, comparison, and optional logical decoding catch-up.

Its `clone --follow` mechanism can capture changes while the initial copy proceeds and replay them toward cutover. The documentation explains that change prefetching can limit the amount of WAL that needs to remain on the source server during large migrations.

Its data comparison uses table-level row counts and checksums, not a complete proof of every individual row's equality.

Primary sources

- pgcopydb architecture and commands: `https://github.com/dimitri/pgcopydb`
- pgcopydb documentation: `https://pgcopydb.readthedocs.io/en/latest/`
- CDC catch-up and logical decoding: `https://pgcopydb.readthedocs.io/en/latest/ref/pgcopydb_follow.html`
- Data and schema comparison: `https://pgcopydb.readthedocs.io/en/v0.18/ref/pgcopydb_compare.html`

#### pgloader

`pgloader` is especially useful for heterogeneous database migration.

It can inspect source systems, transform types, define casting rules, and load data concurrently. Its scope is broader than transferring CSV files, because it can use source database metadata to drive import behavior.

It does not guarantee automatic conversion of every proprietary database feature, procedure, trigger, or complex schema object.

Primary sources

- pgloader repository and commands: `https://github.com/dimitri/pgloader`
- pgloader documentation: `https://pgloader.readthedocs.io/`

#### Native COPY

PostgreSQL `COPY` can execute within the server, while `psql \copy` directs file I/O through the client process.

This distinction affects filesystem permissions, data paths, and whether files need to exist on the database server itself.

Primary sources

- PostgreSQL COPY statement: `https://www.postgresql.org/docs/18/sql-copy.html`
- psql `\copy` behavior: `https://www.postgresql.org/docs/18/app-psql.html`

### 9.2 Foreign data wrappers (FDWs)

PostgreSQL's SQL/MED infrastructure exposes foreign tables representing data stored outside the local PostgreSQL database.

| Extension        | Data integration                                     |
| ---------------- | ---------------------------------------------------- |
| `postgres_fdw`   | Remote PostgreSQL servers                            |
| `file_fdw`       | Structured files accessible to the PostgreSQL server |
| `mysql_fdw`      | MySQL/MariaDB                                        |
| `oracle_fdw`     | Oracle                                               |
| `tds_fdw`        | SQL Server and other TDS-compatible systems          |
| `sqlite_fdw`     | SQLite databases                                     |
| `parquet_fdw`    | Parquet files                                        |
| `parquet_s3_fdw` | Parquet files in S3-compatible storage               |
| Multicorn        | Framework for Python-implemented FDWs                |
| PGSpider         | FDW-based distributed/federated PostgreSQL execution |

FDWs can expose remote data through ordinary SQL queries, sometimes with predicate, projection, aggregate, join, or modification pushdown.

The extent of this functionality depends on the FDW. Transaction behavior, cost estimation, data-type conversion, network failure handling, and execution performance can differ substantially from local tables.

`postgres_fdw` is especially capable because both sides use PostgreSQL semantics. It supports remote planning/pushdown behaviors and connection reuse, but still does not turn independent PostgreSQL instances into one physical transactional database.

Primary sources

- PostgreSQL foreign-data-wrapper architecture: `https://www.postgresql.org/docs/18/postgres-fdw.html`
- PostgreSQL file FDW: `https://www.postgresql.org/docs/18/file-fdw.html`
- MySQL FDW: `https://github.com/EnterpriseDB/mysql_fdw`
- Oracle FDW: `https://github.com/laurenz/oracle_fdw`
- TDS FDW: `https://github.com/tds-fdw/tds_fdw`
- SQLite FDW: `https://github.com/pgspider/sqlite_fdw`
- Parquet FDW: `https://github.com/adjust/parquet_fdw`
- S3 Parquet FDW: `https://github.com/pgspider/parquet_s3_fdw`
- Multicorn: `https://github.com/Segfault-Inc/Multicorn`
- PGSpider: `https://github.com/pgspider/pgspider`

Some less frequently maintained FDWs are not confirmed to support PostgreSQL 18. For example, `parquet_s3_fdw` documents supported PostgreSQL majors through 17 in its upstream repository. Its inclusion here describes the capability, not an assurance of immediate installation compatibility.

### 9.3 DuckDB, Apache Arrow, and analytical integration

| Tool or component           | Execution model                                                                                           |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| DuckDB `postgres` extension | DuckDB reads and writes PostgreSQL data through an external connection                                    |
| pg_duckdb                   | DuckDB functionality available through a PostgreSQL server extension                                      |
| pg_parquet                  | Import/export of Parquet data through PostgreSQL integration                                              |
| Apache Arrow Flight SQL     | SQL-query transport and Arrow-oriented interoperability protocol requiring appropriate providers/adapters |
| pg_bulkload                 | Specialized PostgreSQL data-loading path                                                                  |

#### DuckDB's external PostgreSQL integration

DuckDB can attach a running PostgreSQL database as a catalog and query its tables through DuckDB SQL.

Its PostgreSQL extension supports reading and certain write operations, along with configuration for connection caching, connection limits, binary COPY transfer, and experimental filter pushdown.

It also exposes functions for executing SQL directly on the PostgreSQL server.

This creates several options: accessing remote rows directly, copying them into DuckDB for repeated analytics, or transferring derived results back to PostgreSQL.

#### pg_duckdb

`pg_duckdb` has the opposite integration direction: DuckDB capabilities are embedded in the PostgreSQL server environment.

The two approaches therefore have different execution ownership, resource accounting, compatibility, and transaction boundaries.

Primary sources

- DuckDB PostgreSQL extension architecture: `https://duckdb.org/docs/current/core_extensions/postgres/overview`
- DuckDB PostgreSQL extension functions: `https://duckdb.org/docs/current/core_extensions/postgres/functions`
- pg_duckdb: `https://github.com/duckdb/pg_duckdb`
- pg_parquet: `https://github.com/CrunchyData/pg_parquet`
- Apache Arrow Flight SQL specification: `https://arrow.apache.org/docs/format/FlightSql.html`
- pg_bulkload: `https://github.com/ossc-db/pg_bulkload`

## 10. Security, auditing, anonymization, and policy enforcement

PostgreSQL security tooling spans native authentication and authorization, audit instrumentation, data masking, encryption functions, and operating-system confinement.

### 10.1 Native PostgreSQL security

| Mechanism                                | Capability                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| `pg_hba.conf`                            | Authentication policy by connection type, database, role, and client source    |
| `pg_ident.conf`                          | External-to-database identity mapping                                          |
| SCRAM-SHA-256                            | Password authentication                                                        |
| Client/server TLS                        | Encrypted connections and optional certificate-based validation/authentication |
| PostgreSQL roles                         | Identity, authorization, and privilege delegation                              |
| `GRANT`, `REVOKE`                        | Object-level privileges                                                        |
| Row-level security (RLS)                 | SQL-enforced row access policies                                               |
| `SECURITY DEFINER` / `SECURITY INVOKER`  | Function execution privilege semantics                                         |
| `pgcrypto`                               | Cryptographic functions exposed through SQL                                    |
| `sslmode=verify-full` and libpq settings | Client-side endpoint identity validation                                       |
| `pg_service.conf`, `.pgpass`             | Client connection and credential configuration                                 |

PostgreSQL row-level security is a particularly important engine capability because access filtering can be enforced across different callers without duplicating all policy logic in each application.

However, RLS interacts with privileged roles, table ownership, views, `SECURITY DEFINER` functions, and policy composition. It must not be assumed to apply uniformly regardless of execution context.

Primary sources

- PostgreSQL client authentication: `https://www.postgresql.org/docs/18/client-authentication.html`
- Row-level security policies: `https://www.postgresql.org/docs/18/ddl-rowsecurity.html`
- Privilege system: `https://www.postgresql.org/docs/18/ddl-priv.html`
- SQL function security: `https://www.postgresql.org/docs/18/sql-createfunction.html`
- pgcrypto: `https://www.postgresql.org/docs/18/pgcrypto.html`
- libpq connection parameters: `https://www.postgresql.org/docs/18/libpq-connect.html`

### 10.2 pgAudit and privilege-control extensions

| Tool            | Functionality                                                                            |
| --------------- | ---------------------------------------------------------------------------------------- |
| pgAudit         | Detailed statement/session/object auditing through PostgreSQL's logging system           |
| pgaudit_analyze | Analysis of pgAudit output                                                               |
| set_user        | Controlled changes of session authorization/privileges with additional auditing controls |
| sepgsql         | PostgreSQL integration with SELinux mandatory-access-control policies                    |

pgAudit supports separate branches associated with PostgreSQL major releases, including PostgreSQL 18.

Its critical limitation is that the audit trail is best effort rather than transactionally durable. Audit messages are written through PostgreSQL logging, and a committed transaction is not guaranteed to have a corresponding log entry durably persisted. This matters for audit-trail guarantees and compliance-oriented system design.

Primary sources

- pgAudit capabilities, configuration, and limitations: `https://github.com/pgaudit/pgaudit`
- pgAudit companion analyzer: `https://github.com/pgaudit/pgaudit_analyze`
- set_user privilege-control extension: `https://github.com/pgaudit/set_user`
- PostgreSQL sepgsql documentation: `https://www.postgresql.org/docs/18/sepgsql.html`

### 10.3 PostgreSQL Anonymizer

PostgreSQL Anonymizer supplies more than simple random-data replacement functions.

Its documented strategies include:

- Dynamic masking at query/read time.
- Static irreversible or persistent data transformation.
- Pseudonymization.
- Masked backup generation.
- Anonymized replica creation.
- Masking views.
- Masking-related wrapper functionality.

These approaches solve different problems: dynamic masking limits visibility, static anonymization modifies stored data, and masked replicas or exports create derivative database states with altered disclosure characteristics.

#### Important 2026 security changes

The PostgreSQL Anonymizer 3.2 series introduced new pseudonymization functions and addressed critical privilege-escalation vulnerabilities identified as CVE-2026-19633, CVE-2026-19634, and CVE-2026-83534.

It also changed behavior to restrict certain masking operations involving superusers. By September 25, 2026, version 3.2.3 had been tagged upstream. Compatibility and security should be assessed against the specific patched release, not just the existence of version 3.2.

Primary sources

- PostgreSQL Anonymizer official repository: `https://gitlab.com/dalibo/postgresql_anonymizer`
- Versioned release notes and security changes: `https://gitlab.com/dalibo/postgresql_anonymizer/-/blob/latest/NEWS.md`
- Published release tags: `https://gitlab.com/dalibo/postgresql_anonymizer/-/tags`

### 10.4 Ubuntu operating-system security boundaries

PostgreSQL's own privilege model sits inside the broader Linux security environment.

Relevant controls include systemd service configuration, Unix users/groups, filesystem permissions, Unix socket permissions, AppArmor or SELinux policy, and credentials exposed to service processes.

On Ubuntu, AppArmor is commonly the default mandatory-access-control framework. PostgreSQL's `sepgsql` specifically integrates SELinux and is not simply an AppArmor configuration mechanism.

C/Rust PostgreSQL extensions execute within the database server process and therefore have a different security profile from external client programs.

Primary sources

- PostgreSQL file locations and runtime configuration: `https://www.postgresql.org/docs/18/runtime-config.html`
- SELinux integration: `https://www.postgresql.org/docs/18/sepgsql.html`
- Ubuntu AppArmor documentation: `https://ubuntu.com/server/docs/security-apparmor`

## 11. SQL development, interactive clients, testing, and benchmarking

### 11.1 Interactive command-line and graphical clients

| Tool        | Distinctive capabilities                                                                           |
| ----------- | -------------------------------------------------------------------------------------------------- |
| psql        | Native SQL shell, scripting, introspection, meta-commands                                          |
| pgcli       | Enhanced interactive SQL client with completion and syntax highlighting                            |
| pspg        | Table-aware terminal pager supporting structured navigation and search                             |
| pgAdmin 4   | Graphical database administration, query editing, schema browsing, visual plans, object management |
| DBeaver     | Multi-database SQL editing, data browsing, import/export, and object exploration                   |
| pgModeler   | PostgreSQL-specific data modeling, reverse engineering, SQL generation, and schema synchronization |
| usql        | Multi-database SQL terminal                                                                        |
| pgFormatter | SQL formatting                                                                                     |
| SQLFluff    | SQL linting, formatting, configurable rule enforcement                                             |

`psql` and `pgcli` overlap in interactive SQL execution, but `psql` remains the foundational PostgreSQL scripting environment.

`pspg` is a different kind of tool entirely: it is a pager that can improve presentation and navigation of query results without replacing the SQL client.

Primary sources

- psql command and scripting reference: `https://www.postgresql.org/docs/18/app-psql.html`
- pgcli: `https://github.com/dbcli/pgcli`
- pspg: `https://github.com/okbob/pspg`
- pgAdmin 4: `https://www.pgadmin.org/docs/`
- DBeaver: `https://dbeaver.io/`
- pgModeler documentation: `https://www.pgmodeler.io/support/docs`
- usql: `https://github.com/xo/usql`
- pgFormatter: `https://github.com/darold/pgformatter`
- SQLFluff: `https://docs.sqlfluff.com/`

### 11.2 SQL parsing, static validation, and typed interface generation

| Tool           | Principal function                                                    |
| -------------- | --------------------------------------------------------------------- |
| libpg_query    | Independent access to PostgreSQL parser functionality                 |
| pglast         | Python interfaces for PostgreSQL parse trees                          |
| SQLFluff       | Dialect-aware SQL rules and formatting                                |
| pgFormatter    | SQL formatting and normalization                                      |
| sqlc           | Analyze schema and SQL queries, generate typed application interfaces |
| pg-schema-diff | Schema-aware DDL comparison and migration planning                    |

#### libpg_query and pglast

`libpg_query` exposes PostgreSQL parser structures outside a running server. This enables accurate inspection of SQL syntax using PostgreSQL's grammar rather than hand-written tokenization or regexes.

`pglast` provides Python access to related parse-tree functionality.

Parser versions remain consequential because PostgreSQL's grammar changes across major versions.

#### sqlc

`sqlc` analyzes SQL against database schemas and generates typed application code, notably for Go and through supported code-generation plugins.

Its capabilities include SQL parsing, compilation/validation, formatting, query analysis, code generation, and schema/query verification.

An important advanced mechanism is database-backed analysis: sqlc can use a PostgreSQL database to resolve types and metadata that its built-in static analyzer cannot fully infer.

This potentially eliminates separately maintained query result models and significant client-side mapping code. However, database-backed analysis requires a compatible, correctly migrated schema.

Primary sources

- libpg_query: `https://github.com/pganalyze/libpg_query`
- pglast: `https://github.com/lelit/pglast`
- sqlc documentation: `https://docs.sqlc.dev/en/latest/`
- sqlc code generation and database-backed analysis: `https://docs.sqlc.dev/en/latest/howto/generate.html`
- sqlc CLI reference: `https://docs.sqlc.dev/en/latest/reference/cli.html`
- sqlc configuration and supported generators: `https://docs.sqlc.dev/en/latest/reference/config.html`

### 11.3 PostgreSQL regression, unit, and concurrency testing

| Tool                 | Testing capabilities                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------- |
| pgTAP                | SQL-level assertions for database functions, constraints, schemas, privileges, objects, and behavior |
| pg_prove             | TAP-compatible command-line test runner for pgTAP                                                    |
| pg_regress           | SQL regression tests against expected results                                                        |
| pg_isolation_regress | Deterministic testing of transactional interleavings and isolation behavior                          |
| pg_virtualenv        | Isolated disposable PostgreSQL environments                                                          |
| DBLab Engine         | Full-size thin clones for realistic database testing                                                 |
| cargo pgrx test      | PostgreSQL extension testing from Rust                                                               |

The distinction between ordinary tests and isolation tests is especially important.

A conventional SQL test often verifies a result under one transaction sequence. A concurrency/isolation test controls interleavings of operations to check behavior such as deadlocks, serialization conflicts, lock order, and concurrent modifications.

`pg_isolation_regress` is part of PostgreSQL's own testing infrastructure and provides a mechanism designed for precisely these situations.

pgTAP supplies a complementary assertion system for defining database-level behavioral tests. Its `pg_prove` runner executes and aggregates TAP test outcomes.

Primary sources

- pgTAP project: `https://github.com/theory/pgtap`
- pgTAP documentation: `https://pgtap.org/`
- pg_prove test harness: `https://pgtap.org/pg_prove.html`
- PostgreSQL regression test infrastructure: `https://www.postgresql.org/docs/18/regress-run.html`
- PostgreSQL isolation testing: `https://www.postgresql.org/docs/18/regress-tests.html`
- Temporary test clusters: `https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`
- pgrx Rust testing framework: `https://github.com/pgcentralfoundation/pgrx`

### 11.4 PL/pgSQL linting and profiling

Two specialized tools are especially useful when meaningful logic is executed in stored functions or procedures.

plpgsql_check provides static checking, linting, profiling-related features, and dependency-oriented inspection of PL/pgSQL code. It helps reveal errors and questionable constructs that may otherwise remain undiscovered until a specific function branch executes.

plprofiler provides PL/pgSQL profiling and reports, supporting investigations of procedural database logic whose internal work is not visible from a single top-level application SQL timing measurement.

Primary sources

- plpgsql_check: `https://github.com/okbob/plpgsql_check`
- plprofiler: `https://github.com/bigsql/plprofiler`
- Native PL/pgSQL language behavior: `https://www.postgresql.org/docs/18/plpgsql.html`

### 11.5 Workload benchmarking

| Tool           | Benchmarking capability                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| pgbench        | Native PostgreSQL benchmark client with configurable transactions, concurrency and execution rates |
| BenchBase      | Multi-database benchmark framework with representative transactional workloads                     |
| HammerDB       | Database benchmarking and comparative workload generation                                          |
| pg_test_fsync  | Filesystem synchronization performance                                                             |
| pg_test_timing | Timing overhead characterization                                                                   |
| fio            | Synthetic storage benchmarking                                                                     |
| perf           | CPU profiling of actual server execution                                                           |

`pgbench` supports custom SQL transaction scripts, variable generation, multiple clients/threads, rate limiting, and latency reporting.

BenchBase and HammerDB support broader standardized or representative workloads.

The principal distinction is between synthetic benchmark evidence and observational performance evidence from real workload execution. A synthetic benchmark can test selected contention or query patterns, but it cannot establish that a different application will achieve the same throughput or latency.

Primary sources

- PostgreSQL pgbench: `https://www.postgresql.org/docs/18/pgbench.html`
- BenchBase: `https://github.com/cmu-db/benchbase`
- HammerDB documentation: `https://www.hammerdb.com/docs/`
- PostgreSQL fsync benchmarking: `https://www.postgresql.org/docs/18/pgtestfsync.html`
- PostgreSQL timer benchmarking: `https://www.postgresql.org/docs/18/pgtesttiming.html`

## 12. Specialized execution, indexing, analytical, and integration extensions

Not every PostgreSQL extension is a system administration utility. Nevertheless, many extensions materially change what the PostgreSQL engine can do and therefore affect the overall system tooling landscape.

These extensions can replace entire categories of standalone services or bespoke processing logic, although doing so also moves execution and resource consumption into PostgreSQL.

### 12.1 Full-text search, approximate retrieval, and specialized indexing

| Extension               | Capabilities                                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| pgvector                | Vector data types, distance operators, exact nearest-neighbor search, HNSW and IVFFlat indexing |
| pg_search / ParadeDB    | PostgreSQL-native BM25 full-text search, filtering, ranking, and advanced search functionality  |
| `pg_trgm`               | Trigram similarity and index-assisted approximate string matching                               |
| `fuzzystrmatch`         | Text similarity and phonetic matching functions                                                 |
| `unaccent`              | Accent normalization for text processing                                                        |
| `btree_gin`             | Additional GIN operator classes                                                                 |
| `btree_gist`            | Additional GiST operator classes and exclusion-constraint support                               |
| `bloom`                 | Bloom filter index access method                                                                |
| RUM                     | Specialized inverted indexing with additional ranking/search capabilities                       |
| `hstore`                | Key/value data storage                                                                          |
| `ltree`                 | Hierarchical labels and tree-like relationships                                                 |
| `citext`                | Case-insensitive character-string semantics                                                     |
| `cube`, `earthdistance` | Multidimensional and geographic-distance calculations                                           |
| `tablefunc`             | Pivoting and other table-valued operations                                                      |

#### pgvector

pgvector supports exact and approximate vector similarity search within PostgreSQL.

Its principal index strategies are:

- HNSW: graph-based approximate nearest-neighbor search, generally favoring search speed/recall at greater build-time and memory expense.
- IVFFlat: clustering/list-based approximate search, with different construction and recall characteristics.

Other capabilities include half-precision vectors, sparse vectors, binary quantization, configurable iterative scanning, and multiple distance operators.

The distinction between exact and approximate retrieval is consequential: adding an approximate index can change the returned nearest neighbors. Index quality must be assessed against exact results and the workload's recall requirements.

Version-specific note: pgvector's 0.8.7 release, dated October 1, 2026, includes an IVFFlat index-build buffer-overflow fix. Its 0.8.x release notes also describe important HNSW and PostgreSQL 18 corrections.

Primary sources

- pgvector feature and index documentation: `https://github.com/pgvector/pgvector`
- pgvector release notes and fixes: `https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md`
- pgvector Python integration: `https://github.com/pgvector/pgvector-python`

#### ParadeDB / pg_search

ParadeDB extends PostgreSQL with search indexes and operators supporting BM25-ranked text retrieval, filtering, highlighting, facets, and related functionality.

This offers an alternative to running a separate full-text search service when supported retrieval requirements can be satisfied within PostgreSQL.

Search functionality, PostgreSQL-compatible query execution, distributed search services, and vector retrieval do not automatically have identical ranking or consistency characteristics.

Primary sources

- ParadeDB source and capability documentation: `https://github.com/paradedb/paradedb`
- pg_search extension-specific source: `https://github.com/paradedb/paradedb/blob/main/pg_search/README.md`
- ParadeDB documentation: `https://docs.paradedb.com/`

#### Native and contributed indexing

PostgreSQL's built-in access methods—B-tree, hash, GiST, SP-GiST, GIN, and BRIN—already provide significant indexing flexibility.

Before introducing a separate extension, the native options include expression indexes, partial indexes, covering indexes with `INCLUDE`, multicolumn indexes, and specialized operator classes.

Primary sources

- PostgreSQL index types: `https://www.postgresql.org/docs/18/indexes-types.html`
- Partial indexes: `https://www.postgresql.org/docs/18/indexes-partial.html`
- Expression indexes: `https://www.postgresql.org/docs/18/indexes-expressional.html`
- Covering indexes: `https://www.postgresql.org/docs/18/indexes-index-only-scans.html`
- PostgreSQL full-text search: `https://www.postgresql.org/docs/18/textsearch.html`
- Trigram matching: `https://www.postgresql.org/docs/18/pgtrgm.html`
- RUM indexes: `https://github.com/postgrespro/rum`

### 12.2 Spatial and geospatial tooling

| Component                | Capabilities                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| PostGIS                  | Spatial and geographic types, geometry functions, spatial indexes, transformations and analytics |
| pgRouting                | Graph and routing algorithms using PostgreSQL/PostGIS                                            |
| `shp2pgsql`, `pgsql2shp` | Shapefile import/export                                                                          |
| `raster2pgsql`           | Raster import                                                                                    |
| GDAL / ogr2ogr           | Geospatial data transformation and format interoperability                                       |
| osm2pgsql                | OpenStreetMap ingestion and updates                                                              |
| pg_tileserv              | HTTP vector-tile services backed by PostgreSQL/PostGIS                                           |
| pg_featureserv           | HTTP feature services over PostGIS data                                                          |

PostGIS is a major example of an extension ecosystem rather than a single library.

It has optional components for raster, topology, and other specialized spatial functionality. Its system utilities handle data ingestion and conversion, while SQL types, functions, and indexes participate directly in database queries.

The Ubuntu installation documentation explicitly includes PostgreSQL 18 packages such as `postgresql-18-postgis-3`, the standalone `postgis` utilities package, and the related `postgresql-18-pgrouting` package pattern.

Primary sources

- PostGIS documentation: `https://postgis.net/documentation/`
- PostGIS Ubuntu/PGDG installation and package names: `https://postgis.net/documentation/getting_started/install_ubuntu/`
- pgRouting: `https://pgrouting.org/documentation.html`
- GDAL ogr2ogr: `https://gdal.org/en/stable/programs/ogr2ogr.html`
- osm2pgsql: `https://osm2pgsql.org/doc/manual.html`
- pg_tileserv: `https://github.com/CrunchyData/pg_tileserv`
- pg_featureserv: `https://github.com/CrunchyData/pg_featureserv`

### 12.3 Time-series, incremental computation, and analytical extensions

| Component           | Main capabilities                                                                                                    |
| ------------------- | -------------------------------------------------------------------------------------------------------------------- |
| TimescaleDB         | Hypertables, chunk-based time-series management, continuous aggregates, retention, compression/columnar capabilities |
| TimescaleDB Toolkit | Time-series/statistical hyperfunctions, specialized aggregate states and analytical operations                       |
| timescaledb-tune    | PostgreSQL/TimescaleDB tuning suggestions based on host resources                                                    |
| pg_ivm              | Immediate incremental materialized-view maintenance                                                                  |
| pg_duckdb           | DuckDB analytical execution within PostgreSQL                                                                        |
| Citus               | Distributed PostgreSQL tables, sharding, distributed SQL execution and columnar features                             |

#### TimescaleDB

TimescaleDB builds time-series functionality around hypertables and chunks. Its capabilities include automatic partition-like time-series organization, policies for lifecycle and retention, and continuous aggregate maintenance.

Continuous aggregates can avoid repeatedly recomputing an entire analytical summary, but are constrained by supported query definitions, refresh policies, and the relationship between recent and materialized data.

TimescaleDB Toolkit is a separate extension supplying specialized aggregate functions and statistical operations. Its released and experimental function namespaces should be distinguished.

Primary sources

- TimescaleDB source and feature architecture: `https://github.com/timescale/timescaledb`
- TimescaleDB documentation: `https://docs.timescale.com/`
- Continuous aggregates: `https://docs.timescale.com/use-timescale/latest/continuous-aggregates/`
- TimescaleDB Toolkit: `https://github.com/timescale/timescaledb-toolkit`
- TimescaleDB tuning utility: `https://docs.timescale.com/self-hosted/latest/tooling/about-timescaledb-tune/`

#### pg_ivm: immediate incremental materialized views

`pg_ivm` updates supported incremental materialized views within the same transaction that changes their underlying tables.

It uses trigger-based maintenance, making it a different architecture from asynchronously refreshed materialized views or scheduled continuous aggregates.

The advantage is that derived relations can remain transactionally current for supported definitions. The tradeoff is additional work and possible contention on every relevant write.

Primary source

\- pg_ivm architecture, supported queries, limitations and releases: `https://github.com/sraoss/pg_ivm`

#### pg_duckdb: analytical execution inside PostgreSQL

`pg_duckdb` integrates DuckDB's analytical execution capabilities with PostgreSQL.

Its documented capabilities include analytical SQL execution, columnar/vectorized processing, and access to formats such as Parquet, CSV, JSON, Iceberg, and Delta Lake under supported arrangements.

It has separate compatibility considerations from DuckDB's external PostgreSQL connector; upstream documentation lists PostgreSQL 14–18 and specific operating-system requirements for its distributed builds.

Primary sources

- pg_duckdb source, installation, engine integration and requirements: `https://github.com/duckdb/pg_duckdb`
- pg_duckdb releases: `https://github.com/duckdb/pg_duckdb/releases`

#### Citus: distributed PostgreSQL execution

Citus introduces distributed tables, shard placement, distributed query planning/execution, reference tables, and data rebalancing across multiple PostgreSQL nodes.

It therefore addresses a different problem from an ordinary query accelerator or single-node time-series extension.

Citus 14 added PostgreSQL 18 support and has documented Ubuntu packaging through its community repository.

Primary sources

- Citus architecture and deployment: `https://github.com/citusdata/citus`
- Citus version history: `https://github.com/citusdata/citus/blob/main/CHANGELOG.md`
- Citus 14 documentation and release information: `https://www.citusdata.com/updates/v14-0/`

### 12.4 Graph processing, queues, and database-native APIs

| Component                | Functionality                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------- |
| Apache AGE               | Property-graph data and Cypher-oriented graph querying within PostgreSQL              |
| pgmq                     | PostgreSQL-backed queues with visibility timeouts, consumption, retries and archiving |
| PostgREST                | HTTP APIs derived from PostgreSQL relations, functions, roles and policies            |
| pg_graphql               | GraphQL schema reflection and query resolution inside PostgreSQL                      |
| pg_net                   | Asynchronous HTTP-request functionality initiated from PostgreSQL                     |
| pgsql-http               | HTTP client functions exposed through SQL                                             |
| Native `LISTEN`/`NOTIFY` | Transactional event notification for connected PostgreSQL clients                     |

#### Apache AGE

Apache AGE adds graph-related query and storage capabilities through PostgreSQL extension mechanisms.

This is distinct from representing a graph manually through ordinary edge and vertex tables: AGE supplies graph query semantics and a Cypher-oriented interface.

Compatibility with newer PostgreSQL majors and release-specific graph functionality should be checked independently.

Primary sources

- Apache AGE project: `https://github.com/apache/age`
- Apache AGE documentation: `https://age.apache.org/age-manual/master/index.html`

#### pgmq

`pgmq` implements a database-backed message queue with message visibility, acknowledgment/deletion, and archival.

Its visibility timeout allows a message to become eligible for another consumer if it has not been successfully handled within the configured period.

This supports retries and at-least-once processing patterns, but does not automatically make arbitrary external side effects exactly once.

Primary source

\- pgmq queue semantics and implementation: `https://github.com/pgmq/pgmq`

#### PostgREST and pg_graphql

PostgREST exposes relational data and procedures through HTTP, using PostgreSQL schemas, functions, roles, and permissions as the primary API model.

`pg_graphql` reflects PostgreSQL schema objects into GraphQL, supporting graph traversal, relationships, queries and mutations under PostgreSQL access controls.

The distinction is that PostgREST is an external API service, while pg_graphql is a PostgreSQL extension providing GraphQL query resolution. They can also be combined.

Primary sources

- PostgREST documentation: `https://docs.postgrest.org/`
- pg_graphql source: `https://github.com/supabase/pg_graphql`
- pg_graphql documentation: `https://supabase.github.io/pg_graphql`
- pg_graphql security and RLS semantics: `https://github.com/supabase/pg_graphql/blob/master/docs/security.md`
- pg_net: `https://github.com/supabase/pg_net`
- PostgreSQL HTTP extension: `https://github.com/pramsey/pgsql-http`
- Native LISTEN/NOTIFY semantics: `https://www.postgresql.org/docs/18/sql-notify.html`

### 12.5 Extension development and server programmability

PostgreSQL supports substantial extension of engine behavior, including new functions, operators, types, access methods, background workers, procedural languages, foreign-data wrappers, and custom scan infrastructure.

| Tool/mechanism             | Functionality                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------- |
| PGXS                       | Build infrastructure for external PostgreSQL extensions                             |
| pgrx / cargo-pgrx          | Rust framework for writing, generating, packaging and testing PostgreSQL extensions |
| `postgresql-server-dev-18` | Server headers and development interfaces                                           |
| `pg_config`                | Build and installation configuration                                                |
| `pg_regress`               | Extension regression testing                                                        |
| `pg_isolation_regress`     | Concurrency testing for extensions                                                  |
| PGXN Client                | Community extension discovery and installation                                      |
| PL/Python, PL/Perl, PL/Tcl | Procedural-language execution inside PostgreSQL                                     |

#### pgrx

`pgrx` provides Rust interfaces and associated macros for writing PostgreSQL extensions.

Its companion `cargo pgrx` tooling handles creating extension projects, initializing or registering PostgreSQL installations, running test servers, generating SQL definitions, executing tests, and packaging extension artifacts.

The upstream project documents PostgreSQL 13–18 support and development support for PostgreSQL 19 beta versions. PostgreSQL 19 support should not be treated as stable until the relevant release supports its finalized engine version.

Recent tooling includes independently scoped temporary test clusters, which helps prevent parallel extension test invocations from contending for the same server port or data directory.

Primary sources

- PostgreSQL extension architecture: `https://www.postgresql.org/docs/18/extend.html`
- PostgreSQL extension packaging: `https://www.postgresql.org/docs/18/extend-extensions.html`
- PGXS build infrastructure: `https://www.postgresql.org/docs/18/extend-pgxs.html`
- PostgreSQL C function interfaces: `https://www.postgresql.org/docs/18/xfunc-c.html`
- Background workers: `https://www.postgresql.org/docs/18/bgworker.html`
- pgrx Rust framework: `https://github.com/pgcentralfoundation/pgrx`
- cargo-pgrx tooling reference: `https://github.com/pgcentralfoundation/pgrx/blob/develop/cargo-pgrx/README.md`
- pgrx release and version compatibility: `https://github.com/pgcentralfoundation/pgrx/releases`
- PGXN Client: `https://github.com/pgxn/pgxnclient`

## 13. Ubuntu and PGDG package catalog

The package inventory below is an installation-oriented index, not a recommendation to install everything.

Package names are distinguished from upstream projects because an extension may be available through multiple repositories, under a version-dependent name, or only through source installation.

### 13.1 Foundational PostgreSQL packages

| Package                    | Functionality                                                 |
| -------------------------- | ------------------------------------------------------------- |
| `postgresql-18`            | PostgreSQL server                                             |
| `postgresql-client-18`     | PostgreSQL client utilities                                   |
| `postgresql-common`        | Multi-version/multi-cluster management                        |
| `postgresql-client-common` | Client wrappers and shared infrastructure                     |
| `postgresql-doc-18`        | Locally installed documentation                               |
| `postgresql-server-dev-18` | Server development headers                                    |
| `postgresql-contrib`       | Contributed PostgreSQL modules under distribution conventions |
| `libpq5`, `libpq-dev`      | Native client runtime/development library                     |
| `libecpg-dev`              | Embedded SQL in C                                             |

### 13.2 Operational and administrative packages

| APT name or package family                    | Tooling                              |
| --------------------------------------------- | ------------------------------------ |
| `pgbouncer`                                   | Connection pooling                   |
| `pgagroal`                                    | Connection pooling                   |
| `pgpool2`                                     | PostgreSQL-aware middleware          |
| `pgbackrest`                                  | Physical backup                      |
| `barman`, `barman-cli`, `barman-cli-cloud`    | Backup, archive, and cloud utilities |
| `pgagent`                                     | Database job scheduling              |
| `pgloader`                                    | Heterogeneous database migration     |
| `pgcli`                                       | Interactive SQL client               |
| `pspg`                                        | Terminal query-result pager          |
| `pgbadger`                                    | PostgreSQL log analysis              |
| `pgtap` / PostgreSQL-versioned pgTAP packages | SQL testing                          |
| `postgresql-18-cron`                          | pg_cron scheduler                    |
| `postgresql-18-pglogical`                     | Logical replication                  |
| `postgresql-18-postgis-3`                     | PostGIS                              |
| `postgresql-18-pgrouting`                     | Routing extension                    |

The first group contains packages documented in Ubuntu, PGDG, or upstream distributions. The PostgreSQL-major-version-specific examples are established naming patterns, but availability must still be checked against the configured repository and architecture.

### 13.3 Additional extension packages worth investigating

The following are important package families, with names dependent on the configured repository and PostgreSQL major version:

| Extension family         | Functionality                     |
| ------------------------ | --------------------------------- |
| pg_repack                | Online table/index reorganization |
| pg_partman               | Partition lifecycle               |
| pg_squeeze               | Table bloat cleanup               |
| pgvector                 | Vector indexing                   |
| pgaudit                  | Audit logging                     |
| hypopg                   | Hypothetical indexes              |
| pg_stat_kcache           | Kernel resource accounting        |
| pg_qualstats             | Predicate statistics              |
| pg_wait_sampling         | Wait profiling                    |
| plpgsql_check            | Procedural-language diagnostics   |
| wal2json                 | Logical decoding                  |
| postgres_fdw, other FDWs | Data federation                   |
| TimescaleDB              | Time-series storage and execution |
| TimescaleDB Toolkit      | Time-series analytics             |
| Citus                    | Distributed PostgreSQL            |
| pg_duckdb                | Analytical execution extension    |
| pg_search                | Search indexing and retrieval     |

For example, upstream instructions document `postgresql-18-citus-14.1` for Citus's vendor-maintained APT repository and `timescaledb-2-postgresql-18` for TimescaleDB's own repository. These examples must not be generalized into a claim that every extension is packaged in PGDG or Ubuntu's standard repositories.

### 13.4 Discovering the actual installable package set

The authoritative package inventory for a particular Ubuntu host is its configured APT metadata.

```
# Identify installed PostgreSQL clusters and versions.
pg_lsclusters

# Search installed-repository metadata for PostgreSQL 18 packages.
apt-cache search '^postgresql-18-'

# Search for standalone operational utilities.
apt-cache search \
  'pgbouncer|pgpool2|pgagroal|pgbackrest|barman|pgagent|pgbadger'

# Show installed versions and package candidates.
apt-cache policy postgresql-18 pgbouncer pgbackrest

# Show files owned by Debian/Ubuntu cluster tooling.
dpkg -L postgresql-common

# Inspect version-specific build and extension directories.
/usr/lib/postgresql/18/bin/pg_config --bindir
/usr/lib/postgresql/18/bin/pg_config --pkglibdir
/usr/lib/postgresql/18/bin/pg_config --sharedir

# List extensions available to the connected database.
psql -d postgres -c "
SELECT name, default_version, installed_version
FROM pg_available_extensions
ORDER BY name;"

# List extensions enabled in the connected database.
psql -d postgres -c "
SELECT extname, extversion
FROM pg_extension
ORDER BY extname;"
```

These are illustrative read-only discovery commands, not commands executed on a particular system.

The package catalog and SQL extension catalogs answer different questions: APT reports software available to install on Ubuntu; `pg_available_extensions` reports extension control files and versions recognized by a PostgreSQL server; `pg_extension` reports what is enabled in a particular database.

Primary sources

- PostgreSQL PGDG repository and installation: `https://www.postgresql.org/download/linux/ubuntu/`
- PGDG repository package catalog: `https://wiki.postgresql.org/wiki/Apt/Packages`
- Ubuntu package index: `https://packages.ubuntu.com/`
- Debian PostgreSQL cluster management: `https://manpages.debian.org/unstable/postgresql-common/index.html`

## 14. Architectural combinations and capability interactions

The value of PostgreSQL tooling is often greatest when multiple native and external mechanisms are composed.

| Target capability           | Complementary tooling                                                    | Combined functionality                                                    |
| --------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| Physical state recovery     | pgBackRest/Barman/WAL-G + WAL archives + restore verification            | Recoverable historical database states                                    |
| Major-version lifecycle     | `pg_upgradecluster` + `pg_upgrade` + extension checks + `vacuumdb`       | Coordinated PostgreSQL major upgrades                                     |
| Schema evolution            | Sqitch/Atlas/pg-schema-diff/pgroll + native online DDL                   | Structured changes, hazard analysis and compatibility                     |
| Reproducible state testing  | pg_virtualenv/DBLab + pgTAP + migration verification                     | Repeatable database behavior checks                                       |
| Workload diagnostics        | pg_stat_statements + auto_explain + pgBadger + HypoPG + perf             | Query frequency, execution behavior, indexing hypotheses and CPU hotspots |
| Physical bloat management   | pgstattuple + autovacuum + pg_repack/pg_squeeze                          | Measure and correct storage inefficiency                                  |
| Automatic retention         | Native partitioning + pg_partman + pg_cron                               | Database-managed partition creation and retention                         |
| High availability           | Physical streaming + Patroni/repmgr/pg_auto_failover + PgBouncer/HAProxy | Replication, election, routing and connection management                  |
| Event-based integration     | Logical slots + pgoutput/wal2json + Debezium                             | Snapshot-plus-change capture into downstream processing                   |
| Database-centered analytics | TimescaleDB / pg_ivm / pg_duckdb / Citus                                 | Different incremental, analytical and distributed SQL mechanisms          |
| Typed SQL development       | PostgreSQL schema + libpg_query/pglast + sqlc                            | Parser-grounded SQL validation and generated application contracts        |
| Geospatial SQL services     | PostGIS + GDAL + pgRouting + pg_featureserv                              | Spatial processing, ingestion, routing and HTTP services                  |

These combinations describe general capabilities, not an adoption plan for any particular environment.

### 14.1 Distinct meanings of incremental processing

Three mechanisms can all be described as incremental, but operate at entirely different layers.

| Mechanism                                 | Incremental unit                       | Consistency/lifecycle model                              |
| ----------------------------------------- | -------------------------------------- | -------------------------------------------------------- |
| Incremental physical backup               | Changed physical database blocks/files | Backup-chain and WAL-based recovery                      |
| Incremental materialized-view maintenance | Changes to derived query results       | Immediate transactional or deferred/policy-based updates |
| CDC/logical replication                   | Committed row/change events            | Replication slot, LSN, consumer and delivery semantics   |

The fact that these are incremental does not establish compatible correctness guarantees.

### 14.2 Distinct meanings of verification

| Verification mechanism    | What is checked                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `pg_verifybackup`         | Backup manifests, files, and supported WAL requirements                              |
| `pg_amcheck`              | Supported physical/index/table integrity invariants                                  |
| pgTAP                     | User-defined SQL behavior and structural assertions                                  |
| Sqitch verification       | Deployment-plan state and user-supplied verification scripts                         |
| Schema diff tools         | Differences between database object definitions                                      |
| pgcopydb comparison       | Selected schema metadata or row-count/checksum comparisons                           |
| Actual recovery rehearsal | Whether backups and their required dependencies can reconstruct a functioning server |

These checks are complementary. Passing one does not imply passing all the others.

### 14.3 Where execution takes place

| Execution boundary           | Examples                                             | Benefits                                                          | Costs and limits                                           |
| ---------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| PostgreSQL SQL/backend       | pgvector, pg_ivm, PL/pgSQL, PostGIS, pgrx extensions | Transactional integration, SQL composition, reduced data movement | Shares PostgreSQL resources; version and security coupling |
| PostgreSQL background worker | pg_cron, extension maintenance workers               | Native server-lifecycle integration                               | Resource and availability coupling to PostgreSQL           |
| External CLI process         | pg_repack, pgBackRest, migration tools               | Separation from server execution and independent automation       | Process/connection orchestration                           |
| External service             | Debezium, Patroni, Prometheus                        | Independent coordination, monitoring or event processing          | Additional availability and deployment requirements        |
| Independent query engine     | DuckDB with PostgreSQL connector                     | Specialized execution and independent resource allocation         | Data movement and execution-boundary semantics             |

This execution-boundary distinction often matters more than whether a tool is written in Rust, Python, Go, Perl, or C.

## 15. Important limitations and version-sensitive considerations

The ecosystem's breadth should not obscure several recurring constraints.

PostgreSQL major-version compatibility. Server extensions are often compiled against PostgreSQL-specific APIs and ABI expectations. A package supporting PostgreSQL 17 does not automatically work with PostgreSQL 18 or 19.

APT package provenance. Ubuntu, PGDG, and vendor-maintained repositories can supply packages under overlapping names and different version policies. The candidate selected by APT depends on configured package sources and priorities.

Extension activation. Installing the Ubuntu package, loading a shared library, and creating the extension in a database are separate operations. Upgrading the package may not update installed database extension versions automatically.

Observability overhead. Extensive plan logging, wait sampling, profiling, and per-node instrumentation can affect performance and generate significant metrics/log volumes.

Transaction and session semantics. Connection pooling, logical replication, FDWs, and asynchronous database integrations can change which session state or transactional guarantees apply.

Schema migration hazards. Declarative schema tools can reduce planning work, but locks, rewrites, backfills, nontransactional DDL, and application compatibility remain consequential.

Physical versus logical data semantics. Physical backups, logical exports, filesystem clones, and logical replication cannot be freely substituted for one another.

Security-sensitive extensions. Third-party binaries executing inside PostgreSQL warrant scrutiny, especially those providing HTTP access, privileged operations, masking, or shared-memory/background-worker functionality.

Project maintenance status. Deprecated, archived, and less frequently maintained projects should be distinguished from actively developed alternatives. For example, the older `migra` schema-diff project is deprecated, while historical `pgwatch2` documentation should not be assumed to describe current pgwatch.

Primary sources

- PostgreSQL extension infrastructure: `https://www.postgresql.org/docs/18/extend.html`
- PostgreSQL version policy: `https://www.postgresql.org/support/versioning/`
- PostgreSQL statistics/monitoring semantics: `https://www.postgresql.org/docs/18/monitoring-stats.html`
- PostgreSQL transaction isolation: `https://www.postgresql.org/docs/18/transaction-iso.html`
- Deprecated migra project: `https://github.com/djrobstep/migra`
- Current pgwatch: `https://github.com/cybertec-postgresql/pgwatch`

## 16. Overall perspective

PostgreSQL's Ubuntu tooling ecosystem encompasses substantially more than administration of a relational database server. It provides mature and often highly composable mechanisms for:

- Physical and logical state preservation.
- Database history, recovery, cloning, and branching.
- Declarative and versioned schema evolution.
- Referential, structural, and behavioral validation.
- Query optimization and multi-level performance diagnostics.
- Online storage reorganization and maintenance.
- Physical and logical replication.
- Connection pooling and high availability.
- Data federation, migration, and analytical integration.
- SQL-native search, spatial computing, and specialized execution.
- Database-native scheduling, messaging, and API generation.
- Extension development and deterministic database testing.

The most useful unifying question is where each capability belongs and what guarantees it provides: inside the PostgreSQL engine, in a loadable extension, in a standalone system utility, in a separate service, or in an external execution engine.

That framework helps identify opportunities to replace bespoke infrastructure with mature tooling while preserving the distinctions that matter for correctness, performance, maintainability, security, and operational control.

The detailed URLs throughout this reference are intended to let programming agents investigate those mechanisms independently—directly at the relevant primary documentation, source repository, or version-specific manual—without relying on ChatGPT hyperlinks or citation metadata.