# Typed archive and declared input composition

**Authoring in progress · 2026-11-13.** This normal forward successor follows
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

## Current authoring repair · 2026-11-13

Native candidate `35b20f9ffa464faaab9991cda40317e6` **failed** with established rollback
cleanup: the retired `sem.publish_release_archive(jsonb)` had an extra explicit EXECUTE
grant to `paul`, absent from its frozen ACL contract. Read-only `psql -p 5434 -d
corpus_structure_dev -X -Atc` catalog inspection found owner/admitter plus that grant;
`pg_roles` confirmed `paul` is a superuser. Restoring the frozen ACL therefore removes
no effective operator capability. `psql -p 5434 -d corpus_structure_dev -X -v
ON_ERROR_STOP=1 -c "REVOKE EXECUTE ON FUNCTION sem.publish_release_archive(jsonb) FROM paul;"`
**passed**. This is a persistent ACL correction, not a schema migration, activation or
retained-data change. Later authoring reacquires the target and predecessor normally.
The failed candidate and earlier successful preview `9b3db3512e1744279d27c71430f1456d`
retain their original source and scope; later native JSON-context corrections need fresh authoring.

## Undeployed candidate supersession · 2026-11-13

Candidate `18856ef6b8064c9c8da21c67c38d0ca1` rollback-only authoring and registration
`3187328c634147a3ad2855ecd17b481d` passed for their acquired snapshot. Native selection
`0ea3cb55fc83468891178af7ce30f119` then **failed**, 2 passed/83 setup failures: clean
legacy migration replay retained the migration operator's explicit EXECUTE grant from frozen
Python wrappers 0031–0033, which the SQL-only predecessor collector had omitted. No native
claim or DDO package qualification follows from that selection.

The earlier ACL-drift diagnosis was incorrect: that explicit grant has an authored frozen
source. The redundant `paul` grant was restored with `GRANT EXECUTE ON FUNCTION
sem.publish_release_archive(jsonb) TO paul`; no effective superuser capability was changed.
The collector must capture the wrapper's grant metadata and distinguish the migration
operator from the semantic namespace owner. Native before-state enforcement stays strict.

The never-deployed, invalid archive-v1 registration is retired from the active Alembic search
path. Its exact four files remain unchanged under `raw/rejected_archive_v1/`, with hashes in
`sha256.json`; Git and original managed receipts also preserve their provenance. No database
reached that revision. Replacement authoring targets `semantic_ddo_archive_v2` directly after
`semantic_ddo_original_v1`, through normal preview/candidate/registration. This supersession
changes checkout candidate selection, not persistent schema or retained source/reference data.
