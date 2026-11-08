# Source-linked examples

Each example separates the result produced by the pipeline from the assessment of that result.
The page numbers below are physical PDF pages.

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

The source is the Dartmouth CHANCE Project edition of Grinstead and Snell’s *Introduction
to Probability*, dated 4 July 2006 and identified by its title page as distributed under
the GNU Free Documentation License.

## A condition stays attached to its predicate

In the correlation exercise on page 289, the positive-variance assumption at
`#/texts/5253[3:57)` is attached to the defining predicate `defined` at `[89:96)`.
The retained edge is `1407260e0e7e6a`. The source check supports this local attachment.
[Source page](https://math.dartmouth.edu/~prob/prob/prob.pdf#page=289) · [Attachment assessment](../design_review/evidence/2026-11-08_nce-full-book/review/scoped-outputs.md#source-checks-on-cut-441)

## Candidates and selected relationships

The affine-`X` case retained its candidate list while withholding an unsupported link.
In a separate case, the exact `Z` occurrence was recovered and linked to its declaration.
These results illustrate the difference between retaining a possible connection and selecting
a witnessed one. [Retained X and Z outcomes](../../STATUS.md#delivered-and-assessed)

## Illustrative enterprise workflow

Consider a rule requiring a reviewer to complete Form P-17 before approving a high-risk
purchase unless an approved exception applies. Its structure would distinguish the actor
(the reviewer), the action (complete), the form (P-17), the timing condition (before approval),
the risk scope, and the exception. This is an illustrative workflow.

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
