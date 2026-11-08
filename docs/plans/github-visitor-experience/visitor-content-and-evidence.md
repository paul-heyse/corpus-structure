# Visitor content and source-linked evidence

**Status · 2026-11-08. Proposed.** Owns the GHV-02 and GHV-03 designs. The
[coordinator](../github-visitor-experience_2026-11-08.md) owns execution and
qualification. This companion implements the editorial and evidence routes from
[O01](../../functional_reviews/github-visitor-experience_2026-11-08.md#O01),
[O02](../../functional_reviews/github-visitor-experience_2026-11-08.md#O02) and
[O04](../../functional_reviews/github-visitor-experience_2026-11-08.md#O04).

<a id="GHV-02"></a>

## GHV-02 · Visitor-first README and documentation routes

The README and documentation owners work from the current checkpoint, the
architecture map and reviewed output. Use **Corpus Structure** and the tagline
**From documents to connected, source-grounded knowledge.** Explain how progressive
enrichment preserves useful local observations and partial interpretations.
Introduce what a source anchor does before naming its internal representation.
Place a compact navigation line under the introduction, then the functional figure
and a real example. Use the proposed 900–1,300 words as a scale guide. The normal
reading path should explain the system before reaching development or agent instructions.
[Current README](../../../README.md) · [Status](../../../STATUS.md) · [Knowledge representation](../../design/D1-knowledge-representation.md)

Describe what is implemented through outputs a visitor can inspect. Cover document
intake and source anchoring, linguistic and semantic extraction, contextual linking,
structural comparisons, rooted assembly, and granular assessment. The engineering
section explains progressive representation, typed distinctions, traceable derivation,
and evaluation at the operation being assessed. Use 518 physical pages and 29
selected source views with their denominators identified. Report the review of nine
retained contextual cues alongside the checked references that did not enter
retrieval. Keep test counts and wider corpus coverage claims in their evidence.
Include a short maturity statement and the author attribution. Add the documentation
badge after a verified hosted run and keep language and status indicators restrained.
[Whole-book output review](../../design_review/evidence/2026-11-08_nce-full-book/review/README.md) · [Scoped citation assessment](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations)

Make Overview, Examples, Architecture, Evaluation and Running locally prominent
in the existing documentation entry points. Use ordinary Markdown links and the
existing site selection. Give the examples index a Current entry and keep deep
reviews discoverable through direct links and expanded search. Keep the architectural
map's section labels and historical rationale. Replace its blanket maturity wording,
and add a short current reading route before D0's dated target. Use the same stable
section IDs for readers arriving from old links.
[Documentation index](../../README.md) · [Architecture map](../../design/README.md) · [D0](../../design/D0-target-overview.md) · [Site selection](../../site.toml)

Provide a short code-reading route organized by reader questions. Link source capture
to PDF section views and their SQL contract, observation production to GLiNER, typed
relationships to contextual links, and inspection to the Reader and MCP. Link
operation-level assessment separately.
[PDF section views](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py) · [Source-view SQL](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql) · [GLiNER method](../../../python/corpus-structure/src/corpus_structure/methods/gliner.py) · [Contextual links](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py) · [Operation assessment](../../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py) · [Reader and agent interfaces](../../design/D8-agent-and-query-interfaces.md)

**Closure.** A reader can find all four actions from the opening and explain the
output and its evidence using the README alone. Check the same journeys in the
built site. Follow architecture and evidence links back to the owners. If a
capability lacks current evidence, narrow its maturity wording. Check development
instructions against existing command owners and keep status in STATUS and plans.

<a id="GHV-03"></a>

## GHV-03 · Worked evidence and reproduction instructions

The examples owner uses the retained source and independently reviewed cases as
inputs. The README displays the citation as a compact source-to-result walkthrough.
Put the supporting span, witness, and assessment details on the examples page,
using accessible Markdown with optional expandable receipt details. Keep the
plain-text facts useful at mobile width and without a companion image.

| Example | Required retained meaning |
| --- | --- |
| Printed cross-reference | “Section 5.1” on physical page 260, `#/texts/4682[69:80)`, leads via `cites-section` to “Important Distributions” on page 191, `#/texts/3495[0:27)`. Link the explicit source-cue witness and edge prefix `27b19068cdac` to run 327, cut 447, task 1528. Distinguish the producer's preferred edge from the dated assessment of the printed citation. |
| Qualified local meaning | Show the page 289 positive-variance assumption at `#/texts/5253[3:57)` attached to `defined` at `[89:96)`, edge `1407260e0e7e6a`. Explain the scope of the reviewed attachment. |
| Useful uncertainty | Show the retained candidate list and withheld affine-`X` link. Present the recovered `Z` occurrence and its declaration link as a separate case with separate receipts. |
| Enterprise illustration | Show how a high-risk purchase rule yields an actor, action, form, condition, and exception. Mark it as illustrative and place it after the documented corpus cases. |

Link to the Dartmouth original using physical page fragments and attribute the
edition. The review matched SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`
to the PDF. Use short source identifiers and editorial summaries for launch.
Check the exact source license and terms before adding longer extracts or page crops.
[Original source](https://math.dartmouth.edu/~prob/prob/prob.pdf) · [ADR-0070](../../adr/0070-full-book-method-development.md) · [Citation evidence](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations) · [Qualifier evidence](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) · [X/Z outcomes](../../../STATUS.md#delivered-and-assessed)

Separate three levels of use. The static reader follows the documented result and
original source. A prepared reader can try the exact retained query with a matching
producer release. The whole-book reproduction route uses the authenticated PDF
under the documented corpus directory, the matching release and model assets,
PostgreSQL development setup, and the whole heading inventory. Follow the retained
intake, finalization, inventory and contextual procedure with its explicit
`--rebuild-scoped --cue-pieces` option and recorded inputs. Explain the CUDA layout
and formula models, CPU RapidOCR, and the managed Nemotron prerequisite for the
combined arm. The expected inspected result is the exact source cue and typed
section link with its source-cue witness.
[Reproduction procedure](../../design_review/evidence/2026-11-08_nce-full-book/README.md) · [Native service prerequisites](../../../services/nemotron-parse/README.md)

Check whether a compatible checkout and producing release are available for
`ci query contextual_neighborhood --run 327` with the task and target from the
review. The retained report names project `nce-grinstead-snell-full-book`,
result revision `1`, and release
`release:845ac25166e63bae9177a19771fece4324453204a080fded91921eec5135e7e1`.
Verify any returned witness and edge against the independent review. If the
exact retained run remains incompatible, check for a detached
delivery that the existing verifier can qualify for that same result. Record the
result or specific refusal, including the attempted command and release, and use
the static walkthrough for public inspection. A product migration or replacement
query would require separate product scope. [Exact attempted Reader query](../../functional_reviews/github-visitor-experience_2026-11-08.md#O02) · [Retained contextual reports](../../design_review/evidence/2026-11-08_nce-full-book/raw/review-contextual-reports.jsonl) · [Reader contract](../../../python/corpus-structure/src/corpus_structure/serve/contextual_navigation.py)

**Closure.** Compare each example with its exact spans and assessment. A visitor
can reach the independently reviewed evidence and original pages without local
setup. A prepared reader sees the exact reproduction prerequisites and expected
result or a dated compatibility limit. Product and hosted outcomes retain their
own verification scopes.
