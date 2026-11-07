# Reporting contracts and test evidence

**Status:** Implemented on main. [Coordinator](../cli-reporting_2026-11-07.md) owns scope and integrated
acceptance. This plan consumes [O01](../../functional_reviews/cli-reporting_2026-11-07.md#O01)
and [O02](../../functional_reviews/cli-reporting_2026-11-07.md#O02).

<a id="CLIR-01"></a>
## CLIR-01 · One typed selection with a bounded presentation

Build the first shared slice in the existing `emit` boundary. Default human views show
identity, outcome, counts or stage, and an actionable next read or effect command where the
owner can justify one. Named views choose a typed product before rendering. A selected
detail view reports its ordering, selected and available counts, any omission and the
continuation where supported. Keep default bounds small enough to read in one transcript.
Specify per-view limits and supported filters at the owner, validating combinations after
parsing. Use fixed labels and wrapped identifiers for narrow terminals. Preserve the full
`--json` shape with no view argument. A named view with `--json` has its own typed shape.

| Library mechanism | Role and constraint |
|---|---|
| Rich 15.0.0 `Console.print`, `Table.grid`, `Text` | Render bounded owner-selected rows. Use literal `Text` after the shared redaction and terminal-control policy, and wrap where needed for a complete identifier. `Table.grid` supplies compact alignment. Labels express all outcome distinctions without relying on color. Use `Group` for actual sections and `Tree` for a bounded hierarchy. Use `Columns`, `Panel.fit`, `Rule`, `Align` or `Constrain` only where they clarify reading order. Introduce a semantic `Theme` once several reports share status vocabulary. [Layout overview](../../libraries/python_introspection/rich.md#4-structured-renderables-and-responsive-terminal-layout) · [Table source](https://github.com/Textualize/rich/blob/v15.0.0/rich/table.py) · [Text source](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py) |
| Typer 0.28.0 `Annotated` with `Option`, `Literal` or enum, repeatable options | Declare available views, bounds and documented defaults at the command. Use final validation for cross-argument relationships. Use `get_parameter_source`, `show_default` or `show_choices` if their provenance matters. Consider environment, `default_map`, tri-state and eager options only for a real settings decision that the existing settings owner can express. [Typed parameters](../../libraries/python_introspection/typer.md#3-typed-parameters-conversion-and-validation) · [Pinned behavior](../../libraries/python_introspection/typer.md#90-typer-0280-behavior-update) |
| Pydantic 2.14.1 `BaseModel.model_dump_json()` | Retain the emitter's typed serializer for one complete machine payload. Rich `JSON.from_data` can format explicitly requested human detail, subject to its serializer choices. It has a separate role from the command schema. [Serialization overview](../../libraries/data_model/pydantic.md#6-serialization-as-a-separate-programmable-contract) · [BaseModel API](https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_dump_json) |

Use stock renderables first. Consider `Layout`, `ConsoleOptions`, `Measurement`,
`render_lines`, segment cropping, hooks or custom renderables only for a responsive
requirement stock composition fails to express. Owner bounds precede presentation bounds.
Use `Pretty`, `__rich_repr__`, specialized highlighters or selected Markdown for a bounded
developer view with a concrete reading need. A generic field or path language requires
multiple real consumers for arbitrary selection, with authorization and shape-stability
rules. [Rich rendering addenda](../../libraries/python_introspection/rich.md)

Verify at least one early test view and one model view with equivalent facts in human and
named JSON output. Exercise a width that wraps long Unicode identifiers, literal markup,
terminal controls and credential-shaped diagnostics. Use bounded `Console.capture()` or
`StringIO` for in-process rendering assertions and real process streams for delivery.
Preserve representative full JSON fixtures and test that a valid empty view differs from
unavailable evidence. [Console capture](../../libraries/python_introspection/rich.md#92-capturing-output-without-a-terminal)

<a id="CLIR-02"></a>
## CLIR-02 · Find exact failures and reconcile coverage

Default `ci test coverage ORIGINAL [RETRY …]` to a compact human coverage report.
Use named `--view unresolved` and `--limit` for bounded detail. Plan a test-owned
`ci test failures RESULT_ID` because lane and phase selectors and receipt joins are
test-specific. Reuse the canonical node, phase and lane identities and native observations.
A result that is still running reports partial availability and points to the existing
watch cursor. Report exact retry or recovery only when the receipt or custody supports it.

Have the classifier produce the compact view before returning from its subprocess. Preserve
its full classification for existing full JSON and exact retry callers. Verify all other
`--summary` consumers before selecting the new dispatch. A small final projection may still
need to inspect the required receipt set. Reuse that classification and avoid repeated
transfer of full lists. Report original attempts, reconciled node counts, unresolved or
missing lanes, unsettled custody and source/context differences as independent facts. The
qualification owner judges source applicability. Preserve failed and interrupted attempts
after retry. [Coverage adapter](../../../python/corpus-structure/src/corpus_structure/cli/testing.py#L233) ·
[Classifier](../../../scripts/test_receipts.py#L988)

Verify a failure omitted by the truncated tail, a missing lane, changed source and a
reconciled retry, plus active and unavailable receipt cases. Use the retained 179-node
and 5,119-node examples within their recorded scope, or equivalent owner fixtures. Verify
the compact classifier response omits the full required-node lists and full JSON and exact
retry still use their established semantics. The prior probe measured payload shape and
bytes. A claim about runtime or capacity requires separate measurements.
[Review observations](../../functional_reviews/cli-reporting_2026-11-07.md#current-workflows-and-evidence)
