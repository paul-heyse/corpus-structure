# CLI operations and managed results

**Status:** Partial delivery. CLI-00 rule adoption is complete. CLI-01–08 retain bounded evidence
and open implementation or acceptance obligations. This plan owns their current disposition.
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
| [O01](../functional_reviews/typer-cli-target_2026-11-07.md#O01) | Partial · CLI-CA07 owns remaining routine caller migration. |
| [O02](../functional_reviews/typer-cli-target_2026-11-07.md#O02) | Partial · CLI-CA01 owns provenance and workspace controls. CLI-CA06 owns operational target continuity. |
| [O03](../functional_reviews/typer-cli-target_2026-11-07.md#O03) | Partial · F01 and CLI-CA02 own custody and retention. F02a and F05 own candidate and export continuity. |
| [O04](../functional_reviews/typer-cli-target_2026-11-07.md#O04) | Partial · F03 owns selection and truthful reconciliation. CLI-CA08 owns remaining acceptance. |
| [O05](../functional_reviews/typer-cli-target_2026-11-07.md#O05) | Partial · CLI-CA01 and CLI-CA02 own safe output, progress and diagnostics. |
| [O06](../functional_reviews/typer-cli-target_2026-11-07.md#O06) | Partial · F02, CLI-CA03 and F02a own approved effects, discovery and native deployment. Codemod selection remains conditional. |
| [O07](../functional_reviews/typer-cli-target_2026-11-07.md#O07) | Partial · F04/F05 and CLI-CA04–06 own read authority, replay, run lifecycle, fitting and privileged operations. |

### Improvement review dispositions

| Item | Disposition and owner | Closure or adoption condition |
|---|---|---|
| [I01](../plan_improvement_reviews/cli-operations_2026-11-07.md#I01) | Verified in the locked checkout · [CLI-01](cli-operations/command-context-output.md#typer-0280-transition). | Exact pin, workspace override and bounded grammar/help/reference checks. Standalone resolution has no supporting receipt. |
| [I02](../plan_improvement_reviews/cli-operations_2026-11-07.md#I02) | Partial · CLI-CA01 and F03. | Verify typed intent, harmless completion and literal, policy-checked recipe forwarding. |
| [I03](../plan_improvement_reviews/cli-operations_2026-11-07.md#I03) | Partial · CLI-CA01. | Verify redaction, terminal-control handling and JSON/exit isolation in affected consumers. |
| [I04](../plan_improvement_reviews/cli-operations_2026-11-07.md#I04) | Partial · F03 and CLI-CA08. | Verify applicable lanes and exact retry context across concurrent campaigns. |
| [I05](../plan_improvement_reviews/cli-operations_2026-11-07.md#I05) | Partial · F01. | Verify substituted paths, settlement recovery, held/expired identities and concurrent export/GC. |
| [I06](../plan_improvement_reviews/cli-operations_2026-11-07.md#I06) | Partial · F02 and F02a. | Keep the verified zero-write refusal. Verify applicable native effects as exact, explicit and resumable. |
| [I07](../plan_improvement_reviews/cli-operations_2026-11-07.md#I07) | Partial · CLI-CA03. Tool alternatives remain conditional. | Exercise provenance, coordinates, compile-only validation and coverage through consumers. |
| [I08](../plan_improvement_reviews/cli-operations_2026-11-07.md#I08) | Conditional · [CLI-04/05](cli-operations/model-change-and-deployment.md#introspection-and-edit-decisions). | Adopt LibCST only for a recurring, explicitly mapped qualified rename that passes independent patch and ambiguity controls. |
| [I09](../plan_improvement_reviews/cli-operations_2026-11-07.md#I09) | Partial · F04/F05 and CLI-CA04/06. Remote artifact resource remains conditional. | Verify shared refusals, pure read authority and interrupted exact export. |
| [I10](../plan_improvement_reviews/cli-operations_2026-11-07.md#I10) | Partial · CLI-CA01/02 and F03. | Demonstrate the correct next action by ID. Optional capture, structlog and service logs require the existing consumer and value cases. |

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
| CLI-00 | **Complete.** ADR-0069 adopted CLI-RC01–03 in DESIGN, D8, D9 and operator instructions. Both reviews were recorded. | CLI-07 owns caller cutover. |
| CLI-01 | **Partial.** Typer 0.28.0 and the workspace resolver override landed. Pin-slice Docling Python consumer, grammar, `just ready`, help and Bash completion passed in the locked workspace. Managed reference `f738ea3d0ec246eeb4015d66752e3fcf`. | CLI-CA01, CLI-CA02. |
| CLI-02 | **Partial.** Normal result publication, lookup, holds, expiry and no-replace delivery exercised. Targeted campaign `a92491e73591416d93ddf279e9b1f768` passed 28 nodes at `88fd5d108`. | F01, CLI-CA02. |
| CLI-03 | **Partial.** Ordinary and exclusive native lanes dispatch through `just`. Interrupted campaigns `fab86740c6c44d4187c3d105e87876a0` and `50e67591b89644ec8844ebb4b25284de` retain settlement. Controlled failure `81662a195f114780a95017fdebb5abe7` and replacement `65af9af2222f489397507913919568e4` show exact one-node retry and separate original outcome. | F03, CLI-CA02. |
| CLI-04 | **Partial.** Shared validation and generated patch preparation landed. A prepared release is compared with the one reviewed. Bounded AST/ast-grep hits exist. | F02, CLI-CA03. |
| CLI-05 | **Partial.** Exact file apply and recovery, rollback-only development candidate `1551a8ce2e5845679c459d8fdf86bc91`, controlled registration and isolated PostgreSQL interruption/replay passed at their individual boundaries. | F02a, CLI-CA06. Live deployment is `blocked` pending service and effect authority. |
| CLI-06 | **Partial.** Retained run 205/cut 283 exported as `5e5cc1d8004b4001a3b51f745403c23b` and replayed as `8879a247e9ea49cc9f6cfb3bf71adc89`. The selection digest agreed, detached verification passed and a changed socket route refused. Reader-only stdio `find` passed 1,895 bytes and refused 1,894 bytes and the wrong run. Status reports observed cut, release and realization. | F04/F05, CLI-CA04/05. Native orphan assessment remains open. |
| CLI-07 | **Partial.** Reader and maintenance status passed against 18/corpus. Host and release routes landed, inert entries were removed, and routine examples migrated in README. | CLI-CA06/07. |
| CLI-08 | **Partial.** Assembled review recorded. The declared 5,105 Python-node union was covered in the cited contexts. | CLI-CA08. Live production qualification is `blocked`. |

The PostgreSQL tooling review selected installed `psql` for maintenance diagnosis and the existing
template-backed native fixture for exact predecessor testing. `psql -X -w -p 5434 -U paul -d corpus_structure_dev`
read `semantic_wce_lineage_20261107`; `uv run ci db status --maintenance --json` agreed. The ordinary
reader reports the migration revision as private. Dedicated-cluster status passed through
`uv run ci host status --json`. Backup/restore remains conditional on a recovery scope and owner.
Review replay binds the acquired libpq peer, database OID and completed roots. It also includes
PostgreSQL's system identifier where the purpose role can read `pg_control_system()`.
[Tool inventory](../libraries/postgresql/system-tool-usage.md) ·
[Ubuntu tooling options](../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md#87-ephemeral-database-state-cloning-and-migration-testing)

#### Functional receipts

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

**Implementation.** Rule adoption is complete. The installed journeys are partial. The table
below is the current disposition for the existing review findings and the additional completion
gaps. Each companion records its source locations, repair boundary and acceptance control.

| Finding | Current disposition and repair owner |
|---|---|
| F01 | **Open.** Authenticate managed read paths and GC retirement, and settle or recover abandoned results. [CLI-02](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| F02 | **Open.** Bind the independently classified effects and checks to the reviewed model change. [CLI-04](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| F02a | **Open.** Convey approved physical and retirement effects, bind executable migration bytes and fence the acquired native target. [CLI-05](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| F03 | **Open.** Classify keyword-only selection correctly, retain required lanes without artifacts and reconcile applicable context and retry scope. [CLI-03](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| F04 | **Open.** Move remaining pure MCP reads to reader authority while preserving queue writer effects. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| F05 | **Open.** Bind the exact replay selection and prove authentic interruption, settlement and retry. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA01 | **Open.** Resolve invocation provenance and preserve safe, typed output across consumers. [CLI-01](cli-operations/command-context-output.md#completion-audit-follow-up) |
| CLI-CA02 | **Open.** Deliver bounded, actionable diagnostics and finalize deliberate evidence promotion through its owner. [CLI-02/03](cli-operations/managed-results-and-testing.md#completion-audit-follow-up) |
| CLI-CA03 | **Open.** Complete structural discovery, compile-only checking and declared semantic consumer coverage. [CLI-04](cli-operations/model-change-and-deployment.md#completion-audit-follow-up) |
| CLI-CA04 | **Open.** Make source preparation a scoped effect and report truthful readiness, resume and orphan states. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA05 | **Open.** Expose fitting input applicability and its next action through the ordinary route. [CLI-06](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA06 | **Open.** Carry the chosen target through post-deployment reads and effects and report unhealthy host status correctly. [CLI-07](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA07 | **Open.** Finish the current command inventory, caller cutover and retired-route dispositions. [CLI-07](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |
| CLI-CA08 | **Open.** Qualify the repaired installed journeys and affected source/context selections. Live production remains `blocked`. [CLI-08](cli-operations/corpus-and-operations.md#completion-audit-follow-up) |

**Verification.** Reading the retained classifications independently reproduced 5,105 selected
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

**Benefit evidence.** Installed commands already remove destination selection for the observed
tests, model candidates and review exports. The managed IDs make the recorded export and retry
journeys retrievable. Routine caller coverage and reliable next actions remain incomplete.
Quantitative time and storage savings were outside the accepted completion criteria. Optional
backup tooling, remote artifact resources, extra logging and additional codemod tools retain
their original adoption conditions.
