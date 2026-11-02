# Current-only native forward realization

Date: 2026-11-02. Status: implemented and independently reviewed; final-source author rehearsal passed; freeze pending.

This evidence belongs to the unified-domain-model coordinator's current-only transition.
The current physical model retires 36 obsolete rendition, layered-parsing and aggregate PDF
relations. Released record read shapes are modeled separately and do not own stored DDL.

The harnesses use only the already-owned author database
`cs_sem_pdf68_author_20261101_44132f1db0`, OID `14010645`, owner `paul`, token
`1dbfc2773c354652b64626aaa56eac35`. Every journey checks provenance before replay, owns its
transaction, and rolls back to revision82 and caller `paul`. Frozen83–90 remain unchanged.
No operational corpus intake, other database mutation or database deletion occurs here.

Run scripts from the worktree root using `PYTHONPATH=<worktree>/python/corpus-structure/src:<worktree>/python/corpus-structure/tests uv run --project /home/paul/corpus-structure python <script> <attempt>`.
Executed scripts and failed results remain unchanged. New versions correct the harness rather
than overwriting its history. Raw outputs, including failures, are under `raw/`.

`inspect_author.py` passed rollback-only replay to90 and captured dependencies. That inventory
is an observation for comparing bounded frozen declarations, never desired-state authority.
`candidate_attempt.py` attempts001–008 failed while resolving inventory parsing, frozen function
custody, trigger dependencies/owner/creation privileges and retained ACLs; attempt009 passed.
`compare_predecessor.py` independently isolated the release guards' retained migration-owner ACL.

`trigger_acl_control_v2.py` passed exact ACL/caller restoration after successful trigger creation,
actual trigger invocation, and failed creation inside a savepoint. It checks that the writer lacks
effective EXECUTE through the catalog. The original control's runtime-writer-refusal label is
superseded: SQLSTATE42501 could come from denied SET ROLE before direct function invocation.
Both originals are retained. No role membership or persistent capability was added.

`author_forward_v7.py rehearsal-011` passed the complete bounded rehearsal: all 36 table drops;
52 native operations with 85 desired objects; refreshed model-derived physical CHECK receipt;
no remaining function body references to the 36 retired qualified names; run/config/task/claim,
cancellation with late-completion refusal, and independent observation completion; empty native
and ordinary follow-up candidate; nullable/ACL/unexpected-CHECK drift refusal; stale-directive
refusal; source-window stability; and outer rollback to82 and `paul`.

Physical CHECK replacements are protected by the preceding descriptor's physical ID and source
digest and its exact stored CHECK expressions. Current expressions come from PostgreSQL-normalized
current model tables, and named-paramstyle Alembic DDL preserves literal percent characters.
Two old `#%%` literals become the modeled `#%`; no global SQL text substitution is used.

Earlier rehearsals001–010 remain as failure evidence. They exposed the unavailable admitter/writer
SET ROLE contexts, a leftover identity-exclusion `kb.span` join, missing complete method fixture
metadata and pending deferred constraint events before authoring DDL. Rehearsal011 flushes those
constraints before the fresh candidate check. Rehearsal012 passed after the main merge and formatting. Review caught one lifecycle
RETURN changed into a profile refusal; it is restored before final capture. Rehearsal014 proved
the deferred guard rejects a finished run without its completed EvaluationResult.
`author_forward_v10.py rehearsal-015` then passed the complete current flow in SERIALIZABLE:
Report completion, final sealed cut, empty publication receipt, completed EvaluationResult,
and empty polling in cancelled, sealed/consolidating, finished and failed states. It also
repeats all retirement, empty-candidate, drift, stale-directive and rollback controls.

All release admission and lifecycle checks in the author transaction run as publisher with session
migration owner. They are **guard/catalog and publisher-context functional checks**, not actual
admitter or writer login qualification. The author login cannot SET ROLE to either runtime role;
other connections cannot see its uncommitted forward DDL. The coordinator owns actual runtime
LOGIN qualification on a fresh committed target, assembled acceptance and final freeze approval.

The manual source sweep of current SQL resources found only one intentional semantic-1 occurrence:
`sem.require_archive_bytes` accepts internal schema-only compiler14/archive3 preparation. All
execution/effect entry guards require the current composed release; schema-only preparation has
no execution authority. Final forward artifacts will be captured after source/review integration.
