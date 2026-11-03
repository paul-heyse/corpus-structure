# Stream combinations

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/42ae10c108cd40bbb39a0660224e1b85?pvs=204) · [First production milestone](../first-production-milestone.md)

Run wave describes scheduling in the earlier capability map. Tier and order describe design grouping. Builds on and
Feeds retain the source’s lineage in each direction. All 84 rows in this snapshot are Proposed. The
numeric-reference example has a separately documented prototype under Inference templates.

[Tier 1 Framing (9)](#group-tier-1-framing) · [Tier 2 Span inventory (10)](#group-tier-2-span-inventory) · [Tier 3 Identity (8)](#group-tier-3-identity) · [Tier 4 Propositions (9)](#group-tier-4-propositions) · [Tier 5 Qualification (11)](#group-tier-5-qualification) · [Tier 6 Discourse and argument (7)](#group-tier-6-discourse-and-argument) · [Tier 7 Corpus (16)](#group-tier-7-corpus) · [Tier 8 Ontology (8)](#group-tier-8-ontology) · [Tier 9 Records and control (6)](#group-tier-9-records-and-control)

<a id="group-tier-1-framing"></a>

## Tier 1 Framing

<a id="notion-409141b58369811d8402c5783b88a812"></a>

### 1.1 · Language-routed units

**Status** Proposed · **Order** 101 · **Run wave** 3 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b58369811d8402c5783b88a812)

- **Join key** — Block ID, sentence ID
- **What it lets you say** — Language and script for every block and sentence, so mixed-language documents are
  handled block by block. Each unit goes to the right model variant (GLiNER multi vs base, CorPipe vs Maverick). The
  English-only models (CQE, ReFinED, the PII detectors) get pivot translation or skip the unit; the CPU LLM handles
  claims and argument labels in other languages directly.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [lang](pipeline-streams.md#notion-409141b5836981ab9afaeb69b5d5ae32),
  [sents](pipeline-streams.md#notion-409141b5836981658aa5f249c86d3e7a),
  [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130)
- **Capabilities** — [S4](https://app.notion.com/p/409141b5836981acad4fc8ebb5b6b8d2)
- **Free check** — Detected language vs the language declared in metadata
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b5836981f888d4df9c58419c9a"></a>

### 1.2 · Reliability map

**Status** Proposed · **Order** 102 · **Run wave** 2 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b5836981f888d4df9c58419c9a)

- **Join key** — Block ID
- **What it lets you say** — A reliability grade per block (born-digital, clean OCR, garbled), inherited as a prior
  by every later output from that block. Garbled blocks are flagged for re-OCR, a GPU step outside this CPU
  pipeline, or excluded, instead of polluting later layers.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [quality](pipeline-streams.md#notion-409141b5836981599a32fb76e77c07a7),
  [canon](pipeline-streams.md#notion-409141b58369818a84addd332566fbb1)
- **Feeds** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [S3](https://app.notion.com/p/409141b5836981859f8ec1e6560411c9),
  [V6](https://app.notion.com/p/409141b5836981e4bf8df013f685969b)
- **Free check** — Font and character-box anomalies vs quality score
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b583698102ac89ed4c7f82ea8a"></a>

### 1.3 · Clean reading units

**Status** Proposed · **Order** 103 · **Run wave** 2 · **Downstream reach** 71 · [Notion record](https://app.notion.com/p/409141b583698102ac89ed4c7f82ea8a)

- **Join key** — Block ID, sentence ID
- **What it lets you say** — Sentences that never cross block boundaries; captions, footnotes, list items and cells
  kept as their own units; running heads and page furniture excluded from prose models; a list's lead-in ('the
  following conditions:') bound to its items so they read as one statement.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [sents](pipeline-streams.md#notion-409141b5836981658aa5f249c86d3e7a),
  [canon](pipeline-streams.md#notion-409141b58369818a84addd332566fbb1)
- **Feeds** — [1.5](#notion-409141b5836981499080ff4fc4c8a20e), [1.6](#notion-409141b5836981ef9825f3632387207c),
  [2.1](#notion-409141b5836981e88660f3eede7253ac), [2.10](#notion-409141b5836981e7a84bc95247b126b1),
  [3.1](#notion-409141b5836981f69dc4e1260c26c827), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [9.3](#notion-409141b58369812aa816deef834ae4b1)
- **Capabilities** — [S2](https://app.notion.com/p/409141b5836981e38c73ee6e3e42b0d2),
  [S5](https://app.notion.com/p/409141b5836981b59cc3dcabeecc8e53),
  [D4](https://app.notion.com/p/409141b5836981cb8947c4e965fc4130)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b58369816b8a55d644257d2e23"></a>

### 1.4 · Section roles

**Status** Proposed · **Order** 104 · **Run wave** 5 · **Downstream reach** 59 · [Notion record](https://app.notion.com/p/409141b58369816b8a55d644257d2e23)

- **Join key** — Section path
- **What it lets you say** — Every section labelled with its function (background, method, result, discussion,
  limitation, definitions, requirements, procedure, appendix, references), so each sentence inherits a rhetorical
  prior: a number in Results is likely a measurement; the same number in the Introduction is likely cited
  background. Used as a weighted feature, not a gate.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [genre](pipeline-streams.md#notion-409141b58369818abe2beb2ce219c7f8)
- **Feeds** — [1.9](#notion-409141b5836981369becef06b4f81df0), [2.5](#notion-409141b58369813fb393ea90313ceb6a),
  [3.7](#notion-409141b583698138a0dcedcd6df44e85), [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0),
  [5.9](#notion-409141b583698123a463c42c912a6042), [5.7](#notion-409141b5836981cbaebef8203488d6ba),
  [6.3](#notion-409141b58369816abbbffc5a400dc4c1)
- **Capabilities** — [A1](https://app.notion.com/p/409141b5836981eebb55ce2b091c7230)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b5836981499080ff4fc4c8a20e"></a>

### 1.5 · Citation contexts

**Status** Proposed · **Order** 105 · **Run wave** 3 · **Downstream reach** 29 · [Notion record](https://app.notion.com/p/409141b5836981499080ff4fc4c8a20e)

- **Join key** — Citation marker, sentence ID, reference ID
- **What it lets you say** — Each citing sentence tied to the reference entry and identifier (DOI) it cites, and
  each sentence marked as carrying borrowed content or not. This is the raw material for attribution, evidence
  basis, citation function and the corpus citation graph.
- **Streams used** — [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130)
- **Builds on** — [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [7.2](#notion-409141b5836981ee83cbe564b02d71a9), [5.6](#notion-409141b5836981168731d030ef9a6660),
  [6.4](#notion-409141b5836981558823e904a87ca9c6)
- **Capabilities** — [D10](https://app.notion.com/p/409141b5836981539d11daa4246b656b)
- **Free check** — Markers with no resolvable reference entry
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b5836981ef9825f3632387207c"></a>

### 1.6 · Resolved pointers

**Status** Proposed · **Order** 106 · **Run wave** 3 · **Downstream reach** 49 · [Notion record](https://app.notion.com/p/409141b5836981ef9825f3632387207c)

- **Join key** — Block ID
- **What it lets you say** — 'Table 3', 'Eq. (4)', 'the figure above' and 'the following steps' bound to the actual
  block, so text that talks about a table or formula can be joined with that table's cells or that formula's tree.
- **Streams used** — [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [tables](pipeline-streams.md#notion-409141b583698117b2e1c0b7067f2537),
  [formula](pipeline-streams.md#notion-409141b583698127815fd85f864c0fdd)
- **Builds on** — [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [2.3](#notion-409141b58369815fac36e5072a1d652d), [4.5](#notion-409141b5836981508daff27e73a7bfeb)
- **Capabilities** — [D9](https://app.notion.com/p/409141b5836981788a4aebe4fc1a5a28)
- **Free check** — Pointers to blocks that do not exist
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b58369810e838eefea6cb5ef86"></a>

### 1.7 · Reference time

**Status** Proposed · **Order** 107 · **Run wave** 1 · **Downstream reach** 44 · [Notion record](https://app.notion.com/p/409141b58369810e838eefea6cb5ef86)

- **Join key** — Document ID, message ID
- **What it lets you say** — A reference time for every unit (publication date, message date, revision time), so
  'last year', 'yesterday' and 'the previous version' can later be turned into absolute dates.
- **Streams used** — [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [threads](pipeline-streams.md#notion-409141b5836981eb92d9d7bb774895d8),
  [revs](pipeline-streams.md#notion-409141b58369818f9d2ffe8a835017b2),
  [canon](pipeline-streams.md#notion-409141b58369818a84addd332566fbb1)
- **Feeds** — [1.8](#notion-409141b58369816b8ce0fb40bdc774ac), [2.9](#notion-409141b5836981e6a150e244f5f25270),
  [7.2](#notion-409141b5836981ee83cbe564b02d71a9), [7.8](#notion-409141b5836981089c71d766491f7851),
  [7.11](#notion-409141b583698164b2dbed3f8bc47885)
- **Capabilities** — [D11](https://app.notion.com/p/409141b583698134945ac85c9cf52751)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b58369816b8ce0fb40bdc774ac"></a>

### 1.8 · Edition lineage

**Status** Proposed · **Order** 108 · **Run wave** 2 · **Downstream reach** 7 · [Notion record](https://app.notion.com/p/409141b58369816b8ce0fb40bdc774ac)

- **Join key** — Block hash, duplicate-cluster ID
- **What it lets you say** — Exact duplicate blocks recognized by hash and processed once. Near-duplicate documents
  (editions, drafts, excerpts) recorded as variants of each other, with only their differing blocks sent through the
  expensive models.
- **Streams used** — [dedup](pipeline-streams.md#notion-409141b5836981f59f41c0ed9052e70b),
  [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [revs](pipeline-streams.md#notion-409141b58369818f9d2ffe8a835017b2)
- **Builds on** — [1.7](#notion-409141b58369810e838eefea6cb5ef86)
- **Feeds** — [7.2](#notion-409141b5836981ee83cbe564b02d71a9), [7.5](#notion-409141b583698180ae49d9c346699f52),
  [7.8](#notion-409141b5836981089c71d766491f7851)
- **Capabilities** — [C7](https://app.notion.com/p/409141b58369814fac13f8ed210aa394)
- **Free check** — Edition dates out of order
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-409141b5836981369becef06b4f81df0"></a>

### 1.9 · Schema routing

**Status** Proposed · **Order** 109 · **Run wave** 6 · **Downstream reach** 52 · [Notion record](https://app.notion.com/p/409141b5836981369becef06b4f81df0)

- **Join key** — Document type, section path
- **What it lets you say** — Which label sets, relation inventories (with their Wikidata property mappings) and
  record frames apply where, drawn from the accepted, versioned seed ontology: obligations for contracts,
  specifications for datasheets, findings and measurements for papers, action items for message threads. Later
  extractors then ask the right questions per section instead of all questions everywhere.
- **Streams used** — [genre](pipeline-streams.md#notion-409141b58369818abe2beb2ce219c7f8)
- **Builds on** — [1.4](#notion-409141b58369816b8a55d644257d2e23)
- **Feeds** — [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.1](#notion-409141b5836981ca8d66f08b0b61b113),
  [4.3](#notion-409141b583698169929afb2606b1c8cf), [5.8](#notion-409141b5836981a08f23f3d5626b12da)
- **Capabilities** — [C1](https://app.notion.com/p/409141b583698172a2d2e7f5e171e34b)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="group-tier-2-span-inventory"></a>

## Tier 2 Span inventory

<a id="notion-409141b5836981e88660f3eede7253ac"></a>

### 2.1 · Unified mention inventory

**Status** Proposed · **Order** 201 · **Run wave** 8 · **Downstream reach** 65 · [Notion record](https://app.notion.com/p/409141b5836981e88660f3eede7253ac)

- **Join key** — Character span
- **What it lets you say** — One reconciled mention set with a single ID per span: head word and full noun-phrase
  extent from the parse, syntactic role (subject, object), named entity vs concept from the bi-encoder's concept
  labels plus a genericity flag from the parse (bare plural or generic determiner, present tense), and type votes
  from GLiNER2.5 and the bi-encoder with an agreement level. Pronouns and other noun phrases from the parse are
  added as untyped mentions, so coreference has every candidate.
- **Streams used** — [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8),
  [concepts](pipeline-streams.md#notion-409141b58369810cb26dc09c30bf542d),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373)
- **Builds on** — [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [2.2](#notion-409141b5836981fc9364f2874585b571), [2.8](#notion-409141b5836981f4b896cf86b4998700),
  [3.1](#notion-409141b5836981f69dc4e1260c26c827), [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5),
  [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [R1](https://app.notion.com/p/409141b583698193afd0df397607d787),
  [R2](https://app.notion.com/p/409141b58369816683cadcff6514d2cd)
- **Free check** — Type disagreement rate per type (a calibration feature)
- **Evidence** — GLiNER bi-encoder large 61.5 on CrossNER (GPT-4o 59.9); parse features give 77.4% on genericity
  (Friedrich and Pinkal 2015)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981fc9364f2874585b571"></a>

### 2.2 · Values attached to entities and properties

**Status** Proposed · **Order** 202 · **Run wave** 9 · **Downstream reach** 50 · [Notion record](https://app.notion.com/p/409141b5836981fc9364f2874585b571)

- **Join key** — Referred noun phrase, dependency path
- **What it lets you say** — Each number attached to the entity and property it describes: 'the shaft diameter is 25
  mm' becomes shaft / diameter / 25 mm (0.025 m). CQE already returns the noun phrase each quantity refers to; the
  parse links that phrase to an inventory mention and a property. Ranges, tolerances and approximations stay
  attached.
- **Streams used** — [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373)
- **Builds on** — [2.1](#notion-409141b5836981e88660f3eede7253ac)
- **Feeds** — [3.8](#notion-409141b5836981aab53de3d4c1552549), [4.7](#notion-409141b5836981d48c27e6a4866db6f5),
  [4.5](#notion-409141b5836981508daff27e73a7bfeb), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4),
  [4.9](#notion-409141b583698123a216d4459f31bd6d), [5.9](#notion-409141b583698123a463c42c912a6042),
  [5.7](#notion-409141b5836981cbaebef8203488d6ba), [7.15](#notion-409141b583698126969bdfc3be180171)
- **Capabilities** — [P1](https://app.notion.com/p/409141b583698137a7adc07c92b9f7d9),
  [R3](https://app.notion.com/p/409141b58369813d818fc8e002d6a442),
  [R4](https://app.notion.com/p/409141b583698149be23e0bc40fbe5d8)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b58369815fac36e5072a1d652d"></a>

### 2.3 · Table cells in context

**Status** Proposed · **Order** 203 · **Run wave** 5 · **Downstream reach** 48 · [Notion record](https://app.notion.com/p/409141b58369815fac36e5072a1d652d)

- **Join key** — Table ID, cell
- **What it lets you say** — Every cell value with its unit (from the header, caption or table note), the table's
  global conditions ('at 20 °C'), and the text sentences that cite the table.
- **Streams used** — [tables](pipeline-streams.md#notion-409141b583698117b2e1c0b7067f2537),
  [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65)
- **Builds on** — [1.6](#notion-409141b5836981ef9825f3632387207c)
- **Feeds** — [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [7.14](#notion-409141b583698124ae54c5b01ed5d035),
  [9.3](#notion-409141b58369812aa816deef834ae4b1)
- **Capabilities** — [D6](https://app.notion.com/p/409141b5836981e0b5b0c1d5a20b79fd),
  [D8](https://app.notion.com/p/409141b5836981a1abd3fd86fee705aa)
- **Free check** — Cells whose units cannot be resolved
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981ba9b2ceeaddeb4d553"></a>

### 2.4 · Canonical terms

**Status** Proposed · **Order** 204 · **Run wave** 6 · **Downstream reach** 22 · [Notion record](https://app.notion.com/p/409141b5836981ba9b2ceeaddeb4d553)

- **Join key** — Lemma, short form
- **What it lets you say** — One term record per concept-like expression, with its variants merged: 'heat
  exchangers', 'heat-exchanger' and 'HX' become one term, and the abbreviation's scope (local or document-wide) is
  kept.
- **Streams used** — [terms](pipeline-streams.md#notion-409141b5836981ff9c1cd5300743d087),
  [abbr](pipeline-streams.md#notion-409141b583698146b66fc2dbbaf22d8e),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [concepts](pipeline-streams.md#notion-409141b58369810cb26dc09c30bf542d)
- **Feeds** — [2.5](#notion-409141b58369813fb393ea90313ceb6a), [3.4](#notion-409141b583698155b2c3f9fad114c7a1),
  [3.5](#notion-409141b5836981eeacf6fb407f615d64), [7.12](#notion-409141b58369817baf69c933ae76405d),
  [7.13](#notion-409141b58369817891f7d4dd5dd2e46b)
- **Capabilities** — [T1](https://app.notion.com/p/409141b5836981bf86bcec3dce4cafa8),
  [T2](https://app.notion.com/p/409141b583698161bfe9f830e081d2d5),
  [T4](https://app.notion.com/p/409141b58369818da2d4ec686a32e14c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b58369813fb393ea90313ceb6a"></a>

### 2.5 · Definitions with genus

**Status** Proposed · **Order** 205 · **Run wave** 8 · **Downstream reach** 19 · [Notion record](https://app.notion.com/p/409141b58369813fb393ea90313ceb6a)

- **Join key** — Term record, sentence ID
- **What it lets you say** — Definiendum-definiens pairs with the genus picked out from the parse: 'a heat exchanger
  is a device that transfers heat between fluids' gives genus 'device' and differentia 'transfers heat between
  fluids'. These are is-a seeds and the core of definition records.
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Builds on** — [2.4](#notion-409141b5836981ba9b2ceeaddeb4d553), [1.4](#notion-409141b58369816b8a55d644257d2e23)
- **Feeds** — [2.6](#notion-409141b583698165b5cccc4da90536ef), [3.8](#notion-409141b5836981aab53de3d4c1552549),
  [3.5](#notion-409141b5836981eeacf6fb407f615d64), [7.13](#notion-409141b58369817891f7d4dd5dd2e46b),
  [8.1](#notion-409141b58369812f99dbca796e5f7325), [8.2](#notion-409141b583698116887fda3ca1c5566d),
  [9.1](#notion-409141b583698118b18ef02258134fbe)
- **Capabilities** — [T3](https://app.notion.com/p/409141b5836981039f7ced71c3937105)
- **Evidence** — Copular, appositive and 'defined as' patterns
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b583698165b5cccc4da90536ef"></a>

### 2.6 · Symbol declarations

**Status** Proposed · **Order** 206 · **Run wave** 9 · **Downstream reach** 10 · [Notion record](https://app.notion.com/p/409141b583698165b5cccc4da90536ef)

- **Join key** — Symbol token, sentence ID
- **What it lets you say** — Symbols in equations bound to their declarations in the text ('where σ is the yield
  stress in MPa'), with units, giving each variable a meaning and a dimensional signature.
- **Streams used** — [formula](pipeline-streams.md#notion-409141b583698127815fd85f864c0fdd),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c)
- **Builds on** — [2.5](#notion-409141b58369813fb393ea90313ceb6a)
- **Feeds** — [3.8](#notion-409141b5836981aab53de3d4c1552549), [4.8](#notion-409141b583698120b69fe73e93207120),
  [9.1](#notion-409141b583698118b18ef02258134fbe)
- **Capabilities** — [R5](https://app.notion.com/p/409141b58369810785d0ec481da3e349),
  [S7](https://app.notion.com/p/409141b583698128bb2ffc02dadbca4b)
- **Evidence** — MathAlign
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981debac4faa03c10afea"></a>

### 2.7 · Clause cue map

**Status** Proposed · **Order** 207 · **Run wave** 6 · **Downstream reach** 41 · [Notion record](https://app.notion.com/p/409141b5836981debac4faa03c10afea)

- **Join key** — Clause (dependency subtree)
- **What it lets you say** — For every clause: tense, aspect and mood; modal verb and its type; negation cue;
  condition marker ('if', 'unless', 'provided that'); reporting verb; hedge; comparison marker, each with its
  dependency scope. Not yet attached to propositions, but every qualifier later reads from this map.
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [lex](pipeline-streams.md#notion-409141b5836981e5b923f097afd80915)
- **Feeds** — [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [5.1](#notion-409141b583698178ba75c0b0f79c26a0),
  [5.3](#notion-409141b5836981ae802df3160a2e0f55), [5.5](#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](#notion-409141b5836981168731d030ef9a6660), [5.8](#notion-409141b5836981a08f23f3d5626b12da),
  [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0)
- **Capabilities** — [Q1](https://app.notion.com/p/409141b583698194993dd77b74775d61)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981f4b896cf86b4998700"></a>

### 2.8 · Personal data, by consensus

**Status** Proposed · **Order** 208 · **Run wave** 9 · **Downstream reach** 1 · [Notion record](https://app.notion.com/p/409141b5836981f4b896cf86b4998700)

- **Join key** — Character span
- **What it lets you say** — Personal-data spans weighted by how many detectors agree, with categories from the
  55+-category detector and validated patterns from Presidio.
- **Streams used** — [pii](pipeline-streams.md#notion-409141b5836981faace1e30da5b9f38d)
- **Builds on** — [2.1](#notion-409141b5836981e88660f3eede7253ac)
- **Feeds** — [3.6](#notion-409141b5836981b6b75ce5b51efbf2dd)
- **Capabilities** — [C6](https://app.notion.com/p/409141b5836981968e81f9b88dd95f9a)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981e6a150e244f5f25270"></a>

### 2.9 · Absolute dates

**Status** Proposed · **Order** 209 · **Run wave** 5 · **Downstream reach** 41 · [Notion record](https://app.notion.com/p/409141b5836981e6a150e244f5f25270)

- **Join key** — Date span, reference time
- **What it lets you say** — Relative dates ('last quarter', 'two days later') resolved to absolute intervals using
  each unit's reference time.
- **Streams used** — [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c)
- **Builds on** — [1.7](#notion-409141b58369810e838eefea6cb5ef86)
- **Feeds** — [4.6](#notion-409141b5836981d0804fc95ca5a45fb1), [5.4](#notion-409141b58369810ebfe5fc4145cd7165),
  [6.5](#notion-409141b58369816f966ce592ba2c3432), [7.9](#notion-409141b583698134a9a9cfe2691144f0)
- **Capabilities** — [R4](https://app.notion.com/p/409141b583698149be23e0bc40fbe5d8)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-409141b5836981e7a84bc95247b126b1"></a>

### 2.10 · Implicit sections

**Status** Proposed · **Order** 210 · **Run wave** 5 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981e7a84bc95247b126b1)

- **Join key** — Paragraph, sentence ID
- **What it lets you say** — Topic boundaries in text without markup (emails, transcripts, flat text), from SaT's
  paragraph breaks and drops in lexical cohesion between neighbouring windows, TextTiling-style.
- **Streams used** — [sents](pipeline-streams.md#notion-409141b5836981658aa5f249c86d3e7a),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373)
- **Builds on** — [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Capabilities** — [D3](https://app.notion.com/p/409141b58369814399d4e72925177d13)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="group-tier-3-identity"></a>

## Tier 3 Identity

<a id="notion-409141b5836981f69dc4e1260c26c827"></a>

### 3.1 · Document entities

**Status** Proposed · **Order** 301 · **Run wave** 10 · **Downstream reach** 62 · [Notion record](https://app.notion.com/p/409141b5836981f69dc4e1260c26c827)

- **Join key** — Cluster ID
- **What it lets you say** — Entities instead of mentions: each with all its mentions (names, descriptions,
  pronouns), first mention, mention count and spread across sections. Maverick clusters the inventory, pronouns and
  noun phrases included; inventory mentions it leaves unclustered stay as single-mention entities, since its
  OntoNotes model does not output singletons.
- **Streams used** — [coref](pipeline-streams.md#notion-409141b5836981768728e731d44f5fff)
- **Builds on** — [2.1](#notion-409141b5836981e88660f3eede7253ac), [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [3.6](#notion-409141b5836981b6b75ce5b51efbf2dd),
  [3.7](#notion-409141b583698138a0dcedcd6df44e85), [3.8](#notion-409141b5836981aab53de3d4c1552549),
  [4.2](#notion-409141b5836981b7829bec84ef90f752), [5.6](#notion-409141b5836981168731d030ef9a6660),
  [6.5](#notion-409141b58369816f966ce592ba2c3432)
- **Capabilities** — [R6](https://app.notion.com/p/409141b583698193aff5e313fc233b81)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b58369819fac55ec3d81ffe72e"></a>

### 3.2 · KB-grounded entities

**Status** Proposed · **Order** 302 · **Run wave** 11 · **Downstream reach** 58 · [Notion record](https://app.notion.com/p/409141b58369819fac55ec3d81ffe72e)

- **Join key** — Cluster ID, Wikidata ID
- **What it lets you say** — A KB ID per entity, from Wikidata or the seed ontology's known entities. ReFinED links
  the inventory mentions it is given (its own detection adds recall). Each cluster keeps its competing link
  candidates instead of propagating only the most informative mention's ID, and identity, link, type and relation
  evidence are resolved jointly with 3.3, so one wrong cluster or link does not contaminate everything downstream. A
  link to a class is kept distinct from instance-of: 'centrifugal pump' denotes a class, P-101 an instance of it. A
  failed link is NIL with its reason: local entity, insufficient context, candidate-retrieval failure, ambiguity or
  new concept.
- **Streams used** — [el](pipeline-streams.md#notion-409141b583698179988cc7290f49ed7e)
- **Builds on** — [3.1](#notion-409141b5836981f69dc4e1260c26c827)
- **Feeds** — [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5), [3.4](#notion-409141b583698155b2c3f9fad114c7a1),
  [3.5](#notion-409141b5836981eeacf6fb407f615d64), [4.4](#notion-409141b5836981d18cc4e1e78466f0d2),
  [4.6](#notion-409141b5836981d0804fc95ca5a45fb1), [4.7](#notion-409141b5836981d48c27e6a4866db6f5),
  [7.12](#notion-409141b58369817baf69c933ae76405d), [4.1](#notion-409141b5836981ca8d66f08b0b61b113),
  [7.1](#notion-409141b5836981c6ac16d8729eef6ad4), [7.13](#notion-409141b58369817891f7d4dd5dd2e46b),
  [5.8](#notion-409141b5836981a08f23f3d5626b12da), [8.7](#notion-409141b5836981f5a2e5dd0134042a82),
  [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [R7](https://app.notion.com/p/409141b58369819dbc22ec542be5373f)
- **Free check** — Clusters with conflicting IDs; candidate recall for links
- **Evidence** — Hajishirzi 2013; Durrett and Klein 2014 (joint coreference, typing and linking with cross-task
  factors beat strong independent baselines)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b5836981aaa09fc75d3f86b0f5"></a>

### 3.3 · Type consensus

**Status** Proposed · **Order** 303 · **Run wave** 12 · **Downstream reach** 50 · [Notion record](https://app.notion.com/p/409141b5836981aaa09fc75d3f86b0f5)

- **Join key** — Cluster ID
- **What it lets you say** — Each entity's type decided jointly with its identity, link and the relations it takes
  part in: type votes from GLiNER2.5, the GLiNER bi-encoder and ReFinED's fine-grained Wikidata classes, combined
  with the seed ontology's hierarchy and relation signatures. A strongly supported relation can correct an uncertain
  type, and an entity's type helps separate competing relation labels. Unknown types stay open rather than being
  forced into an existing class. Votes from models that share training data or encoders are not counted as
  independent.
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [2.1](#notion-409141b5836981e88660f3eede7253ac)
- **Feeds** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4),
  [8.3](#notion-409141b5836981d2a263cc95f5409062), [8.2](#notion-409141b583698116887fda3ca1c5566d),
  [7.15](#notion-409141b583698126969bdfc3be180171), [8.5](#notion-409141b5836981699240de5dc69f0539)
- **Capabilities** — [O2](https://app.notion.com/p/409141b5836981ca8611d1e383c3ca49),
  [V5](https://app.notion.com/p/409141b5836981e382b4d1a42cd254ce)
- **Free check** — Type changes made by relation evidence, checked by hand
- **Evidence** — Durrett and Klein 2014
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b583698155b2c3f9fad114c7a1"></a>

### 3.4 · Acronyms grounded

**Status** Proposed · **Order** 304 · **Run wave** 12 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b583698155b2c3f9fad114c7a1)

- **Join key** — Short form, Wikidata ID
- **What it lets you say** — Short forms linked through their long forms; an ambiguous acronym resolved by the
  document's own definition rather than by guessing.
- **Builds on** — [2.4](#notion-409141b5836981ba9b2ceeaddeb4d553), [3.2](#notion-409141b58369819fac55ec3d81ffe72e)
- **Capabilities** — [T2](https://app.notion.com/p/409141b583698161bfe9f830e081d2d5),
  [R7](https://app.notion.com/p/409141b58369819dbc22ec542be5373f)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b5836981eeacf6fb407f615d64"></a>

### 3.5 · Entities the KB doesn't know

**Status** Proposed · **Order** 305 · **Run wave** 12 · **Downstream reach** 10 · [Notion record](https://app.notion.com/p/409141b5836981eeacf6fb407f615d64)

- **Join key** — Cluster ID (NIL)
- **What it lets you say** — Named things with no match in Wikidata or the seed ontology, each with its NIL reason
  (local entity, insufficient context, candidate-retrieval failure, ambiguity or new concept), local definitions and
  mention counts. Only local entities and new concepts become candidates for this domain; retrieval failures and
  ambiguity go back to identity resolution. This is where the corpus says something the KB doesn't.
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [2.4](#notion-409141b5836981ba9b2ceeaddeb4d553),
  [2.5](#notion-409141b58369813fb393ea90313ceb6a)
- **Feeds** — [8.1](#notion-409141b58369812f99dbca796e5f7325)
- **Capabilities** — [R7](https://app.notion.com/p/409141b58369819dbc22ec542be5373f),
  [O1](https://app.notion.com/p/409141b5836981d2b926cbef69cc05a2)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b5836981b6b75ce5b51efbf2dd"></a>

### 3.6 · Complete redaction

**Status** Proposed · **Order** 306 · **Run wave** 11 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981b6b75ce5b51efbf2dd)

- **Join key** — Cluster ID
- **What it lets you say** — Personal-data flags propagated to every mention of the same person ('she', 'the
  claimant', 'the account holder'), so masking covers descriptions and pronouns, not just names.
- **Builds on** — [2.8](#notion-409141b5836981f4b896cf86b4998700), [3.1](#notion-409141b5836981f69dc4e1260c26c827)
- **Capabilities** — [C6](https://app.notion.com/p/409141b5836981968e81f9b88dd95f9a)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b583698138a0dcedcd6df44e85"></a>

### 3.7 · Entity salience and aboutness

**Status** Proposed · **Order** 307 · **Run wave** 11 · **Downstream reach** 1 · [Notion record](https://app.notion.com/p/409141b583698138a0dcedcd6df44e85)

- **Join key** — Cluster ID, section path
- **What it lets you say** — Entities ranked by mention count, position (title, abstract, headings) and spread
  across sections: what each document and section is about.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65)
- **Builds on** — [3.1](#notion-409141b5836981f69dc4e1260c26c827), [1.4](#notion-409141b58369816b8a55d644257d2e23)
- **Feeds** — [6.7](#notion-409141b58369817ab817d6f21b14eb45)
- **Capabilities** — [C5](https://app.notion.com/p/409141b5836981c1bc27c7002c8eaf5d),
  [C2](https://app.notion.com/p/409141b5836981dfad02d457eed504d0)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-409141b5836981aab53de3d4c1552549"></a>

### 3.8 · Local conventions

**Status** Proposed · **Order** 308 · **Run wave** 11 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b5836981aab53de3d4c1552549)

- **Join key** — Cluster ID, symbol
- **What it lets you say** — Definitions and symbol declarations applied to every coreferent mention, and the
  document's own conventions recorded with their scope (what σ means here, which units are the default).
- **Builds on** — [3.1](#notion-409141b5836981f69dc4e1260c26c827), [2.5](#notion-409141b58369813fb393ea90313ceb6a),
  [2.6](#notion-409141b583698165b5cccc4da90536ef), [2.2](#notion-409141b5836981fc9364f2874585b571)
- **Feeds** — [7.14](#notion-409141b583698124ae54c5b01ed5d035), [9.6](#notion-409141b5836981fdb517c06be042bcd3)
- **Capabilities** — [T5](https://app.notion.com/p/409141b583698149a0e3e52d20ce84ae),
  [R5](https://app.notion.com/p/409141b58369810785d0ec481da3e349)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="group-tier-4-propositions"></a>

## Tier 4 Propositions

<a id="notion-409141b5836981ca8d66f08b0b61b113"></a>

### 4.1 · Typed, grounded relations

**Status** Proposed · **Order** 401 · **Run wave** 13 · **Downstream reach** 43 · [Notion record](https://app.notion.com/p/409141b5836981ca8d66f08b0b61b113)

- **Join key** — Mention spans, Wikidata IDs
- **What it lets you say** — Relations whose arguments carry KB IDs and types. GLiNER-Relex extracts end to end on
  paragraph windows, so its argument spans are matched to inventory mentions by overlap. Relation labels the
  argument types can't take (a person 'located in' a date) are pruned or flagged; label sets come from schema
  routing.
- **Streams used** — [rel](pipeline-streams.md#notion-409141b5836981578850f08fd787f43d)
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5),
  [1.9](#notion-409141b5836981369becef06b4f81df0)
- **Feeds** — [4.2](#notion-409141b5836981b7829bec84ef90f752), [4.3](#notion-409141b583698169929afb2606b1c8cf),
  [4.9](#notion-409141b583698123a216d4459f31bd6d), [5.1](#notion-409141b583698178ba75c0b0f79c26a0),
  [5.3](#notion-409141b5836981ae802df3160a2e0f55), [5.4](#notion-409141b58369810ebfe5fc4145cd7165),
  [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [5.6](#notion-409141b5836981168731d030ef9a6660),
  [5.8](#notion-409141b5836981a08f23f3d5626b12da), [8.3](#notion-409141b5836981d2a263cc95f5409062),
  [5.10](#notion-409141b5836981c58169e46a89b8ac6c), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [P2](https://app.notion.com/p/409141b5836981e9a8c0fe4388149650)
- **Free check** — Domain and range violations
- **Evidence** — Roth and Yih 2004
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b5836981b7829bec84ef90f752"></a>

### 4.2 · Relations across sentences

**Status** Proposed · **Order** 402 · **Run wave** 14 · **Downstream reach** 7 · [Notion record](https://app.notion.com/p/409141b5836981b7829bec84ef90f752)

- **Join key** — Cluster ID
- **What it lets you say** — Arguments resolved through coreference ('It was acquired by X in 2019'): pronoun
  arguments are replaced by their cluster's representative mention before GLiNER-Relex runs on the window, extending
  relations beyond one sentence. Kept as candidates with confidence, not facts.
- **Streams used** — [rel](pipeline-streams.md#notion-409141b5836981578850f08fd787f43d)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [3.1](#notion-409141b5836981f69dc4e1260c26c827)
- **Feeds** — [8.3](#notion-409141b5836981d2a263cc95f5409062)
- **Capabilities** — [P2](https://app.notion.com/p/409141b5836981e9a8c0fe4388149650)
- **Evidence** — DocRED: at least 40.7% of facts need several sentences and 17.6% need coreference. DyGIE:
  coreference propagation helped entities on both datasets but hurt sentence-level relations on ACE05 (it helped
  slightly on SciERC); indirect evidence that coreference is not a free gain
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b583698169929afb2606b1c8cf"></a>

### 4.3 · KB corroboration

**Status** Proposed · **Order** 403 · **Run wave** 14 · **Downstream reach** 4 · [Notion record](https://app.notion.com/p/409141b583698169929afb2606b1c8cf)

- **Join key** — Wikidata IDs, property
- **What it lets you say** — Each relation marked as already in the KB, new to the KB, or conflicting with a KB
  statement, once its label is mapped to a Wikidata property: the first split between known facts and new knowledge.
- **Streams used** — [kb](pipeline-streams.md#notion-409141b583698180bb6ec82da7b6e42d)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [1.9](#notion-409141b5836981369becef06b4f81df0)
- **Feeds** — [8.8](#notion-409141b583698140a9f9f1491758b832), [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b5836981d18cc4e1e78466f0d2"></a>

### 4.4 · Table statements

**Status** Proposed · **Order** 404 · **Run wave** 12 · **Downstream reach** 47 · [Notion record](https://app.notion.com/p/409141b5836981d18cc4e1e78466f0d2)

- **Join key** — Table ID, cell, Wikidata ID
- **What it lets you say** — Per cell: row entity (with KB ID), column attribute, value, unit, notes and table
  conditions, assembled by lookup and score over Docling's structure. A column profile separates key, measure and
  dimension columns; GLiNER2.5 types header text against the attribute types schema routing supplies; CQE reads
  value cells and ReFinED links entity cells with the column type as prior. Only tables whose column roles stay
  ambiguous go to the CPU LLM.
- **Streams used** — [tabstmt](pipeline-streams.md#notion-409141b58369810eba6fc542f1f9608a)
- **Builds on** — [2.3](#notion-409141b58369815fac36e5072a1d652d), [3.2](#notion-409141b58369819fac55ec3d81ffe72e),
  [1.9](#notion-409141b5836981369becef06b4f81df0)
- **Feeds** — [4.5](#notion-409141b5836981508daff27e73a7bfeb), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4),
  [5.1](#notion-409141b583698178ba75c0b0f79c26a0), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [5.4](#notion-409141b58369810ebfe5fc4145cd7165), [5.5](#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](#notion-409141b5836981168731d030ef9a6660), [5.8](#notion-409141b5836981a08f23f3d5626b12da),
  [5.9](#notion-409141b583698123a463c42c912a6042), [5.10](#notion-409141b5836981c58169e46a89b8ac6c),
  [7.15](#notion-409141b583698126969bdfc3be180171), [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [P6](https://app.notion.com/p/409141b5836981a7be0df9f5b4231c97)
- **Evidence** — Lookup-and-score systems won SemTab 2020; LLM plus KG retrieval leads SemTab 2025 cell linking.
  Replaced TableLlama (94.4 column typing only inside TURL's label set, no cell assertions)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b5836981508daff27e73a7bfeb"></a>

### 4.5 · Text-table consistency

**Status** Proposed · **Order** 405 · **Run wave** 13 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b5836981508daff27e73a7bfeb)

- **Join key** — Pointer, entity, property
- **What it lets you say** — Values stated in the text compared with the cells of the table the text cites, after
  unit normalization: agree, disagree ('25 mm' in text vs '2.5 mm' in the table) or text-only.
- **Builds on** — [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [2.2](#notion-409141b5836981fc9364f2874585b571),
  [1.6](#notion-409141b5836981ef9825f3632387207c)
- **Feeds** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf),
  [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b5836981d0804fc95ca5a45fb1"></a>

### 4.6 · Events with roles

**Status** Proposed · **Order** 406 · **Run wave** 12 · **Downstream reach** 40 · [Notion record](https://app.notion.com/p/409141b5836981d0804fc95ca5a45fb1)

- **Join key** — Trigger, argument spans
- **What it lets you say** — N-ary events: trigger, agent, object, instrument, time and place. Each role is filled
  by asking the NLI model whether 'X is the agent of the acquisition' follows from the sentence, over candidates
  from the mention inventory.
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [2.9](#notion-409141b5836981e6a150e244f5f25270)
- **Feeds** — [4.9](#notion-409141b583698123a216d4459f31bd6d), [5.1](#notion-409141b583698178ba75c0b0f79c26a0),
  [5.3](#notion-409141b5836981ae802df3160a2e0f55), [5.4](#notion-409141b58369810ebfe5fc4145cd7165),
  [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [5.6](#notion-409141b5836981168731d030ef9a6660),
  [5.8](#notion-409141b5836981a08f23f3d5626b12da), [5.10](#notion-409141b5836981c58169e46a89b8ac6c),
  [7.9](#notion-409141b583698134a9a9cfe2691144f0), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [P3](https://app.notion.com/p/409141b5836981be8850e491e18f02e5)
- **Evidence** — Sainz 2022; Du and Cardie 2020
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b5836981d48c27e6a4866db6f5"></a>

### 4.7 · Comparisons

**Status** Proposed · **Order** 407 · **Run wave** 12 · **Downstream reach** 40 · [Notion record](https://app.notion.com/p/409141b5836981d48c27e6a4866db6f5)

- **Join key** — Clause, value spans
- **What it lets you say** — Compared items, dimension, direction, degree and baseline ('20% higher than the 2019
  design'), from comparison markers plus attached values.
- **Builds on** — [2.2](#notion-409141b5836981fc9364f2874585b571), [2.7](#notion-409141b5836981debac4faa03c10afea),
  [3.2](#notion-409141b58369819fac55ec3d81ffe72e)
- **Feeds** — [4.9](#notion-409141b583698123a216d4459f31bd6d), [5.1](#notion-409141b583698178ba75c0b0f79c26a0),
  [5.3](#notion-409141b5836981ae802df3160a2e0f55), [5.4](#notion-409141b58369810ebfe5fc4145cd7165),
  [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [5.6](#notion-409141b5836981168731d030ef9a6660),
  [5.8](#notion-409141b5836981a08f23f3d5626b12da), [5.10](#notion-409141b5836981c58169e46a89b8ac6c),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [P4](https://app.notion.com/p/409141b58369810bb5deeec31c442642)
- **Evidence** — Jindal and Liu 2006
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b583698120b69fe73e93207120"></a>

### 4.8 · Formal relations, checked

**Status** Proposed · **Order** 408 · **Run wave** 10 · **Downstream reach** 6 · [Notion record](https://app.notion.com/p/409141b583698120b69fe73e93207120)

- **Join key** — Formula ID, symbols
- **What it lets you say** — Equalities and inequalities with typed variables, each equation checked for dimensional
  consistency with pint.
- **Streams used** — [formula](pipeline-streams.md#notion-409141b583698127815fd85f864c0fdd),
  [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c)
- **Builds on** — [2.6](#notion-409141b583698165b5cccc4da90536ef)
- **Feeds** — [9.1](#notion-409141b583698118b18ef02258134fbe), [9.2](#notion-409141b58369814cb018c684b83a279a)
- **Capabilities** — [P5](https://app.notion.com/p/409141b5836981a4a07ff951e3b105c1),
  [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-409141b583698123a216d4459f31bd6d"></a>

### 4.9 · Claim content map

**Status** Proposed · **Order** 409 · **Run wave** 14 · **Downstream reach** 39 · [Notion record](https://app.notion.com/p/409141b583698123a216d4459f31bd6d)

- **Join key** — Proposition ID, sentence ID
- **What it lets you say** — Each atomic claim from the CPU LLM, grounded to its source span by LangExtract's
  character offsets (claims it cannot ground are flagged), then mapped to the relations, attributes, events and
  comparisons it contains. Grounding makes a claim inspectable but does not show that its relation, scope or
  attribution is right, so those are checked separately. Claims with no structured content show meaning the
  extractors missed; relations no claim supports suggest over-extraction.
- **Streams used** — [claims](pipeline-streams.md#notion-409141b58369812db491c726a039ca18)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [2.2](#notion-409141b5836981fc9364f2874585b571),
  [4.6](#notion-409141b5836981d0804fc95ca5a45fb1), [4.7](#notion-409141b5836981d48c27e6a4866db6f5),
  [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [5.1](#notion-409141b583698178ba75c0b0f79c26a0), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [5.4](#notion-409141b58369810ebfe5fc4145cd7165), [5.5](#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](#notion-409141b5836981168731d030ef9a6660), [5.8](#notion-409141b5836981a08f23f3d5626b12da),
  [5.10](#notion-409141b5836981c58169e46a89b8ac6c), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [9.3](#notion-409141b58369812aa816deef834ae4b1)
- **Capabilities** — [P7](https://app.notion.com/p/409141b583698125b20ae7e1a0fbd4c9),
  [V1](https://app.notion.com/p/409141b583698191a28bf004cb5b4b9d),
  [V9](https://app.notion.com/p/409141b583698161977bc2593714282f)
- **Evidence** — Claim2Atom: Qwen3-32B 95.7% completeness and 94.8% correctness, Llama-3.2-3B 24%; Claimify prompts
  (Metropolitansky and Larson 2025)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="group-tier-5-qualification"></a>

## Tier 5 Qualification

<a id="notion-409141b583698178ba75c0b0f79c26a0"></a>

### 5.1 · Polarity

**Status** Proposed · **Order** 501 · **Run wave** 15 · **Downstream reach** 27 · [Notion record](https://app.notion.com/p/409141b583698178ba75c0b0f79c26a0)

- **Join key** — Proposition ID, negation scope
- **What it lets you say** — Affirmed vs negated propositions, with negation scope from the parse rather than a word
  window.
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [2.7](#notion-409141b5836981debac4faa03c10afea)
- **Feeds** — [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [Q1](https://app.notion.com/p/409141b583698194993dd77b74775d61)
- **Evidence** — Packard 2014
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b58369815e9c4ed0a3aa10d0e0"></a>

### 5.2 · Certainty and factuality

**Status** Proposed · **Order** 502 · **Run wave** 16 · **Downstream reach** 26 · [Notion record](https://app.notion.com/p/409141b58369815e9c4ed0a3aa10d0e0)

- **Join key** — Proposition ID
- **What it lets you say** — Happened, planned, hypothetical, conjectured or disputed, and how certain the writer
  is, from hedges, modals, mood and tense in the proposition's scope, with section role as a prior.
- **Builds on** — [5.1](#notion-409141b583698178ba75c0b0f79c26a0), [2.7](#notion-409141b5836981debac4faa03c10afea),
  [1.4](#notion-409141b58369816b8a55d644257d2e23)
- **Feeds** — [5.7](#notion-409141b5836981cbaebef8203488d6ba), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [7.6](#notion-409141b5836981899757c0aeaa4f13ea)
- **Capabilities** — [Q2](https://app.notion.com/p/409141b5836981d7be63ef3a60e8ae83),
  [Q9](https://app.notion.com/p/409141b58369815e9c35cfcfb3cc25b1)
- **Evidence** — Stanovsky 2017; SlinkET
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981ae802df3160a2e0f55"></a>

### 5.3 · Conditions, scope and numeric references

**Status** Proposed · **Order** 503 · **Run wave** 15 · **Downstream reach** 27 · [Notion record](https://app.notion.com/p/409141b5836981ae802df3160a2e0f55)

- **Join key** — Proposition ID, clause, discourse relation
- **What it lets you say** — Conditions, assumptions and exceptions attached to the propositions they govern,
  resolved as typed decisions before anything escalates. The condition clause, the proposition it governs and any
  numeric reference in it ('below this pressure') are each a candidate set with an unresolved option, decided
  jointly by a local inference template from unit dimension, ontology frame roles, syntax and proximity. GLiNER2.5
  condition-clause labels and Stanza scope supply candidates; Dipo condition links are soft features across
  sentences. Only implicit or still-unresolved conditions go to the CPU LLM.
- **Streams used** — [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [2.7](#notion-409141b5836981debac4faa03c10afea)
- **Feeds** — [7.15](#notion-409141b583698126969bdfc3be180171), [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [7.4](#notion-409141b5836981e48095d7500fdf9852),
  [7.6](#notion-409141b5836981899757c0aeaa4f13ea)
- **Capabilities** — [Q4](https://app.notion.com/p/409141b5836981659c0ac394c1f4c79c),
  [Q11](https://app.notion.com/p/409141b58369815684b6e9a4828840ea)
- **Free check** — Condition interval checked against the governed value's dimension
- **Evidence** — Jiang 2019 (fact-condition tuples) is the only extraction work and produced no model; measure in
  prototype 1
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b58369810ebfe5fc4145cd7165"></a>

### 5.4 · Valid time

**Status** Proposed · **Order** 504 · **Run wave** 15 · **Downstream reach** 26 · [Notion record](https://app.notion.com/p/409141b58369810ebfe5fc4145cd7165)

- **Join key** — Proposition ID, date span
- **What it lets you say** — When each proposition holds: a point, an interval or open-ended, from attached dates,
  tense and the unit's reference time.
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [2.9](#notion-409141b5836981e6a150e244f5f25270)
- **Feeds** — [7.9](#notion-409141b583698134a9a9cfe2691144f0), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [7.10](#notion-409141b58369813d9268ee4edaaf939b), [7.4](#notion-409141b5836981e48095d7500fdf9852)
- **Capabilities** — [Q5](https://app.notion.com/p/409141b5836981f8b572f3a99254b65f)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b58369810f96f4e4d695c4c73d"></a>

### 5.5 · Generic vs specific

**Status** Proposed · **Order** 505 · **Run wave** 15 · **Downstream reach** 25 · [Notion record](https://app.notion.com/p/409141b58369810f96f4e4d695c4c73d)

- **Join key** — Proposition ID
- **What it lets you say** — Kind-level statements ('centrifugal pumps cavitate at low suction pressure') separated
  from specific episodes ('pump P-101 cavitated on 3 May'), using determiners, number, aspect and the named-entity
  vs concept split. Generic statements become ontology axiom candidates; specific ones go to the instance graph.
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [2.1](#notion-409141b5836981e88660f3eede7253ac),
  [2.7](#notion-409141b5836981debac4faa03c10afea)
- **Feeds** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [8.4](#notion-409141b5836981c7b5f2fdf4e0df8cc6),
  [7.4](#notion-409141b5836981e48095d7500fdf9852), [8.6](#notion-409141b583698145b882e140fad3deb7)
- **Capabilities** — [Q6](https://app.notion.com/p/409141b583698151b0aef141beebea9e)
- **Evidence** — Friedrich and Pinkal 2015
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981168731d030ef9a6660"></a>

### 5.6 · Attribution

**Status** Proposed · **Order** 506 · **Run wave** 15 · **Downstream reach** 27 · [Notion record](https://app.notion.com/p/409141b5836981168731d030ef9a6660)

- **Join key** — Proposition ID, reference ID or entity ID
- **What it lets you say** — Who asserts each proposition (the authors, a cited work, a named person, a standard)
  and the writer's commitment to it (endorses, reports, disputes).
- **Streams used** — [threads](pipeline-streams.md#notion-409141b5836981eb92d9d7bb774895d8)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [1.5](#notion-409141b5836981499080ff4fc4c8a20e),
  [2.7](#notion-409141b5836981debac4faa03c10afea), [3.1](#notion-409141b5836981f69dc4e1260c26c827)
- **Feeds** — [5.10](#notion-409141b5836981c58169e46a89b8ac6c), [5.7](#notion-409141b5836981cbaebef8203488d6ba),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [6.4](#notion-409141b5836981558823e904a87ca9c6),
  [7.4](#notion-409141b5836981e48095d7500fdf9852)
- **Capabilities** — [Q7](https://app.notion.com/p/409141b5836981daa6bcd1bd76fbd6be)
- **Evidence** — PARC 3.0
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981cbaebef8203488d6ba"></a>

### 5.7 · Evidence basis

**Status** Proposed · **Order** 507 · **Run wave** 17 · **Downstream reach** 25 · [Notion record](https://app.notion.com/p/409141b5836981cbaebef8203488d6ba)

- **Join key** — Proposition ID
- **What it lets you say** — What each proposition rests on: own observation (results section, no citation, past
  tense, quantitative), citation only, proof (in proof blocks), simulation or expert judgement.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65)
- **Builds on** — [5.6](#notion-409141b5836981168731d030ef9a6660), [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0),
  [1.4](#notion-409141b58369816b8a55d644257d2e23), [2.2](#notion-409141b5836981fc9364f2874585b571)
- **Feeds** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [6.3](#notion-409141b58369816abbbffc5a400dc4c1)
- **Capabilities** — [Q8](https://app.notion.com/p/409141b5836981ecb917e73a2bd0ce05)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981a08f23f3d5626b12da"></a>

### 5.8 · Deontic force

**Status** Proposed · **Order** 508 · **Run wave** 15 · **Downstream reach** 29 · [Notion record](https://app.notion.com/p/409141b5836981a08f23f3d5626b12da)

- **Join key** — Proposition ID, bearer entity
- **What it lets you say** — Obligation, permission, prohibition or recommendation, with who bears it ('the supplier
  shall…').
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [2.7](#notion-409141b5836981debac4faa03c10afea),
  [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [1.9](#notion-409141b5836981369becef06b4f81df0)
- **Feeds** — [5.9](#notion-409141b583698123a463c42c912a6042), [6.5](#notion-409141b58369816f966ce592ba2c3432),
  [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [Q3](https://app.notion.com/p/409141b58369812587aac5b34007bf93)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b583698123a463c42c912a6042"></a>

### 5.9 · Value roles

**Status** Proposed · **Order** 509 · **Run wave** 16 · **Downstream reach** 27 · [Notion record](https://app.notion.com/p/409141b583698123a463c42c912a6042)

- **Join key** — Value span
- **What it lets you say** — What each number is: measured, design, rated, limit, set-point or nominal. A value
  under 'shall not exceed' is a limit; a value in a results table is a measurement.
- **Streams used** — [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Builds on** — [2.2](#notion-409141b5836981fc9364f2874585b571), [4.4](#notion-409141b5836981d18cc4e1e78466f0d2),
  [1.4](#notion-409141b58369816b8a55d644257d2e23), [5.8](#notion-409141b5836981a08f23f3d5626b12da)
- **Feeds** — [7.15](#notion-409141b583698126969bdfc3be180171), [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [Q12](https://app.notion.com/p/409141b5836981749dabc35ee7e3ca3a)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981c58169e46a89b8ac6c"></a>

### 5.10 · Stance

**Status** Proposed · **Order** 510 · **Run wave** 16 · **Downstream reach** 25 · [Notion record](https://app.notion.com/p/409141b5836981c58169e46a89b8ac6c)

- **Join key** — Proposition ID
- **What it lets you say** — The asserter's evaluation of the claim or its subject (favourable, critical, neutral).
- **Streams used** — [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [5.6](#notion-409141b5836981168731d030ef9a6660)
- **Feeds** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [6.4](#notion-409141b5836981558823e904a87ca9c6)
- **Capabilities** — [Q10](https://app.notion.com/p/409141b58369815a8065e06db6b2fa0d)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-409141b5836981a6a7b6c0be98a0fe1f"></a>

### 5.11 · Qualified claim

**Status** Proposed · **Order** 511 · **Run wave** 18 · **Downstream reach** 24 · [Notion record](https://app.notion.com/p/409141b5836981a6a7b6c0be98a0fe1f)

- **Join key** — Proposition ID
- **What it lets you say** — The central record: who says what about which grounded entities, under which
  conditions, valid when, on what evidence, generic or specific, with every part aligned to its source span. It
  keeps four separate quantities: author modality (is, may, probably, must), interpretation confidence (how sure we
  are the source was read correctly), source or measurement reliability where assessed, and corpus support with its
  provenance groups (7.5). It keeps the supporting spans, the interpretation decisions connecting them, each source
  quantity alongside its normalized value and transformation, and coherent alternatives where the reading is
  uncertain.
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [4.6](#notion-409141b5836981d0804fc95ca5a45fb1),
  [4.7](#notion-409141b5836981d48c27e6a4866db6f5), [5.1](#notion-409141b583698178ba75c0b0f79c26a0),
  [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [5.4](#notion-409141b58369810ebfe5fc4145cd7165), [5.5](#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](#notion-409141b5836981168731d030ef9a6660), [5.7](#notion-409141b5836981cbaebef8203488d6ba),
  [5.8](#notion-409141b5836981a08f23f3d5626b12da), [5.9](#notion-409141b583698123a463c42c912a6042),
  [5.10](#notion-409141b5836981c58169e46a89b8ac6c)
- **Feeds** — [6.1](#notion-409141b5836981659d9af5ab527c816f), [6.3](#notion-409141b58369816abbbffc5a400dc4c1),
  [7.3](#notion-409141b58369812bbebfe671f59c4652), [7.10](#notion-409141b58369813d9268ee4edaaf939b),
  [8.4](#notion-409141b5836981c7b5f2fdf4e0df8cc6), [8.5](#notion-409141b5836981699240de5dc69f0539),
  [7.7](#notion-409141b5836981f2ae3ae3df3991a162), [7.8](#notion-409141b5836981089c71d766491f7851),
  [8.6](#notion-409141b583698145b882e140fad3deb7), [9.1](#notion-409141b583698118b18ef02258134fbe),
  [9.6](#notion-409141b5836981fdb517c06be042bcd3)
- **Capabilities** — [Q11](https://app.notion.com/p/409141b58369815684b6e9a4828840ea)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="group-tier-6-discourse-and-argument"></a>

## Tier 6 Discourse and argument

<a id="notion-409141b5836981659d9af5ab527c816f"></a>

### 6.1 · Claim roles in the text

**Status** Proposed · **Order** 601 · **Run wave** 19 · **Downstream reach** 5 · [Notion record](https://app.notion.com/p/409141b5836981659d9af5ab527c816f)

- **Join key** — Discourse unit ID, proposition ID
- **What it lets you say** — Claim-to-claim relations (evidence, cause, contrast, concession, elaboration), and
  which claims are conclusions (receive support) vs premises.
- **Streams used** — [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce)
- **Builds on** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Feeds** — [6.2](#notion-409141b5836981278809fc0ca0b6cb51), [6.4](#notion-409141b5836981558823e904a87ca9c6),
  [6.7](#notion-409141b58369817ab817d6f21b14eb45)
- **Capabilities** — [A2](https://app.notion.com/p/409141b5836981e2a5b1de26acb1b9a9)
- **Evidence** — Hewett 2019
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b5836981278809fc0ca0b6cb51"></a>

### 6.2 · Argument graph

**Status** Proposed · **Order** 602 · **Run wave** 21 · **Downstream reach** 1 · [Notion record](https://app.notion.com/p/409141b5836981278809fc0ca0b6cb51)

- **Join key** — Claim pair
- **What it lets you say** — Support and attack edges between claims, kept distinct from entailment and
  contradiction: an observation can support a hypothesis without entailing it, and a methodological criticism can
  attack an argument without contradicting its conclusion. DeBERTa NLI scores are features for these judgements,
  alongside discourse links and cues, not their definition; the CPU LLM labels the top pairs once the non-generative
  baseline is measured. Discourse-linked pairs are scored first, then pairs within a proximity window, which keeps
  the pair count roughly linear in document length without trusting the discourse parse (about 45-56 F1 end to end)
  as a hard filter.
- **Streams used** — [arg](pipeline-streams.md#notion-409141b5836981ab84bffe7436ced61c),
  [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Builds on** — [6.1](#notion-409141b5836981659d9af5ab527c816f)
- **Feeds** — [9.6](#notion-409141b5836981fdb517c06be042bcd3)
- **Capabilities** — [A3](https://app.notion.com/p/409141b583698168b8b3d8ecc07ac832)
- **Evidence** — Gorur et al. 2025: prompted LLMs beat RoBERTa baselines significantly on support and attack;
  gpt-oss-120b 82.1% zero-shot on UKP vs 57.7 F1 for fine-tuned BERT
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b58369816abbbffc5a400dc4c1"></a>

### 6.3 · Unit and mention function

**Status** Proposed · **Order** 603 · **Run wave** 19 · **Downstream reach** 8 · [Notion record](https://app.notion.com/p/409141b58369816abbbffc5a400dc4c1)

- **Join key** — Paragraph, proposition ID
- **What it lets you say** — Each paragraph and claim labelled as definition, method, result, limitation, example or
  background, and each key mention as defined, applied, derived or merely mentioned.
- **Streams used** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Builds on** — [1.4](#notion-409141b58369816b8a55d644257d2e23), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [5.7](#notion-409141b5836981cbaebef8203488d6ba)
- **Feeds** — [6.6](#notion-409141b5836981adacd1d08814bff80e), [6.7](#notion-409141b58369817ab817d6f21b14eb45),
  [9.1](#notion-409141b583698118b18ef02258134fbe)
- **Capabilities** — [A1](https://app.notion.com/p/409141b5836981eebb55ce2b091c7230),
  [A4](https://app.notion.com/p/409141b5836981c990efe562db5c4082)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b5836981558823e904a87ca9c6"></a>

### 6.4 · Citation function

**Status** Proposed · **Order** 604 · **Run wave** 20 · **Downstream reach** 1 · [Notion record](https://app.notion.com/p/409141b5836981558823e904a87ca9c6)

- **Join key** — Citation marker
- **What it lets you say** — Why each work is cited: background, uses, extends, compares, supports or contradicts,
  from the discourse relation around the citation, the attribution and stance, and verb patterns ('we use the method
  of \[12\]').
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373)
- **Builds on** — [1.5](#notion-409141b5836981499080ff4fc4c8a20e), [6.1](#notion-409141b5836981659d9af5ab527c816f),
  [5.6](#notion-409141b5836981168731d030ef9a6660), [5.10](#notion-409141b5836981c58169e46a89b8ac6c)
- **Feeds** — [7.6](#notion-409141b5836981899757c0aeaa4f13ea)
- **Capabilities** — [A5](https://app.notion.com/p/409141b58369819c9493c4594c9d8063)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b58369816f966ce592ba2c3432"></a>

### 6.5 · Commitments in conversation

**Status** Proposed · **Order** 605 · **Run wave** 16 · **Downstream reach** 6 · [Notion record](https://app.notion.com/p/409141b58369816f966ce592ba2c3432)

- **Join key** — Message ID, speaker
- **What it lets you say** — Requests, commitments, decisions and approvals, each with owner (speaker or addressee
  resolved by coreference) and due date.
- **Streams used** — [threads](pipeline-streams.md#notion-409141b5836981eb92d9d7bb774895d8),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Builds on** — [5.8](#notion-409141b5836981a08f23f3d5626b12da), [3.1](#notion-409141b5836981f69dc4e1260c26c827),
  [2.9](#notion-409141b5836981e6a150e244f5f25270)
- **Feeds** — [9.1](#notion-409141b583698118b18ef02258134fbe)
- **Capabilities** — [A6](https://app.notion.com/p/409141b58369816fa33ec3943693d263)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b5836981adacd1d08814bff80e"></a>

### 6.6 · Pairs

**Status** Proposed · **Order** 606 · **Run wave** 20 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981adacd1d08814bff80e)

- **Join key** — Message ID, discourse unit ID
- **What it lets you say** — Question-answer, problem-remedy and exercise-solution pairs.
- **Streams used** — [threads](pipeline-streams.md#notion-409141b5836981eb92d9d7bb774895d8),
  [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce)
- **Builds on** — [6.3](#notion-409141b58369816abbbffc5a400dc4c1)
- **Capabilities** — [A7](https://app.notion.com/p/409141b58369810ebe8ed8dd7e25ebf5)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-409141b58369817ab817d6f21b14eb45"></a>

### 6.7 · Summary of record

**Status** Proposed · **Order** 607 · **Run wave** 20 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b58369817ab817d6f21b14eb45)

- **Join key** — Proposition ID
- **What it lets you say** — An extractive summary built from the central claims (conclusions and results about the
  most salient entities), each pointing to its evidence.
- **Builds on** — [3.7](#notion-409141b583698138a0dcedcd6df44e85), [6.1](#notion-409141b5836981659d9af5ab527c816f),
  [6.3](#notion-409141b58369816abbbffc5a400dc4c1)
- **Capabilities** — [C4](https://app.notion.com/p/409141b58369819c9019d497a1f3a977),
  [C5](https://app.notion.com/p/409141b5836981c1bc27c7002c8eaf5d)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="group-tier-7-corpus"></a>

## Tier 7 Corpus

<a id="notion-409141b5836981c6ac16d8729eef6ad4"></a>

### 7.1 · Corpus entity registry

**Status** Proposed · **Order** 701 · **Run wave** 14 · **Downstream reach** 27 · [Notion record](https://app.notion.com/p/409141b5836981c6ac16d8729eef6ad4)

- **Join key** — Registry ID
- **What it lets you say** — One ID per real-world entity across documents, including entities the KB doesn't know.
  KB IDs act as strong agreement keys; names, types, attribute values (table rows included) and context embeddings
  decide the rest.
- **Streams used** — [splink](pipeline-streams.md#notion-409141b58369816d80fcf751582e646c),
  [emb](pipeline-streams.md#notion-409141b583698173900bfbf18657f719)
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5),
  [2.2](#notion-409141b5836981fc9364f2874585b571), [4.4](#notion-409141b5836981d18cc4e1e78466f0d2)
- **Feeds** — [7.13](#notion-409141b58369817891f7d4dd5dd2e46b), [8.3](#notion-409141b5836981d2a263cc95f5409062),
  [7.9](#notion-409141b583698134a9a9cfe2691144f0), [7.15](#notion-409141b583698126969bdfc3be180171),
  [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae), [7.3](#notion-409141b58369812bbebfe671f59c4652),
  [7.10](#notion-409141b58369813d9268ee4edaaf939b), [8.4](#notion-409141b5836981c7b5f2fdf4e0df8cc6),
  [7.5](#notion-409141b583698180ae49d9c346699f52), [8.6](#notion-409141b583698145b882e140fad3deb7)
- **Capabilities** — [R8](https://app.notion.com/p/409141b583698158b419de22ef9b5bc0)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b5836981ee83cbe564b02d71a9"></a>

### 7.2 · Corpus citation graph

**Status** Proposed · **Order** 702 · **Run wave** 14 · **Downstream reach** 5 · [Notion record](https://app.notion.com/p/409141b5836981ee83cbe564b02d71a9)

- **Join key** — Reference ID, document ID
- **What it lets you say** — Reference entries resolved to documents in the corpus (by DOI, or by Splink on title,
  authors and year), with editions collapsed: who cites whom, and which claims rest on which origin.
- **Streams used** — [sci](pipeline-streams.md#notion-409141b5836981c79610f5ea4b9d5130),
  [splink](pipeline-streams.md#notion-409141b58369816d80fcf751582e646c)
- **Builds on** — [1.5](#notion-409141b5836981499080ff4fc4c8a20e), [1.7](#notion-409141b58369810e838eefea6cb5ef86),
  [1.8](#notion-409141b58369816b8ce0fb40bdc774ac)
- **Feeds** — [7.5](#notion-409141b583698180ae49d9c346699f52), [7.7](#notion-409141b5836981f2ae3ae3df3991a162),
  [7.11](#notion-409141b583698164b2dbed3f8bc47885), [7.6](#notion-409141b5836981899757c0aeaa4f13ea)
- **Capabilities** — [D10](https://app.notion.com/p/409141b5836981539d11daa4246b656b),
  [R8](https://app.notion.com/p/409141b583698158b419de22ef9b5bc0)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b58369812bbebfe671f59c4652"></a>

### 7.3 · Claim equivalence

**Status** Proposed · **Order** 703 · **Run wave** 20 · **Downstream reach** 10 · [Notion record](https://app.notion.com/p/409141b58369812bbebfe671f59c4652)

- **Join key** — Proposition pair
- **What it lets you say** — Claims that say the same thing, entail one another or contradict, across documents.
  Entity IDs are aligned first, so 'P-101' and 'the feed pump' compare correctly; contradiction comes from the
  three-way NLI model; each source's contribution stays separate.
- **Streams used** — [claim\_emb](pipeline-streams.md#notion-409141b5836981e4b650dbcd7ea604e1),
  [bm25](pipeline-streams.md#notion-409141b58369817c8ac1eb2c96d6f443),
  [rerank](pipeline-streams.md#notion-409141b5836981dab3b4fe90fc6c4087),
  [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Builds on** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4)
- **Feeds** — [7.4](#notion-409141b5836981e48095d7500fdf9852), [7.5](#notion-409141b583698180ae49d9c346699f52),
  [7.7](#notion-409141b5836981f2ae3ae3df3991a162), [7.8](#notion-409141b5836981089c71d766491f7851),
  [7.11](#notion-409141b583698164b2dbed3f8bc47885)
- **Capabilities** — [P8](https://app.notion.com/p/409141b5836981b0aa25ca5ef19738f3)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b5836981e48095d7500fdf9852"></a>

### 7.4 · Qualifier-aware contradiction

**Status** Proposed · **Order** 704 · **Run wave** 21 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b5836981e48095d7500fdf9852)

- **Join key** — Proposition pair
- **What it lets you say** — A real conflict only where conditions, valid time, genericity and scope overlap.
  'Efficiency rises with speed' and 'efficiency falls with speed' are not in conflict if one holds below 3,000 rpm
  and the other above.
- **Builds on** — [7.3](#notion-409141b58369812bbebfe671f59c4652), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [5.4](#notion-409141b58369810ebfe5fc4145cd7165), [5.5](#notion-409141b58369810f96f4e4d695c4c73d),
  [5.6](#notion-409141b5836981168731d030ef9a6660)
- **Feeds** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf)
- **Evidence** — Jiang 2019 (conditions change truth)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b583698180ae49d9c346699f52"></a>

### 7.5 · Distinct support and known dependence

**Status** Proposed · **Order** 705 · **Run wave** 21 · **Downstream reach** 2 · [Notion record](https://app.notion.com/p/409141b583698180ae49d9c346699f52)

- **Join key** — Claim group, citation graph
- **What it lets you say** — How much distinct evidence backs each claim. Duplicates, editions and restatements that
  trace through the citation graph to the same origin form one provenance group, and known dependence (shared
  dataset, experiment, report or author group) is recorded explicitly. Independence is claimed only where it is
  checked, since groups can share an uncited origin. Flags amplification (many papers, one data source). Support is
  not converted into probability updates as if groups were independent.
- **Builds on** — [7.3](#notion-409141b58369812bbebfe671f59c4652), [7.2](#notion-409141b5836981ee83cbe564b02d71a9),
  [1.8](#notion-409141b58369816b8ce0fb40bdc774ac), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4)
- **Feeds** — [7.6](#notion-409141b5836981899757c0aeaa4f13ea), [8.8](#notion-409141b583698140a9f9f1491758b832)
- **Capabilities** — [Q8](https://app.notion.com/p/409141b5836981ecb917e73a2bd0ce05),
  [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf)
- **Evidence** — Greenberg 2009 (citation bias, amplification, invention)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b5836981899757c0aeaa4f13ea"></a>

### 7.6 · Claim drift

**Status** Proposed · **Order** 706 · **Run wave** 22 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981899757c0aeaa4f13ea)

- **Join key** — Citation chain
- **What it lets you say** — Changes in certainty or conditions as a claim is passed along citations: 'may' becomes
  'does', a condition is dropped, a hypothesis turns into a fact by citation alone.
- **Builds on** — [7.5](#notion-409141b583698180ae49d9c346699f52), [7.2](#notion-409141b5836981ee83cbe564b02d71a9),
  [5.2](#notion-409141b58369815e9c4ed0a3aa10d0e0), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [6.4](#notion-409141b5836981558823e904a87ca9c6)
- **Capabilities** — [Q2](https://app.notion.com/p/409141b5836981d7be63ef3a60e8ae83),
  [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf)
- **Evidence** — Greenberg 2009
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b5836981f2ae3ae3df3991a162"></a>

### 7.7 · Cited-claim faithfulness

**Status** Proposed · **Order** 707 · **Run wave** 21 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981f2ae3ae3df3991a162)

- **Join key** — Citing claim, cited document
- **What it lets you say** — Whether the cited document, when it is in the corpus, actually supports the claim
  attributed to it: supported, unsupported or contradicted, checked against the cited document's own claims.
- **Streams used** — [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Builds on** — [7.2](#notion-409141b5836981ee83cbe564b02d71a9), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [7.3](#notion-409141b58369812bbebfe671f59c4652)
- **Capabilities** — [V2](https://app.notion.com/p/409141b5836981338261d629a9039854),
  [A5](https://app.notion.com/p/409141b58369819c9493c4594c9d8063),
  [Q7](https://app.notion.com/p/409141b5836981daa6bcd1bd76fbd6be)
- **Evidence** — Greenberg 2009
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b5836981089c71d766491f7851"></a>

### 7.8 · Edition differences at claim level

**Status** Proposed · **Order** 708 · **Run wave** 21 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981089c71d766491f7851)

- **Join key** — Edition pair, claim group
- **What it lets you say** — Claims and values added, removed or changed between editions of the same document, and
  which value is current.
- **Builds on** — [1.8](#notion-409141b58369816b8ce0fb40bdc774ac), [7.3](#notion-409141b58369812bbebfe671f59c4652),
  [1.7](#notion-409141b58369810e838eefea6cb5ef86), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [C7](https://app.notion.com/p/409141b58369814fac13f8ed210aa394)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b583698134a9a9cfe2691144f0"></a>

### 7.9 · Cross-document events and entity timelines

**Status** Proposed · **Order** 709 · **Run wave** 16 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b583698134a9a9cfe2691144f0)

- **Join key** — Event cluster, registry ID
- **What it lets you say** — The same incident reported in several documents merged into one event, and an ordered
  history of events for each entity.
- **Streams used** — [emb](pipeline-streams.md#notion-409141b583698173900bfbf18657f719)
- **Builds on** — [4.6](#notion-409141b5836981d0804fc95ca5a45fb1), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4),
  [5.4](#notion-409141b58369810ebfe5fc4145cd7165), [2.9](#notion-409141b5836981e6a150e244f5f25270)
- **Capabilities** — [R8](https://app.notion.com/p/409141b583698158b419de22ef9b5bc0),
  [F10](https://app.notion.com/p/409141b58369818393a3e67a32538b7c),
  [Q5](https://app.notion.com/p/409141b5836981f8b572f3a99254b65f)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b58369813d9268ee4edaaf939b"></a>

### 7.10 · Topics and trends

**Status** Proposed · **Order** 710 · **Run wave** 21 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b58369813d9268ee4edaaf939b)

- **Join key** — Topic ID, registry ID, date
- **What it lets you say** — Topics over claims (not just passages), the entities central to each topic, and how
  each topic's share changes over time.
- **Streams used** — [topics](pipeline-streams.md#notion-409141b583698142b5c6e6907527d2bd)
- **Builds on** — [7.1](#notion-409141b5836981c6ac16d8729eef6ad4), [5.4](#notion-409141b58369810ebfe5fc4145cd7165),
  [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f)
- **Capabilities** — [C2](https://app.notion.com/p/409141b5836981dfad02d457eed504d0)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b583698164b2dbed3f8bc47885"></a>

### 7.11 · Novelty

**Status** Proposed · **Order** 711 · **Run wave** 21 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b583698164b2dbed3f8bc47885)

- **Join key** — Claim group, date
- **What it lets you say** — Whether each claim is new to the corpus or restates an earlier one, using the earliest
  dated source in its equivalence group and discounting restatements that cite that source.
- **Builds on** — [7.3](#notion-409141b58369812bbebfe671f59c4652), [7.2](#notion-409141b5836981ee83cbe564b02d71a9),
  [1.7](#notion-409141b58369810e838eefea6cb5ef86)
- **Capabilities** — [C8](https://app.notion.com/p/409141b583698188af0cd2b625fef912)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b58369817baf69c933ae76405d"></a>

### 7.12 · Sense inventory

**Status** Proposed · **Order** 712 · **Run wave** 12 · **Downstream reach** 13 · [Notion record](https://app.notion.com/p/409141b58369817baf69c933ae76405d)

- **Join key** — Term record, occurrence
- **What it lets you say** — One sense per term by default. A term is split into distinct senses only when the
  clusters of its contexts are well separated and a definition in the corpus supports the split; the CPU LLM
  confirms. Occurrences linked to different KB IDs give partial ground truth for checking splits.
- **Streams used** — [emb](pipeline-streams.md#notion-409141b583698173900bfbf18657f719)
- **Builds on** — [2.4](#notion-409141b5836981ba9b2ceeaddeb4d553), [3.2](#notion-409141b58369819fac55ec3d81ffe72e)
- **Feeds** — [7.13](#notion-409141b58369817891f7d4dd5dd2e46b), [8.1](#notion-409141b58369812f99dbca796e5f7325)
- **Capabilities** — [T6](https://app.notion.com/p/409141b5836981458307dd46346bf23b)
- **Evidence** — Word sense induction in the LLM era (2026): one sense per lemma scores 73.6, clustering 71-72,
  GPT-4o 66.9
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b58369817891f7d4dd5dd2e46b"></a>

### 7.13 · Consolidated terminology

**Status** Proposed · **Order** 713 · **Run wave** 15 · **Downstream reach** 12 · [Notion record](https://app.notion.com/p/409141b58369817891f7d4dd5dd2e46b)

- **Join key** — Term record, sense
- **What it lets you say** — Corpus terminology: one canonical term per sense, its variants and acronyms, and its
  definitions from each document that gives one.
- **Builds on** — [2.4](#notion-409141b5836981ba9b2ceeaddeb4d553), [7.12](#notion-409141b58369817baf69c933ae76405d),
  [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4),
  [2.5](#notion-409141b58369813fb393ea90313ceb6a)
- **Feeds** — [7.14](#notion-409141b583698124ae54c5b01ed5d035), [8.1](#notion-409141b58369812f99dbca796e5f7325)
- **Capabilities** — [T4](https://app.notion.com/p/409141b58369818da2d4ec686a32e14c),
  [C3](https://app.notion.com/p/409141b5836981eaa5f4da65f0e76caa)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b583698124ae54c5b01ed5d035"></a>

### 7.14 · Convention conflicts

**Status** Proposed · **Order** 714 · **Run wave** 16 · **Downstream reach** 2 · [Notion record](https://app.notion.com/p/409141b583698124ae54c5b01ed5d035)

- **Join key** — Quantity, symbol
- **What it lets you say** — Documents that use different units or symbols for the same quantity (psi vs MPa; σ for
  stress vs standard deviation), so values are converted before they are compared.
- **Builds on** — [3.8](#notion-409141b5836981aab53de3d4c1552549), [2.3](#notion-409141b58369815fac36e5072a1d652d),
  [7.13](#notion-409141b58369817891f7d4dd5dd2e46b)
- **Feeds** — [7.16](#notion-409141b58369811cbf3eedd9e3e6fbae), [9.6](#notion-409141b5836981fdb517c06be042bcd3)
- **Capabilities** — [T5](https://app.notion.com/p/409141b583698149a0e3e52d20ce84ae),
  [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b583698126969bdfc3be180171"></a>

### 7.15 · Value distributions

**Status** Proposed · **Order** 715 · **Run wave** 17 · **Downstream reach** 9 · [Notion record](https://app.notion.com/p/409141b583698126969bdfc3be180171)

- **Join key** — Entity type, property, value role, condition band
- **What it lets you say** — Normalized value distributions per entity type, property and value role, split by
  condition band, with outliers flagged: a likely unit slip, extraction error or a genuinely unusual case.
- **Builds on** — [4.4](#notion-409141b5836981d18cc4e1e78466f0d2), [2.2](#notion-409141b5836981fc9364f2874585b571),
  [5.9](#notion-409141b583698123a463c42c912a6042), [5.3](#notion-409141b5836981ae802df3160a2e0f55),
  [7.1](#notion-409141b5836981c6ac16d8729eef6ad4), [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5)
- **Feeds** — [8.5](#notion-409141b5836981699240de5dc69f0539), [8.6](#notion-409141b583698145b882e140fad3deb7),
  [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-409141b58369811cbf3eedd9e3e6fbae"></a>

### 7.16 · Requirement-measurement compliance

**Status** Proposed · **Order** 716 · **Run wave** 17 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b58369811cbf3eedd9e3e6fbae)

- **Join key** — Registry ID, property, condition
- **What it lets you say** — Limits and specifications joined to measured values for the same entity and property
  under overlapping conditions: which requirements are met, by what margin, and which are violated.
- **Builds on** — [5.8](#notion-409141b5836981a08f23f3d5626b12da), [5.9](#notion-409141b583698123a463c42c912a6042),
  [5.3](#notion-409141b5836981ae802df3160a2e0f55), [4.4](#notion-409141b5836981d18cc4e1e78466f0d2),
  [7.1](#notion-409141b5836981c6ac16d8729eef6ad4), [7.14](#notion-409141b583698124ae54c5b01ed5d035)
- **Capabilities** — [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf),
  [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0),
  [F5](https://app.notion.com/p/409141b5836981d3b344f5f28347603e),
  [F3](https://app.notion.com/p/409141b5836981f09a6ef3cb41339db8)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="group-tier-8-ontology"></a>

## Tier 8 Ontology

<a id="notion-409141b58369812f99dbca796e5f7325"></a>

### 8.1 · Concepts

**Status** Proposed · **Order** 801 · **Run wave** 16 · **Downstream reach** 9 · [Notion record](https://app.notion.com/p/409141b58369812f99dbca796e5f7325)

- **Join key** — Concept ID
- **What it lets you say** — Proposed concepts with labels, glosses from definitions and senses kept apart, each
  checked against the accepted seed ontology first: a match enriches an accepted concept, a non-match becomes a
  proposal. Proposals stay separate from the accepted ontology until reviewed.
- **Builds on** — [7.13](#notion-409141b58369817891f7d4dd5dd2e46b), [3.5](#notion-409141b5836981eeacf6fb407f615d64),
  [2.5](#notion-409141b58369813fb393ea90313ceb6a), [7.12](#notion-409141b58369817baf69c933ae76405d)
- **Feeds** — [8.2](#notion-409141b583698116887fda3ca1c5566d), [8.7](#notion-409141b5836981f5a2e5dd0134042a82),
  [8.8](#notion-409141b583698140a9f9f1491758b832)
- **Capabilities** — [O1](https://app.notion.com/p/409141b5836981d2b926cbef69cc05a2)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b583698116887fda3ca1c5566d"></a>

### 8.2 · Types and hierarchy

**Status** Proposed · **Order** 802 · **Run wave** 17 · **Downstream reach** 7 · [Notion record](https://app.notion.com/p/409141b583698116887fda3ca1c5566d)

- **Join key** — Concept ID
- **What it lets you say** — Is-a and instance-of links with evidence counts, from definition genus, Hearst
  patterns, KB subclass links and type consensus.
- **Streams used** — [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [kb](pipeline-streams.md#notion-409141b583698180bb6ec82da7b6e42d)
- **Builds on** — [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5), [2.5](#notion-409141b58369813fb393ea90313ceb6a),
  [8.1](#notion-409141b58369812f99dbca796e5f7325)
- **Feeds** — [8.4](#notion-409141b5836981c7b5f2fdf4e0df8cc6), [8.6](#notion-409141b583698145b882e140fad3deb7),
  [8.8](#notion-409141b583698140a9f9f1491758b832)
- **Capabilities** — [O2](https://app.notion.com/p/409141b5836981ca8611d1e383c3ca49),
  [O3](https://app.notion.com/p/409141b5836981a4a30bd4a695dc2985)
- **Evidence** — Roller 2018
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b5836981d2a263cc95f5409062"></a>

### 8.3 · Relation inventory

**Status** Proposed · **Order** 803 · **Run wave** 15 · **Downstream reach** 6 · [Notion record](https://app.notion.com/p/409141b5836981d2a263cc95f5409062)

- **Join key** — Predicate
- **What it lets you say** — Predicates with argument-type signatures (domain and range distributions), direction
  and frequency.
- **Builds on** — [4.1](#notion-409141b5836981ca8d66f08b0b61b113), [4.2](#notion-409141b5836981b7829bec84ef90f752),
  [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4)
- **Feeds** — [8.6](#notion-409141b583698145b882e140fad3deb7), [8.8](#notion-409141b583698140a9f9f1491758b832)
- **Capabilities** — [O4](https://app.notion.com/p/409141b583698141aa45e4c5184d1f3a)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b5836981c7b5f2fdf4e0df8cc6"></a>

### 8.4 · Generic-to-instance consistency

**Status** Proposed · **Order** 804 · **Run wave** 19 · **Downstream reach** 6 · [Notion record](https://app.notion.com/p/409141b5836981c7b5f2fdf4e0df8cc6)

- **Join key** — Concept ID, registry ID
- **What it lets you say** — Kind-level claims checked against instance claims through the type hierarchy: which
  specific entities fall inside a generic claim's conditions (an asset run in a range the literature warns about),
  and which instances contradict a generalization.
- **Builds on** — [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [8.2](#notion-409141b583698116887fda3ca1c5566d), [7.1](#notion-409141b5836981c6ac16d8729eef6ad4)
- **Feeds** — [8.6](#notion-409141b583698145b882e140fad3deb7)
- **Capabilities** — [V3](https://app.notion.com/p/409141b58369815eaf43cb763cda18cf),
  [O6](https://app.notion.com/p/409141b5836981e8a185d9b812e496e7)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b5836981699240de5dc69f0539"></a>

### 8.5 · Induced record frames

**Status** Proposed · **Order** 805 · **Run wave** 19 · **Downstream reach** 6 · [Notion record](https://app.notion.com/p/409141b5836981699240de5dc69f0539)

- **Join key** — Entity type
- **What it lets you say** — Recurring attribute sets per entity type ('pumps: flow rate, head, power, NPSH,
  efficiency, with units and test conditions'), proposed as frames. A frame becomes an extraction template for tier
  9 only once accepted into the next ontology version, so tentative frames never return as confirmation of the
  extractions they came from.
- **Builds on** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [3.3](#notion-409141b5836981aaa09fc75d3f86b0f5),
  [7.15](#notion-409141b583698126969bdfc3be180171)
- **Feeds** — [9.1](#notion-409141b583698118b18ef02258134fbe)
- **Capabilities** — [O5](https://app.notion.com/p/409141b5836981b9a833f5e9ecf81624)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b583698145b882e140fad3deb7"></a>

### 8.6 · Constraints and axioms

**Status** Proposed · **Order** 806 · **Run wave** 20 · **Downstream reach** 5 · [Notion record](https://app.notion.com/p/409141b583698145b882e140fad3deb7)

- **Join key** — Predicate, entity type
- **What it lets you say** — Proposed rules and constraints mined from the grounded claims: domain and range,
  cardinality, value ranges with units, each classified as a hard constraint, logical rule, soft expectation or open
  possibility. A reported threshold or typical range stays a soft expectation until reviewed; nothing becomes a hard
  constraint by induction alone. Generic-to-instance conflicts show where a candidate fails.
- **Streams used** — [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Builds on** — [5.5](#notion-409141b58369810f96f4e4d695c4c73d), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [7.1](#notion-409141b5836981c6ac16d8729eef6ad4), [7.15](#notion-409141b583698126969bdfc3be180171),
  [8.2](#notion-409141b583698116887fda3ca1c5566d), [8.3](#notion-409141b5836981d2a263cc95f5409062),
  [8.4](#notion-409141b5836981c7b5f2fdf4e0df8cc6)
- **Feeds** — [8.8](#notion-409141b583698140a9f9f1491758b832), [9.2](#notion-409141b58369814cb018c684b83a279a)
- **Capabilities** — [O6](https://app.notion.com/p/409141b5836981e8a185d9b812e496e7)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b5836981f5a2e5dd0134042a82"></a>

### 8.7 · Alignment

**Status** Proposed · **Order** 807 · **Run wave** 17 · **Downstream reach** 1 · [Notion record](https://app.notion.com/p/409141b5836981f5a2e5dd0134042a82)

- **Join key** — Concept ID, external ID
- **What it lets you say** — Induced concepts mapped to reference ontologies; entities already linked to Wikidata
  supply the anchors.
- **Streams used** — [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3),
  [kb](pipeline-streams.md#notion-409141b583698180bb6ec82da7b6e42d)
- **Builds on** — [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [8.1](#notion-409141b58369812f99dbca796e5f7325)
- **Feeds** — [8.8](#notion-409141b583698140a9f9f1491758b832)
- **Capabilities** — [O7](https://app.notion.com/p/409141b5836981dab846d180d79972ce)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="notion-409141b583698140a9f9f1491758b832"></a>

### 8.8 · Growth proposals

**Status** Proposed · **Order** 808 · **Run wave** 22 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b583698140a9f9f1491758b832)

- **Join key** — Change proposal ID
- **What it lets you say** — Proposed additions and changes to the accepted ontology, each packaged with source
  spans, the provenance groups behind it (7.5) and whether the ontology or KB already has it, ready for review.
  Accepted proposals enter the next ontology version; rejected ones are kept with the reason.
- **Streams used** — [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Builds on** — [8.1](#notion-409141b58369812f99dbca796e5f7325), [8.2](#notion-409141b583698116887fda3ca1c5566d),
  [8.3](#notion-409141b5836981d2a263cc95f5409062), [8.6](#notion-409141b583698145b882e140fad3deb7),
  [8.7](#notion-409141b5836981f5a2e5dd0134042a82), [7.5](#notion-409141b583698180ae49d9c346699f52),
  [4.3](#notion-409141b583698169929afb2606b1c8cf)
- **Capabilities** — [O8](https://app.notion.com/p/409141b5836981618757f549ea19055d)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)

<a id="group-tier-9-records-and-control"></a>

## Tier 9 Records and control

<a id="notion-409141b583698118b18ef02258134fbe"></a>

### 9.1 · Assembled records

**Status** Proposed · **Order** 901 · **Run wave** 21 · **Downstream reach** 5 · [Notion record](https://app.notion.com/p/409141b583698118b18ef02258134fbe)

- **Join key** — Record ID
- **What it lets you say** — Definitions, measurements, requirements, formulas, events, action items,
  responsibilities and transactions assembled from qualified claims as one jointly compatible assignment of entity,
  relation, value and condition, not the top-scoring choice per field; useful alternatives and per-field uncertainty
  are kept. Unresolved required roles trigger targeted re-extraction on the spans the ontology points to. The CPU
  LLM, given the record schema through LangExtract, fills only slots still empty after that, and an expected field
  is never filled by invention.
- **Streams used** — [bm25](pipeline-streams.md#notion-409141b58369817c8ac1eb2c96d6f443),
  [emb](pipeline-streams.md#notion-409141b583698173900bfbf18657f719),
  [nuextract](pipeline-streams.md#notion-409141b5836981118a62f0e02a3decf6)
- **Builds on** — [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f), [2.5](#notion-409141b58369813fb393ea90313ceb6a),
  [2.6](#notion-409141b583698165b5cccc4da90536ef), [4.8](#notion-409141b583698120b69fe73e93207120),
  [6.3](#notion-409141b58369816abbbffc5a400dc4c1), [6.5](#notion-409141b58369816f966ce592ba2c3432),
  [8.5](#notion-409141b5836981699240de5dc69f0539)
- **Feeds** — [9.2](#notion-409141b58369814cb018c684b83a279a), [9.3](#notion-409141b58369812aa816deef834ae4b1)
- **Capabilities** — [F2](https://app.notion.com/p/409141b5836981cf913dfd1db81976c4),
  [F3](https://app.notion.com/p/409141b5836981f09a6ef3cb41339db8),
  [F5](https://app.notion.com/p/409141b5836981d3b344f5f28347603e),
  [F8](https://app.notion.com/p/409141b5836981cebdd9f4bcf064ad47),
  [F10](https://app.notion.com/p/409141b58369818393a3e67a32538b7c),
  [F11](https://app.notion.com/p/409141b58369814a9624d9b8042e4ca6),
  [F14](https://app.notion.com/p/409141b583698167b7e6efd1d4ce1e4b),
  [F15](https://app.notion.com/p/409141b5836981b5ac5acf89fe279a1b),
  [V7](https://app.notion.com/p/409141b5836981efb97cc203d060820f)
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-409141b58369814cb018c684b83a279a"></a>

### 9.2 · Executable checks

**Status** Proposed · **Order** 902 · **Run wave** 22 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b58369814cb018c684b83a279a)

- **Join key** — Record ID
- **What it lets you say** — Records validated against the induced shapes and constraints, with unit dimensions and
  formula consistency checked.
- **Streams used** — [valid](pipeline-streams.md#notion-409141b5836981f6b33dcd95abe6ee43)
- **Builds on** — [9.1](#notion-409141b583698118b18ef02258134fbe), [4.8](#notion-409141b583698120b69fe73e93207120),
  [8.6](#notion-409141b583698145b882e140fad3deb7)
- **Feeds** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V4](https://app.notion.com/p/409141b5836981e98d92ec4d659377a0)
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-409141b58369812aa816deef834ae4b1"></a>

### 9.3 · Support and completeness audit

**Status** Proposed · **Order** 903 · **Run wave** 22 · **Downstream reach** 3 · [Notion record](https://app.notion.com/p/409141b58369812aa816deef834ae4b1)

- **Join key** — Record ID, sentence ID
- **What it lets you say** — Whether each output's evidence entails it, and what the source contains that nothing
  extracted: sentences with no claim, table cells with no statement, required slots left empty.
- **Streams used** — [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Builds on** — [9.1](#notion-409141b583698118b18ef02258134fbe), [4.9](#notion-409141b583698123a216d4459f31bd6d),
  [2.3](#notion-409141b58369815fac36e5072a1d652d), [1.3](#notion-409141b583698102ac89ed4c7f82ea8a)
- **Feeds** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9), [9.5](#notion-409141b5836981a699b4eb88173cf9c3)
- **Capabilities** — [V2](https://app.notion.com/p/409141b5836981338261d629a9039854),
  [V9](https://app.notion.com/p/409141b583698161977bc2593714282f)
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-409141b583698193b6b1fb915cf7b4a9"></a>

### 9.4 · Difficulty routing

**Status** Proposed · **Order** 904 · **Run wave** 23 · **Downstream reach** 2 · [Notion record](https://app.notion.com/p/409141b583698193b6b1fb915cf7b4a9)

- **Join key** — Item ID
- **What it lets you say** — A difficulty score per item from what the interpretation layer leaves unresolved, the
  disagreements and failed checks collected along the way, and components over the inference budget. Only those
  items, and what the structured routes cannot reconstruct, go to the CPU LLM or to review.
- **Streams used** — [valid](pipeline-streams.md#notion-409141b5836981f6b33dcd95abe6ee43)
- **Builds on** — [1.2](#notion-409141b5836981f888d4df9c58419c9a), [2.1](#notion-409141b5836981e88660f3eede7253ac),
  [3.2](#notion-409141b58369819fac55ec3d81ffe72e), [4.1](#notion-409141b5836981ca8d66f08b0b61b113),
  [4.3](#notion-409141b583698169929afb2606b1c8cf), [4.5](#notion-409141b5836981508daff27e73a7bfeb),
  [7.4](#notion-409141b5836981e48095d7500fdf9852), [7.15](#notion-409141b583698126969bdfc3be180171),
  [9.2](#notion-409141b58369814cb018c684b83a279a), [9.3](#notion-409141b58369812aa816deef834ae4b1)
- **Feeds** — [9.5](#notion-409141b5836981a699b4eb88173cf9c3), [9.6](#notion-409141b5836981fdb517c06be042bcd3)
- **Capabilities** — [V5](https://app.notion.com/p/409141b5836981e382b4d1a42cd254ce),
  [V6](https://app.notion.com/p/409141b5836981e4bf8df013f685969b)
- **Evidence** — Analogous to Ma 2023 (filter-then-rerank: small models filter by their own uncertainty, an LLM
  reranks hard cases; +2.4% F1 on average). Here the filter is cross-stream disagreement and the LLM is local, so
  this is an analogy, not a replication
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-409141b5836981a699b4eb88173cf9c3"></a>

### 9.5 · Reconciliation and calibration

**Status** Proposed · **Order** 905 · **Run wave** 24 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981a699b4eb88173cf9c3)

- **Join key** — Item ID
- **What it lets you say** — Part of interpretation at every tier, not a final step: outputs from several producers
  merged as observations, each with its score meaning and shared provenance. Calibration targets are defined per
  decision type. Agreement between producers that share training data, encoders or upstream parses is not counted as
  independent evidence, and Snorkel-style aggregation is used only where its conditional-independence assumption has
  been checked.
- **Streams used** — [valid](pipeline-streams.md#notion-409141b5836981f6b33dcd95abe6ee43)
- **Builds on** — [9.3](#notion-409141b58369812aa816deef834ae4b1), [9.4](#notion-409141b583698193b6b1fb915cf7b4a9)
- **Capabilities** — [V5](https://app.notion.com/p/409141b5836981e382b4d1a42cd254ce),
  [V8](https://app.notion.com/p/409141b583698126aaf1c0db2e01ddb9)
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)

<a id="notion-409141b5836981fdb517c06be042bcd3"></a>

### 9.6 · LLM as composer

**Status** Proposed · **Order** 906 · **Run wave** 25 · **Downstream reach** 0 · [Notion record](https://app.notion.com/p/409141b5836981fdb517c06be042bcd3)

- **Join key** — Item ID
- **What it lets you say** — For the residue, and for what the structured routes for findings, procedures, rules,
  obligations, troubleshooting entries, conventions, mathematical results and worked examples cannot reconstruct
  (implicit reasoning, tacit steps, formalization), the LLM receives a pre-grounded context (entities, values,
  qualifiers, argument links, conventions) and composes; it no longer has to extract from scratch. Its contribution
  is measured against the non-generative baseline.
- **Streams used** — [llm](pipeline-streams.md#notion-409141b58369819ab6edc5170de5803d)
- **Builds on** — [9.4](#notion-409141b583698193b6b1fb915cf7b4a9), [5.11](#notion-409141b5836981a6a7b6c0be98a0fe1f),
  [6.2](#notion-409141b5836981278809fc0ca0b6cb51), [3.8](#notion-409141b5836981aab53de3d4c1552549),
  [7.14](#notion-409141b583698124ae54c5b01ed5d035)
- **Capabilities** — [F1](https://app.notion.com/p/409141b5836981d8ad5af3ca5ac0e1a6),
  [F4](https://app.notion.com/p/409141b5836981579de9e1c4c2b79dbf),
  [F6](https://app.notion.com/p/409141b583698172a6b0d011f4cb4d87),
  [F7](https://app.notion.com/p/409141b5836981839e8df2b7aaa37416),
  [F9](https://app.notion.com/p/409141b583698101aa1ed8c55a9de5d8),
  [F12](https://app.notion.com/p/409141b5836981a09184cb7b164e133e),
  [F13](https://app.notion.com/p/409141b5836981eab010ff1e199c7cc4),
  [T5](https://app.notion.com/p/409141b583698149a0e3e52d20ce84ae)
- **Rollout stage** — [Stage 9](stages.md#notion-40a141b5836981469da5da987927234f)
