# special/Normal.html (canonical text; [pN] numbers page sentences for reference only)

The Normal Distribution

[p1] The normal distribution holds an honored role in probability and statistics, mostly because of the central limit theorem, one of the fundamental theorems that forms a bridge between the two subjects. [p2] In addition, as we will see, the normal distribution has many nice mathematical properties. [p3] The normal distribution is also called the Gaussian distribution, in honor of Carl Friedrich Gauss, who was among the first to use the distribution.

The Standard Normal Distribution

Distribution Functions

[p4] The standard normal distribution is a continuous distribution on \( \R \) with probability density function \(\phi\) given by \[ \phi(z) = \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2}, \quad z \in \R \]

Details:

[p5] Let \(c = \int_{-\infty}^{\infty} e^{-z^2 / 2} dz\). [p6] We need to show that \( c = \sqrt{2 \pi} \). [p7] That is, \(\sqrt{2 \pi}\) is the normalzing constant for the function \(z \mapsto e^{-z^2 / 2}\). [p8] The proof uses a nice trick: \[ c^2 = \int_{-\infty}^\infty e^{-x^2 / 2} \, dx \int_{-\infty}^\infty e^{-y^2 / 2} \, dy = \int_{\R^2} e^{-(x^2 + y^2) / 2} \, d(x, y)\] [p9] We now convert the double integral to polar coordinates: \( x = r \cos \theta \), \( y = r \sin \theta \) where \( r \in [0, \infty) \) and \( \theta \in [0, 2 \pi) \). [p10] So, \( x^2 + y^2 = r^2 \) and \( d(x, y) = r \, d(r, \theta) \). [p11] Thus, converting back to iterated integrals, \[ c^2 = \int_0^{2 \pi} \int_0^\infty r e^{-r^2 / 2} \, dr \, d\theta \] Substituting \( u = r^2 / 2 \) in the inner integral gives \( \int_0^\infty e^{-u} \, du = 1 \) and then the outer integral is \( \int_0^{2 \pi} 1 \, d\theta = 2 \pi \). [p12] Thus, \( c^2 = 2 \pi \) and so \( c = \sqrt{2 \pi} \).

[p13] The standard normal probability density function has the famous “bell shape” that is known to just about everyone.

[p14] The standard normal density function \(\phi\) satisfies the following properties:

[p15] (a) \(\phi\) is symmetric about \(z = 0\).
[p16] (b) \(\phi\) increases and then decreases, with mode \( z = 0 \).
[p17] (c) \(\phi\) is concave upward and then downward and then upward again, with inflection points at \(z = \pm 1\).
[p18] (d) \(\phi(z) \to 0\) as \(z \to \infty\) and as \(z \to -\infty\).

Details:

[p19] These results follow from standard calculus. [p20] Note that \(\phi^\prime(z) = - z \phi(z)\) (which gives (b)) and hence also \( \phi^{\prime \prime}(z) = (z^2 - 1) \phi(z) \) (which gives (c)).

[p21] In the Special Distribution Simulator, select the normal distribution and keep the default settings. [p22] Note the shape and location of the standard normal density function. [p23] Run the simulation 1000 times, and compare the empirical density function to the probability density function.

[p24] The standard normal distribution function \(\Phi\), given by \[ \Phi(z) = \int_{-\infty}^z \phi(t) \, dt = \int_{-\infty}^z \frac{1}{\sqrt{2 \pi}} e^{-t^2 / 2} \, dt \] and its inverse, the quantile function \(\Phi^{-1}\), cannot be expressed in closed form in terms of elementary functions. [p25] However approximate values of these functions can be obtained from the quantile app, and from most mathematics and statistics software. [p26] Indeed these functions are so important that they are considered special functions of mathematics.

[p27] The standard normal distribution function \(\Phi\) satisfies the following properties:

[p28] (a) \(\Phi(-z) = 1 - \Phi(z)\) for \(z \in \R\)
[p29] (b) \(\Phi^{-1}(p) = -\Phi^{-1}(1 - p)\) for \(p \in (0, 1)\)
[p30] (c) \(\Phi(0) = \frac{1}{2}\), so the median is 0.

Details:

[p31] Part (a) follows from the symmetry of \( \phi \). [p32] Part (b) follows from part (a). [p33] Part (c) follows from part (a) with \( z = 0 \).

[p34] In the quantile app, select the normal distribution and keep the default settings.

[p35] (a) Note the shape of the density function and the distribution function.
[p36] (b) Find the first and third quartiles.
[p37] (c) Compute the interquartile range.

[p38] In the quantile app, select the normal distribution and keep the default settings. [p39] Find the quantiles of the following orders for the standard normal distribution:

[p40] (a) \(q = 0.005\), \(q = 0.995\)
[p41] (b) \(q = 0.05\), \(q = 0.95\)
[p42] (c) \(q = 0.1\), \(q = 0.9\)

Moments

[p43] Suppose that random variable \( Z \) has the standard normal distribution.

[p44] The mean and variance of \( Z \) are

[p45] (a) \( \E(Z) = 0 \)
[p46] (b) \( \var(Z) = 1 \)

Details:

[p47] (a) Of course, by symmetry, if \( Z \) has a mean, the mean must be 0, but we have to argue that the mean exists. [p48] Actually it's not hard to compute the mean directly. [p49] Note that \[ \E(Z) = \int_{-\infty}^\infty z \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2} \, dz  = \int_{-\infty}^0 z \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2} \, dz  + \int_0^\infty z \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2} \, dz \] [p50] The integrals on the right can be evaluated explicitly using the simple substitution \( u = z^2 / 2 \). [p51] The result is \( \E(Z) = -1/\sqrt{2 \pi} + 1/\sqrt{2 \pi} = 0 \).
[p52] (b) By part (a), note that \[ \var(Z) = \E(Z^2) = \int_{-\infty}^\infty z^2 \phi(z) \, dz \] Integrate by parts, using the parts \( u = z \) and \( dv = z \phi(z) \, dz \). [p53] Thus \( du = dz \) and \( v = -\phi(z) \). Note that \( z \phi(z) \to 0 \) as \( z \to \infty \) and as \( z \to -\infty \). [p54] Thus, the integration by parts formula gives \( \var(Z) = \int_{-\infty}^\infty \phi(z) \, dz = 1 \).
[p55] (c)

[p56] In the Special Distribution Simulator, select the normal distribution and keep the default settings. [p57] Note the shape and size of the mean \( \pm \) standard deviation bar.. [p58] Run the simulation 1000 times, and compare the empirical mean and standard deviation to the true mean and standard deviation.

[p59] More generally, we can compute all of the moments. [p60] The key is the following recursion formula.

[p61] For \( n \in \N_+ \), \( \E\left(Z^{n+1}\right) = n \E\left(Z^{n-1}\right) \)

Details:

[p62] First we use the differential equation in the proof of [2] above, namely \( \phi^\prime(z) = - z \phi(z) \). \[ \E\left(Z^{n+1}\right) = \int_{-\infty}^\infty z^{n+1} \phi(z) \, dz = \int_{-\infty}^\infty z^n z \phi(z) \, dz = - \int_{-\infty}^\infty z^n \phi^\prime(z) \, dz \] [p63] Now we integrate by parts, with \( u = z^n \) and \( dv = \phi^\prime(z) \, dz \) to get \[ \E\left(Z^{n+1}\right) = -z^n \phi(z) \bigg|_{-\infty}^\infty + \int_{-\infty}^\infty n z^{n-1} \phi(z) \, dz = 0 + n \E\left(Z^{n-1}\right) \]

[p64] The moments of the standard normal distribution are now easy to compute.

[p65] For \(n \in \N\),

[p66] (a) \(\E \left( Z^{2 n + 1} \right) = 0\)
[p67] (b) \(\E \left( Z^{2 n} \right) = 1 \cdot 3 \cdots (2n - 1) = (2  n)! \big/ (n! 2^n) \)

Details:

[p68] The result follows from the mean and variance in [7] and recursion relation in [9].

[p69] (a) Since \( \E(Z) = 0 \) it follows that \( \E\left(Z^n\right) = 0 \) for every odd \( n \in \N \).
[p70] (b) Since \( \E\left(Z^2\right) = 1 \), it follows that \( \E\left(Z^4\right) = 1 \cdot 3 \) and then \( \E\left(Z^6\right) = 1 \cdot 3 \cdot 5  \), and so forth. [p71] You can use induction, if you like, for a more formal proof.

[p72] Of course, the fact that the odd-order moments are 0 also follows from the symmetry of the distribution. [p73] The following theorem gives the skewness and kurtosis of the standard normal distribution.

[p74] The skewness and kurtosis of \( Z \) are

[p75] (a) \(\skw(Z) = 0\)
[p76] (b) \(\kur(Z) = 3\)

Details:

[p77] (a) This follows immediately from the symmetry of the distribution. [p78] Directly, since \( Z \) has mean 0 and variance 1, \( \skw(Z) = \E\left(Z^3\right) = 0 \).
[p79] (b) Since \( \E(Z) = 0 \) and \( \var(Z) = 1 \), \( \kur(Z) = \E\left(Z^4\right) = 3\).

[p80] Because of the last result, (and the use of the standard normal distribution literally as a standard), the excess kurtosis of a random variable is defined to be the ordinary kurtosis minus 3. [p81] Thus, the excess kurtosis of the normal distribution is 0.

[p82] Many other important properties of the normal distribution are most easily obtained using the moment generating function or the characteristic function.

[p83] The moment generating function \( m \) and characteristic function \( \chi \) of \( Z \) are given by

[p84] (a) \(m(t) =  e^{t^2 / 2}\) for \( t \in \R\).
[p85] (b) \(\chi(t) = e^{-t^2 / 2}\) for \( t \in \R \).

Details:

[p86] (a) Note that \[ m(t) = \E(e^{t Z}) = \int_{-\infty}^\infty e^{t z} \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2} \, dz = \int_{-\infty}^\infty \frac{1}{2 \pi} \exp\left(-\frac{1}{2} z^2 + t z\right) \, dz \] [p87] We complete the square in \( z \) to get \( -\frac{1}{2} z^2 + t z = -\frac{1}{2}(z - t)^2 + \frac{1}{2} \). [p88] Thus we have \[ \E(e^{t Z}) = e^{\frac{1}{2} t^2} \int_{-\infty}^\infty \frac{1}{\sqrt{2 \pi}} \exp\left[-\frac{1}{2}(z - t)^2\right] \, dz \] [p89] In the integral, if we use the simple substitution \(u = z - t\) then the integral becomes \(\int_{-\infty}^\infty \phi(u) \, du = 1\). [p90] Hence \( \E\left(e^{t Z}\right) = e^{\frac{1}{2} t^2} \),
[p91] (b) This follows from (a) since \(\chi(t) = m(i t)\).

[p92] Thus, the standard normal distribution has the curious property that the characteristic function is a multiple of the probability density function: \[ \chi = \sqrt{2 \pi} \phi \] [p93] The moment generating function can be used to give another derivation of the moments of \( Z \), since we know that \( \E\left(Z^n\right) = m^{(n)}(0) \).

The General Normal Distribution

[p94] The general normal distribution is the location-scale family associated with the standard normal distribution.

[p95] Suppose that \(\mu \in \R\) and \( \sigma \in (0, \infty) \) and that \(Z\) has the standard normal distribution. [p96] Then \(X = \mu + \sigma Z\) has the normal distribution with location parameter \(\mu\) and scale parameter \(\sigma\).

Distribution Functions

[p97] Suppose that \( X \) has the normal distribution with location parameter \( \mu \in \R \) and scale parameter \( \sigma \in (0, \infty) \). [p98] The basic properties of the density function and distribution function of \( X \) follow from general results for location scale families.

[p99] The probability density function \(f\) of \( X \) is given by \[ f(x) = \frac{1}{\sigma} \phi\left(\frac{x - \mu}{\sigma}\right) = \frac{1}{\sqrt{2 \, \pi} \, \sigma} \exp \left[ -\frac{1}{2} \left( \frac{x - \mu}{\sigma} \right)^2 \right], \quad x \in \R \]

Details:

[p100] This follows from the change of variables formula corresponding to the transformation \( x = \mu + \sigma z \).

[p101] The probability density function \(f\) satisfies the following properties:

[p102] (a) \(f\) is symmetric about \(x = \mu\).
[p103] (b) \(f\) increases and then decreases with mode \( x = \mu \).
[p104] (c) \(f\) is concave upward then downward then upward again, with inflection points at \( x = \mu \pm \sigma \).
[p105] (d) \(f(x) \to 0\) as \(x \to \infty\) and as \(x \to -\infty\).

Details:

[p106] These properties follow from the corresponding properties of \( \phi \) in [2].

[p107] In the special distribution simulator, select the normal distribution. [p108] Vary the parameters and note the shape and location of the probability density function. [p109] With your choice of parameter settings, run the simulation 1000 times and compare the empirical density function to the true probability density function.

[p110] Let \(F\) denote the distribution function of \( X \), and as above, let \(\Phi\) denote the standard normal distribution function.

[p111] The distribution function \(F\) and quantile function \( F^{-1} \) satsify the following properties:

[p112] (a) \(F(x) = \Phi \left( \frac{x - \mu}{\sigma} \right)\) for \(x \in \R\).
[p113] (b) \(F^{-1}(p) = \mu + \sigma \, \Phi^{-1}(p)\) for \(p \in (0, 1)\).
[p114] (c) \(F(\mu) = \frac{1}{2}\) so the median occurs at \(x = \mu\).

Details:

[p115] Part (a) follows since \( X = \mu + \sigma Z \). [p116] Parts (b) and (c) follow from (a).

[p117] In the quantile app, select the normal distribution. [p118] Vary the parameters and note the shape of the density function and the distribution function.

Moments


<<< UNIT T2 part 1 begins >>>
[p119] Suppose again that \( X \) has the normal distribution with location parameter \( \mu \in \R \) and scale parameter \( \sigma \in (0, \infty) \). [p120] As the notation suggests, the location and scale parameters are also the mean and standard deviation, respectively.
<<< UNIT T2 part 1 ends >>>


[p121] The mean and variance of \( X \) are

[p122] (a) \(\E(X) = \mu\)
[p123] (b) \(\var(X) = \sigma^2\)

Details:

[p124] This follows from the representation \( X = \mu + \sigma Z \) and basic properties of expected value and variance.

[p125] So the parameters of the normal distribution are usually referred to as the mean and standard deviation rather than location and scale. [p126] The central moments of \(X\) can be computed easily from the moments of the standard normal distribution. [p127] The ordinary (raw) moments of \(X\) can be computed from the central moments, but the formulas are a bit messy.

[p128] For \(n \in \N\),

[p129] (a) \(\E \left[ (X - \mu)^{2 n} \right] = 1 \cdot 3 \cdots (2n - 1) \sigma^{2n} = (2 n)! \sigma^{2n} \big/ (n! 2^n)\)
[p130] (b) \(\E \left[ (X - \mu)^{2 \, n + 1} \right] = 0\)

[p131] All of the odd central moments of \(X\) are 0, a fact that also follows from the symmetry of the probability density function.

[p132] In the special distribution simulator select the normal distribution. [p133] Vary the mean and standard deviation and note the size and location of the mean \(\pm\) standard deviation bar. [p134] With your choice of parameter settings, run the simulation 1000 times and compare the empirical mean and standard deviation to the true mean and standard deviation.

[p135] The following result gives the skewness and kurtosis.

[p136] The skewness and kurtosis of \( X \) are

[p137] (a) \(\skw(X) = 0\)
[p138] (b) \(\kur(X) = 3\)

Details:

[p139] The skewness and kurtosis of a variable are defined in terms of the standard score, so these results follows from the corresponding result for \( Z \) in [11].

[p140] The moment generating function \( M \) and characteristic function \( \chi \) of \( X \) are given by

[p141] (a) \(M(t) = \exp \left( \mu t + \frac{1}{2} \sigma^2 t^2 \right)\) for \(t \in \R \).
[p142] (b) \( \chi(t) =\exp \left( i \mu t - \frac{1}{2} \sigma^2 t^2 \right)\) for \(t \in \R \)

Details:

[p143] (a) This follows from the representation \( X = \mu + \sigma Z \), basic properties of expected value, and the MGF of \( Z \) in [12]: \[ \E\left(e^{t X}\right) = \E\left(e^{t \mu + t \sigma Z}\right) = e^{t \mu} \E\left(e^{t \sigma Z}\right) = e^{t \mu} e^{\frac{1}{2} t^2 \sigma^2} = e^{t \mu + \frac{1}{2} \sigma^2 t^2}  \]
[p144] (b) This follows from (a) since \( \chi(t) = M(i t) \).

Related Distributions

[p145] The normal family of distributions satisfies two very important properties: invariance under linear transformations of the variable and invariance with respect to sums of independent variables. [p146] The first property is essentially a restatement of the fact that the normal distribution is a location-scale family.


<<< UNIT T3 part 1 begins >>>
[p147] Suppose that \(X\) is normally distributed with mean \(\mu\) and variance \(\sigma^2\). [p148] If \(a \in \R\) and \(b \in \R \setminus \{0\}\), then \(a + b X\) is normally distributed with mean \(a + b \mu\) and variance \(b^2 \sigma^2\).

Details:

[p149] The MGF of \(a + b X\) is \[ \E\left[e^{t (a + b X)}\right] = e^{ta} \E\left[e^{(t b) X}\right] = e^{ta} e^{\mu (t b) + \sigma^2 (t b)^2 / 2} = e^{(a + b \mu)t + b^2 \sigma^2 t^2 / 2} \] which we recognize as the MGF of the normal distribution with mean \(a + b \mu\) and variance \(b^2 \sigma^2\).
<<< UNIT T3 part 1 ends >>>



<<< UNIT U6 part 1 begins >>>
[p150] Recall that in general, if \(X\) is a random variable with mean \(\mu\) and standard deviation \(\sigma \gt 0\), then \(Z = (X - \mu) / \sigma\) is the standard score of \(X\). [p151] A corollary of the last result is that if \(X\) has a normal distribution then the standard score \(Z\) has a standard normal distribution. [p152] Conversely, any normally distributed variable can be constructed from a standard normal variable.
<<< UNIT U6 part 1 ends >>>


[p153] Standard score.

[p154] (a) If \(X\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\) then \(Z = \frac{X - \mu}{\sigma}\) has the standard normal distribution.
[p155] (b) If \(Z\) has the standard normal distribution and if \(\mu \in \R\) and \(\sigma \in (0, \infty)\), then \(X = \mu + \sigma Z\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\).


<<< UNIT U5 part 1 begins >>>
[p156] Suppose that \(X_1\) and \(X_2\) are independent random variables, and that \(X_i\) is normally distributed with mean \(\mu_i\) and variance \(\sigma_i^2\) for \(i \in \{1, 2\}\). [p157] Then \(X_1 + X_2\) is normally distributed with

[p158] (a) \(\E(X_1 + X_2) = \mu_1 + \mu_2\)
[p159] (b) \(\var(X_1 + X_2) = \sigma_1^2 + \sigma_2^2\)

Details:

[p160] The MGF of \(X_1 + X_2\) is the product of the MGFs, so \[ \E\left(\exp\left[t (X_1 + X_2)\right]\right) = \exp\left(\mu_1 t + \sigma_1^2 t^2 / 2\right) \exp\left(\mu_2 t + \sigma_2^2 t^2 / 2\right) = \exp\left[\left(\mu_1 + \mu_2\right)t + \left(\sigma_1^2 + \sigma_2^2\right) t^2 / 2\right] \] which we recognize as the MGF of the normal distribution with mean \(\mu_1 + \mu_2\) and variance \(\sigma_1^2 + \sigma_2^2\).
<<< UNIT U5 part 1 ends >>>


[p161] Theorem [26] generalizes to a sum of \(n\) independent, normal variables. [p162] The important part is that the sum is still normal; the expressions for the mean and variance are standard results that hold for the sum of independent variables generally. [p163] As a consequence of this result and the one for linear transformations [24], it follows that the normal distribution is stable.

[p164] The normal distribution is stable. [p165] Specifically, suppose that \( X \) has the normal distribution with mean \( \mu \in \R \) and variance \( \sigma^2 \in (0, \infty)\). [p166] If \( (X_1, X_2, \ldots, X_n) \) are independent copies of \( X \), then \( X_1 + X_2 + \cdots + X_n \) has the same distribution as \( \left(n - \sqrt{n}\right) \mu + \sqrt{n} X \), namely normal with mean \( n \mu \) and variance \( n \sigma^2 \).

Details:

[p167] By [26] \( X_1 + X_2 + \cdots + X_n \) has the normal distribution with mean \( n \mu \) and variance \( n \sigma^2 \). [p168] By [24], \( \left(n - \sqrt{n}\right) \mu + \sqrt{n} X \) has the normal distribution with mean \( \left(n - \sqrt{n}\right) \mu + \sqrt{n} \mu = n \mu \) and variance \( \left(\sqrt{n}\right)^2 \sigma^2 = n \sigma^2 \).

[p169] All stable distributions are infinitely divisible, so the normal distribution belongs to this family as well. [p170] For completeness, here is the explicit statement:

[p171] The normal distribution is infinitely divisible. [p172] Specifically, if \( X \) has the normal distribution with mean \( \mu \in \R \) and variance \( \sigma^2 \in (0, \infty) \), then for \( n \in \N_+ \), \( X \) has the same distribution as \( X_1 + X_2 + \cdots + X_n\) where \( (X_1, X_2, \ldots, X_n) \) are independent, and each has the normal distribution with mean \( \mu / n \) and variance \( \sigma^2 / n \).

[p173] Finally, the normal distribution belongs to the family of general exponential distributions.

[p174] The normal distribution with mean \(\mu\) and variance \(\sigma^2\) is a two-parameter exponential family with natural parameters \(\left( \frac{\mu}{\sigma^2}, -\frac{1}{2 \, \sigma^2} \right)\), and natural statistics \(\left(X, X^2\right)\).

Details:

[p175] Expanding the square, the normal PDF can be written in the form \[ f(x) = \frac{1}{\sqrt{2 \pi} \sigma} \exp\left(-\frac{\mu^2}{2 \sigma^2}\right) \exp\left(\frac{\mu}{\sigma^2} x - \frac{1}{2 \sigma^2} x^2 \right), \quad x \in \R\] so the result follows from the definition of the general exponential family.

[p176] A number of other special distributions studied in this chapter are constructed from normally distributed variables. [p177] These include

[p178] The lognormal distribution
[p179] The folded normal distribution, which includes the half normal distribution as a special case
[p180] The Rayleigh distribution
[p181] The Maxwell distribution
[p182] The Lévy distribution

[p183] Also, as mentioned at the beginning of this section, the importance of the normal distribution stems in large part from the central limit theorem, one of the fundamental theorems of probability. [p184] By virtue of this theorem, the normal distribution is connected to many other distributions, by means of limits and approximations, including the special distributions in the following list. [p185] Details are given in the individual sections.

[p186] The binomial distribution
[p187] The negative binomial distribution
[p188] The Poisson distribution
[p189] The gamma distribution
[p190] The chi-square distribution
[p191] The student \( t \) distribution
[p192] The Irwin-Hall distribution

Computational Exercises

[p193] Suppose that the volume of beer in a bottle of a certain brand is normally distributed with mean 0.5 liter and standard deviation 0.01 liter.

[p194] (a) Find the probability that a bottle will contain at least 0.48 liter.
[p195] (b) Find the volume that corresponds to the 95th percentile

Details:

[p196] Let \(X\) denote the volume of beer in liters

[p197] (a) \(\P(X \gt 0.48) = 0.9772\)
[p198] (b) \(x_{0.95} = 0.51645\)


<<< UNIT U8 part 1 begins >>>
[p199] A metal rod is designed to fit into a circular hole on a certain assembly. [p200] The radius of the rod is normally distributed with mean 1 cm and standard deviation 0.002 cm. [p201] The radius of the hole is normally distributed with mean 1.01 cm and standard deviation 0.003 cm. [p202] The machining processes that produce the rod and the hole are independent. [p203] Find the probability that the rod is to big for the hole.

Details:

[p204] Let \(X\) denote the radius of the rod and \(Y\) the radius of the hole. [p205] \(\P(Y - X \lt 0) = 0.0028\)
<<< UNIT U8 part 1 ends >>>


[p206] The weight of a peach from a certain orchard is normally distributed with mean 8 ounces and standard deviation 1 ounce. [p207] Find the probability that the combined weight of 5 peaches exceeds 45 ounces.

Details:

[p208] Let \(X\) denote the combined weight of the 5 peaches, in ounces. [p209] \(\P(X \gt 45) = 0.0127\)

A Further Generlization


<<< UNIT U7 part 1 begins >>>
[p210] In some settings, it's convenient to consider a constant as having a normal distribution (with mean being the constant and variance 0, of course). [p211] This convention simplifies the statements of theorems and definitions in these settings. [p212] Of course, the formulas for the probability density function [14] and the distribution function [17] do not hold for a constant, but the other results involving the moment generating function [23], linear transformations [24], and sums [26] are still valid. [p213] Moreover, the result for linear transformations [24] would hold for all \(a\) and \(b\).
<<< UNIT U7 part 1 ends >>>

