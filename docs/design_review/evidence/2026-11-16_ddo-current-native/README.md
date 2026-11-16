# DDO current native root and development adoption

**In progress · 2026-11-16.** The [DDO coordinator](../../../plans/declared-data-operations_2026-11-12.md#current-execution-boundary--2026-11-16)
owns readiness and disposition. [ADR-0118](../../../adr/0118-current-target-installation.md) selects
the single current97-relation basis and normal native-only lifecycle. This folder retains its
actual request, stage identity, reviewed artifacts and execution outcomes; it does not establish
application/provider qualification by preparing or installing infrastructure.

## Current boundary

The existing `corpus_structure_dev` remains PostgreSQL18.7 on dedicated5434, database OID25921445,
system7701811359771751232, installed `semantic_bep_located_v2`; maintenance status reacquired this
identity on2026-11-16. No reset, rename, persistent native deployment, activation or data conversion
has occurred. Current checkout has no registered native root. Historical frozen files remain
unchanged and are not a selectable current install route. The unregistered
[v10 preparation](../2026-11-15_ddo-v10-native/README.md) is superseded.

An explicitly owned empty `corpus_structure_ddo_stage` was created for current root authoring and
readiness before development adoption. Creation-only installation preserves its actual
acknowledged token/OID/owner and target identity. Existing creation ownership, model preview,
rollback-only candidate, inspection, registration and deployment mechanisms supply custody.
No application release, capsule or admission claim is fabricated for native-only installation.
The native request is prepared after final shared source integration; source changes require a
fresh reviewed preview. Actual commands and outcomes are recorded below as they settle.

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

## Acceptance still required

- Final-source current root candidate, reviewed exact physical/native/ACL delta, registration and
  normal installation, including canonical guarded-path catalog/type comparisons.
- Actual current source/runtime/archive/application consumers and their private/ordinary
  visibility, refusal, concurrency and scientific controls. Controlled inference establishes only
  its stated execution, not provider accuracy or independent scientific standing.
- Recovery and fencing/draining before changing the development target; historical generated
  bytes may remain inert. Optional faithful imports must preserve actual meaning and custody,
  otherwise regenerate/reassess without restoring legacy code.
- The coordinator's required functional/provider/fault/nonfunctional DDO-12 union. A fresh install,
  selected pass or accepted architectural decision does not close these obligations.
