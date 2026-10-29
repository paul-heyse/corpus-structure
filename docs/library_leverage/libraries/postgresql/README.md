# PostgreSQL (native capabilities)

**Realization assessed:** PostgreSQL 18, using the 18/corpus cluster's server capabilities.

**Researched:** 2026-10-29 by the R2 cluster (PostgreSQL native, migrations, harness).
- The [overview](../../../libraries/PostgreSQL_System_Tooling_for_Ubuntu.md) was read end to end.
- Follow-ups: Context7 (PostgreSQL 18 docs) and upstream `signalfuncs.c` at REL_18_STABLE.
- No database was used ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-postgres-migrations/README.md)).

## Reusable opportunity types

<a id="postgresql-template-database-clone"></a>

### `postgresql/template-database-clone`

**Need.** Fresh, isolated databases at a prepared state, without replaying the preparation.

**Mechanism.**
- `CREATE DATABASE n TEMPLATE t [STRATEGY WAL_LOG|FILE_COPY]`.
- WAL_LOG is the default and suits small templates.
- FILE_COPY checkpoints. In PostgreSQL 18 it can clone files through `file_copy_method = CLONE`.
- With `IS_TEMPLATE`, anyone holding CREATEDB can clone; otherwise only the owner or a superuser can.

**Discharges.** Database-local objects, data, owner and object-level ACLs.

**Not copied** (documented in the PostgreSQL 18 `CREATE DATABASE` notes):
- database-level `GRANT`s;
- `ALTER DATABASE … SET` parameters.

Cluster-wide state such as roles, `pg_hba` and server configuration is shared rather than cloned.

**Conditions.**
- No other session may be connected to the template while it is cloned.
- Cost grows with template size.

**Cleanup permissions** (source inspected). `pg_terminate_backend` and `DROP DATABASE … WITH (FORCE)`
fail with "permission denied to terminate process" unless the caller is one of:
- a superuser;
- a member of the target role;
- a holder of `pg_signal_backend`, or of `pg_signal_autovacuum_worker` for autovacuum workers (new
  in PostgreSQL 18).

<a id="postgresql-recursive-fixpoint"></a>

### `postgresql/recursive-fixpoint`

**`WITH RECURSIVE … UNION`.** This is semi-naive by construction (documented). Each iteration sees
only the working table, and rows that duplicate any earlier result are discarded.

**Limits.**
- Only one recursive self-reference is allowed per query.
- Non-linear rules (R⋈R) and mutually recursive rule branches therefore need a linear rewrite or
  stratification.

**General alternative: an explicit delta-table loop.**
- Each round joins delta⋈total, plus total⋈delta when the rules are non-linear.
- `INSERT … ON CONFLICT DO NOTHING RETURNING *` produces the next delta.
- The loop stops when the delta is empty.
- For positive, monotone rules this reaches the same least fixpoint as naive iteration.

<a id="postgresql-persisted-derived-key"></a>

### `postgresql/persisted-derived-key`

**Generated columns cannot hold such a key** (documented). Generated expressions must use only
immutable functions and the current row; subqueries are not allowed. Virtual generated columns also
forbid user-defined functions.

**Alternative: a stored column written by a protected admission function.**
- It stays valid only while its inputs are immutable.
- Immutability can be enforced with `BEFORE UPDATE OR DELETE` row triggers, a `BEFORE TRUNCATE`
  statement trigger, and privileges.
- The owner can still disable those triggers.

**Transition tables** (`AFTER … REFERENCING NEW TABLE`, statement level, plain tables only). They
give delta-only checks when no staging delta already exists.

<a id="postgresql-privilege-isolation"></a>

### `postgresql/privilege-isolation`

**Mechanism.** Schema `USAGE` and `SELECT` grants per login role, `REVOKE … FROM PUBLIC`, and
`NOINHERIT` roles.

**Residuals.**
- `GRANT … ON ALL TABLES` is point-in-time. Later tables need the grant repeated, or
  `ALTER DEFAULT PRIVILEGES`.
- SECURITY DEFINER functions and views owned by the protected schema's owner bypass the caller's
  privileges.
- Superusers and the migration owner bypass everything.
- Database-level ACLs do not survive template cloning.

## Applicability at source `d739b88` (read through `6b2335a`)

<a id="applicability-cbo-010"></a>

### CBO-010 — native test databases: **native template fits with conditions; the premise needed correcting**

**Opportunity:** [CBO-010](../../codebase/engineering-workflows.md#cbo-010).
**Type:** [template-database-clone](#postgresql-template-database-clone).

**The premise failure.** Revisions `semantic_0003` and `0007` revoke `TEMP ON DATABASE` from
`PUBLIC` and grant it to the publisher and the writer (coordinator-verified). `CREATE DATABASE …
TEMPLATE` does not copy database-level grants. A per-test clone of a migrated head template would
therefore silently give TEMP back to every role, the reader included. Staging relies on
`pg_temp.sp_*`, so TEMP is part of the ADR-0025 security posture.

**Every template route must replay the database ACL after each clone.** Two ways to do that:
- read the template's `pg_database.datacl` (for example with `aclexplode`) and apply the same
  grants to the clone;
- re-run the database-level statements that the revisions derive from `current_database()`.

**Further conditions.**
- The template key must also cover role inventory. A fourth role, `corpus_sem_evaluator`, arrived in
  `4de601c`, while the fixture still checks three.
- Revisions now number 28.
- Keep bootstrap-from-bare for migration tests.
- Run revision pairs with `upgrade(conn, "semantic_00NN")`, load data, then upgrade to the next
  revision.
- No route reclaims residue left by a killed run; a prefix sweep remains code the repository owns.

<a id="applicability-cbo-019"></a>

### CBO-019 — meaning recomputation and whole-realization revalidation: **native fits with conditions; generated columns ruled out**

**Opportunity:** [CBO-019](../../codebase/storage-and-analytics.md#cbo-019).
**Type:** [persisted-derived-key](#postgresql-persisted-derived-key).

**Question 1: is admitted meaning immutable?**
- `value_meaning` reads guarded `typed_value`/`value_role` rows.
- With `qual=true` it also reads `sem.property_applicability` and `sem.class_definition`.
- Restricted roles have only SELECT on `sem`, but **no trigger enforces the immutability of those
  rows**, so the owner can mutate them.
- The whole-realization recheck is currently the only defence against such mutation.

**Persisted key.** It fits only if `sem.*` and admitted value rows become immutable, enforced by
triggers.

**Transition tables are unnecessary.** The staged `pg_temp.sp_*` relations already *are* the delta.

**Question 2: one key for inference, capture and SP-08?** Plausible, separately for unqualified and
qualified meaning. Unsettled.

<a id="applicability-cbo-022"></a>

### CBO-022 — naive inference fixed point: **a delta-table loop fits; `WITH RECURSIVE` fits only per stratifiable linear stratum**

**Opportunity:** [CBO-022](../../codebase/storage-and-analytics.md#cbo-022).
**Type:** [recursive-fixpoint](#postgresql-recursive-fixpoint).

- Proofs come from the *final* work table, and the context representative is fixed before the loop.
  A semi-naive loop that reaches the same least fixpoint therefore yields identical conclusions and
  proofs. This is argued from the code and standard theory, not probed.
- The transitive rule is a non-linear self-join, and rules feed each other. A single CTE for the
  whole profile is therefore ruled out.
- linkml-datalog remains only the deferred trigger.

<a id="applicability-cbo-006"></a>

### CBO-006 (informs) — gold isolation through privileges

**Type:** [privilege-isolation](#postgresql-privilege-isolation).

**Status.** Being implemented concurrently in `4de601c`, with native enforcement still pending: an
`eval` schema, an evaluator login, and REVOKE from the reader and writer.

**Residuals.**
- Publisher-owned SECURITY DEFINER functions and views can read `eval`.
- `GRANT … ON ALL TABLES` must be repeated in later revisions.
- Template clones lose the database ACL.

<a id="applicability-cbo-003"></a>

### CBO-003 and CBO-020 (informs)

**CBO-003.** A native verification record keyed by release id and content digest is sound only under
the same `sem.*` immutability premise as CBO-019. Under today's mutability, a recorded digest proves
nothing beyond its own transaction.

**CBO-020.** Recursive reachability with `WITH RECURSIVE … UNION` fits, because value graphs are
already guarded acyclic. Global label resolution remains owned by the application. See also
[SQLAlchemy](../sqlalchemy/README.md#applicability-cbo-020).

## Coverage limits

- No live database runs were made, so clone timing and actual ACL loss were not observed. The
  ACL-loss conclusion rests on the documented behaviour plus the coordinator-verified revision
  statements.
- PostgreSQL 18's Unicode version was not re-verified. The repository asserts it natively.
