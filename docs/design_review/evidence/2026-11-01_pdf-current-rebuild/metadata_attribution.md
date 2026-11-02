# Metadata affinity across native selection

Read-only inventory, 2026-11-01. The live integrated producer changes native pointer identity but
passes parent `values['health']`, parent scoped recognition coverage and physical candidate pages
into the new draft (`ingest/pdf_recognition_methods.py:399,420,441`). The publisher moves any
`health.formula_outcomes` into native metadata. Exact diagnostic:
`runtime/source-prepare-attempt-003-parent-report-attribution.json`. All first20 sampled parent
formula pointers changed content; the actual frozen row for `#/texts/503` says succeeded while
that output pointer is ordinary text. Validation checked existence, not identity attribution.

The current metadata classes are already model-owned by `pds:metadata_classes` in
`model/semantic/pdf-staging.yaml`; their fields belong to `pdf-products.yaml`. The inventory is:

| Existing class/family | Identity-bearing content | Observed source80 inheritance | Required policy boundary |
| --- | --- | --- | --- |
| `PdfFormulaOutcome` / `formula_outcomes` | Current native `pointer` | Implicit through copied health | Fresh materialized integration synthesizes UNKNOWN outcomes for current formula pointers; retain original reports through qualified structural input, or explicitly derive/remap verified retained-node reports |
| `PdfRecognitionCoverage` / `recognition_coverage` | Section pointer plus membership/universe/policy | Copied into output metadata and source-view drafting | Scope membership changes even if section pointer spelling survives; cannot inherit current completeness without a justified current derivation |
| `PdfConversionHealth` | Formula outcomes; inline/cell scope pointers; display/inline/cell coverage summaries and policies | Entire parent health copied | Producer policy must derive current health from current selection; reset unsupported current claims consistently, using the existing fresh materialized integration meaning |
| `PdfCellReport` / `cell_reports` | Table pointer, cell index, optional formula pointer | Not copied by this live producer | Keep parent-qualified; output table/cell identity requires explicit current derivation |
| `PdfInlineAlignmentReport` / `inline_alignment_reports` | Item pointers; page/candidate index; description explicitly qualifies original items through envelope parent | Not copied | Its original parent binding must not be relabelled as the new direct input's graph |
| `PdfDerivationMapping` / `derivation_mappings` | Current pointer and origin pointer | Not copied | Output and origin are different roles; preserve their producing product bindings, never copy unqualified pointer spelling |
| `PdfInlineCandidatePage` / `inline_candidate_pages` | Physical page and ordered candidates/source indices/regions, no native item pointer | Exact encoded Arrow copied | Retain exact bytes/order/source indices under unchanged original source/page-frame binding; this is not a current formula/item recognition claim |
| `PdfRuntimeReport` / `runtime_report` | Observed package/provider/options bindings, no native pointer; model says not success assertion | Not copied | Keep observed producing context; parent runtime facts remain available through the structural input |

The model/producer policy must cover all graph-dependent health and metadata together; merely
checking `label == formula` is insufficient. Another formula can occupy the old pointer, and a
section can survive while its member universe changes. Shared validators should enforce the
chosen identity/affinity rule, while tests retain independent renumbering and changed-universe
expectations. Preserve actual parent records and physical candidate payloads; no new untyped
provenance wrapper or metadata-family registry is needed. The initial inventory made no production changes.

## Integrated correction awaiting book acceptance

The subsequent production correction uses shared `native_conversion_health` for materialized
publication and native record drafts. Fresh integrated health is derived from the selected graph:
current formula pointers receive UNKNOWN outcomes, inline/cell coverage remains unknown and
inherited scoped coverage is not represented as current output coverage. The same shared
metadata validator receives the explicitly validated publication kind for both materialized
outer products and frozen native products; a native envelope alone does not invent a kind.

`PdfIntegratedMetadataPolicy` is typed in `contracts.yaml`; its instance is owned by the archived
`pdf-staging.yaml` dependency. `PreparedPdfContext` retains that hash-checked SourceArtifact from
`sem.input`, so enforcement uses producing-context policy custody, not installed-source fallback.
Historical pre-staging contexts remain readable without an invented current policy; current
contexts require that dependency, and fresh integrated production requires the current policy.
Validation contract v4 binds the canonical metadata-policy digest. Prior unfinished witnesses
cannot silently satisfy the changed policy; existing published input pins remain preserved.

The coordinator reports passing live-input/current-UNKNOWN, changed-universe, historical-context,
materialized-kind and physical candidate-byte preservation controls. Native81 plus the forward82 authoring correction are frozen and deployed to the owned target;
fresh-head native and retirement/authority controls passed. These are component checks and implementation evidence: no new whole-book
integrated source has yet passed or been selected, and cancelled run9 remains unqualified.
