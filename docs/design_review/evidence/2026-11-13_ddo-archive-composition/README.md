# Typed archive and declared input composition

**Registered through v5; execution paused and native qualification incomplete · 2026-11-13.** This normal forward successor follows
`semantic_ddo_original_v1`, retaining complete original-source model content while replacing
the oversized whole-archive JSONB transport. It also integrates concrete nominal input
refinement, owned nested subject paths and genuine runless PDF staging foundations.
[ADR-0097](../../../adr/0097-ddo-native-composition.md) and
[ADR-0098](../../../adr/0098-typed-release-archive.md) own the decisions; the
[DDO coordinator](../../../plans/declared-data-operations_2026-11-12.md) owns execution.

The acquired persistent development database remains `semantic_bep_located_v2`,
corpus_structure_dev/OID25921445, PostgreSQL18/corpus port5434,
system7701811359771751232. Candidate authoring replays the registered pending chain
inside a rollback-only transaction. No persistent deployment or activation is performed.

Source integration and candidate registration are not native qualification. The original
failed receipts remain retained. The new request explicitly retires the old JSONB publication
signature; generated API changes follow normal preview/apply rather than manual editing.

## Undeployed candidate supersession · 2026-11-13

Candidate `18856ef6b8064c9c8da21c67c38d0ca1` rollback-only authoring and registration
`3187328c634147a3ad2855ecd17b481d` passed for their acquired snapshot. Native selection
`0ea3cb55fc83468891178af7ce30f119` then **failed**, 2 passed/83 setup failures: clean
legacy migration replay retained the migration operator's explicit EXECUTE grant from frozen
Python wrappers 0031–0033, which the SQL-only predecessor collector had omitted. No native
claim or DDO package qualification follows from that selection.

Candidate `35b20f9ffa464faaab9991cda40317e6` exposed an ACL mismatch. The initial ACL-drift diagnosis was incorrect: that explicit grant has an authored frozen
source. The grant was briefly revoked during diagnosis, then restored with `GRANT EXECUTE ON FUNCTION
sem.publish_release_archive(jsonb) TO paul`; no effective superuser capability was changed.
The collector must capture the wrapper's grant metadata and distinguish the migration
operator from the semantic namespace owner. Native before-state enforcement stays strict.

The never-deployed, invalid archive-v1 registration is retired from the active Alembic search
path. Its exact four files remain unchanged under `raw/rejected_archive_v1/`, with hashes in
`sha256.json`; Git and original managed receipts also preserve their provenance. No database
reached that revision. Replacement authoring targets `semantic_ddo_archive_v2` directly after
`semantic_ddo_original_v1`, through normal preview/candidate/registration. This supersession
changes checkout candidate selection, not persistent schema or retained source/reference data.


## Corrected predecessor acquisition

**Tested · 2026-11-13.** The predecessor collector now replays the frozen Python wrappers’
schema-wide grants into its acquired metadata. Wrapper-affected before-state owners and ACLs
retain the literal acquired migration operator, distinct from namespace-owner bindings. Runtime
catalog comparison still checks exact owner and ACL; no writer-purpose rebinding is introduced.
The clean original-v1 predecessor and metadata controls **passed 7/7**,
`947ec01d14064464ac4dc1b23b9932de` (root), replacing the earlier failed before-state diagnostic.
The replacement v2 preview **passed**, `e3eabeddb45545fab3c3984114030a97`, with no
generated path changes. Rollback-only candidate **passed**,
`cd4414ade9db47cabd635234b61714fa`; registration **passed**,
`e27fd20b3c1e4407a61d875f2c5f7dc8`, writing the exact four
`semantic_ddo_archive_v2` files after `semantic_ddo_original_v1`. The bound release is
`release:612a15fb97da0414263b1d7ad9b0aa665d69e93f8731b52e742cf71fbac1cf48`.
`uv run ci db status --maintenance --json` confirmed the persistent revision remains
`semantic_bep_located_v2`, with checkout head `semantic_ddo_archive_v2`. Native consumer
qualification is running in isolated databases; registration does not establish those results.


## Runtime guard correction

Native selection `bc8830741008498da5f364caec09166f` **failed** at actual demand
registration: PostgreSQL grouped an unparenthesized right JSON extraction after containment,
attempting `boolean -> text`. The campaign was interrupted after the common failure was
established (109 required, 2 passed, 20 failed; remaining nodes unrun). Its complete receipt
is retained. This is a runtime SQL defect, separate from the repaired predecessor metadata.

The source guard now explicitly groups containment and alternative membership. Seven real
PostgreSQL controls against the production predicate **passed**,
`d637175a193b4c9595392ebf8c90caac`. Normal `correction.yaml` authoring follows v2 with
`semantic_ddo_archive_v3`; v2's frozen bytes remain unchanged. V2 applies cleanly and its faulty
query is not invoked during migration replay. No persistent database reached v2.


The correction preview **passed**, `54ce24c7cdab4af3b40f2eb5cc455215`; rollback-only
candidate **passed**, `935373f39ad74d269ff9f2624ed73345`; registration **passed**,
`bf573b6244724f25bb70175ee8c02d4f`. This successor changes three native functions and
no physical table operation. The acquired database stayed at `semantic_bep_located_v2`.
The corrected native journeys remain open until actual runtime checks pass.


## Completion retention and embedded SQL checking

The v3 five-journey run **failed 5/5**, `7aac41db19834af5858691bb3182810a`. Four
reached completion retention and exposed a second deferred SQL precedence error: key subtraction
bound before JSON extraction. The fifth was an independently corrected fixture shadowing of
canonical integer/string kinds; production metadata stayed unchanged, and actual production
preparation **passed**, `bdaf84ab19744525a142d7af8679b2a2`. The source evidence guard now
extracts JSON before subtracting receipt fields. Fourteen real PostgreSQL controls across both
production guards **passed**, `9ee8393140ba470383327c1e0443927f`.

The available plpgsql_check extension SQL version 2.10 (system package 2.10.16) supplies native
embedded SQL type analysis. Final DDO candidate normalization checks the authoritative desired
function inventory after all dependencies are installed, inside its existing rollback-only
savepoint. It rejects checker errors, respects existing checker schemas and native ACLs, disables
in-comment overrides and leaves frozen predecessor interpretation alone. Seven actual PostgreSQL
controls **passed**, `f99afd352f5b4e3091822a4a10ab546b`. Static coverage remains bounded for
dynamic SQL and unknown records; functional qualification remains required. No persistent extension
installation is added. `publication-correction.yaml` authors normal archive-v4 after unchanged v3.


The first v4 candidate `f8dc3b2f01214f6ca1b2d531a6ffc82c` **refused before registration**,
with established rollback cleanup: active checking found an ambiguous PL/pgSQL `reference`
variable versus SQL support aliases in `ddo_validate_binding`. The local population variable is
now qualified by a distinct name. Investigation also corrected episode-ID aggregates to project
only computational references while preserving the full original/computational support list and
both authenticity checks. Five real PL/pgSQL controls **passed**,
`a364c4c2afd24f8a8e365817c2817c3b`, including mixed origins and forged-original refusal.
Checker diagnostics now collect bounded errors across selected functions; nine controls **passed**,
`d0238fe821a3401db105b74f93d49873`. V4 remains unregistered until the refreshed candidate passes.


The current context boundary also distinguishes an explicit JSON-null scope from an omitted
SQL-NULL projection parameter. It uses SQLAlchemy's `JSON.NULL` marker in the existing exact
JSONB type and comparisons; semantic body/parameter null meanings are unchanged. Three genuine
PostgreSQL binding/comparison controls and the combined binding selection **passed 34/34**,
`6799cdf1069f4993a78e0a1120997493`. Original-source predicate coverage is a bounded native
parameter/predicate control: current authentic original-source builders emit object scopes, and
no null original admission was fabricated. A genuine computational null-root native journey is
part of the pending v4 union.


## Accepted v4 authoring and current qualification

Refreshed preview `ad0a9ebb043b4e2aa6f034819c87956b`, rollback-only candidate
`b725cb7122424cdc8bc6bb0e458f3849` and registration `aa6793ea4ce64363b768d699fe0d2180`
**passed**. This checked successor after v3 changes four native functions and no ordinary
physical operation. Critical native/production controls **passed 7/7** (six native journeys and
one production-preparation control),
`78a4a3930af741adb9f2e40f51043418`, including authentic publication/replay, actual production
callable execution/resume, closed discovery fan-in and exact fractional/null context binding.
The complete native union remains open. `ci db status --maintenance` confirmed the working
database remains at `semantic_bep_located_v2` with checkout head v4. Read-only PostgreSQL
extension metadata also confirmed plpgsql_check is absent after candidate rollback; no deployment
or activation occurred.

## V4 full qualification and forward integration correction

The full native/protocol/adjacent-control union **failed**, 129 passed / 13 failed,
`0aaa980a87bc415f8c6c682ebacd2214`. Its retained receipt preserves every selected identity.
The failures exposed trust-snapshot comparison across multiple original roots, a PDF-stage
guard's ambiguous output-column name, obsolete product uniqueness missing analyzed scope,
and retired-attempt attribution inconsistent with the task fence. Additional cases supplied
invalid typed wire inputs or an empty population excluded by their fixture's contract; these
must reach the intended native checks using valid declared inputs.

The source corrections are authored as an ordinary successor after unchanged frozen v4.
No failed migration is rewritten, and no working-database deployment is performed. The final
candidate also actively checks the required PDF-stage ownership guard beside the declared DDO
function inventory. Qualification and package acceptance remain open until the correction's
actual native journeys pass.

## Accepted v5 authoring

Preview `f85b42104df544b68c292fc3e9e0c9b7`, rollback-only candidate
`fa5eaba6351647c581bfec47520baac5` and registration `140d3537f7014c2786f42815cb9ba27e`
**passed**, bound to release
`release:845dae4d93926abb6224d28e154698a1ac717a17b7b72a8e7e123c5fcb0e520c`.
The fourteen native transitions contain the trust-meaning helper, affected read/attach/population
functions, retired-attempt release/fence guard, PDF ownership guard and derived descriptors.
Four PDF companion readers refresh only their declared projection IDs. Owners and ACLs remain
unchanged except the newly created private helper's explicit publisher ownership.

The four ordinary statements remove the obsolete context-incomplete product uniqueness
constraint, switch to the publisher, register the new physical contract and restore the migration
role. No table, column or product is dropped. The qualified product ID primary key remains the
canonical uniqueness authority. The four v5 artifacts were registered unchanged and root
`just turn-end` made no source edits afterwards.

Nineteen real PostgreSQL trust-snapshot controls **passed**,
`cdbe882e2f2547c9873dd82ab6ea6b27`; missing/explicit numeric zero are equivalent, while null,
string, bool, negative/fractional epochs refuse and positive revocation stays exact. The Python
projection now consumes the native reader's validated canonical pins rather than imposing a
second dictionary equality. The actual full-read/multi-root publication/revocation case belongs
to final v5 qualification. PDF guard checking/restoration **passed**, `b452c14cf5cd439f8f8e4b3afe7b1720`;
ten repaired planner/population/graph/purpose controls **passed**, `8dc2c54a9a8f44cfa38f40302d5eec15`.
The initial PDF test's valid drift refusal remains retained separately.

The final 51-file required scope ran as `2a1fdebfd77749378ce7d4598cba5d68` against
source `561634814`. The operator requested cancellation and a pause. SIGINT to the owned pytest
controller stopped the run; its supervisor drained and settled custody. The managed outcome is
**failed due to interruption**: 651 selected, 452 passed, 195 not_run and 4 incomplete.
The [retained receipt](../2026-11-13_cli-2a1fdebfd77749378ce7d4598cba5d68/README.md)
keeps exact partial coverage. No replacement is running and no full qualification is claimed.
Repository checks **passed**, `ef31917fa4ae44cca9aad5b7ae96d0f1`; later documentation changes
receive their own publication check. Qualification and finding/package closure remain open in
the coordinator. On the operator's resumption, exact retry and coverage reconciliation start
from this held invocation; changes to source/context require affected reassessment.
