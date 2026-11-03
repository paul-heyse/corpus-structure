# Design questions and decisions

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/a66f75cca0e243f791bda208f4f9c69f?pvs=204) · [First production milestone](../first-production-milestone.md)

Open and deferred items carry the source’s recommendations where present. Decided rows retain their original scope
and rationale. The proposed M1 deployment supersedes earlier rollout assumptions where the two differ.

[Open (48)](#group-open) · [Decided (27)](#group-decided) · [Deferred (2)](#group-deferred)

<a id="group-open"></a>

## Open

<a id="notion-40b141b5836981d794fafbde9626cc97"></a>

### Do the corpus-support parameters in the reference code mean what the derivation defines?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L4 Interpretation layer, Current implementation · [Notion record](https://app.notion.com/p/40b141b5836981d794fafbde9626cc97)

- **Why it matters** — The derivation defines π\_g as the interpretation confidence that group g states the claim
  and r\_g as the likelihood ratio a correctly read statement provides. The L4 contract table and the 31 October
  summary call π\_g per-source reliability and r\_g recall. The formula Λ\_g = π\_g r\_g + (1 − π\_g) is the same,
  but fitted values would not be interchangeable.
- **Options** — Align the code's names and fitting to the derivation; revise the derivation to the code's meaning.
- **Recommendation** — Check `interpret/support.py` on the reference branch against the derivation, then align the
  names.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

Found while carrying the math formalization into [📚 Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b) (1 November 2026).

<a id="notion-40b141b5836981d283bac12028533f83"></a>

### Docling conversion output can vary between runs and machines

**Kind** Risk · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981d283bac12028533f83)

- **Why it matters** — The input digest (PDF digest plus Docling version and configuration) is a cache key, and
  observation keys hang off Docling element references. If the same PDF and configuration can convert differently,
  cached observations and lineage silently stop matching. Docling 2.145.0 has five known sources of variation:
  timer-based batch assembly (#4274, open), Auto engine selection, font fallback when rendering (#4995, open), GPU
  kernel selection, and thread count on CPU (not checked).
- **Options** — Pin the engine, model files, scale, thread count and fonts, which the reference says removes most
  sources; embed every font at the rendering step so fallbacks never apply; never use OcrAutoOptions; batch timing
  has no configuration fix in 2.145.0 and waits on #4274; re-convert a fixed sample after any change and compare
  element text and boxes to detect drift.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

The sources of variation are listed in the Docling OCR reference §18.4. The configuration side (pin the OCR configuration in the input digest, embed fonts, avoid Auto selection) is on [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15). What remains open is the batch-timing source, which no setting removes in 2.145.0, and whether thread count changes RapidOCR output on CPU, which was not checked.

#### Evidence

None measured. The reference was read from source and nothing was run (§1.2).

#### Sources

- [🔤 Docling OCR reference](https://app.notion.com/p/40b141b5836981b3a105db8f3d39a4b9) §2.3, §10.4, §16, §18.4, §19.4 (see [🔤 Docling OCR §16–19 · Region OCR, several engines, performance and evaluation](https://app.notion.com/p/40b141b5836981579adfd9dd27dd061b) and [🔤 Docling OCR §10–12 · Other engines, plugins and whole-page VLM OCR](https://app.notion.com/p/40b141b5836981a5a3b1c1c646b2586a)).

<a id="notion-40b141b5836981809107db890b0ce06c"></a>

### Does marginal contribution to complete records rank the specialist models differently from their published scores?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L2 Model streams, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b5836981809107db890b0ce06c)

- **Why it matters** — The specialist portfolio is also judged by marginal contribution to complete records. A model
  that adds reliable role, scope or temporal information may contribute more than another model producing similar
  entity spans. That is a hypothesis to test on the corpus, not something leaderboard positions show, and it decides
  which models are worth their CPU time.
- **Options** — Use the prototype ablations (Shapley values and Möbius dividends over stream groups, counted in
  correct accepted records) to rank streams by marginal contribution; or keep choosing by published score per role.
- **Recommendation** — Rank by marginal contribution from the prototype ablations once calibrated LLRs exist; keep
  published scores only as the starting choice.

<a id="notion-40b141b583698173a9cac652a89744dc"></a>

### How are inline formulas drawn as vector paths recovered?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b583698173a9cac652a89744dc)

- **Why it matters** — Page-stage OCR cannot put path-drawn glyphs into a native text line, whatever the engine, and
  formula enrichment covers only regions labelled as formulas, never table cells. Quantities and relations inside
  these formulas are otherwise missing.
- **Options** — Flag elements with unaccounted vector shapes, then re-convert the region with the formula model or a
  grounded VLM and keep both readings in the side record (the current idea on the Docling configuration page); a
  whole-page VLM; FULL\_PAGE or LAYOUT\_REGIONS with OCR priority, which replace good native text; a Nemotron Parse
  second layer used for gap filling in a derived document.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

#### Detail

Discussed on [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15) (Known gap) and [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30) (§13.7). How often region re-conversion runs depends on [What is λ, the CPU-seconds worth one extra correct record?](#notion-40a141b5836981238197f12f6cd8dda8).

#### Sources

- [🔤 Docling OCR reference](https://app.notion.com/p/40b141b5836981b3a105db8f3d39a4b9) §3.4, §4.4, §13.3–§13.5, §16.

<a id="notion-40b141b5836981aa9888fb8a32fcdf00"></a>

### How are scanned pages detected and routed to full-page OCR?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981aa9888fb8a32fcdf00)

- **Why it matters** — Docling 2.145.0 has no built-in way to OCR only scanned pages (#4834). At scale 3 an A4 page
  is shrunk to about 170 DPI before recognition unless max\_side\_len is raised. The L0 route also turns on
  detect\_orientation, which the repository's ObservedRapidOcr refuses.
- **Options** — PDF-aware mode for every page (reads every layout cluster of a page with no text layer, but not text
  the layout model missed); a separate FULL\_PAGE conversion for scanned documents, with RapidOCR
  Global.max\_side\_len raised (no native decode; the mode applies to the whole conversion); a page-level threshold
  as proposed in Docling PR #4999 (open, not in 2.145.0).
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Discussed on [🚨 Failure handling](https://app.notion.com/p/40b141b583698173977ced93021aac08); the scanned-input configuration is on [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15).

#### Sources

- [🔤 Docling OCR reference](https://app.notion.com/p/40b141b5836981b3a105db8f3d39a4b9) §3.1, §3.2, §3.4, §7.4, §19.3.
- [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) §2.1 (detect\_orientation refused by ObservedRapidOcr).

<a id="notion-40b141b5836981bfa9a3c8877162dd5a"></a>

### How do the repository's PDF pipeline decisions (ADR-0038 to ADR-0045) relate to the Notion L0 front end?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** Current implementation, L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981bfa9a3c8877162dd5a)

- **Why it matters** — Since 31 October the repository's main branch implements a PDF-only front end: Docling
  2.145.0 StandardPdfPipeline with in-page RapidOCR, a mandatory Nemotron Parse 3.5 true triple pass and one
  integrated document, decided in repository ADRs 0038 to 0045 and planned in its PDF coordinator (PDF-00 to
  PDF-28). The Notion L0 pages describe the front end as target design and present Nemotron Parse as informational.
  Front-end decisions are now recorded in two places that can drift.
- **Options** — Notion L0 owns the target and the repository ADRs record what is implemented, with differences
  listed on the L0 pages; the repository ADRs own the front end and L0 summarizes them; reconcile item by item when
  each L0 page is written.
- **Recommendation** — Notion owns the target design (Paul, 31 October); L0 pages cite the repository ADRs as the
  implemented state and name each difference.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Repository main at commit 040ba08 (1 November 2026, 09:31) holds ADR-0038 (PDF-native Docling products), ADR-0039 and ADR-0040 (integrated PDF products; no historical HTML compatibility), ADR-0041 to ADR-0045 (PDF publication, segmented byte identity, native metadata and payload validation). The HTML ingest of the parsing review's baseline (commit 430e026) has been removed. The initial PDF is the Siegrist `Full.pdf`, 1,589 pages. Whole-book recognition passed; integrated publication, consumer adoption and complete qualification remain open in the repository's own plan. Upstream conversion of other formats to PDF is outside the repository's scope.

#### Sources

- [📦 What the repository has today](https://app.notion.com/p/40b141b58369814894d7d932105906bf)
- [📄 L0 · Front end: published form to PDF to Docling](https://app.notion.com/p/40a141b58369811b8cd1dc6d9da943b3)
- Repository `docs/plans/pdf-docling-pipeline_2026-10-31.md` and `docs/adr/README.md` at commit 040ba08.

<a id="notion-40b141b5836981b58acdf5c6452d92bd"></a>

### How is the published form identified for each source type?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981b58acdf5c6452d92bd)

- **Why it matters** — It fixes which text every later anchor and observation refers to, and it decides what the
  published form leaves out, which conversion-time metadata must then keep.
- **Options** — The rule so far: the version a reader would see. Examples given: the final rendered paper, not the
  LaTeX; the issued standard, not the draft; the rendered email. Not yet covered: office documents with tracked
  changes or comments, web pages, and sources that already arrive as PDF (passed through unchanged or rendered
  again).
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Discussed on [🔎 Published-form resolution](https://app.notion.com/p/40b141b5836981558918faf10ad69a8f).

#### Open questions

- [What happens to structure that conversion to PDF destroys?](#notion-40a141b5836981de810ef76dc4f8027c)

#### Sources

- L0 front-end page: Flow, step 2, and the empty open section "Published-form resolution per source type" (31 October 2026).

<a id="notion-40b141b5836981b29a4ce65382f99912"></a>

### How much of each hard capability family do the structured routes reconstruct before the CPU LLM composes?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L3 Tiers and combinations, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b5836981b29a4ce65382f99912)

- **Why it matters** — The structured routes for F1, F4, F6, F7, F9, F12, F13 and T5 are proposed subsets to test,
  not claims that the families are solved, and the Capabilities register still rates all eight as Unlikely for CPU
  composition. Until the share each route reconstructs is measured, the size of the residue that 9.6 sends to the
  CPU LLM, and so its CPU cost, is unknown.
- **Options** — Measure per family on sampled passages, with what should have been extracted identified
  independently: share of complete records from the structured route alone, share completed by the CPU LLM from the
  pre-grounded context, and share left unresolved. Or measure only the families present in the corpus.
- **Recommendation** — Measure only the families the corpus actually contains, at stage 9, against the
  non-generative baseline; update each family's CPU composition outlook from the result.
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-40b141b5836981778b36fe066692153d"></a>

### How would Nemotron Parse crop outputs be merged with the full-page parse, and how would its outputs be stored?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981778b36fe066692153d)

- **Why it matters** — The reference merge can add a crop table beside an overlapping direct table whose text
  differs (U-4). PDF-04 asks to retain candidates and unresolved outcomes, and ADR-0038 allows reconciliation only
  through derived products.
- **Options** — Merge: the reference add-only merge plus guarded replacement, or an exclusive per-crop decision
  (replace, else add, else skip); chart Markdown kept or converted with chart\_render; counters only, or every
  candidate and decision. Storage: a DoclingDocument through parse\_nemotron\_parse\_v3\_5, or raw blocks only; raw
  outputs inline as JSONB or as content-addressed artifacts; separate products with parent references, or a derived
  reconciled document; logprobs not requested, summarized per block, or kept as full token arrays.

#### Detail

Informational material, with no recommendation: [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30) §13.5 and §13.6; the reference merge in [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) §7.7 and §7.8.

#### Sources

- Project file `pdf_pipeline_design/docling_nemotron_triple_pass_reference.md` (31 October 2026).

<a id="notion-40b141b5836981c7a800d0a6ade71d15"></a>

### If a Nemotron Parse pass is added, where is it orchestrated and served?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981c7a800d0a6ade71d15)

- **Why it matters** — The root environment is outside the package's torch and transformers bounds, the vLLM plugin
  loads for every model served from its environment, and behaviour on the RTX 5090 (no FA3 path) and GPU memory
  sharing are unknown (U-1, U-2, U-11).
- **Options** — Orchestration: NVIDIA's reference pipeline as-is in a side environment; an own client in the root
  environment reusing the reference algorithms; Docling's engine abstraction for crops plus
  parse\_nemotron\_parse\_v3\_5; Docling's VlmPipeline preset (single pass only). Serving: a dedicated environment
  at the validated runtime (Python 3.12, vLLM 0.26.0, torch 2.11.0, transformers 5.14.1); shared with the planned
  services/vllm-native (vLLM 0.31, Python 3.14); in-process Transformers in the root environment.

#### Detail

Informational material, with no recommendation: [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30) §13.1, §13.2 and §13.8; runtimes in [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) §4.

#### Sources

- Project file `pdf_pipeline_design/docling_nemotron_triple_pass_reference.md` (31 October 2026).

<a id="notion-40b141b58369814c9afac0c9cf279b12"></a>

### Should a Nemotron Parse triple pass run beside Docling, and for what use?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b58369814c9afac0c9cf279b12)

- **Why it matters** — The repository plan treats Nemotron Parse as an investigative alternative, not a production
  entry. Each use changes something different: derivation kinds and coverage wording, the plan's region-only scope,
  or the rule that native conversion is never replaced.
- **Options** — Uses: evidence only (alignment, diffs, alternatives); gap filling in a derived document (inline
  vector math, chart data); coverage audit (math and tables seen by Nemotron but absent from L0 candidates; needs
  whole pages); replacement of L0 text (excluded by the current plan text). Page scope: every page, or pages and
  regions selected from L0 signals.

#### Detail

Informational material, with no recommendation: [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30) §13.4 and §13.7; constraints in §12.1.

#### Sources

- [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) (project file `pdf_pipeline_design/docling_nemotron_triple_pass_reference.md`, 31 October 2026).

<a id="notion-40b141b5836981c4bce8f69e6d6412ab"></a>

### Should the numeric-reference prototype generate the operating-variable option its decision type names?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L4 Interpretation layer, Current implementation · [Notion record](https://app.notion.com/p/40b141b5836981c4bce8f69e6d6412ab)

- **Why it matters** — The Numeric referent decision type lists its options as the quantities in the preceding
  window, an operating variable and UNKNOWN, and the worked example's tier-3 trace includes an operating variable.
  The prototype's candidate set for "this pressure" holds only the three quantities and UNKNOWN. Candidate recall
  bounds every joint decision: a reference to a variable that is never quantified in the passage ("the suction
  pressure" in general) can only fall to UNKNOWN, and the prototype's 0.94 is measured without that competitor.
- **Options** — 1\. Add an operating-variable candidate from the frame roles of the seed ontology (the governed
  property of the condition), with its own prior. 2. Keep quantities only and treat a variable reading as UNKNOWN,
  then measure how often the 20-document sample needs it. 3. Remove the option from the decision type.
- **Recommendation** — Option 2 first, because it costs nothing and measures the need: count, in the 20-document
  sample, references whose correct reading is a variable rather than a stated quantity. Adopt option 1 if that share
  is material.
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40b141b58369812a9499e96904758d85"></a>

### Tables split across pages become separate TableItems

**Kind** Risk · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369812a9499e96904758d85)

- **Why it matters** — Docling 2.145.0 can turn one logical table that spans several PDF pages into several
  TableItem objects, in both the standard and the VLM pipeline. Each piece is well formed but the continuity is
  lost: headers repeat or go missing, records split at the page break, and continuation rows can be read as header
  rows. Table-to-record assembly (prototype P3, stage 4) reads these tables directly, so a split table yields split
  or mislabelled records.
- **Options** — Wait for the upstream opt-in merging of continued tables (proposal of 17 October 2026 on issue
  #2976; not released in 2.145.0); merge continued tables after conversion, using page adjacency, matching column
  count and widths, and a repeated or missing header; or keep the pieces separate and let table-to-record assembly
  join rows across pieces with the same columns.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

#### Detail

Docling's reading order can merge text elements across a page boundary, but tables stay separate objects. The JSON schema can give one item several provenance regions, but that capability does not mean cross-page reconstruction is performed. The research input lists this as the most important limitation its first overview left out.

#### Evidence

None measured. Reported in the Docling issue tracker for both pipelines.

#### Sources

- [📥 Research input: Docling library overview](https://app.notion.com/p/40b141b5836981899f67f489d4d40da3), gap analysis §9.2.
- [Docling issue #2976](https://github.com/docling-project/docling/issues/2976): split tables and the opt-in merge proposal.

<a id="notion-40b141b583698101b5d1d1017d9ad33f"></a>

### What does the front end do when rendering fails, or when Docling fails or only partly succeeds?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b583698101b5d1d1017d9ad33f)

- **Why it matters** — Every element handed downstream must still carry honest anchors and reliability grades. A
  failure that passes silently would enter calibration as good text.
- **Options** — Mechanisms already in the repository (main at 1513b29): conversion outcome success, partial\_success
  or failure; coverage complete, partial, unknown or unsupported; health kept separate from coverage (ADR-0038);
  each recipe converted in a spawned child that is terminated, joined and killed on cancellation; unresolved inline
  alignments kept without invented offsets; per-formula and per-OCR-region outcomes. Not worked out: what happens
  when rendering fails, and what downstream receives from a partly converted document.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

#### Detail

Discussed on [🚨 Failure handling](https://app.notion.com/p/40b141b583698173977ced93021aac08).

#### Sources

- L0 front-end page: the empty open section "Failure handling (render fails, Docling fails, scanned input)".
- [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) §1.1, §1.2, §12.1.

<a id="notion-40b141b58369817983f3f8f4951684d1"></a>

### What schema holds conversion-time metadata, and how is each item joined to the Docling elements it describes?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b58369817983f3f8f4951684d1)

- **Why it matters** — Framing priors and Claim-pair argument read this metadata. Without a schema and a join to
  elements, revisions, speakers and LaTeX formulas cannot become observations.
- **Options** — Known so far: the keys the retired streams emitted (revision ID, author and time; message ID and
  speaker; formula ID with the LaTeX source), and the element anchor still under discussion (Docling element
  reference + page + bounding box, with offsets inside the element). The metadata is captured while rendering,
  before Docling assigns element references; how each item is joined to elements after conversion is not worked out.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5)

#### Detail

Discussed on [🏷️ Conversion-time metadata](https://app.notion.com/p/40b141b583698146803ed474d531652f). Depends on [What happens to structure that conversion to PDF destroys?](#notion-40a141b5836981de810ef76dc4f8027c) and [What is the primary anchor for a span: canonical-text offsets or Docling element references?](#notion-40a141b5836981778930cbdc26e2b25a).

#### Sources

- L0 front-end page: the empty open section "Conversion-time metadata schema" and the need "Conversion-time metadata keyed to elements".
- [Pipeline streams](https://app.notion.com/p/fbe65140b7ea413a913c2f486b0a224a): Key emitted of the canonical text, revisions, threads and formula streams.

<a id="notion-40b141b5836981f28652df3fd637fcc2"></a>

### Which decoding, inputs and model revision would a Nemotron Parse pass use?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981f28652df3fd637fcc2)

- **Why it matters** — Greedy decoding is repeatable and is the vendor serving contract, but it is not the
  configuration behind the published 75.20 triple-pass score; the sampled configuration matches that score but
  depends on seed and runtime (U-6, U-7).
- **Options** — Decoding: greedy (temperature 0, top\_k 1, repetition penalty 1.1) or the ParseBench sampling
  (temperature 0.2/0.2/0.1, top\_k 50, repetition penalty 1.05/1.05/1.0, fixed seed). Revision: e7ea7924… (Docling
  preset) or e5e0406c… (ParseBench run). Page image: 150 DPI JPEG quality 92, or Docling scale 2.0 PNG with maximum
  side 2048. Crops: cut from the page image, or rendered again from the PDF at higher DPI.

#### Detail

Informational material, with no recommendation: [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30) §13.3 and §13.4; sampling configurations in [🔭 Docling and Nemotron Parse triple-pass reference](https://app.notion.com/p/40b141b58369810a9907f9dbbef94efe) §6.

#### Sources

- Project file `pdf_pipeline_design/docling_nemotron_triple_pass_reference.md` (31 October 2026).

<a id="notion-40b141b5836981c5abbcff950cf9f3c7"></a>

### Which renderer turns each published form into a PDF, and how is its fidelity checked?

**Kind** Question · **Status** Open · **Raised** 2026-11-01 · **Area** L0 Front end · [Notion record](https://app.notion.com/p/40b141b5836981c5abbcff950cf9f3c7)

- **Why it matters** — The renderer decides what Docling can read. Path-drawn glyphs never enter the native text,
  non-embedded fonts render differently per machine (Docling #4995), and a symbol font mapped into the private-use
  area can trigger whole-page OCR that also replaces good prose.
- **Options** — No rendering tool has been named or compared yet. Requirements known from the Docling OCR reference:
  embed every font; keep text as text, not outlines or filled paths; use fonts with correct ToUnicode maps; do not
  rasterise text; leave no hidden text; record the fonts available to the renderer in the input digest. Candidate
  fidelity checks, each with a blind spot: parse\_score, the broken-layer test, unaccounted vector shapes, bitmap
  overlap.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Discussed on [🖨️ Rendering to PDF](https://app.notion.com/p/40b141b583698182b472d79db82e5996). The candidate checks come from the health-signal table on [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15).

#### Sources

- L0 front-end page: Flow, step 3, and the empty open section "Rendering to PDF (tools, fonts, fidelity checks)".
- [🔤 Docling OCR reference](https://app.notion.com/p/40b141b5836981b3a105db8f3d39a4b9) §3.4, §4.4, §5.3–§5.4, §13.1, §16, §18.4.

<a id="notion-40a141b58369811ca1eff277ad4edd45"></a>

### How does the interpretation layer relate to the repository's existing confidence design?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L4 Interpretation layer, Current implementation · [Notion record](https://app.notion.com/p/40a141b58369811ca1eff277ad4edd45)

- **Why it matters** — The repository already has a cold-start noisy-OR and a planned Dawid–Skene model for claim
  confidence (design section D5 §6). Two confidence paths would disagree.
- **Options** — Replace D5 §6 for decision types the layer covers; keep both; or have the layer produce
  interpretation confidence while the Dawid–Skene model supplies source reliability π\_g.
- **Recommendation** — The third option: one path per quantity. Retire the noisy-OR when the first decision type is
  adopted.
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3), [Stage
  7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d),
  [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

<a id="notion-40b141b5836981f4a673f85b47ee66e7"></a>

### How should conformal candidate sets handle shift between document families?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L4 Interpretation layer, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b5836981f4a673f85b47ee66e7)

- **Why it matters** — Split-conformal sets guarantee that the true option is in the candidate set with probability
  at least 1 − α only on exchangeable data. A document family unlike the calibration sample can lose candidate
  recall without any warning, and a solver choosing among incomplete candidates produces a coherent but wrong
  answer.
- **Options** — One split-conformal threshold per decision type over the whole sample; weighted conformal per
  document family; per-family thresholds once each family has enough labels.
- **Affects component** — [Decision registry](interpretation-components.md#notion-40a141b5836981658472ca2c89f9fe3b)

Raised in the 31 October summary of the mathematics as an open mathematical choice: "Conformal under distribution shift between document families: weighted conformal per family?". See [🕸️ Joint model and calibration](https://app.notion.com/p/40b141b583698193ab8fd8313f46b0f5).

<a id="notion-40a141b5836981719278c69d7afb8cfd"></a>

### Is the labelling budget for the stage gates realistic?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** Rollout and evaluation · [Notion record](https://app.notion.com/p/40a141b5836981719278c69d7afb8cfd)

- **Why it matters** — The gates assume about 100 numbers, 50 clusters and 200 sentences per qualifier on the
  20-document sample, plus a passage-sampled recall set. Calibration and conformal sets need these labels.
- **Options** — Keep the budget; halve it and accept wider intervals; or label with the CPU LLM and audit a sample
  by hand.
- **Recommendation** — Keep the budget for stages 2 and 3, where calibration is first fitted; size later gates after
  seeing the bootstrap interval widths.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Blocks stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Evaluation
  harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70), [Calibration
  table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

<a id="notion-40a141b5836981689075d6d5d126d651"></a>

### Should templates use pgmpy or the prototype's own exact solver?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L4 Interpretation layer, Current implementation · [Notion record](https://app.notion.com/p/40a141b5836981689075d6d5d126d651)

- **Why it matters** — The pipeline page names pgmpy; the prototype uses its own exact enumeration over connected
  components with a size budget.
- **Options** — Own solver for all local templates; pgmpy for all; own solver by default with pgmpy junction-tree
  inference only for templates whose components exceed the budget.
- **Recommendation** — Own solver by default: templates are small, the solver is exact and refuses rather than
  approximates, and it already integrates lineage and masking. Bring in pgmpy only when a template needs it.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

<a id="notion-40a141b583698171b1fdd837ef91f2a6"></a>

### What are the value v and error cost c for each record type?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L4 Interpretation layer, Rollout and evaluation · [Notion record](https://app.notion.com/p/40a141b583698171b1fdd837ef91f2a6)

- **Why it matters** — They set every acceptance threshold τ = c / (c + v), so they decide how many records are
  accepted and how many errors are tolerated.
- **Options** — A default of c = 3v (τ = 0.75) for most types; c = 9v (τ = 0.9) for compliance findings and argument
  edges; c = v (τ = 0.5) for internal records such as value roles that only feed later decisions.
- **Recommendation** — Start with those three tiers and enter them in the Decision types register; revisit after the
  first harness run shows precision at τ.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Blocks stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Record-type
  registry](interpretation-components.md#notion-40a141b5836981d98f29c170328a3ace)

<a id="notion-40a141b5836981de810ef76dc4f8027c"></a>

### What happens to structure that conversion to PDF destroys?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L0 Front end, L2 Model streams · [Notion record](https://app.notion.com/p/40a141b5836981de810ef76dc4f8027c)

- **Why it matters** — The Pipeline streams register still lists non-PDF producers for canonical text, revisions and
  annotations, and message threads. Tracked changes, comments, email headers and LaTeX source do not survive
  conversion to PDF.
- **Options** — Drop those streams; capture them as metadata during conversion and attach them to the PDF's
  elements; or keep a second path for sources whose structure matters.
- **Recommendation** — Capture them as metadata during conversion, keyed to the PDF elements they describe, so the
  pipeline stays PDF-only while revisions, speakers and LaTeX formulas remain available as observations.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Blocks stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5)

<a id="notion-40a141b5836981778930cbdc26e2b25a"></a>

### What is the primary anchor for a span: canonical-text offsets or Docling element references?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L0 Front end, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40a141b5836981778930cbdc26e2b25a)

- **Why it matters** — Observation cache keys, lineage variables and every source pointer depend on it, and changing
  it later invalidates every cached observation.
- **Options** — Offsets into one canonical document text; Docling element reference + page + bounding box, with
  offsets inside the element; both, with a stored mapping.
- **Recommendation** — Docling element reference + page + bounding box as the anchor, with offsets inside the
  element text. The canonical text is derived from it, and region re-conversion stays addressable.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Blocks stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5),
  [Lineage layer](interpretation-components.md#notion-40a141b5836981aaaed0e68becf62ffa)

<a id="notion-40a141b5836981238197f12f6cd8dda8"></a>

### What is λ, the CPU-seconds worth one extra correct record?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L4 Interpretation layer, Rollout and evaluation · [Notion record](https://app.notion.com/p/40a141b5836981238197f12f6cd8dda8)

- **Why it matters** — It decides how often targeted extraction, region re-conversion and the CPU LLM run.
- **Options** — Set λ from a corpus-wide CPU budget; or set it per record type; or log EVI without acting until
  stage 5 and choose λ from the logged distribution.
- **Recommendation** — Log EVI from stage 3 onward without acting, then choose λ at stage 5 from the counterfactual
  budget it implies.
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3), [Stage
  9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Blocks stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Affects component** — [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

<a id="notion-40a141b5836981b3aff0f76316a42fda"></a>

### Which Docling signals define the reliability grade q per block?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L0 Front end, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40a141b5836981b3aff0f76316a42fda)

- **Why it matters** — With PDF-only input, q is where shared error enters: every model's LLR is calibrated per
  grade.
- **Options** — Text-layer vs OCR origin; layout-model confidence; table-structure confidence; formula enrichment
  success; the existing text-quality score; combinations of these.
- **Recommendation** — Fit the existing text-quality logistic score with Docling's origin and confidence signals
  added as features, and bucket it into three grades.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Blocks stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d),
  [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5)

<a id="notion-40a141b5836981a68cf6f8e9e81ff8ed"></a>

### Which ontology becomes seed ontology v0, and in what format?

**Kind** Question · **Status** Open · **Raised** 2026-10-31 · **Area** L1 Seed ontology · [Notion record](https://app.notion.com/p/40a141b5836981a68cf6f8e9e81ff8ed)

- **Why it matters** — Unit dimensions, relation signatures and frame roles are compiled into factors from stage 1;
  without them the cross-decision factors have nothing to check against.
- **Options** — An existing domain ontology (for example QUDT for units plus a domain ontology); the repository's
  own model packs; or a hand-built v0 covering the 20-document sample.
- **Recommendation** — QUDT for quantity kinds and units, plus a small hand-built frame set for the sample's record
  types, so stage 2's unit-dimension factor works on day one.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Blocks stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Seed ontology v0](interpretation-components.md#notion-40a141b58369812f9465f7037d397d37)

<a id="notion-40b141b5836981f78050f33342bf74be"></a>

### Bridging and abstract reference are unsolved in general

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981f78050f33342bf74be)

- **Why it matters** — References such as "this pressure" decide which quantity a condition or claim is about.
  Identity coreference models do not resolve them, and the best published bridging result is 28.7 F1 on ISNotes,
  with an LLM.
- **Options** — Leave them unresolved; resolve them on CPU by bounded inference; send them all to the CPU LLM; or
  bounded inference first, with ties sent to the CPU LLM with candidate antecedents and a none option.
- **Recommendation** — Bounded inference first, combining unit dimension, ontology roles, syntax and proximity, as
  in the worked example; what stays tied goes to the CPU LLM with candidate antecedents and a none option. This does
  not solve abstract reference in general.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f), [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

#### Detail

Identity coreference models do not resolve "this pressure", and the best published bridging result is 28.7 F1 on ISNotes, with an LLM. Many numeric and property references can still be resolved on CPU by combining unit dimension, ontology roles, syntax and proximity, as in the worked example ([🔬 Worked example: one passage through the tiers](https://app.notion.com/p/40b141b583698129b75bf8c46cd01965)). What stays tied goes to the CPU LLM with candidate antecedents and a "none" option. This does not solve abstract reference in general.

The routing itself is recorded as a decision from the 30 October audit: see the row on bridging and abstract anaphora.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), "Weak spots the stack already had".

<a id="notion-40b141b583698197a415f16e81d22e39"></a>

### Candidate recall bounds every joint decision

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L4 Interpretation layer, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b583698197a415f16e81d22e39)

- **Why it matters** — Joint inference can only choose among the candidates it is given. A solver choosing among
  incomplete candidates produces a coherent but wrong answer.
- **Options** — Hope candidate generation is complete; or measure candidate recall per decision type and keep an
  unresolved option in every set.
- **Recommendation** — Measure candidate recall per decision type, size candidate sets by split-conformal prediction
  to a stated miss rate, and always include the unresolved option.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3), [Stage
  6](stages.md#notion-40a141b58369817c9929cc494bc2c061)
- **Affects component** — [Decision registry](interpretation-components.md#notion-40a141b5836981658472ca2c89f9fe3b),
  [Evaluation harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70)

#### Detail

Joint inference can only choose among the candidates it is given. Candidate recall is measured per decision type, and the unresolved option is always present. The staged plan turns this into a guarantee with a stated miss rate: for each decision type, a split-conformal threshold sets the candidate-set size so that the true reading is in the set with probability at least $1 - \alpha$ (MAPIE). Pair candidate recall for argument edges is measured on the passage-sampled set, since a missed pair can never be labelled.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp), "Candidate sets sized by conformal prediction"; carried in [🏗️ Built once at stage 1](https://app.notion.com/p/40b141b583698127bfb2c1a9c18e278b).

<a id="notion-40b141b5836981ae9becc156c7c8ccff"></a>

### Conditions rest on thin evidence

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981ae9becc156c7c8ccff)

- **Why it matters** — The only extraction work behind combination 5.3 is Jiang et al. 2019 on fact and condition
  tuples, and no model came out of it, so condition scope has no tested component behind it.
- **Options** — Cue lexicons and parse rules alone (the earlier route); GLiNER2.5 condition-clause labels scoped by
  the Stanza parse, with Dipo links as soft candidates and joint resolution; or the CPU LLM for all conditions.
- **Recommendation** — The audit's route: condition-clause labels scoped by the parse, Dipo links as soft
  candidates, joint resolution as typed decisions, and the CPU LLM only for implicit or still-unresolved conditions.
  Measure on the planned 200-sentence sample.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

#### Detail

The only extraction work behind 5.3 is Jiang et al. 2019 on fact and condition tuples, and no model came out of it. Conditions now come from GLiNER2.5 condition-clause labels ("at", "above", "unless", "provided that") scoped by the Stanza parse, with Dipo condition links as soft candidates. The clause, the proposition it governs and any numeric reference in it are resolved jointly as typed decisions; only implicit or still-unresolved conditions go to the CPU LLM. Measure on the planned 200-sentence sample.

The route itself is recorded as a decision: see the row on the explicit conditions route.

#### Evidence

- [Jiang et al. 2019, fact and condition tuples](https://aclanthology.org/D19-1029/)

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), "Weak spots the stack already had".

<a id="notion-40b141b58369810b888adfe76c50a14b"></a>

### Coreference used as input can hurt relation extraction

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369810b888adfe76c50a14b)

- **Why it matters** — Propagating coreference into relation extraction can lower sentence-level relation accuracy,
  so cross-sentence relations built on clusters may be worse than they look.
- **Options** — Treat cross-sentence relations as facts; or keep them as candidates with confidence.
- **Recommendation** — Cross-sentence relations stay candidates with confidence.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

#### Detail

DyGIE's ablation saw sentence-level relation extraction drop on ACE05 when coreference was propagated, though it helped slightly on SciERC. Cross-sentence relations therefore stay candidates with confidence. DocRED reports that 40.7% of facts need several sentences and 17.6% need coreference, which is why the cross-sentence route is kept at all.

#### Evidence

- [Luan et al. 2019, DyGIE (coreference and relation propagation ablation)](https://arxiv.org/abs/1904.03296)
- [Yao et al. 2019, DocRED](https://arxiv.org/abs/1906.06127)

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".

<a id="notion-40b141b5836981a485f3c5a71d5b0bea"></a>

### CPU throughput of the slow models is untimed

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981a485f3c5a71d5b0bea)

- **Why it matters** — Stanza, Maverick, ReFinED and the CPU LLM claim pass are the slow models on CPU. Stanza and
  Maverick sit on the critical path, and the claim pass is the volume job once enabled. Gating limits the work, but
  none of them has been timed here.
- **Options** — Commit to batch sizes now; or time each model on a representative sample first, with Propositionizer
  (Flan-T5-large, 783M) as the fallback for claims if the CPU LLM cannot keep pace.
- **Recommendation** — Time each on a representative sample before committing to batch sizes. First, on the
  20-document sample: the CPU LLM on claim extraction, a paragraph per call, alongside the non-generative baseline;
  then Stanza and Maverick; then GLiClass against GLiNER2.5 and GLiFormer against the bi-encoder.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

#### Detail

- Stanza, Maverick, ReFinED and the CPU LLM claim pass are the slow models on CPU.
- Stanza and Maverick sit on the critical path, and the claim pass is the volume job once it is enabled. Time the claim pass, a paragraph per call, alongside the non-generative baseline.
- If the claim pass cannot keep pace, the fallback is Propositionizer (Flan-T5-large, 783M), which has weaker evidence and returns no offsets.
- Gating limits the work, but none of these models has been timed here. Time each on a representative sample before committing to batch sizes.

The 30 October audit made this risk larger: with Gemma-APS removed, the CPU LLM (Qwen3.6-35B-A3B, about 3B active parameters per token) now carries atomic claims, the volume job. Reading the prompt is the slow part, so a paragraph is sent per call.

#### What to time first (audit, 30 October 2026)

1. The CPU LLM on claim extraction, a paragraph per call.
2. Stanza and Maverick, which remain on the critical path.
3. GLiClass against GLiNER2.5 for heading classes, and GLiFormer against the bi-encoder for mentions.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, "What to time first".

<a id="notion-40b141b5836981f0b5d8db31b59e34c2"></a>

### Dependent signals make agreement look stronger than it is

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981f0b5d8db31b59e34c2)

- **Why it matters** — Correlated model errors, shared upstream parses and derived rules can make agreement look
  stronger than it is, which inflates confidence and acceptance.
- **Options** — Treat each signal as independent; or record shared provenance and model the dependence.
- **Recommendation** — The observation contract records shared provenance, models from one family form one evidence
  factor, corpus support uses provenance groups with a dependence discount, and the dependence-removed ablation
  measures what that handling is worth.
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5),
  [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d), [Corpus
  support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

#### Detail

Correlated model errors, shared upstream parses and derived rules can make agreement look stronger than it is. The observation contract records shared provenance, and the dependence-removed ablation measures what that handling is worth. If the dependence-removed variant looks better on raw counts but worse on calibration, the difference is overcounting, not synergy.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- Formal treatment: [🕸️ Joint model and calibration](https://app.notion.com/p/40b141b583698193ab8fd8313f46b0f5) and [📚 Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b).

<a id="notion-40b141b583698128b25bd28e87ebf029"></a>

### Does GLiClass large-v3 beat GLiNER2.5 for document type and heading classes?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b583698128b25bd28e87ebf029)

- **Why it matters** — Document and heading classes (reach 72) sit on the critical path: section roles, routing and
  gates all read them.
- **Options** — Keep GLiNER2.5 classification; switch to GLiClass large-v3.
- **Recommendation** — Run both on the 20-document sample before stage 1 is closed.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Audit verdict: keep GLiNER2.5, test GLiClass. GLiClass large-v3 averages 0.72 on a 13-set zero-shot suite vs 0.68 for NLI; GLiNER2.5-Decide reports 60.2 on a different suite. There is no head-to-head comparison, so run both on the 20-document sample; this sits on the critical path.

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, verdict row "Document and heading classes (72)" and "What to time first".
- Smoke test: [🔥 Smoke-test shortlist](https://app.notion.com/p/40b141b5836981089fbecb22686ec543).

<a id="notion-40b141b58369819f852ff683609ed6c1"></a>

### Does GLiFormer large beat the GLiNER bi-encoder for typed mentions?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b58369819f852ff683609ed6c1)

- **Why it matters** — Typed mentions (reach 70) feed the mention inventory that every later tier builds on.
- **Options** — Keep the GLiNER bi-encoder large; switch to GLiFormer large.
- **Recommendation** — Test GLiFormer against the bi-encoder on the 20-document sample.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

#### Detail

Audit verdict: keep GLiNER2.5 and the bi-encoder large, test GLiFormer. The bi-encoder large scores 61.5 on CrossNER, above GPT-4o (59.9). GLiFormer large reports 64.4 (authors, September 2026), a self-reported number not yet compared on this corpus.

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, verdict row "Typed mentions (70)" and "What to time first".

<a id="notion-40b141b58369814aa8ffdf89dedaadda"></a>

### Errors compound along long chains of combinations

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b58369814aa8ffdf89dedaadda)

- **Why it matters** — Most links in the long chains are deterministic joins on IDs, not predictions, but every
  predicted link still adds error, and an error made early reaches every combination built on it.
- **Options** — Trust each tier once it is built; or measure each tier before the next is built on it.
- **Recommendation** — Measure each new tier on a small hand-labelled sample before the next tier is trusted. The
  stage gates and the tests before each stage do this.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3), [Stage
  6](stages.md#notion-40a141b58369817c9929cc494bc2c061), [Stage
  7](stages.md#notion-40a141b58369816a9c70f23c650234aa), [Stage
  8](stages.md#notion-40a141b58369811992a0c8007723a20b), [Stage
  9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Affects component** — [Evaluation harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70)

#### Detail

Most links in the long chains are deterministic joins on IDs, not predictions, but every predicted link still adds error. Each new tier should be measured on a small hand-labelled sample before the next tier is trusted, so errors are caught at the tier that made them.

#### Rationale

Cascading errors in annotation pipelines are a known effect: an error made by an early component is inherited by every later one that reads its output (Finkel, Manning and Ng 2006). The rollout is ordered so that each stage ends with a gate and a hand test before anything is built on it.

#### Evidence

- [Finkel, Manning and Ng 2006, cascading errors in annotation pipelines](https://aclanthology.org/W06-1673/)

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions" (as of 1 November 2026).
- Each stage's gate and test: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448).

<a id="notion-40b141b5836981468d31ce8deb070e18"></a>

### How is the residual correlation ρ between provenance groups set before it is measured?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981468d31ce8deb070e18)

- **Why it matters** — ρ sets the effective number of independent provenance groups, k\_eff = k / (1 + (k − 1)ρ),
  and so the corpus support of every claim. If small changes in ρ flip many acceptances, ρ has to be measured before
  support results are relied on.
- **Options** — Estimate ρ from shared metadata (authors, institutions, datasets, instruments); set a conservative
  fixed ρ until it is measured; report support under a range of ρ.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

From the math formalization (combining evidence across documents) and the staged plan's stage 7 test, sensitivity of accepted support to ρ. See [📚 Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b).

<a id="notion-40b141b5836981509d4de742300851e4"></a>

### Joint inference cost grows with template connectivity

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981509d4de742300851e4)

- **Why it matters** — Junction-tree factors grow with connectivity, so an unbounded template can make exact
  inference too slow for CPU.
- **Options** — Approximate inference; or bounded templates with a size budget and difficulty routing for components
  over budget.
- **Recommendation** — Templates bound their candidate counts, factor sizes are monitored, and components over
  budget go to difficulty routing (9.4).
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

#### Detail

Junction-tree factors grow with connectivity. Templates bound their candidate counts, factor sizes are monitored, and components over budget go to difficulty routing. The prototype's own solver refuses rather than approximates when a component exceeds its budget; whether pgmpy is used instead is a separate open question.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".

<a id="notion-40b141b5836981ac95cfc5113dea92ae"></a>

### Model interfaces the design relies on were checked but not run

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981ac95cfc5113dea92ae)

- **Why it matters** — Stages 3 and 4 depend on ReFinED, Maverick, GLiNER-Relex and LangExtract behaving as their
  code and model cards suggest. If an interface differs, the mention inventory cannot be passed in as designed.
- **Options** — Build on the interfaces as read; or exercise each one on the sample before the stage that depends on
  it.
- **Recommendation** — Exercise each interface on the sample before the stage that depends on it is built.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5)

#### Detail

These interfaces were checked against code and model cards but not run:

- ReFinED's `process_text` takes optional spans, though the README shows only raw text.
- Maverick's predefined-mentions mode clusters only the mentions it is given, so pronouns and noun phrases must be in the set, and its OntoNotes model outputs no singletons.
- GLiNER-Relex takes no given spans, so its output is aligned to the inventory afterwards.
- The CPU LLM's claims and slots are grounded to character offsets by LangExtract; anything it cannot ground is flagged, not stored as a fact. Alignment makes an output inspectable; it does not validate the interpretation.

#### Evidence

- [Maverick coreference (predefined-mentions mode, CPU device)](https://github.com/SapienzaNLP/maverick-coref)
- [ReFinED inference code (process\_text takes optional spans)](https://raw.githubusercontent.com/amazon-science/ReFinED/main/src/refined/inference/processor.py)

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".

<a id="notion-40b141b583698169a15adb7b4d61951d"></a>

### Most combinations are design reasoning, not measured results

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b583698169a15adb7b4d61951d)

- **Why it matters** — The 84 combinations are the design inventory. Only some are backed by published results; the
  rest are hypotheses whose value is not yet shown.
- **Options** — Build all combinations; or test the central hypothesis on three prototypes first and track each
  combination's status.
- **Recommendation** — Combinations backed by published results cite them in the Evidence column; the rest are
  hypotheses to test. The Status column of the combinations register tracks each one, and the three prototypes test
  the central hypothesis first.

#### Detail

Those combinations backed by published results cite them in the Evidence column; the rest are hypotheses to test. The Status column in [Stream combinations](https://app.notion.com/p/42ae10c108cd40bbb39a0660224e1b85) tracks each one (Proposed, Prototyped, Measured, Adopted, Rejected).

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

<a id="notion-40b141b58369815cbd37d4c54d84e020"></a>

### Ontology expectations can coerce readings into existing categories

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L1 Seed ontology, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b58369815cbd37d4c54d84e020)

- **Why it matters** — A wrong or incomplete ontology expectation can force readings into existing categories, so
  novel entities and concepts are mislabelled instead of being flagged.
- **Options** — Treat ontology expectations as hard constraints; or keep soft expectations soft and keep unknown
  options open.
- **Recommendation** — Soft expectations stay soft, unknown options stay open, NIL reasons record new concepts, and
  the stress tests include a plausible but wrong ontology expectation.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  8](stages.md#notion-40a141b58369811992a0c8007723a20b)
- **Affects component** — [Seed ontology v0](interpretation-components.md#notion-40a141b58369812f9465f7037d397d37),
  [Factor-template library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

#### Detail

A wrong or incomplete ontology expectation can force readings into existing categories. Soft expectations stay soft, unknown options stay open, and the stress tests include a plausible but wrong expectation. The evaluation also measures unknown-concept handling, and the ontology-factor ablation shows how much of any gain comes from the ontology.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [🌱 L1 · Seed ontology](https://app.notion.com/p/40b141b5836981b796e0e48ade290791).

<a id="notion-40b141b58369815ca1b7df1b499c9306"></a>

### Qualification is where CPU coverage is partial

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b58369815ca1b7df1b499c9306)

- **Why it matters** — The qualified claim (5.11) is the main user-facing record, and its qualifiers are only partly
  covered by CPU signals: explicit cues work, implicit ones do not.
- **Options** — Trust composition for tier 5; or measure each qualifier before trusting it.
- **Recommendation** — Measure on about 200 hand-labelled sentences per qualifier before trusting tier 5 (the stage
  5 gate).
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

#### Detail

The composition analysis rated most qualifiers partly covered by CPU signals: explicit cues work, implicit ones do not. Tier 5 has no new models (Dipo aside), so its quality rests on the rules and on tiers 2 to 4.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- Dropbox 06 Composing CPU Outputs for LLM-only Capabilities (folder `Corpus_Intelligence_Dropbox`, shared link in the Notion record).

<a id="notion-40b141b58369819b95cce78ba12c6c80"></a>

### Several key models are English-only

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b58369819b95cce78ba12c6c80)

- **Why it matters** — CQE, ReFinED, Maverick's OntoNotes model and the personal-data detectors are English-only, so
  non-English text loses quantities, links, coreference and redaction unless it is translated.
- **Options** — Pivot translation (OPUS-MT) with a word aligner to map offsets back; non-English alternatives where
  they exist (CorPipe for coreference); or leave non-English text with fewer streams.
- **Recommendation** — Language routing from stage 1 decides per unit. Pivot translation adds its own errors and
  needs a word aligner, so measure it before relying on it.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

#### Detail

CQE, ReFinED, Maverick's OntoNotes model and the personal-data detectors are English-only. Pivot translation adds its own errors and needs a word aligner to map offsets back. The coreference stream already names CorPipe for non-English text, and the language stream names OPUS-MT for pivot translation with a word aligner.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- Producers as listed in [Pipeline streams](https://app.notion.com/p/fbe65140b7ea413a913c2f486b0a224a).

<a id="notion-40b141b583698109a3e7f9c102144ec7"></a>

### Should the repository add one bounded M13 → M11 pass that re-resolves ambiguous math spans?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** Current implementation, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b583698109a3e7f9c102144ec7)

- **Why it matters** — The repository's production-efficiency target routes shared context "without downstream M13
  feedback", so M11 parses with constants only and 1,888 spans stay ambiguous between application and product. A
  second task that reads M13's typed symbol table would resolve most of them. The parsing methods review calls it
  the single change with the most leverage on math.
- **Options** — Keep the one-way M11 → M13 order; add one bounded second M11 task over ambiguous spans only, reading
  M13's output, so the execution graph stays acyclic; resolve symbol types inside M11 from local cues only.
- **Recommendation** — The bounded second pass (parsing methods review, brief architecture notes): it is the
  "execution acyclic, beliefs updated both ways" pattern of the interpretation layer. Tracked as Known defects item
  6.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

#### Detail

The parsing methods review of 30 October 2026 (commit 430e026) found that M11 builds its parsing context from macros and constants alone: the declared functions are \{Gamma\} and there are no variables, so admissibility can prune nothing. M13 already finds binding sentences such as "Let p ∈ (0, 1)" and "f is the density of X", but its output never reaches M11.

The review's brief architecture notes propose a second task that reads M13's typed symbol table and re-resolves only the ambiguous spans. The graph stays acyclic, because it is a separate task that reads M13's output.

#### Sources

- [📦 What the repository has today](https://app.notion.com/p/40b141b58369814894d7d932105906bf), section Brief architecture notes.
- [Known defects](https://app.notion.com/p/7024f8a41c094558a455736db7122f55), item 6.
- [Parsing methods review](https://claude.ai/artifact/8si2UMpQ6NF9UKQiRK2Mxe).

<a id="notion-40b141b58369812a9192d57a7cdfd9e3"></a>

### Table statements rest on assembly, not on one model

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** L2 Model streams, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369812a9192d57a7cdfd9e3)

- **Why it matters** — Lookup-and-score works best when cells match the KB. Tables whose column roles stay ambiguous
  fall to the CPU LLM, which is the most expensive action.
- **Options** — Accept the CPU LLM share as it comes; or measure how many tables fall through and improve column
  profiling if the share is large.
- **Recommendation** — Measure how many tables fall to the CPU LLM on the sample, and report complete-record
  correctness for tables at stage 4.
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

#### Detail

Table statements are assembled by lookup and score over Docling cells (column profiling, GLiNER2.5 on header text, CQE and pint on value cells, ReFinED on entity cells), with the CPU LLM only for tables whose role assignment stays ambiguous. Lookup-and-score works best when cells match the KB. Tables whose column roles stay ambiguous fall to the CPU LLM, so measure how many do.

With the PDF-only front end, Docling's TableFormer is the only table source, so the assembly inherits its cell and spanning-header errors.

#### Sources

- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a), section "Risks and open questions".
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), "Filling the gaps the removals leave".

<a id="notion-40b141b5836981dd9419e610b3ae2d27"></a>

### The repository's D4 method cards still describe a GPU stack that differs from the Notion stack

**Kind** Risk · **Status** Open · **Raised** 2026-10-30 · **Area** Current implementation, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981dd9419e610b3ae2d27)

- **Why it matters** — The D4 cards name GPU vLLM with Qwen3.5-9B (M10), Qwen3-Embedding (M04) and spaCy-only
  sentence splitting. The Notion stack is CPU: Qwen3.6-35B-A3B at 4 bits, Jina embeddings, SaT, Stanza and
  GLiNER2.5. Encoder methods built from the cards would implement a stack the design has left.
- **Options** — Update the D4 cards to the Notion stack before phase-1 encoder methods are built; treat Notion as
  the only stack description and mark the D4 cards as superseded.
- **Recommendation** — Reconcile the cards with the Notion stack before the phase-1 encoder methods are built
  (parsing methods review).

#### Detail

The parsing methods review of 30 October 2026 (commit 430e026) lists this as a documentation fix in its brief architecture notes. Since 31 October the target design lives in Notion, so the reconciliation runs from [🧱 Current stack](https://app.notion.com/p/409141b583698149bf98dfca6a0580bb) to the repository's `docs/design/D4-method-catalog.md`.

#### Sources

- [📦 What the repository has today](https://app.notion.com/p/40b141b58369814894d7d932105906bf), section Brief architecture notes.
- [Parsing methods review](https://claude.ai/artifact/8si2UMpQ6NF9UKQiRK2Mxe).

<a id="notion-40b141b583698146965ffce689a21969"></a>

### Which heavier reader re-reads pages that Docling grades low?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** L0 Front end, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b583698146965ffce689a21969)

- **Why it matters** — Docling is the strongest layout parser that runs on CPU, but GPU page parsers lead
  OmniDocBench v1.6 (TeleOCR 96.9, PaddleOCR-VL-1.6 96.3). Pages with a low reliability grade lower every later
  extractor's evidence.
- **Options** — PaddleOCR-VL-1.6 (0.9B) on the RTX 5090 for low-graded pages (the audit's suggestion); TeleOCR
  (1.2B), which leads OmniDocBench v1.6 and has the best table score; the Nemotron Parse pass described on the L0
  pages; region re-conversion with Docling at higher resolution or with OCR forced, chosen by EVI at stage 9; or no
  re-conversion, keeping Docling's output with its low grade.
- **Recommendation** — None yet. The options are informational; the choice waits for the reliability-grade signals
  and the stage 9 escalation costs.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Affects component** — [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

#### Detail

The 30 October audit kept Docling for layout and suggested re-parsing pages Docling grades low with PaddleOCR-VL-1.6 on the 5090. Since then the front end became PDF-only (31 October), the L0 pages describe a Nemotron Parse pass as reference material, and the Stages register lists region re-conversion as a stage 9 escalation action. These are alternatives for the same job; none is chosen. Two things are open: which reader does the re-reading, and which grade triggers it. The second depends on which Docling signals define the reliability grade q. The Nemotron Parse option is worked out in more detail in [Should a Nemotron Parse triple pass run beside Docling, and for what use?](#notion-40b141b58369814c9afac0c9cf279b12), which also covers its other uses.

#### Evidence

- OmniDocBench v1.6: TeleOCR 96.9, PaddleOCR-VL-1.6 96.3; both need a GPU. TeleOCR has the best table score.
- Docling (43M layout model plus TableFormer) is the strongest layout parser that runs on CPU.

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), verdict row "Layout (83)".
- [🔭 Nemotron Parse pass](https://app.notion.com/p/40b141b5836981c9b813f5202cf5dd30); [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15).

<a id="notion-40b141b5836981b1a229c9675d1d9c88"></a>

### Which of the repository's two consolidation and evaluation paths should be retired?

**Kind** Question · **Status** Open · **Raised** 2026-10-30 · **Area** Current implementation, Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b5836981b1a229c9675d1d9c88)

- **Why it matters** — The legacy path (`methods/llm/parse.py` → `consolidate/assemble.py` → `evaluate/align.py`)
  and the semantic path (`semantic/proposals.py` → `semantic/domain_operations.py` →
  `evaluate/semantic_alignment.py`) share the quote cascade and the key functions but have drifted apart: head
  words, coarse evidence and tie handling differ. Golden agreement still runs on the lenient legacy path, so its
  scores do not reflect the semantic path's grounding.
- **Options** — Retire the legacy path and move golden agreement to `semantic_alignment.py`; keep both and exclude
  coarse spans from legacy agreement; retire the semantic path.
- **Recommendation** — Retire the legacy path once golden agreement runs on `semantic_alignment.py` with an IoU
  threshold (Known defects item 14).

#### Detail

The parsing methods review of 30 October 2026 (commit 430e026) lists this as one of two structural changes worth making. Each path has its own label handling: the legacy `consolidate/pass_.py` prefixes the pack's head-word keys and the semantic path does not (Known defects item 1). The legacy aligner keeps coarse fallback spans as evidence and counts any overlap as a match (item 14).

#### Sources

- [📦 What the repository has today](https://app.notion.com/p/40b141b58369814894d7d932105906bf), section Brief architecture notes.
- [Known defects](https://app.notion.com/p/7024f8a41c094558a455736db7122f55), items 1 and 14.
- [Parsing methods review](https://claude.ai/artifact/8si2UMpQ6NF9UKQiRK2Mxe).

<a id="group-decided"></a>

## Decided

<a id="notion-40b141b5836981078629fb91c07c8a34"></a>

### Duplicate, merged into the PDF-only decision row (to be deleted)

**Kind** Decision · **Status** Decided · **Raised** 2026-10-31 · [Notion record](https://app.notion.com/p/40b141b5836981078629fb91c07c8a34)

- **Why it matters** — Merged on 1 November 2026 into the row "Only PDFs enter the pipeline: every source is
  converted to its published form, rendered to PDF and parsed by Docling". Nothing links here any more.
- **Decision** — See the merged row.

This row was merged into [Only PDFs enter the pipeline: every source is converted to its published form, rendered to PDF and parsed by Docling](#notion-40b141b583698124bc73ee1447273e70) on 1 November 2026 and is waiting to be deleted. All of its content and every link to it now live on that row.

<a id="notion-40b141b5836981ac9ebcc4faa4718612"></a>

### Generative calls stay off until the stage-5 baseline is measured

**Kind** Decision · **Status** Decided · **Raised** 2026-10-31 · **Area** Rollout and evaluation, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981ac9ebcc4faa4718612)

- **Why it matters** — The CPU LLM is the most expensive action. Its value can only be judged against a measured
  non-generative baseline, and its own Shapley value shows where it duplicates CPU inference.
- **Options** — Run the CPU LLM from the stage that first uses it; or build its passes but keep them off until the
  stage-5 decomposition is measured, logging their expected value of information meanwhile.
- **Recommendation** — Keep it off until stage 5.
- **Decision** — Staged plan, 31 Oct 2026: the CPU LLM is switched on only after stage 5, as a ninth stream group,
  where expected value of information says it pays. From stage 3 the harness records which decisions would have been
  escalated, giving a counterfactual LLM budget. The stage-4 claim pass is built but stays off, with its EVI logged
  per paragraph. The LLM is kept only for record types where its utility per CPU-second is positive.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f), [Evaluation
  harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70)

#### Detail

- **Stage 3.** The harness records which decisions would have been escalated (their EVI), giving a counterfactual LLM budget before the LLM is switched on.
- **Stage 4.** The claim pass is built but stays off. The harness logs its EVI per paragraph, so its expected contribution is estimated before it costs anything.
- **Stage 5.** With eight stream groups in place, the first full decomposition is computed. Then the CPU LLM is switched on as a ninth group, for the claim pass and for decisions whose EVI exceeds λ times its cost. Its Shapley value and its interaction with each group show where it adds value and where it duplicates CPU inference. Keep it only for the record types where its utility per CPU-second is positive.
- **Stage 9.** The LLM's share of items is reported as an output of the EVI rule, not a target.

#### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp), opening and stages 3 to 5.
- [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448).

<a id="notion-40b141b583698124bc73ee1447273e70"></a>

### Only PDFs enter the pipeline: every source is converted to its published form, rendered to PDF and parsed by Docling

**Kind** Decision · **Status** Decided · **Raised** 2026-10-31 · **Area** L0 Front end, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b583698124bc73ee1447273e70)

- **Why it matters** — One input form gives one parser, one anchor scheme (Docling element reference, page and
  bounding box) and one set of health signals for the reliability grade. Structure a PDF cannot carry (revisions,
  comments, speakers, email headers, LaTeX source) has to be captured at conversion time or it is lost, and the
  non-PDF producers in the stream plan become outdated.
- **Options** — Keep format-specific producers per source type (the earlier stream plan: PyMuPDF, Trafilatura,
  docx2python, mail-parser, pylatexenc and others); or convert every source to its published form, render it to PDF
  and parse only PDFs with Docling.
- **Recommendation** — PDF-only through Docling.
- **Decision** — Paul, 31 Oct 2026: each source is converted to its published form up front (the version a reader
  would see), rendered to PDF, and only PDFs go through Docling. PyMuPDF, Trafilatura, docx2python and the other
  format-specific producers are outdated; what they extracted that a PDF cannot carry moves into conversion-time
  metadata keyed to the PDF's elements.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5),
  [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

#### Detail

The front-end decision. The flow: acquire the source in whatever form it arrives; resolve the published form; render to PDF, capturing anything the PDF will lose as conversion-time metadata; Docling converts the PDF (layout, reading order, TableFormer tables, formula and code enrichment, OCR where there is no text layer); the elements, with anchors, grades and links, go to the streams. The flow and its consequences are on [📄 L0 · Front end: published form to PDF to Docling](https://app.notion.com/p/40a141b58369811b8cd1dc6d9da943b3).

Consequences recorded elsewhere:

- What happens to structure that conversion destroys: [What happens to structure that conversion to PDF destroys?](#notion-40a141b5836981de810ef76dc4f8027c), handled on [🏷️ Conversion-time metadata](https://app.notion.com/p/40b141b583698146803ed474d531652f).
- The primary anchor for a span: [What is the primary anchor for a span: canonical-text offsets or Docling element references?](#notion-40a141b5836981778930cbdc26e2b25a).
- Which Docling signals define the reliability grade: [Which Docling signals define the reliability grade q per block?](#notion-40a141b5836981b3aff0f76316a42fda).
- Each stage's front-end needs: the Front-end impact property of [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448).

This row merges two rows that recorded the same decision in parallel on 1 November 2026.

#### Open questions

- [What happens to structure that conversion to PDF destroys?](#notion-40a141b5836981de810ef76dc4f8027c)

#### Sources

- [📄 L0 · Front end: published form to PDF to Docling](https://app.notion.com/p/40a141b58369811b8cd1dc6d9da943b3), status callout (31 October 2026).

<a id="notion-40a141b583698157bd13c80f5b84f768"></a>

### Should the reference code be merged into the repository now?

**Kind** Decision · **Status** Decided · **Raised** 2026-10-31 · **Area** Current implementation · [Notion record](https://app.notion.com/p/40a141b583698157bd13c80f5b84f768)

- **Why it matters** — The stage-1 machinery and prototype 1 exist as tested code, but the target design is still
  being worked out here.
- **Options** — Merge now; keep on its branch as reference; discard.
- **Recommendation** — Keep on its branch as reference.
- **Decision** — Paul, 31 Oct 2026: detail the design in Notion rather than stage it as a pull request. The code
  stays on branch claude/project-thread-dvf80m, unmerged, and the pull request is closed.
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

<a id="notion-40b141b58369818197e0e54f372130e1"></a>

### An interpretation layer chooses readings: observation contract, candidate sets with an unresolved option, bounded joint inference, coherent record assignment

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b58369818197e0e54f372130e1)

- **Why it matters** — Combining outputs without an explicit layer for choosing among interpretations lets a solver
  pick a coherent but wrong reading, and leaves confidence and revision undefined.
- **Options** — Join model outputs directly into records; or add an interpretation layer between the streams and the
  records.
- **Recommendation** — Add the layer, built once at stage 1.
- **Decision** — Interpretation-layer review, 30 Oct 2026: an interpretation layer with an observation contract,
  candidate sets with an unresolved option, bounded joint inference and coherent record assignment. Its components
  are built at stage 1.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5),
  [Decision registry](interpretation-components.md#notion-40a141b5836981658472ca2c89f9fe3b), [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f), [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

#### Detail

The review kept the source-addressed observations, qualified claims, explicit combinations and the recognition of fallibility, and strengthened how the system chooses and revises interpretations. The layer's parts are the rows of [Interpretation components](https://app.notion.com/p/b1966ebe48c6421f8ba6dc3d6446d431); its contracts are on [📜 Principles and contracts](https://app.notion.com/p/40b141b58369813f919ef8685c7ede69).

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).
- [🏗️ Built once at stage 1](https://app.notion.com/p/40b141b583698127bfb2c1a9c18e278b).

<a id="notion-40b141b5836981c2a8e4d69055783b23"></a>

### Atomic claims: Gemma-APS removed, replaced by the CPU LLM claim pass through LangExtract

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981c2a8e4d69055783b23)

- **Why it matters** — Gemma-APS has no independent result. Small LLMs collapse on decomposition (Llama-3.2-3B
  scores 24% completeness on Claim2Atom), and Gemma-APS returns no offsets.
- **Options** — Keep Gemma-APS 2B at 4-bit; or give claims to the stack's CPU LLM; fallback Propositionizer
  (Flan-T5-large, 783M) if the LLM cannot keep pace.
- **Recommendation** — Give claims to the CPU LLM, and time it first.
- **Decision** — Performance audit, 30 Oct 2026: Gemma-APS removed. Qwen3.6-35B-A3B with Claimify-style prompts
  through LangExtract extracts atomic claims, under the same gate (English, non-duplicate, non-reference,
  claim-bearing sentences), a paragraph per call. LangExtract returns character offsets, so the realignment step
  goes away. Per-token cost is similar (about 3B active vs about 2.5B dense). Fallback if too slow: Propositionizer.
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Atomic claims (P7) | Gemma-APS | Qwen3.6-35B-A3B with Claimify-style prompts through LangExtract, under the same gate (English, non-duplicate, non-reference, claim-bearing sentences) | Qwen3-32B scores 95.7% completeness and 94.8% correctness on Claim2Atom; models of Gemma-APS's size collapse. LangExtract returns character offsets, so the realignment step goes away | Similar per token (about 3B active vs about 2.5B dense). Reading the prompt is the slow part, so send a paragraph per call |

The cost of this change is that the CPU LLM now carries atomic claims, which is the volume job. In the staged rollout the claim pass is built at stage 4 but stays switched off until the stage-5 baseline is measured.

#### Evidence

- [Gemma-APS model card](https://huggingface.co/google/gemma-2b-aps-it).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026.
- Related risk: [CPU throughput of the slow models is untimed](#notion-40b141b5836981a485f3c5a71d5b0bea).

<a id="notion-40b141b5836981ed83b0c876eff6dc0e"></a>

### Bridging and abstract anaphora go to the CPU LLM with candidate antecedents and a none option

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981ed83b0c876eff6dc0e)

- **Why it matters** — Maverick, an identity coreference model, does not resolve bridging or abstract anaphora such
  as "this pressure". The best published result is 28.7 resolution F1 on ISNotes, with an LLM.
- **Options** — Leave them to Maverick; or route the unresolved ones to the CPU LLM with candidates.
- **Recommendation** — Route unresolved ones to the CPU LLM after bounded inference on CPU.
- **Decision** — Performance audit, 30 Oct 2026: unresolved definite noun phrases and "this/that + noun" go to the
  CPU LLM with candidate antecedents and a "none" option, after the stage-5 numeric reference template has tried
  unit dimension, ontology roles, syntax and proximity.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f)

#### Detail

| Capability | Current route | Problem | Change |
| --- | --- | --- | --- |
| Bridging and abstract anaphora ("this pressure") | Maverick | Identity coreference models do not resolve these. The best published result is 28.7 resolution F1 on ISNotes, with an LLM | Send unresolved definite noun phrases and "this/that + noun" to the LLM with candidate antecedents and a "none" option, as the page's own example already flags |

The remaining risk is recorded separately: [Bridging and abstract reference are unsolved in general](#notion-40b141b5836981f78050f33342bf74be). The worked example: [🔬 Worked example: one passage through the tiers](https://app.notion.com/p/40b141b583698129b75bf8c46cd01965).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, "Weak spots the stack already had".

<a id="notion-40b141b5836981bd8742d2195fc16a53"></a>

### Claim embeddings come after the qualified claim

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b5836981bd8742d2195fc16a53)

- **Why it matters** — Embedding claims before qualification makes "X is safe" and "X is not safe under load" look
  alike, so equivalence, contradiction and topics would be computed on unqualified text.
- **Options** — Embed claims as extracted; or embed the qualified claim.
- **Recommendation** — Embed the qualified claim.
- **Decision** — Pre-publication review, 30 Oct 2026: claim embeddings (Jina embeddings v5 small) are computed over
  qualified claims, after tier 5, and feed the tier-7 corpus combinations.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

#### Sources

- Review note callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a).
- Stream row: Claim embeddings in [Pipeline streams](https://app.notion.com/p/fbe65140b7ea413a913c2f486b0a224a).

<a id="notion-40b141b5836981d8b9d7fd804422ee76"></a>

### Complete cache keys and targeted re-extraction

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981d8b9d7fd804422ee76)

- **Why it matters** — Masking layers for measurement and re-running after a change are only cheap and correct if
  each observation is keyed by everything that produced it.
- **Options** — Key observations by input and model only; or key them by the full configuration and re-extract only
  what a change affects.
- **Recommendation** — Full configuration keys.
- **Decision** — Interpretation-layer review, 30 Oct 2026: every observation is cached under a complete key (model
  version and full configuration hash: labels, ontology version, supplied mentions, context, preprocessing), and
  re-extraction is targeted at what a change invalidates.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Affects component** — [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5),
  [Lineage layer](interpretation-components.md#notion-40a141b5836981aaaed0e68becf62ffa)

#### Detail

Caching by full configuration makes masking and re-runs cheap; provenance tags make dependence visible. With the PDF-only front end, the input digest is the PDF digest plus the Docling version and configuration hash. Lineage polynomials give exact invalidation: setting a variable to 0 removes everything that depended on it.

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).
- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp), "Built once, at stage 1".

<a id="notion-40b141b5836981e79451c3f99f579a63"></a>

### Concept vs named entity: CNER removed, replaced by the GLiNER bi-encoder with concept labels and a parse genericity flag

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981e79451c3f99f579a63)

- **Why it matters** — CNER has no result outside its own dataset: one DeBERTa-base with a fixed label set, trained
  on Wikipedia. The concept stream (reach 71) feeds terms and the mention inventory.
- **Options** — Keep CNER; or recombine models already in the stack.
- **Recommendation** — Recombine: the bi-encoder is the best measured zero-shot NER, and parse features alone carry
  genericity.
- **Decision** — Performance audit, 30 Oct 2026: CNER removed. The GLiNER bi-encoder with kind-denoting label
  descriptions, plus a genericity flag from the Stanza parse (bare plural or generic determiner, present tense),
  decides concept vs named entity. The type-agreement check becomes GLiNER2.5 vs the bi-encoder. No CPU cost is
  added: one extra label set on a pass that already runs.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Concept vs named entity (R2) | CNER | GLiNER bi-encoder with kind-denoting label descriptions, plus a genericity flag from the Stanza parse (bare plural or generic determiner, present tense). The type-agreement check becomes GLiNER2.5 vs the bi-encoder | The bi-encoder is the best measured zero-shot NER (61.5 CrossNER); parse features alone give 77.4% on genericity vs a 50.4% baseline (Friedrich and Pinkal 2015). CNER has no comparison at all | None added: one extra label set on a pass that already runs |

#### Evidence

- Bi-encoder large: 61.5 on CrossNER, above GPT-4o (59.9).
- Genericity from parse features: 77.4% vs a 50.4% baseline ([Friedrich and Pinkal 2015](https://www.coli.uni-saarland.de/projects/sitent/files/slides_acl2015.pdf)).
- [CNER model card](https://huggingface.co/Babelscape/cner-base).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, "Verdict on each model stream" and "Filling the gaps the removals leave".
- Stream row: Concept vs named-entity mentions in [Pipeline streams](https://app.notion.com/p/fbe65140b7ea413a913c2f486b0a224a).

<a id="notion-40b141b58369813196e2f5470bb81336"></a>

### Conditions get an explicit route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit conditions

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b58369813196e2f5470bb81336)

- **Why it matters** — Conditions feed the qualified claim (5.11). The earlier route (cue lexicons and parse rules,
  Dipo across sentences) rested on Jiang et al. 2019 alone, which produced no model.
- **Options** — Cue lexicons and parse rules; or span labels for condition clauses scoped by the parse, with Dipo
  and the CPU LLM as support.
- **Recommendation** — Span labels scoped by the parse, measured on the 200-sentence sample.
- **Decision** — Performance audit, 30 Oct 2026: GLiNER2.5 span labels for condition clauses ("at", "above",
  "unless", "provided that"), scoped by the Stanza parse; Dipo condition links as candidates; the CPU LLM for
  implicit conditions. Measured on the planned 200-sentence sample.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f)

#### Detail

| Capability | Current route | Problem | Change |
| --- | --- | --- | --- |
| Conditions (tier 5, feeding the qualified claim 5.11) | Cue lexicons and parse rules; Dipo across sentences | The only extraction work is Jiang et al. 2019 on fact and condition tuples, and no model came out of it | GLiNER2.5 span labels for condition clauses ("at", "above", "unless", "provided that"), scoped by the Stanza parse; Dipo condition links as candidates; the LLM for implicit conditions. Measure on the planned 200-sentence sample |

In the interpretation layer the clause, the proposition it governs and any numeric reference in it are resolved jointly as typed decisions (the stage-5 condition scope template). The remaining risk is recorded separately: [Conditions rest on thin evidence](#notion-40b141b5836981ae9becc156c7c8ccff).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, "Weak spots the stack already had".

<a id="notion-40b141b5836981e899b6c8c6b9745fd5"></a>

### Entity links carry NIL reasons, and instances are distinguished from classes

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b5836981e899b6c8c6b9745fd5)

- **Why it matters** — A bare NIL hides why a mention has no KB entry, and treating "centrifugal pump" and P-101
  alike forces classes and instances into one category.
- **Options** — A bare NIL and one entity type; or NIL with a reason and an instance vs class decision.
- **Recommendation** — NIL reasons and the instance-type distinction.
- **Decision** — Interpretation-layer review, 30 Oct 2026: every NIL link carries a reason (local entity,
  insufficient context, retrieval failure, ambiguity, new concept), and instance vs class is its own decision. Only
  local entities and new concepts reach tier 8.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

#### Detail

At stage 3, the entity link per cluster carries a NIL reason, and the instance-vs-class decision is coupled to class through a factor: "centrifugal pump" can be a class while P-101 is an instance of it. NIL-reason accuracy is measured at stage 3, and NIL rate by reason is part of its gate.

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).

<a id="notion-40b141b58369818b95bad9d7d9ee34b7"></a>

### Hard gates are limited to precise signals

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b58369818b95bad9d7d9ee34b7)

- **Why it matters** — A gate removes work from every later model, so an imprecise gate silently drops correct
  material that nothing downstream can recover.
- **Options** — Gate on any useful signal; or gate only where precision on the sample clears a high threshold, and
  use everything else as a prior.
- **Recommendation** — Gate only on precise signals.
- **Decision** — Pre-publication review, 30 Oct 2026: gates are limited to precise signals (language, duplicates,
  block type, reference lists). The staged plan makes this a threshold: a hard gate is allowed only where its
  precision on the sample clears τ\_gate; everything else enters later factors as a prior.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

#### Detail

Gating the CPU LLM on precise earlier outputs (language, duplicates, block type, reference lists) saves the most compute. Each hard gate must meet τ\_gate before stage 2 begins.

#### Sources

- Review note callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a).
- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp), stage 1.

<a id="notion-40b141b5836981648cb3d3ec67923e27"></a>

### NLI is a feature for argument relations, not their definition

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b5836981648cb3d3ec67923e27)

- **Why it matters** — Entailment and argumentative support are different relations. Using the NLI label as the
  support label mislabels edges.
- **Options** — Use the NLI label as support or attack; or use calibrated NLI scores as evidence alongside
  discourse, proximity and qualifier consistency.
- **Recommendation** — Calibrated NLI scores as evidence.
- **Decision** — Interpretation-layer review, 30 Oct 2026: NLI entail and contradict scores enter argument decisions
  as calibrated evidence, not as the label itself. Support and entailment remain different variables.
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

#### Detail

At stage 6 the factors are NLI entail and contradict scores as calibrated evidence, a Dipo-link prior, proximity, and consistency with the claims' polarity and attribution from stage 5. If the interaction index of NLI with discourse and proximity is near zero, the NLI pass is dropped for this decision.

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).

<a id="notion-40b141b58369814fab5de71fe2849af1"></a>

### Provenance groups replace assumed independence in corpus support (7.5)

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369814fab5de71fe2849af1)

- **Why it matters** — Copied reports and repeated citations are not independent confirmations; counting them as
  such manufactures support.
- **Options** — Count statements as independent; or group them by provenance and discount for dependence.
- **Recommendation** — Provenance groups with a dependence discount.
- **Decision** — Interpretation-layer review, 30 Oct 2026: corpus support groups statements into provenance groups
  by citation roots and shared metadata and combines them with a dependence discount, instead of assuming
  independence.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

#### Detail

At stage 7, statements are grouped into provenance groups by citation roots and shared metadata, combined with the mixture per group $\Lambda_g = \pi_g r_g + (1 - \pi_g)$ and the effective count $k_{\text{eff}} = k / (1 + (k - 1)\rho)$. How ρ is set before it is measured is open: [How is the residual correlation ρ between provenance groups set before it is measured?](#notion-40b141b5836981468d31ce8deb070e18).

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).
- [📚 Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b).

<a id="notion-40b141b583698117a17df93f2f9e56ae"></a>

### ReFinED and Maverick receive the mention inventory, with pronouns and noun phrases added for coreference

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b583698117a17df93f2f9e56ae)

- **Why it matters** — Running each model on raw text produces mentions that do not line up with the stage-2
  inventory, so identity cannot be joined on mention keys.
- **Options** — Let ReFinED and Maverick detect their own mentions; or give both the mention inventory.
- **Recommendation** — Give both the inventory.
- **Decision** — Pre-publication review, 30 Oct 2026: ReFinED and Maverick now receive the mention inventory.
  Pronouns and noun phrases are added to the set for coreference, because Maverick's predefined-mentions mode
  clusters only the mentions it is given. ReFinED keeps its own detection as a recall pass.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

#### Detail

One of the changes from the independent review before publication, which checked model interfaces against code and model cards, the dependency logic and the cited numbers. The interfaces were read, not run: [Model interfaces the design relies on were checked but not run](#notion-40b141b5836981ac95cfc5113dea92ae).

#### Sources

- Review note callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a); the change log: [🗒️ Change log](https://app.notion.com/p/40b141b58369813aa60dd91a5eca8773).

<a id="notion-40b141b58369814ea375fd1c47b4c271"></a>

### Sense discrimination defaults to one sense per term per corpus

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369814ea375fd1c47b4c271)

- **Why it matters** — The earlier fix for 7.12 (clustering embeddings into senses, in place of Word Sense Linking)
  makes results worse: embedding clustering scores 71 to 72 and GPT-4o 66.9, against 73.6 for the
  one-sense-per-lemma baseline. The sense inventory (7.12) feeds terminology and the unit and symbol conflict
  checks.
- **Options** — Cluster embeddings into senses by default (the earlier replacement for Word Sense Linking, which
  needs a GPU); or default to one sense per term and split only on evidence.
- **Recommendation** — Default to one sense per term per corpus: no unsupervised method beats that baseline.
- **Decision** — Performance audit, 30 Oct 2026: default to one sense per term per corpus. Split only when clusters
  are well separated and a definition in the corpus supports the split; the CPU LLM confirms.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

#### Detail

| Capability | Current route | Problem | Change |
| --- | --- | --- | --- |
| Sense discrimination (7.12, replacing Word Sense Linking) | Clustering embeddings into senses | No unsupervised method beats one sense per lemma: clustering scores 71–72 and GPT-4o 66.9, against 73.6 for the baseline (Mosolova et al. 2026). Clustering by default makes results worse | Default to one sense per term per corpus. Split only when clusters are well separated and a definition in the corpus supports the split; the LLM confirms |

Word Sense Linking dropped out earlier because it needs a GPU. Its replacement, clustering by default, is what this decision changes.

#### Evidence

- [Word sense induction in the LLM era (2026)](https://arxiv.org/pdf/2603.11686v1.pdf): BERT-large substitute clustering 71.0, embedding clustering about 71 to 72, GPT-4o 66.9 and Llama 3.3 70B 64.2; none beats the one-sense baseline (73.6).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026, "Weak spots the stack already had" and "The revised set by build stage" (stage 7).
- Combination 7.12 Sense inventory in [Stream combinations](https://app.notion.com/p/42ae10c108cd40bbb39a0660224e1b85).

<a id="notion-40b141b58369814ea368f4dead11a360"></a>

### Seven combinations were added in the pre-publication review

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b58369814ea368f4dead11a360)

- **Why it matters** — These combinations answer corpus-level and consistency questions that no earlier combination
  covered.
- **Options** — Keep the inventory as drafted; or add the seven combinations.
- **Recommendation** — Add them.
- **Decision** — Pre-publication review, 30 Oct 2026: seven combinations added. Tier 7: corpus citation graph (7.2),
  cited-claim faithfulness (7.7), edition differences at claim level (7.8), cross-document events and entity
  timelines (7.9), requirement-measurement compliance (7.16). Tier 8: generic-to-instance consistency (8.4). Tier 2:
  implicit sections (2.10).
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865), [Stage
  7](stages.md#notion-40a141b58369816a9c70f23c650234aa), [Stage
  8](stages.md#notion-40a141b58369811992a0c8007723a20b)

#### Detail

The combinations are rows of [Stream combinations](https://app.notion.com/p/42ae10c108cd40bbb39a0660224e1b85); each tier page lists its own.

#### Sources

- Review note callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a).

<a id="notion-40b141b5836981aa9727cad3f5af39a9"></a>

### Stanza replaces UDPipe 2 for parsing on CPU

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981aa9727cad3f5af39a9)

- **Why it matters** — The parse (reach 73) feeds attachment, genericity, condition scope and cue scope. UDPipe 2's
  accuracy needs a GPU.
- **Options** — UDPipe 2; or Stanza on CPU, converted to spaCy Docs.
- **Recommendation** — Stanza on CPU.
- **Decision** — Pre-publication review, 30 Oct 2026: Stanza replaces UDPipe 2 on CPU, converted to spaCy Docs; the
  UDPipe 2 server is used only if it proves fast enough on CPU. The 30 Oct audit kept it: 86.8 LAS on English EWT,
  the most accurate UD parser fast enough for CPU (UDPipe 2's 89.9 needs a GPU). It runs in pretokenized mode on
  math blocks so formulas stay one token.
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

#### Detail

Stanza remains on the critical path and is one of the models to time first.

#### Sources

- Review note callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a).
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), verdict row "Parse (73)".

<a id="notion-40b141b5836981629293c7552893c629"></a>

### Support and attack: ARI RoBERTa removed, replaced by NLI pair scores, Dipo priorities and the CPU LLM on top pairs

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b5836981629293c7552893c629)

- **Why it matters** — ARI RoBERTa reaches 0.70 macro-F1 only inside its own debate data, and prompted LLMs
  significantly beat RoBERTa baselines on support and attack.
- **Options** — Keep ARI RoBERTa; or recombine NLI, discourse links and the CPU LLM.
- **Recommendation** — Recombine: NLI already runs, and the LLM sees only a filtered set.
- **Decision** — Performance audit, 30 Oct 2026: ARI RoBERTa removed. DeBERTa NLI scores on claim pairs (entail as
  support, contradict as attack), prioritised by Dipo links, with the CPU LLM labelling the top pairs. NLI scores
  are calibrated features, not the definition of support.
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Support and attack (A3) | ARI RoBERTa | DeBERTa NLI scores on claim pairs (entail as support, contradict as attack), prioritised by Dipo links; the CPU LLM labels the top pairs | Prompted LLMs beat RoBERTa baselines significantly (Gorur et al., COLING 2025); gpt-oss-120b reaches 82.1% zero-shot on UKP vs 57.7 F1 for a fine-tuned BERT | NLI already runs; the LLM sees a filtered set |

#### Evidence

- [ARI RoBERTa model card](https://huggingface.co/raruidol/ArgumentMining-EN-ARI-AIF-RoBERTa_L).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026.

<a id="notion-40b141b583698137b899ddfa3e8cdc47"></a>

### Table statements: TableLlama removed, replaced by lookup-and-score table assembly

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams, L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b583698137b899ddfa3e8cdc47)

- **Why it matters** — TableLlama's 94.4 is TURL column typing inside TURL's label set. It emits no cell assertions,
  units or notes, and a 7B dense model at 4-bit is the slowest model in phase B.
- **Options** — Keep TableLlama 7B at 4-bit; or assemble statements from Docling cells and models already in the
  stack.
- **Recommendation** — Assemble: lookup-and-score systems won SemTab 2020, and the assembly produces what tier 4
  needs.
- **Decision** — Performance audit, 30 Oct 2026: TableLlama removed. Lookup-and-score assembly over Docling cells
  produces table statements, with the CPU LLM only for tables whose column roles stay ambiguous. This removes the
  slowest phase-B model.
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Table statements (P6) | TableLlama | Lookup-and-score assembly over Docling cells (steps below), LLM only for ambiguous column roles | Lookup-and-score systems won SemTab 2020, and LLM plus KG retrieval leads SemTab 2025 cell linking. It also produces what tier 4 needs (units, notes, row entity), which TURL typing does not | Removes the slowest phase-B model |

Table statements, step by step:

1. **Structure.** Docling cells give header rows and spans. Rules bind units found in headers or cells and note markers to their cells.
2. **Column roles.** A column profile (numeric share, uniqueness, unit consistency) separates key, measure and dimension columns. GLiNER2.5 classifies header text against the schema's attribute types.
3. **Values and entities.** CQE and pint read value cells. ReFinED links entity cells, using the column's type as a prior.
4. **Statements.** Each cell becomes (row entity, column attribute, value, unit, notes), with its cell as the source span.
5. **Residue.** Only tables whose role assignment stays ambiguous go to the CPU LLM.

#### Evidence

- [TableLlama model card](https://huggingface.co/osunlp/TableLlama).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026.
- Related risk: [Table statements rest on assembly, not on one model](#notion-40b141b58369812a9192d57a7cdfd9e3).

<a id="notion-40b141b583698114a698ce768680c79b"></a>

### Template slots: NuExtract3 folded into the CPU LLM

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L2 Model streams · [Notion record](https://app.notion.com/p/40b141b583698114a698ce768680c79b)

- **Why it matters** — NuExtract3 4B at 4-bit is a second generative model competing for the same 16 cores and RAM.
  Independently it scores below GPT-OSS-120B, and it was never compared with Qwen3.6-35B-A3B.
- **Options** — Keep NuExtract3 as a separate slot filler; or use the CPU LLM with the record schema.
- **Recommendation** — One generative model to batch, cache and calibrate instead of two.
- **Decision** — Performance audit, 30 Oct 2026: NuExtract3 folded into the CPU LLM. The same CPU LLM fills template
  slots with the record schema through LangExtract, on retrieved passages only. This frees the RAM and cores
  NuExtract3 held. NuExtract3 comes back only if it wins on slot accuracy per second in the smoke test.
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Template slots (F) | NuExtract3 | The same CPU LLM with the record schema, through LangExtract | One generative model to batch, cache and calibrate instead of two | Frees the RAM and cores NuExtract3 held |

The net effect of the audit: 26 models become 20, and four generative models (Gemma-APS, TableLlama, NuExtract3 and the CPU LLM) become one.

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026.
- Smoke test: [🔥 Smoke-test shortlist](https://app.notion.com/p/40b141b5836981089fbecb22686ec543).

<a id="notion-40b141b5836981679924dd95780edee3"></a>

### Text quality: ocr-error-detection removed, replaced by a feature-based quality score

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L0 Front end, L2 Model streams · [Notion record](https://app.notion.com/p/40b141b5836981679924dd95780edee3)

- **Why it matters** — ocr-error-detection has no published evaluation. The quality grade conditions every later
  evidence factor through calibration per reliability grade.
- **Options** — Keep ocr-error-detection; or fit a calibrated score on labelled blocks.
- **Recommendation** — Fit a calibrated score: no validated model exists for this anywhere, so a calibrated score
  beats an unevaluated one.
- **Decision** — Performance audit, 30 Oct 2026: ocr-error-detection removed. A per-block logistic score over
  replacement-character and (cid:N) rates, glyph-to-Unicode failures, alphabetic ratio, dictionary-hit rate, GlotLID
  confidence and Docling's parse score, fitted on about 200 labelled blocks. CPU cost is negligible.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Affects component** — [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

#### Detail

| Gap (capability) | Removed | Replacement combination | Why it performs better | CPU cost |
| --- | --- | --- | --- | --- |
| Text quality (S3) | ocr-error-detection | Per-block logistic score over U+FFFD and (cid:N) rate, glyph-to-Unicode failures, alphabetic ratio, dictionary-hit rate, GlotLID confidence and Docling's parse score, fitted on about 200 labelled blocks | No validated model exists for this anywhere, so a calibrated score beats an unevaluated one | Negligible |

**With the PDF-only front end (31 October 2026).** The audit named PyMuPDF as the source of glyph-to-Unicode failures. PyMuPDF is outdated now that Docling is the only parser; these features come from Docling's per-page and per-element health signals instead (parse score, OCR share and confidence, layout score). Which signals define the grade is an open question: [Which Docling signals define the reliability grade q per block?](#notion-40a141b5836981b3aff0f76316a42fda).

#### Sources

- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk), 30 October 2026.
- [🩺 Docling configuration and health signals](https://app.notion.com/p/40b141b5836981b9b9bcc79b4053ff15).

<a id="notion-40b141b5836981de9fddceb169da1e9a"></a>

### The central hypothesis is tested first on three prototypes with generative calls disabled, against six baselines

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** Rollout and evaluation · [Notion record](https://app.notion.com/p/40b141b5836981de9fddceb169da1e9a)

- **Why it matters** — Without a non-generative baseline and fixed comparisons, a gain from combining outputs cannot
  be told apart from a gain from exposing more candidates or from the LLM.
- **Options** — Build all 84 combinations and judge the result; or test the hypothesis first on three prototypes
  with baselines and an evaluation plan.
- **Recommendation** — Three prototypes with generative calls disabled.
- **Decision** — Interpretation-layer review, 30 Oct 2026: three prototypes (quantities and references; joint
  identity, type and relation; tables to records), each compared with six baselines in end-to-end and
  fixed-candidate modes, with generative calls disabled. In the staged plan prototype 2 spans stages 3 and 4,
  prototype 3 sits at stage 4 and prototype 1 completes at stage 5.
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839), [Stage
  4](stages.md#notion-40a141b5836981c1b905ff7cee627528), [Stage
  5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Affects component** — [Evaluation harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70)

#### Detail

The prototypes, baselines, comparison modes, measurement targets and sampling rules are carried on [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026), and its section "Prototypes and evaluation".
- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp).

<a id="notion-40b141b5836981fcb557f44444ff4419"></a>

### The eight hard capability families get structured routes before generation

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L3 Tiers and combinations · [Notion record](https://app.notion.com/p/40b141b5836981fcb557f44444ff4419)

- **Why it matters** — The composition analysis judged eight capability families unlikely to be covered without
  generation. That is too broad for the framework's own output definitions: a structured record does not need a
  fluent rewritten sentence.
- **Options** — Send these families to the CPU LLM; or give each a bounded structured route first, with the LLM
  composing only what remains.
- **Recommendation** — Structured routes first, as proposed subsets to test.
- **Decision** — Interpretation-layer review, 30 Oct 2026: each of the eight families gets a bounded structured
  route first; the CPU LLM (9.6) composes only what remains. These are proposed subsets to test, not claims that the
  families are solved.
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

#### Detail

The routes are on [🧮 Non-generative routes for the hard capability families](https://app.notion.com/p/40b141b583698127b9a1f535a32f0a29).

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).

<a id="notion-40b141b5836981bb9b40e96dbe01c03e"></a>

### The qualified claim carries four separate kinds of confidence

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981bb9b40e96dbe01c03e)

- **Why it matters** — A single confidence number mixes what the author asserted, how sure the system is of its
  reading, how reliable the source is and how much the corpus agrees, so none of them can be acted on.
- **Options** — One confidence score; or four separate quantities.
- **Recommendation** — Four separate quantities.
- **Decision** — Interpretation-layer review, 30 Oct 2026: four kinds of confidence on the qualified claim. Author
  modality is a decision variable read from the source; interpretation confidence is the posterior marginal from the
  joint model; source reliability comes from the stage-1 grade and the evidence basis; corpus support is filled at
  stage 7.
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3), [Stage
  7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839),
  [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

#### Detail

- Author modality is a decision variable, read from the source.
- Interpretation confidence is the posterior marginal from the joint model.
- Source reliability comes from stage 1's grade and the evidence basis.
- Corpus support is left empty until stage 7.

All four are assigned at stage 5, except corpus support, which stage 7 fills.

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026).
- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp), stage 5.

<a id="notion-40b141b5836981cfb1fef9641df32bed"></a>

### The versioned seed ontology is an input from tier 1; tier 8 only proposes reviewed changes

**Kind** Decision · **Status** Decided · **Raised** 2026-10-30 · **Area** L1 Seed ontology, L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981cfb1fef9641df32bed)

- **Why it matters** — If the ontology were only induced at tier 8, no earlier interpretation could condition on
  unit dimensions, relation signatures or frame roles, and induced content could confirm itself.
- **Options** — Induce the ontology at tier 8 from the extractions; or supply a versioned seed ontology v0 from tier
  1 and limit tier 8 to reviewed proposals.
- **Recommendation** — Seed ontology v0 from tier 1.
- **Decision** — Interpretation-layer review, 30 Oct 2026: the versioned seed ontology is an input from tier 1. Tier
  8 is limited to scored proposals that review accepts into the next version; nothing induced is used as accepted
  knowledge before that.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  8](stages.md#notion-40a141b58369811992a0c8007723a20b)
- **Affects component** — [Seed ontology v0](interpretation-components.md#notion-40a141b58369812f9465f7037d397d37)

#### Detail

The seed ontology v0 holds accepted concepts, entities, hierarchy, relation signatures, frame roles and unit dimensions. Interpretation conditions on it from the first stage; tier 8 can later only propose a v1. Accepting a proposal changes the ontology version in every affected cache key, and the effect of v1 is measured on held-out documents that did not contribute to the proposals.

Which ontology becomes v0 is open: [Which ontology becomes seed ontology v0, and in what format?](#notion-40a141b5836981a68cf6f8e9e81ff8ed).

#### Sources

- Interpretation-layer review callout on [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a) (30 October 2026); the change log: [🗒️ Change log](https://app.notion.com/p/40b141b58369813aa60dd91a5eca8773).
- [🌱 L1 · Seed ontology](https://app.notion.com/p/40b141b5836981b796e0e48ade290791).

<a id="group-deferred"></a>

## Deferred

<a id="notion-40a141b5836981d498a6c47dc7105a8a"></a>

### When does a shared-error model (Pyro) earn its place?

**Kind** Question · **Status** Deferred · **Raised** 2026-10-31 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40a141b5836981d498a6c47dc7105a8a)

- **Why it matters** — Calibration per reliability grade handles shared error cheaply; a full model is only worth it
  if errors stay correlated after that.
- **Options** — Add at stage 1; add when stage 1 data shows extractor accuracy varying jointly with q beyond what
  per-grade calibration absorbs; never.
- **Recommendation** — Decide from stage 1 data.
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d), [Stage
  7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Calibration table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d)

<a id="notion-40b141b5836981fe87ddf60ddd1995e2"></a>

### Which method handles corpus-level coupling: probabilistic soft logic or Markov logic?

**Kind** Question · **Status** Deferred · **Raised** 2026-10-30 · **Area** L4 Interpretation layer · [Notion record](https://app.notion.com/p/40b141b5836981fe87ddf60ddd1995e2)

- **Why it matters** — Claim groups and type consistency across documents produce millions of groundings, far beyond
  exact local templates. The choice fixes how weighted ontology rules are applied across the corpus.
- **Options** — Probabilistic soft logic (convex MAP over hinge-loss potentials); Markov logic with approximate
  inference.
- **Recommendation** — Probabilistic soft logic, as in the math formalization's scale table and adoption step 7, and
  only after the local templates are measured.
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Affects component** — [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f), [Corpus
  support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)

Deferred until corpus-level coupling is scheduled (adoption step 7, "Only then scale up"). See [🕸️ Joint model and calibration](https://app.notion.com/p/40b141b583698193ab8fd8313f46b0f5) and [📐 Mathematical foundations](https://app.notion.com/p/40a141b5836981798d81c84a75d61194).
