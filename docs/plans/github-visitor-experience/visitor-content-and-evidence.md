# Visitor content and source-linked evidence

**Status · 2026-11-08. GHV-02/03 complete. GHV-08 proposed.** Owns the visitor and evidence designs. The
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
[Original source](https://math.dartmouth.edu/~prob/prob/prob.pdf) · [ADR-0070](../../adr/0070-full-book-method-development.md) · [Citation evidence](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations) · [Qualifier evidence](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) · [Published X and Z examples](../../examples/README.md#candidates-and-selected-relationships)

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

The [published uncertainty example](../../examples/README.md#candidates-and-selected-relationships)
shows the rank-one red-ball candidate and separately links the scoped Z replay.
The [coordinator](../github-visitor-experience_2026-11-08.md#ghv-audit-closure) records live verification.

<a id="GHV-08"></a>

## GHV-08 · Show retained results and how they were assessed

**Proposed.** Owns draft §§3, 6 and 7. Consume the corrected dossier route
from [GHV-07](publication-and-rollout.md#GHV-07). Supply the operation names
and example links used by the diagram and visitor navigation.

### Exhibits

Lead the README with the condition example, followed by the compact section
citation and the link to the richer examples. On the examples page, give
each exhibit a source, operation, result and separate assessment. Make the
relevant source phrase and corresponding output easy to find with explicit
labels and textual emphasis. Put coordinates, identifiers and run details
under a native `<details>` disclosure titled **Inspect evidence**. Keep the
assessment and source route visible without opening the disclosure.

| Exhibit | Retained input and presentation |
| --- | --- |
| Condition attached to a neighboring definition | Use run 320/cut 441, task 1498, view 177, edge `1407260e0e7e6a`. On physical page 289, show the premise at `#/texts/5253[3:57)` and `defined` at `[89:96)` in the following sentence. Identify the textual `scope_inheritance` result and separately attribute the source review's support for the attachment. [Retained report](../../design_review/evidence/2026-11-08_nce-full-book/raw/review-scoped-reports.jsonl) · [Source assessment](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) |
| A local phrase recovers its complete antecedent | Use run 222/cut 313 and the frozen annotation from view 147. Show “This set of points,” the preceding level-set description through its restriction, and the recovered private definition component. Explain that retained token relationships and source boundaries select the supported antecedent, and that a competing or out-of-passage antecedent can leave the local mention in place. [Retained component](../../design_review/evidence/2026-11-07_nce-source-linguistics/antecedent.json) · [Replay and delivery](../../design_review/evidence/2026-11-07_nce-source-linguistics/README.md#antecedent-decision) |
| An assembled normal-density dossier | Use the exact term and formula content from `required_citations` in the retained preflight, and reconcile them with both policies' final result. Display the independently supported terminology and definition facets and show the unrelated, independently supported `marginal totals` component outside the root. Label the two-member scope and the equal membership across the policies. [Frozen citations](../../design_review/evidence/2026-11-06_wce-completion-repair/dossier/attempt003/frozen-preflight.json) · [Final results](../../design_review/evidence/2026-11-06_wce-completion-repair/dossier/attempt003/result.json) · [Finalized record](../../design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) |

Authenticate the original PDF and applicable quotation terms before copying
the two adjacent sentences or any source extract. Use short attributed
wording and exact source links. If attribution, permissions or transcription
cannot be established, use a clearly labeled paraphrase and the precise
locator. Check any readable rendering of the normal-density formula against
the retained exact text. The variance exhibit describes a textual attachment
and the scope of its source assessment.

Publish one small checked JSON download at
`docs/examples/data/retained-examples.json` for these three cases. Select
only the source locators, result fields, producing identities and receipt
references needed to inspect the exhibits. Verify finalized hashes where
available and compare each selected value against the retained output and
independent assessment. Declare the excerpt as an explicit publication asset
with a download link. Author and validate it against the source records when
it changes. Routine publication reads the committed excerpt, including in an
LFS-disabled checkout. Full records remain at their existing revision-bound
source locations.

### Evaluation and organizational application

Add `docs/evaluation.md` as the public evaluation entry. Each row gives the
question assessed, a scoped result or limitation, and a direct evidence link.

| Layer | Evidence and claim |
| --- | --- |
| Source capture | The page 416 matrix example separates retained native math from the projection that shows only the opener. [Capture review](../../design_review/evidence/2026-11-08_nce-full-book/review/README.md#findings-across-page-ranges) |
| Extraction | On physical page 47, role record 184 locates the defining occurrence of `probability`. The retained attachment used a later occurrence and omitted the operative formula and condition. Distinguish extraction of the role from selection of the attachment. [Extraction review](../../design_review/evidence/2026-11-08_nce-full-book/review/definition-window-retry.md#semantic-findings) |
| Attachment and scope | Positive variance stays attached to the neighboring defining predicate in the reviewed occurrence. [Cut 441 checks](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441) |
| Linking | Section 5.1 leads to the supported heading with an explicit witness. The review checked nine retained decisions. [Citation assessment](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations) |
| Assembly | Both dossier policies include two supported root-qualified members and exclude the unrelated component. [Dossier record](../../design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) |
| Coverage gaps | Four additional printed citations did not enter upstream retrieval. Book-wide citation recall remains open. [Source-side misses](../../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-citations-outside-the-contextual-population) |

Explain the intended organizational knowledge application in the opening.
Policies, procedures and technical documentation illustrate where typed
relationships and partial structure could help. The textbook evidence
demonstrates the current methods. Keep the high-risk purchase rule
explicitly illustrative and present its actor, action, object, timing,
scope and exception in a small table. Preserve the X/Z cases and historical
reproduction compatibility limit.

**Closure.** At both widths, a static reader can identify the source, output,
and assessment for all three exhibits, reach the evidence and download the
exact selected fields. Review the exhibit and excerpt against the retained
inputs and the evaluation rows against their separate assessments.
