# Whole-book Standard artifact nominations

This review uses Standard intake run 297/cut 413 and the completed whole-book artifact report from run 300/cut 417, task 1373. The 530-row nomination packet identifies the exact retained endpoint contribution IDs. I recovered each inspected endpoint’s native pointer, offsets, source item, and physical page membership from the retained report and its published Standard product. I checked the authenticated PDF directly where a title or code could conceal a material distinction. Pair numbers below are the one-based nomination packet indexes. Multi-page native items retain both physical page locators where the anchor is item-relative.

## Census and semantic review boundary

The packet contains 530 unique unordered endpoint pairs across 596 retained artifact records and 29 selected source views. There are 483 same-code, unscoped-code nominations, all with `reference_only` standing. Of those, 295 join two items labeled references and 188 join a caption with a reference. There are 47 lexical-title nominations, all joining captions with different controlled codes and all with `namespace_unavailable` standing. The producer emitted 440 same-view and 90 cross-view pairs. Seventy of the cross-view pairs are unscoped-code pairs and 20 are lexical-title pairs. The artifact kinds agree within every pair. Among the lexical-title pairs, 37 involve figures and ten involve tables.

I semantically inspected all 47 lexical-title pairs and 20 selected unscoped-code pairs, for 67 total. The unscoped selection covers same- and cross-view examples, four artifact kinds, useful caption navigation, duplicate references, declarations labeled as references, and contradictory citation context. The other 463 unscoped nominations received the census only. The selected review is diagnostic and supplies no inferred accuracy rate for unreviewed pairs. Score eligibility stays at zero of 530 under the released policy. The authentic same-lineage assessment trigger is still unsatisfied. [Retained result and eligibility](../records/nce.gs518-artifact-trigger.json)

## Selected unscoped-code dispositions

“Useful” means the two inspected endpoints support navigation between a source mention and the corresponding caption or declaration. “Co-reference” means they independently mention the same apparent target. “Ambiguous” means surrounding source context prevents a confident resolution from the bare number.

| Pair | Physical pages | Judgment |
|---:|---|---|
| 1 | 136/138 ↔ 136/138 | Co-reference. Two exact offsets in the same passage, `#/texts/2329` at 159–170 and 73–84, both point to the same shuffle-distance graphic. |
| 2 | 136/138 ↔ 137 | Useful. The VariationList passage points to the distance-to-random-process caption, `#/texts/2333`. |
| 3 | 204 ↔ 204 | Useful. The Benford comparison for Clinton’s tax returns points to the caption naming the same leading-digit plot. |
| 4 | 407 ↔ 350 | Useful. The continuous/discrete caveat names Theorem 9.3, and p350 is its actual theorem statement. The producer labels the declaration `reference`. |
| 8 | 309 ↔ 308 | Useful. The caption for convolutions of exponential densities matches the preceding passage that lists n = 2, 4, 6, 8, and 10. |
| 10 | 212 ↔ 213 | Useful. The passage about the May 3, 1996 data points to the Powerball contestant-choice table. |
| 13 | 110 ↔ 111 | Useful. The calculation over several p values points to the caption “The power curve.” |
| 18 | 175 ↔ 279 | Useful. Theorem 4.3 on independence of transformed variables supports the example involving X squared and Y squared. The declaration is labeled `reference`. |
| 41 | 55 ↔ 192 | Ambiguous. Both discuss the normal density and cite Section 5.2, but original p55 also prints “of Chapter 4.3.” The bare code discards that conflict. |
| 43 | 55 ↔ 331 | Ambiguous. The latter points to a method for simulating normal variables, while p55 has the same inconsistent chapter qualifier as pair 41. |
| 66 | 108 ↔ 333/334 | Useful. The binomial-distribution caption matches the later comparison of binomial plots across n and p. |
| 360 | 336 ↔ 407 | Useful. The later limit discussion points back to the corrected spike graph with standard normal density. |
| 431 | 224 ↔ 224 | Useful. The discussion explicitly points to its expected-values table. |
| 444 | 389 ↔ 390 | Useful. The branching-process parameters precede and refer to the probability-of-dying-out table. |
| 445 | 393 ↔ 394 | Useful. The geometric probabilities in the preceding prose point to the comparison of observed and expected frequencies. |
| 495 | 397 ↔ 398 | Useful. The twenty simulations mentioned in the text point to the finite-distribution chain-letter table. |
| 505 | 202 ↔ 202 | Useful. The explanation of marginal totals refers to the observed-data table immediately above it. |
| 515 | 370 ↔ 341 | Co-reference. The exercise and worked college-admissions example both explicitly use the normal table labeled 9.4. |
| 518 | 283/284 ↔ 217 | Useful. The queueing discussion points to the earlier figure caption “Queue sizes.” |
| 528 | 454 ↔ 454 | Useful. The chip-redistribution prose points to the tuple display’s caption on the same page. |

Sixteen inspected unscoped pairs support the narrow navigation relation, two are co-references, and two remain ambiguous. The theorem examples show why endpoint role classification should be checked separately from target agreement. Revision, alias, and same-lineage assertions require separate evidence.

## Lexical-title dispositions

“Series” identifies distinct outputs with a concrete shared experiment, construction, or illustrative role visible in the compared source. “Topic” means related subject matter with materially different inputs or quantities. “Collision” means the shared descriptor or identical caption is insufficient to relate the distinct subject, population, or example. “Variant” records the one source-confirmed reuse of a diagram’s topology with a substantive edit. All 47 remain distinct caption occurrences and keep their released namespace-unavailable standing.

| Pair | Physical pages | Disposition |
|---:|---|---|
| 7 | 309 ↔ 301 | Series. Exponential convolutions for varying n versus two terms, both at λ = 1. |
| 14 | 16 ↔ 13 | Series. Peter’s heads-or-tails winnings after 10,000 versus 40 plays. |
| 15 | 16 ↔ 16 | Series. Peter’s winnings after 10,000 versus 1,000 plays, on the same printed page. |
| 64 | 108 ↔ 317 | Topic. Binomial and Bernoulli-trials distributions share a family, but the captions name distinct plots in different chapters. |
| 65 | 108 ↔ 193 | Topic. Binomial and geometric distributions are different laws. |
| 105 | 156 ↔ 144 | Topic. A forward-and-reverse tree comparison and an earlier reverse-tree diagram have different source roles. |
| 146 | 301 ↔ 307 | Series. Two uniform densities versus a series of n uniform densities. |
| 147 | 301 ↔ 301 | Topic. Uniform and exponential convolution figures are different inputs on the same page. |
| 149 | 301 ↔ 308 | Topic. Two uniform densities and n standard normals use different inputs. |
| 155 | 74 ↔ 72 | Series. The simulation and the calculation refer to the same Example 2.15 but depict different results. |
| 173 | 24 ↔ 260 | Topic. A general random-walk graphic and an ESP application have different contexts. |
| 199 | 285 ↔ 15 | Collision. Queue lengths and coin-toss winnings are unrelated quantities. |
| 200 | 285 ↔ 286 | Series. Queue lengths and queue waiting times are different measurements in the same model. |
| 211 | 350 ↔ 350 | Series. Two different plots have the identical title “Distribution of standardized sums” and distinct codes. |
| 215 | 56 ↔ 55 | Series. Sum of 100 random numbers versus sum of two. |
| 228 | 185 ↔ 386 | Collision. “Tree” matches different examples in conditional probability and branching processes. |
| 229 | 185 ↔ 184 | Collision. The tree captions explicitly name distinct examples 4.26 and 4.25. |
| 247 | 212 ↔ 305 | Collision. Identical “Observed data” headings refer to different data, including die outcomes on p305. |
| 249 | 212 ↔ 202 | Collision. “Observed data” repeats across separate analyses and tables. |
| 262 | 13 ↔ 16 | Series. Peter’s winnings after 40 and 1,000 plays. |
| 268 | 132 ↔ 132 | Series. The two shuffle figures distinguish a 2-unshuffle from a 4-unshuffle. |
| 291 | 366 ↔ 365 | Topic. Standardized-sum density figures use exponential and uniform inputs with different n sets. |
| 309 | 164 ↔ 90 | Collision. A joint distribution exercise and fixed-point distributions are different objects. |
| 310 | 164 ↔ 151 | Collision. Identical “Joint distribution” captions cover an exercise distribution and the cancer/smoking joint distribution. |
| 314 | 203 ↔ 224 | Collision. “Expected data” repeats in different analyses. |
| 346 | 71 ↔ 72 | Collision. The calculations cite different examples, 2.14 and 2.15. |
| 347 | 71 ↔ 72 | Series. The calculation and the resulting distribution/density display both explicitly refer to Example 2.14. |
| 354 | 307 ↔ 308 | Topic. Convolutions of n uniform and n standard normal densities use different laws. |
| 362 | 73 ↔ 70 | Topic. Two transformation examples use different random variables and transformations. |
| 371 | 90 ↔ 151 | Collision. Fixed points and the cancer/smoking joint distribution are unrelated data. |
| 378 | 399 ↔ 398 | Series. Chain-letter simulations compare Poisson and finite offspring distributions. |
| 381 | 449 ↔ 328 | Collision. The maze problem and the area problem share only a generic descriptor. |
| 382 | 449 ↔ 461 | Variant. Both captions say “The maze problem.” The later diagram adds food in state 5, and Example 11.24 explicitly turns the earlier maze into an absorbing chain. |
| 385 | 306 ↔ 226 | Topic. Chi-squared densities with five and three degrees of freedom are distinct plots. |
| 389 | 317 ↔ 193 | Topic. Bernoulli-trials and geometric distributions name different laws. |
| 421 | 305 ↔ 202 | Collision. The die roll counts and political contingency data both use “Observed data.” |
| 423 | 389 ↔ 193 | Collision. Geometric determination of an extinction fixed point and geometric distributions use “geometric” differently. |
| 439 | 214 ↔ 75 | Topic. A family of exponential densities and a graph with λ = 1/30 have different scopes and source roles. |
| 449 | 328 ↔ 461 | Collision. The area problem and the absorbing maze are unrelated examples. |
| 465 | 394 ↔ 448 | Collision. Branching-population frequencies and Markov-chain weather frequencies compare different observations. |
| 472 | 174 ↔ 175 | Series. The paired displays distinguish independent X1/X2 and dependent X1/X3, with opposing conclusions. |
| 481 | 66 ↔ 223 | Topic. Dart distances in 400 throws and 1,000 drops are separate samples and experimental conditions. |
| 496 | 86 ↔ 87 | Series. The identical “Birthday problem” captions cover different sample-size ranges in the same computation. |
| 503 | 386 ↔ 184 | Collision. The branching-process and conditional-probability trees belong to different examples. |
| 504 | 15 ↔ 286 | Collision. Coin-toss winnings and queue waiting times are unrelated outcomes. |
| 510 | 41 ↔ 102 | Collision. Pascal’s allocation table for stopping a game is a different object from the binomial-coefficient triangle. |
| 522 | 72 ↔ 70 | Topic. Distinct distribution/density plots use different transformed variables and examples. |

Pair 382 is the clearest case where a candidate could help a reader beyond mere shared wording. In the source rendering, Figures 11.4 and 11.5 preserve the nine-cell walls and numbering, and the later diagram adds the state-5 food symbol. The later source prose explicitly relates the models. The exact caption pointers are `#/texts/8257` and `#/texts/8461`. The artifact report still supplies neither an admitted namespace nor an explicit identity relation for this pair. Conversely, two of the “Observed data” pairs have identical caption strings despite different datasets. Source witness and relation type matter independently of lexical agreement.

Publication and calibration are outside the reviewed evidence. The observed useful links are development evidence on an already exposed source.
