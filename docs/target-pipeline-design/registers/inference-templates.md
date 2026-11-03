# Inference templates

Notion design snapshot captured 2026-11-03. Source statuses apply to individual records.

[Register index](README.md) · [Notion source](https://app.notion.com/p/2d64c9b112b340509bceb7840f523542?pvs=204) · [First production milestone](../first-production-milestone.md)

Each template ties its decisions to evidence groups, constraints, cross-decision factors, and a measurement. The
numeric-reference example records illustrative LLRs from its reference implementation.

- [Framing priors](#notion-40a141b583698151a102e12297bafa5f)
- [Quantity attachment](#notion-40a141b5836981c8b7f5cef982766d8c)
- [Link, type and cluster](#notion-40a141b5836981ac9029da913d0e7891)
- [Relation and argument types](#notion-40a141b583698123b468ca9cd6dee971)
- [Table to record](#notion-40a141b583698158bec4e7f2fffdc7ea)
- [Condition scope and qualifiers](#notion-40a141b58369814c9c37f5eca1ff9b32)
- [Numeric reference and value role](#notion-40a141b58369814c9058f2d9adbaf84b)
- [Claim-pair argument](#notion-40a141b5836981a28e53d4643cdf65af)
- [Cross-document identity and support](#notion-40a141b583698170bb84d92ee407418e)
- [Ontology proposal scoring](#notion-40a141b5836981e5ae24d4776483ac13)

<a id="notion-40a141b583698151a102e12297bafa5f"></a>

## Framing priors

**Status** Target · **Prototype** None · [Notion record](https://app.notion.com/p/40a141b583698151a102e12297bafa5f)

- **Decisions** — [Block type](decision-types.md#notion-40a141b583698177bc9fc4d13b6e5241), [Section
  role](decision-types.md#notion-40a141b5836981a190d9f9e059b56b47), [Document
  type](decision-types.md#notion-40a141b58369819eb13fefec7f65ea2a),
  [Language](decision-types.md#notion-40a141b58369813fb569c34ee2303b90), [Reliability
  grade](decision-types.md#notion-40a141b5836981d891dfc66564b447c4)
- **Stream groups** — layout
- **Cross-decision factors** — Section role × heading class × position; document type × section role; language ×
  script.
- **Hard constraints** — Hard gates only where precision clears τ\_gate: block types, reference lists, language,
  exact duplicates.
- **Measured by** — Gate precision; calibration of the quality score; extractor accuracy by reliability grade.
- **Evidence streams** — [layout](pipeline-streams.md#notion-409141b583698151b511eec44610bd65),
  [genre](pipeline-streams.md#notion-409141b58369818abe2beb2ce219c7f8),
  [lang](pipeline-streams.md#notion-409141b5836981ab9afaeb69b5d5ae32),
  [quality](pipeline-streams.md#notion-409141b5836981599a32fb76e77c07a7),
  [dedup](pipeline-streams.md#notion-409141b5836981f59f41c0ed9052e70b)
- **Rollout stage** — [Stage 1](stages.md#notion-40a141b5836981eeae7fe462e5c2a68d)

<a id="notion-40a141b5836981c8b7f5cef982766d8c"></a>

## Quantity attachment

**Status** Target · **Prototype** P1 Quantities and references · [Notion record](https://app.notion.com/p/40a141b5836981c8b7f5cef982766d8c)

- **Decisions** — [Mention span and type](decision-types.md#notion-40a141b583698175ad4feb290edc9e18), [Concept vs
  named entity](decision-types.md#notion-40a141b5836981209660dda3e2bd7285), [Unit and
  dimension](decision-types.md#notion-40a141b5836981e58f4bcf79b8ac8d7e), [Value
  attachment](decision-types.md#notion-40a141b58369810fa965ef1cbd022370), [Abbreviation
  expansion](decision-types.md#notion-40a141b58369817b91b9d794c442e2b1), [Symbol
  binding](decision-types.md#notion-40a141b583698161b6bcdd2b699f581f)
- **Stream groups** — quantities, parse, mentions, ontology
- **Cross-decision factors** — Unit dimension × property; attachment × dependency path; type votes from one model
  family as one factor; definition × acronym; genericity × concept vs entity.
- **Hard constraints** — A unit's dimension must match the property's dimension in the ontology.
- **Measured by** — Attachment on 100 hand-checked numbers at matched coverage; I(quantities, parse) and
  I(quantities, ontology).
- **Evidence streams** — [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8),
  [concepts](pipeline-streams.md#notion-409141b58369810cb26dc09c30bf542d),
  [abbr](pipeline-streams.md#notion-409141b583698146b66fc2dbbaf22d8e),
  [formula](pipeline-streams.md#notion-409141b583698127815fd85f864c0fdd)
- **Rollout stage** — [Stage 2](stages.md#notion-40a141b583698196b5b4c5cc6ab20865)

<a id="notion-40a141b5836981ac9029da913d0e7891"></a>

## Link, type and cluster

**Status** Target · **Prototype** P2 Identity type and relation · [Notion record](https://app.notion.com/p/40a141b5836981ac9029da913d0e7891)

- **Decisions** — [Cluster membership](decision-types.md#notion-40a141b58369818fa634dfbef9760d85), [Entity
  link](decision-types.md#notion-40a141b5836981aeb37bfa048dc12ee3), [Instance vs
  class](decision-types.md#notion-40a141b5836981a3a482edc420ae8ce9)
- **Stream groups** — identity, mentions, ontology
- **Cross-decision factors** — Link × type compatibility; cluster × link (penalty when one cluster links to
  different IDs); instance × class.
- **Hard constraints** — Linked class must be compatible with the span type under the ontology hierarchy.
- **Measured by** — Fixed-candidate vs end-to-end; ontology-factor ablation; NIL-reason accuracy; Shapley over
  mentions, identity and ontology.
- **Evidence streams** — [coref](pipeline-streams.md#notion-409141b5836981768728e731d44f5fff),
  [el](pipeline-streams.md#notion-409141b583698179988cc7290f49ed7e),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8),
  [kb](pipeline-streams.md#notion-409141b583698180bb6ec82da7b6e42d),
  [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Rollout stage** — [Stage 3](stages.md#notion-40a141b5836981bf816cfaf0bb095839)

<a id="notion-40a141b583698123b468ca9cd6dee971"></a>

## Relation and argument types

**Status** Target · **Prototype** P2 Identity type and relation · [Notion record](https://app.notion.com/p/40a141b583698123b468ca9cd6dee971)

- **Decisions** — [Relation label and direction](decision-types.md#notion-40a141b583698127b0ddfc36c059cad8)
- **Stream groups** — identity, mentions, ontology
- **Cross-decision factors** — Relation × argument types × ontology signature, refitted jointly with the stage 3
  template so a strong relation can correct an uncertain type.
- **Hard constraints** — Domain and range from the relation signature.
- **Measured by** — Domain and range violation rate; change in stage 3 numbers after the joint refit.
- **Evidence streams** — [rel](pipeline-streams.md#notion-409141b5836981578850f08fd787f43d),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8),
  [el](pipeline-streams.md#notion-409141b583698179988cc7290f49ed7e),
  [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b583698158bec4e7f2fffdc7ea"></a>

## Table to record

**Status** Target · **Prototype** P3 Tables to records · [Notion record](https://app.notion.com/p/40a141b583698158bec4e7f2fffdc7ea)

- **Decisions** — [Table column role](decision-types.md#notion-40a141b583698149ba2bc4be7294677e), [Column
  property](decision-types.md#notion-40a141b5836981279df7c46735c17b17), [Row
  entity](decision-types.md#notion-40a141b5836981508fb9c58175ee09b9)
- **Stream groups** — tables, quantities, identity, ontology
- **Cross-decision factors** — Column property × header class × unit × row-entity type; text value × table cell for
  the same entity and property (one record, two derivations joined by ⊕).
- **Hard constraints** — Column unit dimension must match the column property; one key column per table region.
- **Measured by** — Complete-record correctness for tables, including condition and note attachment; assembly gain
  (rules minus union).
- **Evidence streams** — [tables](pipeline-streams.md#notion-409141b583698117b2e1c0b7067f2537),
  [tabstmt](pipeline-streams.md#notion-409141b58369810eba6fc542f1f9608a),
  [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [el](pipeline-streams.md#notion-409141b583698179988cc7290f49ed7e),
  [ents](pipeline-streams.md#notion-409141b5836981269418d6ef5cf167c8)
- **Rollout stage** — [Stage 4](stages.md#notion-40a141b5836981c1b905ff7cee627528)

<a id="notion-40a141b58369814c9c37f5eca1ff9b32"></a>

## Condition scope and qualifiers

**Status** Target · **Prototype** P1 Quantities and references · [Notion record](https://app.notion.com/p/40a141b58369814c9c37f5eca1ff9b32)

- **Decisions** — [Polarity](decision-types.md#notion-40a141b5836981f0b698fd9a751c3540), [Author
  modality](decision-types.md#notion-40a141b5836981bc9cedcc12b2557115), [Condition
  scope](decision-types.md#notion-40a141b5836981ee8bdbc9ab27aac913),
  [Genericity](decision-types.md#notion-40a141b583698104b845f1f342fe07ef),
  [Attribution](decision-types.md#notion-40a141b583698150be1addc307c03107), [Valid
  time](decision-types.md#notion-40a141b5836981e6b3c9d09b73d402d0)
- **Stream groups** — conditions, parse, identity, quantities
- **Cross-decision factors** — Condition scope × numeric referent × frame role; value role × section role × cue
  words; genericity × instance vs class × determiner and tense.
- **Hard constraints** — A condition's interval must be on a quantity whose dimension matches the governed variable.
- **Measured by** — About 200 hand-labelled sentences per qualifier; a positive disambiguation term; calibrated
  interpretation confidence per qualifier.
- **Evidence streams** — [lex](pipeline-streams.md#notion-409141b5836981e5b923f097afd80915),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce),
  [concepts](pipeline-streams.md#notion-409141b58369810cb26dc09c30bf542d)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

<a id="notion-40a141b58369814c9058f2d9adbaf84b"></a>

## Numeric reference and value role

**Status** Prototyped · **Prototype** P1 Quantities and references · [Notion record](https://app.notion.com/p/40a141b58369814c9058f2d9adbaf84b)

- **Decisions** — [Numeric referent](decision-types.md#notion-40a141b58369817da69becef271f7f4c), [Value
  role](decision-types.md#notion-40a141b5836981538fafda1bbecb4339)
- **Stream groups** — quantities, parse, conditions, ontology
- **Cross-decision factors** — Frame slot couples the reference decision to the referent's role decision: picking
  quantity q rewards q's role matching the slot's expected role.
- **Hard constraints** — A referent must have the head noun's unit dimension ("this pressure" cannot denote a flow
  rate).
- **Measured by** — Pump example: Shapley values and Möbius dividends over units, proximity and frames; gain
  decomposition by mechanism.
- **Code reference** — Branch claude/project-thread-dvf80m,
  `python/corpus-structure/src/corpus_structure/interpret/templates/numeric_reference.py` (not merged)
- **Evidence streams** — [quant](pipeline-streams.md#notion-409141b5836981d08cb6c348f47e1b8c),
  [coref](pipeline-streams.md#notion-409141b5836981768728e731d44f5fff),
  [parse](pipeline-streams.md#notion-409141b5836981308366f134d0ab9373),
  [lex](pipeline-streams.md#notion-409141b5836981e5b923f097afd80915)
- **Rollout stage** — [Stage 5](stages.md#notion-40a141b583698172b462e8ef1e246de3)

### What it resolves

In the pump passage, the reference "this pressure" could denote any of the three earlier quantities (2 bar, 120 m³/h, 100 m³/h), or none of them. The passage itself and its full trace through the tiers are on [🔬 Worked example: one passage through the tiers](https://app.notion.com/p/40b141b583698129b75bf8c46cd01965), the only copy.

### Decisions

- ref:this\_pressure ∈ \{q\_2bar, q\_120, q\_100, UNKNOWN\}
- role:q for each quantity ∈ \{condition\_threshold, measured, rated, UNKNOWN\}

### Evidence by stream group

| Group | Evidence | Kind |
| --- | --- | --- |
| units | Each quantity's dimension from pint | Hard constraint on the referent |
| proximity | Antecedent LLRs: q\_100 +2.0, q\_2bar +1.5, q\_120 +0.5 | Unary on the reference |
| frames | Role cues ("above" → threshold, "delivered" → measured, "rating" → rated), each +2.0; slot "cavitate below X" expects a threshold, +1.5 | Unary on roles; pairwise reference × role |

### Results (reference implementation, 31 Oct 2026, illustrative LLRs)

| Groups present | P(ref = 2 bar) | Accepted at τ = 0.75? |
| --- | --- | --- |
| proximity | 0.51 for the wrong 100 m³/h | No, so no error is accepted |
| units | 0.50 | No |
| frames | 0.49 | No |
| units + proximity | 0.82 | Yes |
| units + frames | 0.78 | Yes |
| proximity + frames | 0.54 | No, but the argmax flips to the correct answer |
| all three | 0.94 | Yes |

Möbius dividends for the reference record: +1 for units × proximity, +1 for units × frames, −1 for all three (the two routes overlap). Shapley values: units 0.67, proximity 0.17, frames 0.17. The value is entirely synergy: no group resolves the reference alone. Units do most of the work, but only because the other two exist to be corrected.

### Next

Replace the illustrative LLRs with calibrated ones from the 20-document sample, add the condition-scope decision (which proposition "may cavitate below" governs), and add section role from stage 1 as a value-role factor.

### Mathematics

The factor model this template runs, and why its synergy sits in the reference × role factor, are on [🕸️ Joint model and calibration](https://app.notion.com/p/40b141b583698193ab8fd8313f46b0f5). The dividends and Shapley values above are defined on [➕ Value function and synergy](https://app.notion.com/p/40b141b5836981778e63c81add619c75), the acceptance threshold on [⚖️ Acceptance and escalation](https://app.notion.com/p/40b141b5836981f7ac70e9d7fa7cef88), and the measurement plan on [📏 Measuring the synergy](https://app.notion.com/p/40b141b58369815e898fd46f2b34bfdd).

<a id="notion-40a141b5836981a28e53d4643cdf65af"></a>

## Claim-pair argument

**Status** Target · **Prototype** None · [Notion record](https://app.notion.com/p/40a141b5836981a28e53d4643cdf65af)

- **Decisions** — [Claim-pair relation](decision-types.md#notion-40a141b5836981f6a791cd4816270381)
- **Stream groups** — conditions, parse
- **Cross-decision factors** — Support or attack × polarity and attribution of both claims; NLI scores as calibrated
  evidence; discourse-link prior; proximity.
- **Hard constraints** — None; support and entailment stay separate variables.
- **Measured by** — Interaction of NLI with discourse and proximity; pair candidate recall.
- **Evidence streams** — [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284),
  [disc](pipeline-streams.md#notion-409141b5836981ebb77dee17699cd7ce),
  [arg](pipeline-streams.md#notion-409141b5836981ab84bffe7436ced61c)
- **Rollout stage** — [Stage 6](stages.md#notion-40a141b58369817c9929cc494bc2c061)

<a id="notion-40a141b583698170bb84d92ee407418e"></a>

## Cross-document identity and support

**Status** Target · **Prototype** None · [Notion record](https://app.notion.com/p/40a141b583698170bb84d92ee407418e)

- **Decisions** — [Cross-document identity](decision-types.md#notion-40a141b5836981e9bdc5e3b47dc91437), [Claim
  equivalence](decision-types.md#notion-40a141b5836981bf9a1cd380fd6d7492)
- **Stream groups** — corpus
- **Cross-decision factors** — Splink match weights as LLRs; claim equivalence × NLI; contradiction as same
  proposition × opposite polarity × overlapping condition; provenance groups with dependence discount.
- **Hard constraints** — Interval overlap is deterministic.
- **Measured by** — Contradiction and equivalence precision at τ on 50 cases each; sensitivity of support to ρ.
- **Evidence streams** — [splink](pipeline-streams.md#notion-409141b58369816d80fcf751582e646c),
  [claim\_emb](pipeline-streams.md#notion-409141b5836981e4b650dbcd7ea604e1),
  [nli](pipeline-streams.md#notion-409141b58369816ea14af7169d6ca284)
- **Rollout stage** — [Stage 7](stages.md#notion-40a141b58369816a9c70f23c650234aa)

<a id="notion-40a141b5836981e5ae24d4776483ac13"></a>

## Ontology proposal scoring

**Status** Target · **Prototype** None · [Notion record](https://app.notion.com/p/40a141b5836981e5ae24d4776483ac13)

- **Decisions** — [Ontology proposal](decision-types.md#notion-40a141b58369812687cec708fdb42419)
- **Stream groups** — ontology, corpus
- **Cross-decision factors** — Support log-odds from stage 7 × compatibility with ontology v0.
- **Hard constraints** — A proposal that contradicts an accepted hard constraint is rejected outright.
- **Measured by** — Change in V from v0 to v1 on held-out documents only.
- **Evidence streams** — [onto](pipeline-streams.md#notion-409141b5836981479afdf1e51ac86be3)
- **Rollout stage** — [Stage 8](stages.md#notion-40a141b58369811992a0c8007723a20b)
