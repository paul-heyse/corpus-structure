# corpus-structure — agent instructions

**Design guidance:** use the [design principles](docs/design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](docs/design_review/design_principles/core/efficient-architecture-heuristics.md)
together for consequential choices in design, planning, implementation and ADRs. Apply relevant
patterns early, before physical organization, interfaces, preparation, assurance and lifecycle
mechanisms become entrenched. During execution, address material open choices or revealed
mismatches without restarting settled reviews. This is qualitative judgment, with no exhaustive
checklist, cost models, runtime accounting or additional proof machinery.

Builds a highly structured representation of a set of documents

This is a personal project with one operator. Process is deliberately light (ADR-0001). Keep
it that way: before adding a hook, gate, register or new document type, check that it has a
real consumer.

## Start of session

The root agent reads the current checkpoint and authorities relevant to the task. Delegated
workers follow their brief and the [shared worker contract](.agents/roles/worker.md), loading
applicable instructions once; they do not repeat the root's full orientation. Preserve all
permission, concurrent-work and testing constraints, and follow discovered dependencies.

1. Read `STATUS.md` when resuming work or establishing the current execution baseline.
2. For product work, read the relevant active plan in `docs/plans/` (its current state,
   execution queue and findings table). Three plans are active, each owning its own scope
   (operator decision, 2026-10-28): the **design-phase plan** owns design findings and the
   disposition of OPEN items; the **design-spikes series** owns spike execution and its evidence;
   the **phase 0 series** owns the production build. Exception (operator, 2026-10-28): the phase 0
   coordinator §11 owns every finding and probe of the domain-model alignment review (DA-001…025,
   F01–F04, Q-1…Q-7), design findings included. Cross-references between them cite package
   ids and evidence record ids, never copied status.
3. For design questions, follow **owner → decision → open work**:
   - start at the architecture map `docs/design/README.md` and read the owning section in
     `docs/design/DESIGN.md` (scope §1, binding decisions §2) or `docs/design/sections/`, plus
     adjacent consumers; labels there distinguish implemented, accepted target and proposed;
   - the section's `> Decision:` line names the ADR that holds the reason and rejected
     alternatives (`docs/adr/README.md` lists accepted records and open proposals);
   - known defects and deferred choices affecting the section are rows in the design-phase
     plan's findings table, linked from the owner.
4. Retired plans, reviews, evidence and ADRs are not reading context; recover one from Git only
   when a current owner is insufficient (`docs/README.md`, Historical recovery).

## Where things are

| Path | What |
|---|---|
| `docs/design/DESIGN.md`, `docs/design/sections/` | Architectural collection; stable § IDs. DESIGN §2 holds the binding decisions (§B1, §B2, …) |
| `docs/README.md` | Task routes and historical recovery |
| `docs/publishing.md` | Documentation site commands; site navigation and search are derived |
| `docs/plans/` | Plans: the active ones and every finished or superseded one, which stay with their status line saying so. Plans are never deleted |
| `docs/adr/` | Current decision records (accepted and open proposals), a generated index, and `TEMPLATE.md` |
| `docs/design_review/design_principles/` | The layered design standard, declared in `standard.toml`: seven foundations (FP-01–07), including an explicit domain model, scoped semantic authority and qualitative execution-fit assessment for the intended workload; independent architectural judgments A1–A4, supporting rules DP-01–24 and gates G1–G8, the code-intelligence profile, and the repository binding (ADR-0002) |
| `docs/design_review/audit/` | Living diagnostic baseline; not ordinary implementation context |
| `docs/libraries/` | Optional repo-agnostic library capability orientation and authoring guidance |
| `docs/library_leverage/` | Codebase-first opportunity framework, shared patterns and evergreen codebase, library-applicability and comparative-review accounts |
| `docs/plan_improvement_reviews/` | Standalone remaining-change-footprint reviews; plan revision is separately instructed |
| `docs/design_review/reviews/` | Review outputs: evidence, never authority; kept while a finding they supply is open |
| `docs/design_review/evidence/` | Probes, spikes and investigations behind decisions, one `YYYY-MM-DD_<topic>/` folder each with a README; raw outputs and binaries through Git LFS; never venvs or `target/`. Put probes here, not in a session scratchpad |
| `docs/pins.md` | Holds: pins that should not be bumped casually, with reason and revisit trigger |
| `crates/` | The Rust workspace; `crates/corpus-structure` is the starter crate |
| `scripts/` | `adr.py`, `design_sections.py` and `docs.py` (documentation), `check_agents.py`, `check_pins.py` |
| `tests/scripts/` | Tests for the process scripts |
| `rules/`, `rule-tests/` | ast-grep rules. They grow only from design-review findings |

## Commands

The [CLI operations target](docs/plans/cli-operations_2026-11-07.md) routes routine actions
through installed `ci` as their adapters land. Repository automation stays owned by `just`.
Use the underlying recipes for bootstrap and recovery. The plan owns cutover and verification
status (ADR-0069).

| When | Run |
|---|---|
| During a design/implementation phase | Compile checks and targeted `uv run ci test -- PATH` or probes for the scope just implemented. No integrated gate after a slice or commit. |
| After all functional scope in the plan is implemented | `uv run ci test` runs applicable functional lanes and returns the managed result ID. `uv run ci check` runs repository checks. `just test-all`, `just test-native-faults` and `just hygiene` are the underlying qualification routes. Account for the same source/context and required union. |
| End of a turn that changed files | The root agent runs `just turn-end` (ADR index, formatting with ruff's safe auto-fixes). Subagents don't |
| After a dependency, toolchain or process-skill change, or an environment-shaped failure | `just ready` (tool check) |
| Dependency policy | `uv run ci check --only deps`: every registry dependency is pinned exactly (`=x.y.z`) and every git dependency by its `rev`; each declared family (`[workspace.metadata.pins]` in `Cargo.toml`) resolves to one version, its members exact; cargo-deny checks bans and sources |
| Decisions | `just adr new <slug> --title "…"`, `just adr supersede ADR-NNNN <slug>`, `just adr revisit`; `just turn-end` regenerates the index; `just adr-lint` runs within `just hygiene` |
| Documentation changes | `just docs-test` for publisher/resolver changes; `docs-check` (publication) runs within `just hygiene`. First run: `just bootstrap-docs`; preview: `just docs-serve`. No product gate solely for docs. |
| Tools present? | `uv run ci doctor` or the bootstrap `just ready` recipe |
| PostgreSQL (D3 §13) | `uv run ci host provision` creates or reconciles `18/corpus` (port 5434, sudo, idempotent) from `ops/postgresql/`. Use `ci host up`, `ci host down` and `ci host status` for cluster operations. `ci db status` uses the configured reader, and `--maintenance` reads the private migration revision. The application and database tests use the dedicated cluster unless `CORPUS_DATABASE__URL` names another server. Port 5432 belongs to other projects. |
| Prepare a checkout | `bash scripts/setup-env` uses existing lockfiles. Review `.envrc`, then `direnv allow` for activation; ignored `.envrc.local` holds personal overrides. Activation performs no installs, builds or service startup. |
| Template changes | `copier update --defaults`, then review the diff like any other change (`.copier-answers.yml` is never edited by hand) |

The Rust toolchain is deliberately unpinned (operator direction, 2026-10-28): there is no
`rust-toolchain.toml` and no `rust-version`, so cargo uses the machine's rustup default, currently
nightly. Don't pass `+nightly` or `+stable` to cargo in this workspace; record `rustc --version`
with any Rust result.
The repository's `.cargo/config.toml` sets 16 Cargo jobs, `sccache` as the compiler wrapper,
and incremental compilation off so the compiler cache can store workspace crates. Keep Clang
and mold as the linker route. Avoid changing `CARGO_TARGET_DIR`, rustflags, or worktrees during
ordinary development because those changes disrupt build reuse. For an isolated diagnosis,
override the config through Cargo's environment variables and report it.

Python is 3.14.10 via `uv` (`.python-version`); run Python tools as `uv run …`.
No Python activation is required. Agent environments default to `UV_LOCKED=1`; ordinary
commands synchronize dependencies but refuse stale lockfiles. Deliberate dependency changes
use `UV_LOCKED=0 uv add …` or the corresponding lock command. Explicit cross-project and
independent documentation/provider selections keep their own environment boundaries.
The type checker is **pyrefly**, not pyright or mypy. A subdirectory that is a
separate Python project with its own environment goes in root ruff's `extend-exclude`. The
process scripts are stdlib-only and run without a project environment.

## Writing code against libraries

- Optional [library overviews](docs/libraries/README.md) provide repository-agnostic capability
  orientation.
- Deliberate library-leverage inquiries use the [framework](docs/library_leverage/README.md):
  `leverage-codebase-audit` identifies concrete opportunities, `leverage-library-assessment`
  researches focused applicability, and `leverage-opportunity-review` compares complete options.
  All stages use base and assessment-discovered patterns together. Retain useful library types
  and output patterns after current matches retire; promotion into base guidance is manual.
  Ordinary implementation and API questions do not initiate this workflow.
- [Central library-skill references](.claude/skills/README.md#inactive-central-library-skill-references)
  are inactive historical context, no longer selected, synchronized, discovered or required.
  Preserve old plan references until that plan is revisited.

### Library knowledge and reference sources

Use engineering knowledge to frame the problem, identify likely capabilities and develop candidate
approaches. Consult references where they can resolve uncertainty, reveal useful alternatives or
establish a consequential library contract. Choose sources to suit the question; there is no
required lookup sequence.

- **Capability discovery:** `docs/libraries/` provides optional orientation to capability families,
  advanced features, extension points and architectural possibilities. Use it when asking what a
  library could contribute or whether custom machinery has an existing alternative. Overviews are
  selective and may describe versions different from those installed.
- **Repository integration:** Existing code, tests, configuration and dependency declarations show
  how this project uses a library and which versions and features it selects. They are useful
  implementation examples, but may reflect historical choices or a small portion of the library's
  capabilities.
- **Focused documentation questions:** Context7 is an available route to documentation and examples
  for a specific API, configuration, concept or integration. It can help locate relevant material
  when the documentation location is unfamiliar. Use it when useful; direct primary documentation
  is equally appropriate. Check version relevance before applying an example.
- **Contracts and version changes:** Official documentation, API references, release notes and
  migration guides help establish supported behavior, compatibility and intended usage. Prefer
  references matching the selected version when the distinction matters.
- **Exact behavior and edge cases:** Installed sources or upstream source and tests at the relevant
  tag or commit help resolve implementation details, defaults, feature conditions and behavior that
  documentation leaves unclear. Distinguish observed implementation behavior from a documented
  guarantee. Issues and pull requests can explain known problems or upcoming changes; check their
  status and release applicability.

Follow the uncertainty rather than consulting every source. Familiar, routine usage with adequate
local examples may need no additional lookup. Investigate further when correctness depends on an
uncertain detail, when sources conflict, or when a broader capability could materially improve the
approach.

For design work, look beyond the first API that makes the current approach possible: consider native
abstractions and related capabilities that could simplify the whole responsibility. For implementation
work, narrow research to the contracts and integration details that matter.

An empty search or missing overview section does not establish that a capability is absent. Use a
targeted probe when an unresolved behavioral question materially affects the choice; stop researching
once the available evidence supports the decision.

### Dependencies

- **Pinned.** Every declared dependency is pinned exactly: `==x.y.z` (`[tool.uv] add-bounds = "exact"`
  makes `uv add` write it) / `=x.y.z` (`cargo add name@=x.y.z`). The committed lockfiles hold everything
  beneath, so environments change only when someone changes them on purpose.
- **Change versions deliberately, on judgment.** Add or bump a dependency when the work calls for it, with
  no ADR or approval: move that dependency (or its family), check the lock diff moved only what you meant,
  run the tests it affects and name the move in the commit. No wholesale re-resolve (`uv lock --upgrade`,
  bare `cargo update`) unless the operator asks.
- **Holds go in `docs/pins.md`.** A version that must not be bumped casually (a parity oracle, golden
  output or a known breakage) gets a row with its reason and when to revisit it
  (the `pin-check` skill).

## Testing rules

- **During implementation, targeted functional checks.** Run relevant compile checks and focused
  tests for the scope just implemented. Integrated qualification waits for complete functional scope.
- **Substantial-task diagnostics.** Relevant typing/lint checks and repairs belong at a coherent
  capability or integrated package endpoint, not per edit or turn. A narrow read-only diagnostic
  may resolve a concrete defect.
- **Final source before qualification.** The root runs `just turn-end` as the last maintenance
  step of changed turns. At complete scope, applicable native functional/provider/nonfunctional
  results must cover the declared required union; `just test-all` and `just hygiene` remain broad
  routes. Account for selected scope and final source/context, not recipe labels or overlapping
  counts. Preserve failed/interrupted records. Keep unavailable required obligations open, and
  reassess affected evidence after source, harness, environment or shared configuration changes.
  A bounded pass establishes only that scope, not complete qualification.
- **Validators are shared.** Reuse production invariant validators for enforcement and when
  testing their consumers. Tests assessing a validator or semantic result retain independent
  expectations; calling the same validator for both actual and expected cannot establish its
  correctness. Preserve deliberate invalid inputs and independent reference data. This does
  not authorize a duplicate production-validation framework; use the test-assessment companion.
- Rust tests run under nextest in the release profile, so repeated runs reuse cached optimized
  code. Test data may be fresh, existing, or empty according to the test's purpose.
- **Contract snapshots** (insta), once adopted, run with `INSTA_UPDATE=no`. To accept a change,
  read the `.snap.new` diff first, then run `cargo insta accept`. Never run `cargo insta review`,
  which is interactive. A contract snapshot change is a migration, so say so in the commit.
- Python tests live under `tests/`; pytest runs with `--strict-markers --strict-config`.

## Working agreements

- **Judgment over evidence ceremony.** Principles state properties; never add probes, tests or
  oracles merely as proof of diligence. Run a check when it resolves a real question.
- **No new alignment linting.** Don't add lints or checks for design alignment; update existing
  checks only when they break. Skills are welcome.
- **Probes go to the evidence folder**, `docs/design_review/evidence/<date>_<topic>/` with a
  README, not to a session scratchpad. When a result is accepted, write its record
  (`records/<id>.json`, ADR-0010) and run `just evidence finalize <folder> <id>` then
  `just evidence`; reports take figures from `just evidence render` (evidence README).
- **Detail over length.** Architecture pages have no line budget: the detail the design needs
  comes before brevity. History belongs in Git, not in the design.

## Reporting

- Report outcomes as `passed`, `failed`, `blocked` (name the missing prerequisite) or `not_run`,
  and give the command that produced each. A mocked provider is never `passed`. Never turn
  outcomes into a percentage.
- Evidence records (`tools/evidence` `Record.outcome`) may also be `partial`: the investigation
  settled part of its question, and its conclusion names which part and what remains or moved
  elsewhere.
- Design claims carry a principles §D label (`Proposed` … `Tested` … `Measured`). An unlabelled
  claim is a defect; `Proposed` is not.
- Date every "verified" claim.

## Decisions and reviews

- **Write an ADR** (the `adr` skill) when a change alters a §B decision, chooses between real
  alternatives, or would surprise a future session. Amend the owning architectural section in
  the same commit. To pivot, supersede the old ADR; accepted ADRs are immutable.
- **Keep a current working set** (ADR-0001). Update the owner whose meaning changed instead of
  appending history. When a review or ADR loses its last current consumer, carry its surviving
  obligations forward and delete it; Git holds it
  ([historical recovery](docs/README.md#historical-recovery)).
- **Never delete plan documents or evidence** (operator direction, 2026-10-28; this overrides
  ADR-0001's retirement clause for plans and evidence until an ADR records the evidence system).
  A finished or superseded plan stays in `docs/plans/` with its status line saying so. Evidence
  folders, their results and their records stay; a revised result supersedes its record rather
  than replacing or removing it.
- **Design principle audits** use `design-principle-audit` before a diagnostic review of
  production or broad system scope. Test-only scope uses `design-principle-audit-tests` and
  the [separate test account](docs/design_review/test-audit/README.md), with the
  [test-assessment companion](docs/design_review/design_principles/core/test-assessment.md)
  selected through `[core].test_assessment`. The binding owns mixed-scope applicability and
  freshness. Accounts retain independent baselines and findings one primary home. Ordinary
  implementation or test maintenance initiates neither audit nor a full test campaign.
- **Design reviews** use `design-review` and `design-review-code-intelligence`.
  The operator selects holistic, library-targeted, principle-focused or combined review focus;
  clarify an unspecified choice. The binding owns cadence and tier; reviewers choose methods
  and depth. Ordinary implementation and focused plan advice do not initiate a broad audit.
- **Functional enhancement reviews** use `plan-functional-extension-review` / `functional-extension-review`
  to explore useful product, developer, operator or research capabilities within the operator's
  chosen scope. Publish [opportunity reviews](docs/functional_reviews/README.md); no diagnostic audit
  or principle violation is required. Design principles shape proposed realizations. Selected
  opportunities proceed through existing planning without automatic scope approval.
- **Recommendation audits** use `design-review-audit` at requested or explicitly planned boundaries.
  Publish [net changes](docs/design_review/reviews/audits/README.md), preserve the exact input in
  Git, and revise the principal review in place with new attribution. Editorial dispositions
  do not change execution status.
  Functional reviews preserve their value/opportunity lens and use their
  [companion route](docs/functional_reviews/audits/README.md), without a diagnostic audit prerequisite.
- **Completion audits** use `plan-completion-audit` for accepted scope claimed complete. Reconstruct
  obligations across implementation and consumers; correct that same plan's conclusions, package
  state, findings and next work. Distinguish implementation, qualification and benefits. These
  deliberate assessments are not recurring slice gates or authorization for production repairs.
- **Plan-improvement reviews** use `plan-improvement-review` at requested or explicitly planned
  boundaries. Review the remaining change footprint, including substantially affected supporting
  components, for design-principle alignment, general enhancements and execution improvements.
  Judge recommendations for coherent integration and total burden; their value can extend beyond
  the plan's functional target. Publish a standalone
  [plan-improvement review](docs/plan_improvement_reviews/README.md); plan revision from it is
  separately instructed. No broad audit prerequisite or automatic adoption follows; formal
  review cadence remains unchanged.
- **Findings** retain stable audit and source-review IDs. The owning active plan's findings table
  owns current disposition for scheduled work (design findings: the design-phase plan; spike and
  build findings: their own series); unscheduled deferrals stay in the source review with a trigger
  (binding §4). Record the responsible component and closure evidence; link from follow-up
  reviews and STATUS. A decision being accepted does not establish implementation or verified
  closure.

FP-07/A4 execution fit is assessed qualitatively from relevant operations and growth/failure
scenarios, with material tradeoffs explained in plain language. This consideration requires no
numerical estimates, cost models, estimators, runtime cost accounting, execution-planning machinery,
instrumentation, formal cost proofs or additional proof artifacts. Such mechanisms need a separate
concrete functional or operational requirement. Quantitative performance/capacity claims still
require measurements; semantic correctness obligations remain.

## Design-phase development database

Use the persistent `corpus_structure_dev` database on dedicated PostgreSQL18/corpus, port5434,
for normal agent implementation and functional work. The operator login `paul` has the administrative
permissions needed for migrations, restores and ownership work through the maintenance connection.
Do not require agents to create disposable databases to do that work. Native candidate authoring
can use the working database with its existing rollback-only transaction. Isolated test databases
remain appropriate where a test actually requires isolation. Application purpose roles retain their
intended capabilities. Adjust design-phase requirements and developer workflows when they create
unnecessary friction, updating the owner; the operator has authorized those adjustments.

## Agent coordination

Use subagents when another context, capability or perspective supplies useful progress, learning
or independent judgment worth briefing and integration. Shape assignments around coherent outcomes,
available inputs and shared decisions; components and role names are possible organizing aids.
Follow the [shared roles](.agents/roles/README.md), including model/effort routing,
briefs and escalation. [DESIGN §2](docs/design/DESIGN.md#section-2) owns the current workflow decision.
The root remains accountable for design coherence, integration and acceptance; workers exercise
delegated judgment within accepted outcomes and contracts. No fixed role sequence is required.
`library-research` may write assigned new dated folders under `docs/design_review/evidence/`; [its contract](.agents/roles/library-research.md) bounds those writes.

## Git

- Work on `main` in the current working tree for ordinary edits, reviews and spikes. Use a
  separate worktree only when truly parallel agents must edit production code concurrently.
  Clean up any remaining worktrees that are fully merged.
- Commit to `main` in small commits. Each message names the slice and any ADR, and states the
  test outcome. Never push unless asked.
- Never force-push or `reset --hard`.
- `.claude/skills/*` is gitignored except the process skills: `adr`, `design-review`, `design-principle-audit`, `design-principle-audit-tests`, `design-review-audit`, `plan-completion-audit`,
  `functional-extension-review`, `plan-functional-extension-review`,
  `leverage-codebase-audit`, `leverage-library-assessment`, `leverage-opportunity-review`,
  `design-review-code-intelligence`, `plan-design-review`,
  `plan-creation`, `create-plan`, `plan-execution`, `plan-improvement-review`, `execute-plan`, `handoff`, `pin-check`.
- At the end of a session that changed what's true, run the `handoff` skill.
