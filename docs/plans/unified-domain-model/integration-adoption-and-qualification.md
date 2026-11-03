# Integration, adoption and qualification

> Current execution (2026-11-02): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator.

## Baseline and preservation contract

Consume the principal review at `370f0643`, diagnostic publication `54cd74cb` and the current
inspected implementation snapshot recorded by the coordinator. Existing exact archives, protected
native operations, generated metadata, typed result dimensions, qualified graph closure, Arrow
profiles, retained producing pins and independent reference evaluation are useful foundations.
Their old receipts remain evidence only for their original scope/source.

PDF work is still evolving. The operator explicitly selected planning against this snapshot,
with a later **discrete update** to reconcile subsequent PDF changes. Do not continuously chase
that work or import its remaining book/provider/default-adoption obligations. Before executing a
package that consumes a changed PDF contract, perform that focused update and reassess affected
evidence. Ready unrelated work can proceed. A successful PDF deployment does not qualify this
new series; nor does this series claim the PDF coordinator's unfinished delivery.

## UM-14 — Consumer integration and adoption

Every producer package migrates its directly affected consumers. This package owns the final
cross-series inventory and transitions that cannot honestly be closed locally. Inventory the
maintained public and internal callers from actual source, including CLI, MCP, serving/query,
consolidation/scientific evaluation, orchestration, native authoring/admission, Arrow publication,
analysis/capture/export and operator diagnostics. Representative first consumers are not the
complete migration scope. Record an explicit supported reason for a retained alternative.

Required usable boundaries before integration:

- UM-01/02 comparison and observable-invariant contracts and their implementing consumers.
- UM-03 generated request/result/signature/bind/materializer products and runtime validation.
- UM-04 compatible query implementation identity across data, continuation and explanation.
- UM-05/08 projection recipe and qualified dependencies; Core remains primary execution.
- UM-06/07 versioned body/custody/catalog/admission and frozen migration products.
- UM-09/10 runtime resources, supported lazy results, exact transport/snapshot owners.
- UM-11/12/13 actual CLI/MCP applicability, impact and diagnostic capabilities.

These are working products, not agreements alone. Preserve semantic identity, qualified scope,
source versus derived facts, exact versus bounded values, supplied/null/unknown distinctions,
relationship occurrence identity, ordering and multiplicity through each migration.

### Transition route

1. Generate candidate products from explicit source inputs; compare their model meaning and
   selected actual native properties with independent expectations. Keep current artifacts/pins
   available until the selected replacement is usable.
2. Deploy reviewed forward native changes through the existing Alembic comparator → operation
   → renderer → frozen payload → before/after admission route. Do not edit old revisions or
   import current generators during historical replay. Preserve owner/ACL/search-path/dependency
   semantics and caller-owned transaction rollback.
3. Admit a release/implementation binding only when required native capabilities exist. A new
   schema label, annotation or parser success does not authorize effects. Rebuild only derived
   artifacts whose declared premises changed; never reinterpret an old pin under new meaning.
4. Migrate each ordinary caller to its typed domain API, including parameter/result/failure and
   resource ownership. Retire replaced text/metadata interpretation, mapping-key reconstruction,
   duplicate expression/catalog definitions and obsolete compatibility paths once their maintained
   consumers have moved. Generated deployment SQL and deliberately invalid fixtures remain.
5. Exercise real serving/explanation/export and CLI/MCP consumers under the admitted products.
   Replace operational selections only when actually needed by this series, recording supported
   historical-read/refusal behavior. Existing PDF operational defaults remain externally owned.

Useful intermediate states are allowed: a typed read operation can be adopted before all writers,
SQLGlot analysis can serve one settled projection, and the early diagnostic contract can support
call generation before all operator tooling ships. Each state must say what works and what still
uses an older supported contract. No dual-write or universal compatibility layer is introduced
without a concrete migration need.

**Current writer retirement, identified during UM-14 integration (2026-11-02):**
`UnitResult.native_products` / `integrated_products` and their method-context retention callbacks
still reached aggregate writers that populate legacy `native_document_*` / `pdf_product_body`
rows without `pdf_published_revision`. Current stock document producers use the record pipeline;
merely generating typed envelopes for those obsolete writers would preserve the incompatible
authority split. Retire these terminal fields/callbacks and their current operation bindings,
adapt maintained fixtures to actual record publication, and refuse legacy native adoption early
with an actionable record-publication remedy. Preserve explicit historical reads and frozen SQL.
Recognition observation publication remains active and distinct: `_retain_page` publishes immutable
input bodies through the old generic callback. Preserve it as an observation-only named contract
and protected native kind guard; an observation is not a document requiring source-view placement.
Removing the entire generic implementation without migrating this caller would break recognition.
Keep raw-record recovery through the existing explicitly global organize operation when qualified
sections are absent; ordinary organized-record adoption uses selected records without hydration.
An aggregate-to-record importer is not selected. The [database owner](../../design/D3-database.md#relational-document-realization-and-publication)
records the consistent go-forward target; completion still requires actual affected-consumer checks.

### Concrete library composition

Core `select`/typed function/selectable and explicit row materialization realize domain APIs;
Pydantic prepared adapters validate external results; Arrow schemas and profiles preserve exact
bulk representations. pglast-generated declarations feed the existing Alembic native operation
and independent catalog checks. SQLGlot `qualify`/`annotate_types`/`lineage` supplies selected
projection analysis, not database authorization. RDFLib occurrence resources and scoped pySHACL
`validate` retain graph fidelity and separate conformance. The implementing companions retain
exact APIs, versions and source references; integration checks their actual composition.

Runtime PostgreSQL publication still uses the same SQLAlchemy/Psycopg connection with fresh pgpq
encoder state. ADBC read uses its own transaction and imported snapshot; it cannot observe
uncommitted publisher staging. DuckDB relations/Arrow readers retain declared lifetime; detached
outputs outlive scopes only when their contract permits it. Cancellation must settle all owned
resources before reporting completion. None of these boundaries mandates a process or task per
semantic concept.

## UM-15 — Required acceptance union

Define the final required functional/native/provider/nonfunctional scope from the actual changed
contracts and maintained consumers. Do not simply add overlapping package counts or assume all
old tests remain applicable. Package checks establish their bounded behavior; assembled acceptance
requires working integration and final-source/context applicability. Use repository outcomes
passed/failed/blocked/not_run and retain failed/interrupted records unchanged.

| Journey | Independent success and failure expectations |
|---|---|
| Comparison/identity | Two ownership assertions with distinct attribution/interval remain distinct facts while an explicit policy groups them; invalid property/cross-scope reference refuses preparation. |
| Typed calls | Add parameter/result/optionality once; generated signature, native invocation, Arrow/result shape change coherently. Negative Pyrefly cases reject wrong arguments/columns; actual malformed server output is refused. A cast or generated annotation alone cannot pass. |
| Query compatibility | Complete a run, change its plugin and query it through CLI; use a continuation and explanation/evidence reference. Retain declared compatible meaning or refuse explicitly, never execute arbitrary archived Python. |
| Invariant/effect | Required native guard emits its bound stable diagnostic identity; domain failure code matches the admitted promise. Unmapped native failures preserve raw cause. Metadata/body digest agreement does not prove enforcement. |
| Native body/evolution | Generate a suitable SQL-standard body; verify definition-time dependencies, result/overload identity, volatility/security/search path, grants, catalog comparison, stale-before-state refusal, deliberate recreation and rollback. |
| Guarded mutation | Authorized success and unauthorized/stale owner/concurrent writer, duplicate conflict and failure-before-publication preserve atomicity and receipt meaning. Never move mandatory guards into optimizer-reordered expressions. |
| Projection/analysis | New JSON field/path/cast/scope updates Core/Arrow/domain result and qualified dependencies. Missing/JSON-null/SQL-null, exact number, duplicate endpoint and order cases preserve distinctions. Unknown UDF/type stays unknown/refused. WHERE-only/join dependencies and nested pinned sources reach impact output; cycles, CTE shadows and opaque syntax cannot masquerade as complete analysis. |
| Transport/resources | Multiple batches retain exact schema/value/profile and same-transaction adoption; separate ADBC snapshot reads are coherent. Non-default memory/thread/scratch settings reach consolidation. Check cancellation and early consumption, not only full success. |
| Lazy lifetime | Retained relation/reader/iterator cannot bypass supported post-close behavior; materialized detached outputs remain valid. Teardown attempts every independent closer and retains individual failures. |
| O01 | Real CLI/MCP operation explanation distinguishes available/unavailable/unresolved; concurrent state change after preflight is still refused atomically by execution. |
| O02 | Changed comparison/result/invariant/projection reports declared affected consumers with model IDs; incomplete dependency knowledge reports unknown rather than proving equivalence. |
| O03 | Invalid value, cross-record nonconformance and validator infrastructure failure reach real consumers with exact location/scope and original diagnostic, never one Boolean truth bucket. |
| Growth/substitution | High-degree closure and empty-result completeness use the semantically sufficient universe; alternative translator/kernel preserves precision/order/multiplicity/failure/effects. Assess access paths, blocking intermediates and owned working set qualitatively. |

Use independent fixed expectations/invalid inputs/native clients where a producer/decoder could
share the same defect. Reuse production validators to enforce contracts; testing validator
correctness needs independent expectations. Preserve deliberate invalid SQL and historical frozen
artifacts. No second validator, alignment lint or mandatory benchmark framework is introduced.

### Published document consumer acceptance

This required UM-02/03/05/06/07/09/10/11/12/13 integration case follows the
[single binding/projection design](relational-implementations-and-projections.md#published-document-consumers).
Changing a producer includes read selection, target FKs, publication bindings, inserts, replay,
source-frame capture and rendering; typed reads cannot close migration while effects still refer
to an obsolete physical authority. Reference/evaluation consumers must receive the actual prepared
source views. UM-14 closes remaining affected callers, not work deliberately deferred from an
earlier package. PDF retains its implementation/deployment and provider/default acceptance owner.
Working PDF foundations enable this case; contracts and unrelated UM work need not wait for all PDF
qualification. If PDF fixes land first, inspect and reuse them, then qualify UM-specific composition.

Use a small actual PostgreSQL record publication followed by source-view preparation, frame capture
and rendered-artifact persistence. Independent expectations must cover:

- Exact accepted product/build/revision binding; identical pointer spellings in different products
  remain distinct. Reject mismatched published pin/build even when both separately exist.
- Unpublished builds, wrong revisions, absent sections, regions belonging to another pointer and
  stale caller/attempt state. Preserve native failure causes and rollback/no partial consumer effect.
- Idempotent replay retaining the same resolved binding and artifact/view identity.
- Successful document publication followed by failed consumer preparation, then recovery from the
  retained pin without recognition or book republication. Source-ready still requires prepared views.
- Independently specified direct/descendant membership, body order, rich table/chart cells, inline
  content/separators, ancestry, evidence positions and health. Exercise selected-record preparation
  without whole-book reconstruction or per-pointer fetch; full export/global validation stay distinct.
- Generated typed-call refusal and malformed native-result admission; actual O01/O02/O03 responses
  preserve prerequisite, relationship-impact and located-failure distinctions with unknowns explicit.

Runtime semantic/native controls establish these properties; producer-generated expected FKs or
self-round-tripping alone do not. Existing PDF/provider receipts keep their original source and
scope and are not new UM qualification. Do not rerun the whole book to validate a consumer-only
binding change. Changed interpretation/native premises still require their affected checks.

### Verification timing and commands

During implementation run relevant compile, focused Pyrefly/static-negative and functional/native
controls at coherent package endpoints. No integrated campaign after each edit or document.
When all functional scope is implemented, finalize source with root `just turn-end`, run
`just test-all` and applicable `just hygiene` checks, then account for the same-source/context
required union, including external/provider scenarios only where changed supported behavior needs
real-provider evidence. An unavailable required prerequisite remains named and open.

Do not mutate shared or operational databases for convenience. Native migration/privilege/race
checks use authenticated owned disposable instances under the existing database contract;
cleanup requires exact ownership, and other projects' cluster/defaults remain untouched.

Quantitative speed/memory/quality benefit is not a completion claim unless a specific selected
claim has representative measurement. Structural removal of repeated authoring/conversion work
can be explained qualitatively. Frozen failures, partial evidence and earlier overlapping passes
receive no automatic acceptance promotion.

## Completion boundary

UM-14 closes when every maintained affected caller has an explicit supported route, replacements
and transitions are complete, and original exact pins/frozen history retain their stated meaning.
UM-15 closes only with applicable required-union evidence and resolved required obligations.
The coordinator records final package/source disposition, residual native-authoring families and
supported limits. Plans and evidence are retained after completion. Their design text remains
Proposed until implementation and its actual verification justify stronger claims.

## Completion audit — 2026-11-02

**Baseline:** `fb84eb8f`; independent source/consumer and library-mechanism inspection, with no new
product tests, provider runs or database mutations. The coordinator owns all current disposition.

The current-only consumer migration has substantive implementation and232 distinct targeted native passes, with independent pure preparation controls separately scoped. **Integration is not complete:** UM-CA13 leaves cancellation disconnected across SQLAlchemy metadata and ADBC bulk export. UM-CA10 and UM-15 also retain79 unqualified math nodes, corrected fresh PDF intake, five-section actual-provider knowledge/query/report/export/evaluation and full required-union acceptance. Historical failed/interrupted receipts remain immutable. Current test-architecture work retains its own owner; this audit did not refresh its premises.

See the [coordinator audit](../unified-domain-model_2026-11-01.md#completion-audit--2026-11-02)
for combined judgment, UM-CA evidence and remaining obligations. Library tables above retain their
accepted mechanisms and limits. New improvement proposals are separately published and unadopted.

## Test-architecture reconciliation — 2026-11-02

**Selected amendment:** Current implementation and qualification are owned by the coordinator.
TA foundations retain their declared scope; their completion does not itself qualify UM.

Consume [I01–I07](../../plan_improvement_reviews/unified-domain-model-test-architecture_2026-11-02.md) through the existing package owners. Before assembled acceptance,
close newly exposed query-helper custody (UM-TA01), qualify projection preparation/runtime reuse
(UM-TA03), deliver alias impact/advice (UM-TA02), and close UM-CA13 including the actual affected
two-backend consumers. TA DTA dispositions and Phase0 X2-01 remain external owners.
UM-TA04 migrates shared typed scenario ports and all affected callers, with focused wrong-ID/
resource typing controls and real positive/invalid-boundary cases; raw negative setup remains usable.

Reuse the existing native settings captured before ambient-target refusal, owned PgAdmin clones,
purpose credentials and `record_native_context` event stream. Acquired database/OID/principal,
server lifetime and policy/deployment references are required provenance for relevant native
claims. An item-associated maintenance event alone does not prove the operation ran under its
restricted application principal: observe actual SQLAlchemy/ADBC/child sessions where claimed.

The current semantic-1 cold test, hand-authored identity vectors, source-authored counterpart
journeys, stdio proposal/refusal and real formatter byte/cursor controls have different scopes.
The formatter's minimal tables/stub publication and ScalarReader overrides do not establish full
native admission, ADBC transfer or memory/throughput. Post-list-tools cancellation does not
establish active-operation cancellation. Keep separate independent semantic-2 cold, query-helper
edit, alias-only impact, actual native publication and metadata/handoff/bulk controls where needed.

Use existing receipt `source_identity` and selected-node/required-union classification, then
adjudicate changed source, harness, deployment and principal premises. Reuse applicable receipts;
rerun only unresolved or affected obligations. Never add overlapping counts, infer new-test passes
from the earlier212-node TA native increment, or retrofit old provenance. TA-12 qualification and
UM product/provider acceptance remain distinct. Notice/T3-D1 retain their unsupported meanings;
current controlled proposals are not original-document recognition. Final UM acceptance remains open.
