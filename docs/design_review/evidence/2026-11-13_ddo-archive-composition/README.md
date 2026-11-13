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
