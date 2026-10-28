"""HOOK FOR THE COORDINATOR: real-text locator cases on S1's canonical text.

Each case: (page, unit prefixes, quote, expected substring | "COARSE", expected tier).

- ``page``: S1 file stem (``special__Normal``).
- ``unit prefixes``: start of each unit/paragraph segment's text forming the annotation unit
  (T1 is the lead-in paragraph plus unit ``dfn1``); each is resolved to the smallest
  ``unit``/``paragraph`` segment whose text starts with it.
- ``quote``: what an annotator writes.
- the cited sentence is the sentence of the unit that contains the expected substring (for
  "COARSE", give the expected sentence's prefix as the 6th element).

Add cases by appending to ``REAL_CASES``; ``test_locate_real.py`` runs them when the S1 files
exist. Sentences come from ``results/s1/sentences/<page>.<variant>.jsonl`` with ``variant``
from the environment variable ``S0_SENTENCE_VARIANT`` (default ``provisional``).
"""

T1_UNIT = ["As usual, our starting point", "For \\(a \\in \\R\\) and \\(b \\in (0, \\infty) \\)"]
T2_UNIT = ["Suppose again that \\( X \\) has the normal distribution with location parameter"]
T3_UNIT = ["Suppose that \\(X\\) is normally distributed with mean \\(\\mu\\) and variance"]
T4_UNIT = ["Suppose that \\(Y\\) has the normal distribution with mean \\(\\mu \\in \\R\\)"]

REAL_CASES = [
    ("special__LocationScale", T1_UNIT,
     "we fixed random variable \\( Z \\) defined on the probability space, with values in \\( \\R \\)",
     "we fixed random variable \\( Z \\) defined on the probability space, with values in \\( \\R \\)", 1),
    ("special__LocationScale", T1_UNIT, "let \\(X = a + b \\, Z\\)", "let \\(X = a + b \\, Z\\)", 1),
    ("special__LocationScale", T1_UNIT, "let $X = a + b Z$", "let \\(X = a + b \\, Z\\)", 3),
    ("special__LocationScale", T1_UNIT, "is called the location-scale family associated with the given distribution of \\(Z\\)",
     "is called the location-scale family associated with the given distribution of \\(Z\\)", 1),
    ("special__Normal", T2_UNIT,
     "the location and scale parameters are also the mean and standard deviation, respectively",
     "the location and scale parameters are also the mean and standard deviation, respectively", 1),
    ("special__Normal", T2_UNIT, "scale parameter $\\sigma \\in (0,\\infty)$", "scale parameter \\( \\sigma \\in (0, \\infty) \\)", 3),
    ("special__Normal", T3_UNIT,
     "\\(a + b X\\) is normally distributed with mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\)",
     "\\(a + b X\\) is normally distributed with mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\)", 1),
    ("special__Normal", T3_UNIT, "$b^2\\sigma^2$", "\\(b^2 \\sigma^2\\)", 3),
    ("special__LogNormal", T4_UNIT, "The parameter \\( \\sigma \\) is the shape parameter of the distribution",
     "The parameter \\( \\sigma \\) is the shape parameter of the distribution", 1),
    ("special__LogNormal", T4_UNIT, "Then \\(X = e^Y\\) has the lognormal distribution with parameters \\(\\mu\\) and \\(\\sigma\\)",
     "Then \\(X = e^Y\\) has the lognormal distribution with parameters \\(\\mu\\) and \\(\\sigma\\)", 1),
    # trace-style list numbering and $-math: 3 marker chars and 6 delimiter chars differ
    ("special__LogNormal", T4_UNIT, "1. The parameter $\\sigma$ is the shape parameter of the distribution",
     "COARSE", None, "(a) The parameter"),
]
