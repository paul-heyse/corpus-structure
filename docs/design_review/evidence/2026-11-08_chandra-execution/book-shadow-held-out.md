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

## Settled holdout observations

**Tested · 2026-11-08.** The protected comparison verified the producing
group and exact raw and mapped pins for these whole-page requests. Each
provider stop was unknown. The rows assess only the listed source fields.
The comparison marks independently unlocated fragments as candidates even
where their reading is true. Arm credit follows the frozen exact scope.
The Standard alternatives below were read from organized run 356, task
1566, digest `a3de20e84391b90ad183c040ce3107cc74eed2f80e7927a78519d4cd11490817`.

| Physical page | Managed mapping task | Arms | Bounded disposition |
| --- | --- | --- | --- |
| 20 | 1655 | All-page | Seven formula rows are unlocated inline variables and values. The inspected scope has no standalone formula, chart or table gain. |
| 24 | 1657 | Selective, all-page | Three located picture candidates and the three printed local captions are useful panel evidence. The first description omits the left arrow. The detached panel captions have empty association lists. Keep the source-grounded 2D/3D descriptions and distinct local captions as candidates with the shared Figure 1.6 relationship independently witnessed. |
| 66 | 1659 | Selective, all-page | The description locates the target and bar plot as two parts of one figure, a discovery gain over the selected picture's empty metadata. Keep the caption's 400 and the prose's 1000 separately. No exact chart series or separate panel geometry qualifies from the compound result. |
| 75 | 1661 | All-page | Figure 2.20's description correctly supplies the function and horizontal extent. The same function is already in the incumbent chart title. Figure 2.19's description misstates the shaded diagonal band and misses two dimension arrows. Both caption literals remain available through the incumbent's text/orig. |
| 89 | 1663 | All-page | The located Stirling formula `#/texts/37` preserves `n^n e^(−n) √(2πn)`. Selected `#/texts/14583` flattens it, and Standard `#/texts/1526` incorrectly puts the square root inside the exponent. The author formula supplies a direct source repair route. Table 3.4 agrees on the checked row. [Author formula](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch3.tex#L266-L270) |
| 91 | 1665 | All-page | Both Chandra tables preserve the tested snowfall and rank anchors. Selected `#/tables/48` and `#/tables/24` already expose them. The numerical checks give agreement. |
| 92 | 1667 | Selective, all-page | Chandra retained inline logarithms and simulation inputs, with no located display. The page's centered verse does not qualify as a formula. The nomination yields no gain in the inspected structural scope. |
| 114 | 1669 | All-page | The candidate keeps the eight probabilities and combines the wrapped probability header into one logical row. Its two located series also restore the fraction and exponent syntax flattened in the selected text. Standard `#/texts/1976` and `#/texts/1978` already supply readable mathematical structure. |
| 121 | 1673 | Selective, all-page | Candidate `#/tables/0` preserves the checked triangular values and represents the upper-left heading as a two-row span with the six games columns beneath their parent header. The incumbent retains the numeric values and a different header partition. Column hierarchy is a candidate gain. Row header semantics remain open because candidate row labels have no header flags. |
| 127 | 1675 | Selective, all-page | The located Lucas formula `#/texts/46` and paired base-seven expansion `#/texts/54` correct selected malformed notation and the omitted second expansion. Standard `#/texts/2172` and `#/texts/2174` provide independent readings. |
| 143 | 1679 | Selective, all-page | The picture description preserves the checked urn paths and branch probabilities. The generated nested table is an alternative view of a tree and carries no independent table region. Located `#/texts/40` correctly groups both denominator terms in the conditional probability. |
| 146 | 1681 | Selective, all-page | Reject the description's claim that every final door choice has probability `1/2`. The original also has forced branches with weight 1. The nested table does not establish branch ownership and cannot substitute for the original diagram. |
| 175 | 1683 | All-page | The located CDF `#/texts/10` restores the square and all four conditions where selected `#/texts/4600` corrupts the first nonzero branch. Standard `#/texts/3095` retains those branches. Keep the graph description separate because its stated shaded extent omits the vertical boundary at `ω₁=1/2`. |
| 189 | 1685 | All-page | Inline inequalities are recognizable, with no independently located display or new typed picture/table in the inspected scope. |
| 191 | 1687 | Selective, all-page | The caption trigger yields no caption. The source floor operation is explicit in selected `#/texts/1079`. The candidate writes ordinary brackets. Preserve the selected notation and chapter hierarchy. |
| 196 | 1689 | All-page | The caption parameters agree. The description gives a unique peak at `j=4`, while the source shows equal-height adjacent peaks at 4 and 5. The nested generated numerical series has no independent source table. |
| 202 | 1691 | All-page | All nine Table 5.2 numeric anchors agree. Separately, the located hypergeometric expression `#/texts/37` restores the binomial arguments and fraction lost in selected `#/texts/19719`. Standard `#/texts/3662` has a malformed numerator, while the printed formula and author source independently supply the intended expression. [Author formula](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch5.tex#L441) |
| 208 | 1693 | All-page | Chandra retains `λ=600(1/500)=1.2` as an unlocated inline formula. No new standalone structure is established. |
| 217 | 1695 | All-page | The located Figure 5.8 caption `#/texts/3` matches the source and is absent from run 377. Standard `#/texts/3910` supplies it under the frozen repair action. The model combines the two upper queue panels, so its description is distinct from independently bound panel evidence. |
| 218 | 1697 | All-page | The increasing and decreasing cases retain the correct signs. Candidate `#/texts/71` agrees with selected `#/texts/11235` and Standard `#/texts/3946` on the signed derivative. |
| 241 | 1699 | All-page | Candidate `#/texts/13` and `#/texts/68` reproduce the two separate theorem identities already present in the incumbent. The checked identities agree. |
| 254 | 1701 | Selective, all-page | Table 6.4 candidate `#/tables/0` preserves the separate probability labels `p` and `1−p` and the four payoffs in their source rows. Both selected `#/tables/3` and Standard `#/tables/36` collapse labels and lose values. The original layout and author table independently supply the bindings. Table 6.5 agrees on the checked mortality values. [Author table](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch6.tex#L823-L836) |
| 256 | 1703 | All-page | The model represents the opening equality as an inline expression. The page has no chart or table, and no additional independently located structure was established. |
| 285 | 1705 | All-page | Located `#/texts/11` restores both fractions in the waiting-time identity, which selected `#/texts/7073` flattens. Standard `#/texts/5163` already preserves them. The chart reading may describe a histogram bin near zero, without claiming an exact point frequency. |
| 286 | 1707 | All-page | The description identifies the waiting-time histogram but adds hours as the unit. The source plot and surrounding simulation do not establish hours. Keep the incumbent caption and withhold the unit. |
| 303 | 1709 | Selective, all-page | The Cauchy expressions agree. Candidate `#/texts/46` restores the normal exponential as a factor outside the denominator. `#/texts/52` restores the Rayleigh expression and its zero branch. Standard `#/texts/5540` and `#/texts/5542` provide independent readings. |
| 315 | 1711 | Selective, all-page | The source has no picture. The same whole-page request nevertheless restores the missing absolute-value delimiter and correct `≥ε` and `<ε` conditions in the theorem and proof displays. Standard also retains the properly delimited bounds in the proof. |
| 343 | 1717 | All-page | The located Figure 9.5 description correctly identifies the spikes, horizontal scale and center near .54. The source prose and figure already supply the distribution identity and sample count. Retain approximate chart description as an alternative. |
| 345 | 1719 | All-page | Chandra and selected `#/tables/25` agree on the visible columns and the checked 1936 and 1996 rows, including every printed percentage in those rows. |
| 361 | 1721 | All-page | The picture description repeats the already available caption. It supplies no additional labelled trace or qualified numerical series. |
| 386 | 1723 | All-page | Located `#/texts/27` restores the complete `5/16` calculation, also available from Standard `#/texts/7239`. The raw diagram prose omits the root-to-2 branch and adds an unsupported root label. The nested table mixes branch weights with joint probabilities and does not retain the parent paths. |
| 388 | 1725 | All-page | The compound description gives the three source cases and intersections. The exact positions remain panel-specific, while this candidate occupies the combined figure. The incumbent already retains three pictures and the caption, and the cases appear in the surrounding source prose. |
| 390 | 1727 | Selective, all-page | Table 10.1 agrees on the checked values. Candidate `#/tables/1` restores separate `p₉=.0002` and `p₁₀=.0000` rows. Selected `#/tables/4` and Standard `#/tables/44` combine them in a single row. The author source supplies both bindings independently. [Author rows](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch10.tex#L872-L885) |
| 407 | 1729 | Selective, all-page | The CDF integral agrees on its limits and negative exponent. Chandra restores the piecewise terminator and gives one integral where the selected moment-generating derivation duplicates it. The local density limit remains a shared error. The printed `exp(−x²/2)` appears as `exp(t²/2)` in Chandra, selected `#/texts/19703` and Standard `#/texts/7619`. |
| 408 | 1731 | All-page | The candidate restores the displayed hyperbolic-sine fraction and the Cauchy denominator. Standard `#/texts/7626` and `#/texts/7639` already supply these readings. |
| 412 | 1733 | All-page | The retained raw response contains the two running-header fragments and no body. The available mapping has no candidate rows. This agrees with the independently verified blank body even though provider completion remains unknown. |
| 424 | 1735 | All-page | Located `#/texts/26` preserves all five row labels, all five column labels and all 25 matrix values. The outer array declares five columns for a header with six positions. Treat the values and label lists as readable evidence pending a valid positioned matrix contract. Both incumbents preserve those values in `orig`, while their rendered formula text corrupts the arrangement. The author matrix independently binds the values. [Author matrix](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch11.tex#L754-L767) |
| 448 | 1737 | All-page | The located candidate `#/texts/13` preserves all 81 maze matrix values and both label lists in a nested LaTeX representation. Both incumbent originals retain the values, while selected `#/texts/2513` and Standard `#/texts/8252` render only the opening token sequence. The author matrix independently binds all positions. Table 11.3 agrees on all nine checked row and value fields. [Author matrix](../../../statistics_corpus/corpus/grinstead_snell/latex_source/ch11.tex#L2376-L2388) |
| 470 | 1739 | Selective, all-page | Candidate `#/texts/2` restores the missing Figure 11.6 caption, also available from Standard `#/texts/8629`. The description correctly separates time-forward and time-reversed panels but says the lower x-axis runs 1000 to 0. Both printed axes run 0 to 1000. |
| 491 | 1741 | All-page | The candidate preserves the three inequality relations, the parity branches, and the different even/odd sum starts and coefficient signs. It restores fraction and binomial structure flattened in the selected calculations. Exact Standard already preserves these structures at `#/texts/9013` through `#/texts/9019`. |
| 508 | 1745 | All-page | The located Appendix A table `#/tables/0` supplies all 400 printed decimals and all ordered labels in a 41×11 grid. Both incumbents lack a typed table. The ten column labels qualify by position, while the mapping gives the first-column labels no row-header flags. The separate figure description puts the shading to the right of `d`, but the source shades the interval from 0 to `d`. |

The p508 CLI Reader used run 394, raw task 1744 and mapped task 1745 with
digest `8d618b5561e39b958fdfe215c5935fd76219cb4234f06f4f8f20a93859166fdf`.
All 451 mapped unit-span anchors matched the independently extracted
source grid, including the blank corner. The cell `.3264` is at zero-based
row 10 and column 5 with column path `[5]`. The exact candidate has
11 column-header flags and zero row-header flags. The Reader reports
`recognition_candidate` and an unspecified provider stop.

An independent `pdftotext -f 508 -l 508 -bbox-layout` pass found 40
ordered source rows with 11 numeric words each and ten positioned column
labels. The largest body-word left-edge deviation from the median
for its column was 0.275 PDF points. This gives an incumbent recovery
route for the witnessed grid and a candidate routing cue for similarly
aligned numeric layouts. Any wider cue needs separate testing on dense
prose, charts and wrapped tables. The p508 dry router skipped the page,
so the current selective arm missed this structural gain.

The 41-page held-out sample demonstrates selective gains on pp254 and
390 and additional all-page gains on pp89, 202, 424, 448 and 508 in
the inspected fields. Some corrected readings already exist in Standard
or in independently positioned source material. The diagram and figure
errors above demonstrate why an observation's readable structure remains
attributed. The sample settles these field comparisons within the
full-book campaign.
