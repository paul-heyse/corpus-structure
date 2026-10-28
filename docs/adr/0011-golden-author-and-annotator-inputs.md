---
id: ADR-0011
title: Author goldens with Sonnet from generated annotator inputs and query-assembled context
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: []
evidence: Measured
---

## Context

D7 §3 had Opus write goldens: two blind Opus passes and an Opus adjudication session, each given
the guideline, the schema, the unit packet with standing context chosen by position ("previous
binding sentences in the same section") and the page's full text. Spike S0 and its revisit S0-R2
(`docs/design_review/evidence/2026-10-28_design-spikes/`, reports S0 and S0-R2) measured who can do
this work and what they need:

- On the v0 inputs, Sonnet 5.5 and Haiku 5.5 matched Opus on *what* is claimed but trailed on
  qualifiers. The losses sat where the inputs left a convention unstated: statement roles, which
  claims carry conditions, symbol bindings. They also sat where positional context misled: one
  exercise received another's setup, and a premise stated before the unit was missing. The
  reference itself had taken Opus's readings at those points.
- On inputs v1, Sonnet working from unit packets alone reached full-tier F1 0.77 against the
  reference conformed to v1, against 0.37 on v0. Inputs v1 consisted of:
  - written conventions (guideline v1);
  - an annotator reference generated from the schema, with worked examples;
  - standing context assembled from M13 binding sites, each sentence citable;
  - guideline-rule warnings from the validator.

  The Opus v0 passes scored 0.68. Before a three-item reference correction found by reading the
  Sonnet pass, the figures were 0.72 and 0.71–0.72. Haiku reached 0.68, up from 0.35. Sonnet
  against Haiku agreed at 0.76 on six units from pages no rule was written from.
- A Sonnet adjudicator over a Sonnet and a Haiku pass scored 0.75: no gain over the Sonnet pass.
  The v0 Sonnet adjudicator over the two Opus passes reached 0.97 core and 0.82 full against the
  root's reference, where the Haiku adjudicator reached 0.74 full.

The operator chose Sonnet on 2026-10-28 ("it looks like sonnet is the right call, and the rules
establish a clear approach").

## Options

1. **Keep Opus as golden author (D7 as written).** It is the strongest model. On the v0 inputs its
   lead over the smaller models came from conventions it happened to share with a reference built
   from its own passes, so most of the lead is not capability. Its cost and the circularity risk
   remain: goldens and the pipeline's escalation tier would be the same model.
2. **Haiku as author.** It is the cheapest. On inputs v1 it reached 0.68, close to the Opus v0
   passes, but its first drafts needed more repair and its agreement with Sonnet is lower on the
   core units (0.57). It is viable as a second pass, weaker as the sole author.
3. **Sonnet as author, with the v1 inputs.** It matched or exceeded the Opus passes from packets
   alone, its drafts needed the least repair (one unit in eighteen), and it adjudicated close to
   the root.
4. **Better inputs for any model, without fixing the author.** This option is necessary for every
   other one and not sufficient by itself: the golden protocol still has to name its author, its
   inputs and what adjudication is for.

## Decision

Option 3, with option 4's inputs as part of the protocol:

- **Author.** Both blind golden passes and the golden adjudication session are fresh Sonnet 5.5
  subagents dispatched by the Claude Code session. The model is a recorded configuration of the
  golden protocol (`eval.golden_pass` records it), not a name in the design. Changing it is a
  revisit of this record.
- **Inputs.** Each pass receives:
  - the guideline;
  - the annotator reference generated from the schema version (D2 §10.10): every entity type, every
    predicate with its statement role, modality and condition rule, the qualifiers, the enums, the
    exact value and node shapes, and complete worked examples drawn from outside every golden split;
  - the output format;
  - the unit packet.

  The packet's standing context is assembled by query: for each symbol the unit uses, the
  sentence holding the binding site M13 assigns it, when that sentence lies outside the unit, plus
  the site a "Suppose again" reopens. Each context sentence is citable as evidence. The page's full
  text is not given.
- **Validation.** The batch validator reports guideline-rule violations as warnings alongside format
  and invariant errors, and a pass fixes them or says why the rule does not apply.
- **Adjudication** stays a fresh session given the guideline, the reference, the packet, both passes
  and their alignment. Its role is to decide contested items and record guideline gaps. It is not
  expected to raise a batch above its better pass.
- **Out of scope:** the pipeline's agent tier, meaning the Claude Code session working the
  intervention queue (D0, D6, D8 M24), stays Opus and is unchanged by this record.

## Consequences

- D7 §1, §2, §3.2 and §3.4 name Sonnet and the v1 inputs; D7 §6's witnesses guard against errors
  shared by the golden author's passes; D0's actor table separates golden authoring from the agent
  tier; D2 §10.10 is the generated reference; D2 §7.3 lets evidence cite context sentences; D2 §7.4
  compiles the checkable rules as warnings; D4 §4.1 and D8 §3 assemble standing context by query.
  The spike lane's evidence records are the source of every figure.
- **Circularity is reduced:** goldens are no longer written by the model the pipeline escalates to,
  so a pipeline tuned toward Opus's habits is not rewarded by Opus-written goldens.
- **Guideline v1** (the S0-R2 candidate) becomes D2 §10. Its open points are recorded there as open
  questions: indexed-family arguments need a schema construct; the premises a claim uses rather
  than every premise; and the remaining smaller gaps.
- **What is established.** Measured on twelve core units and six held-out units, one pass per model.
  Implemented in the spike instruments only: the production golden tools (D8 `write_golden`) and
  the reference generator remain to be built in phase 0.
- **Open:** whether page text still helps under v1 (not run), and whether Opus also gains from v1
  (not run).

**Revisit when** a golden-set agreement measurement on a new domain or a new guideline version
shows Sonnet passes below the ceiling the protocol needs, or a new model generation changes the
cost or quality balance.
