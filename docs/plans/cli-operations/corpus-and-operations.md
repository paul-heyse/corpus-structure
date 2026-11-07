# Corpus journeys, production operations and adoption

**Accepted target.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns CLI-06 through CLI-08. D6 owns run/task supervision, D3 owns target and purpose roles,
D8 owns source/read/export interfaces and D9 owns developer and production tooling.

<a id="CLI-06"></a>
## CLI-06 · Operate on selected source and retained corpus results

Expose ordinary `ci project init`, `ci ingest`, `ci run`, `ci run status`, `ci run cancel RUN`
and `ci run finalize RUN` journeys through the existing project, source preparation, task
and publication owners. Start from the installed orchestration routes and shared application
functions such as `cancel_bound_run()` and `finalize_bound_run()`. Retain idempotent project
creation and compatible source reuse. Resolve a configured project/profile and its declared
default scope once. Require project or corpus identity for new or ambiguous targets. Keep a
meaningful selector, source locator or realization identity required when it determines the
effect. Distinguish ongoing and orphaned attempts, a completed cut, private proposal,
unavailable prerequisite and published result. Resume by exact binding. A plain read can select
the declared eligible completed/promoted result once and show that identity. Cancel, finalize,
admit and promote require unambiguous effect targets. A discovered latest attempt can support
inspection, while effects use the explicitly resolved selection.
[Current orchestration adapter](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py) ·
[Run authority](../../design/D6-orchestration-metrics-policies.md)

### Shared refusals and read authority

Use the existing query, source, structure, contributions, evaluation and review operations.
`NativeSourceRequest` and `inspect_native_source()` supply the reference contract. The
CLI and MCP currently project overlapping refusal fields separately. Construct the safe
refusal fields once at the semantic owner, then use the CLI typed JSON/exit and FastMCP
`ToolError` protocol adapters. Preserve the owned code, applicability and remedy in each.
For source inspection, resolve the read purpose explicitly. The current MCP read-only
snapshot uses the write-purpose queue pool. Use a read-purpose connection for pure reads
and retain the separate queue purpose for work actions. Resolve project, semantic result
and scope once. Authorization and exposure remain with the application read and export owners.

Preserve FastMCP **4.1.3** `ToolResult` structured/text content and
`_bounded_mcp_result()` accounting for text, structured content and stamped metadata.
CLI budgets its own JSON body. A request may fit one transport and exceed the other.
Compare payload and refusal meaning across installed CLI and registered and fresh stdio
MCP at the exact UTF-8 boundaries. Use `Context.report_progress()` to project existing
events only when the request carries a progress token. For an actual remote consumer
of an already published artifact, investigate an exact-ID `@mcp.resource` URI template
with independent authorization and bounded reads. Publication and role checks remain
with the existing owner.
[Shared source operation](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py) ·
[Semantic refusals](../../../python/corpus-structure/src/corpus_structure/semantic/refusals.py) ·
[MCP budget and server](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py) ·
[FastMCP 4.1.3 ToolResult](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/fastmcp_slim/fastmcp/tools/base.py) ·
[Context progress](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/fastmcp_slim/fastmcp/server/context.py) ·
[Resource templates](https://gofastmcp.com/servers/resources)

### Exact export and continuation

For portable review export, add a named exact-closure selection
mode at the owner, using `ReviewSelection`, `capture_review_relations()`, `export_review_bundle()`
and `verify_review_bundle()`. Derive required retained predecessors under existing snapshot,
role and byte bounds. Report inclusion reasons, actionable missing/inaccessible dependencies
and budget refusals. Do not broaden the user's selection to all retained corpus data. Publish
a complete deliverable through the existing bundle writer and CLI-02 identity. Optional
external delivery is a copy of the settled result. Retry an interrupted export against the exact
completed cut, with a new invocation ID. An expired result or missing dependency does not
authorize new PDF conversion, recognition, fitting or other provider work. Where a fitting
request has no compatible events or protected evaluation, surface the current applicability
report and route remediation to its producer or assessment owner. Publish the operation's
outcome, settled effects and exact cut or missing dependency to the
[CLI-02 diagnostic view](managed-results-and-testing.md#action-driven-diagnostics).
[Source read owner](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py) ·
[Review closure and verification](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) ·
[Fitting availability evidence](../../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)

**Acceptance.** Use an existing completed corpus cut to inspect source and status, export
destination-free exact closure, independently verify the bundle and retrieve it by ID. Exercise
a missing scoped predecessor, a bound refusal, and an interrupted export retried from retained
data. Check through the provider boundary that retained reads start no new extraction.
Demonstrate ambiguity refusal for a mutating command and reconcile a genuine supported run
transition through the application owner. Test wrong run and denied role, read-purpose use
and unchanged queue capability. Compare an equivalent admitted read and a typed refusal
across CLI and MCP. Include a multibyte output that fits the CLI and fails the MCP budget.

<a id="CLI-07"></a>
## CLI-07 · Expose operations and migrate callers

Plan named health, database status/check/migrate and release check actions. Keep installed
product/database operations on their application owners. Use `semantic.migrations.upgrade()`, `current_revision()` and the native
revision checks and release admission/activation fences, with CLI-05 binding
where applying a change. Move callable logic out of CLI-specific glue only where composition
requires it. A read-only production purpose role can inspect allowed health and compatibility.
Installation, migration, admission and selection remain distinct and explicit. Verify the
declared target before privilege use. Redact credentials in context and receipts.
[Database adapter](../../../python/corpus-structure/src/corpus_structure/cli/db.py) ·
[Release owner](../../../python/corpus-structure/src/corpus_structure/semantic/releases.py) ·
[Purpose roles](../../design/D3-database.md)

For local development provisioning, role reconciliation, cluster service and status, invoke
the owned `just db-provision`, `db-semantic-roles`, `db-up`, `db-down` and `db-status` recipes.
Reuse the existing scripts and Ubuntu `pg_ctlcluster 18 corpus` mechanics. Preserve the
dedicated 5434 target and persistent `corpus_structure_dev` as the ordinary working database.
Use test databases only when isolation is part of the test. Target a production service only
through its separately resolved configuration and authority. A production read or help invocation
cannot implicitly install, synchronize, provision or start anything. Surface wrong target,
missing privileges, unexpected predecessor and partial deployment with exact remediation.
[Host recipes](../../../justfile) ·
[PostgreSQL Ubuntu tooling](../../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md) ·
[Ubuntu `pg_ctlcluster` reference](https://manpages.ubuntu.com/manpages/noble/en/man1/pg_ctlcluster.1.html)

For `ci doctor` and named status routes, project the existing owner checks with the resolved
target, role, failure and direct remedy. Investigate a bounded existing service-log read only
for a named operator who needs to distinguish a failure status misses. Select an explicit
source, privilege and read bound, and invoke the owned recipe for host work. Compare the
operator's next action with the status-only route before adoption. Apply the
[CLI-02 value and custody rules](managed-results-and-testing.md#action-driven-diagnostics).

Backup and restore are conditional. First identify the operator, source and database custody,
durable backup storage, recovery point/scope and intended restore target. Evaluate PostgreSQL
18 `pg_dump --format=custom` with `pg_restore` as a logical backup candidate. Verify role and
cluster-global requirements independently and rehearse the selected restore before exposing a
privileged effect. The logical route is appropriate only if it satisfies the chosen recovery
scope. Put domain recovery with its data and source owners. CLI result GC and ordinary result
export do not govern backup retention.
[PostgreSQL 18 dump](https://www.postgresql.org/docs/18/app-pgdump.html) ·
[PostgreSQL 18 restore](https://www.postgresql.org/docs/18/app-pgrestore.html)

Use the CLI-01 command inventory to migrate repository docs, agent instructions, examples,
operator scripts and other actual callers as their replacements become usable. Ingest, digest,
promote and other placeholder entries must either become truthful owned commands or leave
executable help with an opportunity reference in their owners. Remove replaced wrappers,
duplicate defaults, manual output requirements and other bypasses after their callers move.
Keep `just` as the same class of recipe owner under CLI-RC01. Remove recursive recipe-to-CLI
edges from the CLI-invoked call graph. Keep first-install and direct recovery documented.
Keep existing product routes whose meaning and consumer remain valid. Generate command reference
from the final registry. Apply corresponding D8/D9 and workflow changes through CLI-00 and keep
their published descriptions aligned at cutover.

**Acceptance.** Invoke a production status read with the intended role, refuse a local or
wrong target for a production write, and interrupt after migration before admission without
hiding the settled effect. Demonstrate recipe-backed host status separately from configured
production health. Verify no direct caller still needs a retired route, existing recipes remain
usable, and generated help represents the executable surface.

<a id="CLI-08"></a>
## CLI-08 · Qualify the assembled interface

Review the assembled stage using the repository's design/target cadence. Run the required union
on final source, declared scope and matching contexts through the owned recipes and installed
routes under test. Use targeted package checks during construction. Final qualification uses
`just test-all -n auto` and the applicable `just test-native-faults` lane, whether dispatched
through installed `ci test` or run directly to cover an explicit obligation. Run applicable
`just hygiene` and documentation checks. Preserve failed/interrupted receipts and distinguish
replacements, unavailable prerequisites and genuinely empty selections. Test real provider
and native interfaces where required by a changed capability. Use retained corpus inputs to
test exact reads and delivery. A mocked provider cannot establish provider qualification.

Use a fresh installed subprocess in a headless development checkout for context, help and
completion, zero-argument test, failed-test retry, coverage, model check and native candidate.
Use an actual redirected consumer for safe diagnostics and clean JSON. Exercise literal recipe
forwarding, concurrent receipts and cancellation, and use a second process for result hold,
export and cleanup races. Verify the correct next action by ID with a known failure and with
diagnostics unavailable. Cover rejected revision with zero writes, ambiguous source matches,
explicit model apply/recovery and real target-bound deployment roles. Exercise CLI/MCP refusal
meaning, purpose and exact UTF-8 bounds and detached verification of exact export on retained data. Record outcome, command, source and context for each selected obligation.
A failed or blocked required obligation stays open in the coordinator. Publish only the
evidence closure that remains useful after qualification.
[Repository acceptance policy](../../design_review/design_principles/binding/corpus-structure.md) ·
[WCE bounded repair evidence](../witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

### Completion audit follow-up

**F04 · Reader authority across MCP.** `find` and `inspect_source` use the reader, and the queue
writer opens lazily. Structural products, dossiers, contributions, records and record support
still resolve through the writer-backed `bound_run`. Even `queue_status` acquires the writer for
its reads. Compose the existing scope checks with reader snapshots for pure read paths, while
preserving the writer for leases and proposals. Verify the affected operations with a fresh
reader-only client, wrong-run and denied-role controls, and the existing writer queue journey.
Keep the 1,895-byte `find` wire result scoped to that operation and actual transport.
[MCP composition](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py#L556) ·
[Record and structural tools](../../../python/corpus-structure/src/corpus_structure/intervene/record_tools.py#L23)

**F05 · Exact interrupted export.** Retained native exports verify replay of a settled selection
and reject a changed connection route. Retry reads `selection.json` without checking a digest
bound to the first attempt, while the database binding hashes completed roots. A modified
selection over the same roots can pass. The adapter also lacks a SIGTERM settlement path. A
terminated capture can stay running, with its retained selection unavailable to retry. Bind the
exact selection and acquired source, make interruption/recovery truthful under managed custody,
and exercise an interrupted export, edited same-root selection, missing predecessor and retry
from retained data with no new extraction. The two successful manifests do not exercise
interruption.
[Export and retry](../../../python/corpus-structure/src/corpus_structure/cli/review.py#L20) ·
[Snapshot binding](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py#L966)

**CLI-CA04 · Source preparation and run lifecycle.** `ci ingest` still requires domain and
corpus even for an existing bound project and calls regeneration, which archives/adopts a release
before source preparation. This exceeds source-only intent and needs admission authority.
Resolve existing project/release/source defaults once and keep admission an explicit effect.
`run resume --prepare-only` can report `prepared` without checking the retained run state or
source-ready cut. Distinguish completed, source-ready, incomplete and terminal attempts before
choosing a supported continuation or refusal. Native orphan assessment remains open with the
run supervisor. Route expected run refusals through the common typed output boundary and test
the existing-project writer route and incomplete/cancelled/ambiguous attempts.
[Ingest adapter](../../../python/corpus-structure/src/corpus_structure/cli/orchestrate.py#L414) ·
[Regeneration](../../../python/corpus-structure/src/corpus_structure/cli/regenerate.py#L161) ·
[Run supervisor](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py#L372)

**CLI-CA05 · Fitting prerequisites.** The installed fit route requires a protected evaluation
before it can distinguish an unfit population. The retained WCE census establishes a particular
missing-input case and has no installed applicability route. Project the current missing-events,
missing-evaluation and unfit outcomes with remedies pointing to the producer or assessment
owner. Verify the unavailable frame without exposing protected assessments or starting fitting.
[Installed fit](../../../python/corpus-structure/src/corpus_structure/cli/eval.py#L198) ·
[Fitting owner](../../../python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py#L164)

**CLI-CA06 · Production target continuity and health.** Deploy selects an independent profile,
while database status/check and release check/activation/promotion use the base profile without
a selector. A same-identity operation can address development after a separate deployment.
Resolve explicit production target and purpose consistently through these installed routes,
surface the acquired target, and type wrong-target, missing-project and generation refusals.
Separately, local host status can print unreachable or mismatched extensions and still exit zero.
Make the recipe report the unhealthy outcome and its remedy. Exercise wrong-target and healthy/
unhealthy controls independently. Live deployment qualification remains blocked on the configured
service and authority. Keep the separate-target isolated PostgreSQL rehearsal as bounded evidence.
[Release actions](../../../python/corpus-structure/src/corpus_structure/cli/operations.py#L189) ·
[Database actions](../../../python/corpus-structure/src/corpus_structure/cli/db.py#L245) ·
[Host status owner](../../../scripts/pg_provision.sh#L56)

**CLI-CA07 · Caller cutover.** README and agent instructions cover several installed routes,
and `ci docs commands` can generate the command reference. The accepted routine route/caller
inventory and cutover are incomplete. The current purpose-role instructions still use a direct
`just db-semantic-roles` call although the installed host route exists. D7 still names the removed
`ci digest` route without a current disposition. Reconcile current operators, scripts and published
examples with the installed registry. Preserve historical labels and the direct bootstrap and
recovery paths. Attach an opportunity disposition to removed commands with current consumers.
[Purpose-role instructions](../../design/D3-database.md#unified-operation-realization) ·
[Digest description](../../design/D7-evaluation-goldens-outer-loop.md#81-the-digest)

**CLI-CA08 · Assembled acceptance.** The original ordinary and fault lanes and exact stdio retry
establish their declared 5,105-node union. A later replay product change has focused evidence.
The union does not establish the installed controls still called out here and in the companion
packages. Reconcile the affected required selections and contexts after the repairs, including
the authentic interrupted export, concurrent receipt ownership, generated-wrapper deployment
and failure remedies. Keep the live service prerequisite explicit. The audit adds no requirement
to re-extract sources or adopt conditional tooling.
