# CLI operations after the introspection and logging capability review

**Reviewed 2026-11-07. Proposed amendments.** The [CLI operations coordinator][plan] and all four
companions at `40dc403a1` are the plan baseline. CLI-00–08 are proposed. The inspected product
tree at that commit still uses Typer 0.27.3, Rich 15.0.0 and FastMCP 4.1.3. The target for this
review is Typer 0.28.0. Selected fixture and installed-command observations are dated in the
[evidence][evidence]. Native changes, provider calls and product qualification were `not_run`.

## Judgment and coverage

Keep one installed command surface with thin adapters, the established `just` recipe layer,
and independently owned product operations. The amendments with the strongest integration case
are to qualify 0.28 before widening the command tree, make parser and settings intent explicit,
secure diagnostic rendering, and make test and result settlement precise across process and
retention boundaries. For model changes, finish the canonical preview before making source
discovery more expressive. Prefer a shipped LibCST rename only for a demonstrated, explicit
Python migration. For corpus journeys, strengthen shared refusal semantics and read authority
before adding transport features. Adopt only diagnostics tied to an operator action, as proposed
in I10, with the smallest useful capture and retention boundary.

The footprint includes [command/context][command], [results/testing][results],
[model/deployment][model] and [corpus/operations][corpus], including their affected callers.
Inspection followed D2 declaration/revision ownership, D3 purposes and admission, D6 task
ownership, D8 read and delivery, D9 tooling and the test-resolution substrate.
The operator directed this review to treat the existing observability plan as cancelled.
Its completed investigations inform the comparison as historical evidence. No LOG package is
a dependency or presumed future delivery. The review applied core FP-01–07/A1–A4, execution-fit
heuristics, the test-assessment companion and CI-01/02/04/06/08/10–12 for source evidence. Static
findings cover the cited implementation and consumer paths.
[Selected standard](../design_review/design_principles/standard.toml)

All eight introspection references were assessed, including earlier material and all six working-tree
additions. The first columns identify the input and its Git blob before the Typer documentation
edit. Topics without an integration case are included so the disposition of both older and newer
capabilities is visible.

| Reference and input blob | Capability assessment |
|---|---|
| [Typer][typer] · `b337898f1` | Use explicit groups, documented option grammar, context provenance and lifetimes, Markdown generation and public testing. Recheck advanced callback/default/metadata semantics on 0.28. Use stream/file helpers only inside the existing contracts. Interactive prompts, raw terminal input, custom parser subclasses, automatic subapp flattening, chain workflows and a new usage envelope have no current consumer that warrants their complexity. I01–I02. |
| [Rich][rich] · `76a23efe9` | Use scoped Console, Text, Table/Tree and progress. Consider source excerpts and exception-group views where the owner provides safe, selected fields. Render hooks, measurement and line APIs may help presentation tests or a real layout problem. Global console state, interactive prompts, notebook/UI, Markdown extensions, ANSI interpretation and HTML/SVG capture have no role in typed output or durable evidence. I03–I05. |
| [Python AST][ast] · `ae37cadf2` | Bounded syntax and compiler-assisted scope discovery earns use. Structural comparison and source segments support explanation. Literal interpretation, code generation and transformation are outside the handwritten patch path. Python 3.15 lazy-import controls are beyond the pinned interpreter. I06–I07. |
| [ast-grep CLI][sg] · `1bbde17a3` | Existing structured scan, context selectors and relational captures cover scoped discovery. Keep outline for navigation. Rewrite, recursive utilities, transformations, new grammars and LSP integration need their own demonstrated use. Existing lint and rule tests retain their scope. I07. |
| [ast-grep-py][sgpy] · `4c6ef5547` | Conditional in-process matching when repeated, related queries reuse a source snapshot. Ordered composite predicates and recursive utilities can replace bespoke traversal in a proven case. Sibling selectors, variadic captures and transformations add no evidenced first-slice need. Coordinate and result-coverage contract must precede adoption. I07. |
| [Tree-sitter][ts] · `fabf62f75` | Conditional paired captures and syntax recovery with declared scope and grammar. Defer incremental storage, injection/custom grammars, direct-buffer optimization and assumptions of GIL-free parallelism. The installed callback crash changes the cancellation design. I07. |
| [LibCST][cst] · `da3276e01` | Compare shipped rename with manual explicit patch for concrete recurring edits. Use lossless parse, metadata and import helpers where needed. Defer annotation reconciliation, broad modernization, dataclass conversion, experimental reentrant generation and repository-wide caching pending an owned workload. Grammar support alone does not establish metadata fidelity. I08. |
| [FastMCP][mcp] · `3e133075b` | Reuse typed tool results and existing lifecycle. Progress can project owner events. Consider authorized resources or transforms only for a real consumer. Prompts, UI apps, federation, generated Cyclopts CLI, middleware caching and Docket tasks do not improve the selected local or production journeys enough to justify another runtime or authority. I09. |

## Command surface, diagnostics and evidence

<a id="I01"></a>
### I01 · Qualify Typer 0.28.0 before CLI-01 migration

**Version premise and execution improvement · CLI-00/01/07/08.** Pin `typer==0.28.0` during
implementation in a bounded dependency change. Keep other selected versions unless compatibility
requires a specific move. Validate manifest and lock changes, then rerun affected contracts. This
decouples a framework transition from changing flags and moving callers in the same slice.

The tag changes default option spelling when a case-matching custom `metavar` used to supply
capitalization. A fixture accepted `--ITEM-COUNT` on 0.27.3 and `--item-count` on 0.28.0.
Explicit aliases and display metavar remained usable. Static inspection found current CLI custom
metavars on positional `Argument` declarations, with no matching option declaration to migrate.
Check scripts, docs and generated reference as commands change. Declare explicit stable aliases
where a spelling is part of the public contract. The isolated 0.28 overlay passed root and nested
help, unknown-option exit 2 with clean stdout, and Markdown generation with invalid DB settings.
That is a bounded smoke result. Test the final installed version and changed command grammar at
CLI-08. `CliRunner.invoke()` covers parsing in isolated processes. Use fresh subprocesses for
streams, bootstrap, shell completion and process-level controls. (DP-15/23/24.)
[0.28.0 release](https://github.com/fastapi/typer/releases/tag/0.28.0) ·
[Tagged option construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py#L1361-L1365) ·
[Tagged runner](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py) ·
[Probe][evidence]

<a id="I02"></a>
### I02 · Resolve invocation intent after parsing and delimit recipe forwarding

**Alignment and usable defaults · CLI-01/03/07.** Keep explicit `add_typer(name=…)` and named
recipes. In a command, obtain syntax and provenance with `Context.get_parameter_source()`, then
construct one owned request. Put cross-field validation, target selection, effects and redaction
in their existing owners. Treat the source as provenance, not authority. Use paired optional Boolean
flags only when inherit, enable and disable have distinct meanings. Keep callbacks to local
conversion or presentation, and use `Context.with_resource()` only after successful resolution.
In both releases, an explicitly supplied later option ran before the earlier default in the
fixture. Its callback saw partial `ctx.params`, and default callbacks ran. Do not let eager/default
callbacks start providers or make a target-dependent decision. Reserve `expose_value=False`
for a genuine control input that belongs in the adapter.

On Bash completion both versions supplied `args=[]` and parsed context including a default.
Only bounded, local, side-effect-free suggestions should depend on safe parsed context. Check
parameter provenance where meaningful, and return static suggestions or none when authority is
ambiguous. Avoid a second settings overlay in Typer. Conditional prompting may serve a named
human interaction, but cannot be necessary for headless operation or stand in for effect intent.

A qualification-specific explicit separator is stronger than generic `allow_extra_args`: the
fixture gave the same `ctx.args` for extra positional input before and after `--`. Isolate raw
separator handling at the named `ci test` entry boundary, parse the prefix strictly, and pass the
literal suffix through the allowlisted recipe with `[positional-arguments]` and quoted `"$@"`.
Preserve mandatory lane policy, receipt destinations, required plugin and security controls at the
supervisor. Permit customization only when the owner can represent it in scope and receipts.
Check both shell layers with spaces, literal metacharacters and option-looking values. A bounded
`just` fixture establishes quoting, and the current `test-all` recipe has the same forwarding
form. Validate the final installed chain with a small selection and independent expected argv.
Keep direct recipes as bootstrap/recovery and ensure no `ci → just → ci` cycle. (FP-01/04/05,
DP-01/08/14/24.)
[Typer 0.28.0 completion](https://github.com/fastapi/typer/blob/0.28.0/typer/core.py) ·
[Context and sources](https://typer.tiangolo.com/reference/context/) ·
[just positional arguments](https://just.systems/man/en/positional-arguments.html) ·
[Current recipes](../../justfile) · [Probe][evidence]

<a id="I03"></a>
### I03 · Separate safe human diagnostics from typed output

**Observed rendering defect and proposed correction · CLI-01/03/06/08.** The CLI failure adapter
prints interpolated external fields on a default Rich console. A bounded Rich 15.0.0 fixture
showed that markup consumes bracketed text and both literal `Text` and `markup=False` still pass
raw terminal control sequences. Redact sensitive diagnostic fields at their owner. Sanitize
untrusted terminal text before using `Text` or `Console.print(markup=False, highlight=False)`.
Apply trusted semantic styles separately. Keep JSON on the existing typed serializer and preserve
distinct usage, refusal and tool-exit behavior. The Typer error renderer has its own escaping,
which does not cover the failure adapter. Exercise OSC/SGR, bracket markup, newlines, Unicode,
credentials and child output in a redirected installed subprocess.

For operator diagnostics, consider `Syntax(preselected_text, lexer, start_line=…, highlight_lines=…)`
only for authorized excerpts already present in the selected result. Consider
`Traceback.from_exception(show_locals=False)` for explicitly enabled safe diagnostics, with
messages and notes reviewed separately. Display grouping cannot imply that several causes share
one failure identity. Use Rich `Progress(console=stderr, auto_refresh=False,
redirect_stdout=False, redirect_stderr=False)` with `add_task()`, `update()` and bounded batch
`refresh()` over the supervisor's events. Keep unknown totals indeterminate. Use `get_time=`
for stable presentation tests where useful. Never infer process exit, scientific progress or
coverage from a renderer clock. (FP-02/05/06, DP-08/19/21/23.)
[Failure adapter](../../python/corpus-structure/src/corpus_structure/cli/failures.py) ·
[Rich Console](https://github.com/Textualize/rich/blob/v15.0.0/rich/console.py) ·
[Text](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py) ·
[Progress](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py) ·
[Syntax](https://github.com/Textualize/rich/blob/v15.0.0/rich/syntax.py) ·
[Traceback](https://github.com/Textualize/rich/blob/v15.0.0/rich/traceback.py)

<a id="I04"></a>
### I04 · Keep campaign identity with the recipe and receipt supervisor

**Execution improvement · CLI-02/03/08.** Have `ci` allocate one result and hand a private
workspace identity to the existing recipe and supervisor. Give each lane an exclusive child
location. Keep selection, process settlement, native receipt and verified coverage distinct.
`scripts/test_receipts.py` already owns child groups through `Popen(start_new_session=True)`,
signal settlement and `classify()`/`write_unresolved()`. Avoid creating a second classifier or
reconstructing worker state from terminal text. Forward cancellation through the recipe to the
receipt owner and wait for settlement. Reserve separate escalation evidence when that owner or
its children cannot be reached. Preserve the original failed attempt when an eligible rerun
covers its obligation.

Today nextest qualification captures a shared profile JUnit file with an mtime check. Concurrent
campaigns could attach the other campaign's report. Prefer serializing the shared nextest report
creation and capture at its existing owner until an invocation-specific report path is supported
with the existing profile/cache. Scope that lock to the shared target/report, leaving ordinary
pytest parallelism available. Preserve pytest-xdist 3.8.0 `-n auto --dist=loadgroup` and the
separate leased `-n 0` native fault lane. Validate parallel campaigns, an unavailable exclusive
lane, authentic child cancellation through `ci` and `just`, and bounded replacement coverage
against a declared set with independently known gaps. (FP-06/07, DP-19/20/23.)
[Receipt supervisor](../../scripts/test_receipts.py) ·
[Nextest JUnit configuration](https://nexte.st/docs/machine-readable/junit/) ·
[xdist 3.8.0 distribution](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst) ·
[Python subprocess](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen)

<a id="I05"></a>
### I05 · Use one explicit result settlement and custody boundary

**Alignment opportunity · CLI-02/03/05/06.** Express the transitions needed by the actual three
producers first: test receipts, change previews/candidates, and review export. Resolve a producer's
state, settlement and required holds under one stable result owner. Coordinate GC, readers acquiring
an export lease, and hold creation with the same lock identity. Publish finalized manifests with
`os.replace()` and reuse the current Linux no-replace directory publication for a new delivery.
A manifest becoming visible is separate from a result's dependency becoming eligible for deletion.
Pin a live classifier input or approved preview before work becomes dependent on it. Late holds
refuse if the required identity already expired. Keep source and release identity in their owners.
A display timestamp or stale PID alone cannot establish process settlement. Preserve the one-day
success and one-week failure/interruption policy for unheld results and existing durable evidence
custody.

Choose a compact manifest and direct ID resolution before an index, another database or a Rich
recording. Reassess discovery if real bounded lists must inspect a material unbounded population.
Test interruption before and after publication, consumer hold versus expiry under a controlled
clock, concurrent export, and recovery of an unsettled child. Keep removable scratch separate
from accepted evidence. (FP-01/04/07, DP-04/19/20.)
[Existing bundle publication](../../python/corpus-structure/src/corpus_structure/serve/companion_export.py) ·
[Atomic replacement](https://docs.python.org/3.14/library/os.html#os.replace) ·
[Advisory file locking](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock)

## Model change and source evidence

<a id="I06"></a>
### I06 · Make validated canonical preparation the first model delivery

**Observed write-before-validation defect · CLI-04/05/07.** The current generator writes Stage A
files before `record_root()` can refuse. Split pure preparation from apply at the model owner.
Use `schema.change.diff()`, `derived()`, `check()`, existing renderers and
`compare_semantic_releases()` for declaration and composed-release judgments. Route the current
generator and future preview through the same validation. Make the proposed patch and applicability
visible without writing tracked files or starting a native candidate for a provenance-only change.
Keep revision, semantic release, runtime and native predecessor identities separate. Protect
the selected preview and check its exact input digests and authorization before apply. Partial
file effects should be explicit and resumable. Keep target-bound deployment, admission and
activation explicit. The optional discovery tools below can enrich a preview, while its approved
effects come from domain owners and the existing native validation. (FP-01/04/05, DP-03/04/08/18.)

Use independent additive SQL-visible, provenance-only and explicit rename cases already represented
in declaration tests. In the invalid revision case, verify zero writes rather than just an error.
For native165 relation retirement, check frozen migration and predecessor, rooted Reader, CLI,
MCP and detached verification. The old two-argument function's absence is a native contract.
Python search can locate consumers and cannot establish that contract.
[Stage A entry](../../python/corpus-structure/src/corpus_structure/schema/__main__.py) ·
[Independent declaration controls](../../python/corpus-structure/tests/schema/test_change.py) ·
[WCE native165](../plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

<a id="I07"></a>
### I07 · Attach bounded source discovery to the existing impact report

**Alignment opportunity and conditional adoption · CLI-04/05/07.** Reuse the semantic impact
report's declared consumers and unknowns. Include located source candidates as separate
evidence with snapshot and digest, analyzer/rule and grammar where applicable, source coordinate
unit and coverage. Distinguish inspected no-hit from skipped, unresolved, failed or truncated.
Use located evidence for review and caller migration. An empty search cannot authorize a removal
or prove that a dynamic consumer is absent.

- For Python 3.14.10, use `ast.parse(type_comments=True)`, `NodeVisitor` and `get_source_segment()`
  for bounded declaration or call-site discovery. Add `symtable.symtable()` only for a claim
  requiring lexical binding. Treat symbol-table association as ambiguous when scope and node
  evidence do not support a unique join. Distinguish class scopes, comprehension bindings, type
  parameters and decorator coverage. Use `compile(..., "exec", dont_inherit=True)` as a
  separate compile-only check on changed text. Optional `ast.compare()` can aid structural
  comparison. AST rewriting cannot preserve the required trivia. Test decorated and shadowed
  examples and a parse-valid/compile-invalid input.
  [AST 3.14](https://docs.python.org/3.14/library/ast.html#ast.get_source_segment) ·
  [Symbol table 3.14](https://docs.python.org/3.14/library/symtable.html) ·
  [Compile](https://docs.python.org/3.14/library/functions.html#compile)
- For repository discovery, keep installed ast-grep 0.51.0 `scan --json=stream` with an explicit
  scope and rule, contextual `pattern` selectors and ordered relational `all` where it prevents
  custom traversal. Treat `--inspect entity` as diagnostics with mode-specific coverage. A
  bounded search identified the rooted CLI call, while the MCP and detached authorities use
  different shapes. A zero-exit empty stream established no semantic absence. Coordinate units
  differ between CLI byte offsets and Python-facing character coordinates. Test Unicode, CRLF,
  excluded files and stale source before proposing any edit. Keep ast-grep-py `SgRoot`/
  `SgNode.find_all()` conditional on several related queries over the same pinned snapshot
  where repeated CLI traversal materially matters. Evaluate 0.51.1 against exact grammar and
  custom-metavariable behavior only if that use arises.
  [Scan interface](https://ast-grep.github.io/reference/cli/scan.html) ·
  [Effective pattern nodes](https://ast-grep.github.io/advanced/pattern-parse.html) ·
  [Composite rules](https://ast-grep.github.io/guide/rule-config/composite-rule.html) ·
  [Python API](https://ast-grep.github.io/guide/api-usage/py-api.html) ·
  [0.51.1 release](https://github.com/ast-grep/ast-grep/releases/tag/0.51.1)
- Revisit Tree-sitter for a concrete paired-field or recovery workload that the existing route
  cannot express economically. Use `QueryCursor.matches()` to retain capture associations,
  and record grammar identity, parse recovery, termination and `did_exceed_match_limit`.
  Query assertions are metadata, while match limit bounds active matches rather than total
  output. The local binding 0.26.0 with tree-sitter-python 0.25.0 passed ordinary matching and
  segfaulted before entering the supplied `progress_callback` on the same input. If adopted,
  use an isolated worker with external deadline and bounded input/output or qualify a fixed
  exact binding before using that callback. Compare ordinary CLI discovery first. Keep
  incremental parsing and indexes conditional on a repeated workload; changed syntax ranges
  alone are insufficient to establish source identity. (FP-02/07, DP-15/20/21, CI-01/02/04/06/08/10.)
  [QueryCursor API](https://tree-sitter.github.io/py-tree-sitter/classes/tree_sitter.QueryCursor.html) ·
  [Tagged binding](https://github.com/tree-sitter/py-tree-sitter/blob/v0.26.0/tree_sitter/binding/query_cursor.c#L128-L145) ·
  [Probe][evidence]

<a id="I08"></a>
### I08 · Compare shipped LibCST rename with the explicit patch path

**Conditional enhancement · CLI-04/05/07.** Qualify LibCST 1.9.0 only for a demonstrated recurring
Python rename with an explicit qualified old-to-new mapping. Try the shipped
`RenameCommand(CodemodContext, old_name, new_name)` with `parse_module(bytes)` and
`MetadataWrapper` before writing a custom transformer. Use the name metadata and import helpers
for supported import shapes. The tagged implementation checks membership in a potentially
multi-valued qualified-name set and skips some relative/star import shapes. Gate edits to
allowlisted, uniquely supported occurrences and compare the staged patch with an independent
expectation. Leave ambiguous or dynamic cases explicit, preserving the manual patch route.
Exercise re-exports, shadowing, relative imports, Unicode and comments/CRLF, and confirm source
bytes match before apply. LibCST byte spans use UTF-8 units and require explicit conversion for
other original encodings. Distinguish a qualified Python rename from an authored domain name
map, migration, or release decision. Bulk codemods and dependency pinning remain conditional.
(FP-02/04/06, DP-13/15/18/23, CI-02/04/12.)
[Tagged rename](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/commands/rename.py#L204-L300) ·
[Name metadata](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/name_provider.py#L25-L71) ·
[Byte spans](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/metadata/span_provider.py#L87-L111)

## Corpus authority and transport

<a id="I09"></a>
### I09 · Share semantic refusals and retain transport-specific authority and bounds

**Observed projection drift and alignment opportunity · CLI-06/07/08.** `NativeSourceRequest`
and `inspect_native_source()` already supply a shared operation. CLI and MCP build similar refusal
content separately. Produce the safe refusal fields once at the semantic owner and project them
to CLI JSON/exit and MCP `ToolError`/protocol error behavior. Compare admitted payloads and refusal
meaning while preserving transport envelopes. FastMCP 4.1.3 `ToolResult` keeps structured
and text content. MCP currently budgets text, structured content and stamped metadata in
`_bounded_mcp_result()`. CLI emits one JSON body, so an equivalent request can fit the CLI and
exceed the MCP wire budget. Preserve that distinction in actual UTF-8 boundary tests.

Native MCP source inspection runs in a read-only snapshot over a write-purpose queue pool.
Resolve the read purpose explicitly for pure inspection and preserve queue authority for work
actions. Keep role and exposure authorization with existing read/export owners. Tool annotations,
visibility and namespaces cannot replace them. Use `Context.report_progress()` only to project
existing request events when a progress token exists. Retain snapshot, evaluator exposure,
detached verification and publication at the bundle owner. An exact-ID resource URI is a
conditional route for a real remote consumer of an already published artifact. Preserve missing
or inaccessible closure and the absence of provider startup. Verify the typed fields and wire
bounds on registered and fresh stdio MCP, including wrong run and least-authority controls,
alongside installed CLI and detached export. (FP-01/04/05, DP-01/08/20/21/23.)
[CLI source adapter](../../python/corpus-structure/src/corpus_structure/cli/source.py) ·
[MCP server](../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py) ·
[Shared refusal owner](../../python/corpus-structure/src/corpus_structure/semantic/refusals.py) ·
[Review bundle owner](../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py) ·
[FastMCP 4.1.3 ToolResult](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/fastmcp_slim/fastmcp/tools/base.py) ·
[FastMCP 4.1.3 context](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/fastmcp_slim/fastmcp/server/context.py)

<a id="I10"></a>
### I10 · Make CLI diagnostics actionable within the result lifecycle

**Selected scope proposal · CLI-01/02/03/06/07/08.** Use the cancelled plan's dated logging
probes as prior evidence. Bring useful diagnostics directly into the CLI series. Their value
comes from the decision they support. Prefer the producer's existing status, receipt or typed
refusal. Add a diagnostic event or capture only if the operator would otherwise lose the
information needed to choose a concrete next action.

| Operator decision | Smallest source and CLI surface |
|---|---|
| Which check failed, and can I retry it? | `ci results show` surfaces the existing lane, stage, code, retryability and receipt identity. `ci results watch` reads complete new records by bounded cursor from the live owner. Reuse xdist events and settled receipts. Store a bounded child excerpt only when it explains a failure the receipt cannot explain. |
| Did a change stop before a write or after a committed effect? | Show the effect stage, settled effects, and the exact candidate, deployment target or predecessor needed to resume. Carry the result owner’s outcome or refusal. Diagnostic availability cannot alter settlement or authorization. |
| Is the configured service unavailable, or did the request select the wrong target or role? | `ci doctor` and named health/status commands surface the existing owner probe and a direct remedy. Consider a bounded existing service-log read only when it can distinguish failures that status misses, the source and permitted role are explicit, and there is a concrete operational caller. Keep host commands on their owned recipes. |

Carry invocation/result identity, meaningful stage or code, source and optional attempt identity
where it joins existing evidence. Default to actionable errors, warnings and a few phase
transitions needed for operator control. Omit per-item success chatter, routine SQL or provider
payloads and duplicate receipt events. Apply bounds before formatting and persistence. Only
persist an invocation-local sidecar when live state or foreign diagnostics would otherwise be
lost and a named CLI consumer uses it. Bound bytes, event count and excerpts, with a visible
truncated or unavailable state. Stop reading at incomplete records and distinguish a live
partial tail from a corrupt settled stream. Keep existing result TTL and holds. Use incremental
offsets for watch, since `read_stream()` builds the whole input for settled classification.
Avoid a separate logging archive, query index, incident store or retained transcript for this
scope. Diagnostic failure remains visible without replacing the primary result.

**Structlog comparison.** Start with typed owner events and an invocation-scoped stdlib
handler for the needed foreign messages. Existing method and DB producers already expose stdlib
loggers. When one real journey requires shared structured fields from application and foreign
logging and the small stdlib route becomes duplicative, qualify **structlog 26.1.0** for that
slice. Use `structlog.contextvars.bound_contextvars()` and `merge_contextvars()` in the producing
context, `stdlib.LoggerFactory`, `ProcessorFormatter.wrap_for_formatter`, and
`foreign_pre_chain` with `remove_processors_meta` at the stdlib projection boundary. Redact
and freeze safe fields before any buffer, queue or delivery. Carry only explicitly approved
IDs across processes or threads. A listener's context cannot recover producer context, and
stdlib `QueueHandler.prepare()` can flatten record fields. Begin synchronous and local. Keep
the accepted processor pipeline only if it replaces custom work or supports an actionable
diagnostic that the simpler route cannot preserve. Assert final stderr and optional JSONL in a
fresh process. `structlog.testing.capture_logs()` alone does not establish configured processor
behavior.
[Local structlog reference](../libraries/logging/structlog.md) ·
[Method logger](../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py) ·
[Database logger](../../python/corpus-structure/src/corpus_structure/core/db/store.py) ·
[Receipt reader](../../scripts/test_receipts.py) ·
[Structlog context](https://www.structlog.org/en/26.1.0/contextvars.html) ·
[Stdlib integration](https://www.structlog.org/en/26.1.0/standard-library.html) ·
[Structlog testing](https://www.structlog.org/en/26.1.0/testing.html) ·
[QueueHandler](https://docs.python.org/3.14/library/logging.handlers.html#logging.handlers.QueueHandler.prepare)

**Other logging capabilities.** The [unified overview][logging] and linked specialist references
support these dispositions. Python JSON Logger 4.2.0 `JsonFormatter` and ECS 2.3.0
`StdlibFormatter`/`StructlogFormatter` address serialization or external schema delivery.
Revisit if a concrete collector requires that projection. Loguru 0.7.3 adds a second router and
its queued path needs a resource and drain contract. Logbook 1.10.1 failure-context buffering
would need an evidenced gap beyond bounded receipt excerpts and its own global byte admission.
Eliot 1.18.0 introduces action correlation and does not establish native task/result completeness.
OTel and Logfire offer cross-service tracing, telemetry and query. Revisit when a specific
operator decision demonstrably spans independent services and existing action IDs and status
cannot resolve it. OTLP export, metrics, incidents and support bundles need their own consumer
and cost case. Picologging has no measured logging bottleneck or qualified Python 3.14 route in
this review. These mechanisms do not enter the CLI dependency path by default.
[Historical event comparison](../design_review/evidence/2026-11-01_logging-events-history/README.md) ·
[Historical exporter investigation](../design_review/evidence/2026-11-01_logging-telemetry-runtime/README.md)

**Closure.** Show that a real failed test or interrupted effect yields the next correct action
from the selected ID without searching an arbitrary output folder. Test an oversized/noisy source,
redaction, no JSON stdout pollution, disabled or failed diagnostics, cancellation and expiry.
Use a fixture with an independently known fault or interruption. Compare captured data and
processing with the direct receipt-only route. Quantify overhead only if a proposed higher-volume
path depends on a performance claim. (FP-01/04/06/07, DP-14/19–23.)

## Combined adoption and limits

I01 and I02 reduce migration risk before CLI-01 grows. Land I03 with the shared adapter before
fanning out rendering. Shape I04 and I05 together around actual test receipts, then reuse the
custody contract for previews and exports. I06 is a prerequisite for authoring effects. It can
progress before CLI-02 or optional introspection. I07 helps review and caller migration while
I08 requires a demonstrated edit case. The refusal and authority portions of I09 can be assessed
independently of bundle UI and integrated with CLI-06. Fold the bounded diagnosis in I10 into
I03–I05 as the first result producer migrates. CLI-08 owns final assembled acceptance.
I03 and I06 address directly inspected defects. The nextest race and transport authority findings
are source-derived risks with proposed closure controls. No timing or disk savings are claimed.

Preserve accepted CLI-RC01–03. Existing O01–O07 and adjacent
test and WCE finding dispositions remain at their owners. Any decision to adopt
these recommendations belongs to plan revision. LibCST execution, native deployment, provider
calls, concurrency/GC and end-to-end transport qualification were `not_run` in this review.

[plan]: ../plans/cli-operations_2026-11-07.md
[command]: ../plans/cli-operations/command-context-output.md
[results]: ../plans/cli-operations/managed-results-and-testing.md
[model]: ../plans/cli-operations/model-change-and-deployment.md
[corpus]: ../plans/cli-operations/corpus-and-operations.md
[evidence]: ../design_review/evidence/2026-11-07_cli-typer-028/README.md
[typer]: ../libraries/python_introspection/typer.md
[rich]: ../libraries/python_introspection/rich.md
[ast]: ../libraries/python_introspection/ast.md
[sg]: ../libraries/python_introspection/ast-grep.md
[sgpy]: ../libraries/python_introspection/ast-grep-py.md
[ts]: ../libraries/python_introspection/tree-sitter.md
[cst]: ../libraries/python_introspection/libcst.md
[mcp]: ../libraries/python_introspection/fastmcp.md
[logging]: ../libraries/logging/Python_Structured_Logging_and_Observability.md
