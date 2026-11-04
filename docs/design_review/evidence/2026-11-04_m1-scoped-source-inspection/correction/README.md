# Chart-cell parent kinds and complete compact-view inventory

**Implemented; focused controls Tested, 2026-11-04.** This followup corrects two independently
identified gaps in the earlier scoped-source implementation. The original finalized record,
probe sources and `../raw/` receipts remain unchanged; the revised result will supersede it.

Chart pictures have a `chart` parent occurrence, whereas tables have an `item` parent. Ordinary
cell custody now checks the declared parent kind for the selected native address family. Tests
cover both valid table/chart cases and refusal of a table-kind parent for a chart cell.

The compact formula read now validates **every** `projection.items` and `projection.ancestors`
address against the exact retained published product before hydrating the selected formula.
`PublishedPdfReader.require_native_item_inventory()` projects the existing protected native
item statement to product/revision/pointer scalar columns, uses the existing shared row/byte
preflight/accounting, and refuses missing, duplicate or foreign-placement results. It transfers
no sibling native bodies. Complete inventory remains checked even if a corrupt projection's
digest was recomputed to match its added nonexistent item or ancestor.

Runtime changes were paused after the stability signal while the coordinator performs its
source-and-annotation reconstruction. No model/PDF work, database writes/bootstrap, grants,
defaults, migrations or reference-author/held-out reads are part of this correction.

Initial correction controls: `raw/corrections-pure-001.log` has 44 passed tests;
`raw/corrections-types-001.log` retains three test-mock typing defects, corrected with the
passing scoped `raw/corrections-types-002.log`. Final formatting and final-source read-only
query/CLI/registered MCP receipts follow the coordinator's readiness signal.

## Final-source results

After root's final formatting and native128 readiness signal, the expanded focused suite
passed **90 cases**, with the same 3 native database-mutating cases deliberately deselected.
Scoped Ruff and Pyrefly passed. The actual read-only query/CLI/registered in-process MCP
journey passed **58 selected comparisons** at the unchanged **1 MiB** allowance, with all five
runtime source hashes stable before/after the run. Formula envelopes remain 20,859 bytes;
table-cell envelopes remain 35,959 and 35,983 bytes on old pinned runs 11 and 14. Explicit
small-work-budget refusals remain typed. These final receipts are under `raw/actual-final-001`.
Chart-parent correctness is established by focused table/chart controls; this followup does not
claim an actual chart-provider/PDF journey.

Commands from the repository root:

```bash
uv run pytest python/corpus-structure/tests/semantic/test_scoped_native_inspection.py python/corpus-structure/tests/semantic/test_native_source_published.py python/corpus-structure/tests/semantic/test_native_source_budgets.py python/corpus-structure/tests/semantic/test_mcp_source_transport.py -k 'not postgresql and not source_search_preflights_selected_scalar_bytes and not native_queue_ack_refusal'
uv run ruff check python/corpus-structure/src/corpus_structure/serve/native_source.py python/corpus-structure/src/corpus_structure/semantic/native_analysis.py python/corpus-structure/src/corpus_structure/semantic/operations.py python/corpus-structure/src/corpus_structure/semantic/source_views.py python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py python/corpus-structure/tests/semantic/test_scoped_native_inspection.py
uv run pyrefly check python/corpus-structure/src/corpus_structure/serve/native_source.py python/corpus-structure/src/corpus_structure/semantic/native_analysis.py python/corpus-structure/src/corpus_structure/semantic/operations.py python/corpus-structure/src/corpus_structure/semantic/source_views.py python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py python/corpus-structure/tests/semantic/test_scoped_native_inspection.py
uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/correction/run.py actual-final-001
uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/correction/finalize_record.py
```

`pure-final-001.log`, `lint-final-001.log`, and `types-final-001.log` retain final-source outcomes.
The dedicated evidence finalizer uses the existing store APIs on this folder only. It writes
the new record and changes only the old record's `status` and `superseded_by`; previous
conclusions, results, finalized hashes, probe sources and receipt bytes remain unchanged.
Native full regression, the coordinator's preparation-only reconstruction, five-family quality,
accepted readings, default/adopted release and whole-M1 qualification are separate obligations.
