# Grinstead–Snell whole-book development

The [NCE coordinator](../../../plans/next-corpus-enrichment_2026-11-07.md#full-book-execution)
owns current execution and the audit findings. [ADR-0070](../../../adr/0070-full-book-method-development.md)
selects the original 518 physical pages as one shared development origin. The
[original GS120 benchmark](../2026-11-06_wce-gs120/README.md) preserves its own
source selection, outputs and assessment.

The input is the exact parent `Introduction_to_probability_grinstead_and_snell.pdf`
with SHA-256 `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
Place a verified copy under `WORK/corpus/`. Use a copy within the selected corpus
directory so the native original registration's containment check applies.

```sh
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/intake.py WORK --release RELEASE
uv run ci run finalize RUN --output-realization nce-gs518-source-result:RUN --json
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/enrich.py RUN WORK/baseline --release RELEASE --phase inventory
```

The intake uses the existing registered graph with one explicit original, then
runs the annotation method over its selected views. The generic `ci project init`
route selects the pack's default original, so the evidence runner supplies the
existing project registration function with the exact one-file method configuration.
The inventory checks the native page membership and freezes source-only samples.
It reports physical coverage and text projection separately.

Run `enrich.py` on the same pinned input with phases `scoped`, `model`, and
`artifact`. The scoped phase selects source-conditioned table correspondence.
The model phase selects the released bare/flat definition arm with the named
producer enabled. The artifact phase consumes the full eligible source inventory.
`contextual.py` consumes the exact scoped phase receipts and uses the book's
complete selected heading inventory for its eligible cue views. Each phase retains
its actual task scope and independent completion state.

Use the managed installed Reader and exact closure for evidence delivery. Keep
protected authoring and assessment material separate from source-only packets and
ordinary review bundles.
