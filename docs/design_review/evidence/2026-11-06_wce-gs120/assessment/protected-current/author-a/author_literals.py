"""A's manually source-selected literals, frozen before deterministic citation lowering.

No projection, emitted-component text copying, or B/C expectation imports occur here.
Offsets address the source-packet passage, not the native orig field.
"""
SCOPE = 'grinstead-snell-physical191-310'
ROWS = [
    dict(
        name='marginal-totals', ordinal=4,
        component_id='1260f6b3c5b66b10b7d058303de67975cf8e98c4fa748d69c8d788f258aa5989',
        passage_id='gs120-recovered-source-111', source_view_id=111,
        term=dict(start=3624, end=3639, text='marginal totals'),
        content=dict(start=3589, end=3612, text='The row and column sums'),
        interpretation='explanation', judgment='supported',
        pointers=['#/texts/16'],
        quote='The row and column sums are called marginal totals, or marginals.',
        explanation='The source directly names the row and column sums marginal totals. Explanation is a defensible coarse interpretation of this naming. This supports only the literal naming pair in the cited contingency-table context, not completeness of all names, tables, values, or statistical claims.',
        limits=['The alias marginals is not in the selected term.', 'The table and row/column role bindings reside in the enclosing cited passage.', 'Positive attachment is source support, not scientific truth or complete definition recall.'],
    ),
    dict(
        name='normal-density', ordinal=12,
        component_id='dd40f6c3f4447b2a25797110af22a04d16d1b35b1ed08f88f9c1922332d515d5',
        passage_id='gs120-recovered-source-116', source_view_id=116,
        term=dict(start=14565, end=14592, text='The normal density function'),
        content=dict(start=14640, end=14749, text=r'f _ { X } ( x ) = \frac { 1 } { \sqrt { 2 \pi } \sigma } e ^ { - ( x - \mu ) ^ { 2 } / 2 \sigma ^ { 2 } } \ .'),
        interpretation='definition', judgment='supported',
        pointers=['#/texts/197', '#/texts/198', '#/texts/199'],
        quote='The normal density function with parameters µ and σ is defined as follows:',
        explanation='The explicit defining sentence selects the normal density function, and the immediately adjacent display gives its parametric density expression. The chosen narrow label and display are supported as a definition in this passage. The enclosing passage supplies the parameters and positive-sigma qualification; the pair alone is not a complete free-standing formal characterization.',
        limits=['Parameter qualifier with parameters µ and σ is outside the selected term.', 'The cited passage says σ is assumed positive and describes µ and σ; no normalization proof is assessed.', 'The native orig formula linearizes fraction geometry; this assessment uses the converted expression with the native prose and orig as source context, without PDF image inspection.', 'Positive attachment is source support, not external scientific verification.'],
    ),
    dict(
        name='probability-subject', ordinal=13,
        component_id='10701a2dec9c4a68f38de709185a24ed667b282bc215f1f506ea94415bcb2846',
        passage_id='gs120-recovered-source-122', source_view_id=122,
        term=dict(start=1724, end=1761, text='the probability that X is less than Y'),
        content=dict(start=1774, end=1849, text=r'P ( X < Y ) = \int _ { 0 } ^ { \infty } f ( x ) ( 1 - G ( x ) ) \, d x , \\'),
        interpretation='explanation', judgment='unsupported',
        pointers=['#/texts/13', '#/texts/14', '#/texts/15'],
        quote='then the probability that X is less than Y is given by',
        explanation='The emitted component selects Y as subject, but the source explicitly gives the probability that X is less than Y. The exact expected public statement below is a corrected alternative, using the full probability subject. The original selected component therefore is unsupported. Explain why and Use this to show preserve the exercise context; no proof or bulb result is established by this attachment.',
        limits=['The formula applies in the source to independent random variables with stated exponential densities.', 'G is the cumulative distribution function for g, as the following sentence says.', 'The corrected alternative is a proposal for comparison, not an emitted or admitted replacement.', 'No claim that Y itself is defined or explained by this probability integral is supported.'],
    ),
    dict(
        name='historical-contrast', ordinal=22,
        component_id='d5715568638f1b1644d6a105bfb3c152946b02ec01d31f601f9ba5797c9b2fe9',
        passage_id='gs120-recovered-source-135', source_view_id=135,
        term=dict(start=4363, end=4381, text='the expected value'),
        content=dict(start=4337, end=4684, text='Thus, instead of defining the expected value as a weighted average, Huygens assumed that the expected value of certain symmetric gambles are known and deduced the other values from these. Although this requires a good deal of clever manipulation, Huygens ended up with values that agree with those given by our modern definition of expected value.'),
        interpretation='explanation', judgment='unsupported',
        pointers=['#/texts/34', '#/texts/35'],
        quote='Thus, instead of defining the expected value as a weighted average, Huygens assumed that the expected value of certain symmetric gambles are known and deduced the other values from these.',
        explanation='The emitted pair interprets the embedded weighted-average phrase as a direct definition. In this source it is an instead-of-defining historical contrast attributed to Huygens. The exact expected statement is a bounded corrected explanatory alternative retaining the contrast and attribution in its content; it is not authority for an unconditional definition. The original direct-definition component is unsupported.',
        limits=['The corrected explanatory alternative is proposed, not an emitted or admitted replacement.', 'The passage concerns symmetric gambles and unequal rational-probability cases; the local explanation is not a new universal expectation definition.', 'Historical accuracy has not been independently verified.', 'The selected explanatory content overlaps its term intentionally because the sentence itself preserves the historical speech act.'],
    ),
]
