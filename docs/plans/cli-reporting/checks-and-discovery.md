# Repository checks and command discovery

**Status:** Proposed. [Coordinator](../cli-reporting_2026-11-07.md) owns scope and integrated
acceptance. This plan consumes [O05](../../functional_reviews/cli-reporting_2026-11-07.md#O05).

<a id="CLIR-05"></a>
## CLIR-05 · Report the failed step and make the next route discoverable

Extend the existing `just` bundle boundary to return a typed summary of ordered step
identities and outcomes for `ci check`. Preserve the direct recipe's human transcript,
continue-on-failure behavior and aggregate exit. Capture the actual per-step exit at the
recipe, including a step that never started when cancellation interrupted the sequence.
Keep step refusal, failure, cancellation and overall custody separate where evidence
supports the distinction. Use an existing tool's structured output where available.
For foreign text, attach only an actionable, sanitized excerpt with source, stream and
truncation. Prefer a small owned step result over parsing a combined human transcript.
Use that result for a compact human view and for named structured detail. Keep the
existing full JSON route and stable `--only` selectors.
[Recipe bundle](../../../justfile#L74) · [Recipe adapter](../../../python/corpus-structure/src/corpus_structure/cli/operations.py)

Start with a settled summary. The current `subprocess.Popen.communicate(timeout=...)`
route drains both pipes and keeps the full strings before the adapter limits output.
If measured workload or an actionable pre-failure need warrants a change, compare a
bounded dual-stream read against that route. Set caps for bytes in memory and bytes
retained, keep draining both streams under backpressure, and preserve process group
ownership, signal forwarding, settlement and exit attribution. Test credentials split
across chunks if streaming sanitization is selected. Keep subprocess and resource
changes with the existing recipe supervisor. Rich 15.0.0 `Text` is suitable for
literal excerpts after sanitization. Use `Syntax` only for selected known source
diagnostics. [Process owner](../../../python/corpus-structure/src/corpus_structure/cli/recipes.py) ·
[Python subprocess API](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen.communicate) ·
[Rich text source](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py)

Use public Typer 0.28.0 `rich_help_panel`, `rich_markup_mode`, descriptions and
explicit metavars to group the new views, explain inputs and point to safe next actions.
Keep option spelling independent of the metavar and use explicit option names where
compatibility requires them. Use contextual command help for targeted discovery.
Offer an explicit direct Markdown route, proposed as `ci docs commands --stdout`,
when reading the whole current command reference. Reuse the existing registry and
`just ci-reference` generator. Keep managed publication and its full JSON route
available. Reject a combination of direct Markdown and `--json` before doing work.
Gate the direct stream on CLIR-06. [Typer help](../../libraries/python_introspection/typer.md#54-rich-help-and-structured-cli-documentation) ·
[Pinned generator](https://github.com/fastapi/typer/blob/0.28.0/typer/cli.py#L278-L312) ·
[Typer 0.28.0 option construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py#L1361-L1365)

Help and completion stay lazy. Add dynamic completion only when suggestions are
cheap, bounded and safe with partial parsed context. Verify the selected completion in
a fresh supported shell and the new help routes with unusable application settings.
Keep the explicit raw `--` validation for test delegation. Consider `TyperCommand` or
`TyperGroup` extensions only for an essential missing public hook. Test new commands
through `CliRunner.invoke` for grammar, and through the installed process for actual
stdout and stderr. [Typer completion](../../libraries/python_introspection/typer.md#5-shell-completion-and-cli-discoverability) ·
[0.28.0 compatibility observations](../../libraries/python_introspection/typer.md#90-typer-0280-behavior-update)

Verify a multi-step recipe with success, failure and later execution, plus an
interrupted child and a foreign diagnostic with an actionable redacted excerpt.
Check direct recipe usability, selected checkout identity, result availability and
both reference delivery modes. Verify that help and discovery never acquire an
application target merely to describe command syntax.
