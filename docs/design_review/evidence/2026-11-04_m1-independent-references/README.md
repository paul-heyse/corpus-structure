# M1 independent source-reference preparation

**Implemented preparation; actual invocation not_run (2026-11-04).**
`prepare_reference_sets.py` creates the existing protected reference sets and
source-only author packets from explicitly named final-release source-ready runs.
It does not read predictions, A/B/C passes, learned parameters or evaluation
grades. It runs no PDF conversion, recognition provider or extraction model.
Independent A/B/C acquisition and all resulting quality/release dispositions
remain subsequent work owned by the M1 coordinator.

The script uses the exact UTF-8 bytes of
[`domains/statistics/m1-reference-guideline.md`](../../../../domains/statistics/m1-reference-guideline.md),
version `statistics-m1-reference-2`. It declares the separate reference policy
`statistics-reference-reading-2` and prediction policy
`m1-grouped-reading-logistic-1`. These strings do not replace the released domain
model. Exact archived `ReferenceRecordBatch` schema and `record_projection.json`
bytes accompany the packets, preserving every released role/requiredness and the
generic occurrence recipe; the domain guideline owns its family/binding
occurrence policy. No additional guideline or semantic protocol is authored here.

Supply a JSON mapping with the final semantic `release_id` and an `origins` array.
Each entry contains:

- `origin_group`, `partition`, `project_id`, `source_run_id`, `source_cut_id`:
  actual retained source identity and an explicitly sealed final-release cut.
- `label`, `cohort`: descriptive names for the existing reference set and frozen
  sampling cohort. `seed` is optional and defaults to `20261104`.
- `origin_provenance`: a nonempty source-only provenance object naming the original,
  excerpt/parent-page manifest and digests, and common-copy/edition grouping as
  applicable. Native immutable origin assignment remains authoritative.

The script requires each run and every selected source view to match the supplied
final release. Native106 intake IDs cannot stand in for final-release projections.
It neither selects an active/default pointer nor guesses a current source run.

Every `source_units` member enters the census with inclusion probability 1,
including non-analysis, empty and unreadable units. Source health and missing
native context targets are retained. No-output predictions and candidate
uncertainty have no part in selection. The legacy document split is explicitly
`dev`, independently of the declared origin partition; existing contradictory
assignments are refused by the native split operation rather than rewritten.

Frames use the actual source-binding alias and native product/view/recipe digests.
Scopes include native item/cell coarse and item addresses, exact native text
extents when available, and individual genuine selected-projection text-piece
extents. Synthetic separators do not acquire exact scopes. Explicit native
caption/footnote/reference targets absent from the primary view can add a
same-product selected context view; the smallest containing projection is chosen
by source metadata, with source-view identity breaking ties. This establishes
selected custody, not scientific or note applicability. A related view's exact
pin remains separate. Primary native ancestors already belong to its own frame.

Optional `related_contexts` maps a primary source-view ID string to objects with
`source_view_id` and `needed_reason`; these declare additional actually selected
same-product contexts before authoring. Optional `captured_coordinates` uses the
same primary-ID map, with each object containing `source_view_id`, `pointer`, the
released `recognition` address and `needed_reason`. Captured coordinates are absent
by default. When explicitly needed, the script reads their text only through
`ops.record_captured_recognition_text`, which authenticates retained lineage and
unchanged provider precision. It neither reconstructs missing recognition nor
relabels recognition as canonical native text. Native set/frame creation
independently revalidates all pins, scope bounds and retained capture addresses.

From the repository root, after the final source mappings exist:

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-independent-references/prepare_reference_sets.py \
  --mapping /path/to/final-source-mapping.json \
  --out docs/design_review/evidence/2026-11-04_m1-independent-references/freeze-001
```

An existing output directory is refused. Ordinary `read` credentials hydrate
retained source views in a read-only repeatable-read transaction. Existing
`evaluate` credentials assign origins/splits, freeze reference sets and retrieve
author packets. No elevated maintenance role or disposable database is required.
Each origin's reference operations commit together; failure retains a diagnostic
and any completed-set IDs so an interrupted attempt can be reconciled without
silently replacing prior evidence.

Outputs retain the original input mapping and guideline bytes; exact released
schema/role artifacts; each set's frozen sampling, source census and per-unit
author packet; and manifests linking set/unit/run/cut IDs, projection/frame/packet
digests, native sampling digest and canonical sampling digest. Packets are inputs
for independent authors, not submitted reference answers. Retain failed outputs;
use a fresh output directory for a revised invocation.

Preparation checks on 2026-11-04: `--help` passed without opening a database;
scoped Ruff `E4,E7,E9,F,I` checks passed. Actual frame validation, reference-set
creation, label acquisition and quality qualification are `not_run` here.
