"""B's bounded source-authored literal expectations; no actual component values author gold.

Runtime product/source pins bind these meanings only after source authentication.
The original run152 IDs identify assessed outputs, not expected term/content bytes.
"""
B_CASES = (
    dict(case_id='B-LITERAL-NORMAL', component_id='dd40f6c3f4447b2a25797110af22a04d16d1b35b1ed08f88f9c1922332d515d5',
         source_uri='grinstead-snell-physical211-220.pdf', term_pointer='#/texts/197',
         term='The normal density function', content_pointer='#/texts/198',
         content=r'f _ { X } ( x ) = \frac { 1 } { \sqrt { 2 \pi } \sigma } e ^ { - ( x - \mu ) ^ { 2 } / 2 \sigma ^ { 2 } } \ .',
         interpretation='definition', judgment='supported',
         context=('The normal density function with parameters µ and σ is defined as follows:',
                  'The parameter σ is a measure of the "spread" of the density, and thus it is assumed to be positive.'),
         reason='Independently read explicit defining clause and adjacent normal-density display. This supports the narrow source-attributed term-to-formula definition. Parameters µ/σ and positive σ remain local conditions, not complete emitted scope. Native conversion provides this formula; no scientific normalization or PDF fidelity claim.'),
    dict(case_id='B-LITERAL-MARGINALS', component_id='1260f6b3c5b66b10b7d058303de67975cf8e98c4fa748d69c8d788f258aa5989',
         source_uri='grinstead-snell-physical201-210.pdf',term_pointer='#/texts/16',term='marginal totals',
         content_pointer='#/texts/16',content='The row and column sums',interpretation='explanation',judgment='supported',
         context=('The row and column sums are called marginal totals, or marginals.',),
         reason='Independent source reading names row/column sums marginal totals. Explanation is a compatible coarse type for this narrow naming attachment. Tables/axis notation and alternate name marginals remain outside the pair; no table-cell or scientific completeness claim.'),
    dict(case_id='B-LITERAL-WRONG-PROBABILITY-SUBJECT',component_id='10701a2dec9c4a68f38de709185a24ed667b282bc215f1f506ea94415bcb2846',
         source_uri='grinstead-snell-physical231-240.pdf',term_pointer='#/texts/13',term='the probability that X is less than Y',
         content_pointer='#/texts/14',content=r'P ( X < Y ) = \int _ { 0 } ^ { \infty } f ( x ) ( 1 - G ( x ) ) \, d x , \\',
         interpretation='explanation',judgment='unsupported',
         context=('If X and Y are two independent random variables with exponential densities f(x) = λe-λx and g(x) = µe-µx, respectively, then the probability that X is less than Y is given by',
                  'where G(x) is the cumulative distribution function for g(x). Explain why this is the case. Use this to show that'),
         reason='B independently expects the probability comparison P(X<Y), not Y alone, as the explanatory subject. Integral is useful narrow content under the stated independent exponential model and exercise speech act. Exact emitted Y-to-integral pair is unsupported; this corrected expectation must mismatch it.'),
    dict(case_id='B-LITERAL-HISTORICAL-CONTRAST',component_id='d5715568638f1b1644d6a105bfb3c152946b02ec01d31f601f9ba5797c9b2fe9',
         source_uri='grinstead-snell-physical251-260.pdf',term_pointer='#/texts/35',term='the expected value',term_occurrence=0,
         content_pointer='#/texts/35',content='a weighted average',interpretation='unresolved',judgment='unsupported',
         context=('Thus, instead of defining the expected value as a weighted average, Huygens assumed that the expected value of certain symmetric gambles are known and deduced the other values from these.',),
         reason='Expected value and weighted average are mentioned within an instead-of historical contrast, not a positive performed definition. The component pair may be retained only with unresolved/contrastive interpretation; unresolved is an independently authored refusal to assert the available definition/explanation labels as a positive performed act. This exact typed alternative is a bounded encoding limit, not a complete representation of the historical relationship.'),
)
