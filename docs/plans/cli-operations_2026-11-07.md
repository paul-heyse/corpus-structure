# CLI operations and managed results

**Status:** Executing. Installed operations and targeted evidence are recorded below. Owns the CLI
operations target, execution queue, and dispositions for O01–O07 and I01–I10.
**Created:** 2026-11-07. **Revised:** 2026-11-07.

## Outcome and baseline

Make installed `ci` sufficient for routine development and production work, including source and run
operations, repeatable model changes, migrations, testing and verification. A prepared checkout
needs a single activation path. A command asks for operands that select meaning or authorize an
effect. It resolves workspace, prerequisites and delivery through existing owners. Test, native
candidate and export results become retrievable by identity with a defined lifecycle.

Planning consumes the [CLI functional extension review](../functional_reviews/typer-cli-target_2026-11-07.md)
as committed at `f8c76f767`, including its inspections of product baseline `025da5721` and
five recorded operator journeys. Static authoring inspected the CLI registry, settings, test supervisor,
change classifiers, native candidate and publication paths at `f8c76f767`. The review's dated
installed smoke checks establish that help can run with invalid application settings, native candidate
and review export require destination arguments, `ci test` is absent, and an unknown option under
`--json` exits 2 with stderr text. Current implementation and verification claims remain with their
owners. The entire design below is **Proposed**.

This revision integrates the [CLI improvement review](../plan_improvement_reviews/cli-operations_2026-11-07.md)
at `aae1f5429`. Typer 0.27.3 remains the repository baseline. Typer 0.28.0 is the target. The
2026-11-07 isolated comparison covered selected installed help, usage and generated reference plus
option, completion and callback fixtures. The same evidence records a Tree-sitter query progress
callback failure on binding 0.26.0 with Python grammar 0.25.0. These results inform the plan within
their probe scope. [CLI library evidence](../design_review/evidence/2026-11-07_cli-typer-028/README.md)

## Foundation and target

| Existing foundation | Reuse and needed change |
|---|---|
| Explicit Typer registry, lazy `CliState`, settings provenance and typed failures | Keep registration explicit and operation imports lazy. Resolve context once per invocation, move duplicated CLI effects into their actual owners where needed, and distinguish input usage, refusal and execution outcomes. D8 owns the public surface and D9 the development and production workflow. |
| Receipt supervisor, native test isolation and evidence classifier | Keep process and evidence semantics at their current owner. Expose selection, execution, retry and classification by identity. An installed developer command may invoke the established checkout entry point with a supervised argument vector. |
| Core/system declaration classifier, prepared semantic comparison, native authoring and deployment owners | Reuse the two levels of comparison. Split prepare from writes in the local generator, freeze inputs for native authoring, and recheck the applicable predecessor and authority at each effect. D2 owns semantic identity and D3 database authority. |
| PostgreSQL project, run and cut state, exact review closure and no-replace publication | Compose explicit continuations and retained reads. Add managed local delivery and custody while the domain owns run state, source, data and semantic selection. D6 owns supervision and D8 the delivery contract. |

A managed result records an invocation and its minimal recoverable output. Its references may name
authoritative runs, cuts, releases or evidence. A result ID stays stable across copies. A retry owns
a new invocation and references the original. One CLI rendering convention projects the typed result
to a terminal or JSON. Diagnostics help the operator choose an action using existing status,
receipts and refusals. Optional retained diagnostics belong to the managed result. Published
evidence and database state keep their existing custody and authority. [D2 model](../design/D2-schema-and-guidelines.md) · [D3 database](../design/D3-database.md) ·
[D6 orchestration](../design/D6-orchestration-metrics-policies.md) · [D8 interfaces](../design/D8-agent-and-query-interfaces.md) ·
[D9 workflows](../design/D9-repository-and-phase0.md)

**Proposed foundation judgment (A1–A4).** Typed operation contracts preserve the distinction between
intent, authority, effect and output across CLI, Python and selected MCP consumers. A new renderer
can reuse the same outcome and a new result producer can reuse custody without moving its domain state.
One explicit workspace resolution and lazy acquisition keep help and short reads cheap. A compact
manifest and bounded page-oriented discovery suit a single operator. The physical work still includes
directory enumeration, child-process collection and, for an exact export, closure traversal. Reassess
discovery only if retained populations or repeated lookups make enumeration material. Use the supervisor
and PostgreSQL owners at their native boundaries, staging only applicable changes and checking fences
before writes. Generic workflow engines, automatic persistent discovery indexes, generated second CLIs
and full-screen terminal applications have no identified workload in the review.
[Design principles](../design_review/design_principles/core/design-principles.md) ·
[Execution-fit heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md)

## Decisions and ownership

The functional extension review names three rule impacts without IDs. The planning IDs below give them stable references.
The operator settled each during authoring on 2026-11-07. The adopted decisions below govern this
proposed implementation. CLI-00 schedules durable owner changes ahead of affected implementation.

| ID | Operator decision and consequence | Adoption route |
|---|---|---|
| CLI-RC01 | **Accepted with amendment.** Installed `ci` is the single normal interface. Existing repository automation keeps its current classes of work in `just`. The corresponding `ci` commands invoke owned `just` recipes. Product operations call their application owners. Bootstrap and recovery can still invoke their underlying tools. | Update D8, D9 and operator instructions. Use the workflow ADR route if a binding decision changes. Retire obsolete duplicate entry points and placeholders after migration, preserving `just` as the recipe owner. |
| CLI-RC02 | **Accepted with amendment.** Ordinary successes expire after one day. Failed and interrupted results expire after one week. Protect active producers and exports, pending candidates, and named qualification or review dependencies. Cleanup is confined to managed derived outputs. | Adopt through D8/D9 and any affected custody decision before enabling deletion. Use the expiry windows for unreferenced settled results. |
| CLI-RC03 | **Accepted.** Require an inspectable preview and apply by exact preview ID. Deployment requires explicit intent and a bound target. Make activation and selection explicit. Keep purpose roles, native transaction guarantees and predecessor/activation fences. | Update affected D2/D3/D8/D9 owner sections and use the existing ADR route for altered binding decisions before CLI-05. |

The [test audit resolution](test-audit-resolution_2026-11-05.md) owns the test substrate and
qualification semantics. The [WCE plan](witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)
owns corpus findings and prior repair receipts. Use a retained compatible WCE cut for a CLI journey
where available. WCE12 remains separately owned. Treat the observability plan as cancelled for this series.
CLI-01 owns safe presentation, CLI-02 owns bounded diagnostic retrieval and retention, CLI-03
supplies test receipts and CLI-06/07 supply existing product and host outcomes. LOG packages
are historical context. Prior [logging investigations](../design_review/evidence/2026-11-01_logging-events-history/README.md)
supply scoped evidence about library options. The existing [evidence owner](../design_review/evidence/README.md)
governs deliberate promotion and durable retention.

## Execution queue and coverage

CLI-03 is the first end-to-end exercise of the CLI-02 custody and diagnostic contract. Reuse its
working contract for native candidates and exports. Pure model preparation in CLI-04 can proceed
from the declaration and release owners while the managed-result slice is underway.

CLI-00 carries accepted shared rules into their owners and obtains the design/target review
at the first substantial stage. A bounded slice uses change/target
review under the accepted contracts.
Before another substantial stage, changed authority or §B decision, and at the assembled boundary,
apply the [repository review cadence](../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository).

| Package | Owned delivery | Required input |
|---|---|---|
| CLI-00 | Adopt CLI-RC01–03 in affected authorities, and establish review scope and cutover policy. | This proposal and relevant D2/D3/D6/D8/D9 contracts. |
| [CLI-01](cli-operations/command-context-output.md#CLI-01) | Typer 0.28.0 transition, then command routing, lazy context and safe output on an existing operation. | CLI-00 routing decision and settled shared boundaries. Installed command migration follows the qualified pin slice. |
| [CLI-02](cli-operations/managed-results-and-testing.md#CLI-02) | Managed invocation identity, publication, custody and diagnostic retrieval. | CLI-RC02 adopted for expiry and deletion. CLI-01 output contract for installed adapters. |
| [CLI-03](cli-operations/managed-results-and-testing.md#CLI-03) | Installed test and maintenance operations, first full managed result and diagnostic journey. | CLI-01 and working CLI-02 creation/retrieval, existing test supervisor and policy. |
| [CLI-04](cli-operations/model-change-and-deployment.md#CLI-04) | Typed declaration preview and local-vs-archived semantic comparison. | Existing declaration and prepared-release classifiers. Installed preview uses CLI-01 and the CLI-02 custody contract first exercised in CLI-03. Pure preparation is independent. |
| [CLI-05](cli-operations/model-change-and-deployment.md#CLI-05) | Apply preview, prepare native candidate and compose explicit deployment. | Accepted CLI-RC03, working CLI-04 and candidate custody from CLI-02. |
| [CLI-06](cli-operations/corpus-and-operations.md#CLI-06) | Corpus and run journeys, shared refusal meaning, explicit read purpose and exact export. | Existing project, supervision and export operations and CLI-01. Managed export consumes CLI-02 custody after its first exercise in CLI-03. Discovery and closure analysis can start independently of CLI-05. |
| [CLI-07](cli-operations/corpus-and-operations.md#CLI-07) | Health, host and release actions, caller cutover and retirement. | CLI-01/03/05/06 replacements as each caller migrates. Conditional backup/restore is separately gated. |
| [CLI-08](cli-operations/corpus-and-operations.md#CLI-08) | Verify the assembled developer and production journeys, publish and hand off. | Integrated selected scope and same-source/context acceptance evidence. |

| Review opportunity | Scheduled disposition and closure |
|---|---|
| [O01](../functional_reviews/typer-cli-target_2026-11-07.md#O01) | CLI-00/01/07. Command inventory resolves every routine route and its actual caller migration, default and effect. |
| [O02](../functional_reviews/typer-cli-target_2026-11-07.md#O02) | CLI-01/07. Fresh-shell activation, isolated workspace resolution, redacted provenance, and explicit service effects. |
| [O03](../functional_reviews/typer-cli-target_2026-11-07.md#O03) | CLI-02/03/05/06. Destination-free test, candidate and review export with exact custody, holds and safe cleanup. |
| [O04](../functional_reviews/typer-cli-target_2026-11-07.md#O04) | CLI-03/08. Full applicable default selection, explicit unavailable lanes, original failed receipts and scope-correct reconciliation. |
| [O05](../functional_reviews/typer-cli-target_2026-11-07.md#O05) | CLI-01/03/07. Installed usage/result separation, supervised progress, generated command reference and stable machine output. |
| [O06](../functional_reviews/typer-cli-target_2026-11-07.md#O06) | CLI-04/05. Preview, applicable effects, recovery and predecessor checks. Select a codemod only for a qualified recurring transformation. |
| [O07](../functional_reviews/typer-cli-target_2026-11-07.md#O07) | CLI-06/07/08. Exact retained closure, correct authority and release state, actionable missing fitting prerequisites and privileged operations. |

### Improvement review dispositions

| Item | Disposition and owner | Closure or adoption condition |
|---|---|---|
| [I01](../plan_improvement_reviews/cli-operations_2026-11-07.md#I01) | Scheduled · [CLI-01](cli-operations/command-context-output.md#typer-0280-transition). | Qualify exact pin, installed grammar, help and reference generation before command migration. |
| [I02](../plan_improvement_reviews/cli-operations_2026-11-07.md#I02) | Scheduled · [CLI-01](cli-operations/command-context-output.md#CLI-01), consumed by CLI-03/07. | Verify typed intent, harmless completion and literal, policy-checked recipe forwarding. |
| [I03](../plan_improvement_reviews/cli-operations_2026-11-07.md#I03) | Scheduled correction · [CLI-01](cli-operations/command-context-output.md#safe-output-and-progress). | Verify redaction, terminal-control handling and JSON/exit isolation before migrating consumers. |
| [I04](../plan_improvement_reviews/cli-operations_2026-11-07.md#I04) | Scheduled · [CLI-03](cli-operations/managed-results-and-testing.md#CLI-03). | Verify authentic cancellation, isolated receipts and exact retry coverage across concurrent campaigns. |
| [I05](../plan_improvement_reviews/cli-operations_2026-11-07.md#I05) | Scheduled · [CLI-02](cli-operations/managed-results-and-testing.md#CLI-02), first exercised in CLI-03. | Verify settlement, held/expired identities, publication and concurrent export/GC before reuse. |
| [I06](../plan_improvement_reviews/cli-operations_2026-11-07.md#I06) | Scheduled correction · [CLI-04/05](cli-operations/model-change-and-deployment.md#CLI-04). | Rejected revision leaves all files unchanged. Native effects remain exact, explicit and resumable. |
| [I07](../plan_improvement_reviews/cli-operations_2026-11-07.md#I07) | Scheduled bounded discovery with conditional tool alternatives · [CLI-04](cli-operations/model-change-and-deployment.md#introspection-and-edit-decisions), consumed by CLI-05/07. | Exercise provenance, coordinates and coverage. Evaluate ast-grep-py or Tree-sitter only for the specified workload. |
| [I08](../plan_improvement_reviews/cli-operations_2026-11-07.md#I08) | Conditional · [CLI-04/05](cli-operations/model-change-and-deployment.md#introspection-and-edit-decisions). | Adopt LibCST only for a recurring, explicitly mapped qualified rename that passes independent patch and ambiguity controls. |
| [I09](../plan_improvement_reviews/cli-operations_2026-11-07.md#I09) | Scheduled · [CLI-06](cli-operations/corpus-and-operations.md#shared-refusals-and-read-authority) and CLI-07/08. Remote artifact resource remains conditional. | Verify shared refusal meaning, read purpose, transport-specific UTF-8 bounds and exact export. |
| [I10](../plan_improvement_reviews/cli-operations_2026-11-07.md#I10) | Scheduled receipt-first diagnostics · [CLI-02](cli-operations/managed-results-and-testing.md#action-driven-diagnostics), projected by CLI-01 and supplied by CLI-03/06/07. | Demonstrate the correct next action by result ID. Optional capture, structlog and service logs require the consumer and value cases in their owning packages. |

Conditional investigations stay beside their consumers. CLI-02 owns lookup/index and expiry-marker
triggers. CLI-01 owns any later structured usage-error envelope. CLI-04 owns the conditional
introspection and edit tools. CLI-07 owns the backup/restore decision. CLI-06 reports unavailable
fitting inputs through the existing capability and leaves their creation with the producer/assessment
owner. Each investigation states the evidence and the decision it changes. Optional mechanisms remain
outside the required qualification union until selected.

## Completion and evidence

Focused verification belongs to each package. CLI-08 owns the assembled installed journeys and the
declared functional/provider/nonfunctional union on the final source and applicable contexts. Record
original failures, exact replacement coverage, and unavailable required lanes. A prior WCE receipt
establishes its dated scope and can supply retained inputs. This CLI plan adds no requirement to
re-extract sources to verify retained reads or delivery. Observe repeated friction again after use if
benefit assessment is warranted. No timing or disk-savings claim is made at authoring.

**Initial authoring verification, 2026-11-07.** `just docs-check` passed for the original plan publication.
The installed `typer --app app corpus_structure.cli.app utils docs --name ci` command passed
with an intentionally invalid database URL. `just --justfile "$PWD/justfile" --working-directory
"$PWD" --show test-all` passed, inspecting the existing recipe without launching tests.

**Revision verification, 2026-11-07.** `just docs-check` and `just turn-end` passed.
Product qualification is `not_run` for the documentation revision.

### Execution disposition · 2026-11-07

ADR-0069 adopts CLI-RC01–03. The [initial target review](../design_review/reviews/design_review_cli-operations-target_2026-11-07.md)
and [assembled review](../design_review/reviews/design_review_cli-operations-assembled_2026-11-07.md)
set the evidence boundary. The sections below own the package-level evidence and remaining work.

| Package | Current implementation and evidence |
|---|---|
| CLI-00 | Adopted under ADR-0069, D8 and D9. Initial and assembled target reviews recorded. |
| CLI-01 | Installed Typer 0.28.0 with a workspace resolver override for the Docling Core CLI constraint. `just ready` passed. Existing Python Docling consumer and managed CLI controls passed on the pin slice. |
| CLI-02 | Installed managed result publication, second-process lookup, explicit holds, one-day/seven-day GC policy, no-replace delivery and bounded watch. F01 corrections include recovery protection and unsettled child custody. |
| CLI-03 | Installed `ci test` routes ordinary and exclusive native lanes through `just`, retaining actual pytest-xdist and nextest ownership. Scoped forwarding passed. The first full campaign `fab86740c6c44d4187c3d105e87876a0` was interrupted after a source edit changed the runtime pin. The child group settled. This receipt supplies cancellation evidence. |
| CLI-04 | Shared declaration validation, inspectable preview, archive comparison and bounded AST/ast-grep discovery implemented. F02 binds the reviewed prepared release before candidate authoring. |
| CLI-05 | Exact apply and recovery, managed rollback-only native authoring and registered deployment implemented. Development candidate `1551a8ce2e5845679c459d8fdf86bc91` ran on `corpus_structure_dev`. An isolated PostgreSQL test passed interruption after migration, replay, admission and separate activation. F02a owns the remaining distinct-target and registration journey. |
| CLI-06 | Installed ingest and run continuation, read-purpose status, native review export, shared CLI/MCP refusal and replay binding implemented. Retained run 205/cut 283 exported and verified detached without extraction. F04/F05 assembled controls are being qualified. |
| CLI-07 | Added read and explicit maintenance health, release check and activation, host recipe routes and current README examples. The installed registry removed inert commands. Reader status and maintenance revision passed against 18/corpus. |
| CLI-08 | Assembled review and qualification in progress. Final source, context and required selection must be reconciled before closure. |

The PostgreSQL tooling review selected installed `psql` for maintenance diagnosis and the existing
template-backed native fixture for exact predecessor testing. `psql -X -w -p 5434 -U paul -d corpus_structure_dev`
read `semantic_wce_lineage_20261107`; `uv run ci db status --maintenance --json` agreed. The ordinary
reader reports the migration revision as private. Dedicated-cluster status passed through
`uv run ci host status --json`. Backup/restore remains conditional on a recovery scope and owner.
[Tool inventory](../libraries/postgresql/system-tool-usage.md) ·
[Ubuntu tooling options](../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md#87-ephemeral-database-state-cloning-and-migration-testing)
