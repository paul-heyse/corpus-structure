# Native integrity and evolution

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline). Paths below omit
`python/corpus-structure/src/corpus_structure/`; rev means `python/corpus-structure/semantic_alembic/versions/`.
No live catalog, ACL, mutation-refusal or migration qualification was run.

<a id="da-029"></a>

## DA-029 — Earlier uneven-immutability diagnosis removed against restricted-runtime contract

**Source-inspected correction; FP-05, DP-03/19/21, CI-01/11/12.** The previous blanket diagnosis
is removed. `rev/semantic_0031_kernels.sql:454–510` protects semantic content and intrinsic release
rows from mutation. `semantic/sql/closure.sql:20–55` publishes/finalizes the archive atomically;
`semantic/source_view_native.py:159–207` derives additional immutable guards, including M1 rows.

The inspected descriptor has observation INSERT and reference-evaluation scientific-decision
INSERT guards, without equivalent mutation-refusal guards for established reference/pass/frame/grade
families. Observation structure lacks an immutable annotation (`model/semantic/physical.yaml:1320–1386`);
evaluator tables are publisher-owned (`rev/semantic_0028_reference.sql:7–9,25–43`). A defect in a
privileged publisher body would have less preventive protection than admitted semantic content.
Ordinary principals have restricted writes, and no current public mutation route or corrupt record
was demonstrated. ADR-0025:45–55 and ADR-0031:42–47 expressly trust complete definer operations under a
NOLOGIN publisher. Admission denies runtime publisher/owner membership and direct evaluator writes
(admission.sql:135–152). No mutating callable or privilege bypass was demonstrated. Additional
mutation triggers would be a defense-in-depth hypothesis, not an established missing requirement;
absence of that second layer does not sustain the old diagnosis.

<a id="da-030"></a>

## DA-030 — Release-lifecycle and purpose-principal diagnosis corrected

`semantic/runtime.py:21–65,84–93` explicitly resolves purpose credentials, checks common target
and verifies the purpose principal. Protected archive/activation and caller fences are present
(`semantic/sql/closure.sql:20–94,133–158,444–460`); admission checks prohibited role membership,
TEMP and direct writes (`semantic/sql/admission.sql:149–152`). The explicit owner maintenance path
is not application impersonation. Source correction does not qualify actual provisioned roles;
forward101 fitting enforcement remains separately under M1 qualification.

<a id="da-031"></a>

## DA-031 — Name-only physical-parity diagnosis corrected

Ordinary forward authoring compares model-derived metadata through Alembic
(`semantic/native_candidate.py:1193–1287`), normalizes authored CHECK bodies using temporary
relations rather than enrolling live drift (`:1085–1136`), and freezes them. Admission compares
CHECK expressions and unexpected checks (`semantic/sql/admission.sql:8–18`), plus columns,
nullability/defaults/PK/FK vectors, owners, RLS and ACLs (`:110–124`). Shared metadata supplies
relation descriptors (`semantic/native_products.py:88–164`). This contradicts the earlier
hand-maintained/name-only premise. Not every index/unique property was independently assessed;
that omission alone is not a newly established admission defect.

<a id="da-032"></a>

## DA-032 — Forward-evolution diagnosis corrected; result attribution question unresolved

`semantic/native_candidate.py:789–827,1023–1039` binds frozen predecessors and their bytes.
`semantic/alembic_native.py:90–146` refuses stale before-state, installs statements/ACLs and compares
resulting catalogs. Deployment admission records exact descriptor content under its digest
(`semantic/native_products.py:331–342`; physical.yaml:58–71). Earlier in-place edits remain dated
historical evidence, not proof that the current route edits frozen revisions.

Result bindings carry release/realization (`semantic/query.py:387–397`), not a per-result
admitting deployment. Whether that additional attribution is required beyond the immutable release
and deployment history remains unresolved; the missing field alone is not diagnosed as a defect.

## Publication and retry strengths

`semantic/publication.py:718–873` owns SERIALIZABLE publication, rollback settlement and immutable
batch identity. Commit uncertainty uses receipt lookup; cancellation suppresses replay.
`semantic/sql/derived_publication.sql:28–43,63–99` checks replay before admitting new effects against
sealed/source-revision fences. `current_operation_guards.sql:19–30` enforces atomic completed-result
visibility. These bound any general claim of incoherent publication. Repeated assurance scope is
examined separately at [DA-033](execution-fit.md#da-033).
