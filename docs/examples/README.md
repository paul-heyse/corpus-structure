# Source-linked examples

Each example separates the result produced by the pipeline from the assessment of that result.
The page numbers below are physical PDF pages.

The source is the Dartmouth CHANCE Project edition of Grinstead and Snell’s
*Introduction to Probability*, dated 4 July 2006. The title page identifies
distribution under the GNU Free Documentation License.
[Download the selected retained results as JSON](data/retained-examples.json)

## A condition stays attached to its predicate

**Source.** The exercise introduces random variables **“with positive variance.”**
The following sentence says how their correlation is **“defined.”**
[Source on physical page 289](https://math.dartmouth.edu/~prob/prob.pdf#page=289)

**Operation.** Attach the premise to the neighboring defining predicate.

**Retained result.** The definition keeps the textual condition as an inherited
scope attachment. The selected source words and predicate remain inspectable.

**Assessment.** The source review supports this attachment in the correlation
exercise. It assesses the textual relationship.
[Attachment assessment](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441)

<details>
<summary>Inspect evidence</summary>

View 177, run 320, cut 441, task 1498. The premise is at
`#/texts/5253[3:57)` and the defining predicate at `#/texts/5253[89:96)`.
The retained `scope_inheritance` edge has prefix `1407260e0e7e6a`.
[Retained scoped report](../design_review/evidence/2026-11-08_nce-full-book/raw/review-scoped-reports.jsonl)

</details>

## A printed reference becomes a typed link

| Step | Retained result |
| --- | --- |
| Locate | “Section 5.1” on page 260 at `#/texts/4682[69:80)` |
| Connect | Preferred `cites-section` edge to “Important Distributions” on page 191 at `#/texts/3495[0:27)` |
| Explain | An explicit source-cue witness supports the selected edge |
| Inspect | Edge prefix `27b19068cdac`, run 327, cut 447, task 1528 |

The review compared the occurrence and target with the printed book. Its scope is the retained
cue and the selected target. It also documents printed references that never reached the
resolver. [Occurrence on page 260](https://math.dartmouth.edu/~prob/prob/prob.pdf#page=260) · [Target on page 191](https://math.dartmouth.edu/~prob/prob/prob.pdf#page=191) · [Dated assessment](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#contextual-section-citations)

## A local phrase recovers its antecedent

**Source.** “This set of points” refers to a preceding description. In that
description, the points are pairs in the plane for which the joint density
takes a constant value.

**Operation.** Use the retained token relationships and source boundaries to
resolve the local phrase to the complete preceding description, including the
restriction.

**Retained result.** The private definition component names a set of constant
density and uses the full level-set description. The original local mention
remains in the evidence.

**Assessment.** The frozen source check and exact replay support this case.
When candidates compete or the antecedent falls outside the selected passage
or native piece, the bounded rule can preserve the local mention alone.
[Antecedent assessment](../design_review/evidence/2026-11-07_nce-source-linguistics/README.md#antecedent-decision)

<details>
<summary>Inspect evidence</summary>

Run 222, cut 313, source view 147, annotation task 594. In the retained passage,
the antecedent spans `[208:295)` and the local mention spans `[296:314)`.
[Retained component](../design_review/evidence/2026-11-07_nce-source-linguistics/antecedent.json) · [Delivery receipt](../design_review/evidence/2026-11-07_nce-source-linguistics/antecedent-delivery.json)

</details>

## Assemble a dossier around normal density

**Source.** The protected source contains a normal-density definition and a
separate supported definition for marginal totals.
[Frozen source citations](../design_review/evidence/2026-11-06_wce-completion-repair/dossier/attempt003/frozen-preflight.json)

**Operation.** Assemble supported material around the selected normal-density root.

**Retained result.**

| Facet | Root-qualified member |
| --- | --- |
| Terminology | The normal density function |
| Definition | `f _ { X } ( x ) = \frac { 1 } { \sqrt { 2 \pi } \sigma } e ^ { - ( x - \mu ) ^ { 2 } / 2 \sigma ^ { 2 } } \ .` |

The independently supported `marginal totals` component stays outside the
dossier because it is unrelated to this root.

**Assessment.** Both policies retained the same two independently supported
members and facets. The verified scope is this two-member dossier.
[Dossier assessment](../design_review/evidence/2026-11-06_wce-completion-repair/dossier/README.md#verified-native-and-delivery-results--2026-11-07)

<details>
<summary>Inspect evidence</summary>

Runs 196/cut 261 and 202/cut 273. The term and definition span `[14565:14592)`
and `[14640:14749)` in `gs120-recovered-source-116`.
[Finalized record](../design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json) · [Retained result](../design_review/evidence/2026-11-06_wce-completion-repair/dossier/attempt003/result.json)

</details>

## Candidates and selected relationships

### An affine `X` keeps its candidates

In source view 117, the affine formula’s `X` is at `#/texts/30[237:238)`.
The retained list ranks the urn’s red-ball count first among 14 candidates. The
selector recorded insufficient evidence and selected zero edges in run 207,
cut 287. The shared symbol alone gives no source-backed reason to connect the
formula variable to the urn count.
[Full candidate list and decision](../design_review/evidence/2026-11-06_wce-completion-repair/composition/native-retained004/false-bridge-control.json) · [Source assessment](../design_review/evidence/2026-11-06_wce-completion-repair/composition/README.md#native-non-self-route)

### A witnessed declaration resolves `Z`

In a separate scoped replay, run 253 and cut 350, the exact formula `Z` at
`#/texts/30[242:243)` in view 117 has a witnessed `declares` link to the
standard-normal declaration at `#/texts/21[130:161)`.
[Scoped replay results](../design_review/evidence/2026-11-07_nce06-closeout/development-results.json) · [Replay assessment](../design_review/evidence/2026-11-07_nce06-closeout/README.md#verified-development-results--2026-11-07)

## Illustrative enterprise workflow

An illustrative policy requires a reviewer to complete Form P-17 before
approving a high-risk purchase, unless an approved exception applies.

| Field | Illustrative value |
| --- | --- |
| Actor | Reviewer |
| Action | Complete |
| Object | Form P-17 |
| Timing | Before approval |
| Scope | High-risk purchase |
| Exception | An approved exception applies |

## Reproduce the contextual example

For a reproduction, use the exact PDF above with SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`. Put it under
`WORK/corpus/` as `Introduction_to_probability_grinstead_and_snell.pdf`. Prepare the
repository and PostgreSQL development environment and use the authenticated producing
release `release:845ac25166e63bae9177a19771fece4324453204a080fded91921eec5135e7e1`.
The Standard intake uses CUDA Docling layout and formula models with CPU RapidOCR. The
combined arm also needs the managed Nemotron service and its recorded model artifacts.
Use the full heading inventory from the same original. [Source and release procedure](../design_review/evidence/2026-11-08_nce-full-book/README.md) · [Nemotron service setup](../../services/nemotron-parse/README.md)

Follow the evidence procedure for intake, finalization, inventory, and scoped enrichment.
With the matching release bound and the baseline receipts in place, run:

```sh
CORPUS_DATABASE__COMPLETION_STATEMENT_TIMEOUT_SECONDS=900 uv run python \
  docs/design_review/evidence/2026-11-08_nce-full-book/contextual.py \
  WORK/baseline --release RELEASE --repaired --rebuild-scoped --cue-pieces
```

Inspect the result for the page 260 cue, the page 191 target, and the explicit source-cue
witness. Regenerated runs can have different run and task IDs. The retained Reader query for
run 327 was refused with `incompatible_query` on the reviewed installation. A live read of
that historical result requires compatible query code and the producing release.
[Exact retained query](../functional_reviews/github-visitor-experience_2026-11-08.md#O02)
