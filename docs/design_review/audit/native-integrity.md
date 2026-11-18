# Native integrity

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`
([update](README.md#update-2026-11-18-5139eaba3); [baseline and limits](README.md#baseline)).
DA-074 and the earlier identities on this page were re-read at that source. Source paths omit
`python/corpus-structure/src/corpus_structure/`. No catalog was read and no database command
was run; statements about deployed roles or installed objects are about source.

<a id="da-074"></a>

## DA-074 — Native authorization and guard membership are code lists outside the declaration

**Update, 2026-11-18, source `5139eaba3`.** Stands, with a changed footprint. No role, guard
or grant fact entered the model in `d78c98765..5139eaba3`: the two model edits in the range add
a disclosure flag and three protocol definitions, and every `ph:read_roles` annotation is still
the empty list (84 of 84, search). What changed:

- *Role literals moved from SQL files into more Python modules, and their total fell.* Role
  names (`corpus_sem_*`) occur 199 times in 47 `.py` files at `5139eaba3`, and nowhere else
  in the package. At `d78c98765` they occurred 176 times in 39 `.py` files and 70 times in
  the sixteen `.sql` files, 246 in all (counts of occurrences by search at each commit). So
  the Python figure rose because the SQL files were converted, not because more role facts
  were written. The literals from the deleted SQL files reappear in
  `semantic/closure_native.py`, `semantic/native_admission_principals.py`,
  `semantic/native_admission_tables.py`, `semantic/native_admission_release.py`,
  `semantic/source_record_recognition_native.py:224`, `semantic/pdf_descriptor_native.py:125`,
  `semantic/original_document_native.py:123` and `semantic/demand_result_native.py:209`.
- *Two new modules hold role sets as tuples.* `native_admission_tables.py` (`920f1b746`) holds
  the four actor roles (`:27–32`) and the default read roles as a JSON string literal
  (`:176–184`), commented as "the preexisting archive contract, including its array order".
  `native_admission_principals.py` (`08284dc6f`) holds the source and runtime principal tuples,
  the application schemas and four private kernel signatures as text (`:8–16`), with three more
  role names inline.
- *The map from purpose to role is now written twice.* Once in the grant loop
  (`semantic/data_operation_storage.py:1899–1907`, five purposes) and once in
  `data.require_runtime_principal` (`semantic/closure_native.py:174–181`, four purposes, with a
  refusal for an unknown purpose).
- *One sub-item corrected.* The splice of generated comparisons at the literal text of a role
  check is gone with the hand-written `admission.sql` (`9364a5b88`); the privilege checks are
  typed and iterate `PURPOSE_ROLES` (`semantic/alembic_privileges.py`).
- *Two trigger renderings corrected, their membership unchanged.* The frontier-guard trigger
  and the shared-stream triggers are now built by a typed trigger constructor (`4760982d8`)
  instead of concatenated strings. Which relations they cover is still a hand list.

This finding is also the home of the principal-name part of
[DA-020](boundaries-and-composition.md#da-020).

**FP-01, FP-04/A2; DP-01, DP-02, DP-03.**

The physical model declares tables, columns, keys, checks, indexes and an immutability class
per relation, and immutability triggers are derived from those classes
(`semantic/target_installation.py:351–356`). The protocol declares purposes for public
operations, and the execute grants of protocol functions are derived from them
(`data_operation_storage.py:1897–1907`). The following are held only as literals:

- **Frontier guard.** Which relations are covered by the guard that refuses support and
  frontier writes in the same transaction after a demand read was acquired is a hand tuple of
  twelve table names (`data_operation_storage.py:1952–1965`). No declared attribute separates
  the guarded relations from the unguarded ones.
- **Shared-stream triggers.** Chosen by relation name (`target_installation.py:371`). The
  model declares exactly these two relations, and only these two, as
  `ph:immutability: pending-content` (`model/semantic/physical.yaml:1757, 1776`), and that
  value is carried into the compiled relation's `info`; no Python code reads it.
- **Role names.** Defined once as constants (`semantic/alembic_privileges.py:25–33`) and then
  written again in generators, as counted above, with none in the model. The four-role set is
  restated as tuples in `native_admission_tables.py:27–32`,
  `native_admission_principals.py:8–9` and `native_admission_release.py:400–404`.
- **The purpose-to-role map.** Two copies, as above.
- **Execute grants for non-protocol functions.** A chain of comparisons on function names
  (`data_operation_storage.py:1908–1928`), a table of `(label, schema, name, roles)` entries
  (`target_installation.py:227–249`, eleven rows), a runtime-binding grant (`:291`), the
  admission guard's grants (`native_admission_release.py:397–407`) and a default grant to the
  writer role in the helpers that bind task calls (`semantic/native_authoring.py:165, 183`).
- **Table read grants.** The model's `ph:read_roles` annotation is `'[]'` on all 84 relations
  that carry it, so the annotation only ever denies. The grants that exist come from
  `DEFAULT_READ_ROLES`, applied when the annotation is absent (`alembic_privileges.py:74–75`).
  Table admission writes the same four roles again as a JSON string
  (`native_admission_tables.py:176–184`); the literal equals the constant in content and
  order, so it could be derived, and the sibling module does import the constant
  (`semantic/native_admission_functions.py:6, 149`).
- **Principal restrictions, application schemas and private kernels**
  (`native_admission_principals.py:8–16`), and privilege-name lists passed to
  `has_table_privilege` in four modules (`native_admission_principals.py:88–208`;
  `closure_native.py:102–136`; `native_admission_tables.py:200–203`;
  `alembic_privileges.py:349–354`).

**Consequence.** A new demand-graph relation sits outside the frontier guard unless someone
remembers the list. Admission compares the catalog with a descriptor built from the same
lists, so it detects a deployment that drifted from the lists, not a relation the lists never
named. Several existing relations are not in the guard set (`data_publication_receipt`,
`data_product`, `data_intent_adoption`, `data_attempt_failure`); whether any should be cannot
be decided from the model, which is the point. `data_revocation` is outside it deliberately:
the plan states that revocation is always current. A change to a role or to who may execute a
function is an edit in many Python sites, and the privilege policy that admission enforces has
no model owner.

**Contrary evidence.** Immutability triggers read the declared class. Protocol function grants
derive from declared purposes. The role constants are centralized for privileges and host
bootstrap, and privilege admission compares the complete ACL over `PURPOSE_ROLES`. Table read
roles have a modelled slot, even though it is used only to deny. Installed ownership and
privileges are verified independently on PostgreSQL.

**Footprint.** Established for the structure. That a relation is wrongly unguarded today is a
hypothesis for the semantics owner. The role-name count is a search count; it includes
comments and grant statements that would remain literal under any design.

**Lead (not a selected remedy).** The shared-stream membership could be read today from
`relation.info["immutability"]`, as the immutability triggers a few lines above it already do.
This shows that part of the condition for closing this finding can be met by connecting an
existing declaration; the frontier guard and the role names need a declaration that does not
exist yet.

<a id="publication-and-retry-strengths"></a>

## Strengths to preserve

- Physical structure is generated from the annotated model. Forward authoring compares the
  model metadata through Alembic, with a CHECK plugin that compares bound expressions and an
  index plugin that covers collation, predicate, method and included columns
  (`semantic/native_authoring.py:21–24, 789`; `semantic/alembic_checks.py:1–5`;
  `semantic/alembic_indexes.py:1–12`); admission adds native table and reader catalog checks
  (`semantic/native_admission_tables.py:1–7, 90, 252`).
- The admission kernel and the privilege comparison hold no statement text: they are typed
  selects over lightweight catalog relations (`semantic/native_catalog.py`;
  `semantic/native_admission_release.py`; the three `native_admission_*` modules).
- The wire boundary validates once on each side: the generated definer wrapper validates the
  request against its schema, and the client refuses a different contract digest
  (`semantic/data_operation_storage.py:822, 1120`). This realizes PE-F04.
- Restricted principals resolve frozen expectations from native body fingerprints, not from
  the checkout head (`semantic/execution_admission.py:55–59, 120–170`).
- PDF byte streams are content-addressed and verified once per content key, with each part's
  hash enforced by a check constraint (`model/semantic/physical.yaml`, the shared-stream
  relations near `:1757–1776`).
- On the trust scope, only revocation takes an exclusive lock, and every other lock on that
  relation is shared (re-located by search on 2026-11-18 at `d78c98765`; not re-read).
- Task failures have a declared lifecycle and an immutable failure record keyed by the exact
  attempt (`model/semantic/data-operation-native.yaml:5–13`;
  `model/semantic/data-operation-physical.yaml:598–617`;
  `semantic/data_attempt_release_native.py:300–331, 393–394`), and a running task whose lease
  expired can be claimed again (`semantic/data_claim_native.py:74–79, 200–206`). This is the
  design that replaced the subject of [DA-041](structure-and-invariants.md#da-041).

## Prior identities on this page

<a id="da-029"></a>
<a id="da-030"></a>
<a id="da-031"></a>
<a id="da-032"></a>
<a id="da-063"></a>
<a id="da-067"></a>

Statuses were established on 2026-11-18 at `5139eaba3` by reading the code that replaced each
cited subject. Earlier text is in Git at `fbd3f2a98` and before.

| ID | Status at `5139eaba3` | Note |
|---|---|---|
| DA-029 | Corrected, holds (mechanism changed) | Refusal triggers for the `intrinsic`, `immutable` and `deployment` classes are generated from `ph:immutability` (`semantic/target_installation.py:351–369`). The shared-stream relations are still named by hand (DA-074). The trust-in-definer premise is unchanged and bears on [DA-033](execution-fit.md#da-033). Classes with no annotation were not enumerated |
| DA-030 | Corrected, holds | Explicit per-purpose credentials and a native principal check (`semantic/closure_native.py:172–187`) |
| DA-031 | Corrected, holds, and extended to indexes | Alembic comparison with CHECK and index plugins, plus native table catalog checks; sites under the strengths above |
| DA-032 | Partly corrected | Results record `native_kernel_digest`, `validating_kernel_digest` and `kernel_digest` (`model/semantic/data-operation-physical.yaml:22, 484, 632`), and forward bases are frozen (`semantic/migration_chain.py:19–26`). There is still no per-result deployment attribution, and whether one is needed remains open. The digest's breadth is [DA-068](execution-fit.md#da-068). A related fact from the generator lane: each frozen revision calls the live `admit_native` and `admit_privileges` verifiers, and `semantic/alembic_privileges.py` changed in the range (`4760982d8`, `9364a5b88`), so replaying revisions N2 to N13 runs a different privilege verifier than at their freeze. These are verifiers, not effects; the effects come from frozen bytes |
| DA-063 | Corrected, holds | The expectation is selected by the acquired revision, or by body fingerprint for restricted principals (`semantic/execution_admission.py:55–59, 120–170`); deployment passes the actual revision (`schema/model_deployment.py:843, 879`) |
| DA-067 | Corrected, holds | Projection analysis compiles the captured physical sources, and its source identity includes the recipe digests, the captured physical id, the LinkML types digest, the compiler and the runtime (`semantic/projection_analysis_products.py:119–190`); it does not compare against an installed profile |
