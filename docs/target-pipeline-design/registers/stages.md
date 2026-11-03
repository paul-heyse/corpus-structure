# Stages

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448?pvs=204) · [First production milestone](../first-production-milestone.md)

This rollout maps the nine tiers to stage-specific gates and evaluation. The proposed first production milestone
crosses the layers required for its five record families. Its deployment scope, evaluation, and release gates are
specified in the milestone design.

- [1 · Framing](#notion-40a141b5836981eeae7fe462e5c2a68d)
- [2 · Span inventory](#notion-40a141b583698196b5b4c5cc6ab20865)
- [3 · Identity](#notion-40a141b5836981bf816cfaf0bb095839)
- [4 · Propositions and tables](#notion-40a141b5836981c1b905ff7cee627528)
- [5 · Qualification](#notion-40a141b583698172b462e8ef1e246de3)
- [6 · Argument](#notion-40a141b58369817c9929cc494bc2c061)
- [7 · Corpus](#notion-40a141b58369816a9c70f23c650234aa)
- [8 · Ontology](#notion-40a141b58369811992a0c8007723a20b)
- [9 · Records and control](#notion-40a141b5836981469da5da987927234f)

<a id="notion-40a141b5836981eeae7fe462e5c2a68d"></a>

## 1 · Framing

**Status** Target · **Order** 1 · [Notion record](https://app.notion.com/p/40a141b5836981eeae7fe462e5c2a68d)

- **What you can say afterwards** — What each unit is, its language and reliability grade, its section's role, what
  it cites, its reference time, and which documents are editions of each other. With the PDF-only front end the
  edition link is mostly settled upstream, when each work's published form is chosen.
- **Models added** — Seed ontology v0, versioned. Docling, the only parser: layout, reading order, TableFormer
  tables, formula enrichment, and OCR where a page has no text layer (every source is rendered to its published PDF
  first, so PyMuPDF and the format parsers named in the original build order are outdated; PDF-only front end, 31
  Oct 2026). GROBID (CRF mode) for metadata, citations and references. SaT small for sentences, with blocks holding
  inline math routed to spaCy's formula-as-token split. GlotLID. The feature-based quality score, replacing
  ocr-error-detection (audit, 30 Oct 2026). Block hashes, MinHash and SemHash. GLiNER2.5 classification for document
  type and heading classes, with GLiClass large-v3 tested against it on the 20-document sample.
- **Decisions added** — Block type, section role, document type, language, reliability grade q per block, edition
  link. Each has an UNKNOWN option.
- **Where the extra value comes from** — Priors and gates that condition every later factor. The reliability grade q
  modulates all later evidence: each model's LLR is calibrated per grade.
- **Records accepted after it** — Units, sections, citations, editions (framing records only)
- **Front-end impact** — Most affected. Block type, section role and reading order come from Docling's layout labels
  and hierarchy. The reliability grade is read from Docling's recognition health: text layer vs OCR, layout
  confidence, formula and table recognition status. The edition link is settled upstream, since the published form
  is chosen before conversion. Offsets must map to Docling element references plus page and bounding box.
- **Gate to next stage** — Offsets round-trip on 100% of outputs. Each hard gate meets τ\_gate. The quality score is
  calibrated (reliability curve within tolerance).
- **Test before next stage** — Every output's offsets map back to the source anchor (Docling element reference, page
  and bounding box). Block types and section roles correct on a 20-document sample. Duplicates confirmed by hand.
- **Streams** — [tables](pipeline-streams.md#notion-409141b583698117b2e1c0b7067f2537),
  [formula](pipeline-streams.md#notion-409141b583698127815fd85f864c0fdd),
  [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [quality](pipeline-streams.md#notion-409141b5836981599a32fb76e77c07a7),
  [sents](pipeline-streams.md#notion-409141b5836981658aa5f249c86d3e7a),
  [canon](pipeline-streams.md#notion-409141b58369818a84addd332566fbb1),
  [genre](pipeline-streams.md#notion-409141b58369818abe2beb2ce219c7f8),
  [revs](pipeline-streams.md#notion-409141b58369818f9d2ffe8a835017b2),
  [lang](pipeline-streams.md#notion-409141b5836981ab9afaeb69b5d5ae32),
  [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [threads](pipeline-streams.md#notion-409141b5836981eb92d9d7bb774895d8),
  [dedup](pipeline-streams.md#notion-409141b5836981f59f41c0ed9052e70b)
- **Combinations unlocked** — [1.1](stream-combinations.md#notion-409141b58369811d8402c5783b88a812),
  [1.2](stream-combinations.md#notion-409141b5836981f888d4df9c58419c9a),
  [1.3](stream-combinations.md#notion-409141b583698102ac89ed4c7f82ea8a),
  [1.4](stream-combinations.md#notion-409141b58369816b8a55d644257d2e23),
  [1.5](stream-combinations.md#notion-409141b5836981499080ff4fc4c8a20e),
  [1.6](stream-combinations.md#notion-409141b5836981ef9825f3632387207c),
  [1.7](stream-combinations.md#notion-409141b58369810e838eefea6cb5ef86),
  [1.8](stream-combinations.md#notion-409141b58369816b8ce0fb40bdc774ac),
  [1.9](stream-combinations.md#notion-409141b5836981369becef06b4f81df0)
- **Components** — [Record-type registry](interpretation-components.md#notion-40a141b5836981d98f29c170328a3ace),
  [Observation store](interpretation-components.md#notion-40a141b5836981f7a0d2deb300a375b5), [Calibration
  table](interpretation-components.md#notion-40a141b5836981989921fdd4f94c578d), [Decision
  registry](interpretation-components.md#notion-40a141b5836981658472ca2c89f9fe3b), [Factor-template
  library](interpretation-components.md#notion-40a141b58369816480a2c1c21ed0fd0f), [Lineage
  layer](interpretation-components.md#notion-40a141b5836981aaaed0e68becf62ffa), [Acceptance and
  escalation](interpretation-components.md#notion-40a141b5836981e58b7fe0b1125e359f), [Evaluation
  harness](interpretation-components.md#notion-40a141b5836981509450f6bec3fcad70), [Seed ontology
  v0](interpretation-components.md#notion-40a141b58369812f9465f7037d397d37)
- **Decisions** — [Block type](decision-types.md#notion-40a141b583698177bc9fc4d13b6e5241), [Section
  role](decision-types.md#notion-40a141b5836981a190d9f9e059b56b47), [Document
  type](decision-types.md#notion-40a141b58369819eb13fefec7f65ea2a),
  [Language](decision-types.md#notion-40a141b58369813fb569c34ee2303b90), [Reliability
  grade](decision-types.md#notion-40a141b5836981d891dfc66564b447c4)
- **Templates** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Open questions** — [What are the value v and error cost c for each record
  type?](design-questions-and-decisions.md#notion-40a141b583698171b1fdd837ef91f2a6), [Which ontology becomes seed
  ontology v0, and in what format?](design-questions-and-decisions.md#notion-40a141b5836981a68cf6f8e9e81ff8ed),
  [Which Docling signals define the reliability grade q per
  block?](design-questions-and-decisions.md#notion-40a141b5836981b3aff0f76316a42fda), [What is the primary anchor
  for a span: canonical-text offsets or Docling element
  references?](design-questions-and-decisions.md#notion-40a141b5836981778930cbdc26e2b25a), [What happens to
  structure that conversion to PDF
  destroys?](design-questions-and-decisions.md#notion-40a141b5836981de810ef76dc4f8027c)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Only PDFs enter the
  pipeline: every source is converted to its published form, rendered to PDF and parsed by
  Docling](design-questions-and-decisions.md#notion-40b141b583698124bc73ee1447273e70), [How is the published form
  identified for each source type?](design-questions-and-decisions.md#notion-40b141b5836981b58acdf5c6452d92bd),
  [Which renderer turns each published form into a PDF, and how is its fidelity
  checked?](design-questions-and-decisions.md#notion-40b141b5836981c5abbcff950cf9f3c7), [What schema holds
  conversion-time metadata, and how is each item joined to the Docling elements it
  describes?](design-questions-and-decisions.md#notion-40b141b58369817983f3f8f4951684d1), [What does the front end
  do when rendering fails, or when Docling fails or only partly
  succeeds?](design-questions-and-decisions.md#notion-40b141b583698101b5d1d1017d9ad33f), [How are scanned pages
  detected and routed to full-page OCR?](design-questions-and-decisions.md#notion-40b141b5836981aa9888fb8a32fcdf00),
  [How are inline formulas drawn as vector paths
  recovered?](design-questions-and-decisions.md#notion-40b141b583698173a9cac652a89744dc), [How do the repository's
  PDF pipeline decisions (ADR-0038 to ADR-0045) relate to the Notion L0 front
  end?](design-questions-and-decisions.md#notion-40b141b5836981bfa9a3c8877162dd5a), [Text quality:
  ocr-error-detection removed, replaced by a feature-based quality
  score](design-questions-and-decisions.md#notion-40b141b5836981679924dd95780edee3), [Does GLiClass large-v3 beat
  GLiNER2.5 for document type and heading
  classes?](design-questions-and-decisions.md#notion-40b141b583698128b25bd28e87ebf029), [Which heavier reader
  re-reads pages that Docling grades
  low?](design-questions-and-decisions.md#notion-40b141b583698146965ffce689a21969), [The versioned seed ontology is
  an input from tier 1; tier 8 only proposes reviewed
  changes](design-questions-and-decisions.md#notion-40b141b5836981cfb1fef9641df32bed), [An interpretation layer
  chooses readings: observation contract, candidate sets with an unresolved option, bounded joint inference,
  coherent record assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1), [Complete
  cache keys and targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76),
  [Hard gates are limited to precise
  signals](design-questions-and-decisions.md#notion-40b141b58369818b95bad9d7d9ee34b7), [What are the value v and
  error cost c for each record type?](design-questions-and-decisions.md#notion-40a141b583698171b1fdd837ef91f2a6),
  [What is the primary anchor for a span: canonical-text offsets or Docling element
  references?](design-questions-and-decisions.md#notion-40a141b5836981778930cbdc26e2b25a), [Which ontology becomes
  seed ontology v0, and in what format?](design-questions-and-decisions.md#notion-40a141b5836981a68cf6f8e9e81ff8ed),
  [Which Docling signals define the reliability grade q per
  block?](design-questions-and-decisions.md#notion-40a141b5836981b3aff0f76316a42fda), [When does a shared-error
  model (Pyro) earn its place?](design-questions-and-decisions.md#notion-40a141b5836981d498a6c47dc7105a8a), [What
  happens to structure that conversion to PDF
  destroys?](design-questions-and-decisions.md#notion-40a141b5836981de810ef76dc4f8027c), [Docling conversion output
  can vary between runs and machines](design-questions-and-decisions.md#notion-40b141b5836981d283bac12028533f83),
  [Tables split across pages become separate
  TableItems](design-questions-and-decisions.md#notion-40b141b58369812a9499e96904758d85)

Tier page: [1️⃣ Tier 1 · Framing](https://app.notion.com/p/40b141b58369812db57fd921cc0f910c). This row carries the staged plan's "Stage 1: addressing and framing" in full and the pipeline page's build-order row 1, corrected for the 30 October audit and the PDF-only front end. The models, combinations, streams, outcomes, gate and test are in the properties above. Stage 1 also builds the shared machinery that every later stage is specified and measured through: [🏗️ Built once at stage 1](https://app.notion.com/p/40b141b583698127bfb2c1a9c18e278b).

### Detail

#### Decisions

Block type, section role, document type, language, reliability grade $q$ per block, edition link. Each has an unknown option.

#### Factors

- Section role × heading class × position.
- Document type × section role (a datasheet has no Methods).
- Language × script.

#### The reliability hook

Make $q$ a variable that later evidence factors condition on: each model's likelihood ratio is calibrated per reliability grade, $\text{LLR}_a(q)$. This is the first, cheapest way to model shared error. One garbled block lowers every extractor's evidence at once, instead of each being trusted independently. It also gives the first data on whether Pyro will be needed: if extractor accuracy varies strongly and jointly with $q$, shared-error modelling earns its place.

#### Gates

A hard gate is allowed only where its precision on the sample clears a high threshold $\tau_{\text{gate}}$ (block types, reference lists, language, exact duplicates). Everything else enters later factors as a prior.

#### Rules

Offset mapping and duplicate hashing are deterministic; no uncertainty is attached.

#### Records and value

Framing records only. $V$ here is the precision of gates and the calibration of priors, because they condition everything after.

#### Measured before stage 2

Gate precision; calibration of the quality score; extractor accuracy by reliability grade.

#### Gate to stage 2

Offsets round-trip on 100% of outputs. Each hard gate meets $\tau_{\text{gate}}$. The quality score is calibrated (reliability curve within tolerance).

The build order adds hand checks that the gate does not cover: block types and section roles correct on a 20-document sample, and duplicates confirmed by hand. Both are kept, in Gate to next stage and Test before next stage.

#### Prototype

None. The three prototypes start at stage 3; stage 1 provides the harness, registries and lineage they are measured with. See [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Changes from the original build order

- PyMuPDF and the format parsers are outdated at this stage. Since 31 October every source is converted to its published form and rendered to PDF, and Docling is the only parser.
- ocr-error-detection was replaced by the feature-based quality score (audit, 30 October 2026).
- Blocks with inline math are routed to spaCy's formula-as-token split: raw-text splitting scored 0.80 boundary F1 on math-dense text against 1.00 for spaCy with each formula as one token (repository spike S1, method M03).
- GLiClass large-v3 is tested against GLiNER2.5 for document and heading classes, which sit on the critical path.

#### With the PDF-only front end

- Docling's layout model supplies block type and hierarchy as observations with their own scores, not as facts; they are calibrated like any other stream.
- The reliability grade $q$ should be computed from Docling's own health signals per block: whether text came from the PDF text layer or OCR, layout and table confidence, formula enrichment success. This is now the natural place where shared error enters.
- Stage 1 is also where the interpretation layer's observation contract meets the front end: input digest = PDF digest plus Docling configuration hash, and every span carries page, bounding box and Docling element reference.

### Open questions and decisions

- [What are the value v and error cost c for each record type?](design-questions-and-decisions.md#notion-40a141b583698171b1fdd837ef91f2a6)
- [Which ontology becomes seed ontology v0, and in what format?](design-questions-and-decisions.md#notion-40a141b5836981a68cf6f8e9e81ff8ed)
- [Which Docling signals define the reliability grade q per block?](design-questions-and-decisions.md#notion-40a141b5836981b3aff0f76316a42fda)
- [What is the primary anchor for a span: canonical-text offsets or Docling element references?](design-questions-and-decisions.md#notion-40a141b5836981778930cbdc26e2b25a)
- [What happens to structure that conversion to PDF destroys?](design-questions-and-decisions.md#notion-40a141b5836981de810ef76dc4f8027c)
- [When does a shared-error model (Pyro) earn its place?](design-questions-and-decisions.md#notion-40a141b5836981d498a6c47dc7105a8a)
- [Does GLiClass large-v3 beat GLiNER2.5 for document type and heading classes?](design-questions-and-decisions.md#notion-40b141b583698128b25bd28e87ebf029)
- [Which heavier reader re-reads pages that Docling grades low?](design-questions-and-decisions.md#notion-40b141b583698146965ffce689a21969)
- Decided: [Only PDFs enter the pipeline: every source is converted to its published form, rendered to PDF and parsed by Docling](design-questions-and-decisions.md#notion-40b141b583698124bc73ee1447273e70); [Text quality: ocr-error-detection removed, replaced by a feature-based quality score](design-questions-and-decisions.md#notion-40b141b5836981679924dd95780edee3); [Hard gates are limited to precise signals](design-questions-and-decisions.md#notion-40b141b58369818b95bad9d7d9ee34b7); [The versioned seed ontology is an input from tier 1; tier 8 only proposes reviewed changes](design-questions-and-decisions.md#notion-40b141b5836981cfb1fef9641df32bed); [An interpretation layer chooses readings: observation contract, candidate sets with an unresolved option, bounded joint inference, coherent record assignment](design-questions-and-decisions.md#notion-40b141b58369818197e0e54f372130e1); [Complete cache keys and targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp) (Claude Doc, 31 October 2026): "Stage 1: addressing and framing" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 1.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk) (30 October 2026): "The revised set by build stage".
- [📄 L0 · Front end: published form to PDF to Docling](https://app.notion.com/p/40a141b58369811b8cd1dc6d9da943b3) for the front-end needs.

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Next: [2 · Span inventory](#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b583698196b5b4c5cc6ab20865"></a>

## 2 · Span inventory

**Status** Target · **Order** 2 · [Notion record](https://app.notion.com/p/40a141b583698196b5b4c5cc6ab20865)

- **What you can say afterwards** — Every mention typed and marked as a named entity or a concept. Every number
  attached to an entity and property, with units normalized. Terms with their variants, definitions with their
  genus, symbols bound to meanings, implicit sections in unmarked text.
- **Models added** — Stanza on CPU, converted to spaCy Docs, run in pretokenized mode on math blocks so each formula
  stays one token. GLiNER2.5 and the GLiNER bi-encoder large with routed label sets, including concept labels
  (replacing CNER, audit 30 Oct 2026) and condition-clause labels; GLiFormer large tested against the bi-encoder. A
  genericity flag from the parse. CQE and the normalizers (Duckling, dateparser, pint, text2num). Cue lexicons. The
  abbreviation detector (Schwartz-Hearst). Term candidates (GLiNER term labels, KeyBERT, noun chunks). The
  personal-data detectors (Privacy Filter, GLiNER-PII, Presidio) if the documents hold personal data.
- **Decisions added** — Mention span and type, concept vs named entity, quantity value, unit and dimension, value
  attachment, abbreviation expansion, symbol binding.
- **Where the extra value comes from** — Disambiguation: unit dimension with property; type votes from one model
  family as one correlated factor; a later definition resolves an earlier acronym.
- **Records accepted after it** — Attached quantities (entity, property, value, unit)
- **Front-end impact** — Text and formulas now come only from Docling. PDF artefacts (hyphenation, ligatures,
  superscripts lost in extraction, minus signs as hyphens) hit numbers and units first, so LLR calibration per
  reliability grade matters most here. Formula enrichment output feeds symbol binding.
- **Gate to next stage** — Attachment correct on 100 hand-checked numbers at matched coverage, and a positive
  interaction between quantities and the ontology factor.
- **Test before next stage** — Type-agreement rate between GLiNER2.5 and the bi-encoder (since CNER was removed,
  this is the type-agreement check). Value attachment correct on 100 hand-checked numbers. Stanza timed on CPU.
- **Streams** — [concepts](pipeline-streams.md#notion-409141b58369810cb26dc09c30bf542d),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [abbr](pipeline-streams.md#notion-409141b583698146b66fc2dbbaf22d8e),
  [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [lex](pipeline-streams.md#notion-409141b5836981e5b923f097afd80915),
  [pii](pipeline-streams.md#notion-409141b5836981faace1e30da5b9f38d),
  [terms](pipeline-streams.md#notion-409141b5836981ff9c1cd5300743d087)
- **Combinations unlocked** — [2.1](stream-combinations.md#notion-409141b5836981e88660f3eede7253ac),
  [2.2](stream-combinations.md#notion-409141b5836981fc9364f2874585b571),
  [2.3](stream-combinations.md#notion-409141b58369815fac36e5072a1d652d),
  [2.4](stream-combinations.md#notion-409141b5836981ba9b2ceeaddeb4d553),
  [2.5](stream-combinations.md#notion-409141b58369813fb393ea90313ceb6a),
  [2.6](stream-combinations.md#notion-409141b583698165b5cccc4da90536ef),
  [2.7](stream-combinations.md#notion-409141b5836981debac4faa03c10afea),
  [2.8](stream-combinations.md#notion-409141b5836981f4b896cf86b4998700),
  [2.9](stream-combinations.md#notion-409141b5836981e6a150e244f5f25270),
  [2.10](stream-combinations.md#notion-409141b5836981e7a84bc95247b126b1)
- **Decisions** — [Mention span and type](decision-types.md#notion-40a141b583698175ad4feb290edc9e18), [Concept vs
  named entity](decision-types.md#notion-40a141b5836981209660dda3e2bd7285), [Unit and
  dimension](decision-types.md#notion-40a141b5836981e58f4bcf79b8ac8d7e), [Value
  attachment](decision-types.md#notion-40a141b58369810fa965ef1cbd022370), [Abbreviation
  expansion](decision-types.md#notion-40a141b58369817b91b9d794c442e2b1), [Symbol
  binding](decision-types.md#notion-40a141b583698161b6bcdd2b699f581f)
- **Templates** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Open questions** — [Is the labelling budget for the stage gates
  realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [CPU throughput of the
  slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea), [Model
  interfaces the design relies on were checked but not
  run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae), [Several key models are
  English-only](design-questions-and-decisions.md#notion-40b141b58369819b95cce78ba12c6c80), [Conditions rest on thin
  evidence](design-questions-and-decisions.md#notion-40b141b5836981ae9becc156c7c8ccff), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [Should the
  repository add one bounded M13 → M11 pass that re-resolves ambiguous math
  spans?](design-questions-and-decisions.md#notion-40b141b583698109a3e7f9c102144ec7), [Concept vs named entity: CNER
  removed, replaced by the GLiNER bi-encoder with concept labels and a parse genericity
  flag](design-questions-and-decisions.md#notion-40b141b5836981e79451c3f99f579a63), [Conditions get an explicit
  route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit
  conditions](design-questions-and-decisions.md#notion-40b141b58369813196e2f5470bb81336), [Does GLiFormer large beat
  the GLiNER bi-encoder for typed
  mentions?](design-questions-and-decisions.md#notion-40b141b58369819f852ff683609ed6c1), [Stanza replaces UDPipe 2
  for parsing on CPU](design-questions-and-decisions.md#notion-40b141b5836981aa9727cad3f5af39a9), [Seven
  combinations were added in the pre-publication
  review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360), [Is the labelling budget for
  the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)

Tier page: [2️⃣ Tier 2 · Span inventory](https://app.notion.com/p/40b141b5836981f9b526cd13e98c0220). This row carries the staged plan's "Stage 2: span inventory" in full and the pipeline page's build-order row 2, corrected for the 30 October audit and the PDF-only front end. The models, combinations, streams, outcomes, gate and test are in the properties above.

### Detail

#### Decisions

Mention span and type (with unknown), concept vs named entity, quantity value, unit and dimension, value attachment (which noun phrase a quantity belongs to), abbreviation expansion, symbol binding.

#### Factors

- GLiNER2.5 and the bi-encoder share a model family, so their type votes form **one** evidence factor with a jointly fitted likelihood, not two.
- Unit dimension × property, from the ontology's quantity dimensions: a pressure unit cannot attach to a flow property.
- Attachment × dependency path from Stanza.
- Definition × acronym: a later definition can resolve an earlier short form.
- Genericity flag × concept vs entity.

#### Rules

Unit conversion keeps the source quantity and the transformation in the lineage. Declared abbreviations resolve deterministically.

#### Records and value

The first user-facing record type: the attached quantity (entity, property, value, unit), accepted at its $\tau$. Partial frames are kept, with missing roles marked as unknown, never filled by default.

#### Measured

LLR calibration per span model and per reliability grade. Conformal candidate recall for attachment and type. The first interaction index: $I(\text{quantities}, \text{parse})$ and $I(\text{quantities}, \text{ontology})$. This is the earliest test that the joint model adds anything.

#### Gate to stage 3

Attachment correct on 100 hand-checked numbers at matched coverage, and a positive interaction between quantities and the ontology factor. If that interaction is near zero, the unit-dimension factor is fixed before identity is built on it.

The build order adds the type-agreement rate between GLiNER2.5 and the bi-encoder and a CPU timing of Stanza (Test before next stage).

#### Prototype

Stage 2 supplies the quantity, unit and attachment decisions that prototype 1 (quantities, value roles, conditions and numeric references) completes at stage 5. See [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Changes from the original build order

- CNER was removed. Concept vs named entity now comes from the GLiNER bi-encoder with concept label descriptions plus a genericity flag from the Stanza parse (audit, 30 October 2026).
- Condition-clause labels were added to the routed GLiNER label set, so conditions have an explicit route from this stage.
- GLiFormer large is tested against the bi-encoder.
- With the PDF-only front end, text and formulas come only from Docling; PDF artefacts hit numbers and units first (see Front-end impact).

### Open questions and decisions

- [Is the labelling budget for the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- [Does GLiFormer large beat the GLiNER bi-encoder for typed mentions?](design-questions-and-decisions.md#notion-40b141b58369819f852ff683609ed6c1)
- Risks: [Conditions rest on thin evidence](design-questions-and-decisions.md#notion-40b141b5836981ae9becc156c7c8ccff); [CPU throughput of the slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea); [Several key models are English-only](design-questions-and-decisions.md#notion-40b141b58369819b95cce78ba12c6c80); [Candidate recall bounds every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39)
- Decided: [Concept vs named entity: CNER removed, replaced by the GLiNER bi-encoder with concept labels and a parse genericity flag](design-questions-and-decisions.md#notion-40b141b5836981e79451c3f99f579a63); [Conditions get an explicit route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit conditions](design-questions-and-decisions.md#notion-40b141b58369813196e2f5470bb81336); [Stanza replaces UDPipe 2 for parsing on CPU](design-questions-and-decisions.md#notion-40b141b5836981aa9727cad3f5af39a9); [Seven combinations were added in the pre-publication review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 2: span inventory" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 2.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "The revised set by build stage".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [1 · Framing](#notion-40a141b5836981eeae7fe462e5c2a68d) · Next: [3 · Identity](#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-40a141b5836981bf816cfaf0bb095839"></a>

## 3 · Identity

**Status** Target · **Order** 3 · **Prototype** P2 Identity type and relation · [Notion record](https://app.notion.com/p/40a141b5836981bf816cfaf0bb095839)

- **What you can say afterwards** — Entity-level counts and salience, KB IDs and fine types, what the KB does not
  know (NIL candidates with their reason), and redaction that covers pronouns.
- **Models added** — Maverick for coreference (CorPipe for non-English text) and ReFinED for entity links, both
  given the mention inventory, with pronouns and noun phrases added for coreference; ReFinED keeps its own detection
  as a recall pass. A local Wikidata subset plus the seed ontology's known entities as link targets. Joint identity,
  type and relation templates (pgmpy or the prototype's own exact solver: see the design question). The CPU LLM on
  low-confidence and NIL links with their candidates, and on bridging and abstract reference ("this pressure") with
  candidate antecedents and a none option (audit, 30 Oct 2026), only once the stage-5 baseline is measured.
- **Decisions added** — Cluster membership (pairwise links in a bounded window), entity link per cluster with NIL
  reason, entity type, instance vs class.
- **Where the extra value comes from** — Disambiguation: link with type with cluster (prototype 2, first half).
- **Records accepted after it** — Grounded entities; NIL candidates with reasons
- **Front-end impact** — Page furniture (running headers, footers, page numbers) must be excluded by Docling before
  mentions are clustered, or repeated headers become spurious coreference chains.
- **Gate to next stage** — Share of clusters with conflicting IDs, NIL rate by reason, and link candidate recall at
  or above the conformal target.
- **Test before next stage** — Share of clusters with conflicting IDs. NIL rate by type and by reason. Candidate
  recall for links and types. 50 clusters checked by hand.
- **Streams** — [coref](pipeline-streams.md#notion-409141b5836981768728e731d44f5fff),
  [el](pipeline-streams.md#notion-409141b583698179988cc7290f49ed7e),
  [kb](pipeline-streams.md#notion-409141b583698180bb6ec82da7b6e42d)
- **Combinations unlocked** — [3.1](stream-combinations.md#notion-409141b5836981f69dc4e1260c26c827),
  [3.2](stream-combinations.md#notion-409141b58369819fac55ec3d81ffe72e),
  [3.3](stream-combinations.md#notion-409141b5836981aaa09fc75d3f86b0f5),
  [3.4](stream-combinations.md#notion-409141b583698155b2c3f9fad114c7a1),
  [3.5](stream-combinations.md#notion-409141b5836981eeacf6fb407f615d64),
  [3.6](stream-combinations.md#notion-409141b5836981b6b75ce5b51efbf2dd),
  [3.7](stream-combinations.md#notion-409141b583698138a0dcedcd6df44e85),
  [3.8](stream-combinations.md#notion-409141b5836981aab53de3d4c1552549)
- **Decisions** — [Cluster membership](decision-types.md#notion-40a141b58369818fa634dfbef9760d85), [Entity
  link](decision-types.md#notion-40a141b5836981aeb37bfa048dc12ee3), [Instance vs
  class](decision-types.md#notion-40a141b5836981a3a482edc420ae8ce9)
- **Templates** — [Link, type and cluster](inference-templates.md#notion-40a141b5836981ac9029da913d0e7891)
- **Open questions** — [Is the labelling budget for the stage gates
  realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [CPU throughput of the
  slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea), [Model
  interfaces the design relies on were checked but not
  run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae), [Several key models are
  English-only](design-questions-and-decisions.md#notion-40b141b58369819b95cce78ba12c6c80), [Coreference used as
  input can hurt relation extraction](design-questions-and-decisions.md#notion-40b141b58369810b888adfe76c50a14b),
  [Bridging and abstract reference are unsolved in
  general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [Ontology
  expectations can coerce readings into existing
  categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020), [Bridging and abstract
  anaphora go to the CPU LLM with candidate antecedents and a none
  option](design-questions-and-decisions.md#notion-40b141b5836981ed83b0c876eff6dc0e), [Entity links carry NIL
  reasons, and instances are distinguished from
  classes](design-questions-and-decisions.md#notion-40b141b5836981e899b6c8c6b9745fd5), [The central hypothesis is
  tested first on three prototypes with generative calls disabled, against six
  baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a), [Generative calls stay off
  until the stage-5 baseline is
  measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612), [ReFinED and Maverick
  receive the mention inventory, with pronouns and noun phrases added for
  coreference](design-questions-and-decisions.md#notion-40b141b583698117a17df93f2f9e56ae), [Should templates use
  pgmpy or the prototype's own exact
  solver?](design-questions-and-decisions.md#notion-40a141b5836981689075d6d5d126d651), [Is the labelling budget for
  the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)

Tier page: [3️⃣ Tier 3 · Identity](https://app.notion.com/p/40b141b58369815ba14ed8b5098fa57f). This row carries the staged plan's "Stage 3: identity (prototype 2, first half)" in full and the pipeline page's build-order row 3, corrected for the 30 October audit. The models, combinations, streams, outcomes, gate and test are in the properties above.

### Detail

#### Decisions

Cluster membership (as pairwise links within a bounded window), entity link per cluster with NIL reason (local entity, insufficient context, retrieval failure, ambiguity, new concept), entity type, and instance vs class.

#### Factors

- Link × type: the KB or ontology class must be compatible with the span types.
- Cluster × link: a penalty when one cluster's mentions link to different IDs, so the conflict is resolved jointly instead of propagating the most informative mention's ID.
- Instance × class: "centrifugal pump" can be a class while P-101 is an instance of it.
- Ontology known entities as link targets alongside Wikidata.

#### Not yet

Relation × type factors wait for stage 4, which closes prototype 2.

#### Records and value

Grounded entities; NIL candidates with their reason. Only local entities and new concepts reach tier 8 later.

#### Measured

The fixed-candidate vs end-to-end comparison, the ontology-factor ablation, NIL-reason accuracy, and Shapley values over \{mentions, identity, ontology\}. The harness also records which decisions would have been escalated (their EVI), giving a counterfactual LLM budget before the LLM is switched on.

#### Gate to stage 4

Share of clusters with conflicting IDs, NIL rate by reason, and link candidate recall at or above the conformal target.

The build order adds NIL rate by type, candidate recall for types, and 50 clusters checked by hand (Test before next stage).

#### Prototype

Prototype 2, first half: joint identity, type and relation resolution. Competing mention links, local identities and types are kept; stage 4 adds relations and refits the joint model over both stages. See [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Changes from the original build order

- The CPU LLM now also takes low-confidence and NIL links with their candidates (ReFinED routing hard mentions to an LLM beats either alone), and bridging and abstract reference with candidate antecedents and a none option (audit, 30 October 2026). Both wait until the stage-5 baseline is measured.
- Page furniture must be excluded by Docling before mentions are clustered (see Front-end impact).

### Open questions and decisions

- [Is the labelling budget for the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- [Should templates use pgmpy or the prototype's own exact solver?](design-questions-and-decisions.md#notion-40a141b5836981689075d6d5d126d651)
- Risks: [Model interfaces the design relies on were checked but not run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae); [Coreference used as input can hurt relation extraction](design-questions-and-decisions.md#notion-40b141b58369810b888adfe76c50a14b); [Bridging and abstract reference are unsolved in general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be); [Ontology expectations can coerce readings into existing categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020); [CPU throughput of the slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea)
- Decided: [ReFinED and Maverick receive the mention inventory, with pronouns and noun phrases added for coreference](design-questions-and-decisions.md#notion-40b141b583698117a17df93f2f9e56ae); [Entity links carry NIL reasons, and instances are distinguished from classes](design-questions-and-decisions.md#notion-40b141b5836981e899b6c8c6b9745fd5); [Bridging and abstract anaphora go to the CPU LLM with candidate antecedents and a none option](design-questions-and-decisions.md#notion-40b141b5836981ed83b0c876eff6dc0e); [Generative calls stay off until the stage-5 baseline is measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612); [The central hypothesis is tested first on three prototypes with generative calls disabled, against six baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a)

### Evidence

- [Hajishirzi et al. 2013, joint coreference and entity linking](https://aclanthology.org/D13-1029/)
- [Durrett and Klein 2014, joint coreference, typing and linking](https://aclanthology.org/Q14-1037/)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 3: identity (prototype 2, first half)" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 3.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "The revised set by build stage".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [2 · Span inventory](#notion-40a141b583698196b5b4c5cc6ab20865) · Next: [4 · Propositions and tables](#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b5836981c1b905ff7cee627528"></a>

## 4 · Propositions and tables

**Status** Target · **Order** 4 · **Prototype** P2 Identity type and relation, P3 Tables to records · [Notion record](https://app.notion.com/p/40a141b5836981c1b905ff7cee627528)

- **What you can say afterwards** — Grounded, type-checked relations; table statements; text-table conflicts; events
  with roles; comparisons; and, once the claim pass is switched on after stage 5, claims aligned to source and
  mapped to their structured content.
- **Models added** — GLiNER-Relex, run end to end on paragraph windows. FactCG-DeBERTa-L and the DeBERTa-v3 NLI
  cross-encoder. Lookup-and-score table assembly over Docling cells, replacing TableLlama, with the CPU LLM only on
  tables whose column roles stay ambiguous. The CPU LLM claim pass (Qwen3.6-35B-A3B through LangExtract,
  Claimify-style prompts, a paragraph per call), replacing Gemma-APS (audit, 30 Oct 2026): built at this stage but
  switched off until the stage-5 baseline is measured, with its EVI logged per paragraph.
- **Decisions added** — Relation label and direction (with none), table column role, column property, row entity,
  cell statement, claim-content map.
- **Where the extra value comes from** — Assembly and closure: tables to records (prototype 3); relation with type
  closes prototype 2; text and table agreement as one record with two derivations.
- **Records accepted after it** — Measurement, specification and comparison records with lineage
- **Front-end impact** — Docling's table structure is now the only table source, so prototype 3 inherits its cell
  and spanning-header errors. Table recognition confidence should enter as the table's reliability grade, and
  captions and footnotes must arrive linked to their table.
- **Gate to next stage** — Domain and range violation rate, complete-record correctness for tables, and every
  text–table conflict reviewed.
- **Test before next stage** — Domain and range violation rate. Every text-table conflict reviewed. Claim alignment
  rate and share of claims with no structured content, measured once the claim pass is switched on after stage 5.
- **Streams** — [tabstmt](pipeline-streams.md#notion-409141b58369810eba6fc542f1f9608a),
  [claims](pipeline-streams.md#notion-409141b58369812db491c726a039ca18),
  [rel](pipeline-streams.md#notion-409141b5836981578850f08fd787f43d),
  [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Combinations unlocked** — [4.1](stream-combinations.md#notion-409141b5836981ca8d66f08b0b61b113),
  [4.2](stream-combinations.md#notion-409141b5836981b7829bec84ef90f752),
  [4.3](stream-combinations.md#notion-409141b583698169929afb2606b1c8cf),
  [4.4](stream-combinations.md#notion-409141b5836981d18cc4e1e78466f0d2),
  [4.5](stream-combinations.md#notion-409141b5836981508daff27e73a7bfeb),
  [4.6](stream-combinations.md#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](stream-combinations.md#notion-409141b5836981d48c27e6a4866db6f5),
  [4.8](stream-combinations.md#notion-409141b583698120b69fe73e93207120),
  [4.9](stream-combinations.md#notion-409141b583698123a216d4459f31bd6d)
- **Decisions** — [Relation label and direction](decision-types.md#notion-40a141b583698127b0ddfc36c059cad8), [Table
  column role](decision-types.md#notion-40a141b583698149ba2bc4be7294677e), [Column
  property](decision-types.md#notion-40a141b5836981279df7c46735c17b17), [Row
  entity](decision-types.md#notion-40a141b5836981508fb9c58175ee09b9)
- **Templates** — [Relation and argument types](inference-templates.md#notion-40a141b583698123b468ca9cd6dee971),
  [Table to record](inference-templates.md#notion-40a141b583698158bec4e7f2fffdc7ea)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [CPU throughput of the
  slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea), [Model
  interfaces the design relies on were checked but not
  run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae), [Table statements rest on
  assembly, not on one model](design-questions-and-decisions.md#notion-40b141b58369812a9192d57a7cdfd9e3),
  [Coreference used as input can hurt relation
  extraction](design-questions-and-decisions.md#notion-40b141b58369810b888adfe76c50a14b), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [Table
  statements: TableLlama removed, replaced by lookup-and-score table
  assembly](design-questions-and-decisions.md#notion-40b141b583698137b899ddfa3e8cdc47), [Atomic claims: Gemma-APS
  removed, replaced by the CPU LLM claim pass through
  LangExtract](design-questions-and-decisions.md#notion-40b141b5836981c2a8e4d69055783b23), [The central hypothesis
  is tested first on three prototypes with generative calls disabled, against six
  baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a), [Generative calls stay off
  until the stage-5 baseline is
  measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612), [Should templates use pgmpy
  or the prototype's own exact solver?](design-questions-and-decisions.md#notion-40a141b5836981689075d6d5d126d651),
  [Tables split across pages become separate
  TableItems](design-questions-and-decisions.md#notion-40b141b58369812a9499e96904758d85)

Tier page: [4️⃣ Tier 4 · Propositions](https://app.notion.com/p/40b141b58369810f81f1e168b89b607b). This row carries the staged plan's "Stage 4: propositions and tables (prototype 3; closes prototype 2)" in full and the pipeline page's build-order row 4, corrected for the 30 October audit. The models, combinations, streams, outcomes, gate and test are in the properties above.

### Detail

#### Decisions

Relation label and direction (with none), table column role (key, measure, dimension), column property, row entity, cell statement, and the claim-content map.

#### Factors

- Relation × argument types × ontology signature. This closes prototype 2: a well-supported relation can now correct an uncertain type from stage 3, and the joint model is refitted over both stages.
- Column property × header class × unit × row-entity type, the core of prototype 3.
- Text value × table cell for the same entity and property: one record with two derivations, joined by ⊕ in its lineage.

#### Rules

Percentage differences, comparisons and text–table agreement after normalization are deterministic derivations whose premises sit in the lineage.

#### Records and value

Measurement, specification and comparison records, each accepted at its own $\tau$ using the lineage probability. Field confidences are not multiplied.

#### Measured

This is where the assembly-and-closure term (rules minus union) should be largest. Report complete-record correctness for tables, including condition and note attachment, and the refit's effect on stage 3 numbers.

#### CPU LLM

The claim pass is built but stays off. The harness logs its EVI per paragraph, so its expected contribution is estimated before it costs anything.

#### Gate to stage 5

Domain and range violation rate, complete-record correctness for tables, and every text–table conflict reviewed.

The build order adds the claim alignment rate and the share of claims with no structured content (Test before next stage). Both apply once the claim pass is switched on after stage 5.

#### Prototype

Prototype 3, tables to records: rows, headers, units, captions, footnotes, entity candidates and ontology frames are combined, and complete-record correctness is measured, including condition and note attachment. This stage also closes prototype 2 (joint identity, type and relation). See [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Changes from the original build order

- TableLlama was removed. Table statements come from lookup-and-score assembly over Docling cells, with the CPU LLM only for tables whose column roles stay ambiguous (audit, 30 October 2026).
- Gemma-APS was removed. Atomic claims come from the CPU LLM (Qwen3.6-35B-A3B) with Claimify-style prompts through LangExtract, a paragraph per call; LangExtract returns character offsets.
- The staged plan keeps the claim pass off at this stage, although the build order lists it here.
- Docling's table structure is now the only table source (see Front-end impact).

### Open questions and decisions

- Risks: [Table statements rest on assembly, not on one model](design-questions-and-decisions.md#notion-40b141b58369812a9192d57a7cdfd9e3); [Coreference used as input can hurt relation extraction](design-questions-and-decisions.md#notion-40b141b58369810b888adfe76c50a14b); [Model interfaces the design relies on were checked but not run](design-questions-and-decisions.md#notion-40b141b5836981ac95cfc5113dea92ae); [CPU throughput of the slow models is untimed](design-questions-and-decisions.md#notion-40b141b5836981a485f3c5a71d5b0bea)
- Decided: [Table statements: TableLlama removed, replaced by lookup-and-score table assembly](design-questions-and-decisions.md#notion-40b141b583698137b899ddfa3e8cdc47); [Atomic claims: Gemma-APS removed, replaced by the CPU LLM claim pass through LangExtract](design-questions-and-decisions.md#notion-40b141b5836981c2a8e4d69055783b23); [Generative calls stay off until the stage-5 baseline is measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612); [The central hypothesis is tested first on three prototypes with generative calls disabled, against six baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a)

### Evidence

- [Roth and Yih 2004, global inference with entity-relation type constraints](https://aclanthology.org/W04-2401/)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 4: propositions and tables" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 4.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "Filling the gaps the removals leave" and "The revised set by build stage".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [3 · Identity](#notion-40a141b5836981bf816cfaf0bb095839) · Next: [5 · Qualification](#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b583698172b462e8ef1e246de3"></a>

## 5 · Qualification

**Status** Target · **Order** 5 · **Prototype** P1 Quantities and references · [Notion record](https://app.notion.com/p/40a141b583698172b462e8ef1e246de3)

- **What you can say afterwards** — The qualified claim: polarity, certainty, conditions, valid time, genericity,
  attribution, evidence basis, deontic force and value roles, carrying four confidence types (author modality,
  interpretation confidence and source reliability now; corpus support at stage 7).
- **Models added** — Dipo, for conditions that span sentences, as soft evidence only, never a gate. Local inference
  templates for condition scope, value role and numeric reference. Otherwise rules over tiers 2 to 4. Once the
  stage-5 decomposition is measured, the CPU LLM is switched on as a ninth stream group, for the claim pass and for
  decisions whose EVI exceeds λ times its cost.
- **Decisions added** — Polarity, author modality, condition scope, numeric referent, value role, genericity,
  attribution, valid time.
- **Where the extra value comes from** — Disambiguation: condition with referent with unit dimension (prototype 1).
- **Records accepted after it** — Qualified claims carrying four confidence types
- **Front-end impact** — Conditions often sit in footnotes, table notes or captions on another page. Docling must
  preserve those links and the reading order across page breaks, or condition scope loses its candidates.
- **Gate to next stage** — About 200 hand-labelled sentences per qualifier at matched coverage; a positive
  disambiguation term for prototype 1; calibrated interpretation confidence per qualifier.
- **Test before next stage** — A hand-labelled sample of about 200 sentences per qualifier, the same sample the gate
  uses. Composition covers this tier only partly, so measure before trusting it.
- **Streams** — [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce)
- **Combinations unlocked** — [5.1](stream-combinations.md#notion-409141b583698178ba75c0b0f79c26a0),
  [5.2](stream-combinations.md#notion-409141b58369815e9c4ed0a3aa10d0e0),
  [5.3](stream-combinations.md#notion-409141b5836981ae802df3160a2e0f55),
  [5.4](stream-combinations.md#notion-409141b58369810ebfe5fc4145cd7165),
  [5.5](stream-combinations.md#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](stream-combinations.md#notion-409141b5836981168731d030ef9a6660),
  [5.7](stream-combinations.md#notion-409141b5836981cbaebef8203488d6ba),
  [5.8](stream-combinations.md#notion-409141b5836981a08f23f3d5626b12da),
  [5.9](stream-combinations.md#notion-409141b583698123a463c42c912a6042),
  [5.10](stream-combinations.md#notion-409141b5836981c58169e46a89b8ac6c),
  [5.11](stream-combinations.md#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Decisions** — [Polarity](decision-types.md#notion-40a141b5836981f0b698fd9a751c3540), [Author
  modality](decision-types.md#notion-40a141b5836981bc9cedcc12b2557115), [Condition
  scope](decision-types.md#notion-40a141b5836981ee8bdbc9ab27aac913), [Numeric
  referent](decision-types.md#notion-40a141b58369817da69becef271f7f4c), [Value
  role](decision-types.md#notion-40a141b5836981538fafda1bbecb4339),
  [Genericity](decision-types.md#notion-40a141b583698104b845f1f342fe07ef),
  [Attribution](decision-types.md#notion-40a141b583698150be1addc307c03107), [Valid
  time](decision-types.md#notion-40a141b5836981e6b3c9d09b73d402d0)
- **Templates** — [Numeric reference and value
  role](inference-templates.md#notion-40a141b58369814c9058f2d9adbaf84b), [Condition scope and
  qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Open questions** — [Is the labelling budget for the stage gates
  realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Qualification is where
  CPU coverage is partial](design-questions-and-decisions.md#notion-40b141b58369815ca1b7df1b499c9306), [Conditions
  rest on thin evidence](design-questions-and-decisions.md#notion-40b141b5836981ae9becc156c7c8ccff), [Bridging and
  abstract reference are unsolved in
  general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [Atomic claims:
  Gemma-APS removed, replaced by the CPU LLM claim pass through
  LangExtract](design-questions-and-decisions.md#notion-40b141b5836981c2a8e4d69055783b23), [Conditions get an
  explicit route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit
  conditions](design-questions-and-decisions.md#notion-40b141b58369813196e2f5470bb81336), [Bridging and abstract
  anaphora go to the CPU LLM with candidate antecedents and a none
  option](design-questions-and-decisions.md#notion-40b141b5836981ed83b0c876eff6dc0e), [The qualified claim carries
  four separate kinds of confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e),
  [The central hypothesis is tested first on three prototypes with generative calls disabled, against six
  baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a), [Generative calls stay off
  until the stage-5 baseline is
  measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612), [How does the interpretation
  layer relate to the repository's existing confidence
  design?](design-questions-and-decisions.md#notion-40a141b58369811ca1eff277ad4edd45), [What is λ, the CPU-seconds
  worth one extra correct record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8),
  [Should templates use pgmpy or the prototype's own exact
  solver?](design-questions-and-decisions.md#notion-40a141b5836981689075d6d5d126d651), [Is the labelling budget for
  the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd), [Should
  the numeric-reference prototype generate the operating-variable option its decision type
  names?](design-questions-and-decisions.md#notion-40b141b5836981c4bce8f69e6d6412ab)

Tier page: [5️⃣ Tier 5 · Qualification](https://app.notion.com/p/40b141b58369816a8312f6ff6cbe4968). This row carries the staged plan's "Stage 5: qualification (prototype 1 completes)" in full and the pipeline page's build-order row 5. The models, combinations, streams, outcomes, gate and test are in the properties above.

### Detail

#### Decisions

Polarity, author modality, condition scope (which proposition it governs), numeric referent ("this pressure"), value role (measured, rated, predicted, required), genericity, attribution and valid time.

#### Factors

- Condition scope × numeric referent × unit dimension × frame role: the prototype 1 template that resolves the pump example on CPU ([🔬 Worked example: one passage through the tiers](https://app.notion.com/p/40b141b583698129b75bf8c46cd01965)).
- Value role × section role (from stage 1) × cue words: a Results section with "was tested" favours measured; "rating" favours rated.
- Genericity × instance vs class (from stage 3) × determiner and tense.
- Dipo condition links enter as soft evidence only.

#### Four confidence types are assigned here

- Author modality is a decision variable, read from the source.
- Interpretation confidence is the posterior marginal from the joint model.
- Source reliability comes from stage 1's grade and the evidence basis.
- Corpus support is left empty until stage 7.

#### Records and value

The qualified claim (5.11), with lineage, coherent alternatives and the four quantities.

#### Measured: the first full decomposition

With eight stream groups in place, compute $V$ on all 256 subsets over cached layers. Report the gain split into assembly, disambiguation and coverage; group Shapley values; and pairwise interaction indices, with cluster-bootstrap intervals. This is the evidence for or against the central hypothesis. The method: [📏 Measuring the synergy](https://app.notion.com/p/40b141b58369815e898fd46f2b34bfdd).

#### The LLM decision

Now switch the CPU LLM on as a ninth group, for the claim pass and for decisions whose EVI exceeds $\lambda$ times its cost. Its Shapley value and its interaction with each group show where it adds value and where it duplicates CPU inference. Keep it only for the record types where its utility per CPU-second is positive.

#### Gate to stage 6

About 200 hand-labelled sentences per qualifier, at matched coverage. A positive disambiguation term for prototype 1. Calibrated interpretation confidence per qualifier.

The build order's test uses the same 200-sentence sample and adds a warning: composition covers this tier only partly, so measure before trusting it.

#### Prototype

Prototype 1 completes here: quantities, value roles, conditions and numeric references. It combines quantity extraction, syntax, local references, units, property definitions and frame roles, and measures whether it reconstructs which entity and property a quantity concerns, whether the value is measured, rated, predicted or required, which condition governs it, and what references such as "this pressure" denote. See [🧪 Prototypes, baselines and measurement](https://app.notion.com/p/40b141b583698119a17ad60732732306).

#### Changes from the original build order

- Dipo is kept as a soft feature only, never a gate: DMRST-400M scores 53.2 full Parseval on RST-DT, at the CPU frontier, but about half the labelled relations are wrong (audit, 30 October 2026).
- Conditions now come from condition-clause labels added at stage 2, scoped by the parse, with Dipo links as candidates and the CPU LLM for implicit conditions.

### Open questions and decisions

- [Is the labelling budget for the stage gates realistic?](design-questions-and-decisions.md#notion-40a141b5836981719278c69d7afb8cfd)
- [What is λ, the CPU-seconds worth one extra correct record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8)
- [How does the interpretation layer relate to the repository's existing confidence design?](design-questions-and-decisions.md#notion-40a141b58369811ca1eff277ad4edd45)
- Risks: [Qualification is where CPU coverage is partial](design-questions-and-decisions.md#notion-40b141b58369815ca1b7df1b499c9306); [Conditions rest on thin evidence](design-questions-and-decisions.md#notion-40b141b5836981ae9becc156c7c8ccff); [Bridging and abstract reference are unsolved in general](design-questions-and-decisions.md#notion-40b141b5836981f78050f33342bf74be)
- Decided: [The qualified claim carries four separate kinds of confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e); [Conditions get an explicit route: condition-clause labels, parse scope, Dipo candidates, the CPU LLM for implicit conditions](design-questions-and-decisions.md#notion-40b141b58369813196e2f5470bb81336); [Bridging and abstract anaphora go to the CPU LLM with candidate antecedents and a none option](design-questions-and-decisions.md#notion-40b141b5836981ed83b0c876eff6dc0e); [Generative calls stay off until the stage-5 baseline is measured](design-questions-and-decisions.md#notion-40b141b5836981ac9ebcc4faa4718612); [The central hypothesis is tested first on three prototypes with generative calls disabled, against six baselines](design-questions-and-decisions.md#notion-40b141b5836981de9fddceb169da1e9a)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 5: qualification (prototype 1 completes)" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 5.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): verdict row "Discourse (28)" and "Weak spots the stack already had".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [4 · Propositions and tables](#notion-40a141b5836981c1b905ff7cee627528) · Next: [6 · Argument](#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-40a141b58369817c9929cc494bc2c061"></a>

## 6 · Argument

**Status** Target · **Order** 6 · [Notion record](https://app.notion.com/p/40a141b58369817c9929cc494bc2c061)

- **What you can say afterwards** — What supports or attacks what, why each work is cited, who committed to what and
  by when.
- **Models added** — DeBERTa-v3 NLI scores on candidate claim pairs as calibrated features (entail as support,
  contradict as attack), not definitions, prioritised by Dipo links. The CPU LLM labels the top pairs once the
  stage-5 baseline is measured. This replaces ARI RoBERTa (audit, 30 Oct 2026).
- **Decisions added** — Support, attack or none for each candidate claim pair; citation function.
- **Where the extra value comes from** — NLI and discourse as calibrated features, not definitions; consistency with
  polarity and attribution from stage 5.
- **Records accepted after it** — Argument edges above their threshold
- **Front-end impact** — Citation markers and the reference list come from Docling; superscript citation numbers
  lost in PDF text extraction would break citation function.
- **Gate to next stage** — Interaction of NLI with discourse and proximity; pair candidate recall on the
  passage-sampled set.
- **Test before next stage** — Argument edges checked by hand on 10 documents.
- **Streams** — [arg](pipeline-streams.md#notion-409141b5836981ab84bffe7436ced61c)
- **Combinations unlocked** — [6.1](stream-combinations.md#notion-409141b5836981659d9af5ab527c816f),
  [6.2](stream-combinations.md#notion-409141b5836981278809fc0ca0b6cb51),
  [6.3](stream-combinations.md#notion-409141b58369816abbbffc5a400dc4c1),
  [6.4](stream-combinations.md#notion-409141b5836981558823e904a87ca9c6),
  [6.5](stream-combinations.md#notion-409141b58369816f966ce592ba2c3432),
  [6.6](stream-combinations.md#notion-409141b5836981adacd1d08814bff80e),
  [6.7](stream-combinations.md#notion-409141b58369817ab817d6f21b14eb45)
- **Decisions** — [Claim-pair relation](decision-types.md#notion-40a141b5836981f6a791cd4816270381)
- **Templates** — [Claim-pair argument](inference-templates.md#notion-40a141b5836981a28e53d4643cdf65af)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Candidate recall bounds
  every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39), [Support and
  attack: ARI RoBERTa removed, replaced by NLI pair scores, Dipo priorities and the CPU LLM on top
  pairs](design-questions-and-decisions.md#notion-40b141b5836981629293c7552893c629), [NLI is a feature for argument
  relations, not their definition](design-questions-and-decisions.md#notion-40b141b5836981648cb3d3ec67923e27)

Tier page: [6️⃣ Tier 6 · Discourse and argument](https://app.notion.com/p/40b141b58369815e9c55f6b3c8af5074). This row carries the staged plan's "Stage 6: discourse and argument" in full and the pipeline page's build-order row 6, corrected for the 30 October audit. The models, combinations, streams, outcomes, gate and test are in the properties above.

### Detail

#### Decisions

Support, attack or none for each candidate claim pair; citation function.

#### Factors

NLI entail and contradict scores as calibrated evidence (not the label itself); a Dipo-link prior; proximity; consistency with the claims' polarity and attribution from stage 5. Support and entailment remain different variables.

#### Candidates

Pairs come from discourse links, then a proximity window. Pair candidate recall is measured on the passage-sampled set, since a missed pair can never be labelled.

#### Records and value

Argument edges above $\tau$. That threshold is set high, because a wrong edge misleads more than a missing one.

#### Measured

The interaction index of NLI with discourse and proximity. If it is near zero, the NLI pass is dropped for this decision.

#### Gate to stage 7

The staged plan gives no separate gate section for stage 6; its "At a glance" row measures the interaction of NLI with discourse and proximity, and pair candidate recall. The build order adds argument edges checked by hand on 10 documents (Test before next stage).

#### Prototype

None.

#### Changes from the original build order

- ARI RoBERTa was removed. Support and attack come from DeBERTa NLI scores on claim pairs, prioritised by Dipo links, with the CPU LLM labelling the top pairs (audit, 30 October 2026).
- Citation markers and the reference list come from Docling (see Front-end impact).

### Open questions and decisions

- Risk: [Candidate recall bounds every joint decision](design-questions-and-decisions.md#notion-40b141b583698197a415f16e81d22e39)
- Decided: [Support and attack: ARI RoBERTa removed, replaced by NLI pair scores, Dipo priorities and the CPU LLM on top pairs](design-questions-and-decisions.md#notion-40b141b5836981629293c7552893c629); [NLI is a feature for argument relations, not their definition](design-questions-and-decisions.md#notion-40b141b5836981648cb3d3ec67923e27)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 6: discourse and argument" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 6.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "Filling the gaps the removals leave".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [5 · Qualification](#notion-40a141b583698172b462e8ef1e246de3) · Next: [7 · Corpus](#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-40a141b58369816a9c70f23c650234aa"></a>

## 7 · Corpus

**Status** Target · **Order** 7 · [Notion record](https://app.notion.com/p/40a141b58369816a9c70f23c650234aa)

- **What you can say afterwards** — Corpus-wide entities and citation graph; equivalent claims; genuine
  contradictions; independent support; drift; faithfulness of citations; edition differences; event timelines;
  senses; terminology; value distributions; requirement compliance.
- **Models added** — Jina embeddings v5 small for passages and for qualified claims, and Jina reranker v3.5. bm25s.
  Splink for cross-document identity, with the CPU LLM on hard pairs. BERTopic (or FASTopic) over claim embeddings.
  Sense discrimination defaults to one sense per term per corpus; a split needs well-separated clusters and a
  supporting definition in the corpus, confirmed by the LLM (audit, 30 Oct 2026).
- **Decisions added** — Cross-document identity, claim equivalence, contradiction, provenance groups, residual
  correlation ρ.
- **Where the extra value comes from** — Corpus aggregation with a dependence discount; closure over condition
  intervals.
- **Records accepted after it** — Support with provenance groups; contradictions; drift; distributions
- **Front-end impact** — Converting every work to one published PDF up front removes most edition duplicates before
  this stage, so provenance groups need to model citation chains rather than file copies.
- **Gate to next stage** — Contradiction and equivalence precision at τ on 50 sampled cases each; sensitivity of
  accepted support to ρ.
- **Test before next stage** — Precision of contradictions, equivalences and compliance findings on 50 sampled cases
  each. Registry and citation-graph merges spot-checked.
- **Streams** — [topics](pipeline-streams.md#notion-409141b583698142b5c6e6907527d2bd),
  [splink](pipeline-streams.md#notion-409141b58369816d80fcf751582e646c),
  [emb](pipeline-streams.md#notion-409141b583698173900bfbf18657f719),
  [bm25](pipeline-streams.md#notion-409141b58369817c8ac1eb2c96d6f443),
  [rerank](pipeline-streams.md#notion-409141b5836981dab3b4fe90fc6c4087),
  [claim\_emb](pipeline-streams.md#notion-409141b5836981e4b650dbcd7ea604e1)
- **Combinations unlocked** — [7.1](stream-combinations.md#notion-409141b5836981c6ac16d8729eef6ad4),
  [7.2](stream-combinations.md#notion-409141b5836981ee83cbe564b02d71a9),
  [7.3](stream-combinations.md#notion-409141b58369812bbebfe671f59c4652),
  [7.4](stream-combinations.md#notion-409141b5836981e48095d7500fdf9852),
  [7.5](stream-combinations.md#notion-409141b583698180ae49d9c346699f52),
  [7.6](stream-combinations.md#notion-409141b5836981899757c0aeaa4f13ea),
  [7.7](stream-combinations.md#notion-409141b5836981f2ae3ae3df3991a162),
  [7.8](stream-combinations.md#notion-409141b5836981089c71d766491f7851),
  [7.9](stream-combinations.md#notion-409141b583698134a9a9cfe2691144f0),
  [7.10](stream-combinations.md#notion-409141b58369813d9268ee4edaaf939b),
  [7.11](stream-combinations.md#notion-409141b583698164b2dbed3f8bc47885),
  [7.12](stream-combinations.md#notion-409141b58369817baf69c933ae76405d),
  [7.13](stream-combinations.md#notion-409141b58369817891f7d4dd5dd2e46b),
  [7.14](stream-combinations.md#notion-409141b583698124ae54c5b01ed5d035),
  [7.15](stream-combinations.md#notion-409141b583698126969bdfc3be180171),
  [7.16](stream-combinations.md#notion-409141b58369811cbf3eedd9e3e6fbae)
- **Components** — [Corpus support](interpretation-components.md#notion-40a141b583698168b58bcfd2a9183839)
- **Decisions** — [Cross-document identity](decision-types.md#notion-40a141b5836981e9bdc5e3b47dc91437), [Claim
  equivalence](decision-types.md#notion-40a141b5836981bf9a1cd380fd6d7492)
- **Templates** — [Cross-document identity and
  support](inference-templates.md#notion-40a141b583698170bb84d92ee407418e)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Sense discrimination
  defaults to one sense per term per
  corpus](design-questions-and-decisions.md#notion-40b141b58369814ea375fd1c47b4c271), [The qualified claim carries
  four separate kinds of confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e),
  [Provenance groups replace assumed independence in corpus support
  (7.5)](design-questions-and-decisions.md#notion-40b141b58369814fab5de71fe2849af1), [Claim embeddings come after
  the qualified claim](design-questions-and-decisions.md#notion-40b141b5836981bd8742d2195fc16a53), [Seven
  combinations were added in the pre-publication
  review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360), [How does the interpretation
  layer relate to the repository's existing confidence
  design?](design-questions-and-decisions.md#notion-40a141b58369811ca1eff277ad4edd45), [When does a shared-error
  model (Pyro) earn its place?](design-questions-and-decisions.md#notion-40a141b5836981d498a6c47dc7105a8a), [How is
  the residual correlation ρ between provenance groups set before it is
  measured?](design-questions-and-decisions.md#notion-40b141b5836981468d31ce8deb070e18), [Do the corpus-support
  parameters in the reference code mean what the derivation
  defines?](design-questions-and-decisions.md#notion-40b141b5836981d794fafbde9626cc97), [Which method handles
  corpus-level coupling: probabilistic soft logic or Markov
  logic?](design-questions-and-decisions.md#notion-40b141b5836981fe87ddf60ddd1995e2)

Tier page: [7️⃣ Tier 7 · Corpus](https://app.notion.com/p/40b141b5836981609797fe6385b80b5c). This row carries the staged plan's "Stage 7: corpus" in full and the pipeline page's build-order row 7, corrected for the 30 October audit. The models, combinations, streams, outcomes, gate and test are in the properties above. The formal treatment of corpus support is on [📚 Corpus evidence](https://app.notion.com/p/40b141b5836981c48348e0fc536bce5b).

### Detail

#### Decisions

Cross-document identity, claim equivalence, contradiction, provenance groups, residual correlation $\rho$.

#### Cross-document identity

Splink's Fellegi–Sunter match weights are already log-likelihood ratios, so they enter the joint model unchanged.

#### Claim equivalence and contradiction

Equivalence uses retrieval candidates plus NLI evidence. Contradiction is the product of same-proposition, opposite-polarity and overlapping-condition events, replaced by the lineage probability where those readings share a decision. Interval overlap itself is deterministic.

#### Support

Group statements into provenance groups by citation roots and shared metadata. Combine them with the mixture per group and the effective count:

$$
\Lambda_g = \pi_g r_g + (1 - \pi_g), \qquad k_{\text{eff}} = \frac{k}{1 + (k - 1)\rho}
$$

Estimate $\rho$ from shared authors, datasets and instruments, or start conservatively at a fixed value until measured.

#### Escalate the model only on evidence

Add probabilistic soft logic only if corpus-level coupling (type consistency, claim-group consistency) measurably improves $V$. Add a Dawid–Skene or Pyro reliability model only if source error rates vary enough to change accepted records.

#### Records and value

Corpus support with its provenance groups, contradictions, drift and value distributions. This fills the fourth confidence type on each qualified claim.

#### Measured

Contradiction and equivalence precision at $\tau$ on 50 sampled cases each, and the sensitivity of accepted support to $\rho$. If small changes in $\rho$ flip many acceptances, $\rho$ is measured before results are relied on.

#### Gate to stage 8

The staged plan gives no separate gate section for stage 7; the measurements above are its gate. The build order adds compliance findings to the 50-case precision check and spot-checks of registry and citation-graph merges (Test before next stage).

#### Prototype

None.

#### Changes from the original build order

- Sense discrimination defaults to one sense per term per corpus; splits need evidence (audit, 30 October 2026).
- Cross-document identity sends hard pairs to the CPU LLM: LLM pair judges score 98–99 F1 on OpenSanctions pairs vs 91.3 for nomenklatura; xCoRe, which this route replaced, managed 42.4 on ECB+.
- Converting every work to one published PDF removes most edition duplicates before this stage, so provenance groups need to model citation chains rather than file copies (see Front-end impact).

### Open questions and decisions

- [How is the residual correlation ρ between provenance groups set before it is measured?](design-questions-and-decisions.md#notion-40b141b5836981468d31ce8deb070e18)
- [Which method handles corpus-level coupling: probabilistic soft logic or Markov logic?](design-questions-and-decisions.md#notion-40b141b5836981fe87ddf60ddd1995e2)
- [When does a shared-error model (Pyro) earn its place?](design-questions-and-decisions.md#notion-40a141b5836981d498a6c47dc7105a8a)
- [Do the corpus-support parameters in the reference code mean what the derivation defines?](design-questions-and-decisions.md#notion-40b141b5836981d794fafbde9626cc97)
- Decided: [Provenance groups replace assumed independence in corpus support (7.5)](design-questions-and-decisions.md#notion-40b141b58369814fab5de71fe2849af1); [Sense discrimination defaults to one sense per term per corpus](design-questions-and-decisions.md#notion-40b141b58369814ea375fd1c47b4c271); [Claim embeddings come after the qualified claim](design-questions-and-decisions.md#notion-40b141b5836981bd8742d2195fc16a53); [The qualified claim carries four separate kinds of confidence](design-questions-and-decisions.md#notion-40b141b5836981bb9b40e96dbe01c03e); [Seven combinations were added in the pre-publication review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360)

### Evidence

- [Greenberg 2009, how citation distortions create unfounded authority (BMJ)](https://doi.org/10.1136/bmj.b2680)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 7: corpus" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 7.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "Weak spots the stack already had".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [6 · Argument](#notion-40a141b58369817c9929cc494bc2c061) · Next: [8 · Ontology](#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-40a141b58369811992a0c8007723a20b"></a>

## 8 · Ontology

**Status** Target · **Order** 8 · [Notion record](https://app.notion.com/p/40a141b58369811992a0c8007723a20b)

- **What you can say afterwards** — Induced concepts, hierarchy, predicates with type signatures,
  generic-to-instance conflicts, record frames, constraints, and growth proposals with evidence.
- **Models added** — AMIE, sheXer, LogMap with OAK and SSSOM, KGCL and ROBOT. Their outputs stay proposals.
- **Decisions added** — Proposal accept or reject.
- **Where the extra value comes from** — Support log-odds from stage 7 plus compatibility with v0.
- **Records accepted after it** — Reviewed proposals; ontology v1
- **Front-end impact** — None expected.
- **Gate to next stage** — Change in V from v0 to v1 on held-out documents.
- **Test before next stage** — Expert review of the top proposals and generic-to-instance flags. Accepted proposals
  enter the next ontology version; nothing induced is used as accepted knowledge before that.
- **Streams** — [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Combinations unlocked** — [8.1](stream-combinations.md#notion-409141b58369812f99dbca796e5f7325),
  [8.2](stream-combinations.md#notion-409141b583698116887fda3ca1c5566d),
  [8.3](stream-combinations.md#notion-409141b5836981d2a263cc95f5409062),
  [8.4](stream-combinations.md#notion-409141b5836981c7b5f2fdf4e0df8cc6),
  [8.5](stream-combinations.md#notion-409141b5836981699240de5dc69f0539),
  [8.6](stream-combinations.md#notion-409141b583698145b882e140fad3deb7),
  [8.7](stream-combinations.md#notion-409141b5836981f5a2e5dd0134042a82),
  [8.8](stream-combinations.md#notion-409141b583698140a9f9f1491758b832)
- **Decisions** — [Ontology proposal](decision-types.md#notion-40a141b58369812687cec708fdb42419)
- **Templates** — [Ontology proposal scoring](inference-templates.md#notion-40a141b5836981e5ae24d4776483ac13)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Ontology expectations
  can coerce readings into existing
  categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020), [The versioned seed
  ontology is an input from tier 1; tier 8 only proposes reviewed
  changes](design-questions-and-decisions.md#notion-40b141b5836981cfb1fef9641df32bed), [Seven combinations were
  added in the pre-publication review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360)

Tier page: [8️⃣ Tier 8 · Ontology](https://app.notion.com/p/40b141b5836981608228e6dd588f6b21). This row carries the staged plan's "Stage 8: ontology proposals" in full and the pipeline page's build-order row 8. The models, combinations, streams, outcomes, gate and test are in the properties above. The seed ontology itself: [🌱 L1 · Seed ontology](https://app.notion.com/p/40b141b5836981b796e0e48ade290791).

### Detail

#### Decisions

Proposal accept or reject.

#### Score

Each proposal gets the support log-odds from stage 7 plus a compatibility term against v0: does it contradict accepted hierarchy, signatures or constraints? Each is classified as a hard constraint, logical rule, soft expectation or open possibility.

#### Acceptance

Review accepts proposals into v1. Accepting changes the ontology version in every affected cache key, so only the factors and records that depend on the changed content are recomputed.

#### Guard against self-confirmation

The effect of v1 on $V$ is measured on held-out documents that did not contribute to the proposals. A gain that appears only on the inducing documents is the extractions confirming themselves.

#### Records and value

Reviewed proposals; ontology v1.

#### Gate to stage 9

Change in $V$ from v0 to v1 on held-out documents. The build order adds expert review of the top proposals and generic-to-instance flags; accepted proposals enter the next ontology version, and nothing induced is used as accepted knowledge before that (Test before next stage).

#### Prototype

None.

#### Changes from the original build order

None from the audit. Tier 8 now only proposes changes to a seed ontology supplied from tier 1 (interpretation-layer review, 30 October 2026).

### Open questions and decisions

- [Which ontology becomes seed ontology v0, and in what format?](design-questions-and-decisions.md#notion-40a141b5836981a68cf6f8e9e81ff8ed)
- Risk: [Ontology expectations can coerce readings into existing categories](design-questions-and-decisions.md#notion-40b141b58369815cbd37d4c54d84e020)
- Decided: [The versioned seed ontology is an input from tier 1; tier 8 only proposes reviewed changes](design-questions-and-decisions.md#notion-40b141b5836981cfb1fef9641df32bed); [Seven combinations were added in the pre-publication review](design-questions-and-decisions.md#notion-40b141b58369814ea368f4dead11a360)

### Evidence

- [Roller et al. 2018, Hearst patterns revisited](https://arxiv.org/abs/1806.03191)
- LogMap scores 0.64 F1 on the OAEI 2025 Conference track (audit).

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 8: ontology proposals" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 8.

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [7 · Corpus](#notion-40a141b58369816a9c70f23c650234aa) · Next: [9 · Records and control](#notion-40a141b5836981469da5da987927234f)

<a id="notion-40a141b5836981469da5da987927234f"></a>

## 9 · Records and control

**Status** Target · **Order** 9 · [Notion record](https://app.notion.com/p/40a141b5836981469da5da987927234f)

- **What you can say afterwards** — Complete, validated, calibrated records, and an audit of what extraction missed.
- **Models added** — Validators: OWL-RL for adopted entailments, pySHACL for shape validation, units and formulas
  for consistency (with Z3, Pydantic and pandera). MAPIE (in use from stage 1 for conformal candidate sets),
  cleanlab and Crowd-Kit. ppi\_py for audit estimates. The CPU LLM for empty slots and the residue, with NuExtract3
  folded into it: template slots go through the same LLM with the record schema via LangExtract (audit, 30 Oct
  2026).
- **Decisions added** — Slot fills, escalation actions.
- **Where the extra value comes from** — Expected value of information, with λ per CPU-second.
- **Records accepted after it** — Complete, validated, calibrated records
- **Front-end impact** — A new escalation action becomes available: re-converting one page region with Docling at
  higher resolution or with OCR forced, chosen by EVI like any other action.
- **Gate to next stage** — Utility U per CPU-second; PPI estimates of corpus-wide precision and recall.
- **Test before next stage** — Completeness-audit rate. Share of items sent to the LLM: the build order said it
  should stay small; the staged plan reports it as an output of the EVI rule, not a target.
- **Streams** — [nuextract](pipeline-streams.md#notion-409141b5836981118a62f0e02a3decf6),
  [llm](pipeline-streams.md#notion-409141b58369819ab6edc5170de5803d),
  [valid](pipeline-streams.md#notion-409141b5836981f6b33dcd95abe6ee43)
- **Combinations unlocked** — [9.1](stream-combinations.md#notion-409141b583698118b18ef02258134fbe),
  [9.2](stream-combinations.md#notion-409141b58369814cb018c684b83a279a),
  [9.3](stream-combinations.md#notion-409141b58369812aa816deef834ae4b1),
  [9.4](stream-combinations.md#notion-409141b583698193b6b1fb915cf7b4a9),
  [9.5](stream-combinations.md#notion-409141b5836981a699b4eb88173cf9c3),
  [9.6](stream-combinations.md#notion-409141b5836981fdb517c06be042bcd3)
- **Open questions** — [What is λ, the CPU-seconds worth one extra correct
  record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8)
- **Questions and decisions** — [Errors compound along long chains of
  combinations](design-questions-and-decisions.md#notion-40b141b58369814aa8ffdf89dedaadda), [Template slots:
  NuExtract3 folded into the CPU LLM](design-questions-and-decisions.md#notion-40b141b583698114a698ce768680c79b),
  [Which heavier reader re-reads pages that Docling grades
  low?](design-questions-and-decisions.md#notion-40b141b583698146965ffce689a21969), [Complete cache keys and
  targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76), [The eight
  hard capability families get structured routes before
  generation](design-questions-and-decisions.md#notion-40b141b5836981fcb557f44444ff4419), [What is λ, the
  CPU-seconds worth one extra correct
  record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8), [How much of each hard
  capability family do the structured routes reconstruct before the CPU LLM
  composes?](design-questions-and-decisions.md#notion-40b141b5836981b29a4ce65382f99912)

Tier page: [9️⃣ Tier 9 · Records and control](https://app.notion.com/p/40b141b58369816889cad569803d6209). This row carries the staged plan's "Stage 9: records and control" in full and the pipeline page's build-order row 9, corrected for the 30 October audit. The models, combinations, streams, outcomes, gate and test are in the properties above. After stage 9 the design runs as one loop: [🔁 The finished loop and release checks](https://app.notion.com/p/40b141b5836981939830fb1a4f1aa16a).

### Detail

#### Decisions

Slot fills, escalation actions.

#### Acceptance

Complete records are accepted at $\tau_r$ using lineage probabilities. Validators run in their own roles: OWL-RL for adopted entailments, pySHACL for shape, units and formulas for consistency.

#### Escalation

Every remaining action (targeted extraction, region re-conversion, CPU LLM, human review) is chosen by EVI per unit cost against $\lambda$. The LLM's share of items is reported as an output of that rule, not a target. The formal rule: [⚖️ Acceptance and escalation](https://app.notion.com/p/40b141b5836981f7ac70e9d7fa7cef88).

#### Quality estimates

Use cleanlab on the gold sample to find label errors before they skew calibration. Use ppi\_py for corpus-wide precision and recall estimates, with documents as the sampling unit.

#### Records and value

Complete, validated, calibrated records.

#### Measured

Utility $U$ per CPU-second, and its change from stage 5 onward.

#### Gate

Stage 9 is the last stage. Its measures are $U$ per CPU-second and PPI estimates of corpus-wide precision and recall. The build order adds the completeness-audit rate and the share of items sent to the LLM (Test before next stage). The build order said that share should stay small; the staged plan (31 October) reports it as an output of the EVI rule, not a target, and the newer wording holds.

#### Prototype

None.

#### Changes from the original build order

- NuExtract3 was folded into the CPU LLM: template slots go through the same LLM with the record schema via LangExtract (audit, 30 October 2026).
- Region re-conversion with Docling becomes an escalation action (see Front-end impact).

### Open questions and decisions

- [What is λ, the CPU-seconds worth one extra correct record?](design-questions-and-decisions.md#notion-40a141b5836981238197f12f6cd8dda8)
- [Which heavier reader re-reads pages that Docling grades low?](design-questions-and-decisions.md#notion-40b141b583698146965ffce689a21969)
- Decided: [Template slots: NuExtract3 folded into the CPU LLM](design-questions-and-decisions.md#notion-40b141b583698114a698ce768680c79b); [The eight hard capability families get structured routes before generation](design-questions-and-decisions.md#notion-40b141b5836981fcb557f44444ff4419); [Complete cache keys and targeted re-extraction](design-questions-and-decisions.md#notion-40b141b5836981d8b9d7fd804422ee76)

### Sources

- [Staged plan for multiplicative value from the parsers](https://claude.ai/artifact/VRXzynqkkMAg8d4m4Yjorp): "Stage 9: records and control" and "At a glance".
- [🪜 Layered CPU pipeline: sequencing and stream synthesis](https://app.notion.com/p/409141b583698180bb75ed60b359931a): "Build order: adding models in stages", row 9.
- [CPU content processing stack audit](https://claude.ai/artifact/51cN5iYByzCjfnutuiJnUk): "The revised set by build stage".

Up: [Stages](https://app.notion.com/p/1bc8de53205b4b34b204346e988ce448) · Previous: [8 · Ontology](#notion-40a141b58369811992a0c8007723a20b)
