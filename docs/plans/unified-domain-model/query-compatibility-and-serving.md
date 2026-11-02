# Query implementation compatibility and serving

> Current execution (2026-11-02): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator. **Created:** 2026-11-01.
**Target:** Implemented / Tested within the execution checkpoint below. Source [R02 / DA-028](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R02)
is the highest-consequence current correction. The [coordinator](../unified-domain-model_2026-11-01.md)
owns current disposition and assembled completion. Existing plans and frozen products are unchanged.

**Planning snapshot:** committed source/review `370f0643` plus the specifically inspected dirty
PDF/model/native seams. The PDF series is still completing and may change those seams. This plan
does not continuously absorb that work or own its acceptance. A later update will reconcile the
then-current PDF snapshot as a discrete step before dependent execution.

## Baseline and preserved boundary

`semantic/regeneration.py:109–125` archives `operation/queries.py`, while `cli/query.py:25–46`
loads the selected run's current `DOMAINS / domain` plugin. `serve/registry.py:51–76` hashes current
path/bytes for module caching. That identity does not establish agreement with the producing release.
Current named-query continuations carry run, release/realization/revision, query version, parameters,
projection and arithmetic identity (`serve/journey.py:117–145`). Data pinning is useful but incomplete
when answer-affecting implementation meaning can change independently.

Preserve the current `DomainQuery` protocol's name/version, Pydantic parameter/result models,
`rows` and `scope`, positioned pagination and shared read-only snapshot owner. The selected change
adds an admitted implementation compatibility binding; it does not execute arbitrary archived Python
or retain an unlimited collection of historical environments.

## UM-04 — Bound trusted query implementation

A query's trusted installed implementation declares an immutable implementation identity and a
meaning-contract revision, its exact parameter/result schema projection, supported producing-query
contract identities, required runtime/operation capabilities, and source provenance. The producing
release archives the query contract identity and the implementation identity under which it was
admitted. Byte changes are detected from the implementation's explicit code bundle; source files
that affect query meaning are included by the owner rather than discovered through arbitrary imports.

The default support rule is exact identity. A current implementation may declare compatibility with
a prior producing contract only through an explicit trusted compatibility entry with independent
behavioral evidence for that contract. Editing a file while keeping the handwritten query version
unchanged cannot grant compatibility. A cosmetic/source-only change may retain meaning through
such a reviewed entry, but its producing and executing implementation provenance remain distinct.
No permissive wildcard, path-only identity or implicit current-byte fallback is allowed.

Resolve this binding before loading a query for execution. Module caching may continue to hash path
and bytes, but registry construction for a run also requires the admitted binding. The generic query
set follows the same rule wherever its meaning affects an answer; pack-local plugins are not the
only possible implementation dependency. Reject missing, ambiguous, unsupported or incompatible
bindings with a structured unavailable/incompatible-query outcome and explicit reselection/rebuild
advice. A retained compatible implementation may serve an old result when already supported, but
installing or executing an arbitrary archived body is not the recovery path.

Do not reinterpret a frozen release to add the new binding. Newly admitted releases carry the new
product. For existing archives without a query binding, support only an explicitly trusted historical
adapter whose known contract/provenance is qualified; otherwise refuse that named-query route.
Existing primitive data access can remain supported under its own read contract. Refusal is not a
claim that the retained data is corrupt or that all historical reads are unavailable.

## Journey and public behavior

Resolve the query binding once inside the actual read/snapshot entry path and pass the bound query
to parameter validation, scope selection, row production and pagination. The continuation carries
the query meaning-contract and implementation compatibility identity in addition to existing pins.
A continuation issued by a prior token format remains accepted only through its declared supported
reader; never silently treat a missing implementation identity as the current one.

Follow-up explanation and evidence requests receive the same producing query contract and binding.
Where their own implementation meaning can affect the answer, they also resolve their trusted
compatibility requirement. Selecting a newer active model or editing a plugin cannot rebind an
already issued journey. An explicitly new query is a new operation with its own disclosed contract.

Preserve existing parameter normalization, exact predicates, coverage/knowledge outcomes and
projection universe. A code-compatibility pass does not establish data freshness, complete coverage
or evidence closure; those current checks remain. Continued data-revision and parameter mismatches
retain their existing modeled distinctions. Do not collapse programming/infrastructure failures
into an ordinary incompatibility outcome.

## Concrete library composition

| Mechanism | Selected responsibility and limit |
|---|---|
| Pydantic 2.14.1 parameter/result models and reusable `TypeAdapter`/schema projection | Validate actual caller input/output against the admitted query contract. Validation/serialization schemas and custom executable semantics are not interchangeable; include the relevant runtime contract. |
| Existing immutable release products and normalized execution bindings | Supply producing model/query and capability identity. Query implementation compatibility is a separate declared contract, not inferred from matching data schema or the active project release. |
| SQLAlchemy 2.1.6 existing repeatable-read/read-only snapshot owner | Bind the selected completed result and its evidence consistently while the query runs. Snapshot pinning does not pin code; no second connection/transaction owner is introduced by this package. |
| Existing structured continuation/refusal machinery | Carry and classify the additional binding dimension. Keep unsupported token, stale query, wrong parameters, data-revision mismatch and implementation incompatibility distinct. |

Library evidence: [Pydantic boundary account](../../library_leverage/libraries/unified-model-boundaries_2026-11-01.md)
and [PostgreSQL account](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md).
Source entry points are [query registry](../../../python/corpus-structure/src/corpus_structure/serve/registry.py),
[named journey](../../../python/corpus-structure/src/corpus_structure/serve/journey.py) and
[query protocol](../../../python/corpus-structure/src/corpus_structure/serve/protocol.py).
No library reflection or AST analysis proves compatibility of arbitrary changed Python behavior.

## Delivery, migration and dependency boundary

UM-04 consumes existing release archive, query protocol and snapshot/continuation mechanisms. It can
begin independently of UM-01/02 and of wholesale typed API/native-body generation. Its early shared
contract supplies implementation/query identity to typed serving adapters and O02 impact analysis.
Actual consumer migration includes CLI named queries, query discovery/schema description where it
selects run-specific implementations, serving/pagination, explanation/evidence follow-ups and any
MCP route exposing those named answers. Inventory the actual callers before closing this scope;
a representative CLI fixture alone does not establish the complete journey union.

Add producing/reader compatibility products before switching execution. Migrate each caller with
its release-aware registry opener and retire direct live-pack registry construction for run-bound
execution in the same slice. Keep filesystem-only shell completion side-effect free; it may list
installed capabilities but cannot imply run compatibility. Preserve frozen migrations/evidence.
Any stored continuation/product change uses the native evolution and supported-reader routes.

## Execution investigation and acceptance

**UM-I04 — Query compatibility closure.** Inventory answer-affecting query implementation bundles,
helper/runtime requirements and currently supported historic contract/token formats. Produce the
finite compatibility set and independent examples for any non-exact support entry. If a historical
contract cannot be established, the selected outcome is an honest route-specific refusal, not
arbitrary archived-code execution or a new all-history environment framework.

Create a completed-run query and continuation, edit the installed plugin without bumping its name
or version, and request the original query/continuation/explanation. Require compatibility refusal
before executing changed query logic. Then exercise an explicitly compatible implementation with
independent expected rows and evidence. Test a source-only change both without and with its explicit
compatibility entry. Cover wrong parameters, wrong data revision, unsupported token reader, missing
binding, ambiguous compatibility and unrelated infrastructure failure.

After activating a newer release, the supported old-run answer retains its original model, result
and query contract. Current query discovery may show a new capability without changing that old
journey. Compare an incompatible result shape and a semantically changed query with identical shape:
matching Pydantic fields is not sufficient to accept either as equivalent meaning.

The preceding controls describe the accepted delivery scope; observed results follow below.
The [integration owner](integration-adoption-and-qualification.md) assembles actual CLI/MCP/native
journeys and final-source evidence, preserving scoped failures and unavailable required obligations.

## Execution checkpoint — 2026-11-02

`semantic/query_compatibility.py` acquires an explicit installed source bundle before plugin import,
archives its query manifest and normalized bindings through the existing release-product machinery,
and opens a registry against the producing release. Exact identity is the default. Non-exact support
requires an explicit compatible producing contract/implementation and evidence; matching name,
version or result fields alone is insufficient. Archived Python is never executed. Historical named
routes without this binding refuse explicitly; primitive exports retain their independent route.

The finite import-custody bootstrap records actual helper bytes at their owned import boundary.
It preserves light CLI help and ordinary imports, refuses uncustodied warm modules or changed loaded
helpers, and does not treat a later filesystem hash as proof of already-loaded Python objects.
`BoundQuery` and version-2 named tokens carry producing and executing identities through query pages,
explanation and evidence. Origin-token resolution passes the validated run into the actual query;
explicit conflicting run requests refuse. Result validation retains concrete released nested models
through a shallow field mapping instead of erasing their type before serialization.

Scoped checks passed for exact acquisition/binding, edited or missing source, historical unbound
refusal, compatible and incompatible declarations, helper imports before first acquisition, changed
loaded helpers, cold CLI/MCP registration and typed nested-result validation. Logs include
`build/um04-bootstrap-final-controls.log`, `build/um04-cold-mcp-derived-schema-controls.log`,
`build/um04-custody-final-source-controls.log` and `build/um04-typed-result-positive-negative.log`.

The actual admitted native-85 CLI journey passed in two scopes:

- `um04-cli-journey-00007.jsonl`: ordinary named query, continuation, malformed/wrong binding
  refusals, explanation and Parquet export passed. Its separate plugin-edit case failed at the
  evidence origin-run handoff and prompted the bounded CLI correction.
- `um04-cli-journey-00008.jsonl`: initial and continued independent Alice/Bob rows; query/page/
  explanation refusal before an edited plugin could execute; primitive JSONL export during that
  incompatibility; declared-compatible requery, bound explanation and evidence; explicit wrong-run
  and old executing-token refusal all passed. Final scoped typing reported zero errors and Ruff
  passed (`build/um04-origin-context-types.log`).

Receipts are under `build/test-receipts/`; failed attempts remain unchanged. Earlier setup-lock,
shared typed-JSON lowering, nested-result serialization and stale generated report-schema refusals
retain their original scope. These results establish the selected query/CLI behavior, not full
series qualification or operational book/default adoption. The coordinator owns remaining union
accounting and final maintenance.

## Completion audit — 2026-11-02

**Bounded judgment:** owner-declared implementation acquisition, producing compatibility before
registry loading, bound continuation tokens and explanation/evidence origin handling have actual
maintained routes and retained passing query/CLI controls. No material gap was found in those
inspected mechanisms. No production named-query MCP execution route was found requiring migration.
The deliberately unsupported historical unbound route correctly refuses; archived Python is not
executed. This does not establish all supported historical readers: UM-CA01's numeric schema
reconstruction fails compiler10 answer retention and historical capture before their intended
behavior. Keep that single shared defect under UM-03/04/14, without discarding the narrower query
custody passes. Package/enclosing acceptance remains open, as owned by the coordinator.
