# A CLI for operating and developing corpus-structure

**Proposed, 2026-11-07.** Functional extension review of `025da5721`. The intended user is
Codex operating the local project and its production deployment. The target is one ordinary
entry point for actions that can be specified and repeated, including development checks and
controlled changes to the domain model. A command asks for the information needed to choose its
effect. Workspaces, output paths and intermediate invocations follow from the chosen operation.

The review uses the working tree's existing command, test, source and migration contracts and
the WCE repair journeys. Concurrent role, process and library documentation edits were present
during inspection. The current workflow map comes from code and installed help. The review read
all eight introspection overviews end to end, with independent contributions on AST and LibCST,
ast-grep and its Python binding, and Tree-sitter and FastMCP. Primary references below qualify
consequential version-specific behavior. The proposed workflows are separate from the WCE
acceptance status. [CLI owner](../design/D8-agent-and-query-interfaces.md#4-cli) ·
[Architecture standard](../design_review/design_principles/standard.toml) ·
[WCE repair receipts](../design_review/evidence/2026-11-06_wce-completion-repair/README.md)

## What the current routes reveal

The installed `ci` entry uses an explicit Typer registry and lazily initializes a single settings
object. The output adapter emits typed JSON or a Rich rendering. Database, schema, project/run,
source, contribution, query, record, structure, evaluation and review actions already have
useful owners. Several visible entries, including `ingest`, `digest` and `promote`, are
placeholders. The test supervisor, model generator, evidence and docs tools and cluster
maintenance are mostly reached through `just` or module invocations. A command listing should
describe these distinct states accurately. [Command registry](../../python/corpus-structure/src/corpus_structure/cli/__init__.py) ·
[Invocation and output](../../python/corpus-structure/src/corpus_structure/cli/output.py) ·
[Repository recipes](../../justfile)

**Tested, 2026-11-07.** Fresh installed processes with plain rendering and deliberately invalid
application settings returned help for `ci --help`, `ci schema native-candidate --help` and
`ci review export --help` with exit 0 and empty stderr. Help lists `--out` as required for the
native candidate and a destination as a required positional argument for the review export.
`ci test --help` exited 2 with an unknown command error. An unknown option to
`ci schema diff --json` exited 2 with text on stderr and empty stdout. The latter locates a
boundary between Typer usage errors and the existing JSON execution/refusal adapter. These
checks establish those routes only.

### Friction in recorded work

The Codex sample uses repository-bound session and tool records around the WCE repair and
earlier setup, model and verification work. The review follows repeated commands through
results and distinguishes an absent affordance from a legitimate refusal. The documented
examples below use repository evidence and omit private session content. Counts of shell
commands or log matches would conflate retries, parallel agents and repeated inspection.

| Observed journey | Functional improvement |
|---|---|
| Native authoring required a fresh output directory, inspection of compiler artifacts, a migration revision and predecessor, and archive admission. A duplicate revision and a determinant mismatch each produced a separate failed attempt. The earlier migration0156 workflow also shows an initial failure and a successful `ci db migrate` after repair. | Allocate candidate results and carry their exact input and target bindings through preview, apply and admission. Validate revision uniqueness and current determinants before starting the affected work. [Native repair receipts](../design_review/evidence/2026-11-06_wce-completion-repair/native/) · [Migration0156 journey](../design_review/evidence/2026-11-06_wce-definition-linking/README.md) |
| The initial parallel suite failed four identities. Later attempts had different scopes and manifests, and the exclusive fault lane ran separately. The accepted union needed explicit receipt paths and a separate classification command. | Make test scope and invocation distinct identities. Report verified coverage, the initial failure and passing replacements separately. [Qualification](../design_review/evidence/2026-11-06_wce-completion-repair/qualification/README.md) |
| Artifact export with the selected structural result alone failed verification. The succeeding selection used the exact scoped predecessors of the already-completed result. | Show missing closure and allow a policy-controlled exact dependency expansion. Retry export by identity using the existing completed data. [Artifact journey](../design_review/evidence/2026-11-06_wce-completion-repair/artifact/README.md) |
| The first contextual and table journeys used mismatched runtime or method registration bindings after a source change. Codex used per-command interpreter, import-path and shell-startup overrides around candidate authoring. | Resolve environment once, preflight the installed runtime and method binding, and emit the remedy with the failure. Preserve the difference between a semantic release and its runtime binding. [Composition](../design_review/evidence/2026-11-06_wce-completion-repair/composition/README.md) · [Table policy](../design_review/evidence/2026-11-06_wce-completion-repair/table/README.md) |
| Operation fitting already had a CLI route. The selected corpus had zero compatible emitted events and zero matching protected evaluations. | Make the applicability check and its remedy discoverable. The next action belongs to the event producer or assessment owner. [Fitting census](../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md) |

## Recommended command surface

<a id="O01"></a>

### O01 · One ordinary entry point with owned actions

Use installed `ci` for routine actions. Compose explicitly named Typer groups and keep the
operation contract and effect in the module that owns it. Prefer calling an existing Python
operation in process when it already has the right lifecycle. Invoke an existing executable
with an explicit argument vector and process supervision when the executable owns isolation,
parallel execution or tool-specific behavior. Keep `just` as a thin route to the same owner
for bootstrap, recovery when the CLI cannot start, and useful local aliases. A command is
worth exposing when it performs an owned operation or closes a repeated multi-step journey.
A generic shell pass-through would retain the decisions and failure modes this design is meant
to remove.

The following names describe the target command map. Existing public routes with consumers
can keep their spelling where the meaning matches. Migrate repository callers to the chosen
owner before removing replaced wrappers. Show capability status in generated help. A planned
product capability should appear as an opportunity in its owner, separate from executable
commands.

| Workflow | Target interaction | Required intent and normal defaults |
|---|---|---|
| Environment | `ci doctor`, `ci context show`, `ci setup` | No operands in a configured checkout. Report workspace, locked interpreter, relevant tool and service readiness, with a targeted remedy. Setup is an explicit action. |
| Database and releases | `ci db status`, `ci db check`, `ci db migrate`, `ci release check` | Use the resolved target and current compatible declaration. Require a specific target when there is no unique configured authority. Installation, admission and selection have distinct effects. |
| Project and corpus | `ci project init`, `ci ingest`, `ci run`, `ci run status`, `ci run cancel RUN` | Use the declared project/profile and its default scope where available. A new corpus or ambiguous project requires its identity. Cancellation identifies the actual run or an explicitly pinned context. |
| Read, inspect and export | Existing `query`, `source`, `structure`, `contributions` and `review` groups | Infer the configured project and default eligible completed result. Require a query, locator or explicit selection when it determines the operation. Allocate exports automatically. |
| Test and investigate | `ci test`, `ci test retry RESULT`, `ci test coverage RESULT…` | Full applicable suite by default. Selectors, lanes and tuning are useful overrides. Use the prior result identity for repair and reconciliation. |
| Model and native changes | `ci model check`, `ci model change preview REQUEST`, `ci model change apply CHANGE` | The change request states the intended meaning. The operation resolves the source revision, runs applicable generators and identifies its preview, with the deployment step bound to the intended target. |
| Repository maintenance | `ci check`, `ci format`, `ci docs check`, `ci evidence check`, `ci evidence retain RESULT`, ADR actions | Checks select the established relevant workspace by default. Fixing, generation and durable evidence promotion are explicit effects. Slugs and the result to retain are essential operands. |
| Run results | `ci results list`, `ci results show RESULT`, `ci results watch RESULT`, `ci results export RESULT`, `ci results gc` | Identity resolves its own managed location. Watch uses the existing operation state or receipt events. Export destination is optional. GC previews eligible managed results, and `--apply` performs the deletion. |

Favor typed selectors and finite choices for actual variation. Use a validated request file or
stdin for a complex selection or model change, and allow a stored request identity when it
represents the same intent. Use Typer `Annotated`, Enum or `Literal` and native `parser` for
single-value conversion, with cross-field constraints in the owned request model. A Python
call and an MCP tool should get the same validation without going through CLI parsing.
Typer 0.27.3's named groups preserve callback lifetimes. Its source assembles commands by
name in a dictionary and supports group result callbacks, while `chain=True` is absent from
the constructed group invocation path. Compose workflows as ordinary typed operations.
[Typer overview §§2–4 and addendum §§1–4, 9](
../libraries/python_introspection/typer.md) ·
[Typer 0.27.3 group construction](https://github.com/fastapi/typer/blob/0.27.3/typer/main.py#L1213-L1286)

<a id="O02"></a>

### O02 · Resolve context and prerequisites once

In a prepared development checkout, anchor relative managed paths to that checkout. Have
`ci context show` explain the effective project, database target and role, source and release
binding, interpreter and managed result root, with redacted values and their provenance.
Use the existing `Settings` precedence as the authority. Explicit applicable CLI overrides
become constructor values. Operator environment supplies deployment choices and secrets.
Application defaults supply ordinary development settings. A machine-local activation path
can supply those settings once using the existing `.envrc.local` mechanism. For headless
Codex use, recommend one checkout-aware launcher or profile that resolves the locked toolchain
without relying on the interactive shell or repeating `PYTHONPATH` and settings per command.
The existing `scripts/setup-env` remains a useful first-install boundary because a fresh checkout
has no installed `ci` executable. [Settings owner](../../python/corpus-structure/src/corpus_structure/settings.py) ·
[Bootstrap](../../scripts/setup-env) · [Environment activation](../../.envrc)

Build on the existing lazy `CliState` and acquire resources only for commands that need them.
Typer `Context`, `get_parameter_source()` and `with_resource()` can carry provenance and bind
invocation-owned resources. `default_map` is suitable only where it projects an already
resolved settings decision. Typer's parameter source can explain how the shell supplied a
value. Deployment authority still comes from the application settings and purpose role.
Short-lived commands and completion should avoid model imports and database or service setup.
Completion can suggest local profiles, declared selectors and readily available result IDs
through a bounded local read. A missing prerequisite should produce a code and one direct
remedy. Permission repair, role provisioning, service startup and dependency synchronization
are explicit operations, with the installed production target and local maintenance target
resolved independently. [Typer context reference](https://typer.tiangolo.com/reference/context/) ·
[Typer overview §§4–5](../libraries/python_introspection/typer.md)

**Acceptance example.** A fresh Codex shell uses one documented activation step and runs
`ci doctor`, `ci test` and `ci schema native-candidate` without inline environment assignments.
A second worktree resolves its own generated paths and results. An invalid settings override
names the field and its source. Help and completion remain usable with a missing database,
invalid settings or a stopped provider.

<a id="O03"></a>

### O03 · Managed results with a small retention policy

A test, candidate or export should announce an operation result ID as soon as it has a managed
workspace. Include it in the final result and use the separate diagnostic channel for the
early announcement in JSON mode. List and inspect can show a running receipt and its current
stage while the producer owns its staging files. The receipt names the action and scope, effective target, source/runtime bindings
when applicable, outcome, and the small set of available artifacts with their roles and
retention. It can refer to existing semantic run, cut, release or evidence IDs. Reuse those IDs
for semantic reads. A local export of a semantic result has its own local identity and points
back to its exact selection. An output directory is an optional delivery preference. Copy an
already-produced result to that destination while preserving its identity.

Start with an owner-controlled workspace root, an opaque ID, and a compact manifest in each
managed result. Use the checkout's ignored `build/ci/` in development and a deployment-owned
persistent state directory on an installed host. A local listing can derive its entries from
manifests with a bounded page and scope. Add an index only if real lookup workloads require
it. Publish settled manifests atomically and publish complete bundles through the existing
new-directory/no-replace mechanism where appropriate. In-progress output stays private to
the producer. Interruptions record the stage and cleanup outcome, and a retry gets a distinct
identity with a reference to the original. Neither Rich's console recording nor a copy of
every intermediate stream supplies the result authority. [Bundle publication](../../python/corpus-structure/src/corpus_structure/serve/companion_export.py) ·
[Evidence custody](../design_review/evidence/README.md)

| Output class | Minimum content and initial retention recommendation |
|---|---|
| Scratch, staging and subprocess transport | Keep until operation settlement and cleanup. Preserve a bounded diagnostic excerpt when needed for a failure. Reclaim abandoned workspace content only after ownership and process settlement are established. |
| Ordinary successful result | Keep its small receipt, named deliverables needed for retrieval, and pointers to authoritative results. Expire the local result after seven days unless a qualifying consumer needs it. |
| Failed or interrupted result | Keep exact identity, stage, exit and cleanup state and the evidence required to diagnose or reconcile that failure. Use 30 days as the initial diagnostic window. |
| Model and migration candidate | Keep exact candidate and predecessor bindings while a pending approved change or dependent result references it. An unreferenced preview follows the seven-day window. A stale preview remains inspectable within retention and requires a new preview before application. |
| Verification or review dependency | Keep the receipts required by a named active qualification or review until it settles and its required evidence is published or released. Retain the necessary portable closure for a published assessment through the existing evidence owner. |
| Committed evidence, source and functional data | Repository and domain owners govern these classes. Managed-result cleanup operates only on the workspace's derived outputs. PostgreSQL and the durable corpus remain authoritative for their own data. |

Seven and 30 days are proposed operational defaults for a sole operator's inspect and repair
loops. Revisit them from actual usage or disk pressure. Make retain/release and expiry visible in
`ci results show`. Recompute by identity only when the operation supports it and name the new
result if it does. One explicit GC command should preview and apply eligibility using the same
owner, with optional local maintenance scheduling. Skip running, held and dependency-bound
results, including concurrent exports. Handle an expired identity as an actionable unavailable
result. A compact expiry marker is useful if callers need to distinguish expired from unknown.
For test receipts, retain what the classifier actually needs for replay, replacement and audit.
Compact successful raw data only after proving that the retained representation supports its
consumers. Move durable evidence deliberately through the existing evidence workflow.

**Acceptance example.** Run a check, export a review and prepare a migration candidate without
any destination flags. From a second process, inspect each by ID, export the selected files, and
retrieve a failure's relevant diagnostics. GC leaves a live export, a referenced candidate and
committed evidence accessible, and reclaims an expired unrelated result.

<a id="O04"></a>

### O04 · Test, diagnose and reconcile from the same command family

Make `ci test` select the full declared applicable suite by default. Reuse the current
supervisor, pytest-xdist `-n auto`, nextest profile and event/receipt classifier. The default
qualified campaign runs the ordinary lane first, followed by the exclusive shared-cluster
fault lane when applicable and its existing isolation prerequisites are satisfied. A declared
required lane that cannot run reports a missing prerequisite. A lane or target selector gives
a deliberate narrower check. Keep pytest-specific options after a declared `--` boundary
using bounded forwarding to that parser. Preserve strict CLI parsing elsewhere. Give an empty
test selection its own outcome. [Current recipes](../../justfile) ·
[Test supervisor and classifier](../../scripts/test_receipts.py)

Report the invocation outcome and the required selection coverage separately. Progress names
the selected lane, active stage, completed count if known and blocked reason. Final output
names the result and the next owned action. `ci test retry RESULT` uses the existing
unresolved-selection writer and rechecks applicability to current collection/source/context.
When the changed footprint needs a broader affected selection, accept that deliberate scope
and show why. `ci test coverage RESULT…` reports missing and replaced identities and any
context differences, keeping the original outcomes visible. Neither startup warnings nor
unused Rust selections count as passing functionality.

Expose current `ready`, hygiene, docs and verification tools as named routes with direct
remedies. Separate check behavior from intentional write operations. The current `just ruff`
and `turn-end` include fixes, so the new non-mutating check command must select read-only
flags and the format/fix route must advertise writes. Preserve existing review and test
independence. A generated manifest can describe test applicability, while test expectations
and protected results keep their own authority. [Test assessment companion](../design_review/design_principles/core/test-assessment.md)

**Acceptance example.** Reproduce the WCE sequence with a retained ordinary failure, an
affected rerun and an exclusive lane. The failed attempt remains failed while the declared
union can become covered. An interrupted child settles or reports owned cleanup failure.
Retrieval and retry use result IDs and preserve full native provenance.

<a id="O05"></a>

### O05 · Deliberate human and machine output

Keep the typed result and refusal models upstream of the renderer. Reuse `emit` and
`failure_boundary` as the starting point for a consistent result/diagnostic boundary.
An automated invocation receives one structured final result or deliberate refusal on
stdout under `--json`; diagnostic events are separate. Retain Typer's usage error on
stderr with its distinct exit code, even where parsing fails before result formatting is
active. If a machine consumer later needs a structured usage envelope, qualify an explicit
entry-boundary mode on the pinned Typer API. Use public Typer help and parser APIs for the
initial target. Record an operation ID, effect phase,
redacted target and remediation in actionable errors. Native refusal, tool failure,
interruption and stale selection require different next actions. [Current failure boundary](
../../python/corpus-structure/src/corpus_structure/cli/failures.py)

Use `rich_help_panel`, short help and examples to group stable workflows and show defaults and
their meaning. Generate the command reference from the registered Typer surface and keep the
cross-command journey examples in the repository docs. Use a shared invocation-scoped Rich
stderr console for human diagnostics. Render concise `Table` or `Tree` views over the same
typed data. Render supervised progress with `Progress` or `Live` only where the underlying
operation reports truthful state. For a multi-process test run, the existing owner supplies
events and the parent renders them. Use indeterminate totals when scope is unknown, and choose
explicit refresh for sparse updates. Disable global stream interception, in particular
`redirect_stdout`, and use plain or quiet progress in headless mode. Treat external text as
literal and sanitize terminal controls separately. Configure `RichHandler` on stderr for
ordinary logging where useful. Keep traceback locals disabled. [Typer overview §§5, 8–9](
../libraries/python_introspection/typer.md) · [Rich overview §§2–7, 9–10](
../libraries/python_introspection/rich.md) ·
[Rich 15.0.0 Live implementation](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py)

**Acceptance example.** Run the same operation through terminal and redirected subprocesses.
The JSON and exit semantics are stable across width, color and progress settings. A child
warning leaves stdout intact. Help and completion start without connecting to the database.
Use `CliRunner` for grammar and stream checks in isolated processes under xdist, and an
installed subprocess for startup, actual exit, cancellation and headless behavior.

<a id="O06"></a>

### O06 · Make a declared model change an executable unit

The existing routes address different layers. The local model generator validates and
renders Stage A files. Its current generate path writes files before the revision-log
operation can refuse a later revision. The declaration-level classifier already derives
compatibility and calls for explicit input on renames, key consequences, conversions and
breaking decisions. The semantic compiler prepares composed releases. Its comparison
operation accepts prepared inputs, but `ci schema diff` currently loads both releases
from the archive. Native candidate authoring compiles against a chosen migrated
predecessor using rollback-only maintenance scope, and migration and admission have
their own authority. These are valuable primitives for a composed operation.
[Local entry point](../../python/corpus-structure/src/corpus_structure/schema/__main__.py) ·
[Declaration change classifier](../../python/corpus-structure/src/corpus_structure/schema/change.py) ·
[Semantic comparison](../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py) ·
[Native candidate CLI](../../python/corpus-structure/src/corpus_structure/cli/schema.py)

Recommend a typed preview and apply journey, with the same owned implementation available
to automation.

1. **Preview.** Accept either a diff of canonical declarations against an explicit baseline
   or a typed request for a supported recurring edit. The request states the meaning and
   supplies intent that cannot be derived, such as a rename map, conversion, authorization
   or breaking-change decision. Use the existing core/system and composed-release classifiers.
   Produce the reviewable declaration, compatibility, impact, revision and generated diffs
   in a managed result. Identify which effects are applicable, which consumers need edits,
   which dependency coverage is unknown, and which independent checks apply. A description-only
   or origin-only change can settle without database work. A read-only preview can use an
   archived release as the baseline and compare it to a local prepared candidate without
   admission. Native authoring is a separately identified rollback-only effect when needed.
2. **Apply by preview ID.** Recheck the worktree, canonical input digests, source and generator
   versions and native predecessor before touching their affected boundaries. Validate the
   entire revision request before writing generated files. Stage all deterministically derived
   work, show the complete patch, and apply only the approved paths if their source state
   still matches. Use the native candidate owner and Alembic to prepare frozen migration
   artifacts when the declared change needs them. Use the existing generated artifact and
   no-replace bundle mechanisms. When an operation spans several tracked files, preserve a
   staged patch and report which effects settled if interruption occurs. A retry validates
   what is now present and preserves concurrent edits. Treat each settled file effect separately.
3. **Deploy the approved change to a bound target.** When requested as part of the apply
   operation, compose migration, archive/admission and verification using their existing
   effect boundaries, purpose roles and predecessor or activation fences. Report each
   settled stage and resume only against its exact evidence. Keep release activation and
   selection of a completed result explicit. A candidate or runtime change cannot decide
   on its own to rewrite data, change semantic identity or promote a run. Reuse the
   persistent development target and rollback-only authoring where appropriate.
   [Native candidate owner](../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py) ·
   [Release owner](../../python/corpus-structure/src/corpus_structure/semantic/releases.py)

For this repository, typed composition earns its place where identity, applicable effects
and recovery information currently travel through manual steps. A shell recipe remains
appropriate for a short fixed sequence with no change-specific decisions. Keep canonical
generation as the primary route for declared representations. Start with local candidate
comparison and draft generation before automating edits in handwritten consumers.
A generic textual rewrite or reflection-driven change language would hide the part that
still requires semantic judgment.

| Capability | Appropriate use and limit |
|---|---|
| Python AST and `symtable` | Inventory declarations, annotations and lexical bindings without importing the code. Use `NodeVisitor` and source locations for candidates, and use the pinned Python 3.14 parser and compiler for syntax checks. Syntax and lexical binding leave runtime consumers, dynamic references and semantics to other owners. [AST §§3–6, 10](../libraries/python_introspection/ast.md) · [Python 3.14 AST reference](https://docs.python.org/3.14/library/ast.html) |
| LibCST | Use byte round-tripping, matchers and scope or qualified-name metadata for repeatable, explicitly mapped Python edits that must preserve trivia. `CodemodCommand` or `ContextAwareTransformer`, import helpers, skip diagnostics and exact-output fixtures offer a small route when a proven rewrite recurs. Qualify real repository syntax before selecting a pin. Ambiguous re-exports, reflection and external consumers stay explicit. [LibCST §§3–7, 10](../libraries/python_introspection/libcst.md) · [Codemod reference](https://libcst.readthedocs.io/en/latest/codemods.html) |
| ast-grep and ast-grep-py | Prefer the existing CLI for on-demand repository traversal and streaming candidate matches. Use rule fields and bounded relational constraints to identify consumer shapes, and inspect replacement offsets when proposing a fix. The Python binding's `SgRoot`, `find_all` and `commit_edits` fit a Python-owned snapshot if repeated in-process correlation warrants another dependency. Qualify skipped files, tool exits, overlapping edits and the distinction between CLI byte offsets and binding character offsets. Experimental outline output is navigation evidence. [ast-grep §§3–9](../libraries/python_introspection/ast-grep.md) · [ast-grep-py §§2, 5–7](../libraries/python_introspection/ast-grep-py.md) |
| Tree-sitter | Use field-aware grammar queries and `QueryCursor.matches()` where a real mixed-language scenario needs paired captures beyond the cheaper existing inventory. Report grammar, source snapshot, locations, parse recovery and truncated or unsupported coverage. Resolve dependencies and compare meaning through their semantic owners. Qualify each grammar before depending on it. A persistent index needs a demonstrated repeated workload. [Tree-sitter §§3, 5–7 and Python boundary](../libraries/python_introspection/tree-sitter.md) |
| FastMCP | Use `NativeSourceRequest` and `inspect_native_source` as the control for reusing an operation and typed result from Typer and FastMCP with separate transport/session lifetimes. Compare one field change and one typed refusal through both. FastMCP's typed tool schemas and `ToolResult` can project the same outcome. Its generated CLI is a server-backed Cyclopts client, useful when remote access is itself required. The direct local CLI avoids bringing up a server for repository, workspace and host work. [FastMCP typed tools and CLI generation](../libraries/python_introspection/fastmcp.md) · [Native source operation](../../python/corpus-structure/src/corpus_structure/serve/native_source.py) |

**Acceptance examples.** An additive SQL-visible field identifies the relational effect and
produces a correctly scoped candidate. A rename refuses until it has an explicit name mapping,
then shows its generated and handwritten effects separately. A relation-signature retirement
replays the native165 pattern and checks the affected Reader, CLI, MCP and detached consumers.
A provenance-only change avoids unnecessary regeneration. A stale predecessor or edited file
refuses before its write boundary. A runtime-only correction preserves the semantic release
where its meaning and output contract remain the same.
[Current change controls](../../python/corpus-structure/tests/schema/test_change.py) ·
[Semantic impact controls](../../python/corpus-structure/tests/semantic/test_operation_reporting.py) ·
[Native165 repair](../plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

<a id="O07"></a>

### O07 · Close routine corpus and operational journeys

Expose the current owned steps for creating or inspecting a project, reusing retained source,
running or continuing work, finalizing results, inspecting status and exporting exact evidence.
Use source, task and result authority already in PostgreSQL. Provide a short context/status
summary that distinguishes an ongoing run, an orphan, a completed cut, a private proposal,
an unavailable source prerequisite and a published result. Carry the chosen completed
result through subsequent reads and continuations. A plain read may resolve the declared
default completed or promoted result once and print its identity. Writes, cancellation,
admission and promotion require an explicitly resolved authority and target, and must refuse
ambiguity. “Latest” may help a user find an attempt and cannot silently choose a write target.

For portable review export, resolve the user's result and scope once. Offer a documented exact
dependency-closure mode that derives only the retained predecessors required by the selected
product, subject to the existing role and byte bounds. Report what was included and why. Where
a predecessor is missing or inaccessible, emit the missing dependency with a direct remedy.
A result view or test retry should never trigger PDF conversion, recognition or another provider
run just because a local export expired. A fitting command should report compatible-event and
protected-evaluation prerequisites when the selected corpus has none. [Portable closure owner](
../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) ·
[Operation fitting availability](../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)

Use a small production operations family for health, database contract checks, migration and
admission, service status and bounded exports. Use the existing idempotent host tooling as the
implementation owner for local cluster provisioning and roles. Give privileged effects their
own explicit command, with scope and purpose visible before execution. The persistent
development target is the normal implementation target. Temporary databases are useful for
tests requiring isolation. The production profile binds the configured production target and
role and avoids implicit local provisioning. A supported backup/restore command is valuable
once its operator, storage and recovery responsibilities are specified and rehearsed. Source and
semantic recovery need their own authoritative owners. A filesystem results sweep cannot perform
that recovery. [Database authority and native custody](../design/D3-database.md) ·
[Run supervision](../design/D6-orchestration-metrics-policies.md)

**Acceptance example.** From a completed corpus run, inspect its source and status, export
exact closure, verify the bundle and retrieve the export by identity. Resume after an
interrupted export using the existing completed cut. A read-only production role can inspect
health and compatible status. A deliberate deployment fails early on the wrong target or
predecessor and reports each settled effect if later admission fails.

## Priority and design decisions

| Recommendation | Priority and dependency |
|---|---|
| O01, O02 and O05 | Establish stable names, cheap help, effective context, consistent output and direct remedies first. Route one existing command through these decisions before changing the whole tree. |
| O03 and O04 | Implement the first complete destination-free journey for test execution, retrieval and retry. This exercises identity, retention, concurrency and cancellation using an existing supervisor. Extend the same result ownership to native candidates and review exports after confirming fit. |
| O06 | Start with the local comparison and typed revision preview. Add apply and native deployment composition once stale, partial and resumed effects are correct. Qualify a codemod only where an observed recurring handwritten transformation warrants it. |
| O07 | Close corpus and release journeys using the same context and result primitives. Select privileged service and backup/restore routes as their operation ownership and recovery scenarios become concrete. |

The main choices to accept before implementation planning are the CLI as the ordinary route
and `just` as bootstrap/alias tooling, the managed result lifecycle and initial expiry defaults,
and the effect boundaries for applying model changes and deploying them. That changes
developer workflow guidance and the D8/D9 interface descriptions. Canonical model authority,
purpose roles and native transaction/admission guarantees remain decisive constraints on each
proposal. Assess rollout command by command, migrating callers and testing both the typed
operation and its installed consumer. Keep direct lower-level tools available through the
bootstrap or documented recovery path.

The recommendation uses one authority for each fact and a small typed composition of existing
operations. This serves FP-01–FP-06 and A1–A3 by making ownership, identity, explicit effects and
replaceable adapters visible. FP-07/A4 favors shallow local help and result discovery, batching
at subprocess and database boundaries, and retaining the smallest replayable evidence. These
are qualitative execution-fit judgments. A durable generic workflow engine, automatic discovery
index, full-screen terminal application or generated second CLI would add work without an
identified consumer in the current sample.
[Design principles](../design_review/design_principles/core/design-principles.md) ·
[Execution-fit heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) ·
[Code-intelligence guidance](../design_review/design_principles/profiles/code-intelligence/principles.md)

**Verification boundary.** The installed help and usage smoke checks above are the runtime
observations for this review. Product qualification, provider execution, migration, cleanup and
codemod probes were `not_run`. The acceptance examples define what the proposed capabilities
would need to demonstrate.
