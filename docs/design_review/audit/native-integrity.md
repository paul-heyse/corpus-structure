# Native integrity

**Freshness:** findings retain their stated older evidence except where explicitly refreshed.
The [November 1 engagement refresh](README.md#unified-model-refresh)
narrows current reliance; inherited prose is not a newly verified current defect.

These findings concern what the PostgreSQL layer itself guarantees, at the
[audited baseline](README.md#baseline):
- which writes it refuses;
- which principal may perform which effect;
- whether its structure and routines have one authority and a recorded identity.

ADR-0025 makes this layer the enforcement boundary for publication. The operator selected it as an
emphasis area for this audit.

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with
`docs/` or `scripts/` (repository root), `tests/` (`python/corpus-structure/tests/`) or `rev/`
(`python/corpus-structure/semantic_alembic/versions/`). Probe results are in the
[audit probe evidence](../evidence/2026-10-29_design-principle-audit-probes/README.md) (P1–P6).

Native code that binds release semantics by literal name has its primary home on the semantic
page ([DA-026](semantic-model-and-authority.md#da-026)). The execution cost of native revalidation
is on the execution-fit page ([DA-033](execution-fit.md#da-033)).

<a id="da-029"></a>

## DA-029 — Immutability of release rows, admitted content, observations and grades is enforced unevenly

**Principles:** FP-05, DP-03 (G3), DP-05, DP-19 (G5); heuristics H18/H19. **Subject:** implemented,
judged against accepted decisions:
- ADR-0025: "immutable release rows";
- DESIGN §B5;
- ADR-0030: "previous grades remain immutable".

### Diagnosis

The property "immutable once written" holds for several families of rows, and each family uses a
different mechanism, some of them none.

| Rows | Mechanism at head | Evidence |
|---|---|---|
| `ops.method`, `ops.completed_result`, `ops.source_frame*`, measurement custody, terminal `ops.task` | BEFORE UPDATE/DELETE refusal triggers. `ops.source_frame*` also refuses TRUNCATE; `completed_result` does not | `rev/semantic_0025_*.sql:20-27`; `rev/semantic_0023_execution.sql:269-276`; `rev/semantic_0030_source_frames.sql:28-45`; `rev/semantic_0024_*.sql:122`; `rev/semantic_0012_observation_inputs.sql:84` |
| `data.realization` after completion | `guard_completed_output` refuses any change once a completed result points at the row | `rev/semantic_0023_execution.sql` |
| `sem.*` release rows (14 tables) | **No trigger.** Privilege absence only: every restricted role holds SELECT. The tables are owned by the operator login, which archives releases | probe P1; `cli/regenerate.py:79-82` |
| Admitted `data.*` content: fact, occurrence, typed value, value role, support, evidence, membership, assessment, … | **No refusal trigger.** `corpus_sem_publisher` holds UPDATE on 29 `data` tables, DELETE on 10 and TRUNCATE on 9 | probe P1; `rev/semantic_0003_publication.sql:7`; `rev/semantic_0006_*.sql:403` |
| `kb.observation` and the source custody tables | Publisher holds INSERT and UPDATE; no trigger | probe P1; `rev/semantic_0006_*.sql:323` |
| `eval.*` reference sets, passes and evaluations (7 tables) | Publisher-owned, and the publisher holds INSERT/UPDATE/DELETE/TRUNCATE; no trigger | probe P1; `rev/semantic_0028_reference.sql:7-11` |

The UPDATE privileges were granted wholesale at 0003 and 0006: `ON ALL TABLES IN SCHEMA`. No
routine uses them on content tables; the only UPDATE and DELETE statements in the native code
touch `data.project`, `data.realization` and `data.selection`. Tables created later received only
SELECT and INSERT (for example `rev/semantic_0016_*.sql:21`). No `ALTER DEFAULT PRIVILEGES`
exists, so a table's posture depends on which revision created it.

Detection substitutes for prevention, and its strength differs by family:
- **`sem.*` is re-verified on every use.** Each `load_release` — every read session, run start,
  resumption, evaluation and activation — re-derives the release and byte-compares all projection
  rows and artifacts (`semantic/releases.py:446-465`). Tampering is caught the next time the release
  is used, not prevented.
- **`data.*` content is re-checked only by the next publish into the same realization.** That
  covers fact meaning only (`rev/semantic_0027_transport.sql:153-155`), not occurrences, evidence,
  membership or support. Completed realizations never receive another publish. Readers verify
  nothing: `ops.completed_result` records task and derivation id lists, not a content digest that a
  reader checks.
- **Nothing** re-verifies `kb.observation` or `eval.*`.

The operator login owns 59 of the 71 tables (probe P1). It can mutate them whatever the publisher's
privileges are.

The composed-model admission check attests writer and reader denials on `sem`/`data`
(`rev/semantic_0030_admission.sql:115-122`). It does not attest the publisher's privileges or the
TEMP posture.

### Consequence

Three routes can change admitted values, source observations or "immutable" grades without any
refusal or later detection. Archived definitions would be caught at their next use:
- owner-credential commands;
- any of the 53 SECURITY DEFINER routines (all run as the publisher);
- application Python running under `SET ROLE corpus_sem_publisher` ([DA-030](#da-030)).

Served answers and grades rest on rows whose immutability is a convention of roughly 40 definer
bodies and all maintenance code.

**Correcting a bad admitted fact** (scenario SC3) shows the gap from the other side. The model has
no correction, retraction or supersession concept. The sanctioned route is a fresh run of the
whole method (`ci run --fresh`; `ci regenerate` has no such option), which produces a new
realization and a selection CAS. Without `--fresh`, the default `agent_reuse="full"` replays the
identical bad output (`semantic/operations.py:208-226`). The unsanctioned route, a direct UPDATE by
the owner or the publisher, is open and goes undetected.

The whole-realization rechecks that partly compensate cost every publish
([DA-033](execution-fit.md#da-033)). They are a symptom of the same gap.

### Counterevidence and limits

- The ordinary principals cannot write `sem` or `data`; writer and reader have SELECT only
  (probe P1), and this is attested.
- `load_release` performs an exact reconstruction.
- With a single, peer-authenticated operator, the residual risk is defects rather than adversaries.
- The owner can always bypass triggers. Enforcement narrows the routes rather than closing them.
- Whether a correction or retention workflow should be able to change admitted rows in place is
  not decided anywhere (see SC3 in the [scenario list](README.md#scenarios)).
- The probe established privileges and trigger presence on a fresh head database. It did not test
  mutation.
- An earlier draft of this finding said `sem.*` detection came late. A scenario reviewer corrected
  it: `sem.*` is caught at every use (W2-B, 2026-10-29).

**Evidence:** diagnosed from source; privileges measured by probe P1 (2026-10-29).

**Lead:** the `ops.source_frame` pattern (publisher ownership, refusal of UPDATE/DELETE/TRUNCATE,
descriptor attestation), applied to the families above, with unused UPDATE grants revoked.

<a id="da-030"></a>

## DA-030 — Principal separation does not cover the release lifecycle, and purpose principals are derived from configuration

**Principles:** FP-05, FP-02, DP-03 (G3), DP-01 (decision against realization), DP-18, A3.
**Subject:** implemented, judged against:
- ADR-0025:45-47;
- ADR-0030: "CLI/MCP entry points use restricted semantic credentials";
- D3: "The application never receives migration credentials".

### Diagnosis

The effects that change what every consumer reads are archiving a release, activating it, and
selecting a completed result. Those are exactly the effects that no restricted principal performs
through a protected routine.

- **(a) Archiving is an owner operation.** `persist_release` runs on the maintenance credentials
  (`cli/regenerate.py:79-82`; `settings.py:36`), which are the migration owner. All `sem.*` tables
  belong to that login, and no restricted role holds INSERT on them (probe P2).
- **(b) Activation and selection run application Python under an assumed role, and native code
  treats that role as proof of a reviewed routine.**
  - `ci regenerate` issues `SET LOCAL ROLE corpus_sem_publisher` and then runs
    `activate_release` and the selection from Python (`cli/regenerate.py:143-171`).
  - Native guards use `current_user='corpus_sem_publisher'` to tell protected completion from
    direct DML (`rev/semantic_0012_observation_inputs.sql:42,87,94`; `rev/semantic_0023_*.sql:215,248`;
    `rev/semantic_0020_*.sql:5`).
  - The operator holds `SET` on the publisher role (`scripts/pg_semantic_roles.sh:37`; probe P1:
    `set_option` true, `inherit_option` false).
  - So any operator session that assumes the role satisfies the "protected publication" checks.
  - Activation also updates `data.project` directly, while selection goes through a SECURITY DEFINER
    routine. One pointer pair has two privilege patterns.
- **(c) The activation principal is not part of the activation contract.**
  - Tests activate as the owner; regenerate activates as the publisher.
  - Latent consequence: a release with authored SQL cannot be activated through regenerate. No
    `reader_conn` is passed (`semantic/authored_sql.py:291`), and the publisher lacks INSERT on
    `sem.sql_admission`. No current pack has authored SQL, so this has not been triggered.
- **(d) Purpose principals are derived by literal username substitution.**
  - `connection_settings` maps a URL whose user is exactly `corpus_sem_writer` to the reader.
  - Any other user name is kept for reads, and the evaluator defaults to a name substitution
    (`semantic/runtime.py:28-42`).
  - An owner-configured URL therefore makes query, explain, export and the MCP worker run with
    owner powers, silently.
  - Session identity is verified only inside authored-SQL admission (`semantic/authored_sql.py:194-201`).
- **(e) The TEMP posture differs from the decision text.**
  - Revision 0007 grants `TEMP ON DATABASE` to the writer (`rev/0007_qualified_inference.py:21`) for
    inference's work table (`semantic/inference.py:76-90`). Probe P1 confirms writer TEMP.
  - ADR-0025:46 says the writer has no generic temporary-table creation.
  - Staging stays safe because `begin_stage` refuses pre-existing relations and checks ownership.
  - Neither the ADR nor admission records the actual posture.

### Consequence

The privilege model protects the writer and reader paths well. It does not protect the archive,
activation and selection paths, and those decide what every consumer reads. "Who may perform this
effect" is not part of any operation's contract, so a defect in maintenance Python or a
misconfigured URL changes the effective principal without any refusal. The accepted decision text
(ADR-0025's TEMP sentence, D3's credential sentence) no longer describes the deployment.

### Counterevidence and limits

- The operator's `SET` membership in the publisher role is deliberate. Migrations need it to create
  definer routines owned by the publisher. The defect is reusing that membership at runtime
  (`cli/regenerate.py:146`).
- Under peer authentication the separation guards against defects, not adversaries.
- The project-update trigger still runs full admission whatever the role.
- The statistics and transfer journeys completed through this path (STATUS, 2026-10-29).
- The leverage review's earlier lead — that `persist_release` ran under the publisher role — is
  **not reproduced** at this baseline. Persistence runs as the owner, which is item (a).

**Evidence:** diagnosed from source. Membership, TEMP and privileges measured by probe P1. Item (c)
is suspected; it was not executed.

**Lead:** protected archive, activate and select routines, or a non-owner admission login; a
declared principal per purpose, verified when the engine opens.

<a id="da-031"></a>

## DA-031 — Relation structure has two hand-maintained authorities, and no check compares their bodies

**Principles:** FP-04, A2, DP-01 (G1), DP-24 (G2), DP-03, DP-23; §G "generated from one source".
**Subject:** implemented, judged against ADR-0025 and DESIGN §B4: "the trusted physical LinkML
module derives shared Core metadata".

### Diagnosis

`physical.yaml`, compiled into SQLAlchemy MetaData, is the declared authority for the relational
structure that Core queries, staging types and Arrow projections rely on (`semantic/metadata.py`;
`semantic/publication.py:279-290`). Only revision 0001 is a frozen projection of it. From 0006 to
0030, every table, constraint and index is hand-written SQL in the revision chain, beside a second,
independent statement of the same facts in `physical.yaml`. That second statement is
`ph:checks`, `ph:foreign_keys` and `unique_keys` written as JSON inside YAML.

Nothing compares the two bodies:
- The only parity test compares column *names* (`tests/semantic/test_migrations.py:22-25`). It is
  cited as evidence of scope, not as test architecture.
- No `command.check` or `compare_metadata` call exists outside evidence folders.
- The configured `checkconstraint_byname` plugin compares CHECK constraints by name only (Alembic
  1.20.0, `ext/checkconstraint_byname.py`, Interface-checked). The digest-named CHECK convention
  (`schema/relational.py:55`, `check_name`) exists so that a member change shows up as a name
  change. It only works if the SQL is regenerated from the MetaData, and it is not.
- `PHYSICAL_MODEL_ID` is a byte hash of the YAML file (`semantic/metadata.py:21`), so any edit
  changes it, even a comment.
  - The constants recorded in revisions 0001 and 0003 are inert.
  - The live native record is the descriptor's `physical_id` (0026–0030). It equals today's hash and
    gates only authored-SQL admission (`rev/semantic_0030_admission.sql:27`).
  - After any physical edit, authored-SQL releases would refuse until a new descriptor is deployed.
    That is latent, because no pack ships authored SQL.
- The descriptor attests columns, primary keys and foreign keys for two tables only:
  `ops.source_frame` and its sentences.
- A body-level catalog comparator exists for the legacy tree (`tests/db/test_migration.py:100-111`),
  not for the native one.

The physical compiler, naming convention and digest naming live in the legacy `schema.relational`
module (`semantic/metadata.py:18`; [DA-045](boundaries-and-composition.md#da-045)).

**Probe P3 (2026-10-29) shows the two statements currently agree body for body on a fresh head
database:**
- columns: 471 against 471;
- indexes: 112 against 112;
- constraint definitions identical, apart from the two native constraint triggers on `ops.run`;
- 69 constraints carry different names (PostgreSQL default names in the hand SQL against the
  MetaData convention);
- Alembic's configured check reports 49 operations.

**The drift that can pass unseen is a changed body under an unchanged name.** That has already
happened. Revision 0028 was edited in place while it was head (commit `01da23a`):
- its `ck_document_split_physical_23de252598` now enforces `('dev','test','reserved')`, while the
  digest in its name is that of `('dev','test')` (`rev/semantic_0028_reference.sql:19`);
- the MetaData names the new body `ck_document_split_physical_a319d8e82e`;
- at head, Alembic does report the name difference, but buried among 49 naming-only operations.

What is invisible is a database built from the earlier 0028 text: same name, same version row,
different expression. No check runs on long-lived databases ([DA-032](#da-032)).

### Consequence

Adding a column, a closed-set member or a constraint takes two independent edits, kept equal by
care. A type or staging-shape mismatch fails loudly at publish. A mismatch in a CHECK body,
nullability or foreign key silently changes what the database admits, and the configured
detector cannot see it.

### Counterevidence and limits

- At head, the two statements agree, so the risk lies in change, not in the current state.
- The 0030 source-frame tables are fully shape-attested by the descriptor.
- The operational database was built at 0030, after the in-place edits.

**Evidence:** diagnosed from source; body parity measured by probe P3; plugin behaviour
Interface-checked.

**Lead:** derive revision DDL from the MetaData, or compare bodies at head and after migration of
long-lived databases as a functional check; record the realized physical identity with each
revision.

<a id="da-032"></a>

## DA-032 — Native evolution is hand-propagated, committed revisions were edited, and no deployment identity is recorded

**Principles:** DP-24 (G2), DP-16, DP-01 (derived artifacts record their derivation), DP-21,
FP-06, A1; heuristic H27. **Subject:** implemented.

### Diagnosis

The native routines and their attestation evolve by copying, and the result is not identified
anywhere it is used.

- **Whole routines are copied into each revision.**
  - The publication routine is fully redefined in nine revisions: as `publish_batch` in 0003, 0006,
    0008, 0014, 0016, 0017 and 0021, and as `publish_contract_batch` in 0024 and 0027. Revision 0023
    adds only a wrapper.
  - The function bodies are 24–43 KB (the transport files 57–71 KB), and consecutive copies differ
    by 22–38 statement lines.
  - `begin_stage` has eight full definitions.
  - The descriptor (38–50 KB) and `require_execution_release` (11–16 KB) are re-emitted in every
    revision from 0026 to 0030.
- **The current body can only be found by replaying the chain.**
  - Nine `ALTER FUNCTION … RENAME` steps layer the chain: the current `validate_state` calls
    `validate_pre_contract_state` (0007's body), which calls `validate_pre_inference_state` (0011).
  - `finish_evaluation` has been renamed three times.
  - The S3 contributor reconstructed the head bodies with a pglast replay outside the repository.
- **The generator is not recorded.**
  - The transport revisions are derived from `STAGE_TYPES` plus the template
    `semantic/sql/publication.sql` by `semantic/routines._transport_sql`. No committed authoring
    step runs it.
  - `semantic/routines.py` and `semantic/sql/*.sql` have no consumer and are stale: none of the head
    validators appear in them. D3 still names them as the supplier of protected staging and native
    enforcement.
  - `deploy_routines` would grant UPDATE on all `data` tables to the publisher
    (`semantic/routines.py:98-110`).
- **The attestation is hand-maintained in three places.**
  - The descriptor JSON (`rev/semantic_0030_admission.sql:2-3`) is patched by one-off scripts.
  - The only generator is an evidence draft that writes to `/tmp`
    (`docs/design_review/evidence/2026-10-29_semantic-consumer-regeneration/draft-0031/generate.py`).
  - Python separately pins the descriptor and admission hashes (`_DESCRIPTOR_SHA256`,
    `_REQUIRE_SHA256`; `semantic/execution_admission.py:280-284`).
  - So the same facts live in the catalog, the descriptor and the Python constants.
- **"Frozen" revisions were edited in place while they were head.** The SQL of 0027 was edited
  five times (13:56–14:06 on 2026-10-29, including `51bba6c`), and that of 0028 four times
  (14:38–14:54, including `01da23a`). After each had a successor, only a ruff reformat touched their
  Python wrappers. The version table records only a revision id (`semantic/migrations.py:13`), so a
  database that applied an earlier text cannot be told apart.
- **Routine deployment is attested, but relation deployment and results carry no identity.**
  - The descriptor and its Python hash attest 89 function bodies, 34 triggers and 71 read grants.
    They are checked at activation, in Python and natively, and natively on every guarded write.
  - Relation and constraint identity is attested for only two tables ([DA-031](#da-031)).
  - `data.batch`, `data.realization` and `ops.completed_result` record no deployment identity. Once
    0031 lands, realizations admitted under 0030's rules and under 0031's rules will be
    indistinguishable.
  - `ci db` reports `model_revision` from code, not from the database (`cli/db.py:104, 122`).
- **Batch content has no format version (suspected).** Python orders receipt content by dataclass
  field order, and native code reconstructs it from a hand-ordered list
  (`rev/semantic_0027_transport.sql:88`). A run that straddles a transport revision could not
  resolve a lost-commit receipt (`semantic/publication.py:571`). The window is narrow.

### Consequence

The pending one-predicate correction (draft-0031, the STATUS blocker) shows what a change costs:
- copy a 70 KB function region into a new revision;
- re-hash and patch the descriptor with a script;
- regex-patch a Python constant.

Reviewers diff whole files rather than definitions. The extension path depends on knowledge
outside the repository. In-place edits make two databases at the same revision id differ, and
nothing records which rules admitted which data.

### Counterevidence and limits

- Frozen full-body revisions are conventional Alembic practice, and ADR-0025 makes the chain the
  authority for routines.
- Descriptor body hashes detect drift between source and deployment for routines, and attestation
  fails closed.
- Downgrades and legacy databases are refused (`cli/db.py:106-114`).

**Evidence:** diagnosed from source and git history.

**Lead:** one committed emitter for the transport routine and the descriptor; a deployment identity
in the version record and in receipts; a named freeze point; deletion of `deploy_routines`.
