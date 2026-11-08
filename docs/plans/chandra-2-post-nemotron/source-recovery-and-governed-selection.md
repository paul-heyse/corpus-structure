# Source recovery and governed selection

**Case dispositions recorded, recovery and selection work proposed · 2026-11-08.** Companion to the [Chandra coordinator](../chandra-2-post-nemotron_2026-11-08.md). CH-03 can deliver useful alternatives while the promotion question remains open.

<a id="CH-04"></a>
## CH-04 · Locate the loss and decide what qualifies for recovery

For each selected issue, inspect original pixels and available PDF evidence, raw retained responses, native objects, application mapping and selection, projection, and the affected reader. Attribute a loss to the earliest supported layer. Compare a qualified incumbent reading first. Use a Chandra page or crop when it offers independent detail, structure or context. Compare page and crop as separate recipes. The p151 and p416 crop probes reproduced their main content without establishing a marginal advantage. The rotated p509 crop recovered part of the note but retained misleading header and cell alignment. [Live and crop evidence](../../design_review/evidence/2026-11-08_chandra-post-nemotron/README.md#executed-cases)

| Case | Decision and revealing check |
| --- | --- |
| p108, 301 and 334 | Determine when a recovered caption can attach, including shared panels and detached printed labels. Compare the incumbent's dropped shared caption, invented Figure 12 title and asymmetric chart values with the actual printed captions and plotted shape. Keep caption identity, generated description and numeric interpretation separate. |
| p151 Table 4.2 | Compare the published loss with retained Nemotron page/crop values, the extra crop row and Chandra's 4×4 reading. Require the four fractions and C/S header paths to agree with the original before considering a local replacement. |
| p398 and p510 | Verify actual cell content and spans independently of shape. The p398 Chandra grid repairs early Combined Profit values but adds a wrong Z5 where Standard was correct. p510 independently confirms the already correct Combined reading across 344 cells. |
| p509 and table parser limits | Check upright headers and exact row and column alignment, including the note and totals. Retain continuations as separate parts with witnesses before proposing association. Test rich cells, an expanded grid at and above the 1,000-cell parser cap, empty-table fallback, and header continuity. An empty mapped table after an oversize warning is incomplete evidence. |
| p416 and p439 | Compare retained `orig`, selected `text`, Chandra's complete strings, projection and current grammar. All six Chandra p416 matrix strings reached projection and failed the positioned grammar. A readable alternative is already useful. Establish a qualified matrix representation before claiming interpretation. Keep p439's (i/N), recurrence, exercise and conditions associated at their actual scope. |
| p11, p142 and p506 | Retain independent clean controls for exact table values and floor notation, formula/prose boundaries, and running-header-only blank body. A change that helps a target case must preserve the applicable control behavior. |

Use `parse_chandra_html` for structured cell, caption and formula candidates, and the existing PDF occurrence comparison and table/header paths for attributable comparison. Demand positioned syntax where machine-readable math is requested. Use stronger equivalence through the existing math owner only with stated assumptions and an explicit consumer demand. Geometry and syntax can establish localization and structure. Independent source review establishes cell and formula fidelity. [Parser and grid controls](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) · [Existing comparison and selection](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py) · [Reader and grammar evidence](../../design_review/evidence/2026-11-08_chandra-post-nemotron/raw/matrix-consumer.json)

### Decision and closure

For each issue, record the supported source reading, where recovery belongs, affected consumer, residual uncertainty and recommendation. Compare retaining alternatives, local governed promotion and general selection policy. The incumbent policy uses lexical comparisons, replace/add defaults and crop precedence. Those rules do not confer Chandra selection authority. A proposed promotion needs independently checked fields, exact occurrence and region custody, versioned selection and coverage, a protected derived publication, ordinary Reader and packet verification, and clean controls. Resolve the binding and any ADR with the operator before that dependent scope is selected. Route promotion into a separately approved implementation package. A supported decision to retain the incumbent or leave a candidate unresolved closes the investigation for its stated question.

<a id="CH-08"></a>
## CH-08 · Recover witnessed structure from incumbent evidence

**Proposed implementation · 2026-11-08.** Consume the archived integrated baseline,
its exact Standard and A/B/C inputs, the original PDF, and the CH-04 case dispositions.
A Chandra comparison can nominate an investigation. This package derives the correction
from qualified original or incumbent evidence. It delivers the correction through the
existing integrated publication and Reader path.

- **Captions and panels.** Preserve p108's one printed Figure 3.5 caption and each actual
  panel. Use the printed identifier, independent source regions and reading context to
  establish the association and exclude neighboring figures. Use Core's native
  `FloatingItem.captions` references when panels are selected floating occurrences and
  the consumer preserves shared references. When a composite figure has separately
  located panels, represent the association through the existing typed artifact/region
  contract or its targeted extension. A relation does not reparent or duplicate the
  caption. Docling's `link_adjacent_captions` considers one compatible adjacent owner
  and cannot decide this shared case. Test p301 as the separate-caption control.
  [Core floating references](https://github.com/docling-project/docling-core/blob/v2.106.0/docling_core/types/doc/items/node.py#L204-L217) ·
  [Docling caption linkage](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/vlm_utils.py)
- **Table structure.** Recover p151 Table 4.2 by qualifying the C/S header paths, spans,
  exact values and assignment to cells from the source and retained observations. For
  born-digital ruled tables, evaluate the existing Docling Parse backend
  `get_shape_lines(horizontal=…, vertical=…)` and `get_segmented_page()` for independent
  boundary and positioned text evidence. Use the geometry only where the source draws the
  relevant structure. On scans, independently checked positioned OCR or original pixels
  must establish each affected binding. Treat a grid change and all bindings it changes
  as one decision. Preserve stable cell references where the same occurrence survives.
  For continuations, retain separate physical occurrences and link verified fragments
  only when the header, column mapping and boundary support continuity. p398 must retain
  the source-checked `2`, and p509 misaligned cells remain unresolved.
  [Docling Parse page backend](https://github.com/docling-project/docling/blob/v2.148.0/docling/backend/docling_parse_backend.py#L159-L246) ·
  [Native table design](../../adr/0058-native-row-location.md) ·
  [Pinned Docling grid mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py)
- **Formula projection.** Recover source-checked readable `orig` on p416 through the
  formula Reader and attributed projection where its selected text is truncated.
  Keep readable LaTeX, positioned syntax, and interpreted math distinct. Use the
  existing `compare_pdf_occurrences` and positioned grammar to identify the smallest
  representation or grammar gap. Qualify matrix labels, dimensions, delimiters and
  positions before exposing machine-readable matrices. Preserve p439's recurrence
  scope and its conditions, and p142's formula/prose boundaries. Defer matrix
  interpretation if the independent syntax and symbol controls do not qualify.
  [Occurrence comparison](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py) ·
  [Positioned math owner](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py) ·
  [Matrix control](../../design_review/evidence/2026-11-08_chandra-post-nemotron/raw/matrix-consumer.json)

Preserve exact predecessor identity, scope, occurrence correspondences and source witnesses.
Validate the candidate against the original before publishing a complete derived product
through the incumbent authority. Verify the affected Reader, projection and packet
consumers, with search checked when text or hierarchy changes. Keep archived products
readable and stable. If an intended correction cannot be independently derived from
incumbent evidence, deliver the candidate via CH-09 and route any proposed direct
dependency to CH-11. [PDF authority](../../adr/0040-forward-pdf-only-contracts.md)


### Comparator publication reuse

**Proposed follow-up · 2026-11-08.** Use the sealed predecessor and exact
validation contract as premises for a compatible derivation. Identify the changed
native records, companions and byte streams by exact identity. Inherit established
checks only where both inputs and applicable rules match. Recheck the changed
occurrences and dependent references, page frames, containment and section order,
relation endpoints, and affected ordinary projections. Treat p416's readable
formula binding as a projection change when its selected product stays identical.

Qualify incremental and full publication on the same source and compare logical
identity, Reader outputs, search, and packet results. Reject changed bytes,
stale premises, missing dependent endpoints and order changes outside the
declared closure. Use full validation for an incompatible schema, policy,
address migration or an unbounded dependency change. Preserve the predecessor
and the existing single selected document contract.
[Measured validation boundary and parallelization](specialist-extensions-and-scale.md#comparator-execution-fit--2026-11-08) ·
[PDF publication authority](../../adr/0040-forward-pdf-only-contracts.md)

<a id="CH-11"></a>
## CH-11 · Qualify a narrow direct promotion effect

**Conditional target · 2026-11-08.** Reopen only after CH-08 and CH-09 identify a
source-verified useful correction or structure whose construction genuinely depends on
Chandra and whose consumer needs the selected product. Confirm with the operator the
specific addition to selected-input authority under the current CH-04 boundary. A target
review must settle the protected input/address contract before implementation. Retain
the ADR-0040 single selected document and immutable input rules. The current Python
selector admits only A/B/C, and native publication explicitly rejects Chandra inputs.
Both guards remain in force on their existing routes.
[Incumbent selector](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py) ·
[Protected publication](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_publication_native.py)

Use a separately versioned protected derivation over one exact predecessor and original.
Require the Chandra observation pin and exact supported candidate address, the independent
witness addresses, the affected field or relationship and its dependent closure, and the
keep/add/replace/unresolved disposition with its reason. Match using source identity,
physical page, region frame, occurrence type and local context. Treat proximity,
normalized similarity, parser success and model agreement as nomination signals.
A verified native literal must be visible, spatially compatible and healthy for the
target occurrence. Positioned OCR can corroborate literals. Neither verifies a changed
cell binding or a relationship without its own source check.

Current mapped visual candidates reside in a digest-bound artifact and do not populate
the native occurrence inventory. Use versioned, protected artifact addresses for the
candidate side, validated against the admitted artifact and exact source scope. Keep
published relation endpoints in the admitted occurrence inventory. Confirm this
boundary in target review. Record the actual Chandra dependency in the protected derivation. If the protected
address or dependent correspondence cannot be established, retain the attributed
alternative under CH-09 and keep the existing publication authoritative.
[Observation custody](../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py) ·
[Current candidate addresses](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_visual_mapping.py)

First qualification permits one narrowly supported structure type. Demonstrate a useful
independently verified change through the ordinary Reader, search and packet paths where
applicable. Reject wrong original, stale predecessor, witness outside scope, invented
cell or edge, and partly verified dependent structures. Exercise a failed publication,
retry, exact replay and retained predecessor read. Model majority, whole-page replacement,
and unqualified specialist metadata have no path to selected facts through this effect.
Record the new decision and its governing contract through the repository ADR route
before activation.
