# File-free reporting through the installed CLI

**Reviewed 2026-11-07 · Proposed extensions.** The scope is routine inspection and composition by
people, Codex and scripts. Each should be able to see the needed result or pass it to another
command without creating, exporting or reopening a scratch file. Managed receipts support replay
and diagnosis, detached bundles support handoff, and internal staging supports custody and atomic
publication. Those purposes constrain the review.

The inspected checkout started at `9fb9c9185` with concurrent changes in the failure adapter and
its tests, and in corpus/model/native code. The observations below name their actual commands and
data. The review does not qualify those concurrent changes. The locked environment is Python
3.14.10, Rich 15.0.0 and Typer 0.28.0. The library inventory includes both overviews and all their
addenda. Source-derived findings from Typer 0.27.3 are treated as leads where the 0.28.0 guide or
the installed pin has no confirming evidence. [Rich overview](../libraries/python_introspection/rich.md) ·
[Typer overview](../libraries/python_introspection/typer.md) ·
[CLI owner](../design/D8-agent-and-query-interfaces.md#4-cli) · [ADR-0069](../adr/0069-cli-operations-custody.md)

**Recommendation.** Start with direct test failure and coverage reports and a managed model
preview reader. Both replace an actual read-and-filter workflow. Give the selected data a clear,
bounded Rich presentation, and expose structured projections for agents and pipes. Apply the same
approach to review evidence and recipe diagnostics where the owners can answer a named question.
Reserve dynamic progress and logging changes for decisions the simpler routes cannot support.

## Current workflows and evidence

| Journey | Observed route and friction | What a direct route needs |
|---|---|---|
| Reconcile tests | `ci test coverage` already pipes directly to a decoder. The 179-node held example with `COLUMNS=80` emitted 598 human-output lines. JSON selected through the pipe showed the original attempt failed, the retry passed, 179 required, zero unresolved, zero missing lanes and changed source context. A separate 5,119-node selection emitted 685,475 JSON bytes for a direct pipe extracting counts and unresolved nodes. | A decision-sized report from the classifier. Keep attempt outcomes, node coverage and source applicability separate. [Coverage adapter](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L233) · [Classifier](../../scripts/test_receipts.py#L988) |
| Find the failed node | On held attempt `895619a228b442e2b9a654f47ea98270`, `ci results show` reported settled custody, 179 selected, 178 passed and one failed. It reported a truncated tail and a retry command. The tail counts showed four passing call records and supplied no failed node identity. Watch can announce newly seen failures within its cursor budget. | An exact, bounded lookup of failed nodes by lane and phase, plus evidence availability. A tail view still serves active work. [Managed diagnostics](../../python/corpus-structure/src/corpus_structure/cli/managed.py#L775) · [Receipt tail](../../python/corpus-structure/src/corpus_structure/cli/managed.py#L890) |
| Inspect proposed model work | `ci results show 64160d62f0a0497b95c06015df345ed1` exposed roles `preview` and `patch`. `ci results export … --role patch --json` returned the existing patch path. The retained native candidate `246dae08ce714974aca49c6bb1cb8532` exposed three artifact roles. The preview's initial response gives effect identity and changed paths. The semantic comparison, discovered consumers and patch require a further read. | Direct review of the bound preview's effects, patch and discovery by preview ID. Inspect the existing candidate by ID when deciding what to register. [Preview production](../../python/corpus-structure/src/corpus_structure/cli/model.py#L181) · [Bound artifact reader](../../python/corpus-structure/src/corpus_structure/cli/model.py#L56) |
| Read corpus review evidence | `ci review inspect` passed against the held detached bundle for run 205/cut 283. Its fields included selection, relations, original source completeness, assessment scope and completeness. The command takes a path, so a managed-result caller first resolves the bundle path. Export requires a selection path. Model preview already accepts `-` on stdin. | Inspect the managed bundle by ID and accept a typed selection from stdin when another process produces it. Keep detached verification available for handoff. [Review command entry points](../../python/corpus-structure/src/corpus_structure/cli/review.py#L222) · [Selection contract](../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py#L54) |
| Check target, tools and reference | `ci db status --json` observed `corpus_structure_dev` on port 5434 as `corpus_sem_reader` with purpose `read`. `ci context show --target deployment --json` returned a typed missing-profile refusal. Recipe checks collect child stdout/stderr, redact and retain suffixes of 12,000/6,000 characters in one report. `ci docs commands` generates Markdown and returns a managed path. | Keep acquired identity, action and failure distinct from a configured profile. Surface the failed check and a useful bounded excerpt. Provide direct help or reference text where the user only needs to read it. [Recipe report](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L40) · [Process ownership](../../python/corpus-structure/src/corpus_structure/cli/recipes.py#L32) · [Reference generator](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L136) |

A headless caller can already pipe JSON in several of these journeys. Direct pipes avoid scratch
files but still require the caller to know the full shape, buffer or filter the response, or
retrieve another path. Rich can make a selected answer easy to read. Selection, meaning, and
stream compatibility are contracts of the CLI and the underlying report owners.

## Recommended reporting capabilities

<a id="O01"></a>
### O01 · Answer the immediate question, then offer bounded detail

**Proposed, first shared slice.** Give selected high-value commands a default human summary with
stable identity, outcome, relevant counts or stage, and next action. Use a flat layout that reads
well in a headless transcript. Add named projections only where a caller repeatedly asks for
detail, such as failures, unresolved nodes, effect summary or patch. A projection should carry its
subject identity, selection, count semantics and completeness or availability. Page using
owner ordering and bounds when the detail can grow. Human labels and colors must express the
same facts as the projection. Expose the rule for any omitted detail.

Keep `--json` with its existing full typed shape for callers that use it. A named projection may
have its own small typed result in JSON mode. Plain output for automation should have an explicit
contract where there is a real line-oriented consumer. Compare four choices:

| Alternative | Judgment |
|---|---|
| Full JSON piped to a selector | Useful immediately for unusual questions and scripts already using the schema. It still transfers the full payload, including at the classifier subprocess boundary. |
| Default Rich formatting over the whole result | Improves legibility on small objects. Large nested output still makes the caller find the answer. |
| Named owner-backed projections | Recommended. Keep criteria close to the owning operation and use the same projection for human and machine views. |
| Generic field/path/filter language | Defer until multiple real consumers need arbitrary selection. It adds grammar, shape stability, and visibility questions. |

Use the existing `emit` seam with command-owned typed projections. Compare an invocation-scoped
`Console` in existing `CliState` with the current per-call construction when progress and
diagnostics need to coordinate. Keep explicit stream routing at the boundary. `Table` and
`Table.grid` suit narrow summaries. Use `Group` for headed sections, `Tree` for a bounded
hierarchy, and `Columns`, `Panel.fit`, `Rule`, `Align` and `Constrain` where they improve
reading order. Prefer wrap and meaningful labels over hiding relevant columns. Style explicit
`Text` spans after redaction and terminal-control handling. Use a semantic `Theme` only when
several reports share status meanings. Include a stable readable presentation for pipes without
cursor updates, color assumptions, or mandatory paging.
The synthetic probe produced a seven-line table at widths 44 and 100, while whole-payload
Pretty output used 10,247 and 5,125 lines. This compares shapes with different selected content.
[Existing emitter](../../python/corpus-structure/src/corpus_structure/cli/output.py#L48) ·
[Rich console, text and layout](../libraries/python_introspection/rich.md#2-rendering-architecture-console-renderables-and-segments) ·
[Typer parameter model](../libraries/python_introspection/typer.md#3-typed-parameters-conversion-and-validation)

<a id="O02"></a>
### O02 · See exact test failures and actionable coverage by ID

**Proposed, first consumer.** Put compact coverage counts at the classifier boundary and expose
bounded failed or unresolved identities with lane, phase, and reason where the owner can establish
them. The current `--summary` subprocess response still contains all required node IDs. Project
counts before serializing across that boundary and retain full classification for the existing
full-detail route and exact retry. Source/context differences, missing lanes, unsettled custody,
and original failure each keep their own meaning. A reconciled union is evidence for the
selected requirements. The owning plan judges source applicability.

Illustrative interactions are `ci test coverage ORIGINAL RETRY` for a short outcome/coverage
summary and `ci test coverage ORIGINAL RETRY --view unresolved --limit 20 --json` for typed
drill-down. An existing failure could be inspected by `ci results show ID --view failures`
or a test-owned report command. Prefer the test-owned command if the output needs test-specific
filters or joins. Reuse the classifier's canonical node identities, failure stages, and native
observations. For a still-running attempt, report partial availability and use the existing
cursor. A tail that omits a failure cannot establish that it did not occur. The next-action
projection can name retry, recovery, or a fresh lane without taking the effect.
[Classifier coverage and compact dispatch](../../scripts/test_receipts.py#L988) ·
[Test retry selection](../../python/corpus-structure/src/corpus_structure/cli/testing.py#L312)

<a id="O03"></a>
### O03 · Inspect reviewed effects and managed artifacts in place

**Proposed, first consumer alongside O02.** Use an owner-specific read such as
`ci model change inspect PREVIEW_ID` for authority, effects and semantic impact, with a named
patch or discovery view. Reuse the action, settlement and digest checks that the existing model
loader applies. Read the patch from the verified preview if that is its exact bound copy.
Use `Syntax` with the diff lexer, line ranges and highlighted locations for selected hunks.
Show total versus displayed hunks, exact preview ID and target so the user can decide whether to
apply. A raw-text projection can pipe a requested diff; script-oriented output keeps its own
bytes and exit contract. Apply and deploy still use the original bound inputs under their
existing effect rules.

Use the managed owner to authenticate roles and hold the lease through every read, including
an explicitly requested stream. The current export without a destination yields a path after
its lease ends. Shell substitution removes a caller file but leaves a later open racing with
retirement. A role that names a directory cannot safely be treated as an arbitrary filesystem
browser. Start with named, safe textual views and owner decoders. Consider a generic bounded
content command only after multiple compatible roles demonstrate a shared need. Distinguish
unknown role, expired or missing result, unavailable content, and verified empty output.
Read operations acquire a lease for the read; protection beyond it follows the named hold and
expiry policy. Current lookup can serve a physically retained result while a new dependency
is subject to an expiry check. Preserve that distinction and report expiry only when the
owner has evidence for it.
[Managed read and delivery](../../python/corpus-structure/src/corpus_structure/cli/managed.py#L545) ·
[Model artifact verification](../../python/corpus-structure/src/corpus_structure/cli/model.py#L56) ·
[Rich source excerpts](../libraries/python_introspection/rich.md#6-advanced-source-code-presentation)

<a id="O04"></a>
### O04 · Compose review and corpus reporting over typed inputs

**Proposed, next consumer.** Use `ci review inspect --result RESULT_ID` as a candidate route to
verified coverage under the managed lease. Resolve the authenticated bundle, preserve the
detached verifier's digest, relation and member checks, and anchor any member opens used for
managed lookup. Measure work qualitatively against bundle size and lookup frequency. If a cheaper
manifest-only view is valuable, label it as unverified and retain explicit verified inspection.
A plain path stays useful for detached verification. Offer named, bounded corpus and evaluation
views over run, cut and release identity, preserving witness attribution and the owner's
continuation or ordering where applicable. Use the existing fitting applicability result before
considering any new fit events.

An intentional `-` input for review selection can use Typer `FileText` or the explicit
`get_binary_stream("stdin")` boundary when exact bytes matter. `Path(allow_dash=True)` alone
admits the token. Parse once into the existing selection model, enforce the same byte, selection
and role limits as for path input, and pass the accepted selection to the existing owner. The
managed invocation retains its bound selection for replay. Separate stdin, file and managed-ID
inputs where their meanings differ. The evaluator route retains its independent authority.
[Review export and inspect](../../python/corpus-structure/src/corpus_structure/cli/review.py#L222) ·
[Detached verifier](../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) ·
[Typer standard streams](../libraries/python_introspection/typer.md#6-file-streams-and-unix-style-command-composition)

<a id="O05"></a>
### O05 · Surface the failing check and offer direct command reference reads

**Proposed.** Let a recipe owner report its step identity, outcome, exit or refusal, and bounded
excerpt where it changes the next action. Prefer an existing tool's typed output or a small
owned recipe summary to regex over a combined human transcript. The `just` bundle already
knows step order, individual exits and failed steps. Add a structured route there if needed
and keep the direct recipe's human output. Keep a text excerpt for
foreign tools with no structured mode, with explicit truncation. Compare an end-of-command
summary with bounded streaming of useful messages, using the current process group and
cancellation owner. The current suffix bounds limit emitted text. An alternative reader also
needs to bound memory and avoid blocking on one pipe while the other fills. A human Rich view
can use `Syntax` excerpts for a source diagnostic or plain literal `Text` for raw output.

For installed help, use Typer's public `rich_help_panel`, `rich_markup_mode`, option descriptions,
explicit metavars, contextual usage, and command/group help as the primary route. Name result
views and safe next steps in help. Compare direct command-reference stdout with the existing
managed publication mode where readers specifically need the whole Markdown. Reuse Typer's
registry and generator. Test that help and completion stay cheap and free of effectful lookups.
The metavar correction is verified on 0.28.0. Check completion with a fresh shell before relying
on callback arguments or metadata beyond the known Bash fixture. Keep raw `--` validation for
delegated test arguments at the existing entry point.
[Recipe reporting](../../python/corpus-structure/src/corpus_structure/cli/operations.py#L40) ·
[Typer help and completion](../libraries/python_introspection/typer.md#5-shell-completion-and-cli-discoverability) ·
[Pinned Typer observations](../libraries/python_introspection/typer.md#90-typer-0280-behavior-update)

<a id="O06"></a>
### O06 · Show live work and preserve stream contracts

**Proposed, conditional on the operator decision.** Begin with stable stage and count lines.
Use `Status` for a single indeterminate stage, and consider `Live.update` or `Progress` only
when a user needs to see multiple changing tasks or an actual count. The supervisor and
result owner supply facts. Use a single invocation-owned stderr console, explicit refresh
driven by meaningful observations, and `redirect_stdout=False` and `redirect_stderr=False`.
Use `Task.fields`, named columns and `total=None` when the owner lacks a denominator.
Where progress is applicable, compare bounded update cadence, `ProgressColumn.max_refresh`,
`get_time` for deterministic checks, and task reset for real retries. Show settled outcome
only after owner settlement. Headless output can use a compact line per meaningful stage and
one final result. A TTY can add a live view without changing the work or the machine payload.

An installed pipe control with a consumer that closed immediately yielded a Python
`BrokenPipeError` at stdout flush and Bash `PIPESTATUS` of `120 0`. Establish an explicit
broken-pipe outcome before adding more stream routes. Prefer concise termination without a
traceback, preserving an already known operation failure. Compare a distinct nonzero pipe
status with quiet cancellation for explicitly stream-oriented reads, using real downstream
consumers and `pipefail`. A truncated machine document cannot stand as a complete result.
Keep usage errors, typed refusals, unexpected exceptions and cancellation distinct. For
authorized debug use, compare bounded `Traceback.from_exception` with exception groups,
notes and locals disabled. A render or stream failure must preserve the operation's
settlement record and allow retrieval by ID.
[Existing output boundary](../../python/corpus-structure/src/corpus_structure/cli/output.py#L56) ·
[Rich Live and Progress](../libraries/python_introspection/rich.md#6-live-displays-progress-and-execution-state-visualization) ·
[Typer exception behavior](../libraries/python_introspection/typer.md#8-testing-and-diagnostic-inspection)

<a id="O07"></a>
### O07 · Add diagnostic data only for a demonstrated missing answer

**Proposed adoption boundary.** The sample outcomes, failure identities, held patch and fitting
states are already owned by results, receipts, or the selected domain operation. New
instrumentation has no first-slice value for those cases. The plausible gap is foreign or
pre-failure context absent from an existing receipt, such as which supervised child step last
made progress before cancellation. First compare an existing status or process receipt, an
explicit owner event, and an invocation-scoped stdlib handler. A selected `RichHandler`
can display useful stdlib records on stderr with explicit markup and traceback policy.
Its input still requires redaction, record-size limits, and a clear effect on the report.

| Candidate | Disposition and adoption condition |
|---|---|
| stdlib `logging.Handler` / `MemoryHandler`, Logbook `FingersCrossedHandler` / `GroupHandler` | Compare only when preceding events can explain a failed action. Bound total bytes as well as record count, release references, and test trigger, overflow and close. Logbook adds a second dispatch lifecycle, and the wrapped handler's filtering semantics need checking. [Logbook buffering](../libraries/logging/logbook.md#61-fingerscrossedhandler-retain-context-until-escalation) |
| structlog `bound_contextvars`, `merge_contextvars`, `ProcessorFormatter`, `foreign_pre_chain`, `wrap_for_formatter` | Best conditional structured enrichment when app and stdlib sources need the same approved invocation or stage fields and the small stdlib route duplicates work. Apply context in the producer and pass approved correlation fields explicitly across process boundaries. Test configured output in a real process as well as any `capture_logs` assertion. [structlog](../libraries/logging/structlog.md) |
| Loguru `bind`, `contextualize`, `patch`, callable sinks, Eliot actions | Defer. Consider Loguru for a concrete reusable sink or enrichment contract and Eliot when causal action nesting changes a user decision. Account for extra routing, buffer or queue ownership and flush. Logging ancestry cannot establish product completeness. [Loguru](../libraries/logging/loguru.md) · [Eliot](../libraries/logging/Eliot.md) |
| Python JSON Logger `JsonFormatter` and ECS formatters | Conditional on a named downstream diagnostic schema. Formatting does not supply missing data or define the typed CLI result. [JSON Logger](../libraries/logging/python-json-logger.md) · [ECS logging](../libraries/logging/ecs-logging.md) |
| OpenTelemetry spans and links, Logfire typed spans, in-memory exporters for tests | Revisit only for a named cross-service decision the local receipt and operation IDs cannot explain. Evaluate filtering, redaction, propagation, sampling and exporter lifetime with that consumer. A collector, incident store and production-wide instrumentation would be separate investments. [OpenTelemetry](../libraries/logging/OpenTelemetry_Python.md) · [Logfire](../libraries/logging/pydantic-logfire.md) |
| picologging | Defer until profiling establishes a logging bottleneck and compatibility with the installed Python and needed handlers. [Unified logging overview](../libraries/logging/Python_Structured_Logging_and_Observability.md) |

Keep diagnostics bounded and redact before buffering, forwarding or rendering. Prefer a
scoped live excerpt to persistent storage. If a post-settlement consumer needs the same
excerpt, use the existing managed lifecycle with explicit availability and budget. The
accepted cancellation of the earlier observability plan is the baseline.
[Prior I10 comparison](../plan_improvement_reviews/cli-operations_2026-11-07.md#i10--make-cli-diagnostics-actionable-within-the-result-lifecycle)

## Additional library dispositions

| Family | Judgment |
|---|---|
| Rich low-level renderables, `Layout`, hooks, `ConsoleOptions`, `Measurement`, `render_lines` and segment cropping | Conditional on a concrete responsive view the stock components cannot compose. Keep owner bounds ahead of rendering. A render hook has shared stack/lifetime implications and supplies neither trusted selection nor sanitization. |
| Rich `Console.capture`, `StringIO`, recording, export text/HTML/SVG and themes | Use bounded in-memory capture for test assertions or a named downstream presentation consumer. Recording retains rendered segments, so prefer direct output for ordinary reports. A visual export requires deliberate request and custody. Scoped themes and style spans can help accessibility. Treat ANSI decoding as a rendering transformation after safety checks. |
| Rich `Pretty`, `__rich_repr__`, JSON, Markdown, specialized highlighters and lexers | Use bounded developer detail, explicit human JSON and selected Markdown/diff content where they add meaning. `JSON.from_data()` has serialization choices including non-finite values. Retain the typed serializer for machine results. Introduce custom Markdown elements, lexers or regex highlighters when a stock renderer cannot present a concrete case. |
| Typer typed selectors and provenance | Use `Annotated` options, `Literal`/enum, repeatable list parameters, bounds and local parsers or callbacks. Validate combinations after parsing. Check `get_parameter_source`, `show_default` and `show_choices` for useful provenance. Compare `default_map`, environment and tri-state controls only where existing settings ownership permits. Keep eager and callback-only options conditional. |
| Typer context, teardown and extensions | Prefer explicit named groups and existing emitter with scoped `ctx.obj` or namespaced `ctx.meta`. Compare `with_resource` and `call_on_close` for a real lease or presentation lifecycle. Use `result_callback` only if returned report and cleanup order need it on the actual pin. `Context.invoke` is a callback helper. Consider `TyperCommand` or `TyperGroup` overrides when a required hook is absent and help, completion and invocation can stay coherent. UNIX pipes and owner operations supply composition without relying on Click plugins or the older unimplemented chaining path. |
| TTY-only extras | Explicit paging can help a human read long detail. Compare terminal dimensions, prompts, single-character input and `typer.progressbar` only for a named interactive case. Full-screen controls, REPL inspection, notebooks, widgets and decorative effects add no demonstrated value for this reporting target. |

[Rich integration details and addendum](../libraries/python_introspection/rich.md) ·
[Typer invocation and parameter addenda](../libraries/python_introspection/typer.md)

## Design boundaries and evidence for selection

FP-01–05 and DP-01/02/08/18/19 place report meaning, selection and effect with the
existing owners. Under FP-06/07 and DP-14/20/21, materialize only the requested detail and
avoid moving whole classification results or holding resources while a person reads an
unrelated page. For code-intelligence excerpts and corpus evidence, preserve attribution,
bounded selection and the distinction between unknown and absent under CI-01/04/08/11.
The current architecture supports additive views and input routes. A change to the existing
full JSON shape or exit semantics would need an explicit compatibility decision. The
proposed broken-pipe contract needs selection and proof before adoption. Logging or
interactive modes carry their own value decision.
[Applied design standard](../design_review/design_principles/standard.toml) ·
[Execution heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) ·
[Binding](../design_review/design_principles/binding/corpus-structure.md)

| Acceptance example for later implementation | What would establish the benefit |
|---|---|
| Failed ordinary campaign, exact retry, then coverage | Read the failed node, phase and next action from the original ID. Inspect retry coverage with original outcomes, missing lanes, source differences and counts all distinct. A changed source remains visible. Run the entire read and retry interaction with zero caller-created scratch files. |
| Model preview and authorized later effect | Review semantic changes and selected diff hunks from the preview ID, with the bound target and source witness. Try an expired or substituted artifact and distinguish that refusal. Verify the review path does not register or apply a change. |
| Managed and detached corpus report, plus a piped selection | Inspect the same authorized projection using managed identity and the detached verifier as applicable. Exercise a malformed or oversized stdin selection, a corrupt bundle, a missing prerequisite and two distinct sources of partial coverage. Preserve all relevant limits and attribution. |
| One failed check and one interrupted long operation | From the report identify the failed step or unresolved custody and the next correct action. Use wide and narrow terminals, a headless subprocess and a pipe. Check safe literal Unicode, embedded markup, controls and credential-shaped data, clean JSON stdout, meaningful stderr, broken-pipe behavior and cancellation cleanup. |

Use independent expectations for report meaning and actual stream output. `CliRunner` can
exercise grammar, output bytes and invocation return values. Real installed subprocesses and
PTYs should exercise actual stream routing, cleanup and completion. The
[bounded probe record](../design_review/evidence/2026-11-07_cli-reporting/README.md) establishes
the observed library and current CLI behavior only. It does not establish the proposed API,
resource capacity, performance improvement, or production/provider qualification.
