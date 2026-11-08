# Grinstead–Snell definition window retry review

The definition retry addresses exact source intervals that the original model
refused or left beyond its window cap. It uses the same Standard source views
and bare, flat GLiNER 2.5 profile. The retry selects smaller exact passages
and runs the model route alone. The [original attachment
review](definition-attachments.md) gives the separate dispositions of all 160
original retained attachments.

I compared each decoded attachment with its full surrounding Standard source
context and consulted the original PDF where the projected math or meaning
needed confirmation. The packet exporter checks the exact original passage,
absolute term and content offsets, physical page joins, and matching native
window receipts. It also inventories all individually located role proposals
and indexed decoder refusals. The semantic dispositions below concern
attachments. A raw role proposal is a possible term or content span without a
validated relationship to another span.

I used the same disposition vocabulary as the original review. **D** is a
source-supported definition or exact naming. **E** is a supported local
explanation, example, or assignment. **P** is a recognizable intended relation
with a materially incomplete span, proposition, or condition. **X** is an
unsupported or misbound relation. **U** marks insufficient evidence to decide.

## Retained attachment dispositions

The index identifies the one-based row in `definitions-retry.jsonl`, ordered
by retained run, task and component order. Page numbers refer to physical
PDF pages.

| Index | Task | Physical page | Judgment | Source-grounded disposition |
| --- | --- | --- | --- | --- |
| 1 | 1535 | 47 | P | The exercise defines an asymptotic-density candidate for a set of positive integers. The component captures only the left side `P(A)`, omitting the limiting ratio and its existence condition. Its term occurrence is from the later discussion of the rule. |
| 2 | 1535 | 125 | X | Stirling’s formula estimates a particular probability about the color split of drawn balls. The exercise supplies a calculation method and gives no definition of probability. |
| 3 | 1535 | 126 | X | Theorem 3.8 is a proof hint for the probability of collecting all the Wheaties pictures. The citation supplies neither the event probability nor the definition of the word. |
| 4 | 1536 | 178 | X | Equation 4.5 gives the distribution of the unknown efficacy parameter. The attached word `drug` names the treatment in a later clause. |
| 5 | 1536 | 197 | P | The source identifies Equation 5.2 as the Poisson probability mass function. The model keeps a clipped `distribution` from a later occurrence of the full name and attaches only the equation reference. |
| 6 | 1537 | 266 | P | Theorem 6.6 supplies an alternative variance computation. The selected label drops the formula `E(X²) − μ²` and the premise `E(X) = μ`. |
| 7 | 1537 | 276 | X | Theorem 6.2 is a comparison with an earlier result. The current passage starts the properties of continuous expectation under Theorem 6.10, and the pair supplies none of them. |
| 8 | 1537 | 279 | X | Theorem 6.12 justifies factoring the expectation of `AB` in this independent case. The component instead binds it to a bare occurrence of `A`. |
| 9 | 1537 | 279 | X | Theorem 6.11 justifies the expected-value calculation for `A` and `B`. The source has already assigned `A = X²`. |
| 10 | 1537 | 282 | X | Theorem 6.15 supplies a step in computing the variance of `Z`. The component binds it to the symbol `Z` with the rest of the calculation discarded. |
| 11 | 1538 | 307 | P | The prose introduces the density of the sum of `n` independent uniform variables. The displayed span is only another occurrence of the function symbol, omitting the piecewise expression. |
| 12 | 1538 | 336 | X | The nearby Stirling reference introduces an asymptotic formula for factorials. The attached `n` is an operand in the preceding binomial calculation. |
| 13 | 1539 | 405 | P | The passage identifies `kX` as the Fourier transform of the density `fX`. The content span is only `equation`, with both the transform and the explanation outside its boundary. |
| 14 | 1539 | 407 | X | Figure 9.3 illustrates a preceding convergence claim. The selected `g` is from the next paragraph, where the source gives its own integral. |
| 15 | 1539 | 409 | P | The passage defines the Cauchy characteristic function by an integral. The component keeps a clipped function name and the word `formula`, excluding the integral itself. |

## Native retry coverage

**Measured, 2026-11-08, for the retained retry population.** All 375 exact
retry windows returned a native model reply. Together their source intervals
cover the 99 original refused intervals and all seven uninspected tails.
Reconciliation against the original returned windows leaves no uncovered
text in the selected Standard model views. The native retry is a separate
run series with its own custody.

| Run | Cut | Task | Returned windows | Located roles | Retained attachments |
| --- | --- | --- | --- | --- | --- |
| 331 | 455 | 1535 | 64 | 990 | 3 |
| 332 | 457 | 1536 | 64 | 1,071 | 2 |
| 333 | 459 | 1537 | 64 | 1,044 | 5 |
| 334 | 461 | 1538 | 64 | 970 | 2 |
| 335 | 463 | 1539 | 64 | 984 | 3 |
| 336 | 465 | 1540 | 55 | 723 | 0 |
| **Total** | | | **375** | **5,782** | **15** |

The 5,782 exact role records contain 5,418 term proposals and 364 content
proposals, representing 5,224 distinct roles by original view and source
coordinates. Exactly 30 role records participate as endpoints of retained
attachments. Located extraction recorded 369 successful windows and six
empty windows. Attachment recorded ten successful windows, 320 empty
windows, and 45 failed windows. Three of the failed windows also retained a
decoded component. The 60 indexed candidate rejections all lacked the
declared decoded endpoint roles. Every role was checked for an exact source
anchor and matching model window. Role-only semantic judgments use selected
examples. The decoder-rejected outputs are represented by their indexed
native diagnostics.

## Semantic findings

- The model marked four retained attachments as definitions and 11 as
  explanations. Independent review found six materially incomplete
  attachments and nine unsupported ones. Zero retained pairs conveyed a
  usable definition or local explanation at their selected boundaries.
- Physical p47 shows a role-selection failure within one reply. Role
  record 184 locates the original defining occurrence of `probability`
  at offsets 88560–88571. Attachment 1 instead uses record 182 at
  88862–88873, a later application of the rule, and attaches it to the
  left side `P(A)` at 88581–88588. The formula and its limit-existence
  condition remain outside the content span.
- Attachment 5 repeats the exact term and content coordinates of original
  attachment 89. The provider changed its interpretation from definition
  to explanation under the retry window. The clipped term and equation
  reference remain insufficient to convey the Poisson mass function.
  This was the sole exact source-coordinate attachment pair common to
  the original and retry outputs.
- Pages 266, 307, 405 and 409 have meaningful source material around the
  model’s citation, left side, or generic formula label. The captured
  content omits the operative expression. Pages 125, 126, 279 and 407 show
  citation roles attached to the wrong token or preceding or following
  proposition.

Recreate the review packet from the exact retained task reports and the
Standard page packet with the [packet helper](../review_proposals.py).

```sh
uv run python docs/design_review/evidence/2026-11-08_nce-full-book/review_proposals.py \
  build/nce-full-book/review --definition-tasks 1535 1536 1537 1538 1539 1540
```

This development-corpus evidence establishes window return, retained span
custody and the judgments above. Definition recall across the original
source and correctness of every raw role remain separate questions.
