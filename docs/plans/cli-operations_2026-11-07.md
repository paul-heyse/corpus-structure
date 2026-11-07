# CLI operations and managed results

**Status:** Development repairs verified. CLI-05 and CLI-08 retain live production qualification,
blocked pending a configured target and effect authority.
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
owners. The proposed target is retained below. Current implementation and qualification are in
the [execution disposition](#execution-disposition--2026-11-07).

This revision integrates the [CLI improvement review](../plan_improvement_reviews/cli-operations_2026-11-07.md)
at `aae1f5429`. Typer 0.27.3 was the planning baseline for the move to 0.28.0. The
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
| [O01](../functional_reviews/typer-cli-target_2026-11-07.md#O01) | CLI-CA07 owns routine caller migration. |
| [O02](../functional_reviews/typer-cli-target_2026-11-07.md#O02) | CLI-CA01 owns provenance and workspace controls. CLI-CA06 owns operational target continuity. |
| [O03](../functional_reviews/typer-cli-target_2026-11-07.md#O03) | F01 and CLI-CA02 own custody and retention. F02a and F05 own candidate and export continuity. |
| [O04](../functional_reviews/typer-cli-target_2026-11-07.md#O04) | F03 owns selection and truthful reconciliation. CLI-CA08 owns remaining acceptance. |
| [O05](../functional_reviews/typer-cli-target_2026-11-07.md#O05) | CLI-CA01 and CLI-CA02 own safe output, progress and diagnostics. |
| [O06](../functional_reviews/typer-cli-target_2026-11-07.md#O06) | F02, CLI-CA03 and F02a own approved effects, discovery and native deployment. Codemod selection remains conditional. |
| [O07](../functional_reviews/typer-cli-target_2026-11-07.md#O07) | F04/F05 and CLI-CA04–06 own read authority, replay, run lifecycle, fitting and privileged operations. |

### Improvement review dispositions

| Item | Disposition and owner | Closure or adoption condition |
|---|---|---|
| [I01](../plan_improvement_reviews/cli-operations_2026-11-07.md#I01) | Verified in the locked checkout · [CLI-01](cli-operations/command-context-output.md#typer-0280-transition). | Exact pin, workspace override and bounded grammar/help/reference checks. Standalone resolution has no supporting receipt. |
| [I02](../plan_improvement_reviews/cli-operations_2026-11-07.md#I02) | CLI-CA01 and F03. | Verify typed intent, harmless completion and literal, policy-checked recipe forwarding. |
| [I03](../plan_improvement_reviews/cli-operations_2026-11-07.md#I03) | CLI-CA01. | Verify redaction, terminal-control handling and JSON/exit isolation in affected consumers. |
| [I04](../plan_improvement_reviews/cli-operations_2026-11-07.md#I04) | F03 and CLI-CA08. | Verify applicable lanes and exact retry context across concurrent campaigns. |
| [I05](../plan_improvement_reviews/cli-operations_2026-11-07.md#I05) | F01. | Verify substituted paths, settlement recovery, held/expired identities and concurrent export/GC. |
| [I06](../plan_improvement_reviews/cli-operations_2026-11-07.md#I06) | F02 and F02a. | Keep the verified zero-write refusal. Verify applicable native effects as exact, explicit and resumable. |
| [I07](../plan_improvement_reviews/cli-operations_2026-11-07.md#I07) | CLI-CA03. Tool alternatives remain conditional. | Exercise provenance, coordinates, compile-only validation and coverage through consumers. |
| [I08](../plan_improvement_reviews/cli-operations_2026-11-07.md#I08) | Conditional · [CLI-04/05](cli-operations/model-change-and-deployment.md#introspection-and-edit-decisions). | Adopt LibCST only for a recurring, explicitly mapped qualified rename that passes independent patch and ambiguity controls. |
| [I09](../plan_improvement_reviews/cli-operations_2026-11-07.md#I09) | F04/F05 and CLI-CA04/06. Remote artifact resource remains conditional. | Verify shared refusals, pure read authority and interrupted exact export. |
| [I10](../plan_improvement_reviews/cli-operations_2026-11-07.md#I10) | CLI-CA01/02 and F03. | Demonstrate the correct next action by ID. Optional capture, structlog and service logs require the existing consumer and value cases. |

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

| Package | Disposition and bounded evidence | Remaining owner |
|---|---|---|
| CLI-00 | **Complete.** ADR-0069 adopted CLI-RC01–03 in DESIGN, D8, D9 and operator instructions. | — |
| CLI-01 | **Complete.** Typer 0.28.0 and the workspace override passed the Docling Python consumer, grammar, help, completion and reference checks. The repair verifies winning setting provenance and safe output. | CLI-CA01. |
| CLI-02 | **Complete.** Managed publication, held and expired lookup, abandoned result recovery, authenticated retirement and durable evidence promotion passed. | F01 and CLI-CA02. |
| CLI-03 | **Complete.** `just` dispatches both lanes. Selection, exact retry, context reporting and missing-lane coverage passed their controls. | F03 and CLI-CA02. |
| CLI-04 | **Complete.** The shared declaration and physical compilers bind the reviewed effects. Structural discovery and compile-only checks have named controls. | F02 and CLI-CA03. |
| CLI-05 | **Development verified.** Exact apply, rollback-only candidate authoring, registration and isolated native interruption and replay passed. | CLI-CA08 owns live deployment, `blocked` on target and effect authority. |
| CLI-06 | **Complete.** Retained review replay, pure MCP reads, writer queue, source-only preparation, supervisor handoff and fitting applicability passed. | F04/F05 and CLI-CA04/05. |
| CLI-07 | **Complete.** Development and host health passed. Isolated native controls exercised deployment-profile reads and effects. Routine callers use the installed reference. | CLI-CA06/07. |
| CLI-08 | **Development verified.** Assembled review, applicable functional union and repository checks recorded. | CLI-CA08 owns live production qualification, `blocked`. |

The PostgreSQL tooling review selected installed `psql` for maintenance diagnosis and the existing
template-backed native fixture for exact predecessor testing. `psql -X -w -p 5434 -U paul -d corpus_structure_dev`
read `semantic_wce_lineage_20261107`; `uv run ci db status --maintenance --json` agreed. The ordinary
reader reports the migration revision as private. Dedicated-cluster status passed through
`uv run ci host status --json`. Backup/restore remains conditional on a recovery scope and owner.
Review replay binds the acquired libpq peer, database OID and completed roots. It also includes
PostgreSQL's system identifier where the purpose role can read `pg_control_system()`.
[Tool inventory](../libraries/postgresql/system-tool-usage.md) ·
[Ubuntu tooling options](../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md#87-ephemeral-database-state-cloning-and-migration-testing)

#### Earlier functional receipts

`uv run ci test --json` at product `88fd5d108` produced `53329800b8004ffcb55e29b991af2d1d`.
Ordinary pytest selected 5,097 nodes on 16 xdist workers, passed 5,093 and failed four stdio
assertions that still required eager writer acquisition. The serial fault lane passed all eight
selected nodes. Both lanes reported zero worker losses and settled child ownership. Nextest listed
zero Rust tests, recorded as `not_run`. Toolchain `rustc 1.101.0-nightly (2d20b42b8 2026-11-04)`.

The stdio assertions now check that startup has no writer, queue use acquires the writer role,
and early exit, cancellation, tool failure and completion still settle. `uv run ci test retry
53329800b8004ffcb55e29b991af2d1d --lane ordinary --json` recollected the original selection and
passed those four cases in `f00a8efcf0e8485abe8f77f3335c203f`. `uv run ci test coverage
53329800b8004ffcb55e29b991af2d1d f00a8efcf0e8485abe8f77f3335c203f --json` preserved the original
`failed` attempt and reported 5,105 required nodes covered, 890 native-required, zero unresolved.
Source differences between these receipts reflect documentation and the targeted test contract
change. The test bodies changed only in those four modes. Both receipts remain available by
managed ID. The later replay-fingerprint correction was exercised by a focused installed
campaign `ef669eabac224aea82bb5c900bdf4dd0` and the native export, replay and changed-route
refusal above. The 5,105-node union is scoped to the cited receipts and their source contexts.
Final review and custody checks passed 12 nodes under `uv run pytest -n auto
python/corpus-structure/tests/test_review_cli.py python/corpus-structure/tests/test_cli_managed.py`.
`just hygiene` and `just turn-end` passed.

## Completion audit

**2026-11-07 · inspected `789d6a640`, initially clean.** The audit covered the execution
disposition's delivered CLI-00–08 scope, including work reported implemented with bounded tests.
It used the four companion targets, ADR-0069 and the original and assembled review findings.
Independent read-only reviews followed the installed adapters through the owning recipes,
custody, native migration, PostgreSQL role and MCP consumers. The accepted retention periods,
ordinary `ci` route, `just` ownership and explicit effect boundaries continue to govern.

**Implementation at the audit baseline.** Rule adoption was complete and the installed journeys
were partial. Each companion retains the source diagnosis and acceptance control. The table
records the disposition after repair.

| Finding | Current disposition and repair owner |
|---|---|
| F01 | **Closed.** Publication and reads bind the owned entry. Substituted receipt members and unowned retirements refuse. Recovery requires positive child settlement. [CLI-02](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| F02 | **Closed.** Apply, candidate and deploy consume the exact approved preview, including the changed physical sources and release pin. [CLI-04](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| F02a | **Development verified.** Additive authoring, explicit retirement, exact wrapper execution, acquired target refusal and replay passed. CLI-CA08 owns live proof. [CLI-05](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| F03 | **Closed.** Keyword selection stays in the ordinary lane. Required lanes and outcomes survive absent or invalid collection. Exact retries use owner-verified evidence and report changed contexts. [CLI-03](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| F04 | **Closed.** Reader-only stdio passed queue status, structural products, dossiers, contributions, records and support. Wrong scope and denied role refused. Writer queue operations passed separately. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| F05 | **Closed.** Native capture settled after SIGTERM and replayed its exact selection. Detached verification passed. Same-root editing and a missing exact predecessor refused. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA01 | **Closed.** Winning settings provenance, lazy command discovery, literal Rich rendering and typed redacted output passed. [CLI-01](cli-operations/command-context-output.md#completion-audit-follow-up) |
| CLI-CA02 | **Closed.** Managed status includes exact settled-lane counts, bounded stream diagnostics and next action. The evidence owner finalizes provenance and file hashes that remain verifiable after managed expiry. [CLI-02/03](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| CLI-CA03 | **Closed.** Structural discovery joins declared consumers. Compile-only generated checks and physical/admission agreement passed. [CLI-04](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| CLI-CA04 | **Closed.** Writer-only default ingestion passed. PostgreSQL supervision distinguishes intentional handoff, active custody and orphaned work with a one-connection writer pool. Terminal resume refused. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA05 | **Closed.** Fitting applicability reports missing events, missing evaluation or an unfit population before fitting. Retained run 205/cut 283 reported zero compatible events and the producer action. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA06 | **Development verified.** The selected profile and acquired binding continue through status, check and selection effects. Unreachable and mismatched host health exit nonzero. CLI-CA08 owns live proof. [CLI-07](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA07 | **Closed.** Routine caller examples and the current command inventory were reconciled. Installed reference result `aa6fcb3af854446e9ec28050d38e95fd`. [CLI-07](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA08 | **Development verified.** The assembled assessment and reconciled qualification below apply to development and isolated native contexts. Live production qualification is `blocked` on configured target and effect authority. [CLI-08](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |

**Audit-baseline verification.** Reading the retained classifications independently reproduced 5,105 selected
nodes, 890 native-required, and zero unresolved in the observed union. The four replacement
IDs equal the four originally failed IDs. Both classification inputs have active holds. The
ordinary and fault lanes share product commit `88fd5d108`; their recorded worktree hashes differ.
The fault and retry contexts include the stdio test change. Later `review_bundle.py` product
changes have separate focused evidence. The result establishes its declared node set and native
acquisition coverage. It cannot establish absent required lanes or the open installed journeys.
Rust remains `not_run` with an empty selection. A new integrated campaign was `not_run` for this
audit. Bounded probes used temporary files or read-only commands.

| Audit check | Observed outcome |
|---|---|
| `uv run --no-sync python scripts/test_receipts.py validate-pytest --report-selection -- -k sample` | **Failed.** Returned `false` for a selector. `-q` also returned `false`; a test path returned `true`. |
| Installed `ci test coverage` with a temporary full-campaign result containing a passed ordinary receipt and failed fault lane with no artifact | **Failed.** Reported `passed` and `covered` over the 28 ordinary nodes. |
| `ResultStore.deliver()` with temporary manifest artifact `.` and `ResultStore.collect()` with an unrelated `.gc-<id>` folder | **Failed.** Copied private staging and deleted an unowned directory omitted from preview. |
| Installed `ci check --only lint --json` with a temporary child emitting a synthetic URI | **Failed.** The retained excerpt included the credential after the prefix was cut. |
| `CORPUS_GPU__MODE=__audit_invalid uv run --no-sync ci status --json` | **Failed.** Exit 1 with traceback and empty JSON stream. |

**Audit-baseline benefit evidence.** Installed commands already removed destination selection for the observed
tests, model candidates and review exports. The managed IDs make the recorded export and retry
journeys retrievable. Routine caller coverage and reliable next actions remain incomplete.
Quantitative time and storage savings were outside the accepted completion criteria. Optional
backup tooling, remote artifact resources, extra logging and additional codemod tools retain
their original adoption conditions.

### Repair verification · 2026-11-07

The [assembled repair assessment](../design_review/reviews/design_review_cli-operations-assembled_2026-11-07.md#completion-audit-repair-assessment) records the integration findings. ADR-0069 still governs. The development migration and authoring checks used persistent `corpus_structure_dev` on `18/corpus`, port 5434. Target-switching and interruption controls used isolated native PostgreSQL where an independent predecessor or role was necessary.

| Journey | Outcome and evidence |
|---|---|
| Managed custody, safe output and test grammar | `uv run pytest -n auto` over CLI, managed results and test supervisor passed 129 focused tests before the final affected selection. The controls exercised substitution, interrupted retirement, expiry, evidence retention, output redaction and missing lanes. Installed `uv run ci test --json -- -k test_recipe_redacts_before_clipping` passed ordinary only in `5710513a9d8245a59f675ec0c256bb8e`. The fault lane refused `-k`. The existing held full and retry receipts were imported under their original IDs, preserving the original failed outcome and covered selection. |
| Model authoring and deployment | Installed focused result `c18040cfc39e4bdfb82c0c177cc77c85` passed 43 tests, including reviewed effects, discovery, exact native interruption and replay, altered target and executable controls, and separate activation. A real installed preview, apply and rollback-only candidate `246dae08ce714974aca49c6bb1cb8532` authored a nullable `data.project` field from the approved source. Its release identity agreed across stages. Catalog inspection confirmed the field was absent and the revision stayed `semantic_cli_run_supervisor` after rollback. The temporary declaration workspace was removed. |
| Corpus and review | Installed focused result `5a6014d26cd44c95994f174d7ba8fa6d` passed 12 tests, including default writer-only ingest, one-connection supervision, retained preparation and writer stdio. Fresh reader-only stdio exercised the six pure operations and refused a wrong scope and denied reader role. In the isolated result store `build/review-interrupted-wx0zl1y9/results`, held `1d73b83698b14e83a3d9a4974bd9896c` settled after SIGTERM and `bf79f3102b2f46d3aa2fcd1c9fc62cbc` replayed and detached-verified run 205/cut 283. A separate replay control refused a same-root selection edit and an unavailable exact task. `uv run ci eval operation-event-availability 205 --project wce-gs120-method-development-20261106 --json` reported `missing_events` and its producer action. |
| Database, host and command reference | `uv run ci db migrate --expected-predecessor semantic_wce_lineage_20261107 --json` passed on development and advanced the operational revision to `semantic_cli_run_supervisor` with the same corpus physical model. `uv run ci db status --maintenance --json` verified the acquired target and revision. `uv run ci host status --json` passed healthy checks and reported nonzero exit on unreachable and mismatched extension controls. `uv run ci docs commands --json` generated the verified inventory. |
| Live production | `blocked`. `uv run ci context show --target deployment --json` confirmed the deployment profile is unavailable. Resume with an explicitly configured production endpoint, the applicable predecessor and purpose roles, and authority for the exact deployment and separate activation and selection. Isolated controls qualify their recorded target only. |

#### Reconciled functional and nonfunctional results

`uv run ci test --json` created held result `9bdf4f6075244e7696b986a4e39203fa`.
Ordinary pytest at `107053d33` ran with 16 xdist workers and recorded 5,110 passed and one
failed. All eight exclusive PostgreSQL fault controls passed at `f751b352a`. The intervening
commits changed documentation only. Both lanes settled with zero worker losses. Rust was
`not_run` because Nextest listed zero tests. Toolchain `rustc 1.101.0-nightly (2d20b42b8 2026-11-04)`.

The failure exposed admission metadata captured before an independent physical edit. The
production repair `52623af68` resolves the metadata at use time and also fences custody before
test retry or coverage. The initial exact retry `d6798e9789d641b3b29dc69f48611c3c` and affected
selection `895619a228b442e2b9a654f47ea98270` each retained the fixture's missing physical identity
failure. The affected selection passed its other 178 tests, including 26 native-required nodes.
Commit `562b3e49e` supplied the fixture's independently derived identity and asserted both old and
changed admission identities. `uv run ci test retry d6798e9789d641b3b29dc69f48611c3c --lane ordinary --json`
passed the exact node in `5c839e6154d2480d9df0a206f7969f21`.

`uv run ci test coverage 9bdf4f6075244e7696b986a4e39203fa 895619a228b442e2b9a654f47ea98270 5c839e6154d2480d9df0a206f7969f21 --json`
reported 5,119 required Python nodes covered, including 888 native-required, with zero unresolved
and zero missing lanes. The separate affected selection plus exact retry covered all 179 of its
required nodes, including the new custody regression. The reconciliations preserve failed attempt
outcomes and the different source contexts. The affected checks cover the changed admission and
custody boundaries. The operator scoped final validation to the failure and directly affected
tests. `uv run ci check --json`, `just types` and `just turn-end` passed.
