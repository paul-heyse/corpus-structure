# Held-out source checks for the repaired book shadow

The source witnesses below use physical PDF page numbers and the original
SHA-256 `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
The frozen sample belongs to exact integrated run 377, task 1627, cut 492.
It excludes the historical Chandra cases and the current pilot. A source
witness describes the checked field. An arm receives credit only when an
exact observation available to that arm supplies the field and the
incumbent lacks it or reads it incorrectly. [Original PDF](../../../statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf) ·
[Repaired comparator](incumbent-recovery.md#optimized-comparator--2026-11-08)

**Tested · 2026-11-08.** The source fields below were read from physical
page renders with Poppler and checked against positioned text. The table
identifies the scope of adjudication and the principal error to check.
Chandra content remains unadjudicated until a matching protected
observation is available.

| Physical page | Frozen stratum | Original field to check |
| --- | --- | --- |
| 20 | Unflagged, no located typed region | The historical discussion and two exercises contain prose, two footnotes and inline numbers. There is no standalone formula, table or figure. |
| 24 | Recognize caption | Figure 1.6 has three panels labelled a, b and c for walks in one, two and three dimensions. One printed caption applies to all three. |
| 66 | Recognize picture | Figure 2.12 shares one caption across a dart-target diagram and a histogram overlaid by `y=2r`. The caption specifies 400 throws. The body separately says the program ran 1000 darts. Preserve both statements with their roles. |
| 75 | Unflagged picture | Figure 2.19 has a diagonal region E with four boundary dimensions of `1−z`. Figure 2.20 is a separate exponential density with `λ=1/30`. Distinguish the two pictures and their captions. |
| 89 | Unflagged caption | Table 3.4 is a single factorial approximation table with headers `n`, `n!`, Approximation and Ratio. Row 8 gives 40320, 39902.395 and 1.010. Keep the nearby definition and Stirling formula separate from the table. |
| 91 | Unflagged table | Table 3.6 is a two-column date/snowfall table with 1977 → 110. Table 3.7 is a distinct two-row year/ranking table with year 4 → rank 10 and year 6 → rank 1. |
| 92 | Recognize formula | The records discussion prints simulation averages 2.968, 3.656 and 3.960 for `n=10,20,30` respectively. The logarithms are prose. The centered St. Ives material is verse, with no mathematical display. |
| 114 | Unflagged table | Table 3.9 has the two-line probability header and eight observations. Both `n=9` and `n=10` print .367879. The text below gives the limiting value .3678794. |
| 121 | Recognize table | Table 3.13 has headers 6 through 1 games and descending row lengths. Row 1 reads 63, 70, 80, 96, 128, 256. Row 6 contains only 8 in the six-games column. The indented blank positions are structural. |
| 127 | Recognize formula | Exercise 38 gives Lucas's relation with the product indexed from `i=0` to `k`. The worked example has `p=7`, `n=12` and `j=9`, and its final congruence is modulo 7. |
| 143 | Recognize table | Figure 4.1 is a probability tree. Two branches leave the start at `1/2` each. Urn I paths terminate at `1/5` and `3/10`, and Urn II paths at `1/4` each. The printed column labels describe branches and terminal values rather than an independent table. |
| 146 | Recognize table | Figure 4.3 has one Monty Hall probability tree. Car placement 1 and contestant door 1 lead to Monty doors 2 and 3, with `1/18` per path. Placement 1 and contestant door 2 lead to Monty door 3 at `1/9`. A candidate needs the branch bindings to preserve these readings. |
| 175 | Repair formula | Figure 4.8 is followed by an area calculation ending at `3/8`. The separate four-branch CDF uses `(1/2)r₃²` on `0≤r₃≤1` and `1−(1/2)(2−r₃)²` on `1≤r₃≤2`. |
| 189 | Skipped, no trigger | The two-envelope continuation and exercises use inline inequalities, prose and two footnotes. There is no standalone table or figure. |
| 191 | Recognize caption | Chapter 5 and section 5.1 head the page. There are no pictures or captions. The discrete uniform algorithm has one centered expression `1+⌊n(rnd)⌋`. |
| 196 | Unflagged caption | Figure 5.2 is one negative binomial plot with `k=2` and `p=.25`. Its bars and vertical scale support approximate reading. The only exact probabilities claimed here are the printed parameters. |
| 202 | Reviewed incumbent agreement | Table 5.2 Female row is 24, 4, 28. Male row is 8, 14, 22. The totals are 32, 18, 50. The lower Table 5.3 uses symbolic entries and separate caption. |
| 208 | Unflagged, no located typed region | Exercises 20–25 contain no standalone chart or table. Exercise 22 binds 600 raisins, 500 cookies, and `λ=600(1/500)=1.2` in the paragraph. |
| 217 | Repair caption | Both top panels share Figure 5.7, “Queue sizes.” The lower histogram owns Figure 5.8, “Waiting times.” Treat the two caption addresses and their associations separately. |
| 218 | Reviewed incumbent agreement | The last display is the decreasing-φ density formula. It has a minus sign before `f_X`, uses `φ⁻¹`, and differentiates with respect to `y`. The immediately preceding increasing case has the same structure with a positive sign. |
| 241 | Reviewed incumbent agreement | Theorem 6.3 gives `E(S_n)=np` for Bernoulli trials. Theorem 6.4 separately gives `E(X·Y)=E(X)E(Y)` for independent random variables. Preserve those two scopes. |
| 254 | Recognize caption | Table 6.4 has two rows of payoffs with signs `−u, v` and `0, −x`. Table 6.5 separately lists age and survivors, including age 6 → 64 and age 76 → 1. Both tables have their own printed caption. |
| 256 | Unflagged, no located typed region | Exercises 7–14 have no standalone figure or table. The opening identity `E(XY)=E(X)E(Y)` is an inline premise of exercise 7. |
| 285 | Unflagged formula | The queue-length formula has `s_j=(1−ρ)ρ^j` for `j=0,1,2,…` under `ρ<1`. Its waiting-time display is `T=ρ/[λ(1−ρ)]=1/(μ−λ)`. Keep these distinct from the Figure 6.8 histogram. |
| 286 | Unflagged picture | Figure 6.9 is a single histogram of queue waiting times, followed by exercises. It is distinct from p285's queue-length histogram, despite matching horizontal extent and similar bar shapes. |
| 303 | Recognize incomplete OCR | The Cauchy section distinguishes `2/[π(4+z²)]` from `1/[π(1+z²)]`. The later Rayleigh example has a two-branch square-variable density, including zero otherwise. |
| 315 | Recognize picture | The Law of Large Numbers page contains theorem, proof and displayed inequalities with no figure or table. The upper statement has `P(abs(S_n/n−μ)≥ε)→0` and the complementary probability approaches 1. |
| 343 | Unflagged picture | Figure 9.5 is one spike plot with a smooth overlaid curve, centered near .54. The printed text supplies population 100,000, sample size 1200, 10,000 draws and 9648 within the chosen margin. Values between axis labels are estimates. |
| 345 | Unflagged table | Table 9.1 has five columns. The 1936 first data row is Roosevelt, 55.7%, 62.5%, 6.8%. The 1996 last data row is Clinton, 52.0%, 50.1%, 1.9%. Preserve the two-line column headings. |
| 361 | Skipped, no trigger | Figure 9.12 is one photographic plate with negative/positive deviation labels and several graphical traces. It has a single printed caption and no independent exact data series in the checked image. |
| 386 | Unflagged formula | Figure 10.1 has a probability tree with first-generation branches 2, 1 and 0 carrying `1/4, 1/4, 1/2` respectively. The branch 2 → 2 is `5/16`, with joint probability `5/64`. A located probability expression elsewhere on the page cannot supply these graph roles. |
| 388 | Repair picture | Figure 10.2 has three panels (a), (b) and (c) with one shared caption. The three cases are `d<1`, `d=1` and `d>1`. The plotted entities are the line `y=z` and curve `y=h(z)`. |
| 390 | Recognize formula | Table 10.1 places generation 12 → .598931. Table 10.2 separately has `p₀=.2092` and `p₁₀=.0000`. The latter is a labelled vertical series of equations with one caption. |
| 407 | Recognize incomplete OCR | The normalized sum is `S_n*=S_n/√n`. The discrete CLT display integrates to `a` from `−∞` with integrand `exp(−x²/2)` and factor `1/√(2π)`. The later step function uses a half-open interval around `j`. |
| 408 | Repair formula | The continuation defines `sinh(t/2)=(e^(t/2)−e^(−t/2))/2`, then states the scaled ratio limit 1. The separately headed Cauchy density is `1/[π(1+x²)]`. |
| 412 | Verified blank body | The source has the running chapter header and printed number 404. The rest of the page is blank. |
| 424 | Unflagged formula | Example 11.13 has a labelled 5×5 transition matrix, row and column labels 0–4. Rows 0 and 4 are absorbing. Row 1 has `1/2` under columns 0 and 2, with zero elsewhere. |
| 448 | Unflagged caption | Table 11.3 rows R, N and S have counts 4010, 1902 and 4088 and fractions .401, .19 and .409. The later maze matrix belongs to Example 11.22. It is a separately labelled 9×9 array with row 1 nonzero only at columns 2 and 6. |
| 470 | Recognize picture and incomplete OCR | Figure 11.6 has two plots with “Time forward” above “Time reversed.” The lower plot reverses the same simulation. One shared caption names the figure. |
| 491 | Repair formula | Exercise 8 distinguishes `≥0`, `>0` and `≠0`. Exercise 9 uses a parity-conditional pair `p_(n,r)` or `p_(n,r+1)` and separate even and odd expectation sums with different starting indices. |
| 508 | Skipped, no trigger | Appendix A has a normal-curve schematic and a distinct unruled 40×10 numeric grid. Column labels are .00–.09 and row labels 0.0–3.9. At row 0.9, column .04 reads .3264. At row 0.0, column .01 reads .0040. Check explicit decimals and ordered row/column roles. |

Reproduce each layout read with `pdftoppm -f PAGE -l PAGE -r 120
-singlefile -png "$pdf" "$out"` and `pdftotext -f PAGE -l PAGE -layout
"$pdf" "$out.txt"`. The prior review provides separately scoped
incumbent-agreement observations and documented projection issues for p448
and p508. [Earlier incumbent agreement](../2026-11-08_nce-full-book/review/pages-174-346.md) ·
[Earlier matrix and appendix checks](../2026-11-08_nce-full-book/review/pages-347-518.md)

## Exact incumbent checks

**Tested · 2026-11-08.** The published Reader bound the physical region
inventory to the same frozen product. The following fields provide
comparison controls for the managed observations.

- P202 Table 5.2 `#/tables/39` retains all nine printed numeric cells
  with their anchors. P218 `#/texts/11235` preserves the signed derivative.
  P241 `#/texts/21421` and `#/texts/21479` preserve the two target identities.
- P24 has two selected pictures, while the source presents three labelled
  panels. The selected shared caption `#/texts/17308` is referenced only by
  `#/pictures/48`. P75 has two distinct pictures with empty caption
  references. Figure 2.19's caption text is empty at `#/texts/8542`, while its
  `orig` retains the caption and subscript.
- P217 retains the three pictures and the first caption
  `#/texts/8547`. The published page has no separate Figure 5.8 caption.
  P470 similarly retains the picture `#/pictures/150` with empty
  caption references and no selected caption region.
- P285 `#/texts/7073` flattens both fractions in its `text` and `orig`.
  P424 `#/texts/2385` retains the printed matrix values in `orig`, while
  its selected LaTeX puts labels and entries at different offsets and omits
  values. P448 `#/texts/2513` retains the matrix values and labels in `orig`,
  while its selected text ends at `\begin{array} {`. A readable original and
  a qualified matrix structure are separate benefits.
- P508 has one selected picture `#/pictures/13` and 456 text regions,
  with no typed table region. The printed grid is visible in the PDF and
  the deposited author PostScript contains its numerical strings.
  [Original PostScript for Appendix A](../../../statistics_corpus/corpus/grinstead_snell/latex_source/figures/PSfigappA.ps#L2173-L2183)
