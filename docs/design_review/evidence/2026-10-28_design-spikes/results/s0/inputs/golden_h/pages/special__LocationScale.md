# special/LocationScale.html (canonical text; [pN] numbers page sentences for reference only)

Location-Scale Families

General Theory


<<< UNIT T1 part 1 begins >>>
[p1] As usual, our starting point is a random experiment, modeled by a probability space \((\Omega, \ms F, \P)\). [p2] So \( \Omega \) is the set of outcomes, \( \ms F \) the collection of events, and \( \P \) the probability measure on the sample space \( (\Omega, \mathscr F) \). [p3] In this section, we assume that we fixed random variable \( Z \) defined on the probability space, with values in \( \R \).
<<< UNIT T1 part 1 ends >>>


Definition


<<< UNIT T1 part 2 begins >>>
[p4] For \(a \in \R\) and \(b \in (0, \infty) \), let \(X = a + b \, Z\). [p5] The two-parameter family of distributions associated with \(X\) is called the location-scale family associated with the given distribution of \(Z\). [p6] Specifically, \(a\) is the location parameter and \(b\) the scale parameter.
<<< UNIT T1 part 2 ends >>>


[p7] Thus a linear transformation, with positive slope, of the underlying random variable \(Z\) creates a location-scale family for the underlying distribution. [p8] In the special case that \(b = 1\), the one-parameter family is called the location family associated with the given distribution, and in the special case that \(a = 0\), the one-parameter family is called the scale family associated with the given distribution. [p9] Scale transformations, as the name suggests, occur naturally when physical units are changed. [p10] For example, if a random variable represents the length of an object, then a change of units from meters to inches corresponds to a scale transformation. [p11] Location transformations often occur when the zero reference point is changed, in measuring distance or time, for example. [p12] Location-scale transformations can also occur with a change of physical units. [p13] For example, if a random variable represents the temperature of an object, then a change of units from Fahrenheit to Celsius corresponds to a location-scale transformation.

Distribution Functions

[p14] Our goal is to relate various functions that determine the distribution of \( X = a + b Z \) to the corresponding functions for \( Z \). [p15] First we consider the (cumulative) distribution function

[p16] If \(Z\) has distribution function \(G\) then \(X\) has distribution function \(F\) given by \[  F(x) = G \left( \frac{x - a}{b} \right), \quad x \in \R\]

Details:

[p17] For \( x \in \R \) \[ F(x) = \P(X \le x) = \P(a + b Z \le x) = \P\left(Z \le \frac{x - a}{b}\right) = G\left(\frac{x - a}{b}\right) \]

[p18] Next we consider the probability density function. [p19] The results are a bit different for discrete distributions and continuous distribution, not surprising since the density function has different meanings in these two cases.

[p20] If \( Z \) has a discrete distribution with probability density function \( g \) then \( X \) also has a discrete distribution, with probability density function \( f \) given by \[ f(x) = g\left(\frac{x - a}{b}\right), \quad x \in \R \]

Details:

[p21] If \( Z \) takes values in a countable subset \( S \subset \R \) then \( X \) takes values in \( T = \{a + b z: z \in S\} \), which is also countable. [p22] Moreover \[ f(x) = \P(X = x) = \P\left(Z = \frac{x - a}{b}\right) = g\left(\frac{x - a}{b}\right), \quad x \in \R \]

[p23] If \(Z\) has a continuous distribution with probability density function \(g\), then \(X\) also has a continuous distribution, with probability density function \(f\) given by

[p24] \[ f(x) = \frac{1}{b} \, g \left( \frac{x - a}{b} \right), \quad x \in \R\]

[p25] (a) For the location family associated with \(g\), the graph of \(f\) is obtained by shifting the graph of \(g\), \(a\) units to the right if \(a \gt 0\) and \(-a\) units to the left if \(a \lt 0\).
[p26] (b) For the scale family associated with \(g\), if \(b \gt 1\), the graph of \(f\) is obtained from the graph of \(g\) by stretching horizontally and compressing vertically, by a factor of \(b\). [p27] If \(0 \lt b \lt 1\), the graph of \(f\) is obtained from the graph of \(g\) by compressing horizontally and stretching vertically, by a factor of \(b\).

Details:

[p28] First note that \( \P(X = x) = \P\left(Z = \frac{x - a}{b}\right) = 0 \), so \( X \) has a continuous distribution. [p29] Typically, \( Z \) takes values in an interval of \( \R \) and thus so does \( X \). [p30] The formula for the density function follows by taking derivatives of the distribution function in [2], since \( f = F^\prime \) and \( g = G^\prime \).

[p31] If \(Z\) has a mode at \(z\), then \(X\) has a mode at \(x = a + b z\).

Details:

[p32] This follows from density function in [3] in the discrete case or the density function in [4] in the continuous case. [p33] If \( g \) has a maximum at \( z \) then \( f \) has a maximum at \( x = a + b z \)

[p34] Next we relate the quantile functions of \(Z\) and \(X\).

[p35] If \(G\) and \(F\) are the distribution functions of \(Z\) and \(X\), respectively, then

[p36] (a) \(F^{-1}(p) = a + b \, G^{-1}(p)\) for \(p \in (0, 1)\)
[p37] (b) If \(z\) is a quantile of order \(p\) for \(Z\) then \(x = a + b \, z\) is a quantile of order \(p\) for \(X\).

Details:

[p38] These results follow from the distribution function in [2].

[p39] Suppose now that \( Z \) has a continuous distribution on \([0, \infty)\), and that we think of \(Z\) as the failure time of a device (or the time of death of an organism). [p40] Let \(X = b Z\) where \( b \in (0, \infty)\), so that the distribution of \(X\) is the scale family associated with the distribution of \(Z\). [p41] Then \(X\) also has a continuous distribution on \([0, \infty)\) and can also be thought of as the failure time of a device (perhaps in different units).

[p42] Let \(G^c\) and \(F^c\) denote the reliability functions of \(Z\) and \(X\) respectively, and let \(r\) and \(s\) denote the failure rate functions of \(Z\) and \(X\), respectively. [p43] Then

[p44] (a) \(F^c(x) = G^c(x / b)\) for \(x \in [0, \infty)\)
[p45] (b) \(s(x) = (1 / b)r(x / b)\) for \(x \in [0, \infty)\)

Details:

[p46] Recall that \( G^c = 1 - G \), \( F^c = 1 - F \), \( r = g / \bar{G} \), and \( R = f / \bar{F} \). [p47] So the results follow from the distribution function in [2] and the density function in [4].

[p48] In particular, from part (b) note that the \(X\) has the same general failure rate features (increasing, decreasing, etc.) as \(Z\).

[p49] The entropy of \(X\) and \(Z\) are related by \(H(X) = H(Z) + \ln b\).

Details:

[p50] The result follows easily from the definition of entropy as an expected value: \[ H(X) = -\E[\ln f(X)] = -\E[\ln f(b Z)] = -\E(\ln [ g(Z) / b]) = -\E[\ln g(Z) - \ln b] = H(Z) + \ln b \]

Moments

[p51] The following theorem relates the mean, variance, and standard deviation of \(Z\) and \(X\).

[p52] As before, suppose that \(X = a + b \, Z\) with \(a \in \R\) and \(b \in (0, \infty)\). [p53] Then

[p54] (a) \(\E(X) = a + b \, \E(Z)\)
[p55] (b) \(\var(X) = b^2 \, \var(Z)\)
[p56] (c) \(\sd(X) = b \, \sd(Z)\)

Details:

[p57] These result follow immediately from basic properties of expected value and variance.

[p58] Recall that the standard score of a random variable is obtained by subtracting the mean and dividing by the standard deviation. [p59] The standard score is dimensionless (that is, has no physical units) and measures the directed distance from the mean to the random variable in standard deviations. [p60] Since location-scale familes essentially correspond to a change of units, it's not surprising that the standard score is unchanged by a location-scale transformation.

[p61] The standard scores of \(X\) and \(Z\) are the same:

[p62] \[ \frac{X - \E(X)}{\sd(X)} = \frac{Z - \E(Z)}{\sd(Z)} \]

Details:

[p63] From the mean and variance in [9]:

[p64] \[ \frac{X - \E(X)}{\sd(X)} = \frac{a + b Z - [a + b \E(Z)]}{b \sd(Z)} = \frac{Z - \E(Z)}{\sd(Z)} \]

[p65] Recall that the skewness and kurtosis of a random variable are the third and fourth moments, respectively, of the standard score. [p66] Thus it follows from [10] that skewness and kurtosis are unchanged by location-scale transformations: \(\skw(X) = \skw(Z)\), \(\kur(X) = \kur(Z)\). [p67] We can represent the moments of \( X \) about 0 (sometimes called raw moments) to those of \( Z \) by means of the binomial theorem: \[ \E\left(X^n\right) = \sum_{k=0}^n \binom{n}{k} b^k a^{n - k} \E\left(Z^k\right), \quad n \in \N \] Of course, the moments of \( X \) about the location parameter \( a \) have a simple representation in terms of the moments of \( Z \) about 0: \[ \E\left[(X - a)^n\right] = b^n \E\left(Z^n\right), \quad n \in \N \] [p68] The following exercise relates the moment generating functions of \(Z\) and \(X\).

[p69] If \(Z\) has moment generating function \(m\) then \(X\) has moment generating function \(M\) given by

[p70] \[ M(t) = e^{a t} m(b t) \]

Details:

[p71] \[ M(t) = \E\left(e^{tX}\right) = \E\left[e^{t(a + bZ)}\right] = e^{ta} \E\left(e^{t b Z}\right) = e^{a t} m(b t) \]

Type

[p72] As we noted earlier, two probability distributions that are related by a location-scale transformation can be thought of as governing the same underlying random quantity, but in different physical units. [p73] This relationship is important enough to deserve a name.

[p74] Suppose that \( P \) and \( Q \) are probability distributions on \( \R \) with distribution functions \(F\) and \(G\), respectively. [p75] Then \( P \) and \( Q \) are of the same type if there exist constants \(a \in \R\) and \(b \in (0, \infty)\) such that \[ F(x) = G \left( \frac{x - a}{b} \right), \quad x \in \R \]

[p76] Being of the same type is an equivalence relation on the collection of probability distributions on \(\R\). [p77] That is, if \(P\), \(Q\), and \(R\) are probability distribution on \( \R \) then

[p78] (a) \(P\) is the same type as \(P\) (the reflexive property).
[p79] (b) If \(P\) is the same type as \(Q\) then \(Q\) is the same type as \(P\) (the symmetric property).
[p80] (c) If \(P\) is the same type as \(Q\), and \(Q\) is the same type as \(R\), then \(P\) is the same type as \(R\) (the transitive property).

Details:

[p81] Let \( F \), \( G \), and \( H \) denote the distribution functions of \( P \), \( Q \), and \( R \) respectively.

[p82] (a) This is trivial, of course, since we can take \( a = 0 \) and \( b = 1 \).
[p83] (b) Suppose there exists \( a \in \R \) and \( b \in (0, \infty) \) such that \( F(x) = G\left(\frac{x - a}{b}\right) \) for \( x \in \R \). [p84] Then \( G(x) = F(a + b x) = F\left(\frac{x - (-a/b)}{1/b}\right) \) for \( x \in \R \).
[p85] (c) Suppose there exists \( a, \, c \in \R \) and \( b, \, d \in (0, \infty) \) such that \( F(x) = G\left(\frac{x - a}{b}\right) \) and \( G(x) = H\left(\frac{x - c}{d}\right) \) for \( x \in \R \). [p86] Then \( F(x) = H\left(\frac{x - (a + bc)}{bd}\right)\) for \( x \in \R \).

[p87] So, the collection of probability distributions on \( \R \) is partitioned into mutually exclusive equivalence classes, where the distributions in each class are all of the same type.

Examples and Applications

Special Distributions

[p88] Many of the special parametric families of distributions studied in this chapter and elsewhere in this text are location and/or scale families.

[p89] The arcsine distribution is a location-scale family.

[p90] The Cauchy distribution is a location-scale family.

[p91] The exponential distribution is a scale family.

[p92] The exponential-logarithmic distribution is a scale family for each value of the shape parameter.

[p93] The extreme value distribution is a location-scale family.

[p94] The gamma distribution is a scale family for each value of the shape parameter.

[p95] The Gompertz distribution is a scale family for each value of the shape parameter.

[p96] The half-normal distribution is a scale family.

[p97] The hyperbolic secant distribution is a location-scale family.

[p98] The Lévy distribution is a location scale family.

[p99] The logistic distribution is a location-scale family.

[p100] The log-logistic distribution is a scale family for each value of the shape parameter.

[p101] The Maxwell distribution is a scale family.

[p102] The normal distribution is a location-scale family.

[p103] The Pareto distribution is a scale family for each value of the shape parameter.

[p104] The Rayleigh distribution is a scale family.

[p105] The semicircle distribution is a location-scale family.

[p106] The triangle distribution is a location-scale family for each value of the shape parameter.

[p107] The uniform distribution on an interval is a location-scale family.

[p108] The U-power distribution is a location-scale family for each value of the shape parameter.

[p109] The Weibull distribution is a scale family for each value of the shape parameter.

[p110] The Wald distribution is a scale family, although in the usual formulation, neither of the parameters is a scale parameter.
