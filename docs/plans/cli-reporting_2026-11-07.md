# CLI reporting and file-free composition

**Status:** Audit repairs verified in the reporting worktree. Main integration and final-source qualification are pending. **Created:** 2026-11-07.

## Outcome and baseline

Read test failures, coverage, model effects and corpus evidence directly through installed
`ci`, using a result identity or a typed pipe where the task calls for one. A compact default
answers the immediate question. A named view returns selected detail with its identity,
selection and limits. Ordinary inspection and composition require zero caller-created
scratch files. Managed invocation results support recovery, detached delivery supports
handoff, and owner staging supports coherent publication.

This plan consumes the [file-free CLI reporting review](../functional_reviews/cli-reporting_2026-11-07.md)
at `e2385dd1f`. Source inspection for planning used that HEAD on 2026-11-07, with concurrent
changes in the CLI failure adapter, detached verifier and enrichment code. Recheck those
shared boundaries before editing. The environment pins Python 3.14.10, Rich 15.0.0,
Typer 0.28.0 and Pydantic 2.14.1. The dated controls establish the observed behavior on their
selected inputs, including the pre-implementation exit 120 on early pipe closure. [Reporting controls](../design_review/evidence/2026-11-07_cli-reporting/README.md) ·
[Dependency manifest](../../python/corpus-structure/pyproject.toml)

| Current owner | Inspected foundation and consequence |
|---|---|
| CLI boundary | The explicit Typer registry and lazy `CliState` support help without opening settings or a database. `emit` already separates the typed serializer and Rich renderable. Reuse it and the failure boundary. A shared console lifetime earns its place when progress and diagnostics need coordination. |
| Test evidence | The coverage adapter calls the receipt classifier with `--summary`. That route still carries the required node lists, and the same classifier mode has other callers. Add an explicit compact classifier route and migrate only consumers whose contracts it fulfills. |
| Managed and domain reads | `ResultStore` can lease a result and authenticate a published artifact by descriptor. The model decoder already verifies action, digest and preview identity. Detached verification already checks bundle membership and relationships. Reuse these responsibilities, extending descriptor-rooted reads where the current path-based verifier needs them. |
| Repository checks | The `just` bundle decides step order and failure membership. The supervisor owns child process groups and cancellation. Its captured transcript is reduced only after collection. Expose step facts at their owner and separately assess whether bounded collection solves a remaining diagnostic problem. |

## Shared contracts and decisions

- The CLI projects owner products. Named views carry subject identity, outcome, selection,
  counts and their denominator, coverage or availability, and omission or continuation
  when applicable. The full `--json` shape remains available when no view is specified.
  Human and JSON views derive from the same typed selection. Add a plain stream only for a
  named consumer and specify its bytes, limits and completion semantics.
- Use [ADR-0069](../adr/0069-cli-operations-custody.md) for effect and custody rules. A read
  holds its lease for the authenticated access. A new dependency follows the separate expiry
  and hold rules. Successes expire after one day and failures or interruptions after one
  week, subject to protections. Apply, registration, deployment, activation and selection
  keep their explicit authority. Continue to route repository automation through `just`.
- The [CLI operations plan](cli-operations_2026-11-07.md#completion-audit) owns its existing
  repairs and live production obligations. [Next corpus enrichment](next-corpus-enrichment_2026-11-07.md)
  owns the domain products and their assessment. Consume its settled read products as available.
  Fitting applicability can be reported from the existing read with its actual prerequisites.
- **Proposed design judgment.** A second report view should change the owning selection and
  renderer, with custody and settlement reusable. A future transport should consume the same
  typed report without acquiring authority over it. Bounded output alone cannot justify
  moving full classifications through a subprocess, parsing unrestricted selections, or
  verifying an entire bundle on every browse. Keep required verification explicit and choose
  access, bounds and lifetime together. [Design principles](../design_review/design_principles/core/design-principles.md) ·
  [Execution-fit guidance](../design_review/design_principles/core/efficient-architecture-heuristics.md)
- **CLIR-D01 · Accepted 2026-11-07.** An incomplete report caused by stdout closure exits
  74 and reports the delivery failure on stderr where possible. An already-known command
  failure or cancellation keeps its original status. Settlement and managed result identity
  remain with the operation. This applies to existing and new human, JSON and explicit
  text reports. Operator decision recorded in the execution planning conversation.

## Execution scope and current disposition

| Package | Source | Prerequisite and completion boundary | Current disposition |
|---|---|---|---|
| [CLIR-01 · Report boundary](cli-reporting/reporting-and-test-evidence.md#CLIR-01) | O01 | Extend the emitter with the minimum contract shared by compact test and leased model reads. Verify equivalent human and named JSON facts and the existing full JSON route. | **Branch verified.** Ordered selection and human and JSON parity verified through installed reads. |
| [CLIR-02 · Test evidence](cli-reporting/reporting-and-test-evidence.md#CLIR-02) | O02 | Consume CLIR-01. The classifier projects counts and bounded details at its boundary. An exact failure and reconciled retry coverage can be inspected by ID. | **Branch verified.** Compact context and custody reports and selected-lane isolation verified. |
| [CLIR-03 · Preview and candidate](cli-reporting/managed-model-and-corpus-reads.md#CLIR-03) | O03 | Consume CLIR-01. Bound model artifacts are read in place. The explicit raw diff stream is gated by CLIR-06. | **Branch verified.** Bound hunk attribution and local action prerequisites verified. |
| [CLIR-04 · Review and corpus](cli-reporting/managed-model-and-corpus-reads.md#CLIR-04) | O04 | Consume CLIR-01 and authenticated read capabilities exercised by CLIR-03. Managed and detached inspection agree for the same authorized bundle. Complete the stdin and verified corpus routes against their owner contracts. New stream routes use CLIR-06's accepted policy. | **Branch verified.** Verified selection and coverage reporting, ordinary replay and evaluated exposure exercised. |
| [CLIR-05 · Repository diagnostics and discovery](cli-reporting/checks-and-discovery.md#CLIR-05) | O05 | Consume CLIR-01 and existing recipe ownership. Identify failed steps, explain safe next actions and provide a direct reference route once its stdout contract is settled in CLIR-06. | **Branch verified.** Owner applicability and failure excerpts verified through the installed step route. |
| [CLIR-06 · Streams and stage reporting](cli-reporting/streams-and-diagnostics.md#CLIR-06) | O06 | Start the compatibility inquiry alongside CLIR-01. Make stream and settlement behavior available independently of optional TTY work. | **Branch verified.** Delivery, interruption and owner stage reporting implemented and tested. |
| [CLIR-07 · Diagnostic gaps](cli-reporting/streams-and-diagnostics.md#CLIR-07) | O07 | Compare actual gaps after CLIR-05 and the stage/report slice of CLIR-06. Add a mechanism only for a demonstrated decision gap. A reasoned disposition with a revisit trigger can close the investigation. | **Branch verified.** Bounded step capture recovered the lost diagnostic in the reported scenario. |
| CLIR-08 · Adoption and qualification | O01–O07 | Consume the delivered packages and resolved or explicitly deferred conditional work. Qualify the declared union, update operator guidance with the shipped routes, and record any remaining blocked obligation at its owner. | **Branch verified.** Installed branch journeys exercised. Reconcile the required union against final main source. |

Source IDs are scoped to this review. The supporting plans disposition the additional
library families with the package where they would apply. Generic selectors and content
browsing, dynamic terminal features and additional logging are conditional, with the
specific adoption conditions in those plans. Reconsider the package design if an
investigation changes owner responsibility or a required input. Follow the
[design review cadence](../design_review/design_principles/binding/corpus-structure.md#reviews-in-this-repository)
for affected boundaries and the assembled increment.

## Integrated acceptance and adoption

| Installed journey | Required independent evidence |
|---|---|
| Read a failed test, retry it and reconcile coverage | Know the expected failed node and phase independently of the renderer. Show the original failure after successful retry and distinguish unresolved requirements, missing lanes and changed source. Observe a compact classifier response for a large retained selection. |
| Inspect effects and candidate standing | Compare the rendered and typed views with the bound preview and candidate. Exercise missing, expired and substituted artifacts with expected distinctions based on owner evidence. Prove read-only behavior and lease cleanup. |
| Inspect corpus evidence and pipe a selection | Compare managed and detached reads of the same bundle. Exercise malformed and oversized input, corrupt or escaped members, missing prerequisites and two distinct causes of partial coverage. Verify preserved witness and selection attribution and the separate evaluated authority. |
| Explain a failed check or interrupted operation | Establish the exact failed step or unsettled stage and next action. Run installed subprocess and PTY controls for narrow/wide layout, Unicode, redaction, ANSI safety, stream separation, early close and cancellation. Retrieve the original settled or interrupted result by ID. |

All four journeys run through installed `ci` without caller-created scratch files. Fixtures
can supply existing managed receipts or detached bundles. Use `CliRunner.invoke` for grammar and
typed output, and a real process or PTY for OS stream, signal and shell behavior. Keep local
checks focused on changed behavior and affected consumers. At the integrated endpoint qualify
the applicable required union for final source and context. Record command, scope, date, outcome
and blocked prerequisites. Keep historical receipts and synthetic controls at their original
scope. Update installed help and the relevant [ci skill routes](../../.claude/skills/ci/SKILL.md)
as each capability lands. [Pinned Typer test runner](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py)

## Branch execution checkpoint · 2026-11-07

- Reporting started from `5edbd2f0a`. The operator requested integration of the NCE
  pause point `73599a210` and authorized the merge to `main` at `78a21de7a` before full
  qualification. The final campaign ran on main.
- The first broad ordinary attempt `c3d1d17b541943219acf04c99260066c` was interrupted
  during concurrent cluster activity after 2,560 of 5,160 nodes passed. The branch retry
  `dacb2d0f6de24042bd1d5e152a7d1998` was stopped at operator direction after the merge.
  Both receipts remain available. Neither establishes main qualification.
- A PostgreSQL 18 `pg_virtualenv` run on the staged integration of `1331728f9` passed
  all 12 selected tests, including a native CLI failure check. Receipt
  `deda02c1c21f47229df5224f57246b33` records the private test context. The temporary
  cluster was removed. The real authentication fault lane targets the dedicated cluster.
- The branch delivered compact classifier output, exact test failures, preview and
  candidate reads, managed review inspection, bounded stdin, ordered recipe steps and
  the shared stream boundary. The completion audit below owns the remaining work. Managed review
  results created before publication recorded a manifest digest can still be verified
  from an intentional detached bundle. A fresh export establishes managed origin proof.
- The initial CLIR-07 investigation relied on the recipe step channel and existing managed
  stages and counts. Its controls identified the failed step or unsettled result and a next
  action. CLIR-CA10 records a later control where the reason for failure is lost and reopens
  the excerpt decision. Additional logging and continuous progress remain conditional.
- CLIR-08 records targeted and integrated qualification separately. The separate live
  CLI operations prerequisites retain their existing owner.

### Branch verification

| Command or journey | Outcome on 2026-11-07 |
|---|---|
| `uv run ci test --json --` with the affected reporting, verifier and classifier modules | `passed`. Integrated receipt `cde5b8be0ffb498193201e76730a3b75` covered 191 tests. Follow-up receipt `9f732152596243c8afb687169e2cb694` covered 75 tests after the custody and delivery review fixes. The selections overlap. |
| `uv run ci check --json` and `uv run ci docs check --json` | `passed` on the reporting branch. Rules were `not_run` with no registered rules. |
| `ci test failures`, `ci test retry --lane ordinary` and `ci test coverage --view unresolved` | `passed`. Initial receipt `b60343be69404004a931511ac2de5fe6` failed nine native test setups when the migration inputs were LFS pointers. After hydration, retry `07243b2c52424443bbf51bc8fe2b1aed` passed all nine. Reconciliation retained the initial failure and showed 50 required, 50 covered and zero unresolved, with the source-context difference visible. |
| `ci model change preview -` and `ci model change inspect` | `passed` against bound no-effect preview `a72f921cae04458a82de6e556da104d6`. Focused fixtures exercise candidate registration evidence, expiry and substitutions and feed exact diff bytes to Git. |
| `ci review export -` and `ci review inspect --result` | `passed` for inventory scope, run 205 and cut 283, under result `4e8c7df6081c45d5b9e0d47765f0cb8b`. Focused tests cover detached parity, bounded input, regular-file enforcement and substitution of a self-consistent bundle. |
| `ci docs commands --stdout \| head -c 0` | `passed` as an early-close control. Pipeline statuses were `74 0`. Focused tests cover child interruption, write and flush closure, and known failures with both output streams closed. |

## Main qualification · 2026-11-07

These receipts establish the recorded development test union. The completion audit
separately assesses functional scope and installed journeys. The
operator-directed guidance in [AGENTS.md](../../AGENTS.md) and the
[ci skill](../../.claude/skills/ci/SKILL.md) makes routine report materialization
an in-scope CLI responsibility.

| Command | Outcome and applicability |
|---|---|
| `uv run ci test --json` | Initial main receipt `fce1f0a6a72d4e8cb2f89205484a9cd7` at `18cbaccaf` settled `failed`. Ordinary pytest selected 5,165 nodes with 5,164 passed and one PostgreSQL claim-renewal lock timeout. All eight exclusive fault nodes passed. Rust functional coverage was `not_run` because nextest listed zero tests under rustc 1.101.0-nightly. |
| `uv run ci test retry fce1f0a6a72d4e8cb2f89205484a9cd7 --lane ordinary --json` | `passed`. Receipt `215a0a7279114003b295702aa418bc7d` selected only `test_six_published_views_keep_current_claims_and_native_dependencies` at `9f4acd541`. Only agent and skill guidance changed between the source commits. |
| `uv run ci test coverage fce1f0a6a72d4e8cb2f89205484a9cd7 215a0a7279114003b295702aa418bc7d --view unresolved --limit 20 --json` | `passed` as a report. The required Python union is covered at 5,173 of 5,173 with zero unresolved, no missing lanes and settled custody. The original failure, successful retry and source-context difference remain visible. |
| `uv run ci check --view steps --json`, `uv run ci docs check --json`, `uv run ci doctor --json` | `passed` on main. Repository checks covered the installed step report, lint, types, publication, dependency pins and Clippy. The docs and tool checks passed after the reporting guidance change. |

## Completion audit

**2026-11-07 · inspected committed `397a52964` on main.** Reviewed all claimed CLIR-01–08
scope against the companion plans, O01–O07, ADR-0069, and the operator's CLIR-D01 decision.
Three independent read-only reviews followed the installed command, owner, custody and
verification paths. Concurrent NCE edits, including changes to predicate replay in the shared
review verifier, are outside the baseline. The findings describe the audited state. Branch repair evidence is recorded below.

**Implementation.** The core file-free routes work. The audit reopened reporting fidelity,
effect guidance and stream behavior where the actual outcome falls short of the accepted
scope. The plan's existing conditions for generic browsing, manifest-only inspection,
dynamic progress and logging still apply. The lost failure diagnostic supplies a concrete
case for CLIR-07 to reconsider with the recipe owner.

**Verification.** The retained main receipts still reconcile to 5,173 required Python
nodes, zero unresolved, both lanes present and settled custody. The original lock timeout
remains visible. Between the tested source and the inspected commit, changes were limited
to agent guidance and plan documentation. The installed managed review and model-preview
reads, exact failure lookup and coverage reconciliation passed bounded audit reads. The audit
also reproduced false success for an inapplicable rule check, omitted review scope in the human view, and
stream edge cases recorded below. Installed Bash completion also passed with invalid
application settings. Product test execution was `not_run` in this audit.
The recorded campaign does not close the installed journey obligations below.

**Benefit.** Compact classification avoids returning the full required-node list over
the subprocess boundary. The retained model and review reads and ordinary retry journey
show direct use by ID without caller scratch files. These observations establish usable
routes and bounded payload shape. Runtime improvement remains unmeasured.

| Finding | Owner and gap | Required closure |
|---|---|---|
| CLIR-CA01 | **CLIR-01 · Branch verified.** The named failure and unresolved-node views show selected and omitted counts. Their payloads and human renderers omit the declared ordering required to interpret the selection. [Report models and renderers](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L81) | State the owner ordering in both views and prove the same selection and readable exact identities through installed human and JSON reads, including narrow Unicode, literal markup, controls and credential-shaped text. |
| CLIR-CA02 | **CLIR-02 · Branch verified.** The compact classifier compares source fingerprints. An installed fixture with identical source and changed Python and pytest versions reports `sources_differ: false` without surfacing those context differences. Active coverage identifies custody but offers no watch action. Failures can repeat a stored exact-retry hint after current evidence makes retry unavailable. [Classifier](../../scripts/test_receipts.py#L954) · [Coverage and failure adapters](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L489) | Distinguish source and applicable execution-context differences and unknowns in the bounded reports. Carry the current custody and derive watch, recovery or retry from available evidence. Cover same-source changed context, active and classifier-only unsettled custody, and a missing collection manifest with a stale hint. Keep full JSON compatible. |
| CLIR-CA03 | **CLIR-02 · Branch verified.** An explicit ordinary-lane failure read authenticates all artifact roles before selecting the lane. A substituted fault artifact refused the intact ordinary lookup in an installed fixture. [Receipt selection](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L391) · [Failure command](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L565) | Resolve the requested lane before opening its artifacts. Prove the intact selected lane remains readable and the same substitution still refuses when its lane is selected. |
| CLIR-CA04 | **CLIR-03 · Branch verified.** Bounded patch pages lose the file identity of individual hunks and the bound target. Preview guidance can suggest an effect for a stale checkout. Candidate inspection keeps a register hint when installed artifacts conflict and the registration owner would refuse. [Patch and preview report](../../python/corpus-structure/src/corpus_structure/cli/model.py#L244) · [Candidate guidance](../../python/corpus-structure/src/corpus_structure/cli/model.py#L444) · [Registration owner](../../python/corpus-structure/src/corpus_structure/schema/model_deployment.py#L282) | Attribute each hunk to its file and each page to its preview and target. Use locally available owner checks to distinguish eligible, stale and conflicting actions. Surface remaining effect prerequisites as conditions. Exercise multi-file pages, a stale preview, and missing versus conflicting candidate artifacts. Preserve the exact streamed bytes and lease. |
| CLIR-CA05 | **CLIR-04 · Branch verified.** The installed human review read of `4e8c7df6081c45d5b9e0d47765f0cb8b` shows only inventory, source completeness and two relation types. JSON includes the selected run and cut, relation row counts and assessment scope. The human source coverage projection also omits the exact content digest. [Review renderer](../../python/corpus-structure/src/corpus_structure/cli/review.py#L346) · [Source coverage renderer](../../python/corpus-structure/src/corpus_structure/cli/source.py#L134) | Materialize a bounded attributed human review view with selection, witness and assessment coverage. Include the exact source product pin in coverage. Verify normal inventory, evaluated scope and distinct incomplete cases against owner facts. |
| CLIR-CA06 | **CLIR-05 · Branch verified.** `ci check --only rules --view steps --json` exited 0 with `passed`. The unchanged full route reported `rules-scan: not_run (no rules yet)`. The owned bundle channel also maps zero exit to `passed` without a separate applicability fact. [Rule owner](../../justfile#L155) · [Step consumer](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L183) | Carry the owner's applicability and refusal separately from process exit. Check skipped, passed, failed, interrupted and unobserved steps through both the bundle and single-step routes. Preserve the direct transcript and full JSON behavior. |
| CLIR-CA07 | **CLIR-06 · Branch verified.** A closed stdout with unavailable stderr can replace the accepted exit 74 with exit 1 when reporting the delivery error. Managed command reference generation converts known cancellation to a generic failed result and exit 1. The direct reference route preserves the cancellation status. [Delivery boundary](../../python/corpus-structure/src/corpus_structure/cli/output.py#L61) · [Reference routes](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L242) | Make stderr diagnostics best effort when stdout closes and preserve the known operation status. Settle interrupted managed reference generation truthfully and verify the original result by ID. Exercise installed write and flush failures with unavailable stderr, plus direct and managed cancellation. |
| CLIR-CA08 | **CLIR-06 · Branch verified.** Test and review commands surface owner stages. Long-running model and native candidate operations write stages into manifests and expose the initial ID, while the command itself omits the meaningful stage changes from stderr. [Stage owner](../../python/corpus-structure/src/corpus_structure/cli/managed.py#L212) · [Model stages](../../python/corpus-structure/src/corpus_structure/cli/model.py) | Materialize bounded owner stage lines on the affected long-running routes, with a settled final result and clean stdout. Verify on an installed command without requiring a separate watch. |
| CLIR-CA09 | **CLIR-08 · Branch verified.** The retained installed corpus journey is ordinary inventory. Focused fixtures cover evaluated role selection and stdin or replay separately with mocked edges. The installed preview case has no semantic effects. They leave the required installed evaluated stdin and exposure, ordinary replay of an admitted stdin selection, two different incomplete coverage causes, and attributed nonempty model review unqualified. Earlier width and safety probes used synthetic rendering. The installed PTY control covers stderr staging and JSON separation, leaving the shipped narrow and wide report and interrupted managed result retrieval to qualify. [Journey criteria](#integrated-acceptance-and-adoption) · [Review controls](../../python/corpus-structure/tests/test_review_cli.py#L31) · [Preview controls](../../python/corpus-structure/tests/test_cli_model_inspect.py#L90) | After the reporting repairs, exercise the remaining installed journeys with independent expected owner facts and the applicable evaluator authority. Recheck directly affected consumers and assess the required union for the final source. Preserve earlier receipts at their recorded scope. |
| CLIR-CA10 | **CLIR-05 and CLIR-07 · Branch verified.** Excerpts come from the final 1,200 characters of each aggregate stream, without a step identity. In an installed bundle control an early step failed with exit 17 and a later passing step emitted enough stderr to displace the first failure's diagnostic. The report named the failed step but lost the reason needed to choose a next action. [Excerpt selection](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L190) | Compare retaining an owner-attributed bounded excerpt with the existing process receipt and scoped handler options. Preserve the actionable failed-step excerpt and truncation information through later output. Qualify a failed step followed by a verbose passing step, redaction and interruption. Adopt the smallest owner mechanism that supplies the fact. |

## Audit repair execution

**2026-11-07 · reporting worktree.** Started from `29e288d14` on
`work/cli-reporting-audit-repair` while NCE work continued on main. The branch keeps
the existing recipe, receipt and domain owners. In the structured check route the
bundle supplies order and each step supplies its process result, applicability and a
bounded failure excerpt. This preserves the reason for a failed step when later output
is verbose. The existing transcript and managed custody cover the remaining diagnostic
needs in this scope. The operation owner remains responsible for effect fences. Model
inspection reuses read-only local preflight and presents target-side prerequisites as
conditions. Review inspection derives run and cut from authenticated selection rows.

| Command or installed journey | Outcome on 2026-11-07 |
|---|---|
| `uv run ci test --json -- …` for recipe reporting, report delivery, test evidence, managed results, model inspection, review and source CLI, schema preview, review bundles and receipt classification | `passed`. Receipt `681bb708b9424e0cbc876d0b8c80b317` covered all 212 ordinary nodes. Included installed 44- and 110-column human reports, exact managed cancellation retrieval, stderr I/O failure, and attribution after later verbose output. Earlier affected receipts `2c34c5043dfd4bf39c9f736da4581434`, `544e5fc6b0c644f4baa3363df7c465c8`, `9d4858b74102408590052fc086e67ce8` and `9976f25bf35147f59485e0f2b1ab247f` overlap this selection. |
| `uv run ci test --json -- python/corpus-structure/tests/semantic/test_review_cli_native.py` in a private PostgreSQL 18 cluster | `passed` for all three installed journeys in receipt `575f45edc52643efbce28778b06de985`. Earlier receipt `5d35d88347414baf9e13d06fa6f18692` passed the evaluated exposure and bound nonempty preview. Its ordinary replay assertion incorrectly expected the capture identity to be reused. Exact retry `0057838f2e18486d98c490591b4fde15` passed with a fresh capture identity and matching retained selection, omission and verified scope. |
| `uv run ci test --json -- python/corpus-structure/tests/semantic/test_native_candidate_cli.py` and the installed native preview node | `passed`. Receipt `e602e859993e44d1a0009ab27b8c94f0` covered 14 native-candidate adapter nodes, including rollback and stage diagnostics. Exact native preview receipt `a2a2053e9ce14b10a5211698e73195df` verified ordered stderr stages and a single JSON stdout report. |
| `uv run ci check --view steps --json` and `uv run ci docs check --json` | Agent and ADR lint, Ruff, types, dependency checks and Clippy `passed`. The rules were `not_run` because the registry was empty. Publication initially lacked the local ignored `docs/statistics_corpus/SOURCES.tsv` in the worktree. The direct publication rerun and final integrated check `passed` after bringing in that manifest. |
| `uv run ci test coverage fce1f0a6a72d4e8cb2f89205484a9cd7 215a0a7279114003b295702aa418bc7d --view unresolved --limit 2 --json` | `passed` as a branch report against the retained main receipts. It reported 5,173 required and covered nodes, zero unresolved and distinct source and native-context differences. Those receipts retain their recorded source and context. |

The PostgreSQL controls used test-owned databases and separate maintenance, reader and
evaluator roles. The private `pg_virtualenv -v 18` cluster loaded `pg_textsearch` and
`pg_stat_statements` at startup, seeded `cs_template` from the pinned extension record and
used `max_locks_per_transaction=1024` for native migration setup. The launcher removed
the private cluster after the tests.
The first attempt `5d225024959d406db9a499d7240ece88` preserves the setup failure at the
PostgreSQL default lock-table setting.

**Next.** At the operator's main pause point, integrate the current main tip, review any
shared verifier and migration changes, and qualify affected behavior on the merged source.
Reconcile the applicable final test union and exclusive fault evidence before closing the
findings. Required branch receipts are held for integration. Retain the applicable evidence before removing the merged worktree. The
[CLI operations plan](cli-operations_2026-11-07.md) owns its production prerequisites.
