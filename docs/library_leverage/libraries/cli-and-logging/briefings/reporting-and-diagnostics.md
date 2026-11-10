# Reports, streams and exception presentation

**Discovery, 2026-11-10; benefits Proposed.** [Baseline and authority](../briefing.md).

## Current foundation and journeys

[output.py](../../../../../python/corpus-structure/src/corpus_structure/cli/output.py) emits
Pydantic JSON or a Rich projection, creates consoles per call, redacts diagnostic text and
handles broken pipes. A successful incomplete delivery exits74; known failure status remains
available to the emitter. Diagnostic failure is best effort. Those branches encode application
delivery obligations that generic Rich output alone does not replace.

[testing.py](../../../../../python/corpus-structure/src/corpus_structure/cli/testing.py) already
provides bounded failures, unresolved views, exact retry and coverage comparisons.
[model.py](../../../../../python/corpus-structure/src/corpus_structure/cli/model.py) has bounded
patch/SQL/effect/candidate views and explicit next actions. The current
[failure boundary](../../../../../python/corpus-structure/src/corpus_structure/cli/failures.py)
distinguishes expected refusals and database failures while allowing programming errors and
cancellation to retain their identity. Concurrent DMC changes add attributed diagnostic detail;
their active [companion](../../../../plans/domain-data-model/diagnostics-and-graph-workflows.md)
owns meaning, not the renderer.

<a id="cli-04"></a>
## CLI-04 — Rich as a projection of selected meaning

**Mechanisms.** `Text` for literal identifiers, `Table.grid` and `Group` for concise labeled
facts, bounded `Tree` for relationships, `Syntax` for located source/diff excerpts, `Pretty`
limits for exploratory object detail and `Theme` for shared status vocabulary.

**Potential value.** Extend current views to make a located failure, selected effect or qualified
relationship understandable in one read. Source excerpts could connect a diagnostic's exact
location to the text Codex must edit. A hierarchy can expose nested attribution without forcing
the agent to reconstruct it from unrelated prose. Native layout may remove repeated presentation
work across actual compatible reports.

**Counterconditions.** Generic `Pretty` is already sufficient for some reports. A renderer cannot
repair missing selections or omitted facts in an owner product. Wrapping/truncation can hide exact
identifiers; narrowing presentation must not silently narrow semantic coverage. Rich JSON formatting
is a human display facility and does not replace `model_dump_json` or its schema. Custom protocols,
highlighters and render hooks have no demonstrated need until built-ins leave a repeated gap.

**Next question.** Which current report makes Codex perform another lookup or reconstruct a
relationship? Determine whether that is a missing owner-selected view or simply a rendering gap.
For either case preserve selection, identity, completeness and retrievable omitted detail.

Sources: [tables](https://rich.readthedocs.io/en/stable/tables.html),
[Text15](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py),
[Syntax15](https://github.com/Textualize/rich/blob/v15.0.0/rich/syntax.py),
[Pretty15](https://github.com/Textualize/rich/blob/v15.0.0/rich/pretty.py).
These are capability routes; no new report has been rendered or qualified in this discovery.

<a id="cli-05"></a>
## CLI-05 — Output ownership across capture and terminals

**Mechanisms.** Explicit stderr Console, markup/highlighting policy, terminal/interactivity
detection, capture, `Live` redirection controls and Typer's separate Rich switches.

**Source observation.** Rich15 `Live._enable_redirect_io` swaps process stdout/stderr when its
console is terminal/Jupyter and the respective redirect flag is enabled. An stderr terminal
console can therefore redirect stdout even while stdout is a machine-data pipe. This is a
concrete composition hazard, not evidence of a current defect: no Live/Progress integration was
found in the searched CLI package. Existing per-call consoles intentionally honor runner stream
swaps and width; an invocation-wide console must preserve those properties if introduced.

**Potential value.** A deliberate presentation lifetime could coordinate diagnostic lines and
optional status updates without contaminating results or MCP stdio. Headless output could preserve
meaningful transitions while avoiding cursor redraw noise. Native Console/Live management can
discharge display restoration once a real consumer needs it.

**Counterconditions.** Current plain stage lines may serve Codex better. `NO_COLOR` is not a
complete terminal-control policy; formatting disablement is not input sanitization. `Text.from_ansi`
decodes formatting, not arbitrary safe terminal content. Typer help/error output and application
consoles are distinct; recording one does not capture all others. Changing global Rich configuration
or installing hooks introduces additional owners and test coupling.

**Next question.** Does a named operation need final JSON, live terminal status and third-party
diagnostics concurrently? If so, qualify piped stdout with terminal stderr as well as fully captured
execution, output closure and cancellation. Otherwise retain current plain diagnostics.

Sources: [Live15](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py),
[Console15](https://github.com/Textualize/rich/blob/v15.0.0/rich/console.py),
[Typer core0.28](https://github.com/fastapi/typer/blob/0.28.0/typer/core.py).

<a id="cli-06"></a>
## CLI-06 — Actionable exception structure with one renderer per destination

**Mechanisms.** Current typed failures plus Rich `Traceback.from_exception`, Typer
`pretty_exceptions_*`, exception notes/groups, and structlog `ExceptionRenderer` with
`ExceptionDictTransformer` or `dict_tracebacks`. A structured traceback can expose frames and
causes to an agent without requiring prose extraction; a bounded terminal projection can support
an explicit debugging read.

**Source observations.** Rich15 `RichHandler.emit` first formats the record, then, if
`rich_tracebacks` and surviving `exc_info` apply, rebuilds the message through `getMessage` and
`formatter.formatMessage`. Consequently a ProcessorFormatter-rendered event cannot be assumed to
survive that branch. **Refined by the functional review, 2026-11-10:** ProcessorFormatter copies
the record before clearing exception state, so foreign exceptions can trigger RichHandler's
branch even with default `keep_exc_info=False`; the earlier warning limited to `True` was too
narrow. See the [composed target](../../../../functional_reviews/cli-and-logging/execution-and-diagnostic-events.md#corrected-composition-warning).
Investigate either structlog-owned
rows/tracebacks or RichHandler-owned presentation with a compatible adapter. Do not stack complete
renderers on the assumption that they compose. Structlog26.1's exception dictionary transformer
defaults locals on; any candidate must choose disclosure and bounds deliberately.

**Potential value.** Preserve unexpected exception causes, notes and grouped failures alongside
the exact attempt/stage identity, while typed refusals continue to express domain failures.

**Counterconditions.** Existing typed reports and retained stderr may already answer the question.
Raw frame/source/local data can duplicate artifacts, expose sensitive material or overwhelm the
consumer. Current string-level `safe_text` does not establish recursive redaction of exception
dictionaries. Typer's control-flow exceptions are not all subclasses of one universal base;
central catching must preserve usage, cancellation and programming-error distinctions.

**Next question.** Which real failure forces Codex to recover information from a flattened
traceback, and which fields would change its action? Only then select exception depth and one
renderer per destination, with nested-data redaction and delivery policy explicitly retained.

Sources: [Rich logging15](https://github.com/Textualize/rich/blob/v15.0.0/rich/logging.py),
[Rich traceback15](https://github.com/Textualize/rich/blob/v15.0.0/rich/traceback.py),
[structlog exceptions26.1](https://www.structlog.org/en/26.1.0/exceptions.html),
[transformer API](https://www.structlog.org/en/26.1.0/api.html#structlog.tracebacks.ExceptionDictTransformer).

## Follow-up scenarios

If selected for assessment, use independent expected fields and exact bytes for normal JSON,
malformed input, typed refusal, unexpected/grouped error, narrow Unicode, literal markup/control
text, redaction, stdout/stderr closure and known cancellation. Use CliRunner for grammar and a
fresh process/PTY only for actual stream/hook/terminal uncertainty. No such runtime checks were
needed to establish these discovery leads; outcomes remain source-level and Proposed for local fit.
