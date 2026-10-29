# Engineering and operator workflows

This page records comparative judgments for CBO-010 (native test databases), CBO-011 (outcome
classification on the qualification route) and CBO-004 (principals, pools and the regeneration
path). Baseline, inputs and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/` unless they start with `docs/` or `scripts/`. Every recommendation is
**Proposed**.

<a id="cbo-010"></a>

## CBO-010 — Native head template with database-ACL replay and an equivalence assertion

**Premise, settled by probe and extended.**
- **Scale.** The semantic fixtures serve 42 test files, about 217 tests. Each test bootstraps
  through 29 revisions.
- **The probe confirmed the ACL loss.** A clone of a migrated template has `datacl NULL`, so the
  reader and evaluator gain TEMP. A generic `aclexplode` replay restores the identical set
  ([evidence](../../design_review/evidence/2026-10-29_library-leverage-review-probes/README.md)).

The G5 review added:
- **Nothing tests the TEMP posture.** No test or source checks `has_database_privilege`, `datacl` or
  `ON DATABASE` (searched). A template route that dropped the replay would therefore pass the whole
  suite silently.
- **Only the database ACL diverges.** No revision runs `ALTER DATABASE … SET` or embeds the database
  name elsewhere (searched).
- **The legacy `PgAdmin` harness already has the mechanisms:** keyed template, advisory lease, prefix
  sweep and builder lock. It still serves five files, including a test of the *semantic* `ci db init`.
  Its `DROP … WITH (FORCE)` cannot work here, because the operator cannot terminate restricted-login
  backends.
- **Decision text disagrees with the deployment (coordinator-verified).** ADR-0025 says the writer
  has no "generic temporary-table creation", but revision 0007 grants the writer `TEMP ON DATABASE`
  ("Inference owns private temporary work").

**Options.**
- **A.** A native head template built once per session, plus a generic ACL replay and an assertion
  that the clone's ACL equals the template's. Residue is owned by the generalized legacy lease and
  sweep, with the 55006 wait-drop.
- **A′.** A, but with the template kept across sessions under a key. That brings key obligations:
  `.py` and `.sql` revisions, `env.py`, extension versions, `server_version_num`, and role inventory
  *including oids*, because object ACLs store oids.
- **B.** pytest-postgresql. Its clone names are fixed, it builds from `template1`, terminate-on-drop
  errors, and it has no ACL replay or lease.
- **C.** Keep per-test bootstrap and add only a sweep.

Outer-transaction rollback and TRUNCATE-reset are rejected: native claims need real commits and
separate logins.

**Revealing case.**
- Bootstrapping each test from bare exercises the frozen deployment every time.
- Under A, the frozen deployment still runs once per session from bare, and in the migration and
  revision-pair tests.
- With the replay and the assertion, a clone is equivalent at database level. Without them, the
  template route silently weakens ADR-0025 posture.
- The operator still has to accept this reading of the plan's "fresh … frozen deployment" wording.
  This is DTA-002's open interpretation.

**Recommendation: recommended target A.**
- **Fixtures:**
  - `semantic_head_template` (session scope);
  - `semantic_db_engine` (same contract: a per-test clone plus replay and assertion);
  - `semantic_bare_engine`;
  - `semantic_database_at(revision)`, which uses the existing `migrations.upgrade(conn, target)`
    with era-shaped raw-SQL data, then upgrades to the next revision;
  - `semantic_evaluator_engine`, replacing three ad hoc engines.
- **Role preflight** checks all four roles, taken from one principal-constant owner (CBO-004).
- **One residue owner** for both harnesses' prefixes.
- **Bare bootstrap stays for** `test_migrations.py`, the `ci db init` test, the revision-pair tests,
  and **one new posture test**:
  - the reader and evaluator lack TEMP;
  - the publisher has it;
  - the writer matches whatever ADR-0025 settles.
- **What disappears:** bootstrapping 29 revisions per test, hand-checked residue, and a separate
  semantic harness lifecycle.
- **Possible follow-on:** a second template level holding a persisted standard release, whose key is
  free because release ids are digests. It is gated on [CBO-002](release-lifecycle.md#cbo-002).

**Rule impacts.**
- The operator's reading of the PostgreSQL plan's wording.
- The ADR-0025 versus 0007 writer-TEMP discrepancy goes to the ADR-0025 owner.

<a id="cbo-011"></a>

## CBO-011 — Stream outcomes and make hangs fatal

**Premise, sharpened.**
- `grammar.py` saves and restores the SIGALRM handler, but calls `setitimer(ITIMER_REAL, 0)` at the
  end. That **cancels** any outer timer (coordinator-verified). pytest-timeout's signal method would
  therefore silently lose its timeout on every grammar test, rather than merely conflict.
- The corpus skip reason ("… is absent") has no `blocked:` prefix, so outcome mapping cannot rely on
  reason prefixes.
- The Rust crate has zero tests. nextest is already bounded against hangs through
  `.config/nextest.toml`.

**Options.**
- **A.** `pytest-reportlog` (`--report-log`). It writes per-report `TestReport`/`CollectReport` JSON
  lines, flushed after each write (upstream source; not installed). Combine it with the built-in
  `faulthandler_timeout` plus `faulthandler_exit_on_timeout=true`, `--hypothesis-profile=ci`, `-rA`,
  and a small stdlib classifier under `scripts/`.
- **B.** Built-in JUnit with faulthandler-exit, treating a missing JUnit file as failed. JUnit is
  written only at session end, so a hang loses every outcome.
- **C.** pytest-timeout. Rejected: the signal method is silently disabled by the grammar, and the
  thread method is equivalent to faulthandler.
- **D.** Per-test subprocesses. Disproportionate, and it breaks session-scoped fixtures such as the
  CBO-010 template.

**Comparison.**
- **A survives a hang.** It keeps every completed test's record, the collected manifest and the hung
  item's setup record. Execution order is collection order. So the classifier marks the hung item
  `failed (hang)`, using faulthandler's dump; later items `not_run`; earlier items as reported. A
  missing `SessionFinish` record marks an interrupted run
  ([LOP-X011](../assessment-patterns.md#lop-x011)).
- **faulthandler** uses a watchdog thread, so it does not collide with SIGALRM.

**Revealing case.**
- `derandomize=True` makes every qualification explore the same cases. Exploration therefore stays
  in the dev profile, while qualification needs replay.
- A generous per-test faulthandler bound bounds hangs. It is a policy, not a performance
  measurement.

**Recommendation: recommended target A.**
- **Routes.** `test-all` becomes the classified, qualifying route; `check` and `py-test` remain
  developer routes.
- **Outcome mapping:**

  | pytest result | Classified outcome |
  |---|---|
  | passed | passed |
  | failed or error | failed |
  | skipped | blocked, with the reason |
  | collected but unreported | not_run |
  | hang | failed (hang) |

- **Provider context recorded per run:** the masked settings report, server version, ADBC driver
  path and `rustc --version`.
- **nextest:** `--no-tests=warn`.
- **Selection:** add the semantic fixtures to `DB_FIXTURES`, so the native union can be selected
  (DTA-003).
- **Remaining for SP-10:** declaring which node ids make up the required union.

**Rule impacts.**
- AGENTS "Commands" text for `test-all`.
- Adding `pytest-reportlog` is an ordinary pinned dependency move.

<a id="cbo-004"></a>

## CBO-004 — Retain one engine per purpose phase; harden principal derivation

**Premise.** Largely realized.
- **The phases are sequential.** `ci regenerate` opens one engine per phase: maintenance (with
  `SET LOCAL ROLE corpus_sem_publisher`), then write, then maintenance. No current process holds two
  logins at once; the callers were checked.

**Defects the refresh missed** (coordinator-verified where marked):
- **Read falls back to the owner.** `connection_settings(…, "read")` falls back to the URL's own user
  unless that user is exactly `corpus_sem_writer`. A test locks in read-as-owner for a non-writer URL
  (verified). An owner URL therefore silently runs reads with owner powers.
- `purpose` defaults to `"write"`.
- **Role names are literals** in seven places outside the frozen migration SQL.
- **Release persistence and activation use the operator login.** The publisher is NOLOGIN and is
  reached through SET membership. D3 says "The application never receives migration credentials",
  and ADR-0030 says CLI entry points use restricted credentials. Both are only approximately true
  for `ci regenerate`.
- **Concurrent-work hazard** (coordinator-verified; another agent's uncommitted tree).
  - `cli/regenerate.py` now issues `SET LOCAL ROLE corpus_sem_publisher` before `persist_release`.
  - `persist_release` inserts directly into `sem.release` and the `sem.*` projections.
  - The publisher has only `USAGE` on schema `sem` and `SELECT` on its tables. No INSERT grant was
    found.
  - A first-time persist should therefore fail with permission denied.

**Options.**
- **Pools:**
  - **P1:** sequential engines per purpose through `open_store` (current), reading D3 §1 as one
    pool per authenticated login.
  - **P2:** concurrent per-login pools.
  - **P3:** `NullPool` with plain creators. Rejected: a second connection-opening path that must
    repeat the adapters, extension check and classification.
  - `NullConnectionPool` behind `NullPool` remains ruled out at 3.3.3.
- **Settings:**
  - **S1:** flat purpose URLs (current), with the derivation hardened.
  - **S2:** nested principal sections.

**Revealing case.**
- An operator debugging with an owner URL loses the silent read-as-owner. That is intended.
- An explicit `evaluator_url` with another login name must still pass. So "expected principal" means
  *is or has the declared role, and is neither superuser nor schema owner*, not strict name equality.

**Recommendation: retain P1 and S1, with a bounded hardening target.**
- **Principal constants.** One owner holds the four role constants and `missing_roles(conn)`. It is
  consumed by `connection_settings`, `authored_sql`, `execution_admission`, `regenerate`'s
  `SET LOCAL ROLE`, the `ci db init` preflight and the test fixtures.
- **Purpose becomes required** in `open_runtime_engine` and `connection_settings`, which changes
  three call sites.
- **Read always derives the reader** unless a `reader_url` is given.
- **Purpose URLs naming another endpoint are refused.**
- **`open_store` asserts the principal** after `pool.wait`, alongside the extension check.
- **A `conninfo(settings, purpose)` accessor** gives ADBC and psycopg one connection authority (for
  [CBO-007](consumer-read-boundary.md#cbo-007)).
- **Regenerate classifies database errors** through `classify_error`: retry-class means "failed;
  resume with `--resume-run N`", and a defect means "refused" (CBO-012).
- **Kept as is:** the provisioning script, and test fixtures choosing logins directly. In tests the
  login is an independent expectation.
- **Move to P2 when** the first long-lived process needs two logins at once, for example MCP read
  tools under ADR-0025's "catalog admission under the actual restricted reader".

**Rule impacts.**
- **D3 §1 / D9 "Connections":** amend to "one psycopg pool per authenticated login per process;
  SQLAlchemy borrows; COPY never acquires another connection". If the operator treats this as a
  change, it needs a short ADR, but not a supersession of ADR-0025.
- **D3 "Roles" paragraph:** stale against the semantic principals.
- **Unsettled, for the ADR-0025/0030 owner:** either D3 states that release persist and activate are
  operator-credential phases reaching the publisher through `SET ROLE`, or a fifth non-owner
  admission login is added. This bears directly on the concurrent-work hazard above.
