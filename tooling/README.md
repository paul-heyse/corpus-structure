# corpus-tooling

Read-only repository tooling, separate from the product ([ADR-0132](../docs/adr/0132-tooling-package.md)).
The installed command is `tooling`; library-discovery commands live under `tooling library`. Plans
are in [`docs/plans/`](docs/plans/library-discovery-tooling_2026-11-17.md), whose "Shared contracts"
section defines the target, the installation reader and the result envelope.

## Adding a command

1. **Module.** Add `src/corpus_tooling/library/<command>.py` exporting
   `register(group: typer.Typer) -> None`, which calls `group.command("<name>")(<function>)`. The
   coordinator adds `<command>.register` to `REGISTRATIONS` in `library/app.py`. Import Griffe or
   LibCST inside the command function, not at module level.
2. **Item kind.** Subclass `envelope.Item` with `kind: Literal["<kind>"] = "<kind>"`, the
   fields, `columns: ClassVar = (Column("field"), Column("other", "header"), …)` and
   `sort_fields: ClassVar = ("path", "line")` (override `sort_key()` if needed). Both renderings
   come from `columns`. A command with several views declares one item kind per view.
3. **Unresolved kinds.** Subclass `envelope.Unresolved` with `kind: Literal["a", "b"]` (the
   command's closed set) and any extra fields. Omit it when the command has none.
4. **Function.** Take `ctx: typer.Context`, `json: JsonOpt = False`, `limit: LimitOpt =
   DEFAULT_LIMIT`, `offset: OffsetOpt = 0`, `strict: StrictOpt = False` (all from `output`).
   `state = library_state(ctx)` gives `state.target` (a `Target`: `.project`, `.environment`,
   `.display(path)`; call `.require_project()` in a selection-class command) and
   `state.installation` (`lookup(name)`, `distributions`, `import_map`, `import_owners(name)`,
   `skipped`). Resolution happens on first use, so its failures follow `--json`.
5. **Envelope.** `emit(library_envelope(ctx, MyItem, items, limit=limit, offset=offset,
   unresolved_type=MyUnresolved, authorities={"griffe": version}, scanned=n, no_hit_scopes=…,
   excluded=…, skipped_inputs=[SkippedInput(input=…, reason="parse_error")], unresolved=[…],
   unavailable_metadata=[…], notes=[…]), json=json, strict=strict)`. Sorting, paging,
   `truncated`, the baseline block, target notes and the normalized command are filled in.
6. **Failure.** `raise ToolFailure("<kind>", "<what failed>", "<what to pass or fix>")`: exit 3
   with the same envelope, `status: failed`. Progress and diagnostics: `output.progress()`,
   `output.diagnostic(text)` (stderr only).
7. **Tests** under `tests/`, with `typer.testing.CliRunner().invoke(cli.app, ["library",
   "--project", str(path), "<name>", "--json"])`; assert `result.stdout` (one JSON envelope) and
   `result.stderr` separately. Build fixture trees under `tmp_path` from hand-written content
   (`conftest.py`'s `trees`: a fake 3.12 environment, a workspace project); write expectations by
   hand. `tests/test_output_contract.py` registers a probe command the same way.
