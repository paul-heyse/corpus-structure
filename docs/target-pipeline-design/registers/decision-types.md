# Decision types

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/bea78039da9b4df887435988c0d1bac4?pvs=204) · [First production milestone](../first-production-milestone.md)

Each decision has bounded candidates with an UNKNOWN option. All 30 source rows have unset value v, cost c, and
conformal α. The threshold formula is τ = c / (c + v), rounded to three places in the source register. The returned
formula references are handles. The register defines a blank threshold until v and c are set.

<a id="notion-40a141b583698177bc9fc4d13b6e5241"></a>

## Block type

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698177bc9fc4d13b6e5241)

- **Candidate generator** — Docling layout model
- **Options** — Docling layout classes (text, title, list item, table, figure, caption, footnote, formula, page
  furniture) + UNKNOWN
- **Record type** — Framing record
- **Template** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b58369819eb13fefec7f65ea2a"></a>

## Document type

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369819eb13fefec7f65ea2a)

- **Candidate generator** — GLiNER2.5 over title, headings and first paragraphs
- **Options** — Paper, standard, datasheet, report, manual, thesis + UNKNOWN
- **Record type** — Framing record
- **Template** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b58369813fb569c34ee2303b90"></a>

## Language

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369813fb569c34ee2303b90)

- **Candidate generator** — GlotLID
- **Options** — GlotLID top languages + UNKNOWN
- **Record type** — Framing record
- **Template** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b5836981d891dfc66564b447c4"></a>

## Reliability grade

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981d891dfc66564b447c4)

- **Candidate generator** — Text-quality score plus Docling recognition health (text layer vs OCR, layout and table
  confidence)
- **Options** — Clean, degraded, garbled + UNKNOWN
- **Record type** — Framing record
- **Template** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b5836981a190d9f9e059b56b47"></a>

## Section role

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981a190d9f9e059b56b47)

- **Candidate generator** — Docling hierarchy plus GLiNER2.5 heading classes
- **Options** — Abstract, introduction, methods, results, discussion, specification, references, appendix + UNKNOWN
- **Record type** — Framing record
- **Template** — [Framing priors](inference-templates.md#notion-40a141b583698151a102e12297bafa5f)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b58369817b91b9d794c442e2b1"></a>

## Abbreviation expansion

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369817b91b9d794c442e2b1)

- **Candidate generator** — Schwartz–Hearst pairs
- **Options** — Long forms in the document + UNKNOWN
- **Record type** — Typed mention
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b5836981209660dda3e2bd7285"></a>

## Concept vs named entity

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981209660dda3e2bd7285)

- **Candidate generator** — GLiNER concept labels plus Stanza genericity flag
- **Options** — Concept, named entity + UNKNOWN
- **Record type** — Typed mention
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b583698175ad4feb290edc9e18"></a>

## Mention span and type

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698175ad4feb290edc9e18)

- **Candidate generator** — GLiNER2.5 and GLiNER bi-encoder (one correlated factor)
- **Options** — Ontology types for the span + UNKNOWN
- **Record type** — Typed mention
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b583698161b6bcdd2b699f581f"></a>

## Symbol binding

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698161b6bcdd2b699f581f)

- **Candidate generator** — Docling formula enrichment plus the repository's symbol-scope methods
- **Options** — Defining expressions in scope + UNKNOWN
- **Record type** — Attached quantity
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b5836981e58f4bcf79b8ac8d7e"></a>

## Unit and dimension

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981e58f4bcf79b8ac8d7e)

- **Candidate generator** — CQE and pint
- **Options** — pint unit parses with their dimensions + UNKNOWN
- **Record type** — Attached quantity
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b58369810fa965ef1cbd022370"></a>

## Value attachment

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369810fa965ef1cbd022370)

- **Candidate generator** — CQE noun phrase plus Stanza dependency paths
- **Options** — Noun phrases in the sentence window + UNKNOWN
- **Record type** — Attached quantity
- **Template** — [Quantity attachment](inference-templates.md#notion-40a141b5836981c8b7f5cef982766d8c)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b58369818fa634dfbef9760d85"></a>

## Cluster membership

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369818fa634dfbef9760d85)

- **Candidate generator** — Maverick coreference
- **Options** — Pairwise link or no link within a bounded window + UNKNOWN
- **Record type** — Grounded entity
- **Template** — [Link, type and cluster](inference-templates.md#notion-40a141b5836981ac9029da913d0e7891)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-40a141b5836981aeb37bfa048dc12ee3"></a>

## Entity link

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981aeb37bfa048dc12ee3)

- **Candidate generator** — ReFinED plus ontology known entities
- **Options** — KB and ontology candidates + NIL with reason (local entity, insufficient context, retrieval failure,
  ambiguity, new concept)
- **Record type** — Grounded entity
- **Template** — [Link, type and cluster](inference-templates.md#notion-40a141b5836981ac9029da913d0e7891)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-40a141b5836981a3a482edc420ae8ce9"></a>

## Instance vs class

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981a3a482edc420ae8ce9)

- **Candidate generator** — Determiner and genericity features
- **Options** — Instance, class + UNKNOWN
- **Record type** — Grounded entity
- **Template** — [Link, type and cluster](inference-templates.md#notion-40a141b5836981ac9029da913d0e7891)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-40a141b5836981279df7c46735c17b17"></a>

## Column property

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981279df7c46735c17b17)

- **Candidate generator** — GLiNER2.5 on header text
- **Options** — Ontology properties compatible with the column's units + UNKNOWN
- **Record type** — Measurement or specification record
- **Template** — [Table to record](inference-templates.md#notion-40a141b583698158bec4e7f2fffdc7ea)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b583698127b0ddfc36c059cad8"></a>

## Relation label and direction

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698127b0ddfc36c059cad8)

- **Candidate generator** — GLiNER-Relex
- **Options** — Ontology relations in both directions + none + UNKNOWN
- **Record type** — Relation record
- **Template** — [Relation and argument types](inference-templates.md#notion-40a141b583698123b468ca9cd6dee971)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b5836981508fb9c58175ee09b9"></a>

## Row entity

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981508fb9c58175ee09b9)

- **Candidate generator** — ReFinED with the column type as prior
- **Options** — Entity candidates for the key cell + UNKNOWN
- **Record type** — Measurement or specification record
- **Template** — [Table to record](inference-templates.md#notion-40a141b583698158bec4e7f2fffdc7ea)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b583698149ba2bc4be7294677e"></a>

## Table column role

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698149ba2bc4be7294677e)

- **Candidate generator** — Docling cells with column profiling
- **Options** — Key, measure, dimension + UNKNOWN
- **Record type** — Measurement or specification record
- **Template** — [Table to record](inference-templates.md#notion-40a141b583698158bec4e7f2fffdc7ea)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b583698150be1addc307c03107"></a>

## Attribution

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698150be1addc307c03107)

- **Candidate generator** — Reporting-verb lexicon plus citation markers
- **Options** — The document's authors, a cited source, a named party + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981bc9cedcc12b2557115"></a>

## Author modality

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981bc9cedcc12b2557115)

- **Candidate generator** — Hedge and deontic cue lexicons
- **Options** — Asserted, hedged, possible, required + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981ee8bdbc9ab27aac913"></a>

## Condition scope

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981ee8bdbc9ab27aac913)

- **Candidate generator** — Condition cue lexicon, Stanza scope, Dipo condition links (soft)
- **Options** — Propositions in the sentence window + both + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b583698104b845f1f342fe07ef"></a>

## Genericity

**Status** Target · [Notion record](https://app.notion.com/p/40a141b583698104b845f1f342fe07ef)

- **Candidate generator** — Stanza parse genericity flag
- **Options** — Generic, specific + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b58369817da69becef271f7f4c"></a>

## Numeric referent

**Status** Prototyped · [Notion record](https://app.notion.com/p/40a141b58369817da69becef271f7f4c)

- **Candidate generator** — Quantities from stage 2 within the sentence window
- **Options** — Quantities in the preceding window + operating variable + UNKNOWN
- **Record type** — Numeric reference
- **Template** — [Numeric reference and value role](inference-templates.md#notion-40a141b58369814c9058f2d9adbaf84b)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981f0b698fd9a751c3540"></a>

## Polarity

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981f0b698fd9a751c3540)

- **Candidate generator** — Negation cue lexicon over the parse
- **Options** — Affirmed, negated + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981e6b3c9d09b73d402d0"></a>

## Valid time

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981e6b3c9d09b73d402d0)

- **Candidate generator** — Duckling and dateparser
- **Options** — Normalized dates and intervals in scope + UNKNOWN
- **Record type** — Qualified claim
- **Template** — [Condition scope and qualifiers](inference-templates.md#notion-40a141b58369814c9c37f5eca1ff9b32)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981538fafda1bbecb4339"></a>

## Value role

**Status** Prototyped · [Notion record](https://app.notion.com/p/40a141b5836981538fafda1bbecb4339)

- **Candidate generator** — Cue words, section role, frame slots
- **Options** — Measured, rated, predicted, required, condition threshold + UNKNOWN
- **Record type** — Value role
- **Template** — [Numeric reference and value role](inference-templates.md#notion-40a141b58369814c9058f2d9adbaf84b)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b5836981f6a791cd4816270381"></a>

## Claim-pair relation

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981f6a791cd4816270381)

- **Candidate generator** — Dipo links, then a proximity window
- **Options** — Support, attack, none + UNKNOWN
- **Record type** — Argument edge
- **Template** — [Claim-pair argument](inference-templates.md#notion-40a141b5836981a28e53d4643cdf65af)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-40a141b5836981bf9a1cd380fd6d7492"></a>

## Claim equivalence

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981bf9a1cd380fd6d7492)

- **Candidate generator** — Claim embeddings and reranking
- **Options** — Equivalent, contradictory, unrelated + UNKNOWN
- **Record type** — Corpus support
- **Template** — [Cross-document identity and
  support](inference-templates.md#notion-40a141b583698170bb84d92ee407418e)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-40a141b5836981e9bdc5e3b47dc91437"></a>

## Cross-document identity

**Status** Target · [Notion record](https://app.notion.com/p/40a141b5836981e9bdc5e3b47dc91437)

- **Candidate generator** — Splink blocking rules
- **Options** — Match, non-match + UNKNOWN
- **Record type** — Corpus entity
- **Template** — [Cross-document identity and
  support](inference-templates.md#notion-40a141b583698170bb84d92ee407418e)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-40a141b58369812687cec708fdb42419"></a>

## Ontology proposal

**Status** Target · [Notion record](https://app.notion.com/p/40a141b58369812687cec708fdb42419)

- **Candidate generator** — Tier 8 induction (AMIE, sheXer and term candidates)
- **Options** — Accept as hard constraint, logical rule, soft expectation, open possibility; reject
- **Record type** — Ontology change
- **Template** — [Ontology proposal scoring](inference-templates.md#notion-40a141b5836981e5ae24d4776483ac13)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)
