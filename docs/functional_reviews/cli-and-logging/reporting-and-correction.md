# Correction, unexpected failures and replayable presentation

**Recommendations Proposed, 2026-11-10.** [Review and baseline](../cli-and-logging_2026-11-10.md).

<a id="O04"></a>
## O04 — From an attributed observation to a correction or investigation

Recommend a correction-focused view shared by immediate failures and retained diagnostic reads.
Present the outcome, violated constraint, instance/declaration locations, bound release/product,
coverage/omission status and exact next inspection route. Codex can then follow understand → edit
→ recheck without reconstructing a relationship from a large object dump. This does not require
a past failed agent session to have value: repeated input/model authoring is a credible consumer.

The dirty DMC implementation already supplies `LocatedValidationReport`, original-engine detail
and optional digest-verified managed retrieval. Current non-JSON failure rendering mostly emits
compact prose. Extend the view over those owned products; do not add a second diagnostic model,
validation pass or evidence store. Distinguish instance paths, logical declaration addresses and
physical source lines. A contributor set does not identify a unique winning declaration.

Use Rich `Group`, literal `Text`, `Table.grid` and selected `Tree` branches; use `Syntax` for an
already-selected excerpt with its true starting line. Obtain text from authenticated retained
inputs, or verify the checkout digest before identifying it as the diagnosed source. When only a
logical declaration path is known, display that useful location rather than fabricate lines.
`Text.append_tokens` can reuse owner-supplied classification; a renderer should not reinterpret
domain severity or provenance. Themes express shared vocabulary where several views actually use it.

**Alternatives.** Existing JSON/Pretty remains suitable for exploratory object reads. Prefer a
purposeful view for relationships and action guidance over elaborate tables everywhere. A custom
`__rich_console__`/`__rich_measure__` object is conditional on repeated layout that native composition
cannot express. Global render hooks and a generic report-rendering registry have no sufficient
benefit here. Readable text and full typed data remain complementary outputs.

Unexpected defects need a different diagnostic branch: preserve exception type, causal chain,
notes, grouped children and bounded frames linked to invocation/stage. Keep programming exceptions
as defects, expected validation as typed refusal and cancellation as interruption. Capturing a
defect must not make it an ordinary refusal or successful report operation. Use existing text plus
explicit Rich `Traceback.from_exception` if that suffices; for O05's structured target reuse
`ExceptionRenderer(ExceptionDictTransformer(show_locals=False, ...))`. Frame limits alone do not
bound group nesting or encoded bytes. Sanitize messages/source/nested data before every retained
or emitted safe representation; opting out of locals does not sanitize exception text.

**Delivery criteria.** Repair a nested invalid input from the safe view; retrieve omitted evidence
under the original release; distinguish unavailable lines, changed source and incomplete examination.
A grouped unexpected failure retains causes/notes without locals, and publication failure preserves
the original outcome. CLI/MCP expose the same diagnostic meaning. Independent expected paths and
causes test the producer, while render tests check selection fidelity and exact identifiers.

Sources: [current failure boundary](../../../python/corpus-structure/src/corpus_structure/cli/failures.py),
[diagnostic custody](../../../python/corpus-structure/src/corpus_structure/cli/diagnostic_artifacts.py),
[active DMC target](../../plans/domain-data-model/diagnostics-and-graph-workflows.md),
[Syntax15](https://github.com/Textualize/rich/blob/v15.0.0/rich/syntax.py),
[Text15](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py),
[exception transformer26.1](https://www.structlog.org/en/26.1.0/api.html#structlog.tracebacks.ExceptionDictTransformer),
[traceback filtering](https://www.structlog.org/en/26.1.0/recipes.html#custom-filtering-of-dict-tracebacks).

<a id="O07"></a>
## O07 — Re-present a retained result without repeating its producer

Recommend separating report selection and presentation so an authenticated retained result can
be read as compact text, a correction hierarchy, selected event rows or JSON without rerunning
validation, a provider or a model compiler. This enables focused later investigation and comparison
of two attempts. Each view names original pins, observation availability and omitted detail;
changing presentation does not turn partial evidence into a complete result.

Use ordinary pure presentation functions over the existing typed selection. Rich capture/StringIO
can produce requested text; `Console(record=True)` can support a saved HTML/SVG presentation for a
reviewer or research note. Recommend text/JSON replay first. HTML/SVG are conditional because Codex
usually consumes text and a styled export adds little unless someone will inspect/share it. This
is a credible future consumer, not an automatic rejection due to missing current usage.

**Alternatives.** Retain raw text alone when later selection is unnecessary; it cannot recover
fields filtered before rendering. Retain typed result/events and re-render when selection or layout
changes are useful. Retaining every output format at execution time duplicates data and is not
recommended. Recording stores rendered segments, not domain data. Multi-format exports must account
for buffer-clearing defaults and retained memory, supply controlled width and declare unavailable
content. Use existing managed artifact custody for an explicitly retained presentation; do not add
a publishing service or treat an SVG as original-engine evidence.

Rich ANSI decoding may preserve selected dependency text formatting, but is neither a sanitizer
nor a parser for semantic events. Custom Markdown elements, interactive Text metadata, notebooks,+pagers and alternate screens are not needed for this target; revisit for an actual different
consumer. Rich's built-in Markdown can display a supplied description without such extensions.

**Delivery criteria.** Two different views of one retained diagnostic agree on binding/outcome and
omissions; expired/corrupt evidence returns unavailable rather than a fresh producer run. A saved
presentation discloses its selected scope and remains separate from replayable semantic data.
No quantitative rendering-speed benefit is claimed or needs demonstration.

Sources: [Rich Console15](https://github.com/Textualize/rich/blob/v15.0.0/rich/console.py),
[export/capture overview](../../libraries/python_introspection/rich.md#9-interactive-input-capture-and-output-export),
[export controls](../../libraries/python_introspection/rich.md#102-additional-html-and-svg-export-controls),
[managed reads](../../../python/corpus-structure/src/corpus_structure/cli/managed.py).

## Destination contract shared with O05/O06

Retain the current report/delivery adapters: stdout is the final typed result or explicitly selected
text; stderr carries best-effort diagnostics. Current broken-pipe hooks preserve known failure or
otherwise exit74 for incomplete delivery. MCP stdout is protocol-only. Scope presentation after
parsing and honor runner stream swaps. Do not replace these obligations with generic Console defaults.
Conditional Live/Progress uses explicit stderr and both redirect flags false. Qualify JSON with
terminal stderr, output closure and cancellation if that branch is selected; source inspection alone
does not establish terminal restoration or OS signal behavior.
