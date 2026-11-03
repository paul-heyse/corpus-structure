# Release transition and integrated acceptance

**Proposed implementation plan · 2026-11-03.** Companion to the
[audit-closure coordinator](../audit-closure_2026-11-03.md), the sole owner of package state,
execution queue, new-review disposition and the M1 impact handoff. This document develops
AC13–AC14 and the I04 native-foundation investigation. It does not duplicate package statuses or
move original audit findings from their prior disposition owners.

## Basis, foundations and boundary

The accepted planning input is the [audit-closure target review](../../design_review/reviews/design_review_audit-closure-target_2026-11-03.md)
at `fd4ea6011ca0a501d0c986829304fe661a3c5751`, with its three linked semantic, runtime and
consumer contributions and audit `90ed25c4`. All RC01–RC12 were accepted for planning by the
operator on 2026-11-03. AC00 schedules the owning ADR/design changes; no authority is changed by
this companion. Current implementation inspection used `fd4ea601` and concurrent dirty M1 files,
including untracked forward101 artifacts. This is source evidence, not native deployment proof.

The [declared standard](../../design_review/design_principles/standard.toml) is core3.3,
heuristics1.0, code-intelligence1.4 and test-assessment1.2. FP-02/04/05, CI-10–13 and H23–25 govern
versioned meaning, pinned journeys, independent evidence and recovery. Exact representation,
source assertion, derived evidence, selection, assessment and coverage retain distinct meanings.
Atomic visibility is an existing strength, not a reason to merge semantic responsibilities into
one broad transaction or create a new release certificate system.

Current owners are [D2](../../design/D2-schema-and-guidelines.md),
[D3](../../design/D3-database.md), [D5](../../design/D5-consolidation-identity-confidence.md),
[D6](../../design/D6-orchestration-metrics-policies.md), [D7](../../design/D7-evaluation-goldens-outer-loop.md)
and [D8](../../design/D8-agent-and-query-interfaces.md). Their accepted runtime/reader contracts
and current-source claims must be reconciled before they are relied on, not replaced by review prose.

| Foundation inspected | Consequence for execution |
|---|---|
| `semantic/native_candidate.py`, `native_inventory.py`, `native_sql_body.py`, `alembic_native.py` under product source | Existing candidate authoring prepares normalized native objects with predecessor inventories and enforcing admission guards. Preserve actual body/signature/owner/grant/dependency interpretation, including SQL-standard body handling; a source checksum alone is not live admission. |
| `python/corpus-structure/semantic_alembic/versions/0101_m1_records.py` and its dirty state/admission companions | A draft forward revision from immutable native100 exists, not a proven deployed prerequisite. I04 must establish the actual supported starting revision and its inventory agreement before AC changes author another forward transition. |
| `semantic/records.py`, `semantic/sql/record_publication.sql` and dirty M1 reader/report fixes | Current source preserves absent terminal reports rather than silently dropping their units. Carry that boundary through new standing/coverage/query shapes; source existence does not establish current native/public consumer behavior. |
| `semantic/query.py:342–397`, query/reader fixtures and compatibility operations | Read-only repeatable-read and release/realization pins exist. Migrate changed query/result/cursor/reader contracts at the operation that introduces them; preserve immutable old products under supported readers or refuse incompatible use. |
| `python/corpus-structure/tests/semantic/conftest.py`, package `tests/conftest.py` and shared native support | Existing owned template/cloning and separate reader/writer/evaluator/admitter principals supply actual native lifecycle evidence. Reuse them, with explicit bare/upgrade paths for migration obligations. |
| `scripts/test_receipts.py`, `justfile` | The qualification runner records actual selected node outcomes and native acquisition context; it does not choose applicability. The integrator declares the required union and checks unresolved items, without using recipe labels or counts as coverage. |

## AC13 — Carry each corrected contract through release and consumers

AC13 is the continuing owner of cross-cutting release compatibility, forward-native coordination
and atomic adoption. It participates from the first changed contract; it is not a final phase to
which AC01–AC12 may defer necessary consumers. Each feature package delivers its producer,
generated/native enforcement, affected readers and actual consumer migrations together. AC13
supplies the compatible release/version slice and checks composition across those deliveries.

**Required input:** AC00's accepted RC routes and preserved guarantees; I04 for new native
authoring/admission; the specific working contract from the feature package. Contract agreement
is sufficient for early adapter work, while native/consumer execution requires a coherently
installed/admitted revision. AC14 consumes the final assembled result, not just that agreement.

Use the existing effective release/compiler, frozen archive readers, operation bindings and
native forward migration machinery. Change version/determinants wherever meaning or compatibility
changes: source attribute assertion shapes/admissible subsets, RuleValue ABI and dependent rules,
resolution/representative products, executable policy contexts, producer/trust binding,
coverage/standing/query payloads, walk order/cursors and evaluator split-decision operations.
Do not independently author lists or interpret old fields under new defaults. Only changed
contracts need version movement; do not bump unrelated dependencies or promise arbitrary old-runtime
execution.

For each delivered contract slice, the responsible feature owner and AC13 must:

1. Identify the producer, released declarations/compiled products, native acceptance boundary,
   persisted forms, query/materializer and all live CLI/MCP/export/automation/policy consumers.
   Use actual source inventory, not an illustrative fixture as the migration boundary.
2. Prepare the replacement from one pinned release/cut and binding. Independently specify what
   the new form means and which old forms remain readable. Migrate the current consumers in the
   same coherent delivery; remove displaced literal classifiers, projections and public methods
   after adoption. Required examples include AC06's four reader callers and AC08's queue/policy/
   packet/automation routes, not merely schema publication.
3. Author forward migrations from the confirmed frozen predecessor. Keep historical migration
   bodies, native99, native100 and any subsequently frozen native101 bytes immutable. Use existing
   admission and exact native descriptors, including overloads, security mode, owner, EXECUTE
   roles and SQL body/dependency binding. A transient dirty101 defect is a readiness question,
   not authority to rewrite predecessor history or open broad M1 repair scope.
4. Prepare/rebuild only affected derived artifacts and versioned query/read products. Old bytes,
   reference/grade outputs and source coordinates retain their recorded meaning. New source
   attributes must not manufacture old evidence; new split provenance must not invent historical
   seeds/populations/reasons. Legacy unavailable provenance remains explicit.
5. Publish through existing protected reconciliation, attempt/source/release fences and atomic
   visibility. Current-only execution compatibility stays explicit. Preserve supported immutable
   reading without executing changed preparation under an archived binding. An incompatible old
   request, result, cursor, cached artifact or producer protocol is refused or explicitly
   reselected, never silently rebound. Cross-call evidence and export retain the original pin.

Intermediate releases must be internally coherent: a new source shape cannot be accepted before
its native enforcement and current consumers understand it. Private preparation may proceed early;
visibility waits for that slice's complete premises. If execution is interrupted before visibility,
leave the previous published selection usable and inspect/replay the existing exact intent. An
uncertain commit resolves through the existing receipt/fence owner. Do not add a second rollout,
certificate, deployment registry or dual-writing pipeline for this local operator deployment.

AC09 retains inference inside atomic publication initially. Its prepared candidate indexes and
delta frontier remove repeated work while the same transaction still protects the fixed point,
direct witnesses and coherent result. AC13 must not move inference outside the transaction as a
release convenience; that needs a complete immutable prospective-input contract and revision fence
that this plan does not select. Other private model/source work stays outside publication locks.
AC07 keeps per-task terminal durability; atomic visibility of an assembled result does not turn
all task completion into a single all-or-nothing batch.

### I04 — Establish the native foundation this new scope actually consumes

Before AC authoring/admission or native consumer qualification, inventory the current source
revision plus dirty paths, the actual Alembic head/predecessor, frozen native inventory/admission
files, generated functions/guards and the owned test/deployment database's installed state.
Specifically reconcile forward101's source declarations, normalized bound bodies, native inventory
and admission descriptors with the current `native_candidate`/`native_inventory`/`native_sql_body`
implementation. Include missing-report/report-presence behavior where the new consumer contracts
depend on it. A source hash or collected test node is insufficient to establish installed agreement.

The outcome is a concrete supported predecessor and working author/install/admit route for AC's
new scope, with bounded repairs scheduled under the responsible existing or new owner. Exercise
an owned fresh/bare installation and supported predecessor-forward transition to settle the actual
route, plus exact drift/refusal controls where changed. If forward101 is still draft, coordinate
its owner before freezing or depending on it. If already frozen, preserve it and use the next
forward route. Do not assume the file name proves readiness. Missing server/principal/artifact
prerequisites block only work that needs them; pure contract work may continue.

I04 does not resume the paused M1 qualification campaign, close M1-11/12/13/14, repair every old
native issue or demand completion of another plan. Native99 history and prior UM standing remain
intact. Any independently required M1 acceptance still belongs to its later revised coordinator.
DA-032/033 retain current deployment history, independent catalog/role/cross-row checks and
NOLOGIN publisher trust. Reopen only a concrete diagnostic-consumer need or a demonstrated
trust/concurrency/admin-drift premise change; this plan creates no blanket assurance-reduction task.

**AC13 completion evidence:** each changed ABI has independent meaning expectations, supported
historical reading or explicit incompatibility, and actual migrated producers/consumers. Native
fresh/forward installation, invocation/admission, rollback/replay and drift refusal cover the
specific changed functions, descriptors, roles and constraints. A populated old/new pin journey
must refuse mixed revisions/cursors without changing historical bytes. Pure generated-schema
agreement does not substitute for the real native and transport path.

## AC14 — Qualify the assembled correction and prepare the M1 handoff

**Required input:** complete selected AC00–AC13 functional scope and consumer migrations,
settled I03 trust premises, I04's working native foundation, and independent expectations/reference
inputs for the affected semantics. A missing real provider, supported native server/principal or
actual consumer attachment leaves that required obligation open; it is not satisfied by a mock.
The accepted dedicated managed-recognition route is required: an I03 binding failure leaves that
support and its real-provider acceptance obligation open/blocked on the missing prerequisite.
Manual or unmanaged evidence retains its weaker truthful meaning and does not waive managed
acceptance; narrowing the accepted target requires an explicit operator scope decision.

At implementation endpoints use compile checks and focused functional/native tests for the
changed capability. No package automatically starts a broad campaign. Once all selected functional
scope is implemented, the root performs the last source maintenance with `just turn-end`, then
records the final source and relevant context for qualification. Run `just test-all` and applicable
`just hygiene` against that final source/context. If hygiene makes source changes, reassess and
rerun affected functional evidence; a pre-mutation receipt cannot silently become final evidence.
Record `rustc --version` with Rust results and use the workspace default toolchain/release-nextest
route. Run `just ready` only when its environment/dependency/process-change trigger applies.

The required union is the following behavior, not a sum of overlapping test counts. The integrator
maps it to exact selected native/provider/consumer nodes and actual journey commands before the
campaign, using the existing receipt/applicability machinery rather than a new acceptance registry.

| Required scope | Discriminating evidence and actual path |
|---|---|
| Released authority, attributes and rules: AC01–AC05 | Independently authored subset/role/value/attribute cases, source-derived refusal versus valid derived inference, nested enum/expression/range projection, qualified supports, ambiguous/cyclic/provisional identity and deterministic representative behavior. I01 qualifies the supported Unicode/runtime/collation pair using relevant mappings and independent non-ASCII cases; samples are not universal parity proof. Structured reasons stay machine-readable and programming failures do not become successful undecided. Generated Python/native products must enforce the same released meaning without deriving all expectations from that generator. |
| Source effects and producers: AC06–AC08 | Unsupported policy refuses before tasks; all four owned-reader routes; actual persistent-write refusal; slow whole-lifetime claims, forced renewal/terminal/uncertain-commit/reclaim races and per-task durability; two compatible producer bindings; actual managed recognition generation binding/replacement and truthful manual/provider-reported routes. |
| Preparation and inference: AC09 | Independently specified cycles, self-loops, reconvergence, mutual rule enabling, contexts and distinct direct witnesses for the same conclusion; self-excluded symbols and preserved universe; native atomic rollback and exact replay. |
| Answer/evidence/walk consumers: AC10–AC11 | Populated native facts with rejected, ambiguous, unassessed and conflicting standing; zero-output incomplete coverage versus established absence; missing producer reports; bounded inventory/evidence/source access; large payload/early close/cancellation; cyclic parallel-edge high-degree walks with work exhaustion before output; exact pin and cursor incompatibility. Exercise actual CLI, MCP tool/resource/continuation and export routes, including a default/selection change mid-journey. |
| Evaluator provenance: AC12 | Protected native assignment with actual seed override/frozen policy/population/reason, exact replay versus conflicting decision; explicit legacy unavailable provenance. Preserve evaluator isolation, immutable historical grades and M1's separate origin/sample meanings. |
| Release and recovery: AC13 | Fresh and supported predecessor-forward native transitions; installed normalized body/dependency/role agreement, native rejection under wrong principal/drift, coherent publication, cancellation/uncertain outcome/replay and old-product reading or explicit incompatibility across each affected actual consumer. |
| Applicable nonfunctional and source integrity | Applicable typing/lint/dependency/documentation/Rust checks after complete scope, resource ownership and failure cleanup. Assess ordinary intact-source and skewed-degree physical routes; do not claim measured capacity, latency or RSS without measurements. |

Reuse `python/corpus-structure/tests/semantic/` native lifecycle and scenario helpers and existing
orchestration, recognition, intervene, serving and evaluator consumers. Exact focused starting
routes include `uv run pytest python/corpus-structure/tests/semantic/test_native_inventory.py
python/corpus-structure/tests/semantic/test_record_migration_native.py` for the I04/AC13 seam,
with migration/admission nodes selected for the confirmed predecessor; native99/100 coverage is
not inferred from these two names. Extend actual journey tests such as
`test_pdf_native_consumer_journey.py`, existing CLI/MCP/export tests and new ordinary-answer
cases where their contracts change. Inventory the actual names and application commands at
execution time; do not report a named-but-unrun test as a capability. Broad commands remain
`just test-all` and applicable `just hygiene`, with required external journeys supplied separately
when those recipes do not exercise them.

Retain failed and interrupted receipts unchanged, and record actual command, date, source and
context for `passed`, `failed`, `blocked` (missing prerequisite) or `not_run`. The runner's native
context metadata is necessary for native applicability; collection, a skipped provider, a detached
mock or schema-only pass does not establish it. Union coverage must be assessed against the same
declared final source/context; rerun affected obligations after source/harness/shared configuration
or provider-generation drift. Use existing evidence records for accepted investigations and
benefit measurements. No additional numerical cost model or proof machinery is selected.

### Completion boundary and M1 impact handoff

Complete this new series first. AC14 then writes the impact handoff **inside the new coordinator**,
with the concrete released versions/native predecessor, corrected contracts and downstream changes
M1 must consume; preserved UM/PDF/test-series standing; exact qualified scope and unresolved
prerequisites; and the order for separately revising the M1 coordinator and every affected
companion. The handoff must identify evidence invalidation and requalification needs by consumed
contract, rather than claim all prior M1 results invalid or all M1 acceptance satisfied.

Likely affected M1 responsibilities include field/attribute evidence and admissibility; owned
source reads and lifetime; producer protocol/trust identity; native bindings/publication;
record/ordinary-query standing, coverage and source retrieval; evaluator split provenance; and
actual consumer/qualification prerequisites. These are input categories for the concrete handoff,
not edits to M1 or automatic new M1 scope now. After new-series completion, separately revise
M1's coordinator/companions from that handoff, then resume M1. Preserve failed/interrupted M1
receipts and keep its independent references, statistical release gates, actual CPU/provider
journeys and operational adoption boundaries with M1's owner. This series neither reruns the
paused campaign as I04 nor promotes source corrections into a qualified M1 release.

DA-011's current architectural/compiler/compatibility guidance is reconciled from the final
implemented contract through AC00/AC13, with dated maturity and historical labels. Enduring
semantics move into their existing D2–D8 owners; accepted ADRs remain immutable and superseding
decisions follow the established route. Plans and evidence remain retained. Qualification closes
only the declared AC union; quantitative benefits and unrelated providers or invariant breadth
remain unclaimed unless independently measured/exercised under stated conditions.

## Library realization and authoring verification

Carry the review's **Interface-checked** mechanisms into AC13 rather than repeat broad library
selection. Alembic1.20.1's `MigrationContext`/operations and custom `NativeTransitionOp` provide the
existing frozen/forward route; [autogenerate limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
mean generic defaults are not authority for CHECK/function completeness. Existing
`prepare_native_authoring`, normalized `NativeObject` admission and predecessor inventory own
the missing native semantics. SQLAlchemy2.1.6 transactions and PostgreSQL18 native row locks/fences
protect visibility/replay; [read transaction modes](https://www.postgresql.org/docs/18/sql-set-transaction.html)
and [SQLAlchemy connection source](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/connections.rst)
bound the actual guarantee. Streaming/`yield_per`/partition closure can bound buffering but do not
bound recursive query work; AC11's indexed bounded frontiers own that separate correction.

No dependency change, provider run, native operation, product test or broad check was performed
for plan authoring. The root owns plan integration, final maintenance and handoff. Target behavior
and benefits remain **Proposed** until their scoped native/provider/consumer evidence exists.
