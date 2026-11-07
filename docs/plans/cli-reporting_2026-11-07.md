# CLI reporting and file-free composition

**Status:** Implemented on `work/cli-reporting`. Branch qualification and operator-directed
integration are in progress. **Created:** 2026-11-07.

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
selected inputs, including the current early-pipe-close failure. The proposed commands and
their runtime qualification are `not_run`. [Reporting controls](../design_review/evidence/2026-11-07_cli-reporting/README.md) ·
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

## Execution queue and source coverage

| Package | Source | Prerequisite and completion boundary |
|---|---|---|
| [CLIR-01 · Report boundary](cli-reporting/reporting-and-test-evidence.md#CLIR-01) | O01 | Extend the emitter with the minimum contract shared by compact test and leased model reads. Verify equivalent human and named JSON facts and the existing full JSON route. |
| [CLIR-02 · Test evidence](cli-reporting/reporting-and-test-evidence.md#CLIR-02) | O02 | Consume CLIR-01. The classifier projects counts and bounded details at its boundary. An exact failure and reconciled retry coverage can be inspected by ID. |
| [CLIR-03 · Preview and candidate](cli-reporting/managed-model-and-corpus-reads.md#CLIR-03) | O03 | Consume CLIR-01. Bound model artifacts are read in place. The explicit raw diff stream is gated by CLIR-06. |
| [CLIR-04 · Review and corpus](cli-reporting/managed-model-and-corpus-reads.md#CLIR-04) | O04 | Consume CLIR-01 and authenticated read capabilities exercised by CLIR-03. Managed and detached inspection agree for the same authorized bundle. Complete the stdin and verified corpus routes against their owner contracts. New stream routes use CLIR-06's accepted policy. |
| [CLIR-05 · Repository diagnostics and discovery](cli-reporting/checks-and-discovery.md#CLIR-05) | O05 | Consume CLIR-01 and existing recipe ownership. Identify failed steps, explain safe next actions and provide a direct reference route once its stdout contract is settled in CLIR-06. |
| [CLIR-06 · Streams and stage reporting](cli-reporting/streams-and-diagnostics.md#CLIR-06) | O06 | Start the compatibility inquiry alongside CLIR-01. Make stream and settlement behavior available independently of optional TTY work. |
| [CLIR-07 · Diagnostic gaps](cli-reporting/streams-and-diagnostics.md#CLIR-07) | O07 | Compare actual gaps after CLIR-05 and the stage/report slice of CLIR-06. Add a mechanism only for a demonstrated decision gap. A reasoned disposition with a revisit trigger can close the investigation. |
| CLIR-08 · Adoption and qualification | O01–O07 | Consume the delivered packages and resolved or explicitly deferred conditional work. Qualify the declared union, update operator guidance with the shipped routes, and record any remaining blocked obligation at its owner. |

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

- The reporting branch starts from committed `main` at `5edbd2f0a`. The coordinator
  integrates only operator-designated later main checkpoints and waits for separate
  authorization to land on main.
- CLIR-01–06 are implemented. Compact classifier output, exact test failures, preview and
  candidate reads, authenticated managed review inspection, bounded stdin, ordered recipe
  steps and the installed stream boundary are available on the branch. Managed review
  results created before publication recorded a manifest digest can still be verified
  from an intentional detached bundle. A fresh export establishes managed origin proof.
- CLIR-07 uses the recipe step channel and existing managed stages and counts. The failed
  and interrupted controls identify the step or unsettled result and the next action.
  Additional logging, continuous progress and retained excerpts remain conditional on
  a named decision those reports cannot support. Revisit bounded transcript collection
  if measured child output or a specific pre-failure need warrants changing the supervisor.
- CLIR-08 records targeted and integrated qualification separately. Qualification does not
  imply a merge to main or change the separate live CLI operations prerequisites.

### Branch verification

| Command or journey | Outcome on 2026-11-07 |
|---|---|
| `uv run ci test --json --` with the affected reporting, verifier and classifier modules | `passed`. Integrated receipt `cde5b8be0ffb498193201e76730a3b75` covered 191 tests. Follow-up receipt `9f732152596243c8afb687169e2cb694` covered 75 tests after the custody and delivery review fixes. The selections overlap. |
| `uv run ci check --json` and `uv run ci docs check --json` | `passed` on the reporting branch. Rules were `not_run` with no registered rules. |
| `ci test failures`, `ci test retry --lane ordinary` and `ci test coverage --view unresolved` | `passed`. Initial receipt `b60343be69404004a931511ac2de5fe6` failed nine native test setups when the migration inputs were LFS pointers. After hydration, retry `07243b2c52424443bbf51bc8fe2b1aed` passed all nine. Reconciliation retained the initial failure and showed 50 required, 50 covered and zero unresolved, with the source-context difference visible. |
| `ci model change preview -` and `ci model change inspect` | `passed` against bound no-effect preview `a72f921cae04458a82de6e556da104d6`. Focused fixtures exercise candidate registration evidence, expiry and substitutions and feed exact diff bytes to Git. |
| `ci review export -` and `ci review inspect --result` | `passed` for inventory scope, run 205 and cut 283, under result `4e8c7df6081c45d5b9e0d47765f0cb8b`. Focused tests cover detached parity, bounded input, regular-file enforcement and substitution of a self-consistent bundle. |
| `ci docs commands --stdout \| head -c 0` | `passed` as an early-close control. Pipeline statuses were `74 0`. Focused tests cover child interruption, write and flush closure, and known failures with both output streams closed. |
