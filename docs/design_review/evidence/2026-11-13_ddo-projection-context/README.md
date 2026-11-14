# Compiled projection and complete-context native successor

**Authoring Tested · 2026-11-13.** Implements the native portion of DDO-CA-05/06/07 under the
[DDO coordinator](../../../plans/declared-data-operations_2026-11-12.md). The coordinator alone
owns finding and package disposition. Source baseline is `94539f712` plus the integrated DDO
implementation; exact captured inputs and artifact hashes belong to the managed receipts.

## Native change and custody

`ops.ddo_impl_close_data_population(jsonb)` now rejects duplicate complete member contexts,
using subject, original source and JSONB analyzed-scope meaning within the authenticated project.
Distinct scopes may share a local subject; equal JSON numbers remain equal contexts.
`sem.require_execution_projection(text)` requires current effective model v3 for target execution.
The native and execution descriptors are regenerated through their existing owners.

Final preview `10a81274757548a084cad38f26fd10da`, rollback-only candidate
`7ccd25c86a534675a5db847dc2d5db27` and registration `7c5d74466b734072bc47ffe8848516b7`
**passed**. The registered successor is `semantic_ddo_projection_v1` after
`semantic_test_pdf_seal_producer`. Inspection found exactly four function-body transitions,
zero ordinary schema operations and unchanged function owners/ACLs. The retained
[operation inventory](raw/native-operations.json) and [SQL view](raw/native-sql.json) identify
those changes. The population and archive guards each have one exact line replacement.

Registration added four new frozen files. The [post-maintenance inspection](raw/registered-candidate.json)
reports registration **verified**, with the predecessor dependency available; their bytes still
match the candidate. Its suggested future action is unavailable because subsequent source-migration
preparation fixes changed the generator identity. This lifecycle staleness does not alter frozen
artifacts or authorize deployment. A future effect must reacquire current bindings.

[Maintenance observation](raw/after-database.json) confirms the persistent database remains
`semantic_bep_located_v2`, database OID `25921445`, PostgreSQL system identifier
`7701811359771751232`, on PostgreSQL 18.7 at port 5434. No deployment, activation or DDO cutover
was performed. Frozen predecessors were not edited.

## Retained preparation attempts

Previews `108fd4f2547a471eb15bf17ab75f21a4`, `940c40d1ea0444cc8c4c76d816c824d3`,
`6b62a7163c954d30ab02facb719620b2`, `111c8c9c1a214a27b453ec3fe146a29a` and
`3c32337e5769454d9e8468e60e36cda3` passed at their captured source states and are superseded
by the final preview above. Candidate `93c6717e21a347e89075a046ea25b1fb` refused a changed
model toolchain before acquiring a database target or authoring native changes. These receipts
remain unchanged. A proposed overlong revision name was shortened before candidate authoring.

## Functional consumer evidence

The initial managed selection `07021252b8464b599428d0d3655957e0` **failed**: 94 selected,
91 passed and three failed. The [retained result](raw/native-initial-result.json) and
[failures](raw/native-initial-failures.json) distinguish one seed-backend teardown/setup race
from two invalid newly authored test inputs. The population recipe requires `Scope{page:integer}`;
null/string scopes and a float meaning tag cannot inhabit that typed container body.

The fixture retains that schema. The numeric-equivalence case now supplies integer context in
the canonical body and explicit `1.0` in the member-header context; native packet authentication
compares their JSONB meaning, and closure still refuses duplicate complete contexts. The invalid
null/string population parameter is removed. Separate existing JSON-null binding/demand controls
retain their actual supported contract; no schema or normalization guard was weakened.

Final focused selection `09ecb5f88e5f476a9ed8bcd226e30829` **passed 10/10** on the final
builtin/port and seed-exit guards. It covers the previously failed scope setup, page1/page2 child
publication, both exact/equal-number duplicate-context cases, actual production source preparation
and publish/resume, and four independent JSON-null controls. The [final result](raw/native-final-result.json)
retains exact scope. The original receipt retains passing native binding, four hydration forms,
publication/conflicting-intent, purpose-principal and support-recovery controls.

The [coverage report](raw/native-coverage.json) deliberately remains **unresolved** against the
original 94-identity inventory: its sole unresolved identity is the removed invalid null/string
population parameter. It also reports source differences. The coordinator owns that explicit
retirement and applicability judgment; successful report delivery is not complete qualification.
Changed source execution is replaced by the final production-source cases; remaining passing
storage/binding controls are not relabelled fresh runs. Both test receipts, the accepted preview
and the registered candidate are held while consumers depend on them.

All selected cases use delivered scenario seeds and named native isolation contracts. The
[final maintenance observation](raw/final-database.json) confirms the persistent database still
has its original revision/OID/system identity. No provider/book/full-series qualification or
production adoption is claimed. The accepted record is `records/ddo.projection-context.json`.
