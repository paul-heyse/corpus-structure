# Native integrity

**Interface-checked by source inspection.** The page was read as a whole on 2026-11-17 at
source `fbd3f2a98` ([baseline and limits](README.md#baseline)). DA-074 was re-read on
2026-11-18 at source `d78c98765` ([refresh](README.md#refresh-2026-11-18)); the strengths below
were re-located where a line is given with that date, and the earlier-identity table keeps its
2026-11-17 date. Source paths omit `python/corpus-structure/src/corpus_structure/`; `sql/`
means `semantic/sql/`. No catalog was read and no database command was run; statements about
deployed roles or installed objects are about source.

<a id="da-074"></a>

## DA-074 — Native authorization and guard membership are code lists outside the declaration

**Refresh, 2026-11-18, source `d78c98765`.** Stands. Membership is unchanged; no commit in
`1afa63f88..d78c98765` changed which relations or roles are listed, and the rendering changed
again (`30bf7ec6c`, `455405a8d`, `4f38ddead`). Two things are new in the footprint. First, the
generator layer was read as new scope and shows how widely roles are held in code: role names
occur 176 times across 39 modules (literals, constants, comments and SQL strings), and every `ph:read_roles` annotation in
the model is the empty list. Second, one of the listed memberships turns out to have a
declaration that nothing reads: the model marks exactly the two shared-stream relations as
`ph:immutability: pending-content`.

**FP-01, FP-04/A2; DP-01, DP-02, DP-03.**

The physical model declares tables, columns, keys, checks, indexes and an immutability class
per relation, and immutability and archive triggers are derived from those classes
(`semantic/data_operation_storage.py:1925–1935`; `semantic/target_installation.py:334–347`).
The protocol declares purposes for public operations, and the execute grants of protocol
functions are derived from them (`data_operation_storage.py:1885–1895`). The following are
held only as literals:

- **Frontier guard.** Which relations are covered by the guard that refuses support and
  frontier writes in the same transaction after a demand read was acquired is a hand tuple of
  twelve table names (`data_operation_storage.py:1936–1949`), and the trigger is a concatenated
  `CREATE TRIGGER` string (`:1950–1960`). All sixteen candidate relations carry the same
  `ph:immutability: intrinsic` (search, 2026-11-18), so no declared attribute separates the
  guarded relations from the unguarded ones.
- **Shared-stream triggers.** Chosen by relation name
  (`semantic/target_installation.py:350`). The model already declares exactly these two
  relations, and only these two, as `ph:immutability: pending-content`
  (`model/semantic/physical.yaml:1757, 1776`), and that value is carried into the compiled
  relation's `info`; no Python code reads it (search, 2026-11-18).
- **Role names and the purpose-to-role map.** The roles are defined once as constants
  (`semantic/alembic_privileges.py:25–33`) and reused by host bootstrap, and then written again
  in generators: 176 occurrences of role names across 39 modules, counting literals,
  constants, comments and SQL strings (search, 2026-11-18), with none in the model. The map from a protocol purpose to a role is a literal dictionary
  inside the grant loop (`data_operation_storage.py:1887–1893`).
- **Execute grants for non-protocol functions.** A chain of comparisons on function names
  (`data_operation_storage.py:1896–1914`), a table of `(file, schema, name, roles)` entries
  (`target_installation.py:209–231`), a runtime-binding grant (`:266–277`), a default grant to
  the writer role in the helper that binds task calls (`semantic/native_authoring.py:177`),
  and grant statements inside the hand-written admission body (`sql/admission.sql:182–186`).
- **Table read grants.** The model's `ph:read_roles` annotation is `'[]'` on all 84 relations
  that carry it (search, 2026-11-18), so the annotation only ever denies. The grants that
  exist come from `DEFAULT_READ_ROLES`, applied when the annotation is absent
  (`alembic_privileges.py:74–75`), and the same four roles are written again in the admission
  body (`sql/admission.sql:148`).
- **Role sets and prohibited memberships** in the admission body
  (`sql/admission.sql:130, 162–178`), which also finds the point where generated comparisons
  are spliced in by the literal text of a role name (`semantic/native_admission.py:412–416`,
  as reported by the generator lane).

**Consequence.** A new demand-graph relation sits outside the frontier guard unless someone
remembers the list. Admission compares the catalog with a descriptor built from the same
lists, so it detects a deployment that drifted from the lists, not a relation the lists never
named. Several existing relations are not in the guard set (`data_publication_receipt`,
`data_product`, `data_intent_adoption`, `data_attempt_failure`); whether any should be cannot
be decided from the model, which is the point. `data_revocation` is outside it deliberately:
the plan states that revocation is always current. A change to a role or to who may execute a
function is an edit in many Python and SQL sites, and the privilege policy that admission
enforces has no model owner.

**Contrary evidence.** Protocol function grants do derive from declared purposes. The role
constants are centralized for privileges and host bootstrap. Table read roles have a modelled
slot, even though it is used only to deny. Installed ownership and privileges are verified
independently on PostgreSQL.

**Footprint.** Established for the structure. That a relation is wrongly unguarded today is a
hypothesis for the semantics owner. The count of role-name occurrences is a search count; it
includes comments and grant statements that would remain literal under any design. Much of
the SQL that holds these names is hand-written PostgreSQL whose conversion is scheduled and
open ([DA-084](boundaries-and-composition.md#da-084)).

**Lead (not a selected remedy).** The shared-stream membership could be read today from
`relation.info["immutability"]`. This shows that part of the condition for closing this
finding can be met by connecting an existing declaration; the frontier guard and the role
names need a declaration that does not exist yet.

<a id="publication-and-retry-strengths"></a>

## Strengths to preserve

- Physical structure is generated from the annotated model, and index definitions enter the
  admission descriptor and are compared (`semantic/native_admission.py:250–258`, re-located
  2026-11-18).
- The wire boundary validates once on each side: the generated definer wrapper validates the
  request against its schema and the client refuses a different contract digest
  (`data_operation_storage.py:814–862, 1111–1113`, re-located 2026-11-18). This realizes PE-F04.
- Restricted principals resolve frozen expectations from native body fingerprints, not from
  the checkout head (`semantic/execution_admission.py:122–186`).
- PDF byte streams are content-addressed and verified once per content key, with each part's
  hash enforced by a check constraint (`model/semantic/physical.yaml`, the shared-stream
  relations near `:1757–1776`).
- On the trust scope, only revocation takes an exclusive lock: `revoke_data_support` locks
  `ops.data_trust_scope` for update and advances the epoch
  (`semantic/demand_result_native.py:403–413`), and every other lock on that relation is
  shared (`semantic/demand_result_native.py:230`; `semantic/data_read_boundary_native.py:126`;
  `semantic/demand_registration_native.py:824`; `semantic/request_attachment_native.py:1866`;
  `semantic/support_trust_native.py:180`). Re-located 2026-11-18, by search.
- Immutability and archive triggers, physical value sets and protocol function grants are
  derived from declarations ([map](domain-model-map.md#strengths)).

## Prior identities on this page

<a id="da-029"></a>
<a id="da-030"></a>
<a id="da-031"></a>
<a id="da-032"></a>
<a id="da-063"></a>
<a id="da-067"></a>

Earlier text is in Git at `fbd3f2a98`.

| ID | Status at `fbd3f2a98` | Note |
|---|---|---|
| DA-029 | Changed footprint | Immutability now derives from the declared class. The trust-in-definer premise is unchanged and bears on [DA-033](execution-fit.md#da-033) |
| DA-030 | Correction stands | Principal checks at `sql/admission.sql:166–183`; caller fences at `sql/closure.sql:44–50` |
| DA-031 | Correction stands | Index definitions are in the descriptor and compared |
| DA-032 | Changed footprint, unresolved | Revisions are frozen and digest-checked; receipts record the validating kernel digest per result. Per-result deployment attribution is still not recorded, and whether it is needed remains open. The kernel digest's breadth is [DA-068](execution-fit.md#da-068) |
| DA-063 | Correction stands | `semantic/execution_admission.py:122–186` |
| DA-067 | Not re-examined | Last evidence 2026-11-10 |
