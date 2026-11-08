# Remaining whole-book unscoped artifact nominations

I examined the 463 unscoped-code pairs left after the [initial artifact review](artifact-nominations.md). Together the two reviews give a source-navigation disposition to each of the 530 nominated pairs. This extension uses the same Standard product and whole-book artifact result, run 300/cut 417/task 1373. The source is the authenticated 518-page Grinstead–Snell PDF.

The retained result supplies each endpoint’s contribution ID, native item pointer, and anchored offsets. The 463 pairs involve 514 distinct endpoints grouped here by 211 kind-and-code combinations. I read the anchored source context for each endpoint. Each retained exact quote matched its native text slice. I consulted the original PDF for contradictory or suspect cases. The table groups repeated citations to the same numbered source target and lists each pair’s one-based packet index exactly once. Caption and theorem target locators refer to the Standard product, task 1342. Section groups contain reference endpoints.

- **Navigation** links a source mention to the matching caption or theorem declaration.
- **Co-reference** joins two passages that cite the same source target in compatible contexts.
- **Ambiguous** retains an unresolved conflict in the source reference.
- **Duplicate** joins two retained readings of a single source mention.
- **Wrong target** joins an erroneous retained designator to a different source target.

Disposition totals for this extension are 268 navigation, 190 co-reference, 2 ambiguous, 1 duplicate, and 2 wrong target.

## Source-verified exceptions

- **Pairs 301 and 302, physical p70.** The original closing sentence of the transformed-uniform example says “See Figure 2.13.” The retained formula item `#/texts/1108` at offsets 278–288 reads “Figure 2.1.” The candidates therefore link to the spinner discussion and caption on pp49–50. The exact native anchor faithfully locates a corrupted reference. Its precision says nothing about fidelity to the original PDF.
- **Pairs 42 and 44, physical p55.** The original prints “Section 5.2 of Chapter 4.3,” matching the native p55 item `#/texts/803` at offsets 537–548. The other endpoints refer to continuous densities and exponential simulation in Section 5.2. The contradictory chapter qualifier remains part of the witness and leaves these two matches ambiguous. Pairs 41 and 43 have the same issue in the initial review.
- **Pair 252, physical p503.** The original contains one sentence crediting Theorem 12.2. Standard projects that sentence both inside formula `#/texts/9234` at offsets 758–770 and in adjacent text `#/texts/9235` at offsets 37–49. This pair joins duplicate readings of one source occurrence. Other pairs using either endpoint still point to the theorem and should not be counted as additional source mentions.
- **Figure 2.12, physical p66.** The prose says the plotted simulation used 1,000 darts and explicitly names Figure 2.12. The caption says 400 throws. The target navigation is supported, while the conflicting sample size remains unresolved. The count conflict is present in the original.

The score-eligibility record independently assigns `reference_only` standing to all 463 pairs. Zero of the full 530 qualify for same-lineage scoring. [Artifact eligibility record](../records/nce.gs518-artifact-trigger.json)

## Figure targets

| Code | Witness context and target | Navigation | Co-reference | Ambiguous | Duplicate | Wrong target |
|---|---|---|---|---|---|---|
| 1.1 | Peter's winnings in 40 plays of heads or tails · p13 · `#/texts/92` | 73, 261 | 74 | — | — | — |
| 1.4 | Peter's winnings in 1000 plays of heads or tails · p16 · `#/texts/138` | 357 | — | — | — | — |
| 1.5 | Peter's winnings in 10,000 plays of heads or tails · p16 · `#/texts/153` | 16, 17 | 497 | — | — | — |
| 1.7 | Basic set operations · p30 · `#/texts/357` | 446 | — | — | — | — |
| 1.8 | Tree diagram for three tosses of a coin · p33 · `#/texts/401` | 256, 257 | 266 | — | — | — |
| 1.9 | Pascal's table · p41 · `#/texts/546` | 509 | — | — | — | — |
| 2.1 | A spinner · p50 · `#/texts/703` The p70 formula truncates the original Figure 2.13 code. | 349 | — | — | — | 301, 302 |
| 2.2 | Area under y = x2  · p51 · `#/texts/715` | 19 | — | — | — | — |
| 2.3 | Computing the area by simulation · p52 · `#/texts/731` | 202 | — | — | — | — |
| 2.4 | Buffon's experiment · p53 · `#/texts/744` | 276 | — | — | — | — |
| 2.5 | Set E of pairs (θ, d) with d < 1 2 sinθ · p53 · `#/texts/748` | 195 | — | — | — | — |
| 2.6 | Simulation of Buffon's needle experiment · p54 · `#/texts/765` | 417 | — | — | — | — |
| 2.7 | Sum of two random numbers · p55 · `#/texts/788` | 305, 400 | 304 | — | — | — |
| 2.8 | Sum of 100 random numbers · p56 · `#/texts/810` | 214 | — | — | — | — |
| 2.9 | Random chord · p56 · `#/texts/824` | 277, 298 | 278 | — | — | — |
| 2.10 | Bertrand's paradox · p58 · `#/texts/854` | 56 | — | — | — | — |
| 2.11 | Spinner experiment · p64 · `#/texts/958` | 274 | — | — | — | — |
| 2.12 | Distribution of dart distances in 400 throws · p66 · `#/texts/1013` The prose and caption refer to the same figure but print conflicting sample sizes. | 437, 474 | 436 | — | — | — |
| 2.13 | Distribution and density for X = U 2  · p70 · `#/texts/1081` | 403 | — | — | — | — |
| 2.14 | Calculation of distribution function for Example 2.14 · p71 · `#/texts/1113` | 201 | — | — | — | — |
| 2.15 | Distribution and density functions for Example 2.14 · p72 · `#/texts/1131` | 210 | — | — | — | — |
| 2.16 | Calculation of Fz for Example 2.15 · p72 · `#/texts/1154` | 375 | — | — | — | — |
| 2.17 | Distribution and density for Z = √X 2 + Y 2  · p73 · `#/texts/1167` | 258 | — | — | — | — |
| 2.18 | Simulation results for Example 2.15 · p74 · `#/texts/1209` | 154 | — | — | — | — |
| 2.19 | Calculation of FZ · p75 · `#/texts/1232` | 50 | — | — | — | — |
| 2.20 | Exponential density with λ = 1/30 · p75 · `#/texts/1240` | 484 | — | — | — | — |
| 2.21 | Residual lifespan of a hard drive · p76 · `#/texts/1255` | 466 | — | — | — | — |
| 2.22 | Tree for infinite number of tosses of a coin · p78 · `#/texts/1285` | 524 | — | — | — | — |
| 3.1 | Tree for your menu · p84 · `#/texts/1404` | 284 | — | — | — | — |
| 3.2 | Two-stage probability assignment · p85 · `#/texts/1471` | 185, 186 | 184 | — | — | — |
| 3.3 | Pascal's triangle · p102 · `#/texts/1692` | 255 | — | — | — | — |
| 3.4 | Tree diagram of three Bernoulli trials · p104 · `#/texts/1719` | 98 | — | — | — | — |
| 3.5 | Binomial distributions · p108 · `#/texts/1831` | 63 | 170 | — | — | — |
| 3.6 | Simulation of the Galton board · p109 · `#/texts/1869` | 416, 422 | 415 | — | — | — |
| 3.8 | Pythagorean triangular patterns · p117 · `#/texts/2012` | 191 | — | — | — | — |
| 3.9 | Geometric representation of the tetrahedral number 10 · p117 · `#/texts/2017` | 312 | — | — | — | — |
| 3.10 | Chu Shih-chieh's triangle. [From J. Needham, Science and Civilization in China, vol. 3 (New York: Cambridge Unive… · p119 · `#/texts/2036` | 339 | — | — | — | — |
| 3.11 | Before a 2-unshuffle · p132 · `#/texts/2239` The same ordering is the start of one procedure and an intermediate outcome of another. | 269, 270 | 514 | — | — | — |
| 3.12 | Before a 4-unshuffle · p132 · `#/texts/2257` | 286 | — | — | — | — |
| 3.13 | Distance to the random process · p137 · `#/texts/2333` | 72 | — | — | — | — |
| 4.1 | Tree diagram · p143 · `#/texts/2398` | 267 | — | — | — | — |
| 4.2 | Reverse tree diagram · p144 · `#/texts/2470` | 179 | — | — | — | — |
| 4.3 | The Monty Hall problem · p146 · `#/texts/2490` | 368 | — | — | — | — |
| 4.4 | Conditional probabilities for the Monty Hall problem · p147 · `#/texts/2563` | 328 | — | — | — | — |
| 4.5 | Forward and reverse tree diagrams · p156 · `#/texts/2727` | 106 | — | — | — | — |
| 4.6 | From Woodstock to Tunbridge · p163 · `#/texts/2875` | 131, 132, 133 | 187, 188, 206 | — | — | — |
| 4.7 | X1 and X2 are independent · p174 · `#/texts/3055` | 471 | — | — | — | — |
| 4.8 | X1 and X3 are not independent · p175 · `#/texts/3082` | 194 | — | — | — | — |
| 4.9 | Beta density for α = β = .5, 1, 2 · p176 · `#/texts/3104` | 361 | — | — | — | — |
| 4.10 | Play the best machine · p179 · `#/texts/3156` | 313 | — | — | — | — |
| 4.11 | Play the winner · p180 · `#/texts/3197` | 192 | — | — | — | — |
| 4.12 | Tree for Example 4.25 · p184 · `#/texts/3299` | 345 | — | — | — | — |
| 4.13 | Tree for Example 4.26 · p185 · `#/texts/3354` | 227 | — | — | — | — |
| 4.14 | John Finn's version of Example 4.28 · p187 · `#/texts/3424` | 283 | — | — | — | — |
| 5.1 | Geometric distributions · p193 · `#/texts/3521` | 259, 482 | 260 | — | — | — |
| 5.2 | Negative binomial distribution with k = 2 and p = .25 · p196 · `#/texts/3582` | 152 | — | — | — | — |
| 5.3 | Flying bomb hits · p200 · `#/texts/3631` | 141 | — | — | — | — |
| 5.5 | Distribution of choices in the Powerball lottery · p212 · `#/texts/3801` | 213 | — | — | — | — |
| 5.6 | Exponential densities · p214 · `#/texts/3835` | 384 | — | — | — | — |
| 5.7 | Queue sizes · p217 · `#/texts/3888` | 487 | 486 | — | — | — |
| 5.8 | Waiting times · p217 · `#/texts/3910` | 432 | — | — | — | — |
| 5.9 | Converting a uniform distribution FU into a prescribed distribution FY  · p220 · `#/texts/3963` | 230 | — | — | — | — |
| 5.10 | Normal density for two sets of parameter values · p221 · `#/texts/3984` | 388 | — | — | — | — |
| 5.11 | Distribution of dart distances in 1000 drops · p223 · `#/texts/4023` | 139 | — | — | — | — |
| 5.12 | Chi-squared density with three degrees of freedom · p226 · `#/texts/4065` | 134, 397 | 135 | — | — | — |
| 6.1 | Tree measure for craps · p244 · `#/texts/4360` | 51 | — | — | — | — |
| 6.2 | Tree for 2-prison Monte Carlo roulette · p246 · `#/texts/4430` | 168, 303 | 169 | — | — | — |
| 6.3 | Your money is put in prison · p247 · `#/texts/4461` | 183 | — | — | — | — |
| 6.4 | Mr. Ace's system · p250 · `#/texts/4515` | 322, 376 | 321 | — | — | — |
| 6.5 | Winnings distribution for n = 20 · p251 · `#/texts/4533` | 358 | — | — | — | — |
| 6.6 | Random walk for ESP · p260 · `#/texts/4658` | 308 | — | — | — | — |
| 6.7 | Empirical distribution of An · p269 · `#/texts/4838` | 9 | — | — | — | — |
| 6.8 | Distribution of queue lengths · p285 · `#/texts/5146` | 198 | — | — | — | — |
| 6.9 | Distribution of queue waiting times · p286 · `#/texts/5172` | 299 | — | — | — | — |
| 7.1 | Density of Sn for rolling a die n times · p296 · `#/texts/5354` | 11 | — | — | — | — |
| 7.2 | Convolution of two uniform densities · p301 · `#/texts/5484` | 148 | — | — | — | — |
| 7.3 | Convolution of two exponential densities with λ = 1 · p301 · `#/texts/5494` | 379 | — | — | — | — |
| 7.4 | Chi-squared density with 5 degrees of freedom · p306 · `#/texts/5570` | 112 | — | — | — | — |
| 7.5 | Rolling a fair die · p306 · `#/texts/5581` | 21 | — | — | — | — |
| 7.6 | Convolution of n uniform densities · p307 · `#/texts/5600` | 181, 288 | 180 | — | — | — |
| 7.7 | Convolution of n standard normal densities · p308 · `#/texts/5635` | 92 | — | — | — | — |
| 8.1 | Bernoulli trials distributions · p317 · `#/texts/5814` | 157, 235 | 156 | — | — | — |
| 8.2 | Illustration of Law of Large Numbers - uniform case · p326 · `#/texts/6019` | 287 | — | — | — | — |
| 8.3 | Area problem · p328 · `#/texts/6125` | 450 | — | — | — | — |
| 9.1 | Standard normal density · p334 · `#/texts/6222` | 205 | — | — | — | — |
| 9.2 | Normalized binomial distribution and standard normal density · p335 · `#/texts/6246` | 96 | — | — | — | — |
| 9.3 | Corrected spike graph with standard normal density · p336 · `#/texts/6263` | 166 | 167 | — | — | — |
| 9.4 | Table of values of NA(0, z), the normal area from 0 to z · p339 · `#/texts/6320` | 189 | — | — | — | — |
| 9.5 | Polling simulation · p343 · `#/texts/6451` | 116 | — | — | — | — |
| 9.6 | Confidence interval simulation · p344 · `#/texts/6465` | 394 | — | — | — | — |
| 9.7 | Distribution of standardized sums · p350 · `#/texts/6555` | 456 | — | — | — | — |
| 9.8 | Distribution of standardized sums · p350 · `#/texts/6578` | 212 | — | — | — | — |
| 9.9 | Sums of randomly chosen random variables · p354 · `#/texts/6650` | 140 | — | — | — | — |
| 9.10 | Distribution of heights of adult women · p355 · `#/texts/6685` | 57, 58 | 67 | — | — | — |
| 9.11 | Two-stage version of the quincunx · p359 · `#/texts/6733` | 396 | — | — | — | — |
| 9.13 | Density function for S ∗n (uniform case, n = 2, 3, 4, 10) · p365 · `#/texts/6821` | 402 | — | — | — | — |
| 9.14 | Density function for S ∗n (exponential case, n = 2, 3, 10, 30, λ = 1) · p366 · `#/texts/6845` | 292 | — | — | — | — |
| 9.15 | Graph of t-density for n = 1, 3, 8 and the normal density with µ = 0, σ = 1 · p369 · `#/texts/6898` | 95 | — | — | — | — |
| 10.1 | Tree diagram for Example 10.8 · p386 · `#/texts/7232` | 413, 485 | 412 | — | — | — |
| 10.2 | Graphs of y = z and y = h(z) · p388 · `#/texts/7266` | 190 | — | — | — | — |
| 10.3 | Geometric determination of d · p389 · `#/texts/7305` | 351, 401 | 350 | — | — | — |
| 10.4 | Simulation of Zn/mn for the Keyfitz example · p395 · `#/texts/7416` | 93 | — | — | — | — |
| 11.2 | State of the stepping stone model after 10,000 steps · p421 · `#/texts/7801` | 29 | — | — | — | — |
| 11.3 | Drunkard's walk · p425 · `#/texts/7849` | 59 | — | — | — | — |
| 11.4 | The maze problem · p449 · `#/texts/8257` | 177 | — | — | — | — |
| 11.5 | The maze problem · p461 · `#/texts/8461` | 517 | — | — | — | — |
| 11.6 | Ehrenfest simulation · p470 · `#/texts/8629` | 300 | — | — | — | — |
| 11.7 | Maze for Exercise 7 · p475 · `#/texts/8714` | 377 | — | — | — | — |
| 11.8 | Simplified Monopoly · p477 · `#/texts/8752` | 153 | — | — | — | — |
| 12.1 | A random walk of length 40 · p481 · `#/texts/8812` | 136, 434 | 137 | — | — | — |
| 12.2 | Times in the lead · p503 · `#/texts/9221` | 455 | — | — | — | — |

## Table targets

| Code | Witness context and target | Navigation | Co-reference | Ambiguous | Duplicate | Wrong target |
|---|---|---|---|---|---|---|
| 1.1 | Sample output of the program RandomNumbers · p11 · `#/texts/61` | 55 | — | — | — | — |
| 2.1 | Buffon needle experiments to estimate π · p59 · `#/texts/894` | 320 | — | — | — | — |
| 3.1 | Birthday problem · p86 · `#/texts/1482` | 323 | — | — | — | — |
| 3.3 | Values of the factorial function · p88 · `#/texts/1508` | 197 | — | — | — | — |
| 3.4 | Stirling approximations to the factorial function · p89 · `#/texts/1519` | 340 | — | — | — | — |
| 3.5 | Fixed point distributions · p90 · `#/texts/1532` | 370 | — | — | — | — |
| 3.6 | Snowfall in Hanover · p91 · `#/texts/1539` | 70 | — | — | — | — |
| 3.7 | Ranking of total snowfall · p91 · `#/texts/1540` | 151 | — | — | — | — |
| 3.8 | Binomial probabilities for n = 100, p = 1/2 · p107 · `#/texts/1819` | 223 | — | — | — | — |
| 3.9 | Hat check problem · p114 · `#/texts/1974` | 414 | — | — | — | — |
| 3.10 | Pascal's triangle · p116 · `#/texts/2000` | 26 | — | — | — | — |
| 3.11 | Figurate numbers · p116 · `#/texts/2001` | 359 | — | — | — | — |
| 3.12 | Outcomes for the roll of two dice · p118 · `#/texts/2021` | 329 | — | — | — | — |
| 3.13 | Pascal's solution for the problem of points · p121 · `#/texts/2077` | 222 | — | — | — | — |
| 3.14 | Distance to the random process · p137 · `#/texts/2332` | 272, 380 | 273 | — | — | — |
| 4.1 | Smoking and cancer · p151 · `#/texts/2645` | 71 | — | — | — | — |
| 4.2 | Joint distribution · p151 · `#/texts/2647` | 193 | — | — | — | — |
| 4.3 | Diseases data · p154 · `#/texts/2698` | 94 | — | — | — | — |
| 4.4 | Posterior probabilities · p155 · `#/texts/2713` | 408 | — | — | — | — |
| 4.5 | Collins case probabilities · p162 · `#/texts/2863` | 97 | — | — | — | — |
| 4.6 | Joint distribution · p164 · `#/texts/2905` | 275 | — | — | — | — |
| 5.1 | Poisson approximation to the binomial distribution · p198 · `#/texts/3619` | 138 | — | — | — | — |
| 5.3 | General data table · p202 · `#/texts/3660` | 130 | — | — | — | — |
| 5.4 | Expected data · p203 · `#/texts/3667` | 315 | — | — | — | — |
| 5.5 | Mule kicks · p209 · `#/texts/3759` | 75 | — | — | — | — |
| 5.6 | Observed data · p212 · `#/texts/3800` | 248 | — | — | — | — |
| 5.8 | Calculus class data · p224 · `#/texts/4045` | 294 | — | — | — | — |
| 5.10 | Grading on the curve · p230 · `#/texts/4151` | 159 | — | — | — | — |
| 6.1 | Frequencies for dice game · p234 · `#/texts/4201` | 330 | — | — | — | — |
| 6.2 | Tossing a coin three times · p237 · `#/texts/4249` | 69 | — | — | — | — |
| 6.3 | Number of fixed points · p240 · `#/texts/4295` | 209 | — | — | — | — |
| 6.4 | Payoffs · p254 · `#/texts/4585` | 31 | — | — | — | — |
| 6.5 | Graunt's mortality data · p254 · `#/texts/4586` | 60 | — | — | — | — |
| 7.1 | Observed data · p305 · `#/texts/5560` | 236 | — | — | — | — |
| 8.1 | Chebyshev estimates · p327 · `#/texts/6112` | 30 | — | — | — | — |
| 10.2 | Distribution of number of female children · p390 · `#/texts/7331` | 182 | — | — | — | — |
| 10.5 | Simulation of chain letter (Poisson case) · p399 · `#/texts/7467` | 364 | — | — | — | — |
| 11.1 | Powers of the Land of Oz transition matrix · p416 · `#/texts/7746` The caption is valid as a destination. The selected formula projection loses the matrix contents. | 341 | — | — | — | — |
| 11.2 | Weather in the Land of Oz · p447 · `#/texts/8243` | 204 | — | — | — | — |
| 11.3 | Comparison of observed and predicted frequencies for the Land of Oz · p448 · `#/texts/8247` | 395 | — | — | — | — |

## Theorem targets

| Code | Witness context and target | Navigation | Co-reference | Ambiguous | Duplicate | Wrong target |
|---|---|---|---|---|---|---|
| 1.1 | Probability rules for events, including finite additivity · p30 · `#/texts/336` | 244, 245, 246 | 469, 470, 488 | — | — | — |
| 1.2 | Pairwise disjoint subsets and additivity · p31 · `#/texts/374` | 20 | — | — | — | — |
| 1.4 | Two-event union formula · p32 · `#/texts/389` | 158 | — | — | — | — |
| 3.1 | Number of permutations of a set · p88 · `#/texts/1509` | 234 | — | — | — | — |
| 3.3 | Stirling approximation · p89 · `#/texts/1525` | 521, 523 | 520 | — | — | — |
| 3.4 | Binomial-coefficient recurrence · p101 · `#/texts/1684` | 78 | — | — | — | — |
| 3.5 | Binomial-coefficient formula · p102 · `#/texts/1700` | 506 | — | — | — | — |
| 3.7 | Binomial theorem · p111 · `#/texts/1925` | 334 | — | — | — | — |
| 3.8 | Generalized union formula · p112 · `#/texts/1946` | 109, 348 | 110 | — | — | — |
| 3.9 | Coding of unshuffles · p130 · `#/texts/2224` | 507, 527 | 508 | — | — | — |
| 3.10 | Ordering from a pair of shuffles · p133 · `#/texts/2280` | 171, 203 | 172 | — | — | — |
| 3.11 | Rising sequences and cut/interleaving counts · p134 · `#/texts/2296` | 87 | — | — | — | — |
| 5.1 | Change of variable for continuous distributions · p218 · `#/texts/3933` | 102, 426, 452, 457, 460, 461 | 99, 100, 101, 103, 104, 424, 425, 427, 428, 451, 453, 454, 458, 459, 473 | — | — | — |
| 6.1 | Expected value for discrete random variables · p238 · `#/texts/4263` | 39, 480, 494, 500, 513, 516 | 34, 35, 36, 37, 38, 476, 477, 478, 479, 491, 492, 493, 498, 499, 512 | — | — | — |
| 6.2 | Additivity of expected values · p239 · `#/texts/4274` | 23, 113, 306, 307 | 22, 24, 25, 114, 115, 440 | — | — | — |
| 6.5 | Expectation over a partition · p247 · `#/texts/4486` | 27, 404 | 28 | — | — | — |
| 6.6 | Variance identity · p266 · `#/texts/4781` | 49, 324 | 48 | — | — | — |
| 6.7 | Scaling variance by a constant · p267 · `#/texts/4795` | 150 | — | — | — | — |
| 6.8 | Variance of an independent sum · p267 · `#/texts/4803` | 285 | — | — | — | — |
| 6.9 | Moments of independent trials · p268 · `#/texts/4813` | 40 | — | — | — | — |
| 6.11 | Expected value of a function of a continuous variable · p278 · `#/texts/5023` | 383 | — | — | — | — |
| 6.12 | Expectation of a product under independence · p278 · `#/texts/5029` | 271 | — | — | — | — |
| 6.15 | Variance identity for continuous variables · p280 · `#/texts/5066` | 45, 46, 47 | 392, 393, 464 | — | — | — |
| 9.1 | Central limit theorem for the binomial distribution · p336 · `#/texts/6278` | 372, 373, 374 | 398, 399, 529 | — | — | — |
| 9.3 | Local discrete limit with a greatest-common-divisor hypothesis · p350 · `#/texts/6603` | 53, 54 | 5, 6, 369 | — | — | — |
| 9.4 | Central limit theorem for discrete independent trials · p351 · `#/texts/6611` | 88, 331, 332, 333 | 89, 90, 91, 386, 387, 525 | — | — | — |
| 9.5 | Central limit theorem for independent discrete variables · p353 · `#/texts/6638` | 33 | — | — | — | — |
| 9.6 | Central limit theorem for continuous variables · p365/366 · `#/texts/6842` | 391 | — | — | — | — |
| 11.1 | Multi-step Markov transition probabilities · p415 · `#/texts/7737` | 293 | — | — | — | — |
| 11.2 | Distribution after n Markov steps · p417 · `#/texts/7749` | 429, 511 | 430 | — | — | — |
| 11.6 | Absorption probabilities · p428 · `#/texts/7913` | 363 | — | — | — | — |
| 11.7 | Regular-chain convergence to a common row · p442 · `#/texts/8144` | 84, 121, 220, 318, 442, 447, 502 | 79, 80, 81, 82, 83, 85, 117, 118, 119, 120, 122, 217, 218, 219, 221, 316, 317, 319, 441, 443, 448 | — | — | — |
| 11.8 | Fixed vectors of regular chains and later ergodic discussion · p443 · `#/texts/8155` | 164, 240, 281, 326, 352, 365 | 160, 161, 162, 163, 165, 237, 238, 239, 241, 279, 280, 282, 325, 327, 353 | — | — | — |
| 11.9 | Limit for an arbitrary initial distribution · p445 · `#/texts/8201` | 216 | — | — | — | — |
| 11.10 | Unique stationary probability vector for ergodic chains · p446 · `#/texts/8218` | 411 | — | — | — | — |
| 11.11 | Ergodic Cesàro limit and frequency interpretation · p446 · `#/texts/8221` | 232, 475 | 231 | — | — | — |
| 11.12 | Law of large numbers for ergodic chains · p447 · `#/texts/8231` | 366, 483 | 367 | — | — | — |
| 11.14 | Alternate regular-chain proof via coupling · p457/458 · `#/texts/8406` | 12 | — | — | — | — |
| 11.16 | Mean first passage matrix · p467 · `#/texts/8580` | 61, 62 | 178 | — | — | — |
| 12.1 | Return to the origin at even time · p481 · `#/texts/8813` | 342 | — | — | — | — |
| 12.2 | First-return recursion · p481 · `#/texts/8818` One source mention appears in both the formula and the adjacent text projection. | 128, 253, 337, 419, 489, 519 | 124, 125, 126, 127, 129, 250, 251, 254, 335, 336, 338, 418, 420, 490 | — | 252 | — |
| 12.3 | First-return probability and generating function · p482 · `#/texts/8829` | 174, 462, 463 | 175, 176, 468 | — | — | — |
| 12.4 | Time in the lead · p502 · `#/texts/9211` | 438 | — | — | — | — |
| 12.5 | Time of the first maximum · p503 · `#/texts/9240` | 52 | — | — | — | — |

## Section targets

| Code | Witness context and target | Navigation | Co-reference | Ambiguous | Duplicate | Wrong target |
|---|---|---|---|---|---|---|
| 1.2 | Finite distributions, set events, voting, and historical remarks in Chapter 1. | — | 142, 143, 144, 145, 224, 225, 226, 343, 344, 407 | — | — | — |
| 2.1 | Buffon’s needle and the simulation-based area estimate point into the same introduction. | — | 196 | — | — | — |
| 3.1 | Hat-check, records, and Stirling approximation point to the permutations section. | — | 107, 108, 111 | — | — | — |
| 3.2 | Binomial program, plotted probabilities, and the historical game discussion. | — | 76, 77, 123 | — | — | — |
| 5.1 | Hypergeometric and negative binomial examples point into the discrete-distributions section. | — | 233 | — | — | — |
| 5.2 | Continuous densities and simulation methods. The p55 source anchor carries a conflicting chapter qualifier. | — | 295, 296, 297, 409, 410, 526 | 42, 44 | — | — |
| 6.2 | Discrete moments results and a standardized-variable exercise. | — | 68 | — | — | — |
| 7.1 | Discrete convolution and support of a sum. | — | 530 | — | — | — |
| 7.2 | Continuous convolution and densities of sums. | — | 405, 406, 435 | — | — | — |
| 9.1 | Bernoulli-trials discussion and a later pointer to its third figure. | — | 86 | — | — | — |
| 9.2 | Discrete-trials central limit theorem and examples. | — | 242, 243, 433 | — | — | — |
| 10.1 | Discrete generating-function facts reused by two later derivations. | — | 390 | — | — | — |
| 10.3 | Proof pointers for continuous and discrete central limit results. | — | 263, 264, 265, 289, 290, 501 | — | — | — |
| 11.1 | The Land of Oz Markov chain and its multi-step transition matrix. | — | 207, 208, 311 | — | — | — |
| 11.3 | Stationary vectors and regular-chain limits. | — | 32 | — | — | — |
| 12.1 | Random walks, path representations, and first-return quantities. | — | 355, 356, 467 | — | — | — |
