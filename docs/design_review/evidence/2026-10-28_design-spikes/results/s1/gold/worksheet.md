# Sentence-boundary worksheet

Each block below is one paragraph, list item, table cell or caption of canonical text.

## B001

```text
The chi-square distribution
```

## B002

```text
Let \(X\) denote the volume of beer in liters
```

## B003

```text
(a) \(\P(18 \lt X \lt 25)\)
```

## B004

```text
Expanding the square, the normal PDF can be written in the form \[ f(x) = \frac{1}{\sqrt{2 \pi} \sigma} \exp\left(-\frac{\mu^2}{2 \sigma^2}\right) \exp\left(\frac{\mu}{\sigma^2} x - \frac{1}{2 \sigma^2} x^2 \right), \quad x \in \R\] so the result follows from the definition of the general exponential family.
```

## B005

```text
(b) \(\E(X) = 400\), \(\sd(X) = 200\)
```

## B006

```text
The skewness and kurtosis of a variable are defined in terms of the standard score, so these results follows from the corresponding result for \( Z \) in [11].
```

## B007

```text
If \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\) then \(1 / X\) has the lognormal distribution with parameters \(-\mu\) and \(\sigma\).
```

## B008

```text
In the simulation of the special distribution simulator, select the gamma distribution. Vary the shape and scale parameters and note the shape and location of the probability density function. For various values of the parameters, run the simulation 1000 times and compare the empirical density function to the true probability density function.
```

## B009

```text
The mean and variance of \( Z \) are
```

## B010

```text
In particular, note that \( \skw(X) \to 0 \) and \( \kur(X) \to 3 \) as \( k \to \infty \). Note also that the excess kurtosis \( \kur(X) - 3 \to 0 \) as \( k \to \infty \).
```

## B011

```text
\[ f(x) = \frac{1}{b} \, g \left( \frac{x - a}{b} \right), \quad x \in \R\]
```

## B012

```text
(b) \(x_{0.95} = 0.51645\)
```

## B013

```text
Clearly \( f \) is a valid probability density function, since \( f(x) \gt 0 \) for \( x \gt 0 \), and by definition, \( \Gamma(k) \) is the normalizing constant for the function \( x \mapsto x^{k-1} e^{-x} \) on \( (0, \infty) \).
```

## B014

```text
The normal distribution is stable. Specifically, suppose that \( X \) has the normal distribution with mean \( \mu \in \R \) and variance \( \sigma^2 \in (0, \infty)\). If \( (X_1, X_2, \ldots, X_n) \) are independent copies of \( X \), then \( X_1 + X_2 + \cdots + X_n \) has the same distribution as \( \left(n - \sqrt{n}\right) \mu + \sqrt{n} X \), namely normal with mean \( n \mu \) and variance \( n \sigma^2 \).
```

## B015

```text
In the quantile app, select the normal distribution and keep the default settings.
```

## B016

```text
In the simulation of the special distribution simulator, select the lognormal distribution. Vary the parameters and note the shape and location of the mean\( \pm \)standard deviation bar. For selected values of the parameters, run the simulation 1000 times and compare the empirical moments to the true moments.
```

## B017

```text
(a) \(\E \left( Z^{2 n + 1} \right) = 0\)
```

## B018

```text
The distribution function \( F \) of \( X \) is given by \[ F(x) = \frac{\Gamma(k, x/b)}{\Gamma(k)}, \quad x \in (0, \infty) \]
```

## B019

```text
The Poisson distribution
```

## B020

```text
Suppose that \(Z\) has the standard normal distribution and let \(W = e^Z\) so that \(W\) has the standard lognormal distribution. If \(\mu \in \R\) and \(\sigma \in (0, \infty)\) then \(Y = \mu + \sigma Z\) has the normal distribution with mean \(\mu\) and standard deviation \(\sigma\) and hence \(X = e^Y\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\). But \[X = e^Y = e^{\mu + \sigma Z} = e^\mu \left(e^Z\right)^\sigma = e^\mu W^\sigma\]
```

## B021

```text
(b) \(\phi\) increases and then decreases, with mode \( z = 0 \).
```

## B022

```text
The Wald distribution is a scale family, although in the usual formulation, neither of the parameters is a scale parameter.
```

## B023

```text
In the special distribution simulator select the normal distribution. Vary the mean and standard deviation and note the size and location of the mean \(\pm\) standard deviation bar. With your choice of parameter settings, run the simulation 1000 times and compare the empirical mean and standard deviation to the true mean and standard deviation.
```

## B024

```text
(b) \(s(x) = (1 / b)r(x / b)\) for \(x \in [0, \infty)\)
```

## B025

```text
If \(Z\) has distribution function \(G\) then \(X\) has distribution function \(F\) given by \[  F(x) = G \left( \frac{x - a}{b} \right), \quad x \in \R\]
```

## B026

```text
(a) Find the probability that the device will last more than 300 hours.
```

## B027

```text
These result follow from the first four moments of the lognormal distribution in [7] and the standard computational formulas for skewness and kurtosis.
```

## B028

```text
Suppose that \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\) and that \(a \in \R \setminus \{0\}\). Then \(X^a\) has the lognormal distribution with parameters with parameters \(a \mu\) and \(|a| \sigma\).
```

## B029

```text
The gamma function was first introduced by Leonhard Euler.
```

## B030

```text
Theorem [26] generalizes to a sum of \(n\) independent, normal variables. The important part is that the sum is still normal; the expressions for the mean and variance are standard results that hold for the sum of independent variables generally. As a consequence of this result and the one for linear transformations [24], it follows that the normal distribution is stable.
```

## B031

```text
(b) \( f \) is concave upward then downward then upward again, with inflection points at \( x = \exp\left(\mu - \frac{3}{2} \sigma^2 \pm \frac{1}{2} \sigma \sqrt{\sigma^2 + 4}\right) \)
```

## B032

```text
This follows from the definition of the general exponential family. The gamma PDF can be written as \[ f(x) = \frac{1}{b^k \Gamma(k)} \exp\left[(k - 1) \ln x - \frac{1}{b} x\right], \quad x \in (0, \infty) \]
```

## B033

```text
(a) For the location family associated with \(g\), the graph of \(f\) is obtained by shifting the graph of \(g\), \(a\) units to the right if \(a \gt 0\) and \(-a\) units to the left if \(a \lt 0\).
```

## B034

```text
This follows from the change of variables formula corresponding to the transformation \( x = \mu + \sigma z \).
```

## B035

```text
First note that \( \P(X = x) = \P\left(Z = \frac{x - a}{b}\right) = 0 \), so \( X \) has a continuous distribution. Typically, \( Z \) takes values in an interval of \( \R \) and thus so does \( X \). The formula for the density function follows by taking derivatives of the distribution function in [2], since \( f = F^\prime \) and \( g = G^\prime \).
```

## B036

```text
The gamma distribution
```

## B037

```text
If \(G\) and \(F\) are the distribution functions of \(Z\) and \(X\), respectively, then
```

## B038

```text
(b) Suppose there exists \( a \in \R \) and \( b \in (0, \infty) \) such that \( F(x) = G\left(\frac{x - a}{b}\right) \) for \( x \in \R \). Then \( G(x) = F(a + b x) = F\left(\frac{x - (-a/b)}{1/b}\right) \) for \( x \in \R \).
```

## B039

```text
The result follows easily from the definition of entropy as an expected value: \[ H(X) = -\E[\ln f(X)] = -\E[\ln f(b Z)] = -\E(\ln [ g(Z) / b]) = -\E[\ln g(Z) - \ln b] = H(Z) + \ln b \]
```

## B040

```text
(d) If \( 0 \lt k \le 1 \), \( f \) is concave upward.
```

## B041

```text
Part (a) follows since \( X = \mu + \sigma Z \). Parts (b) and (c) follow from (a).
```

## B042

```text
We can generalize the last result to odd multiples of \( \frac{1}{2} \).
```

## B043

```text
The arcsine distribution is a location-scale family.
```

## B044

```text
Suppose that the lifetime of a device (in hours) has the gamma distribution with shape parameter \(k = 4\) and scale parameter \(b = 100\).
```

## B045

```text
(a) \(\E(X) = a + b \, \E(Z)\)
```

## B046

```text
The standard normal distribution is a continuous distribution on \( \R \) with probability density function \(\phi\) given by \[ \phi(z) = \frac{1}{\sqrt{2 \pi}} e^{-z^2 / 2}, \quad z \in \R \]
```

## B047

```text
(c) \(F(\mu) = \frac{1}{2}\) so the median occurs at \(x = \mu\).
```

## B048

```text
These results follow from standard calculus. Note that \(\phi^\prime(z) = - z \phi(z)\) (which gives (b)) and hence also \( \phi^{\prime \prime}(z) = (z^2 - 1) \phi(z) \) (which gives (c)).
```

## B049

```text
(f) If \( k \gt 2 \), \( f \) is concave upward, then downward, then upward again, with inflection points at \( k - 1 \pm \sqrt{k - 1} \).
```

## B050

```text
Even though the lognormal distribution has finite moments of all orders, the moment generating function is infinite at any positive number. This property is one of the reasons for the fame of the lognormal distribution.
```

## B051

```text
The special case \(k = 1\) gives the standard exponential distribution. The exponential distribution is studied in more detail in the chapter on Poisson process. When \(k \ge 1\), the gamma distribution is unimodal.
```

## B052

```text
(b) \( \var(Z) = 1 \)
```

## B053

```text
The moment generating function of \( X \) is given by \[ \E\left(e^{t X}\right) = \frac{1}{(1 - t)^k}, \quad t \lt 1 \]
```

## B054

```text
(d) \(f(x) \to 0\) as \(x \to \infty\) and as \(x \to -\infty\).
```

## B055

```text
(b) If \( n \in \N \), then by [3], \( \Gamma(k + n) = k (k + 1) \cdots (k + n - 1) \Gamma(k)  \), so the result follows from (a).
```

## B056

```text
The moments of the lognormal distribution can be computed from the moment generating function of the normal distribution. Once again, we assume that \(X\) has the lognormal distribution with parameters \(\mu \in \R\) and \(\sigma \in (0, \infty)\).
```

## B057

```text
In the quantile app, select the normal distribution and keep the default settings. Find the quantiles of the following orders for the standard normal distribution:
```

## B058

```text
The moment generating function \( M \) and characteristic function \( \chi \) of \( X \) are given by
```

## B059

```text
The entropy of \(X\) and \(Z\) are related by \(H(X) = H(Z) + \ln b\).
```

## B060

```text
The gamma function \( \Gamma \) is defined as follows \[ \Gamma(k) = \int_0^\infty x^{k-1} e^{-x} \, dx, \quad k \in (0, \infty) \] The function is well defined, that is, the integral converges for any \(k \gt 0\). On the other hand, the integral diverges to \( \infty \) for \( k \le 0 \).
```

## B061

```text
As usual, our starting point is a random experiment, modeled by a probability space \((\Omega, \ms F, \P)\). So \( \Omega \) is the set of outcomes, \( \ms F \) the collection of events, and \( \P \) the probability measure on the sample space \( (\Omega, \mathscr F) \). In this section, we assume that we fixed random variable \( Z \) defined on the probability space, with values in \( \R \).
```

## B062

```text
For \(a \in \R\) and \(b \in (0, \infty) \), let \(X = a + b \, Z\). The two-parameter family of distributions associated with \(X\) is called the location-scale family associated with the given distribution of \(Z\). Specifically, \(a\) is the location parameter and \(b\) the scale parameter.
```

## B063

```text
Suppose again that \( X \) has the normal distribution with location parameter \( \mu \in \R \) and scale parameter \( \sigma \in (0, \infty) \). As the notation suggests, the location and scale parameters are also the mean and standard deviation, respectively.
```

## B064

```text
Suppose that \(X\) is normally distributed with mean \(\mu\) and variance \(\sigma^2\). If \(a \in \R\) and \(b \in \R \setminus \{0\}\), then \(a + b X\) is normally distributed with mean \(a + b \mu\) and variance \(b^2 \sigma^2\).
```

## B065

```text
The MGF of \(a + b X\) is \[ \E\left[e^{t (a + b X)}\right] = e^{ta} \E\left[e^{(t b) X}\right] = e^{ta} e^{\mu (t b) + \sigma^2 (t b)^2 / 2} = e^{(a + b \mu)t + b^2 \sigma^2 t^2 / 2} \] which we recognize as the MGF of the normal distribution with mean \(a + b \mu\) and variance \(b^2 \sigma^2\).
```

## B066

```text
Recall that in general, if \(X\) is a random variable with mean \(\mu\) and standard deviation \(\sigma \gt 0\), then \(Z = (X - \mu) / \sigma\) is the standard score of \(X\). A corollary of the last result is that if \(X\) has a normal distribution then the standard score \(Z\) has a standard normal distribution. Conversely, any normally distributed variable can be constructed from a standard normal variable.
```

## B067

```text
Suppose that \(X_1\) and \(X_2\) are independent random variables, and that \(X_i\) is normally distributed with mean \(\mu_i\) and variance \(\sigma_i^2\) for \(i \in \{1, 2\}\). Then \(X_1 + X_2\) is normally distributed with
```

## B068

```text
(a) \(\E(X_1 + X_2) = \mu_1 + \mu_2\)
```

## B069

```text
(b) \(\var(X_1 + X_2) = \sigma_1^2 + \sigma_2^2\)
```

## B070

```text
The MGF of \(X_1 + X_2\) is the product of the MGFs, so \[ \E\left(\exp\left[t (X_1 + X_2)\right]\right) = \exp\left(\mu_1 t + \sigma_1^2 t^2 / 2\right) \exp\left(\mu_2 t + \sigma_2^2 t^2 / 2\right) = \exp\left[\left(\mu_1 + \mu_2\right)t + \left(\sigma_1^2 + \sigma_2^2\right) t^2 / 2\right] \] which we recognize as the MGF of the normal distribution with mean \(\mu_1 + \mu_2\) and variance \(\sigma_1^2 + \sigma_2^2\).
```

## B071

```text
A metal rod is designed to fit into a circular hole on a certain assembly. The radius of the rod is normally distributed with mean 1 cm and standard deviation 0.002 cm. The radius of the hole is normally distributed with mean 1.01 cm and standard deviation 0.003 cm. The machining processes that produce the rod and the hole are independent. Find the probability that the rod is to big for the hole.
```

## B072

```text
Let \(X\) denote the radius of the rod and \(Y\) the radius of the hole. \(\P(Y - X \lt 0) = 0.0028\)
```

## B073

```text
In some settings, it's convenient to consider a constant as having a normal distribution (with mean being the constant and variance 0, of course). This convention simplifies the statements of theorems and definitions in these settings. Of course, the formulas for the probability density function [14] and the distribution function [17] do not hold for a constant, but the other results involving the moment generating function [23], linear transformations [24], and sums [26] are still valid. Moreover, the result for linear transformations [24] would hold for all \(a\) and \(b\).
```

## B074

```text
Suppose that \(Y\) has the normal distribution with mean \(\mu \in \R\) and standard deviation \(\sigma \in (0, \infty)\). Then \(X = e^Y\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\).
```

## B075

```text
(a) The parameter \( \sigma \) is the shape parameter of the distribution.
```

## B076

```text
(b) The parameter \( e^\mu\) is the scale parameter of the distribution.
```

## B077

```text
If \(Z\) has the standard normal distribution then \(W = e^Z\) has the standard lognormal distribution.
```

## B078

```text
Suppose that \(n \in \N_+\) and that \((X_1, X_2, \ldots, X_n)\) is a sequence of independent variables, where \(X_i\) has the lognormal distribution with parameters \(\mu_i \in \R\) and \(\sigma_i \in (0, \infty)\) for \(i \in \{1, 2, \ldots, n\}\). Then \(\prod_{i=1}^n X_i\) has the lognormal distribution with parameters \(\mu\) and \(\sigma\) where \(\mu = \sum_{i=1}^n \mu_i\) and \(\sigma^2 = \sum_{i=1}^n \sigma_i^2\).
```

## B079

```text
Again from definition [1], we can write \( X_i = e^{Y_i} \) where \(Y_i\) has the normal distribution with mean \(\mu_i\) and standard deviation \(\sigma_i\) for \(i \in \{1, 2, \ldots, n\}\) and where \((Y_1, Y_2, \ldots, Y_n)\) is an independent sequence. Hence \(\prod_{i=1}^n X_i = \exp\left(\sum_{i=1}^n Y_i\right)\). But \(\sum_{i=1}^n Y_i\) has the normal distribution with mean \(\sum_{i=1}^n \mu_i\) and variance \(\sum_{i=1}^n \sigma_i^2\).
```

## B080

```text
The mean and variance of \( X \) are
```

## B081

```text
(a) From [3], \[ \E(X) = \int_0^\infty x \frac{1}{\Gamma(k)} x^{k-1} e^{-x} \, dx = \frac{\Gamma(k + 1)}{\Gamma(k)} = k\]
```

## B082

```text
(b) From [3] again \[ \E\left(X^2\right) = \int_0^\infty x^2 \frac{1}{\Gamma(k)} x^{k-1} e^{-x} \, dx = \frac{\Gamma(k + 2)}{\Gamma(k)} = (k + 1) k\] and hence \( \var(X) = \E\left(X^2\right) - [\E(X)]^2 = k \)
```

## B083

```text
If \(Z\) has the standard gamma distribution with shape parameter \(k \in (0, \infty)\) and if \( b \in (0, \infty) \), then \(X = b Z\) has the gamma distribution with shape parameter \(k\) and scale parameter \(b\).
```

## B084

```text
Suppose that \(X_1\) and \(X_2\) are independent random variables, and that \(X_i\) has the gamma distribution with shape parameter \(k_i \in (0, \infty)\) and scale parameter \(b \in (0, \infty)\) for \(i \in \{1, 2\}\). Then \(X_1 + X_2\) has the gamma distribution with shape parameter \(k_1 + k_2\) and scale parameter \(b\).
```

## B085

```text
Recall that the MGF of \( X = X_1 + X_2 \) is the product of the MGFs of \( X_1 \) and \( X_2 \), so \[ \E\left(e^{t X}\right) = \frac{1}{(1 - b t)^{k_1}} \frac{1}{(1 - b t)^{k_2}} = \frac{1}{(1 - b t)^{k_1 + k_2}}, \quad t \lt \frac{1}{b} \]
```
