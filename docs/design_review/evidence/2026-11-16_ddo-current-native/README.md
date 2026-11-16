# DDO current native root and development adoption

**In progress · 2026-11-16.** The [DDO coordinator](../../../plans/declared-data-operations_2026-11-12.md#current-execution-boundary--2026-11-16)
owns readiness and disposition. [ADR-0118](../../../adr/0118-current-target-installation.md) selects
the single current97-relation basis and normal native-only lifecycle. This folder retains its
actual request, stage identity, reviewed artifacts and execution outcomes; it does not establish
application/provider qualification by preparing or installing infrastructure.

## Current boundary

The existing `corpus_structure_dev` remains PostgreSQL18.7 on dedicated5434, database OID25921445,
system7701811359771751232, installed `semantic_bep_located_v2`; maintenance status reacquired this
identity on2026-11-16. That development database has had no reset, rename, native deployment,
activation or data conversion. The current root is registered and installed only on the owned stage. Historical frozen files remain
unchanged and are not a selectable current install route. The unregistered
[v10 preparation](../2026-11-15_ddo-v10-native/README.md) is superseded.

An explicitly owned empty `corpus_structure_ddo_stage` was created for current root authoring and
readiness before development adoption. Creation-only installation preserves its actual
acknowledged token/OID/owner and target identity. Existing creation ownership, model preview,
rollback-only candidate, inspection, registration and deployment mechanisms supply custody.
No application release, capsule or admission claim is fabricated for native-only installation.
The native request captures shared source integration; later native source changes require a
fresh reviewed successor. Actual commands and outcomes are recorded below as they settle.

## Empty authoring stage · 2026-11-16

**passed:** `ci db init --creation-only --creation-token … --json`, with the explicit database URL
selecting `corpus_structure_ddo_stage` on dedicated5434. [Creation](stage-creation.json) retains the
acknowledged token and disposal owner; [stdout](stage-creation.stdout.json) records created=true,
revision/head=null and no applied migration. The existing development database is unchanged.

The first `ci db status --maintenance --json` on this empty stage **failed**: it mistook an absent
migration table for denied revision access. The owner now reports `revision_table_present` separately
and still refuses a real present-but-unreadable table. Actual creation/status/refusal control
`b9b682afbd494dd7ae4507f186ec0faf` passed; the repaired command on this actual stage passed with
present=false/readable=false/revision=null/head=null. The
[read-only ownership observation](stage-observation.json) authenticates owner `paul`, actual
OID130661481, the acknowledged ownership stamp and system7701811359771751232. That bounded fallback
used existing `acknowledged_database`, `acquired_target` and `current_revision` while the CLI defect
was repaired. No native/application deployment or adoption is established.

## Rollback-only root preparation · 2026-11-16

**passed:** native-only preview `264a9a24186b4bd9a62645dbf7748bdd`, exact apply
`516cf3eee46246d4a26194d6271c7672` (no source patch), and rollback-only candidate
`c3b3900d559244fd9cc62808bdc37f39` on the owned stage. The candidate contains594 native
and124 ordinary operations, with no application release or admission claim. The
[current request](current-root.yaml) selects an empty current root, never the historical chain.

This first candidate is **superseded before registration**: integration inspection found that the
shared restricted selected-fit reader and older record-fit checks could resolve an adopted
request's current release instead of its immutable producing episode. The correction must retain
original release/runtime/recipe/generation and exact intent request/task/attempt/runtime fences,
including original inputs/support when rechecking the fit. No persistent installation occurred.
A fresh reviewed preview/candidate must capture that correction before registration.

## Registered root and stage installation · 2026-11-16

**passed:** corrected preview `9924b10ed5a84fa486c7717b2d2626be`, exact apply
`df2987139e0e47079d53ae546cfc4fdc`, rollback-only candidate
`f93ca97b64c840c69ccb8b92bfe4be93`, registration `b7f0e7946ccd4867bd10883cc3a41ade`
and deployment `797c62ed148c4527a95861fb23daa274`, using `ci model change` on the explicit stage
URL. Registration committed as `280a73976`; the frozen revision is `semantic_ddo_current_root`.

Candidate operation inspection paged all594 transitions:382 functions,107 triggers,4 views,
97 table privilege normalizations and4 schema privilege normalizations. No PUBLIC ACL transitions
were present. The124 ordinary installation operations create the canonical target. Exact frozen
SQL, state/catalog descriptor and admission bytes are retained under
`python/corpus-structure/target_alembic/versions/semantic_ddo_current_root*`; registered bytes must
remain unchanged. Current root formatting excludes frozen wrappers, as it already excludes the
historical series; lint still checks them.

The normal deploy command applied and verified the installation. A separate actual
`ci db status --maintenance --json` reacquired the same OID130661481/system7701811359771751232,
principal `paul`, readable/present migration table and revision=head=`semantic_ddo_current_root`.
No application release, activation, historical conversion or default development-target change
has occurred. Actual current artifact, contextual, selected annotation and event/record journeys
are executing on isolated native hosts; their qualification is separate from this installation.

## Acceptance still required

- Preserve exact registered root custody and qualify any required native successor discovered by
  actual application consumers; frozen source is never patched in place.
- Actual current source/runtime/archive/application consumers and their private/ordinary
  visibility, refusal, concurrency and scientific controls. Controlled inference establishes only
  its stated execution, not provider accuracy or independent scientific standing.
- Recovery and fencing/draining before changing the development target; historical generated
  bytes may remain inert. Optional faithful imports must preserve actual meaning and custody,
  otherwise regenerate/reassess without restoring legacy code.
- The coordinator's required functional/provider/fault/nonfunctional DDO-12 union. A fresh install,
  selected pass or accepted architectural decision does not close these obligations.
