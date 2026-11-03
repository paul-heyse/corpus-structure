# Pipeline streams

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/fbe65140b7ea413a913c2f486b0a224a?pvs=204) · [First production milestone](../first-production-milestone.md)

The stream IDs and run waves describe the earlier full-stack capability map. Audit verdicts apply to the choices as
recorded. A Removed verdict can describe a replaced producer on a row whose producer and change fields now describe
the replacement. Performance evidence refers to the cited measurements in the source. Corpus performance remains
unmeasured in this snapshot.

[Build stage 1 Addressing and framing (12)](#group-build-stage-1-addressing-and-framing) · [Build stage 2 Span inventory (8)](#group-build-stage-2-span-inventory) · [Build stage 3 Identity (3)](#group-build-stage-3-identity) · [Build stage 4 Propositions (4)](#group-build-stage-4-propositions) · [Build stage 5 Qualification (1)](#group-build-stage-5-qualification) · [Build stage 6 Discourse and argument (1)](#group-build-stage-6-discourse-and-argument) · [Build stage 7 Corpus (6)](#group-build-stage-7-corpus) · [Build stage 8 Ontology (1)](#group-build-stage-8-ontology) · [Build stage 9 Records and control (3)](#group-build-stage-9-records-and-control)

<a id="group-build-stage-1-addressing-and-framing"></a>

## Build stage 1 Addressing and framing

<a id="notion-409141b58369818a84addd332566fbb1"></a>

### Canonical text and offset map (canon)

**Verdict** Outdated by PDF-only front end · **Run wave** 0 · **CPU cost** Very low · **Licence** AGPL (PyMuPDF) · [Notion record](https://app.notion.com/p/409141b58369818a84addd332566fbb1)

- **Producer** — PyMuPDF; Trafilatura, docx2python, mail-parser, pylatexenc; ftfy and ICU
- **Key emitted** — Character offset, mapped to page, box and font
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
  PyMuPDF held up on performance before the PDF-only front end.
- **Change** — Since 31 Oct 2026 only PDFs enter the pipeline, through Docling, so Docling's converted document
  supplies text, layout and offsets. PyMuPDF and the format parsers (Trafilatura, docx2python, mail-parser,
  pylatexenc) are outdated as producers. The stream itself stays, because every join depends on its offsets. Still
  open: what PDFs lose (design question 'What happens to structure that conversion to PDF destroys?') and whether
  the primary anchor is canonical-text offsets or Docling element references.
- **Reach** — 84
- **Models conditioned** — 29
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [PyMuPDF (+ PyMuPDF4LLM, PyMuPDF-Layout)](https://app.notion.com/p/409141b58369811e87eada86fca8f045),
  [Trafilatura](https://app.notion.com/p/409141b58369812aab02fcf875da745f)
- **Capabilities** — [S1](https://app.notion.com/p/409141b5836981c4b411db5c99c866ad),
  [S8](https://app.notion.com/p/409141b5836981f398ddd96402481d6e)
- **Used by** — [1.2](stream-combinations.md#notion-409141b5836981f888d4df9c58419c9a),
  [1.3](stream-combinations.md#notion-409141b583698102ac89ed4c7f82ea8a),
  [1.7](stream-combinations.md#notion-409141b58369810e838eefea6cb5ef86)

<a id="notion-409141b583698151b511eec44610bd65"></a>

### Blocks, reading order, section tree, lists (layout)

**Verdict** Keep with change · **Run wave** 0 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698151b511eec44610bd65)

- **Producer** — Docling
- **Key emitted** — Block ID, section path
- **Performance evidence** — The strongest layout parser that runs on CPU. GPU page parsers lead OmniDocBench v1.6
  (TeleOCR 96.9, PaddleOCR-VL-1.6 96.3).
- **Change** — Re-parse pages Docling grades low with PaddleOCR-VL-1.6 on the RTX 5090 (the region re-conversion
  escalation on L0). Under the PDF-only front end Docling is the only converter, so it also takes over text and
  offsets from the outdated format parsers.
- **Reach** — 83
- **Models conditioned** — 32
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [Docling](https://app.notion.com/p/409141b5836981aa9889c7f3107ce7d9)
- **Capabilities** — [D1](https://app.notion.com/p/409141b58369819e8fe8f425e791fe81),
  [D2](https://app.notion.com/p/409141b5836981079d46d62b1b716ffb),
  [D4](https://app.notion.com/p/409141b5836981cb8947c4e965fc4130),
  [S2](https://app.notion.com/p/409141b5836981e38c73ee6e3e42b0d2)
- **Used by** — [1.1](stream-combinations.md#notion-409141b58369811d8402c5783b88a812),
  [1.2](stream-combinations.md#notion-409141b5836981f888d4df9c58419c9a),
  [1.3](stream-combinations.md#notion-409141b583698102ac89ed4c7f82ea8a),
  [1.4](stream-combinations.md#notion-409141b58369816b8a55d644257d2e23),
  [1.6](stream-combinations.md#notion-409141b5836981ef9825f3632387207c),
  [2.3](stream-combinations.md#notion-409141b58369815fac36e5072a1d652d),
  [3.7](stream-combinations.md#notion-409141b583698138a0dcedcd6df44e85),
  [5.7](stream-combinations.md#notion-409141b5836981cbaebef8203488d6ba),
  [6.3](stream-combinations.md#notion-409141b58369816abbbffc5a400dc4c1)

<a id="notion-409141b58369818f9d2ffe8a835017b2"></a>

### Revisions and annotations (revs)

**Verdict** Outdated by PDF-only front end · **Run wave** 0 · **CPU cost** Very low · **Licence** GPL (pandoc) · [Notion record](https://app.notion.com/p/409141b58369818f9d2ffe8a835017b2)

- **Producer** — pandoc (as a separate program), docx-revisions, pdfannots
- **Key emitted** — Revision ID, author, time
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — Tracked changes, comments and annotations do not survive rendering to PDF, so pandoc, docx-revisions
  and pdfannots no longer see them. They would have to be captured as conversion-time metadata before rendering. The
  design question on what PDFs lose ('What happens to structure that conversion to PDF destroys?') is still open.
  Its reach (76) comes mostly through reference time and edition lineage.
- **Reach** — 76
- **Models conditioned** — 20
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [Pandoc](https://app.notion.com/p/409141b58369817abe70e3d6830c3fce)
- **Capabilities** — [D13](https://app.notion.com/p/409141b58369815c8487e76b7239fcc9)
- **Used by** — [1.7](stream-combinations.md#notion-409141b58369810e838eefea6cb5ef86),
  [1.8](stream-combinations.md#notion-409141b58369816b8ce0fb40bdc774ac)

<a id="notion-409141b5836981c79610f5ea4b9d5130"></a>

### Metadata, citations, references, notes, cross-references (sci)

**Verdict** Keep · **Run wave** 0 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981c79610f5ea4b9d5130)

- **Producer** — GROBID (CRF mode)
- **Key emitted** — Reference ID, citation marker, DOI
- **Performance evidence** — About 86 F1 on PMC reference parsing; leads a 2026 citation-string benchmark, 0.856 vs
  0.748 for the best open LLM.
- **Change** — No change.
- **Reach** — 82
- **Models conditioned** — 24
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [GROBID](https://app.notion.com/p/409141b583698190bc2af5b875e6ebd7)
- **Capabilities** — [D8](https://app.notion.com/p/409141b5836981a1abd3fd86fee705aa),
  [D9](https://app.notion.com/p/409141b5836981788a4aebe4fc1a5a28),
  [D10](https://app.notion.com/p/409141b5836981539d11daa4246b656b),
  [D11](https://app.notion.com/p/409141b583698134945ac85c9cf52751)
- **Used by** — [1.1](stream-combinations.md#notion-409141b58369811d8402c5783b88a812),
  [1.4](stream-combinations.md#notion-409141b58369816b8a55d644257d2e23),
  [1.7](stream-combinations.md#notion-409141b58369810e838eefea6cb5ef86),
  [1.5](stream-combinations.md#notion-409141b5836981499080ff4fc4c8a20e),
  [1.6](stream-combinations.md#notion-409141b5836981ef9825f3632387207c),
  [1.8](stream-combinations.md#notion-409141b58369816b8ce0fb40bdc774ac),
  [7.2](stream-combinations.md#notion-409141b5836981ee83cbe564b02d71a9)

<a id="notion-409141b5836981eb92d9d7bb774895d8"></a>

### Messages, turns and speakers (threads)

**Verdict** Outdated by PDF-only front end · **Run wave** 0 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981eb92d9d7bb774895d8)

- **Producer** — mail-parser, quotequail
- **Key emitted** — Message ID, speaker
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — Emails are rendered to PDF before they enter the pipeline, so mail-parser and quotequail no longer
  see the source. Message IDs, speakers and quoted turns would have to be captured as conversion-time metadata
  before rendering. The design question on what PDFs lose ('What happens to structure that conversion to PDF
  destroys?') is still open. Its reach (76) comes mostly through reference time and edition lineage.
- **Reach** — 76
- **Models conditioned** — 20
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [mail-parser](https://app.notion.com/p/409141b583698164ba61f13f71a14c0d)
- **Capabilities** — [D12](https://app.notion.com/p/409141b583698198a3f7d9308562626a)
- **Used by** — [1.7](stream-combinations.md#notion-409141b58369810e838eefea6cb5ef86),
  [5.6](stream-combinations.md#notion-409141b5836981168731d030ef9a6660),
  [6.5](stream-combinations.md#notion-409141b58369816f966ce592ba2c3432),
  [6.6](stream-combinations.md#notion-409141b5836981adacd1d08814bff80e)

<a id="notion-409141b5836981f59f41c0ed9052e70b"></a>

### Duplicate and near-duplicate signatures (dedup)

**Verdict** Keep · **Run wave** 1 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981f59f41c0ed9052e70b)

- **Producer** — Exact block hashes; datasketch MinHash, SemHash
- **Key emitted** — Block hash, duplicate-cluster ID
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 74
- **Models conditioned** — 20
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [datasketch (MinHash, LSH, LSH Ensemble,
  HNSW)](https://app.notion.com/p/409141b5836981b1bceacb2f82d64c5a)
- **Capabilities** — [C7](https://app.notion.com/p/409141b58369814fac13f8ed210aa394)
- **Used by** — [1.8](stream-combinations.md#notion-409141b58369816b8ce0fb40bdc774ac)

<a id="notion-409141b583698127815fd85f864c0fdd"></a>

### Formula expression trees (formula)

**Verdict** Keep with change · **Run wave** 1 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698127815fd85f864c0fdd)

- **Producer** — LaTeX source, or Docling formula enrichment for PDFs; parsed with pylatexenc and SymPy
- **Key emitted** — Formula ID, symbol tokens
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — The LaTeX-source route is outdated by the PDF-only front end: formulas now come from Docling formula
  enrichment, parsed with pylatexenc and SymPy. Inline mathematics drawn as paths needs region re-conversion (L0,
  Docling configuration and health signals). The design question on what PDFs lose, source LaTeX included, is still
  open.
- **Reach** — 53
- **Models conditioned** — 6
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [SymPy](https://app.notion.com/p/409141b583698187b8d0e024df5a3a7b)
- **Capabilities** — [S7](https://app.notion.com/p/409141b583698128bb2ffc02dadbca4b)
- **Used by** — [1.6](stream-combinations.md#notion-409141b5836981ef9825f3632387207c),
  [2.6](stream-combinations.md#notion-409141b583698165b5cccc4da90536ef),
  [4.8](stream-combinations.md#notion-409141b583698120b69fe73e93207120)

<a id="notion-409141b5836981599a32fb76e77c07a7"></a>

### Text-quality grade per block (quality)

**Verdict** Removed · **Run wave** 1 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981599a32fb76e77c07a7)

- **Producer** — Per-block logistic score over replacement-character and (cid:N) rates, glyph-to-Unicode failures,
  alphabetic and dictionary-hit rates, GlotLID confidence and Docling's parse score, fitted on about 200 labelled
  blocks. Replaced ocr-error-detection on 30 Oct 2026 (no published evaluation)
- **Key emitted** — Quality score per block
- **Performance evidence** — ocr-error-detection: no published evaluation. No validated model exists for this task,
  so a calibrated score beats an unevaluated one.
- **Change** — ocr-error-detection removed by the audit. This row now describes its replacement: a per-block
  logistic score over U+FFFD and (cid:N) rates, glyph-to-Unicode failures, alphabetic ratio, dictionary-hit rate,
  GlotLID confidence and Docling's parse score, fitted on about 200 labelled blocks, at negligible CPU cost. Its
  features overlap with Docling's health signals and the reliability grade q on L0 (design question 'Which Docling
  signals define the reliability grade q per block?').
- **Reach** — 4
- **Models conditioned** — 1
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [Docling](https://app.notion.com/p/409141b5836981aa9889c7f3107ce7d9)
- **Capabilities** — [S3](https://app.notion.com/p/409141b5836981859f8ec1e6560411c9)
- **Used by** — [1.2](stream-combinations.md#notion-409141b5836981f888d4df9c58419c9a)

<a id="notion-409141b5836981658aa5f249c86d3e7a"></a>

### Sentences and paragraph breaks (sents)

**Verdict** Keep with change · **Run wave** 1 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981658aa5f249c86d3e7a)

- **Producer** — Segment any Text (SaT, small); blocks with inline math go to spaCy with each formula kept as one
  token (1.00 vs 0.80 boundary F1 on math-dense pages, repo method M03)
- **Key emitted** — Sentence ID, newline probability
- **Performance evidence** — 97.4 vs 92.9 for spaCy's sentencizer on English. On math-dense text, raw-text splitting
  scored 0.80 boundary F1 against 1.00 for spaCy with each formula as one token (repo spike S1, method M03).
- **Change** — Route blocks with inline math to spaCy with each formula kept as one token. Already reflected in
  Producer.
- **Reach** — 81
- **Models conditioned** — 27
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [Segment any Text (SaT) / wtpsplit](https://app.notion.com/p/409141b5836981ba9bf1e717c4f4cb03)
- **Capabilities** — [S5](https://app.notion.com/p/409141b5836981b59cc3dcabeecc8e53)
- **Used by** — [1.1](stream-combinations.md#notion-409141b58369811d8402c5783b88a812),
  [1.3](stream-combinations.md#notion-409141b583698102ac89ed4c7f82ea8a),
  [2.10](stream-combinations.md#notion-409141b5836981e7a84bc95247b126b1)

<a id="notion-409141b583698117b2e1c0b7067f2537"></a>

### Table structure and cells (tables)

**Verdict** Keep · **Run wave** 1 · **CPU cost** Medium · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698117b2e1c0b7067f2537)

- **Producer** — Docling TableFormer
- **Key emitted** — Table ID, cell (row, column)
- **Performance evidence** — Runs on CPU; TeleOCR has the best table score but needs a GPU.
- **Change** — No change.
- **Reach** — 50
- **Models conditioned** — 6
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [Docling](https://app.notion.com/p/409141b5836981aa9889c7f3107ce7d9)
- **Capabilities** — [D5](https://app.notion.com/p/409141b583698180823bc130b7481b69),
  [D6](https://app.notion.com/p/409141b5836981e0b5b0c1d5a20b79fd)
- **Used by** — [1.6](stream-combinations.md#notion-409141b5836981ef9825f3632387207c),
  [2.3](stream-combinations.md#notion-409141b58369815fac36e5072a1d652d)

<a id="notion-409141b5836981ab9afaeb69b5d5ae32"></a>

### Language and script per unit (lang)

**Verdict** Keep · **Run wave** 2 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981ab9afaeb69b5d5ae32)

- **Producer** — GlotLID; OPUS-MT for pivot translation, with a word aligner to map offsets back
- **Key emitted** — Language tag per block and sentence
- **Performance evidence** — 98.3 F1 on FLORES+ (third-party test, on clean single-language text).
- **Change** — No change.
- **Reach** — 78
- **Models conditioned** — 22
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [GlotLID](https://app.notion.com/p/409141b583698137aac4f126e8bdcd92)
- **Capabilities** — [S4](https://app.notion.com/p/409141b5836981acad4fc8ebb5b6b8d2)
- **Used by** — [1.1](stream-combinations.md#notion-409141b58369811d8402c5783b88a812)

<a id="notion-409141b58369818abe2beb2ce219c7f8"></a>

### Document type and heading classes (genre)

**Verdict** Keep with change · **Run wave** 4 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369818abe2beb2ce219c7f8)

- **Producer** — GLiNER2.5 classification over title, headings and first paragraphs
- **Key emitted** — Document-type label, heading class
- **Performance evidence** — GLiClass large-v3 averages 0.72 on a 13-set zero-shot suite vs 0.68 for NLI;
  GLiNER2.5-Decide reports 60.2 on a different suite. No head-to-head comparison.
- **Change** — Run GLiClass and GLiNER2.5 on the 20-document sample; this stream sits on the critical path.
- **Reach** — 72
- **Models conditioned** — 12
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)
- **Models** — [GLiNER2 / GLiNER2.5 (incl. Decide)](https://app.notion.com/p/409141b5836981f3b0baf8df94dc1ea1)
- **Capabilities** — [C1](https://app.notion.com/p/409141b583698172a2d2e7f5e171e34b)
- **Used by** — [1.4](stream-combinations.md#notion-409141b58369816b8a55d644257d2e23),
  [1.9](stream-combinations.md#notion-409141b5836981369becef06b4f81df0)

<a id="group-build-stage-2-span-inventory"></a>

## Build stage 2 Span inventory

<a id="notion-409141b583698146b66fc2dbbaf22d8e"></a>

### Abbreviation pairs (abbr)

**Verdict** Keep · **Run wave** 3 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698146b66fc2dbbaf22d8e)

- **Producer** — Schwartz-Hearst algorithm (scispaCy abbreviation detector)
- **Key emitted** — Short-form and long-form spans
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 23
- **Models conditioned** — 1
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [scispaCy](https://app.notion.com/p/409141b5836981bd9459da37813762a3)
- **Capabilities** — [T2](https://app.notion.com/p/409141b583698161bfe9f830e081d2d5)
- **Used by** — [2.4](stream-combinations.md#notion-409141b5836981ba9b2ceeaddeb4d553)

<a id="notion-409141b58369810cb26dc09c30bf542d"></a>

### Concept vs named-entity mentions (concepts)

**Verdict** Removed · **Run wave** 4 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369810cb26dc09c30bf542d)

- **Producer** — GLiNER bi-encoder large with concept label descriptions (on the routed GLiNER pass), plus a
  genericity flag from the Stanza parse (bare plural or generic determiner, present tense). Replaced CNER on 30 Oct
  2026: 61.5 on CrossNER vs no published comparison for CNER
- **Key emitted** — Mention span, concept or named entity
- **Performance evidence** — CNER: no result outside its own dataset (one DeBERTa-base with a fixed label set,
  trained on Wikipedia). Replacement: the bi-encoder is the best measured zero-shot NER (61.5 on CrossNER); parse
  features alone give 77.4% on genericity vs a 50.4% baseline (Friedrich and Pinkal 2015).
- **Change** — CNER removed by the audit. This row now describes its replacement: the GLiNER bi-encoder with
  kind-denoting concept label descriptions, plus a genericity flag from the Stanza parse (bare plural or generic
  determiner, present tense). The type-agreement check becomes GLiNER2.5 against the bi-encoder. No CPU cost added:
  one extra label set on a pass that already runs.
- **Reach** — 71
- **Models conditioned** — 10
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [GLiNER bi-encoder v2.0](https://app.notion.com/p/409141b58369817da32fc0f3d8b9539d),
  [Stanza](https://app.notion.com/p/409141b5836981189dfdd5d472f11aaa)
- **Capabilities** — [R2](https://app.notion.com/p/409141b58369816683cadcff6514d2cd)
- **Used by** — [2.4](stream-combinations.md#notion-409141b5836981ba9b2ceeaddeb4d553),
  [2.1](stream-combinations.md#notion-409141b5836981e88660f3eede7253ac)

<a id="notion-409141b5836981308366f134d0ab9373"></a>

### Tokens, lemmas, morphology, dependencies (parse)

**Verdict** Keep with change · **Run wave** 4 · **CPU cost** Medium to high · **Licence** Apache (Stanza); CC BY-NC-SA if UDPipe 2 is used · [Notion record](https://app.notion.com/p/409141b5836981308366f134d0ab9373)

- **Producer** — Stanza on CPU, converted to spaCy Docs; UDPipe 2 server only if it proves fast enough on CPU
- **Key emitted** — Token ID, dependency head
- **Performance evidence** — 86.8 LAS on English EWT; the most accurate UD parser fast enough for CPU (UDPipe 2's
  89.9 needs a GPU).
- **Change** — Run in pretokenized mode on math blocks so formulas stay one token. Time it on the 20-document
  sample: it is on the critical path.
- **Reach** — 73
- **Models conditioned** — 12
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [Stanza](https://app.notion.com/p/409141b5836981189dfdd5d472f11aaa),
  [spaCy](https://app.notion.com/p/409141b5836981959fb2ffd3b5262758)
- **Capabilities** — [S6](https://app.notion.com/p/409141b5836981b9a23adc33ac665d54)
- **Used by** — [2.4](stream-combinations.md#notion-409141b5836981ba9b2ceeaddeb4d553),
  [2.7](stream-combinations.md#notion-409141b5836981debac4faa03c10afea),
  [2.1](stream-combinations.md#notion-409141b5836981e88660f3eede7253ac),
  [2.5](stream-combinations.md#notion-409141b58369813fb393ea90313ceb6a),
  [2.10](stream-combinations.md#notion-409141b5836981e7a84bc95247b126b1),
  [2.2](stream-combinations.md#notion-409141b5836981fc9364f2874585b571),
  [2.6](stream-combinations.md#notion-409141b583698165b5cccc4da90536ef),
  [4.6](stream-combinations.md#notion-409141b5836981d0804fc95ca5a45fb1),
  [5.4](stream-combinations.md#notion-409141b58369810ebfe5fc4145cd7165),
  [8.2](stream-combinations.md#notion-409141b583698116887fda3ca1c5566d),
  [6.4](stream-combinations.md#notion-409141b5836981558823e904a87ca9c6)

<a id="notion-409141b5836981faace1e30da5b9f38d"></a>

### Personal-data spans (pii)

**Verdict** Keep · **Run wave** 4 · **CPU cost** Low to medium · **Licence** NVIDIA licence (commercial use allowed) · [Notion record](https://app.notion.com/p/409141b5836981faace1e30da5b9f38d)

- **Producer** — OpenAI Privacy Filter, NVIDIA GLiNER-PII, Presidio
- **Key emitted** — Span, personal-data category
- **Performance evidence** — Privacy Filter 0.96 F1 on its own set but 0.46 on medical PII in a third-party test;
  GLiNER-PII adds 55+ categories.
- **Change** — No change. Run only if the documents hold personal data.
- **Reach** — 2
- **Models conditioned** — 0
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [OpenAI Privacy Filter](https://app.notion.com/p/409141b5836981868cb9e33b6a6c93bb), [NVIDIA
  GLiNER-PII](https://app.notion.com/p/409141b583698126a670dfd2f2481dca), [Presidio
  (Analyzer/Anonymizer)](https://app.notion.com/p/409141b5836981a69dabc207e5152bf0)
- **Capabilities** — [C6](https://app.notion.com/p/409141b5836981968e81f9b88dd95f9a)
- **Used by** — [2.8](stream-combinations.md#notion-409141b5836981f4b896cf86b4998700)

<a id="notion-409141b5836981d08cb6c348f47e1b8c"></a>

### Quantities, dates and units, normalized (quant)

**Verdict** Keep · **Run wave** 4 · **CPU cost** Low · **Licence** GPL (CQE) · [Notion record](https://app.notion.com/p/409141b5836981d08cb6c348f47e1b8c)

- **Producer** — CQE (English only; returns the noun phrase each quantity refers to); Duckling, dateparser, pint,
  text2num
- **Key emitted** — Value span, referred noun phrase, canonical value and unit
- **Performance evidence** — CQE 85.6 value-and-unit F1 on NewsQuant vs 47.2 for quantulum3 and 59.1 for few-shot
  GPT-3.
- **Change** — No change.
- **Reach** — 58
- **Models conditioned** — 7
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [CQE (Comprehensive Quantity Extractor)](https://app.notion.com/p/409141b583698141aeedfc48eb2f5347),
  [Duckling](https://app.notion.com/p/409141b58369812c8089d21211e9a118),
  [Pint](https://app.notion.com/p/409141b583698170975fe6bd2fd8939f)
- **Capabilities** — [R3](https://app.notion.com/p/409141b58369813d818fc8e002d6a442),
  [R4](https://app.notion.com/p/409141b583698149be23e0bc40fbe5d8)
- **Used by** — [2.9](stream-combinations.md#notion-409141b5836981e6a150e244f5f25270),
  [2.2](stream-combinations.md#notion-409141b5836981fc9364f2874585b571),
  [2.3](stream-combinations.md#notion-409141b58369815fac36e5072a1d652d),
  [2.6](stream-combinations.md#notion-409141b583698165b5cccc4da90536ef),
  [4.8](stream-combinations.md#notion-409141b583698120b69fe73e93207120)

<a id="notion-409141b5836981e5b923f097afd80915"></a>

### Cue lexicons (lex)

**Verdict** Keep with change · **Run wave** 5 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981e5b923f097afd80915)

- **Producer** — Curated hedge, reporting-verb, condition, deontic, negation and comparison lists, matched over the
  parse
- **Key emitted** — Cue span and cue type
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
  For conditions, the only extraction work is Jiang et al. 2019 on fact and condition tuples, and no model came out
  of it.
- **Change** — Conditions no longer rest on cue lexicons and parse rules alone: GLiNER2.5 condition-clause labels
  ('at', 'above', 'unless', 'provided that'), scoped by the Stanza parse, with Dipo condition links as candidates
  and the CPU LLM for implicit conditions. Measure on the planned 200-sentence sample.
- **Reach** — 42
- **Models conditioned** — 5
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [negspacy (NegEx for spaCy)](https://app.notion.com/p/409141b5836981939f0bc3729010ba40)
- **Capabilities** — [Q1](https://app.notion.com/p/409141b583698194993dd77b74775d61),
  [Q2](https://app.notion.com/p/409141b5836981d7be63ef3a60e8ae83),
  [Q3](https://app.notion.com/p/409141b58369812587aac5b34007bf93),
  [Q4](https://app.notion.com/p/409141b5836981659c0ac394c1f4c79c),
  [Q7](https://app.notion.com/p/409141b5836981daa6bcd1bd76fbd6be)
- **Used by** — [2.7](stream-combinations.md#notion-409141b5836981debac4faa03c10afea)

<a id="notion-409141b5836981ff9c1cd5300743d087"></a>

### Term candidates (terms)

**Verdict** Keep · **Run wave** 5 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981ff9c1cd5300743d087)

- **Producer** — GLiNER term labels, KeyBERT, noun chunks from the parse
- **Key emitted** — Term span, termhood score
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 23
- **Models conditioned** — 1
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [GLiNER2 / GLiNER2.5 (incl. Decide)](https://app.notion.com/p/409141b5836981f3b0baf8df94dc1ea1),
  [KeyBERT (incl. KeyLLM)](https://app.notion.com/p/409141b5836981499315d934c84345fb)
- **Capabilities** — [T1](https://app.notion.com/p/409141b5836981bf86bcec3dce4cafa8)
- **Used by** — [2.4](stream-combinations.md#notion-409141b5836981ba9b2ceeaddeb4d553)

<a id="notion-409141b5836981269418d6ef5cf167c8"></a>

### Typed mentions and labels (ents)

**Verdict** Keep with change · **Run wave** 7 · **CPU cost** Medium · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981269418d6ef5cf167c8)

- **Producer** — GLiNER2.5 base and GLiNER bi-encoder large
- **Key emitted** — Mention span, type
- **Performance evidence** — Bi-encoder large 61.5 on CrossNER, above GPT-4o (59.9). GLiFormer large reports 64.4
  (authors, Sep 2026).
- **Change** — Test GLiFormer against the bi-encoder. The routed pass gains concept labels and condition-clause
  labels (the conditions route).
- **Reach** — 70
- **Models conditioned** — 10
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)
- **Models** — [GLiNER2 / GLiNER2.5 (incl. Decide)](https://app.notion.com/p/409141b5836981f3b0baf8df94dc1ea1),
  [GLiNER bi-encoder v2.0](https://app.notion.com/p/409141b58369817da32fc0f3d8b9539d)
- **Capabilities** — [R1](https://app.notion.com/p/409141b583698193afd0df397607d787),
  [T7](https://app.notion.com/p/409141b5836981088386e252c531ad6e),
  [D7](https://app.notion.com/p/409141b583698152ad9bf211bb833339),
  [A4](https://app.notion.com/p/409141b5836981c990efe562db5c4082),
  [Q10](https://app.notion.com/p/409141b58369815a8065e06db6b2fa0d)
- **Used by** — [2.1](stream-combinations.md#notion-409141b5836981e88660f3eede7253ac),
  [2.5](stream-combinations.md#notion-409141b58369813fb393ea90313ceb6a),
  [5.9](stream-combinations.md#notion-409141b583698123a463c42c912a6042),
  [5.10](stream-combinations.md#notion-409141b5836981c58169e46a89b8ac6c),
  [6.5](stream-combinations.md#notion-409141b58369816f966ce592ba2c3432),
  [6.3](stream-combinations.md#notion-409141b58369816abbbffc5a400dc4c1)

<a id="group-build-stage-3-identity"></a>

## Build stage 3 Identity

<a id="notion-409141b5836981768728e731d44f5fff"></a>

### Coreference clusters (coref)

**Verdict** Keep with change · **Run wave** 9 · **CPU cost** High · **Licence** CC BY-NC-SA · [Notion record](https://app.notion.com/p/409141b5836981768728e731d44f5fff)

- **Producer** — Maverick on CPU (CorPipe for non-English text); bridging and abstract reference ("this pressure")
  go to the CPU LLM with candidate antecedents and a none option
- **Key emitted** — Cluster ID
- **Performance evidence** — Maverick 83.6 CoNLL-F1 on OntoNotes, best English. CorPipe wins CRAC 2026 at 77.1.
- **Change** — Bridging and abstract anaphora ('this pressure') get their own route: unresolved definite noun
  phrases and 'this/that + noun' go to the CPU LLM with candidate antecedents and a 'none' option. Identity
  coreference models do not resolve these; the best published result is 28.7 F1 on ISNotes, with an LLM.
- **Reach** — 64
- **Models conditioned** — 6
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)
- **Models** — [Maverick coreference](https://app.notion.com/p/409141b583698147b9c2c1de27225966), [CorPipe
  (25/26)](https://app.notion.com/p/409141b5836981528e7efddee36131b1)
- **Capabilities** — [R6](https://app.notion.com/p/409141b583698193aff5e313fc233b81)
- **Used by** — [3.1](stream-combinations.md#notion-409141b5836981f69dc4e1260c26c827)

<a id="notion-409141b583698179988cc7290f49ed7e"></a>

### Entity links with fine types (el)

**Verdict** Keep with change · **Run wave** 9 · **CPU cost** Medium to high · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698179988cc7290f49ed7e)

- **Producer** — ReFinED, given the inventory mentions as spans, with its own detection as a recall pass;
  low-confidence and NIL links go to the CPU LLM with their candidates (ReFinED plus LLM beats either alone)
- **Key emitted** — Wikidata ID, fine-grained type
- **Performance evidence** — 87.4 AIDA and 94.5 MSNBC disambiguation with given mentions. ReFinED routing hard
  mentions to an LLM (ARTER) beats either alone.
- **Change** — Send low-confidence and NIL links to the CPU LLM with their candidates. Already reflected in
  Producer.
- **Reach** — 60
- **Models conditioned** — 7
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)
- **Models** — [ReFinED](https://app.notion.com/p/409141b583698166ba44d04b01bbb387)
- **Capabilities** — [R7](https://app.notion.com/p/409141b58369819dbc22ec542be5373f)
- **Used by** — [3.2](stream-combinations.md#notion-409141b58369819fac55ec3d81ffe72e)

<a id="notion-409141b583698180bb6ec82da7b6e42d"></a>

### Local Wikidata subset (data, not a model) (kb)

**Verdict** Keep · **Run wave** 10 · **CPU cost** Very low · **Licence** CC0 · [Notion record](https://app.notion.com/p/409141b583698180bb6ec82da7b6e42d)

- **Producer** — Wikidata dump filtered to linked entities
- **Key emitted** — Wikidata statements and class hierarchy
- **Performance evidence** — Data, not a model: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 10
- **Models conditioned** — 1
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)
- **Capabilities** — [R7](https://app.notion.com/p/409141b58369819dbc22ec542be5373f),
  [O7](https://app.notion.com/p/409141b5836981dab846d180d79972ce)
- **Used by** — [4.3](stream-combinations.md#notion-409141b583698169929afb2606b1c8cf),
  [8.2](stream-combinations.md#notion-409141b583698116887fda3ca1c5566d),
  [8.7](stream-combinations.md#notion-409141b5836981f5a2e5dd0134042a82)

<a id="group-build-stage-4-propositions"></a>

## Build stage 4 Propositions

<a id="notion-409141b58369812db491c726a039ca18"></a>

### Atomic propositions per sentence (claims)

**Verdict** Removed · **Run wave** 4 · **CPU cost** High (generative) · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369812db491c726a039ca18)

- **Producer** — The CPU LLM (Qwen3.6-35B-A3B, 4-bit) with Claimify-style prompts through LangExtract, a paragraph
  per call, on non-duplicate, non-reference, claim-bearing text. Replaced Gemma-APS on 30 Oct 2026: 32B-class models
  score 95.7% completeness on Claim2Atom while 2-3B models collapse. Fallback if too slow: Propositionizer
- **Key emitted** — Proposition text, source character span
- **Performance evidence** — Gemma-APS: no independent result; small LLMs collapse on decomposition (Llama-3.2-3B
  scores 24% completeness on Claim2Atom), and it returns no offsets. Replacement: Qwen3-32B scores 95.7%
  completeness and 94.8% correctness on Claim2Atom.
- **Change** — Gemma-APS removed by the audit. This row now describes the CPU LLM (Qwen3.6-35B-A3B, 4-bit) with
  Claimify-style prompts through LangExtract, a paragraph per call, under the same gate (English, non-duplicate,
  non-reference, claim-bearing text). LangExtract returns character offsets, so no realignment step. Time it first;
  the fallback is Propositionizer (Flan-T5-large, 783M), with weaker evidence and no offsets.
- **Reach** — 40
- **Models conditioned** — 5
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)
- **Models** — [Qwen 3.x single-GPU models (Qwen3.8-27B, Qwen3.6-35B-A3B, Qwen3.6-27B,
  Qwen3.5-27B/9B)](https://app.notion.com/p/409141b58369816d8becd5748dde9d75)
- **Capabilities** — [P7](https://app.notion.com/p/409141b583698125b20ae7e1a0fbd4c9)
- **Used by** — [4.9](stream-combinations.md#notion-409141b583698123a216d4459f31bd6d)

<a id="notion-409141b58369816ea14af7169d6ca284"></a>

### Support and entailment scores (nli)

**Verdict** Keep · **Run wave** 4 · **CPU cost** Medium per pair · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369816ea14af7169d6ca284)

- **Producer** — FactCG-DeBERTa-L (supported or not); DeBERTa-v3 NLI cross-encoder (entail, neutral, contradict)
- **Key emitted** — Premise-hypothesis pair
- **Performance evidence** — FactCG 75.6 on LLM-AggreFact, best of the sub-1B checkers (MiniCheck-Flan-T5-L 75.0,
  HHEM 71.8).
- **Change** — No change to the producer. Its NLI scores also feed support and attack between claims, which replaced
  ARI RoBERTa.
- **Reach** — 41
- **Models conditioned** — 5
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)
- **Models** — [FactCG-DeBERTa-v3-Large](https://app.notion.com/p/409141b58369817db7cdc150eec7053b)
- **Capabilities** — [V2](https://app.notion.com/p/409141b5836981338261d629a9039854),
  [P8](https://app.notion.com/p/409141b5836981b0aa25ca5ef19738f3)
- **Used by** — [4.6](stream-combinations.md#notion-409141b5836981d0804fc95ca5a45fb1),
  [7.3](stream-combinations.md#notion-409141b58369812bbebfe671f59c4652),
  [6.2](stream-combinations.md#notion-409141b5836981278809fc0ca0b6cb51),
  [7.7](stream-combinations.md#notion-409141b5836981f2ae3ae3df3991a162),
  [9.3](stream-combinations.md#notion-409141b58369812aa816deef834ae4b1)

<a id="notion-409141b58369810eba6fc542f1f9608a"></a>

### Table statements: column roles and cell assertions (tabstmt)

**Verdict** Removed · **Run wave** 7 · **CPU cost** Low to medium · **Licence** Follows its component models · [Notion record](https://app.notion.com/p/409141b58369810eba6fc542f1f9608a)

- **Producer** — Table assembly, lookup and score: Docling cells and column profiling (key, measure, dimension),
  GLiNER2.5 on header text against the schema's attribute types, CQE and pint on value cells, ReFinED on entity
  cells with the column type as prior; each cell becomes (row entity, column attribute, value, unit, notes). The CPU
  LLM only for tables whose column roles stay ambiguous. Replaced TableLlama on 30 Oct 2026
- **Key emitted** — Table ID, cell, row entity, column attribute
- **Performance evidence** — TableLlama: its 94.4 is TURL column typing inside TURL's label set; it emits no cell
  assertions, units or notes, and a 7B dense model at 4-bit was the slowest model in phase B. Replacement:
  lookup-and-score systems won SemTab 2020, and LLM plus KG retrieval leads SemTab 2025 cell linking.
- **Change** — TableLlama removed by the audit. This row now describes table assembly: Docling cells and column
  profiling, GLiNER2.5 on header text, CQE and pint on value cells, ReFinED on entity cells; each cell becomes (row
  entity, column attribute, value, unit, notes). The CPU LLM only for tables whose column roles stay ambiguous.
  Removes the slowest phase-B model.
- **Reach** — 48
- **Models conditioned** — 5
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)
- **Models** — [Docling](https://app.notion.com/p/409141b5836981aa9889c7f3107ce7d9), [GLiNER2 / GLiNER2.5 (incl.
  Decide)](https://app.notion.com/p/409141b5836981f3b0baf8df94dc1ea1), [CQE (Comprehensive Quantity
  Extractor)](https://app.notion.com/p/409141b583698141aeedfc48eb2f5347),
  [ReFinED](https://app.notion.com/p/409141b583698166ba44d04b01bbb387), [Qwen 3.x single-GPU models (Qwen3.8-27B,
  Qwen3.6-35B-A3B, Qwen3.6-27B, Qwen3.5-27B/9B)](https://app.notion.com/p/409141b58369816d8becd5748dde9d75)
- **Capabilities** — [P6](https://app.notion.com/p/409141b5836981a7be0df9f5b4231c97)
- **Used by** — [4.4](stream-combinations.md#notion-409141b5836981d18cc4e1e78466f0d2)

<a id="notion-409141b5836981578850f08fd787f43d"></a>

### Relations (rel)

**Verdict** Keep · **Run wave** 9 · **CPU cost** Medium · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981578850f08fd787f43d)

- **Producer** — GLiNER-Relex, run end to end on paragraph windows
- **Key emitted** — Head span, tail span, relation label
- **Performance evidence** — 25.6 average zero-shot F1 vs 22.1 for GPT-5-mini and 17.8 for GLiNER2.5 (authors'
  comparison). Every zero-shot option is weak at document scope.
- **Change** — No change.
- **Reach** — 44
- **Models conditioned** — 5
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)
- **Models** — [GLiNER-RelEx (joint NER + relation
  extraction)](https://app.notion.com/p/409141b5836981cfba02c26331bf5b83)
- **Capabilities** — [P2](https://app.notion.com/p/409141b5836981e9a8c0fe4388149650)
- **Used by** — [4.1](stream-combinations.md#notion-409141b5836981ca8d66f08b0b61b113),
  [4.2](stream-combinations.md#notion-409141b5836981b7829bec84ef90f752)

<a id="group-build-stage-5-qualification"></a>

## Build stage 5 Qualification

<a id="notion-409141b5836981ebb77dee17699cd7ce"></a>

### Discourse parse (disc)

**Verdict** Keep with change · **Run wave** 4 · **CPU cost** Medium · **Licence** Research-only weights · [Notion record](https://app.notion.com/p/409141b5836981ebb77dee17699cd7ce)

- **Producer** — Dipo
- **Key emitted** — Discourse unit ID, rhetorical relation
- **Performance evidence** — DMRST-400M (Dipo) scores 53.2 full-Parseval F1 on RST-DT from raw text, vs 53.9 for
  IsaNLP v3 on GPU, so it is at the CPU frontier, but low enough that discourse links are never used as gates. F1
  combines precision and recall, so it does not say what share of emitted relations are wrong.
- **Change** — Soft feature only: weights and priorities, never a gate.
- **Reach** — 28
- **Models conditioned** — 5
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)
- **Models** — [Dipo (Discourse Parsing Omnibus) with DMRST and generative RST
  parsers](https://app.notion.com/p/409141b58369815cac04f462b26d4a26)
- **Capabilities** — [A2](https://app.notion.com/p/409141b5836981e2a5b1de26acb1b9a9)
- **Used by** — [5.3](stream-combinations.md#notion-409141b5836981ae802df3160a2e0f55),
  [6.1](stream-combinations.md#notion-409141b5836981659d9af5ab527c816f),
  [6.6](stream-combinations.md#notion-409141b5836981adacd1d08814bff80e)

<a id="group-build-stage-6-discourse-and-argument"></a>

## Build stage 6 Discourse and argument

<a id="notion-409141b5836981ab84bffe7436ced61c"></a>

### Support and attack between claims (arg)

**Verdict** Removed · **Run wave** 20 · **CPU cost** Medium per pair · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981ab84bffe7436ced61c)

- **Producer** — DeBERTa-v3 NLI on candidate claim pairs (entail as support, contradict as attack), prioritised by
  Dipo links; the CPU LLM labels the top pairs. Replaced ARI RoBERTa on 30 Oct 2026: prompted LLMs beat RoBERTa
  baselines significantly (Gorur et al. 2025)
- **Key emitted** — Claim pair
- **Performance evidence** — ARI RoBERTa: 0.70 macro-F1 inside its own debate data. Prompted LLMs significantly beat
  RoBERTa baselines on support and attack (Gorur et al., COLING 2025); gpt-oss-120b reaches 82.1% zero-shot on UKP
  vs 57.7 F1 for a fine-tuned BERT.
- **Change** — ARI RoBERTa removed by the audit. This row now describes DeBERTa NLI scores on candidate claim pairs
  (entail as support, contradict as attack), prioritised by Dipo links, with the CPU LLM labelling the top pairs.
  NLI scores are features of support and attack, not their definition. No added cost: NLI already runs and the LLM
  sees a filtered set.
- **Reach** — 2
- **Models conditioned** — 0
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)
- **Models** — [FactCG-DeBERTa-v3-Large](https://app.notion.com/p/409141b58369817db7cdc150eec7053b), [Qwen 3.x
  single-GPU models (Qwen3.8-27B, Qwen3.6-35B-A3B, Qwen3.6-27B,
  Qwen3.5-27B/9B)](https://app.notion.com/p/409141b58369816d8becd5748dde9d75)
- **Capabilities** — [A3](https://app.notion.com/p/409141b583698168b8b3d8ecc07ac832)
- **Used by** — [6.2](stream-combinations.md#notion-409141b5836981278809fc0ca0b6cb51)

<a id="group-build-stage-7-corpus"></a>

## Build stage 7 Corpus

<a id="notion-409141b58369817c8ac1eb2c96d6f443"></a>

### Keyword index (bm25)

**Verdict** Keep · **Run wave** 3 · **CPU cost** Very low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369817c8ac1eb2c96d6f443)

- **Producer** — bm25s
- **Key emitted** — Term postings
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 14
- **Models conditioned** — 2
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [BM25S](https://app.notion.com/p/409141b583698172b5e5e6a900cd6c2f)
- **Capabilities** — [V7](https://app.notion.com/p/409141b5836981efb97cc203d060820f)
- **Used by** — [7.3](stream-combinations.md#notion-409141b58369812bbebfe671f59c4652),
  [9.1](stream-combinations.md#notion-409141b583698118b18ef02258134fbe)

<a id="notion-409141b583698173900bfbf18657f719"></a>

### Passage embeddings (emb)

**Verdict** Keep · **Run wave** 3 · **CPU cost** Medium · **Licence** CC BY-NC · [Notion record](https://app.notion.com/p/409141b583698173900bfbf18657f719)

- **Producer** — Jina embeddings v5 small
- **Key emitted** — Vector per passage
- **Performance evidence** — Jina v5 small: 71.7 English MTEB vs 70.7 for Qwen3-Embedding-0.6B; 67.7 vs 64.3
  multilingual.
- **Change** — No change.
- **Reach** — 30
- **Models conditioned** — 4
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [Jina Embeddings v5 (text, omni)](https://app.notion.com/p/409141b58369814aa34fe1f273063707)
- **Capabilities** — [V7](https://app.notion.com/p/409141b5836981efb97cc203d060820f)
- **Used by** — [7.12](stream-combinations.md#notion-409141b58369817baf69c933ae76405d),
  [7.1](stream-combinations.md#notion-409141b5836981c6ac16d8729eef6ad4),
  [7.9](stream-combinations.md#notion-409141b583698134a9a9cfe2691144f0),
  [9.1](stream-combinations.md#notion-409141b583698118b18ef02258134fbe)

<a id="notion-409141b5836981dab3b4fe90fc6c4087"></a>

### Reranking scores (rerank)

**Verdict** Keep · **Run wave** 4 · **CPU cost** Medium per query · **Licence** CC BY-NC · [Notion record](https://app.notion.com/p/409141b5836981dab3b4fe90fc6c4087)

- **Producer** — Jina reranker v3.5 (listwise: one pass over a query and its candidates)
- **Key emitted** — Query and candidate list
- **Performance evidence** — Jina reranker v3.5: BEIR 63.2 vs 56.9 and MIRACL 74.1 vs 67.1 for Qwen3-Reranker-0.6B.
- **Change** — No change.
- **Reach** — 11
- **Models conditioned** — 1
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [Jina Reranker v3 / v3.5](https://app.notion.com/p/409141b5836981c38133e0ba480d92c1)
- **Capabilities** — [V7](https://app.notion.com/p/409141b5836981efb97cc203d060820f)
- **Used by** — [7.3](stream-combinations.md#notion-409141b58369812bbebfe671f59c4652)

<a id="notion-409141b58369816d80fcf751582e646c"></a>

### Record-linkage scores (splink)

**Verdict** Keep · **Run wave** 13 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369816d80fcf751582e646c)

- **Producer** — Splink
- **Key emitted** — Record pair
- **Performance evidence** — Deterministic: the performance audit judged it to hold up. For cross-document identity
  it is an upgrade on xCoRe: LLM pair judges score 98–99 F1 on OpenSanctions pairs vs 91.3 for nomenklatura, and
  xCoRe managed 42.4 on ECB+.
- **Change** — No change.
- **Reach** — 29
- **Models conditioned** — 2
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [Splink](https://app.notion.com/p/409141b5836981e1a204f47351dc3edd)
- **Capabilities** — [R8](https://app.notion.com/p/409141b583698158b419de22ef9b5bc0)
- **Used by** — [7.2](stream-combinations.md#notion-409141b5836981ee83cbe564b02d71a9),
  [7.1](stream-combinations.md#notion-409141b5836981c6ac16d8729eef6ad4)

<a id="notion-409141b5836981e4b650dbcd7ea604e1"></a>

### Claim embeddings (claim\_emb)

**Verdict** Keep · **Run wave** 19 · **CPU cost** Medium · **Licence** CC BY-NC · [Notion record](https://app.notion.com/p/409141b5836981e4b650dbcd7ea604e1)

- **Producer** — Jina embeddings v5 small, over qualified claims
- **Key emitted** — Vector per claim
- **Performance evidence** — Jina v5 small: 71.7 English MTEB vs 70.7 for Qwen3-Embedding-0.6B; 67.7 vs 64.3
  multilingual.
- **Change** — No change.
- **Reach** — 12
- **Models conditioned** — 2
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [Jina Embeddings v5 (text, omni)](https://app.notion.com/p/409141b58369814aa34fe1f273063707)
- **Capabilities** — [P8](https://app.notion.com/p/409141b5836981b0aa25ca5ef19738f3)
- **Used by** — [7.3](stream-combinations.md#notion-409141b58369812bbebfe671f59c4652)

<a id="notion-409141b583698142b5c6e6907527d2bd"></a>

### Topic model (topics)

**Verdict** Keep · **Run wave** 20 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b583698142b5c6e6907527d2bd)

- **Producer** — BERTopic or FASTopic, over claim embeddings
- **Key emitted** — Topic ID
- **Performance evidence** — The performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 1
- **Models conditioned** — 0
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)
- **Models** — [BERTopic](https://app.notion.com/p/409141b58369819392b2dfc7b0991032)
- **Capabilities** — [C2](https://app.notion.com/p/409141b5836981dfad02d457eed504d0)
- **Used by** — [7.10](stream-combinations.md#notion-409141b58369813d9268ee4edaaf939b)

<a id="group-build-stage-8-ontology"></a>

## Build stage 8 Ontology

<a id="notion-409141b5836981479afdf1e51ac86be3"></a>

### Ontology tools (onto)

**Verdict** Keep · **Run wave** 0 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981479afdf1e51ac86be3)

- **Producer** — AMIE, sheXer, LogMap with OAK and SSSOM, KGCL and ROBOT
- **Key emitted** — Rule, shape, mapping, change proposal
- **Performance evidence** — LogMap 0.64 F1 on OAEI 2025 Conference; the two better 2025 matchers cannot be
  obtained.
- **Change** — No change. Outputs stay proposals for review.
- **Reach** — 7
- **Models conditioned** — 1
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)
- **Models** — [AMIE (rule mining under incomplete
  evidence)](https://app.notion.com/p/409141b583698164bfadf86f3ac8bedb), [sheXer (ShEx/SHACL shape
  extraction)](https://app.notion.com/p/409141b5836981a2a1e2d36e71cc63bf), [LogMap (incl. LogMapLt, LogMapBio,
  LogMapLLM oracle)](https://app.notion.com/p/409141b58369817fbd60cb0298694c0c)
- **Capabilities** — [O3](https://app.notion.com/p/409141b5836981a4a30bd4a695dc2985),
  [O4](https://app.notion.com/p/409141b583698141aa45e4c5184d1f3a),
  [O6](https://app.notion.com/p/409141b5836981e8a185d9b812e496e7),
  [O7](https://app.notion.com/p/409141b5836981dab846d180d79972ce),
  [O8](https://app.notion.com/p/409141b5836981618757f549ea19055d)
- **Used by** — [8.7](stream-combinations.md#notion-409141b5836981f5a2e5dd0134042a82),
  [8.6](stream-combinations.md#notion-409141b583698145b882e140fad3deb7),
  [8.8](stream-combinations.md#notion-409141b583698140a9f9f1491758b832)

<a id="group-build-stage-9-records-and-control"></a>

## Build stage 9 Records and control

<a id="notion-409141b5836981f6b33dcd95abe6ee43"></a>

### Validators and calibration (valid)

**Verdict** Keep · **Run wave** 0 · **CPU cost** Low · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981f6b33dcd95abe6ee43)

- **Producer** — pySHACL, Z3, Pydantic, pandera, MAPIE, cleanlab, Crowd-Kit
- **Key emitted** — Check result, calibrated score
- **Performance evidence** — Deterministic stream: the performance audit judged it to hold up and gave it no score.
- **Change** — No change.
- **Reach** — 4
- **Models conditioned** — 1
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Models** — [pySHACL](https://app.notion.com/p/409141b583698169be5cfa1f0ad2c01a)
- **Capabilities** — [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0),
  [V5](https://app.notion.com/p/409141b5836981e382b4d1a42cd254ce),
  [V8](https://app.notion.com/p/409141b583698126aaf1c0db2e01ddb9)
- **Used by** — [9.2](stream-combinations.md#notion-409141b58369814cb018c684b83a279a),
  [9.4](stream-combinations.md#notion-409141b583698193b6b1fb915cf7b4a9),
  [9.5](stream-combinations.md#notion-409141b5836981a699b4eb88173cf9c3)

<a id="notion-409141b5836981118a62f0e02a3decf6"></a>

### Template slot filling (nuextract)

**Verdict** Folded into another stream · **Run wave** 20 · **CPU cost** High (generative) · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b5836981118a62f0e02a3decf6)

- **Producer** — The CPU LLM (Qwen3.6-35B-A3B) with the record schema through LangExtract, on retrieved passages
  only. NuExtract3 folded in on 30 Oct 2026: one generative model to batch and calibrate; keep NuExtract3 only if it
  wins on slot accuracy per second in the smoke test
- **Key emitted** — Filled slot with source span
- **Performance evidence** — NuExtract3 4B at 4-bit: a second generative model competing for the same 16 cores and
  RAM. Independently below GPT-OSS-120B; never compared with Qwen3.6-35B-A3B.
- **Change** — NuExtract3 folded into the CPU LLM stream (Local LLM for the residue). This row now describes the CPU
  LLM with the record schema through LangExtract: one generative model to batch, cache and calibrate instead of two,
  and the RAM and cores NuExtract3 held are freed. Keep NuExtract3 only if it wins on slot accuracy per second in
  the smoke test.
- **Reach** — 6
- **Models conditioned** — 1
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Models** — [Qwen 3.x single-GPU models (Qwen3.8-27B, Qwen3.6-35B-A3B, Qwen3.6-27B,
  Qwen3.5-27B/9B)](https://app.notion.com/p/409141b58369816d8becd5748dde9d75)
- **Used by** — [9.1](stream-combinations.md#notion-409141b583698118b18ef02258134fbe)

<a id="notion-409141b58369819ab6edc5170de5803d"></a>

### Local LLM for the residue (llm)

**Verdict** Keep with change · **Run wave** 24 · **CPU cost** Very high (generative) · **Licence** Permissive · [Notion record](https://app.notion.com/p/409141b58369819ab6edc5170de5803d)

- **Producer** — Qwen3.6-35B-A3B at 4-bit on CPU, wrapped in LangExtract. The one generative model: atomic claims,
  ambiguous tables, top argument pairs, and what bounded inference leaves unresolved (links, references, conditions,
  empty slots, the residue). Its contribution is measured against a baseline with generative calls disabled
- **Key emitted** — Grounded output
- **Performance evidence** — Qwen3.6-35B-A3B at 4-bit: about 3B active parameters per token, so generation runs at a
  usable speed on 16 cores; it needs about 22 GB of RAM, and reading long inputs is the slow part (29 Oct stack).
- **Change** — Gains three jobs from removed models: atomic claims (Gemma-APS), ambiguous tables (TableLlama) and
  top argument pairs (ARI RoBERTa). It also takes NuExtract3's template slots, low-confidence and NIL links, and
  bridging. Four generative models become one. Time it on claim extraction, a paragraph per call, on the 20-document
  sample before committing.
- **Reach** — 1
- **Models conditioned** — 0
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)
- **Models** — [Qwen 3.x single-GPU models (Qwen3.8-27B, Qwen3.6-35B-A3B, Qwen3.6-27B,
  Qwen3.5-27B/9B)](https://app.notion.com/p/409141b58369816d8becd5748dde9d75)
- **Used by** — [9.6](stream-combinations.md#notion-409141b5836981fdb517c06be042bcd3)
