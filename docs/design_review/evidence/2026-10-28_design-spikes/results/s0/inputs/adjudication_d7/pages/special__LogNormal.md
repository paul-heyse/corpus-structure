# special/LogNormal.html (canonical text; [pN] numbers page sentences for reference only)

The Lognormal Distribution

Basic Theory

Definition


<<< UNIT T4 part 1 begins >>>
[p1] Suppose that \(Y\) has the normal distribution with mean \(\mu \in \R\) and standard deviation \(\sigma \in (0, \infty)\). [p2] Then \(X = e^Y\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\).

[p3] (a) The parameter \( \sigma \) is the shape parameter of the distribution.
[p4] (b) The parameter \( e^\mu\) is the scale parameter of the distribution.

[p5] If \(Z\) has the standard normal distribution then \(W = e^Z\) has the standard lognormal distribution.
<<< UNIT T4 part 1 ends >>>


[p6] So equivalently, if \(X\) has a lognormal distribution then \(\ln X\) has a normal distribution, hence the name. [p7] The lognormal distribution is a continuous distribution on \((0, \infty)\) and is used to model random quantities when the distribution is believed to be skewed, such as certain income and lifetime variables.

Distribution Functions

[p8] Suppose that \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\).

[p9] The probability density function \(f\) of \(X\) is given by \[ f(x) = \frac{1}{\sqrt{2 \pi} \sigma x} \exp \left[-\frac{\left(\ln x - \mu\right)^2}{2  \sigma^2} \right], \quad x \in (0, \infty) \]

[p10] (a) \( f \) increases and then decreases with mode at \( x = \exp\left(\mu - \sigma^2\right) \).
[p11] (b) \( f \) is concave upward then downward then upward again, with inflection points at \( x = \exp\left(\mu - \frac{3}{2} \sigma^2 \pm \frac{1}{2} \sigma \sqrt{\sigma^2 + 4}\right) \)
[p12] (c) \( f(x) \to 0 \) as \( x \downarrow 0 \) and as \( x \to \infty \).

Details:

[p13] The form of the PDF follows from the change of variables theorem. [p14] Let \( g \) denote the PDF of the normal distribution with mean \( \mu \) and standard deviation \( \sigma \), so that \[ g(y) = \frac{1}{\sqrt{2 \pi} \sigma} \exp\left[-\frac{1}{2}\left(\frac{y - \mu}{\sigma}\right)^2\right], \quad y \in \R \] [p15] The mapping \( x = e^y \) maps \( \R \) one-to-one onto \( (0, \infty) \) with inverse \( y = \ln x \). [p16] Hence the PDF \( f \) of \( X = e^Y \) is \[ f(x) = g(y) \frac{dy}{dx} = g\left(\ln x\right) \frac{1}{x} \] [p17] Substituting gives the result. [p18] Parts (a)–(d) follow from standard calculus.

[p19] In the special distribution simulator, select the lognormal distribution. [p20] Vary the parameters and note the shape and location of the probability density function. [p21] For selected values of the parameters, run the simulation 1000 times and compare the empirical density function to the true probability density function.

[p22] Let \(\Phi\) denote the standard normal distribution function, so that \(\Phi^{-1}\) is the standard normal quantile function. [p23] Recall that values of \(\Phi\) and \(\Phi^{-1}\) can be obtained from standard mathematical and statistical software packages, and in fact these functions are considered to be special functions in mathematics. [p24] The following two results show how to compute the lognormal distribution function and quantiles in terms of the standard normal distribution function and quantiles.

[p25] The distribution function \(F\) of \(X\) is given by \[ F(x) = \Phi \left( \frac{\ln x - \mu}{\sigma} \right), \quad x \in (0, \infty) \]

Details:

[p26] Once again, write \( X = e^{\mu + \sigma Z} \) where \( Z \) has the standard normal distribution. [p27] For \( x \gt 0 \), \[ F(x) = \P(X \le x) = \P\left(Z \le \frac{\ln x - \mu}{\sigma}\right) = \Phi \left( \frac{\ln x - \mu}{\sigma} \right) \]

[p28] The quantile function of \(X\) is given by \[ F^{-1}(p) = \exp\left[\mu + \sigma \Phi^{-1}(p)\right], \quad p \in (0, 1) \]

Details:

[p29] This follows by solving \( p = F(x) \) for \( x \) in terms of \( p \).

[p30] In the quantile app, select the lognormal distribution. [p31] Vary the parameters and note the shape and location of the probability density function and the distribution function. [p32] With \(\mu = 0\) and \(\sigma = 1\), find the median and the first and third quartiles.

Moments

[p33] The moments of the lognormal distribution can be computed from the moment generating function of the normal distribution. [p34] Once again, we assume that \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\).

[p35] For \( t \in \R \), \[ \E\left(X^t\right) = \exp \left( \mu t + \frac{1}{2} \sigma^2 t^2 \right) \]

Details:

[p36] Recall that if \( Y \) has the normal distribution with mean \( \mu \in \R \) and standard deviation \( \sigma \in (0, \infty) \), then \( Y \) has moment generating function given by \[ \E\left(e^{t Y}\right) = \exp\left(\mu t + \frac{1}{2} \sigma^2 t^2\right), \quad t \in \R \] [p37] Hence the result follows immediately since \( \E\left(X^t\right) = \E\left(e^{t Y}\right) \).

[p38] In particular, the mean and variance of \(X\) are

[p39] (a) \(\E(X) = \exp\left(\mu + \frac{1}{2} \sigma^2\right)\)
[p40] (b) \(\var(X) = \exp\left[2 (\mu + \sigma^2)\right] - \exp\left(2 \mu + \sigma^2\right)\)

[p41] In the simulation of the special distribution simulator, select the lognormal distribution. [p42] Vary the parameters and note the shape and location of the mean\( \pm \)standard deviation bar. [p43] For selected values of the parameters, run the simulation 1000 times and compare the empirical moments to the true moments.

[p44] From the general formula for the moments, we can also compute the skewness and kurtosis of the lognormal distribution.

[p45] The skewness and kurtosis of \(X\) are

[p46] (a) \( \skw(X) = \left(e^{\sigma^2} + 2\right) \sqrt{e^{\sigma^2} - 1} \)
[p47] (b) \(\kur(X) = e^{4 \sigma^2} + 2 e^{3 \sigma^2} + 3 e^{2 \sigma^2} - 3\)

Details:

[p48] These result follow from the first four moments of the lognormal distribution in [7] and the standard computational formulas for skewness and kurtosis.

[p49] The fact that the skewness and kurtosis do not depend on \( \mu \) is due to the fact that \( \mu \) is a scale parameter. [p50] Recall that skewness and kurtosis are defined in terms of the standard score and so are independent of location and scale parameters. [p51] Naturally, the lognormal distribution is positively skewed. [p52] Finally, note that the excess kurtosis is \[ \kur(X) - 3 = e^{4 \sigma^2} + 2 e^{3 \sigma^2} + 3 e^{2 \sigma^2} - 6 \]

[p53] Even though the lognormal distribution has finite moments of all orders, the moment generating function is infinite at any positive number. [p54] This property is one of the reasons for the fame of the lognormal distribution.

[p55] \(\E\left(e^{t X}\right) = \infty\) for every \(t \gt 0\).

Details:

[p56] By definition, \(X = e^Y\) where \(Y\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\). [p57] Using the change of variables formula for expected value we have \[\E\left(e^{t X}\right) = \E\left(e^{t e^Y}\right) = \int_{-\infty}^\infty \exp(t e^y) \frac{1}{\sqrt{2 \pi} \sigma} \exp\left[-\frac{1}{2}\left(\frac{y - \mu}{\sigma}\right)^2\right] dy = \frac{1}{\sqrt{2 \pi} \sigma} \int_{-\infty}^\infty \exp\left[t e^y - \frac{1}{2} \left(\frac{y - \mu}{\sigma}\right)^2\right] dy\] If \(t \gt 0\) the integrand in the last integral diverges to \(\infty\) as \(y \to \infty\), so there is no hope that the integral converges.

Related Distributions

[p58] The most important relations are the ones between the lognormal and normal distributions in the definition: if \(X\) has a lognormal distribution then \(\ln X\) has a normal distribution; conversely if \(Y\) has a normal distribution then \(e^Y\) has a lognormal distribution. [p59] It's easy to write a general lognormal variable in terms of a standard lognormal variable.

[p60] Suppose that \(W\) has the standard lognormal distribution and that \(\mu \in \R\) and \(\sigma \in (0, \infty)\). [p61] Then \(X = e^\mu W^\sigma\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\).

Details:

[p62] Suppose that \(Z\) has the standard normal distribution and let \(W = e^Z\) so that \(W\) has the standard lognormal distribution. [p63] If \(\mu \in \R\) and \(\sigma \in (0, \infty)\) then \(Y = \mu + \sigma Z\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\) and hence \(X = e^Y\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\). [p64] But \[X = e^Y = e^{\mu + \sigma Z} = e^\mu \left(e^Z\right)^\sigma = e^\mu W^\sigma\]

[p65] As noted earlier, the lognormal distribution is also a scale family.

[p66] Suppose that \( X \) has the lognormal distribution with parameters \( \mu \in \R \) and \( \sigma \in (0, \infty) \) and that \( c \in (0, \infty) \). [p67] Then \( c X \) has the lognormal distribution with parameters \( \mu + \ln c\) and \( \sigma \).

Details:

[p68] From definition [1], we can write \( X = e^Y \) where \( Y \) has the normal distribution with mean \( \mu \) and standard deviation \( \sigma \). [p69] Hence \[ c X = c e^Y = e^{\ln c} e^Y = e^{\ln c + Y} \] [p70] But \( \ln c + Y \) has the normal distribution with mean \( \ln c + \mu \) and standard deviation \( \sigma \).

[p71] The reciprocal of a lognormal variable is also lognormal.

[p72] If \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\) then \(1 / X\) has the lognormal distribution with parameters \(-\mu\) and \(\sigma\).

Details:

[p73] Again from definition [1], we can write \( X = e^Y \) where \(Y\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\). [p74] Hence \(1 / X = e^{-Y}\). [p75] But \(-Y\) has the normal distribution with mean \(-\mu\) and standard deviation \(\sigma\).

[p76] The lognormal distribution is closed under non-zero powers of the underlying variable. [p77] In particular, this generalizes [14].

[p78] Suppose that \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\) and that \(a \in \R \setminus \{0\}\). [p79] Then \(X^a\) has the lognormal distribution with parameters with parameters \(a \mu\) and \(|a| \sigma\).

Details:

[p80] Again from definition [1], we can write \( X = e^Y \) where \(Y\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\). [p81] Hence \(X^a = e^{a Y}\). [p82] But \(a Y\) has the normal distribution with mean \(a \mu\) and standard deviation \(|a| \sigma\).

[p83] Since the normal distribution is closed under sums of independent variables, it's not surprising that the lognormal distribution is closed under products of independent variables.


<<< UNIT U9 part 1 begins >>>
[p84] Suppose that \(n \in \N_+\) and that \((X_1, X_2, \ldots, X_n)\) is a sequence of independent variables, where \(X_i\) has the lognormal distribution with parameters \(\mu_i \in \R\) and \(\sigma_i \in (0, \infty)\) for \(i \in \{1, 2, \ldots, n\}\). [p85] Then \(\prod_{i=1}^n X_i\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\) where \(\mu = \sum_{i=1}^n \mu_i\) and \(\sigma^2 = \sum_{i=1}^n \sigma_i^2\).

Details:

[p86] Again from definition [1], we can write \( X_i = e^{Y_i} \) where \(Y_i\) has the normal distribution with mean \(\mu_i\) and standard deviation \(\sigma_i\) for \(i \in \{1, 2, \ldots, n\}\) and where \((Y_1, Y_2, \ldots, Y_n)\) is an independent sequence. [p87] Hence \(\prod_{i=1}^n X_i = \exp\left(\sum_{i=1}^n Y_i\right)\). [p88] But \(\sum_{i=1}^n Y_i\) has the normal distribution with mean \(\sum_{i=1}^n \mu_i\) and variance \(\sum_{i=1}^n \sigma_i^2\).
<<< UNIT U9 part 1 ends >>>


[p89] Finally, the lognormal distribution belongs to the family of general exponential distributions.

[p90] Suppose that \( X \) has the lognormal distribution with parameters \( \mu \in \R \) and \( \sigma \in (0, \infty) \). [p91] The distribution of \( X \) is a 2-parameter exponential family with natural parameters and natural statistics, respectively, given by

[p92] (a) \(\left( -1 / 2 \sigma^2, \mu / \sigma^2 \right)\)
[p93] (b) \(\left(\ln^2(X), \ln X\right)\)

Details:

[p94] This follows from the definition of the general exponential family, since we can write the lognormal PDF in [2] in the form \[ f(x) = \frac{1}{\sqrt{2 \pi} \sigma} \exp\left(-\frac{\mu^2}{2 \sigma^2}\right) \frac{1}{x} \exp\left[-\frac{1}{2 \sigma^2} \ln^2(x) + \frac{\mu}{\sigma^2} \ln x\right], \quad x \in (0, \infty) \]

Computational Exercises

[p95] Suppose that the income \(X\) of a randomly chosen person in a certain population (in $1000 units) has the lognormal distribution with parameters \(\mu = 2\) and \(\sigma = 1\). [p96] Find \(\P(X \gt 20)\).

Details:

[p97] \(\P(X \gt 20) = 0.1597\)

[p98] Suppose that the income \(X\) of a randomly chosen person in a certain population (in $1000 units) has the lognormal distribution with parameters \(\mu = 2\) and \(\sigma = 1\). [p99] Find each of the following:

[p100] (a) \(\E(X)\)
[p101] (b) \(\var(X)\)

Details:

[p102] (a) \(\E(X) = e^{5/2} \approx 12.1825\)
[p103] (b) \(\sd(X) = \sqrt{e^6 - e^5} \approx 15.9629\)
