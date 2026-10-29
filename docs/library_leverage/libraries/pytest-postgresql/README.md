# pytest-postgresql

**Realization assessed:** pytest-postgresql 9.1.1. The library is **not adopted and not installed**.
It received a light pass because CBO-010 names it directly.

**Researched:** 2026-10-29 by the R2 cluster.
- Overview sections read: [overview](../../../libraries/pytest-postgresql.md) §1–6, §9, §10.3 and §11.
- Source read at tag `v9.1.1`: `janitor.py`, `noprocess.py`, `client.py` and `executors/noop.py`.

## Reusable opportunity types

<a id="pytest-postgresql-template-fixture-lifecycle"></a>

### `pytest-postgresql/template-fixture-lifecycle`

**Mechanism.**
- `postgresql_noproc` creates a session-scoped template named
  `<dbname>[<xdist-worker>]_tmpl`, marked `IS_TEMPLATE`.
- It runs `load` callables, which receive `host, port, user, dbname, password, autocommit`.
- Function-scoped clients clone the template for each test under a **fixed** name (`tests` plus the
  worker suffix).
- `depends_on` layers templates on top of each other.
- The janitor drops a database by setting `ALLOW_CONNECTIONS false`, calling `pg_terminate_backend`,
  then issuing `DROP`.
- The template is dropped when the session ends.

**Residual obligations and limits.**
- **No reuse across sessions.** There is no template key; staleness is avoided by rebuilding the
  template every session.
- **Names collide.** Clone names are not unique across concurrent sessions.
- **Base template.** A template without `depends_on` clones `template1`, not a custom bare template.
- **Connections.** Clients are psycopg connections opened as the janitor user.
- **Drop permissions.** Terminate-on-drop is subject to PostgreSQL's signalling rules (see
  [postgresql](../postgresql/README.md#postgresql-template-database-clone)).
- **Database ACLs.** Loss of database-level grants on clone is not handled.

## Applicability at source `d739b88`

<a id="applicability-cbo-010"></a>

### CBO-010 — native test databases: **fits only with substantial conditions**

Opportunity: [CBO-010](../../codebase/engineering-workflows.md#cbo-010).

**Q1: restricted roles, a migrated template, and the shared cluster.**

Restricted logins compose with it, since they are separate connections to the clone. The rest does
not fit without work:
- The base template clones `template1` rather than `cs_template`, unless a duck-typed `depends_on`
  base fakes it.
- Clone names are fixed. The current fixture instead uses pid plus a uuid.
- When the operator lacks `pg_signal_backend`, `pg_terminate_backend` in the janitor **errors** on
  lingering restricted-login backends. The current fixture deliberately waits on SQLSTATE 55006
  instead.
- It yields a psycopg connection, not an engine.
- It does not replay the database ACL.

**Q2: a template key.** Not applicable. The library rebuilds the template every session.

**Relative to the native route.** The native route
([PostgreSQL template clone](../postgresql/README.md#applicability-cbo-010)) carries fewer conditions
for this harness. Which route to take is a comparative-review choice.

## Coverage limits

- Source and documentation only. The library was not installed or exercised.
