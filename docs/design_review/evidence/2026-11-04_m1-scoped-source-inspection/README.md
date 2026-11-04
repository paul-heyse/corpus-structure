# Scoped ordinary native source inspection

**Current corrected result:** [chart custody and complete compact-view inventory](correction/README.md),
finalized as [m1.scoped-source-inspection-correction](records/m1.scoped-source-inspection-correction.json).
It supersedes the initial result described below. The original results and raw receipts remain
intact; only predecessor supersession metadata changed.

**Implemented; focused checks Tested, 2026-11-04.** This folder retains the bounded M1 F22
implementation checks and actual retained-source reads. The coordinator owns adoption and
assembled qualification. The earlier failures and larger-budget receipts remain in
`../2026-11-04_m1-actual-consumers/` unchanged.

The authorized change composes existing exact occurrence custody for a selected cell and its
parent, and reads formula membership/health/reference metadata without hydrating an analytical
source view. Native API v4 retains its existing shared internal row/byte-work allowance and
complete response limit. Whole SDK response admission remains unchanged. No model, PDF,
database bootstrap, grant, default, dependency, native migration or reference-author work is
part of this slice.

Targeted tests and actual read-only run 11 / run 14 journeys are recorded under `raw/`.
They are not whole-M1, five-family, accepted-reading or independent-quality qualification.

## Implementation

`serve/native_source.py` composes a cell companion from the exact cell occurrence and its
parent native item. Kind, pointer, occurrence identity and cell index must match before
`PublishedPdfReader.occurrence_context()` supplies all selected relations/endpoints, input
pins, applicable coverage and mapping reports. Sibling cells are outside this request's
selection; whole-item/table requests retain their existing broader meaning. Native products
without an integrated companion keep their existing `None` result.

`semantic/source_views.py` reads the compact retained source projection and recipe bytes,
charges both to the same invocation budget, and reuses `SourceViewDraft` validation plus its
projection/recipe digests. It verifies the exact published placement and reads only the selected
native formula to qualify membership/kind. Returned health remains scoped to that formula,
including explicit `unknown`. No partial `PreparedSourceView` is constructed.

`BoundReader.source_view_ref()` and `source_observations_for_ref()` preserve selected-run and
supersession authorization without analytical hydration. Existing `source_view()` and
`source_observations()` consumers retain their full-view behavior. `native_analysis.py` shares
the existing resolver across complete and selected-formula reads, retaining projection/recipe/
product bindings, producer ambiguity, named observation dependencies, cycle checks and typed
unavailable/not-requested distinctions. Observation reads retain the existing optional cut join.

No public source API fields, v4 budget meaning, protected operation, physical table, native SQL,
grant, service default or model setting changed. The existing canonical-response and complete
SDK-envelope limits still apply.

## Focused checks

**Passed:**

```bash
uv run pytest python/corpus-structure/tests/semantic/test_scoped_native_inspection.py python/corpus-structure/tests/semantic/test_native_source_published.py python/corpus-structure/tests/semantic/test_native_source_budgets.py python/corpus-structure/tests/semantic/test_mcp_source_transport.py -k 'not postgresql and not source_search_preflights_selected_scalar_bytes and not native_queue_ack_refusal'
uv run pyrefly check python/corpus-structure/src/corpus_structure/serve/native_source.py python/corpus-structure/src/corpus_structure/semantic/native_analysis.py python/corpus-structure/src/corpus_structure/semantic/operations.py python/corpus-structure/src/corpus_structure/semantic/source_views.py python/corpus-structure/tests/semantic/test_scoped_native_inspection.py
uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/run.py actual-001
uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/run.py actual-002
```

The initial focused suite passed 76 cases (`raw/targeted-pure-001.log`). After adding malformed
projection with a matching recomputed hash, bulk-path preservation and parent-custody cases,
the expanded selected suite passed 82 cases with 3 native database-mutating cases deliberately
deselected (`raw/targeted-pure-002.log`). Targeted Pyrefly returned `0 errors` (`raw/types-001.log`).
Fixtures in the pure transport tests assess adapter mechanics; the actual provider/read journey
is separately retained by `run.py`.

The initial live journey passed 57 selected comparisons (`raw/actual-001/summary.json`): actual
reader-principal queries, CLI subprocesses and registered in-process MCP on pinned old runs
11 and 14, using the retained integrated product and unchanged 1 MiB request budget. It also
retains explicit small-work-budget refusals. This first receipt predates final source formatting;
the coordinator's final formatting and native integration remain separately owned.

| Actual retained selection | Complete MCP response | Companion before / after |
| --- | --- | --- |
| Run 11 formula `#/texts/255` | 20,859 bytes | Formula meaning, metadata, source health and companion preserved |
| Run 11 table cell 0 | 35,959 bytes | 643,785 / 15,844 bytes |
| Run 14 formula `#/texts/255` | 20,859 bytes | Same source fields and companion; run-relative interpretation remains pinned |
| Run 14 table cell 3 | 35,983 bytes | 643,785 / 15,851 bytes |

The cell comparison independently selects expected relation identities from the earlier full
companion's native endpoint pins and selected cell/parent identities, then compares complete
relation bodies/endpoints. Coverage remains exact; retained occurrence/input/mapping rows must
come from the prior companion. Native values, blank semantics and source health remain exact.
Formula reads preserve original/recognized text, recognition metadata, alignment reports,
regions and companion. These are transport/custody comparisons, not recognition-quality
or scientific-meaning oracles.

After the coordinator's final formatting, the selected pure suite again passed **82 cases**
with the same 3 native database-mutating cases deselected (`raw/targeted-pure-003.log`). Scoped
Ruff and Pyrefly passed (`raw/lint-final-001.log`, `raw/types-final-001.log`). The final-source
live journey passed **58 selected comparisons** (`raw/actual-002/summary.json`), including stable
source hashes before/after the run. Its source values, complete SDK envelope sizes, companion
sizes and explicit small-budget refusals agree with the table above. Earlier receipts remain
unchanged. Actual transport is registered **in-process** MCP against the real reader database;
this is not an external host attachment or HTTP-service qualification.

`finalize_record.py` uses the existing evidence store's `Folder`, `Record` and `finalize` APIs
against this folder only, avoiding reads of unrelated reference-author/held-out records and
leaving global index/catalog publication to the coordinator:

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-scoped-source-inspection/finalize_record.py
```

**Not_run:** native migrations/bootstrap, model/PDF execution, broad product qualification,
default/adoption changes or independent reference/held-out author inspection. The coordinator
owns native127 integration and any subsequent complete source-context run.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 1 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Chart parent custody and complete compact source inventory](records/m1.scoped-source-inspection-correction.json) | M1-12 | passed | F22 | 2026-11-04 |

**Superseded**

| Record | Superseded by | Finalized |
|---|---|---|
| [Scoped ordinary formula and cell native inspection](records/m1.scoped-source-inspection.json) | m1.scoped-source-inspection-correction | 2026-11-04 |
<!-- evidence-index:end -->
