# Statistics corpus

These source acquisitions support calibration and evaluation of probability and
statistics document processing. The files retain their original bytes. This
index records what the public archive covers and how to retrieve it.

| Source | Public archive | Attribution and terms |
| --- | --- | --- |
| Kyle Siegrist, *Random: Probability, Mathematical Statistics, Stochastic Processes* | [Original HTML collection](corpus/siegrist_random/random/) and [LibreTexts PDF](corpus/siegrist_random/Full_PDF/Full.pdf) | [RandomServices](https://www.randomservices.org/random/) · [LibreTexts edition](https://stats.libretexts.org/Bookshelves/Probability_Theory/Probability_Mathematical_Statistics_and_Stochastic_Processes_%28Siegrist%29) · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) |
| Charles M. Grinstead and J. Laurie Snell, *Introduction to Probability* | [Authenticated 4 July 2006 PDF](corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf) and [expanded LaTeX and figures](corpus/grinstead_snell/latex_source/) | CHANCE Project edition, copyright Peter G. Doyle and the original authors as identified on the title page. [Dartmouth edition](https://math.dartmouth.edu/~prob/prob/prob.pdf) · [GNU Free Documentation License](licenses/GFDL-1.3.txt) |
| NIST/SEMATECH, *e-Handbook of Statistical Methods* | [Selected HTML and assets](corpus/nist_ehandbook/html/) and [seven chapter PDFs](corpus/nist_ehandbook/pdf/) | DOI `10.18434/M32189`. Republished courtesy of the National Institute of Standards and Technology. [Handbook](https://www.itl.nist.gov/div898/handbook/) · [NIST terms](https://www.nist.gov/copyrights-disclaimers) |

## Retrieve and verify

Open an archive link in GitHub to view the tracked path and retrieve its Git
LFS contents. From a checkout with Git LFS installed, retrieve the public files
and verify the [byte manifest](PUBLIC-MANIFEST.sha256).

```sh
git lfs pull --include="docs/statistics_corpus/corpus/**"
cd docs/statistics_corpus
sha256sum -c PUBLIC-MANIFEST.sha256
```

The Grinstead–Snell PDF has 518 physical pages and SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`.
It is the exact input documented by the
[whole-book review](../design_review/evidence/2026-11-08_nce-full-book/README.md).
The LibreTexts PDF is the 17 June 2026 compilation of Siegrist's work.
Original HTML retains its source notices and links. The source archive
keeps the expanded Dartmouth TeX because it matches the tarball entries
byte for byte.

## Local material and upstream access

The full NIST PDF and the Process Improvement chapter include a separately
copyrighted ASA/SIAM case study. Use NIST's
[printer-friendly downloads](https://www.itl.nist.gov/div898/handbook/toolaids/pff/index.htm)
for those editions. The [Wiley edition of *Statistical Distributions*](https://onlinelibrary.wiley.com/doi/book/10.1002/9780470627242)
requires separate access. The [Dartmouth supplements](https://math.dartmouth.edu/~prob/prob/extra/)
remain at their source because the edition's redistribution notice covers
the book and its LaTeX source.

The local acquisition includes evaluation references, generated indexes
and acquisition logs. Those files support local preparation and evaluation.
The site runtime and duplicate archive also stay outside the public corpus.
