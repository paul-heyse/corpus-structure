# Native integrity

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline and limits](README.md#baseline)). Source paths omit
`python/corpus-structure/src/corpus_structure/`; `sql/` means `semantic/sql/`. No catalog was
read and no database command was run; statements about deployed roles or installed objects are
about source.

<a id="da-074"></a>

## DA-074 — Native authorization and guard membership are code lists outside the declaration

**Delta, 2026-11-17, source `1afa63f88`.** Stands. Grant and catalog statements are now rendered by typed builders (`30bf7ec6c`, `e2b291df5`); membership is still held in code lists (`semantic/data_operation_storage.py:1755–1768`; `semantic/target_installation.py:186–255, 332–351`; `semantic/alembic_privileges.py:25–33`) ([delta](README.md#delta-1afa63f88)).

**FP-04/A2; DP-01, DP-02, DP-03.**

The physical model declares tables, columns, keys, checks, indexes, read roles and an
immutability class per relation, and immutability triggers are derived from that class and
checked (`semantic/data_operation_storage.py:1551–1576`; `semantic/target_installation.py:314–331`).
The protocol declares purposes for public operations. The following are held only as literals:

- which relations are covered by the guard that refuses support and frontier writes in the same
  transaction after a demand read was acquired: a hand list of twelve tables
  (`data_operation_storage.py:1679–1703`);
- which relations get shared-stream mutation triggers, chosen by name
  (`target_installation.py:332–351`);
- EXECUTE grants for non-protocol functions (`target_installation.py:186–255`;
  `data_operation_storage.py:1629–1658`) and GRANT text inside `sql/admission.sql:187–191`;
- role sets, prohibited memberships and the signatures of earlier private kernels in the
  admission body (`sql/admission.sql:152, 166–183`).

**Consequence.** A new demand-graph relation sits outside the frontier guard unless someone
remembers the list. Admission compares the catalog with a descriptor built from the same
lists, so it detects a deployment that drifted from the lists, not a relation the lists never
named. Several existing relations are not in the guard set (`data_publication_receipt`,
`data_product*`, `data_intent_adoption`, `data_attempt_failure`); whether any should be cannot
be decided from the model, which is the point. `data_revocation` is outside it deliberately:
the plan states that revocation is always current.

**Footprint.** Established for the structure. That a relation is wrongly unguarded today is a
hypothesis for the semantics owner.

<a id="publication-and-retry-strengths"></a>

## Strengths to preserve

- Physical structure is generated from the annotated model, and index definitions enter the
  admission descriptor and are compared (`semantic/native_admission.py:118–125`;
  `sql/admission.sql:160–165`).
- The wire boundary validates once on each side: the definer wrapper validates the request and
  stamps a contract digest; the client validates the result and refuses a different digest
  (`data_operation_storage.py:595–610, 824–858`). This realizes PE-F04.
- Restricted principals resolve frozen expectations from native body fingerprints, not from
  the checkout head (`semantic/execution_admission.py:122–186`).
- PDF byte streams are content-addressed and verified once per content key, with each part's
  hash enforced by a check constraint (`model/semantic/physical.yaml:1812–1846`).
- Settlement takes shared locks; only revocation takes exclusive ones
  (`sql/data_operations.sql:189, 209, 1919`).

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
