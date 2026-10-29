# Native integrity and execution

This page records comparative judgments for:
- the shared `sem.*` immutability decision;
- CBO-019 (meaning recomputation and whole-realization revalidation);
- CBO-008 (the drift half: the physical schema is written twice);
- CBO-014 (the transport routine);
- CBO-015 (the typed-value codec mirror);
- CBO-020 (known-input loading);
- CBO-022 (the inference fixed point).

Baseline, inputs and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/` unless they start with `docs/`. Every recommendation here is
**Proposed**.

<a id="sem-immutability"></a>

## Shared decision: make `sem.*` and admitted content rows immutable, enforced by triggers

**Judgment: recommended.** This enforces a decision that already exists; it does not change one.
ADR-0025 and DESIGN already say that release rows and admitted content are immutable.

What the code shows:
- **Nothing writes these rows after insert.**
  - Release persistence only inserts. An identical replay compares rows instead
    (`src/corpus_structure/semantic/releases.py` `persist_release`).
  - The only DML on `data` or `sem` in the migrations and `src/` is `DELETE FROM data.selection`
    (mutable by design) and updates of the lifecycle tables `data.realization` and `data.project`.
  - No foreign key cascades.
- **Nothing enforces immutability either.**
  - No trigger exists on any `sem.*` table or on the admitted content tables.
  - `semantic_0003_publication.sql` grants the publisher `SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA data`.
    Any SECURITY DEFINER function owned by the publisher can therefore update content.
  - The dead `routines.deploy_routines` repeats that grant (coordinator-verified).
- **Precedent exists in the repository:**
  - the `immutable_completed_result` and `immutable_method_contract` triggers;
  - since `8db1889`, which landed after the reviewers finished, `immutable_source_frame` and
    `no_truncate_source_frame` (`BEFORE UPDATE OR DELETE` plus `BEFORE TRUNCATE`) on the new
    `ops.source_frame` tables. The revision 0030 admission descriptor attests them (`87c0503`).

  This is the recommended shape, already applied to one family of tables.

**Target.**
- **Refusal triggers.** Add `BEFORE UPDATE OR DELETE … FOR EACH ROW` and
  `BEFORE TRUNCATE … FOR EACH STATEMENT` refusals on:
  - every `sem.*` table;
  - the admitted content tables: entity, typed_value, value_role, fact, membership, occurrence,
    support, evidence and its links, derivation and its premises, coverage, assessment, input
    lineage, alternatives, identity exclusions, batch.
- **Exclusions:** `data.realization`, `data.project`, `data.selection`, the `ops.*` lifecycle tables
  and `eval.*`. `eval.*` needs a separate decision.
- **Descriptor coverage.** Add the triggers to the native execution descriptor
  (`data.execution_contract_descriptor()`). It already checks `tgenabled` and the trigger-function
  digests, so admission would refuse a missing or disabled guard.
- **Grants as a second layer.** Revoke content-table `UPDATE` from the publisher.

**What the triggers do not stop.** The table owner or a superuser can still disable or drop a
trigger, and `session_replication_role=replica` bypasses triggers. A future backfill must disable and
re-enable explicitly in reviewed SQL, which keeps it visible.

**Settling condition.** The operator confirms that no in-place correction or retention workflow is
intended. Corrections mean a new realization or a rebuild.

**What it unlocks.**
- Simplifying [CBO-019](#cbo-019).
- A meaningful verification record for [CBO-003](release-lifecycle.md#cbo-003). Without it, a
  recorded digest proves nothing beyond its own transaction.

**Rule impact.** None to a §B decision; it realizes ADR-0025.
- ADR-0025 is accepted, and accepted ADRs are immutable.
- Removing the meaning-only recheck under ADR-0025's "validates candidate plus admitted state"
  therefore needs either a follow-up ADR, or a clarification in the owning section if the operator
  reads that wording as already allowing it (see CBO-019).

<a id="cbo-019"></a>

## CBO-019 — Meaning recomputation and whole-realization revalidation

**Premise, refined.** The head `publish_contract_batch` (`semantic_0027_transport.sql`) does three
whole-realization things:
- **(a)** recomputes `fact_identity` for every admitted fact;
- **(b)** recomputes the report meaning for every occurrence;
- **(c)** re-checks property applicability and `validate_property` for every occurrence, plus the
  `validate_state`, `occurrence_context`, `entity_source` and `alternatives` validators.

(a) and (b) defend only against mutation from outside the publication route. They catch it only at
the next publish into that realization, and never after finish. (c) has a legitimate cumulative
reason: a later batch can add memberships to existing entities, which changes which constraints
apply to earlier occurrences.

Elsewhere, the qualified key is recomputed by analytical capture (per fact) and by inference (up to
three times per seed fact).

**Options.**
- **A.** Retain.
- **B.** Immutability, then drop (a), scope (b) to staged occurrences, and keep (c).
- **C.** B plus a persisted `data.fact.qualification_key` written by protected publication from the
  staged rows and read by capture, inference and SP-08 conflict grouping.
- **D.** B plus scoping (c) to the affected subjects.

**Revealing case.** Because memberships grow across batches, validating only the staged rows would
accept an occurrence that has become invalid. That rules out naive delta checks for (c).

**Recommendation.**
- *Recommended target:* B, together with the trigger revision.
- *Conditional:* C, with the next transport revision or when SP-08 conflict grouping needs it.
  Generated columns are ruled out: the expression is STABLE and reads other rows and tables.
- *Unsettled:* D, until a measured or regeneration workload shows many batches per realization.
  Today there is one consolidation batch plus one inference batch.

**What disappears.** The meaning-only loops. Once C lands, per-consumer
`value_meaning(…, qual=true)` calls disappear too.

**Library basis:** [`postgresql/persisted-derived-key`](../libraries/postgresql/README.md#postgresql-persisted-derived-key).

<a id="cbo-008"></a>

## CBO-008 — Drift between frozen migrations and the derived MetaData

**Premise, settled by probe.**
- **The configured check is not clean.** Alembic's `command.check` at head `semantic_0029` reports
  49 differences
  ([evidence](../../design_review/evidence/2026-10-29_library-leverage-review-probes/README.md)).
  Revision 0030, committed afterwards in `8db1889`, adds physical declarations that were not
  probed.
- **All 24 constraint pairs are naming-only.**
  - CHECK expressions are equal under PostgreSQL deparsing.
  - Unique constraints have identical columns.
  - `physical.yaml` declares unique-key names (`bound_observation`, `source_row`), but
    `_compile_physical` drops them.
  - The one `modify_default` is an Alembic false positive. Alembic evaluates the volatile
    `gen_random_uuid()::text` on the server, and its own source comments on the limitation.
- **Committed revisions were edited in place** (coordinator-verified):
  - Revision 0028's `eval.document_split` CHECK changed from `('dev','test')` to
    `('dev','test','reserved')` while keeping the digest name `…_23de252598`, which is the sha256 of
    the old text.
  - Commit `51bba6c` also edited revision 0027.
  - A database migrated before the edit holds a different expression under the same name. A
    by-name check cannot see this, and a fresh-database check never does.
- **A native catalog check already exists.** `data.execution_contract_descriptor()` (revisions
  0026–0029) compares function bodies, owners, security and EXECUTE roles, triggers, reader grants
  and index definitions at composed admission. It is hand-copied into four revisions, with hash
  constants in `execution_admission.py`.

**Options.**
- **O1.** A forward reconciliation revision, plus `command.check` as a functional SP-10 check, with
  a `compare_server_default` callable for the volatile default.
- **O2.** O1 plus comparing deparsed constraints and indexes (`pg_get_constraintdef`/`pg_get_indexdef`)
  between a migrated head and a `create_all` database.
- **O3.** A separate golden catalog snapshot of functions, grants and owners.
- **O4.** Extend and *generate* the existing descriptor, instead of O3.

**Revealing case.** A reconciliation that only renames would *hide* stale expressions. On an older
database it would stamp the current digest onto the obsolete `('dev','test')` CHECK.

**Recommendation: recommended target (O1 + O4).**
- **One reconciliation revision, produced by the emitter (see CBO-014):**
  - CHECKs are dropped and re-added from MetaData (`AddConstraint` compile), so every database
    converges regardless of its history.
  - Uniques are renamed with `ALTER TABLE … RENAME CONSTRAINT`. Foreign keys depend on them, and
    PostgreSQL renames the backing index.
- **`command.check` placement:** it becomes the SP-10 physical-evolution check at head, and also a
  post-step of `ci db migrate` on long-lived databases. That is the only place where in-place
  history edits become visible.
- **Functions, triggers and grants: O4.** Generate the descriptor and its hash constants at
  authoring time, and add the partial indexes and the immutability triggers to it.
- **O2:** unsettled, and low priority once CHECKs are generated.
- **Remaining blind spots:** the `data.selected_fact` view, the database ACL (CBO-010 replay) and
  `ALTER DATABASE … SET`.

**Rule impacts.**
- **Freeze point (ADR-0025 owner, through a follow-up ADR or the owning section):** name it. A committed revision is never edited;
  corrections go in a new revision. Revisions 0027 and 0028 are counterexamples.
- **SP-10 plan:** name the check in the physical-evolution row.
- **Binding:** confirm this is a functional check, not alignment linting.

Where the lowering lives is judged in [retirement dependencies](retirement-dependencies.md#cbo-008-location).

<a id="cbo-014"></a>

## CBO-014 — The transport routine

**Premise corrected: the generator is not stale.**
- Rendered with the current `STAGE_TYPES`, `routines._transport_sql` produces every per-relation
  create, verify, content and insert line (26 relations) verbatim in the head transport.
- The only differences:
  - the function's name, which was renamed `publish_contract_batch` in revision 0023;
  - the order of the `identity_exclusion` relation;
  - the missing `data.end_stage`, which holds the disposal guards for the two newest relations.
- So the transports are generator output plus hand edits, with no authoring command wired up.
- `deploy_routines` is dead and dangerous: it grants `UPDATE` on all `data` tables.

**Options.**
- **A.** Retain; runtime verify catches mismatches loudly.
- **B.** Wire the existing generator as the authoring emitter, with a parity test that needs no
  database.
- **C.** B plus emit table DDL through SQLAlchemy `CreateTable`, which reproduced frozen 0027
  exactly in the library assessment's probe.

**Revealing case.** Guards that exist only on the newest relations may be deliberate. They must
become explicit per-relation metadata (for example, optional disposal) rather than being flattened.

**Recommendation: recommended target C.**
- Update the template: current function name, an `end_stage` template, explicit relation order and
  disposal policy.
- Emit the next `semantic_00NN_transport.sql` deterministically. Quote with SQLAlchemy's preparer,
  not `psycopg.sql.Identifier`, which would change bytes.
- Add the parity test. It is a derivation check
  ([LOP-X002](../assessment-patterns.md#lop-x002)), not alignment linting.
- Delete `deploy_routines`.
- Extend the same emitter to the descriptor JSON and its hash constants. `pg_proc.prosrc` holds the
  body between the dollar quotes, so body digests can be computed from reviewed SQL.

**Library basis:** [`sqlalchemy/ddl-text-emission`](../libraries/sqlalchemy/README.md#sqlalchemy-ddl-text-emission).

<a id="cbo-015"></a>

## CBO-015 — Typed-value codec around the deliberate mirror

**Premise.**
- `str(raw)` in `consolidation.py` is safe for meaning, because both Python `_meaning` and native
  `decimal_canonical` canonicalize.
- It is not authored-preserving: `0.0000001` is stored as `1E-7` while `1.50` keeps its trailing
  zero. So `decimal_lexical` is currently neither authored text nor canonical text.
- The non-boundary copies are:
  - `types.py` (qualified meaning);
  - `evaluate/semantic_alignment.py`, which re-implements qualified meaning;
  - query decode;
  - Arrow per-row normalization.
- `observations.source_value` is a separate contract.

**Options.**
- **A.** Retain the hand vectors.
- **B** ([LOP-X003](../assessment-patterns.md#lop-x003)): one written specification, Hypothesis
  differential parity against the native functions, pinned independent `@example` vectors, and
  alignment's qualified meaning consolidated onto the `types.py` owner.
- **C.** B plus a specified lexical form in the encoder.

**Revealing cases.** These must go into the specification and the vectors:
- NUL characters and lone surrogates: Python accepts them, PostgreSQL text refuses them.
- `-0.0` versus `0.0`: their float hex differs, so they are distinct facts.
- `0E-10` and `-0`.
- Exponents beyond NUMERIC bounds.
- Casefold specials (ß, ﬁ, İ) at Unicode 16.

**Recommendation.**
- *Recommended target:* B. Run Hypothesis lists per example in one `SELECT … unnest` round trip, so
  the engine fixture need not be function-scoped. It depends on the [CBO-010](engineering-workflows.md#cbo-010)
  template.
- *Unsettled:* C. The specification must first choose between authored-preserving and plain
  `format(raw, "f")`.

**Library basis:** [`hypothesis/differential-native-parity`](../libraries/hypothesis/README.md#hypothesis-differential-native-parity);
the pyarrow edge-case caution in [`pyarrow/exact-numeric-boundary`](../libraries/pyarrow/README.md#pyarrow-exact-numeric-boundary).

<a id="cbo-020"></a>

## CBO-020 — Known-input loading

**Premise refined.**
- `ids` is every entity with a membership in the realization. Every `.in_(ids)` — and the
  exclusion-link, evidence and observation `.in_` lists — can be derived in the database. This is
  [LOP-X005](../assessment-patterns.md#lop-x005) in pure form.
- Decoded fields are used only for identity keys and the label.
- The registry is scanned per fact.
- **Possible defect, for the SP-08/09 owner to confirm:** evidence and evidence_source rows are
  carried forward for *all* known entities. Only the membership tables are filtered by the used set.

**Options.**
- **A.** Replace the IN lists: subqueries, joins, or an `= ANY(:array)` bind.
- **B.** A plus restricting facts to the identity, required and display properties, computed once
  from the release.
- **C.** B plus a recursive closure from the resolved used set.

**Revealing case.** Narrowing by reachability before resolution would drop known label anchors and
change which identities are chosen.

**Recommendation.**
- *Recommended target:* B, with the registry scan precomputed.
- *Unsettled:* C, until native `kind='entity'` traversal is shown to equal the release-typed walk
  ([CBO-016](consumer-read-boundary.md#cbo-016)).

**Library basis:** [`sqlalchemy/array-membership-binding`](../libraries/sqlalchemy/README.md#sqlalchemy-array-membership-binding).

<a id="cbo-022"></a>

## CBO-022 — The inference fixed point

**Premise.** Valid, but low consequence. The larger growth term is proof enumeration: every direct
transitive witness pair becomes a derivation, which grows roughly as n³ along a chain.

**Options.**
- **A.** Retain.
- **B.** Semi-naive, using a `round` column on the existing temporary work table. Single-atom rules
  read `round = k`; the transitive rule runs delta⋈all and all⋈delta; new rows get `k+1`.
- **C.** Per-stratum `WITH RECURSIVE`. Ruled out: the rules feed each other and the transitive rule
  joins the relation with itself.

**Recommendation.**
- *Recommended target, low priority:* B. It reaches the same least fixpoint, and proofs are
  unchanged because they come from the final table.
- Whether to emit one representative witness instead of all of them is a proof-policy question for
  the ADR-0027 owner. No change is recommended here.

**Library basis:** [`postgresql/recursive-fixpoint`](../libraries/postgresql/README.md#postgresql-recursive-fixpoint).
