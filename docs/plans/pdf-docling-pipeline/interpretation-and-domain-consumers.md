# Mathematical interpretation and domain consumers

**Status:** Planned target; no PDF implementation or qualification is claimed.
**Created:** 2026-10-31. The [coordinator](../pdf-docling-pipeline_2026-10-31.md) owns
PDF-06/07 status, investigation outcomes and scheduled disposition of review O04/O05.
Consumes the [functional review](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O04)
at `2c33372` and its [target model](../../functional_reviews/pdf-docling-pipeline_2026-10-31_target-model.md).
RC01–RC05 were selected by the operator on 2026-10-31; their architecture route is PDF-00.

## Foundation assessment and resulting boundary

`methods/math/spans.py` currently discovers `math_inline`/`math_display` segments and strips
HTML-source delimiter pairs. `PreparedMathInput` in `methods/math/prepared.py` separates lexical,
structural, syntax, interpretation, symbolic and assessment demand, while `scope.py` and
`source_context.py` retain declaration position and applicability. Reuse the useful scientific
contracts and lazy preparation; replace source discovery rather than wrap the whole historical
frontend around a Docling blob.

`semantic/proposals.py:519` hashes and renders a packet containing sentences, entities, macros
and scope coverage. It does not yet supply native PDF item/table/formula/region context.
`semantic/source_frames.py` checks packet hash, native rendition and sentence coordinates.
Changing packet rendering alone leaves persistence/admission inconsistent. Version the complete
producer, frame, packet, submission and downstream evidence contract together under PDF-02/03.
Only consolidation writes knowledge claims; document labels remain attributed observations.

<a id="PDF-06"></a>
## PDF-06 — Formula-item interpretation and scientific analysis

**Owner:** mathematical-method integration. **Requires:** PDF-02's admitted formula/context
contracts; PDF-04 recognized formula products; PDF-05 ordered item/text mappings; I03 coverage
and recognition-health results and I05 native-parser compatibility. Pure adapter work may use
agreed contracts before storage is deployed; durable qualification requires PDF-03/09.

**Result:** M09 and M11 consume pinned formula occurrences and recognized LaTeX directly.
Discovery no longer scans HTML delimiters, acquires MathJax macros or reconstructs rendered math.
Retain untreated `orig`, recognized `text`, producing conversion/item, recognition outcome and
source-region links separately. A recognized string is not the author's original TeX source.

Use SymPy 1.14.0 `parse_latex(..., backend="lark")` as the starting native adapter.
When I05 demonstrates a required grammar/transformer gap, prepare `LarkLaTeXParser` through
`grammar_file`/`transformer`; its installed constructor is
`(print_debug_output=False, transform=True, grammar_file=None, transformer=None)`.
Do not use unverified `local_dict`/`global_dict` constructor examples or quietly fall back to
ANTLR, which can accept a valid prefix of malformed input. Compare actual recognized sets,
relations, binders, operators, matrices and `f(x)` ambiguity before retiring supported extensions.
Retain only the necessary extension through native mechanisms, with explicit capability/outcome.

M09 must preserve repeated symbol occurrences and consumed occurrence positions. A normalized
SymPy expression may merge or simplify them; it cannot replace an occurrence inventory.
When positions are needed, derive them in recognized formula-text coordinates and map the
formula occurrence to its PDF region. Do not claim glyph-level alignment from an item box.
If native syntax does not provide the required positions, I05 selects the smallest supported
positioned adapter; no second general formula recognizer is added by default.

M11 separates availability/recognition from interpretation, symbolic normalization and assessment.
Reuse operation-owned preparation by formula content, kind, admitted recipe, context/declaration
basis, assumptions and requested demand. Preserve contextual symbol roles, `Dummy` isolation,
`Q`, `ask`/`refine` and source definedness where required. An unqualified logarithm cancellation
or normalized equality cannot establish unstated domain assumptions. Unevaluated expressions
may be available; ambiguity/unsupported/unknown are meaningful results, distinct from failure.
A syntax or inspect request must not trigger a stronger symbolic or assessment stage.

**Recognition boundary:** I03 must account separately for detected formulas, inline prose math
and table-cell mathematics. Tagged Docling 2.145.0 can retain unchanged backend text after an
enrichment exception; nonempty `text`, FORMULA label or `text != orig` is not a success receipt.
Ordinary PDF table cells are a known enrichment gap ([issue 3828](https://github.com/docling-project/docling/issues/3828)).
Do not feed arbitrary visual-order cell strings into the parser as successful LaTeX or infer
complete absence of math from missing formula items.

If actual corpus cells expose the gap, PDF-04 owns the selected supported cell-aware enrichment
route using existing page/cell geometry and rich-cell→FormulaItem links in a derived document.
This package consumes that qualified result. If no route is qualified, the dependent capability
remains unresolved; wider VLM comparisons are investigation candidates, not automatic parallel
production pipelines. Product completeness must not hide unsupported recognition regions.

**Retirement:** remove delimiter/macro/rendering-only paths after every current M09/M11 consumer
has moved. Retain historical decoding without promising to rerun an old source adapter. Archive
the new implementation and parser/model recipes through the existing release manifest.

**Acceptance:** actual Docling output reaches native parsing; repeated equal formulas/symbols
retain occurrence identity; malformed trailing input and unresolved function/multiplication do
not silently become success; domain conditions survive simplification; weak demand avoids
stronger work; inline/table gaps and caught enrichment failures remain explicit. Reuse and
retry do not turn a budget-dependent failure into a cached successful interpretation.

<a id="PDF-07"></a>
## PDF-07 — Section-grounded domain recognition, scope and packets

**Owner:** domain-method and proposal integration. **Requires:** PDF-02/03 qualified source
addresses and native frame storage, PDF-05 section hierarchy/text views, PDF-06 where math is
consumed; I04 hierarchy applicability and I08 actual extraction/reference journey selection.
I03 recognition coverage remains part of scope evidence even for methods not demanding SymPy.

Replace HTML-class author markup and `<details>` containment hints with model-declared recognition
rules over section/item labels, content and relations. The source profile currently recognizes
definitions/theorems/exercises, proof/solution context, author IDs and references; PDF heading
labels alone do not replace these semantics. Preserve which rule/library/source evidence
established each recognition and its uncertainty. Do not synthesize `proves` merely because a
visually inferred block occurs beneath another item.

Use intact sections/subsections as the organizing units. Method-specific item selections are
views within that hierarchy, not persistent chunks. Declare direct versus descendant membership
per operation so parent/subsection traversal does not duplicate extraction. Physical page breaks
do not end logical sections, statements or scope. Cross-page continuation remains unresolved
where not established by a qualified producer; proximity alone cannot create it.

M13 derives structural scope from section ancestry and local statement membership, retaining
source order and each declaration's forward applicability extent. A declaration midway through
a section must not affect earlier formulas or unrelated sibling statements. Explicit reopening
and shadowing retain typed evidence. Missing/unsupported formula recognition contributes partial
or unknown scope coverage rather than complete absence of declarations or symbols.

Generate spaCy `Doc`/sentence inputs from PDF-05's reusable item-to-text projection. Preserve
atomic math/reference behavior of the shared text layout where required; use existing prepared
layouts and `nlp.pipe` rather than tokenize the same section per consumer. Synthetic separators,
ancestor headings added for prompting and repeated table headers are contextual additions,
not original source spans. Do not round-trip Markdown to recreate Docling structure.

Version `ProposalPacket`, source frames, proposal schemas and native submission enforcement to
carry bounded section ancestry, ordered item/cell/formula references, recognition health,
relevant table headers/spans, captions, PDF regions and source/scope coverage. Include the actual
supplied values and producing products in packet identity. A changed context must change the
packet binding; descriptive context discarded before hashing does not satisfy this package.
Keep source-frame coordinates qualified: canonical/text projection ranges are not PDF geometry.

A table cell is eligible typed evidence without being reduced to prose. Preserve
`TableData.table_cells`, row/column offsets, spans, header roles and rich-cell references;
`grid` is a derived access view. Figures and captions remain connected to evidence and can be
retrieved on demand. Do not embed the whole book or every page raster in each proposal packet.
Transport paging delivers one intact unit's context; it does not define semantic chunks.

**Acceptance:** a real packet from a selected intact section exposes and hashes native context;
source-frame capture and native proposal admission agree with it. Cell/formula/figure evidence
resolves back to the selected conversion. A mid-section declaration, sibling exercise and page
break exercise ordered scope. Missing recognition does not produce false complete coverage.
Independent grading stays isolated from extraction; existing answers/references are not silently
re-anchored. PDF-11 owns the assembled provider journey and required evidence union.

## Sources and evidence limits

Concrete library mechanisms and version-sensitive limits are retained from review O04/O05,
[SymPy parsing](https://docs.sympy.org/latest/modules/parsing.html), the local
[SymPy overview](../../libraries/Sympy.md), [spaCy overview](../../libraries/spacy.md),
and [Docling OCR technical-PDF guidance](../../libraries/docling_ocr.md).
I03/I05 resolve remaining native API/coverage uncertainty before dependent claims. These packages
are planned work, not proof of parser fidelity or a measured efficiency gain. No inference,
product test, grading run or dependency change was performed to author this document.
