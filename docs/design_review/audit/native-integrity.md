# Native integrity and evolution

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline). Paths below omit
`python/corpus-structure/src/corpus_structure/`; rev means `python/corpus-structure/semantic_alembic/versions/`.
No live catalog, ACL, mutation-refusal or migration qualification was run.

<a id="da-063"></a>

## DA-063 — Native admission checks the checkout head instead of the bound target revision

**Implemented source inspected, 2026-11-08.** FP-01/02/04, A1/A2,
DP-01/04/08/19/21, G1/G6/G7. Registration installs a frozen successor
wrapper and its products in the checkout. This step has separate authority
from migration of a bound database. The archive fence nevertheless reads
the expected descriptor body from the unique installed checkout head, with
a cache keyed by the migration directory stamp. It compares that body to
the acquired database without using the database's revision to select the
expectation (`schema/model_deployment.py:334–376`;
`semantic/execution_admission.py:83–119,163–263`).

When a registered successor changes the descriptor, an otherwise matching
older target can fail archive verification solely because registration
changed the checkout. Exact candidate deploy also commits the bound
migration before archive verification. An exact registered candidate behind
the installed head can therefore reach its migration revision and still
refuse archive and admission at the head-based fence
(`schema/model_deployment.py:383–419,480–526`;
`semantic/releases.py:409–426`). The frozen migration, acquired target,
predecessor, role and descriptor-integrity fences are real. The mismatch is
which revision supplies the trusted descriptor for the acquired target.
This is separate from [DA-032](#da-032), which concerns whether an individual
served result needs more deployment attribution.

<a id="da-067"></a>

## DA-067 — Projection analysis can change under the same release identity

**Implemented source inspected, 2026-11-08.** FP-01/02/04, DP-08/09/18/21,
G1/G4/G6. Preparation hashes the retained physical sources but compares
their ID with the installed physical profile. A mismatch emits an empty
analysis with an explicit unknown. A match analyzes the projections using
installed metadata. The cache and release manifest include the retained
dependencies and qualified analysis-library versions. The installed
physical profile is absent from those determinants
(`semantic/projection_analysis_products.py:105–188`;
`semantic/prepare.py:525–550,820–836,1137–1149`;
`semantic/determinants.py:41–68`).

An exact model preview can prepare proposed physical sources while the old
profile is installed. The next candidate invocation can prepare the same
sources after apply, with the new profile installed. The analysis artifact
can change even though the candidate compares equal to the reviewed
release ID and manifest digest (`cli/model.py:699–708,874–884`).
Ordinary archived reads use retained analysis bytes. This finding concerns
rederivation and the scope of exact preview, including full verification
that reprepares archived sources (`semantic/projection_analysis_products.py:54–70`;
`semantic/releases.py:557–579`). No two-process preview/apply experiment
was run during this audit.

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
M1 qualification receipts retain their own source, dates and scope.

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

## Current runtime and progressive publication custody

**Source-inspected 2026-11-05.** `semantic/sql/runtime_bindings.sql:2–100` authenticates
canonical runtime/archive bytes, semantic inputs and same-release run binding; registration
refuses conflicting bytes. `semantic/runtime_binding_store.py:34–79` reads the producing runtime,
using explicit historical archive fallback. This preserves the distinction between logical model
identity and exact executable provenance without backfilling current runtime over old results.

Local semantic eligibility binds protected grade/digest, selected origins, contribution operation
and actual source (`semantic/sql/record_publication.sql:965–1041`). Structural publication
revalidates selected final-cut origin, original source custody, independent passes, policy and
semantic participant citations (`semantic/sql/structural_publication.sql:77–176`), then requires
staged assertions to equal the exact native eligible set (`:192–207`). Dossier input membership
alone cannot establish predecessor-output support. No current integrity violation was established
in these inspected paths. This does not attest actual deployed ACLs, catalogs or execution.
