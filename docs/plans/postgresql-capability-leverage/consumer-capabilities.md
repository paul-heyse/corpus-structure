# Analytical, operator and selected-source consumers

**Proposed target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-06/07/10 and PG-I03. These are selected delivery scope, not optional future discovery. Existing published/read contracts are prerequisites; unfinished work in another plan is not imported.

## PG-06 — Companion Parquet and DuckDB inventory

Deliver one shared application operation receiving a published product pin, selected companion families and a destination. The initial supported set is input, relation, coverage and mapping report. The model determines exact projected fields, keys, cardinality and null/unknown meaning. The operation returns an owned export manifest; files are not writable authoritative database replacements.

Extend the existing pinned source export service/CLI with a clearly named companion-Parquet operation, rather than exposing arbitrary raw tables. Consume model-derived authorized batch projections from [typed realization](typed-realization-and-transfer.md). Close ADBC readers/cursors/sessions on success, failure and abandoned iteration; output files remain owned until the last consumer finishes. Produce deterministic logical ordering where the export contract requires it; physical batch boundaries must not change product identity.

Add a DuckDB inventory operation that reads that manifest and produces input counts, relation-kind/endpoint inventory, coverage outcome distribution and mapping status for the same product pin. Compare two explicitly named exports under the same declared projection to report differences; do not implicitly select latest data or merge incomparable profiles. Unknown/unrequested/partial/failed outcomes are separate, and a zero count is not independent proof of complete coverage.

This consumer demonstrates the value of columnar families rather than adding an Arrow helper unused by product flows. Keep bounded Core item reads and native JSON event export separate. Do not round-trip whole native documents through dicts solely to construct these relational analyses.

**Acceptance:** real PostgreSQL → batch reader → Parquet → DuckDB through the public service/CLI, with independently expected membership/types/counts. Cover wrong product/project/pin, hidden staging, empty legitimate family versus unsupported family, exact numeric/JSON/null semantics, multiplicity, mismatched manifest/file binding, snapshot change and early sink/reader failure. A mock driver is not the live path. Dataset scanner pushdown is allowed where it preserves the actual input universe and metadata.

## PG-07 — `ci db describe`

Extend the existing Typer database command group and `--json` output convention. Deliver a structured description for explicit schema/relation filters, optional prospective **read-only query output schema**, requested metadata depth and optional estimates. One shared service supplies CLI rendering and later callers; no separate interactive catalog browser or agent-specific interpretation is required.

Use ADBC `adbc_get_objects` for scoped physical discovery, `adbc_execute_schema` for a supported admitted read-only statement's output shape, and supported `adbc_get_statistics` for estimates. Reuse Core/native inspection for specific facts these interfaces omit; do not replace stronger function-body/owner/grant admission with incomplete metadata. Query description accepts an existing admitted SELECT representation or applies the current read-query admission boundary; it is not a path to execute arbitrary DDL/DML under a “describe” name.

The report labels each meaning: model declaration, physical observation, query output or planner estimate. Include database/schema/relation context, declared limits and provenance/freshness when actually available. Missing statistics stay unavailable; exact counts are not silently inferred. Describe filters/returned scope so an empty answer can distinguish no match, insufficient privilege and unsupported observation. No package-version inventory or approximate percentage of correctness.

**Acceptance:** actual selected-relation and query-schema journeys with independent expected columns/types; filtered schemas, omitted fields, unsupported statistics, privilege refusal, stale estimates, empty/missing relations and query refusal before effects. Assert JSON and human output carry the same meanings. Access uses the existing read principal and explicit session lifetime. Richer backend fields are conditional detail, not a new catalog authority.

## PG-10 / PG-I03 — Selected-source export for an intact section

Deliver a distinct **selected-source-v1 JSONL package** through the existing shared source export service and CLI. A request supplies one published product pin and one declared intact section/subtree selector. Do not use complete `docling-json`/`integrated-json` format names for partial output. Existing request/response types may change deliberately to express the clearer target.

Use ordered record/event rows and sink streaming, not full-subtree hydration or a call per native node. The package has a bound header, ordered selected native records/events, required integration/evidence context and a closing export receipt. Its contract declares the selected root, source addresses, schema/selection policy, included families, context rules, explicit outside references and omissions. Original addresses are retained; do not manufacture a reindexed “complete DoclingDocument.” Export byte identity identifies this serialization, distinct from the source product's logical identity.

PG-I03 settles actual context closure for one scientific/extraction caller before implementation: descendants and containment/order needed to interpret the section; selected decisions and coverage; direct source/input evidence; and referenced outside records required by that consumer. Carry resolvable external references or necessary context according to the declared operation, not every transitively reachable object by default. A root outside the published selection refuses. Necessary context exceeding output scope remains explicit; a filtered output is not a silently filtered scientific input universe.

The consumer reads the JSONL package through the same selected-source meaning used by source frames/packet preparation and verifies that formula/table context and evidence addresses resolve without full-document hydration. This is a projection of a completed product, not progressive publication or a new authoritative document. A failed sink cannot publish a completed export receipt; cleanup removes only its owned temporary output.

**Acceptance:** independently expected subtree membership/order and required context; repeated occurrences, external references, large scalars/Unicode, coarse or missing geometry, wrong pin, hidden staging, explicit companion omissions, cross-project refusal and abandoned sink. Include one actual extraction/scientific **input-preparation** journey; no new inference, independent golden authoring or whole-book validation obligation is imported. Verify complete native exports retain their existing meaning after interface migration.

## Library-informed composition

[ADBC original §§3–9 and addendum §§1/5–8](../../libraries/postgresql/adbc-driver-postgresql.md) supplies columnar transfer and physical description; [SQLAlchemy relational/streaming sections](../../libraries/postgresql/sqlalchemy.md) supplies bounded rows and query intent; [Psycopg cursor/lifecycle](../../libraries/postgresql/psycopg.md) and [pool ownership](../../libraries/postgresql/psycopg-pool.md) constrain cleanup. The model and source owner supply scientific meaning and publication authorization.

Keep the three outputs distinct: typed analytical relations, physical/query description and selected native/context serialization. They share source facts and resource mechanics without one lowest-common-denominator reader. H5/H6/H8/H16/H17 favor useful demand and bounded movement; DP-07/08/15 preserve completeness, ordering and evidence distinctions. Quantitative benefits require measurement rather than being inferred from the word “streaming.”
