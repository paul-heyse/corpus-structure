# SymPy — Comprehensive Python Library Capability Reference

Target version: SymPy 1.14.0 (current stable release) | Research date: October 21, 2026

Official documentation: `https://docs.sympy.org/latest/index.html` Source repository: `https://github.com/sympy/sympy` Package: `https://pypi.org/project/sympy/` Release history: `https://github.com/sympy/sympy/releases`

SymPy 1.14.0, released April 27, 2025, remains the latest stable release listed by the official project and PyPI at the time of research. The separate development documentation describes 1.15.0.dev; development-only capabilities are not treated as released functionality here.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



## 1. Architectural orientation

SymPy is an open-source, predominantly pure-Python computer algebra system (CAS). Although commonly introduced as a library for symbolic differentiation, integration, equation solving, and simplification, its capabilities extend substantially further.

It provides a general symbolic mathematics infrastructure encompassing exact algebra, computer algebra algorithms, expression manipulation, formal mathematical representations, differential equations, discrete mathematics, probability, mathematical physics, symbolic linear algebra, numerical evaluation, and generation of executable numerical code.

Its most important architectural characteristic is the ability to represent mathematical operations as first-class symbolic objects, transform and reason about those objects, and subsequently translate them into specialized mathematical or numerical representations.

This makes SymPy useful in several distinct roles:

- Symbolic mathematics engine: Perform algebraic transformations, derive formulas, prove or test mathematical relationships, and solve supported classes of equations.
- Mathematical intermediate representation: Express and manipulate equations, derivatives, matrices, tensors, piecewise functions, constraints, and other mathematical structures without immediately evaluating them.
- Exact algebra engine: Operate over integers, rational numbers, finite fields, polynomial rings, algebraic number fields, and related mathematical domains.
- Analytical model generator: Derive Jacobians, Hessians, series approximations, analytical transformations, dynamical systems, and governing equations.
- Compiler front end for mathematical expressions: Transform symbolic formulas into executable Python, NumPy, C, Fortran, Rust, and other supported target-language representations.
- Scientific modeling foundation: Build symbolic models in mechanics, controls, quantum physics, statistics, geometry, and other mathematical disciplines.

SymPy is not primarily a high-performance numerical array engine, a general-purpose constrained-optimization platform, or a large-scale numerical simulation runtime. Its strength is the representation and transformation of mathematics, including the generation of formulas and numerical kernels for execution elsewhere.

### 1.1 The main capability families

| Capability                            | Principal mechanisms                                                                                            |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Symbolic representation               | `Basic`, `Expr`, `Symbol`, `Function`, `Add`, `Mul`, `Pow`, expression trees                                    |
| Mathematical reasoning                | Assumptions, predicates, `ask`, `refine`, symbolic relations, Boolean logic                                     |
| Transformation and optimization       | Simplification, expansion, factoring, collection, rewriting, pattern matching, common-subexpression elimination |
| Calculus and analysis                 | Differentiation, integration, limits, series, sums, products, special functions, integral transforms            |
| Equations and systems                 | `solve`, `solveset`, `linsolve`, `nonlinsolve`, `nsolve`, `dsolve`, `pdsolve`                                   |
| Polynomial and exact algebra          | `Poly`, coefficient domains, polynomial rings, Gröbner bases, number fields, algebraic extensions               |
| Linear algebra                        | Symbolic matrices, `MatrixExpr`, matrix decompositions, exact-domain matrices, sparse representations           |
| Tensor mathematics                    | Indexed expressions, array expressions, tensor symmetries, tensor contraction                                   |
| Discrete mathematics                  | Number theory, combinatorics, permutation groups, recurrence equations, symbolic logic                          |
| Advanced mathematical representations | Holonomic functions, hypergeometric functions, formal power series, differential geometry                       |
| Applied mathematics and physics       | Classical mechanics, biomechanics, control theory, quantum mechanics, units, optics                             |
| Probability and statistics            | Symbolic random variables, distributions, joint probability, expectations, conditional probability              |
| Numerical and compiled execution      | `evalf`, `lambdify`, `ufuncify`, `autowrap`, code generation and language-specific printers                     |
| Extensibility                         | Custom symbolic classes, defined and undefined functions, evaluation hooks, derivatives, rewrites, printers     |

The official reference demonstrates that these families are not simply interfaces to a single generic algebra solver. They are specialized mathematical subsystems with different internal representations and algorithms. In particular, the polynomial-domain infrastructure, matrix-expression system, mechanics framework, and symbolic code-generation machinery warrant examination independently of ordinary scalar expression manipulation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation

+2



Primary capability index: `https://docs.sympy.org/latest/reference/index.html`

Polynomial and exact algebra reference: `https://docs.sympy.org/latest/modules/polys/index.html`

## 2. Symbolic representation and expression architecture

### 2.1 The expression tree as SymPy's foundational abstraction

Most SymPy objects inherit from `Basic`. Mathematical scalar expressions ordinarily inherit from `Expr`, which adds algebraic operations and mathematical behavior.

An expression is represented structurally through a class and its arguments:

- `expr.func` identifies the operation or constructor.
- `expr.args` contains its immediate operands.
- `expr.free_symbols` identifies symbols that are free within the expression.
- `expr.atoms()` identifies selected terminal objects or expression types.
- `expr.has()`, `find()`, and tree traversal utilities support structural inspection.
- `srepr()` exposes the constructor-oriented representation.

For example, `x**2 + x*y` is internally composed from `Add`, `Pow`, `Mul`, `Symbol`, and `Integer` objects.

A consequential characteristic is that SymPy expressions are immutable. Transformations ordinarily construct new expressions rather than mutating existing trees. This supports structural hashing, caching, symbolic substitution, and reuse of subexpressions.

SymPy also normally canonicalizes elementary operations as objects are constructed. Commutative sums and products are normalized, like terms may combine, and simple arithmetic can evaluate automatically.

Consequently, SymPy is not an unrestricted syntax-tree representation preserving every original operation and evaluation order. The distinction matters for exact algebra, numerical floating-point semantics, compiler transformations, and applications requiring faithful source-level representations.

Relevant interfaces include `evaluate=False`, `UnevaluatedExpr`, `sympify`, `S`, `Dummy`, `Wild`, and `Lambda`.

Source: `https://docs.sympy.org/latest/modules/core.html`

### 2.2 Exact values and mathematical identity

SymPy distinguishes exact mathematical objects from approximate numerical values.

| Representation      | Semantics                                              |
| ------------------- | ------------------------------------------------------ |
| `Integer(2)`        | Exact integer                                          |
| `Rational(1, 3)`    | Exact rational                                         |
| `Float(...)`        | Finite-precision floating-point approximation          |
| `pi`, `E`, `I`      | Symbolic mathematical constants                        |
| `sqrt(2)`           | Exact algebraic expression                             |
| `RootOf`, `CRootOf` | Algebraic numbers represented through polynomial roots |
| `Symbol`            | Indeterminate with optional assumptions                |
| `Dummy`             | Uniquely identified symbolic placeholder               |

An important distinction is that Python arithmetic may already have converted exact values into floating-point approximations before SymPy receives them.

For instance, `S(1)/3` preserves an exact rational, whereas Python's `1/3` produces a floating-point number.

The separation of exact expressions and approximations is fundamental to SymPy's symbolic solvers, polynomial algorithms, and arbitrary-precision evaluation.

There are also distinct notions of equality:

- `a == b` generally checks structural equality after SymPy's normal canonicalization.
- `Eq(a, b)` represents a mathematical equality.
- `a.equals(b)` attempts mathematical equivalence reasoning and may return `None` when inconclusive.
- `simplify(a - b) == 0` is a useful but not complete equivalence test.

No single general-purpose simplification procedure constitutes a universal decision algorithm for arbitrary symbolic mathematical equality.

Source: `https://docs.sympy.org/latest/explanation/best-practices.html`

### 2.3 Unevaluated mathematical operations

SymPy can preserve mathematical operations symbolically rather than immediately execute them.

Examples include:

| Object               | Represents                                      |
| -------------------- | ----------------------------------------------- |
| `Derivative`         | An unevaluated derivative                       |
| `Integral`           | An unevaluated definite or indefinite integral  |
| `Sum`, `Product`     | Symbolic finite or infinite summation/product   |
| `Limit`              | A limiting operation                            |
| `Subs`               | A substitution operation                        |
| `Piecewise`          | A condition-dependent expression                |
| `RootOf` / `CRootOf` | An algebraic root without requiring radicals    |
| `MatrixExpr`         | A matrix operation without constructing entries |

Many of these objects implement `.doit()` to evaluate the operation when supported.

This separation between representing and executing mathematics creates opportunities for staged transformations, symbolic differentiation of integrals or sums, preservation of analytical structure, and partial evaluation.

It also allows SymPy to return a meaningful unevaluated object when an analytical algorithm cannot complete the requested operation, rather than always requiring numerical approximation.

### 2.4 Noncommutative expressions

Symbols can be created with `commutative=False`, allowing SymPy to retain multiplication order.

This is useful for operator algebra, quantum mechanics, noncommutative products, and mathematical systems where \\(AB\neq BA\\).

However, noncommutative expressions remain subject to the capabilities of the particular SymPy subsystem. Declaring noncommutativity does not automatically provide a complete general-purpose noncommutative algebra solver.

More structured representations, such as tensor objects, matrices, or quantum operators, may carry additional semantics that ordinary noncommutative symbols do not.

## 3. Mathematical assumptions and domain-aware reasoning

Assumptions are a foundational part of SymPy's correctness model, not merely optional annotations.

They govern when mathematical transformations are valid, whether expressions can be simplified, and how certain solvers interpret the mathematical domain.

### 3.1 Core assumptions system

Symbols can be declared with properties such as:

`real`, `positive`, `nonnegative`, `integer`, `rational`, `finite`, `nonzero`, `imaginary`, `hermitian`, and `commutative`.

These properties propagate through logical implications. For example, positivity implies realness, while integer status implies rationality.

The core assumptions system uses three-valued reasoning:

| Result  | Interpretation        |
| ------- | --------------------- |
| `True`  | Property established  |
| `False` | Property disproved    |
| `None`  | Property undetermined |

`None` is not equivalent to `False`.

The assumptions system intentionally does not attempt to establish every mathematically decidable property. Some predicates would require expensive algebraic reasoning, and others are undecidable in general.

This matters particularly when symbolic transformations depend on signs, realness, nonzero denominators, or branch conditions.

Source: `https://docs.sympy.org/latest/guides/assumptions.html`

### 3.2 Predicate-based assumptions: `Q`, `ask`, and `refine`

SymPy also has a separate predicate-based reasoning interface.

`Q` expresses mathematical predicates, `ask()` evaluates propositions under assumptions, and `refine()` simplifies expressions using additional information.

For example:

```
from sympy import symbols, sqrt, Q, ask, refinex = symbols("x", real=True)assert ask(Q.real(x)) is Trueexpr = sqrt(x**2)refined = refine(expr, Q.positive(x))# refined is x
```

This example is illustrative and has not been executed here.

The distinction between the two assumptions systems is important:

- The core, symbol-property assumptions system remains heavily used throughout SymPy.
- The predicate-based system supports explicit propositions and reasoning contexts.
- `refine()` applies supplied assumptions to supported transformations.
- The two systems are not universally interchangeable or comprehensively integrated.

The official documentation explicitly cautions that the historically named "old" system remains the primary assumptions mechanism used internally.

Sources:

`https://docs.sympy.org/latest/modules/assumptions/ask.html`

`https://docs.sympy.org/latest/modules/assumptions/refine.html`

### 3.3 Symbolic logic versus fuzzy Boolean reasoning

SymPy distinguishes symbolic Boolean expressions such as `And`, `Or`, `Not`, `Eq`, and relational inequalities from Python-level truth values and fuzzy assumption results.

An unresolved symbolic inequality is not simply a Python `False`; it is a mathematical object whose truth may depend on variable values.

This allows conditions to remain embedded in `Piecewise` expressions, symbolic constraints, sets, and analytical results.

It also requires careful treatment of Python control flow: an arbitrary symbolic relation cannot generally be converted into a definite Python `bool`.

Source: `https://docs.sympy.org/latest/guides/booleans.html`

## 4. Symbolic transformations, simplification, and expression optimization

SymPy provides a much broader transformation system than its familiar `simplify()` function.

For sophisticated symbolic workflows, it is useful to distinguish semantic simplification, algebraic normalization, structural rewriting, and operation-cost reduction.

### 4.1 Algebraic transformation families

| Family                                  | Principal operations                                 | Significance                                                  |
| --------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| General simplification                  | `simplify`, `signsimp`, `powsimp`                    | Heuristic reduction of expression complexity                  |
| Expansion                               | `expand`, `expand_mul`, `expand_trig`, `expand_func` | Expose polynomial terms and identities                        |
| Factorization                           | `factor`, `factor_terms`                             | Identify multiplicative structure                             |
| Rational normalization                  | `cancel`, `together`, `apart`, `ratsimp`             | Normalize, combine, or decompose rational expressions         |
| Coefficient collection                  | `collect`, `rcollect`                                | Group expressions by variables or powers                      |
| Trigonometric reduction                 | `trigsimp`, `trigsimp(method="fu")`, `fu`            | Apply trigonometric identities and specialized heuristics     |
| Exponential/logarithmic transformations | `expand_log`, `logcombine`, `expand_power_exp`       | Rewrite transcendental structure under appropriate conditions |
| Radical transformations                 | `radsimp`, `sqrtdenest`, `powdenest`                 | Rationalize or denest eligible expressions                    |
| Special-function transformations        | `hyperexpand`, `combsimp`, `gammasimp`               | Simplify specialized functions and combinatorial expressions  |
| Complex decomposition                   | `re`, `im`, `expand_complex`, `as_real_imag`         | Separate real and imaginary components                        |
| Operation sharing                       | `cse`                                                | Extract repeatedly occurring subexpressions                   |

These operations are not interchangeable.

For example, `expand()` may increase expression size while producing a form better suited to coefficient extraction, integration, or polynomial algorithms. Conversely, factorization may reduce apparent complexity but obscure sparsity useful to other operations.

Likewise, `simplify()` is a heuristic operation and should not be treated as either a canonical normal form or an optimization for minimum execution cost.

Sources:

`https://docs.sympy.org/latest/modules/simplify/simplify.html`

`https://docs.sympy.org/latest/modules/rewriting.html`

### 4.2 Structural pattern matching and custom transformations

SymPy supports structural pattern matching and selective rewriting through:

- `Wild` symbols and `.match()`
- `.replace()` with patterns, types, or predicates
- `.xreplace()` for exact node replacement
- `.subs()` for mathematical substitution
- `.rewrite()` for supported representation changes
- `.collect()` for algebraic grouping
- Expression traversal and reconstruction using `.func` and `.args`

These operations enable rule-based mathematical transformations without writing a complete independent expression tree system.

However, they have different semantics.

`subs()` can apply mathematical substitution rules that differ from literal tree replacement. `xreplace()` performs exact structural replacements. Pattern matching should not be confused with a complete algebraic equivalence prover.

The choice matters when substitutions involve bound variables, reordered commutative expressions, function identities, or mathematical domains.

### 4.3 Common-subexpression elimination

`cse()` is particularly significant for generated numerical calculations.

Given a collection of mathematical expressions, it identifies repeated subexpressions and produces temporary assignments plus reduced output expressions.

Consider:

```
from sympy import symbols, sin, cos, csex, y = symbols("x y")f = (sin(x) + cos(y))**2g = (sin(x) + cos(y))**3temporaries, outputs = cse([f, g])
```

Instead of independently computing `sin(x) + cos(y)` for every expression, the resulting representation can compute it once and reuse its value.

The benefit can extend to multiple outputs, Jacobians, residual vectors, tensor components, and equation systems.

There are important qualifications:

1. `cse()` identifies symbolic reuse, but it is not a complete compiler optimizer.
2. Sharing can reduce arithmetic while increasing temporary storage or register pressure.
3. The optimal grouping of operations depends on the eventual numerical backend.
4. Some code-generation workflows require explicit coordination of CSE with the generated program.

`count_ops()` supplies a symbolic operation-counting mechanism useful for comparing expression forms. It is a structural cost heuristic, not an accurate predictor of machine execution time.

Source: `https://docs.sympy.org/latest/modules/rewriting.html`

### 4.4 Transformation pipelines rather than isolated simplification calls

A powerful architectural pattern is to compose transformations according to the mathematical workload.

For example, a symbolic numerical-kernel derivation might:

1. Construct equations in exact symbolic form.
2. Differentiate or otherwise derive required outputs.
3. Normalize appropriate rational or polynomial subexpressions.
4. Apply domain-valid simplifications.
5. Detect common subexpressions across outputs.
6. Convert the optimized mathematical representation into executable code.

The advantage is not simply fewer lines of symbolic-manipulation code. It is the ability to operate on a coherent mathematical model and delay numerical implementation decisions until the desired analytical transformations have been performed.

This composition is a general possibility, not a guarantee of faster numerical execution. Expression form, floating-point behavior, branch conditions, and backend optimization all affect the eventual outcome.

## 5. Polynomial systems, exact algebra, and algebraic domains

The `sympy.polys` subsystem is one of the most consequential parts of SymPy and is substantially more sophisticated than ordinary expression expansion or factorization.

It provides explicit representations of polynomial rings and coefficient domains, together with algorithms for exact arithmetic, factorization, elimination, algebraic number theory, and computational commutative algebra.

### 5.1 `Expr` versus `Poly` versus polynomial rings

Three representations serve materially different purposes.

| Representation        | Main role                                                    | Important distinction                                               |
| --------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------- |
| `Expr`                | General symbolic mathematical expression                     | Supports broad operations but does not require polynomial structure |
| `Poly`                | Polynomial with designated generators and coefficient domain | Exposes polynomial-specific algorithms and domain information       |
| `ring()` / `PolyRing` | Algebraic polynomial-ring elements                           | Operates within an explicit coefficient domain and generator set    |

`Poly` provides access to coefficients, monomials, terms, polynomial division, factorization, content/primitive-part decomposition, and many more specialized operations.

The ring APIs are particularly interesting when polynomial arithmetic itself constitutes a substantial workload. Rather than repeatedly converting arbitrary symbolic expressions into polynomial form, they allow operations to take place directly in a polynomial representation.

This separation can reduce repeated coefficient-domain inference and the overhead of general-purpose expression manipulation.

Sources:

`https://docs.sympy.org/latest/modules/polys/basics.html`

`https://docs.sympy.org/latest/modules/polys/reference.html`

`https://docs.sympy.org/latest/modules/polys/domainsref.html`

### 5.2 The algebraic-domain system

SymPy's domain system explicitly represents the coefficient structures over which polynomial and matrix algorithms operate.

| Domain or construction    | Meaning                                               |
| ------------------------- | ----------------------------------------------------- |
| `ZZ`                      | Integers                                              |
| `QQ`                      | Rational numbers                                      |
| `RR`                      | Arbitrary-precision approximate real-number domain    |
| `CC`                      | Arbitrary-precision approximate complex-number domain |
| `GF(p)`                   | Modular arithmetic, including prime-field cases       |
| `QQ.algebraic_field(...)` | Algebraic extensions of the rational field            |
| `K.poly_ring(...)`        | Polynomial ring over domain `K`                       |
| `K.frac_field(...)`       | Rational-function field over domain `K`               |
| `EX`                      | General symbolic-expression domain                    |
| `ZZ_I`, `QQ_I`            | Gaussian integers and Gaussian rationals              |

The algebraic structure matters because algorithms require different properties from their coefficient domains.

For example, polynomial division over a field is fundamentally different from division over an integer ring, while some factorization algorithms require exact arithmetic or a particular field structure.

The generic expression domain `EX` permits more general coefficients, but it can be substantially more expensive than working with specialized domains such as `QQ` or an algebraic extension.

An important architectural principle follows: the mathematical coefficient domain is part of the computational representation, not merely a type annotation attached to the result.

SymPy provides `construct_domain()` and domain-conversion mechanisms to infer and manipulate these representations. Some algorithms also support explicitly requesting extensions, rational-function fields, or exact coefficient domains.

Source: `https://docs.sympy.org/latest/modules/polys/domainsintro.html`

### 5.3 Advanced polynomial algorithms

The polynomial subsystem includes:

Polynomial arithmetic and normalization: Euclidean and extended-Euclidean algorithms, GCD and LCM, polynomial division, pseudodivision, square-free decomposition, primitive-part extraction, content computation, and normalization.

Factorization and decomposition: Exact polynomial factorization, multivariate factorization, rational-function decomposition, and operations over supported algebraic number fields.

Elimination theory: Resultants, subresultant sequences, discriminants, elimination of variables, and polynomial-system transformations.

Root analysis: Exact roots where supported, symbolic algebraic root objects, real-root isolation, multiplicities, numerical polynomial root approximations, and root refinement.

Interpolation and composition: Polynomial interpolation, composition, decomposition, and transformations of polynomial representations.

This means SymPy can perform many algebraic tasks that would otherwise require bespoke manipulation of polynomial coefficients or custom algebraic elimination routines.

### 5.4 Gröbner bases and polynomial-system elimination

`groebner()` computes Gröbner bases for polynomial ideals using supported monomial orders, including `lex`, `grlex`, and `grevlex`.

A Gröbner basis provides a structured representation of a polynomial ideal useful for:

- Polynomial ideal membership and reduction.
- Elimination of variables.
- Solving supported polynomial equation systems.
- Determining whether polynomial systems admit common zeros.
- Transforming polynomial constraints into algebraically equivalent forms.

Related infrastructure includes polynomial reduction, Gröbner basis conversion, and support for FGLM-style monomial-order conversion under its applicable mathematical conditions.

The key distinction from a general symbolic equation solver is that the problem has been expressed over a specific polynomial ring with an explicit algebraic domain.

Gröbner basis calculations can be extremely powerful, but their worst-case computational complexity is severe. The number of variables, polynomial degree, coefficient domain, and monomial order can dramatically affect their feasibility.

Source: `https://docs.sympy.org/latest/modules/polys/reference.html`

### 5.5 Algebraic numbers and number fields

SymPy supports algebraic-number calculations through facilities including:

`AlgebraicNumber`, `minimal_polynomial` / `minpoly`, `primitive_element`, `field_isomorphism`, `to_number_field`, `RootOf`, and `CRootOf`.

These allow exact representations of algebraic quantities without relying on potentially enormous radical expressions.

For example, the field generated by \\(\sqrt{2}\\) and \\(\sqrt{3}\\) can be expressed using a primitive element \\(\sqrt{2}+\sqrt{3}\\), whose minimal polynomial is

\\[ x^4-10x^2+1. \\]

The resulting algebraic field permits exact arithmetic using polynomial representations reduced modulo the minimal polynomial.

This becomes useful for algebraic factorization, exact matrix computations, symbolic roots, and problems where algebraic irrationalities are pervasive.

SymPy also exposes field embeddings, subfield problems, and related algebraic-number operations.

Source: `https://docs.sympy.org/latest/modules/polys/numberfields.html`

### 5.6 Algebraic geometry and commutative algebra

The `sympy.polys.agca` subsystem extends polynomial algebra toward ideals, modules, quotient structures, and localizations.

It provides abstractions for working with mathematical objects such as:

- Polynomial ideals and submodules.
- Free modules and module homomorphisms.
- Quotient rings and quotient modules.
- Ring localization and local algebra.
- Algebraic structures associated with polynomial varieties.

These facilities can reduce the need to construct custom abstractions for polynomial ideals and related operations.

However, this is not a complete computational algebraic geometry environment. The documentation explicitly notes that useful functionality is concentrated in particular classes of rings, especially polynomial rings over fields and some associated quotient or localization structures.

Source: `https://docs.sympy.org/latest/modules/polys/agca.html`

### 5.7 Polynomial-backed series computation

A less obvious capability is `sympy.polys.ring_series`.

Ordinary Taylor expansions often use general symbolic-expression operations. The ring-series subsystem instead performs truncated series calculations using sparse polynomial arithmetic.

It supports specialized operations for series expansion, truncation, inversion, logarithms, exponentials, roots, and series reversion, together with `rs_series()`.

This can be advantageous for high-order expansions and multivariate series when the underlying functions are supported.

The official documentation includes historical examples where polynomial-backed methods substantially outperform generic series manipulation. Those measurements are illustrative rather than guaranteed speedups for arbitrary expressions.

Function support and the class of series being expanded remain important limitations; the subsystem is not a universal substitute for general asymptotic analysis.

Source: `https://docs.sympy.org/latest/modules/polys/ringseries.html`

## 6. Exact matrix algebra and `DomainMatrix`

Although matrix algebra is part of ordinary SymPy usage, its different representations deserve separate consideration.

### 6.1 Explicit symbolic matrices

The `Matrix` family supports dense and sparse matrices containing arbitrary SymPy expressions.

Important operations include:

| Family                   | Capabilities                                                        |
| ------------------------ | ------------------------------------------------------------------- |
| Matrix arithmetic        | Addition, multiplication, powers, transposes, inversion             |
| Linear-system solving    | `LUsolve`, `QRsolve`, `gauss_jordan_solve`, `solve`                 |
| Decompositions           | LU, QR, Cholesky, LDL, and other applicable decompositions          |
| Structural analysis      | Rank, nullspace, column space, row space, RREF                      |
| Eigenstructure           | Eigenvalues, eigenvectors, diagonalization, Jordan forms            |
| Matrix functions         | Matrix exponentials, powers, characteristic and minimal polynomials |
| Symbolic differentiation | Entrywise differentiation, Jacobians, Hessians                      |
| Specialized exact forms  | Smith and Hermite normal forms                                      |

There are mutable and immutable variants, including `MutableDenseMatrix`, `ImmutableDenseMatrix`, and sparse matrix types.

Symbolic matrix algorithms can generate enormous expressions. The cost may be dominated by intermediate expression growth rather than ordinary floating-point arithmetic.

Sources:

`https://docs.sympy.org/latest/modules/matrices/matrices.html`

`https://docs.sympy.org/latest/modules/matrices/normalforms.html`

### 6.2 `DomainMatrix`: exact-domain linear algebra

`DomainMatrix`, implemented within `sympy.polys.matrices`, represents matrices whose elements all belong to a specified algebraic domain.

Unlike a general `Matrix` containing arbitrary expressions, it makes the coefficient domain explicit and uses dedicated dense and sparse internal representations.

Principal representation classes include:

- `DDM`: dense domain matrix.
- `SDM`: sparse domain matrix.
- `DFM`: FLINT-backed dense domain matrix when the requisite optional backend is available.

Supported operations include exact-domain matrix arithmetic, linear solving, inversion under suitable conditions, RREF, determinant calculation, characteristic-polynomial computation, and related algorithms.

A particularly important family comprises fraction-free and denominator-aware methods, including operations such as `solve_den()` and `rref_den()`.

These can represent a matrix result as a numerator matrix and a common denominator rather than constructing a field fraction at every elimination step.

For suitable exact domains, this can reduce the cost of intermediate rational arithmetic and help control expression growth.

The benefit depends on the coefficient domain and the structure of the system.

Source: `https://docs.sympy.org/latest/modules/polys/domainmatrix.html`

### 6.3 Native FLINT integration

SymPy 1.14 also documents optional integration with `python-flint`, the Python bindings to the FLINT computer algebra library.

For supported integer and rational domains, SymPy can use FLINT-backed arithmetic and matrix representations.

In particular, with the documented `SYMPY_GROUND_TYPES=flint` configuration and `python-flint` installed, supported dense `DomainMatrix` representations can use the native `DFM` backend.

This is a more consequential integration than simply using a faster arbitrary-precision integer type. It can shift some exact algebra operations from pure-Python implementations into optimized native mathematical kernels.

The integration is not universal: different domains, representations, and algorithms have different backend support. FLINT should not be assumed to accelerate all SymPy expression manipulation.

Source: `https://docs.sympy.org/latest/modules/polys/domainmatrix.html`

### 6.4 Matrix normal forms over exact rings

SymPy supports Smith normal form and Hermite normal form, with important domain restrictions.

These are useful in computational number theory, lattice-related calculations, integer linear algebra, and classification of finitely generated algebraic structures.

For example, Smith normal form is applicable over principal ideal domains, while the documented Hermite normal form implementation operates on integer matrices.

They are fundamentally different from floating-point matrix decompositions and should not be treated as interchangeable approaches to generic numerical linear-system solving.

Source: `https://docs.sympy.org/latest/modules/matrices/normalforms.html`

## 7. Symbolic equation solving and constraint systems

SymPy has several solver families because solving a polynomial equation, an arbitrary transcendental equation, an exact linear system, and a numerical nonlinear system are different computational problems.

### 7.1 The primary algebraic solver interfaces

| Interface                     | Problem class                               | Important output behavior                             |
| ----------------------------- | ------------------------------------------- | ----------------------------------------------------- |
| `solve()`                     | Broad symbolic equation solving             | Mature, flexible API with variable output shapes      |
| `solveset()`                  | Univariate equations over specified domains | Returns mathematical sets                             |
| `linsolve()`                  | Linear systems                              | Returns solution sets, including parametric solutions |
| `nonlinsolve()`               | Multivariate nonlinear systems              | Returns sets of solution tuples                       |
| `nsolve()`                    | Numerical nonlinear equation solving        | Returns numerical approximations                      |
| `roots()`                     | Algebraic polynomial roots                  | May return roots with multiplicities                  |
| `all_roots()`, `real_roots()` | Polynomial root representations             | Supports exact algebraic-root objects                 |
| `nroots()`                    | Numerical polynomial root approximation     | Computes approximate roots                            |

The precise mathematical domain and completeness of the result matter at least as much as the particular algorithm selected.

### 7.2 `solve()` versus `solveset()`

`solve()` is the older, broad, relatively mature interface, capable of handling numerous equation structures and optional behaviors.

Its return values can vary among lists, dictionaries, expressions, and tuples depending on problem shape and options.

For programmatic processing, `dict=True` can provide a more consistent format for supported cases.

`solveset()` takes a more explicitly mathematical approach, returning solution-set objects.

Examples of such results include:

- `FiniteSet`
- `Interval`
- `Union`
- `ImageSet`
- `ConditionSet`
- `EmptySet`

A crucial advantage is that `solveset()` can preserve an unresolved component in a `ConditionSet` instead of presenting a partial collection of roots as though it were necessarily complete.

Its real and complex domains also differ explicitly.

For instance, solving \\(e^x=1\\) over the real numbers produces a different solution set from solving it over the complex numbers.

Sources:

`https://docs.sympy.org/latest/modules/solvers/solvers.html`

`https://docs.sympy.org/latest/modules/solvers/solveset.html`

### 7.3 Linear and nonlinear systems

`linsolve()` handles exact symbolic linear systems, including systems that have parameterized solution families.

It can operate on systems represented through equations, augmented matrices, or matrix/vector pairs.

`nonlinsolve()` handles supported nonlinear equation systems, including systems involving polynomial and certain nonpolynomial expressions.

It supports positive-dimensional systems, where solutions can depend on free parameters rather than being a finite collection of isolated numerical points.

These capabilities connect to the exact polynomial infrastructure, including elimination and Gröbner bases.

The resulting mathematical problem may nevertheless be intractable, or the available algorithms may not fully resolve its symbolic structure.

### 7.4 Numerical nonlinear solutions

`nsolve()` provides numerical root finding for systems that cannot conveniently be solved analytically.

It uses mpmath numerical machinery and supports arbitrary-precision calculations where appropriate.

Its properties differ materially from analytical solvers:

- The initial guess can determine which root is found.
- Numerical convergence is not guaranteed.
- Singular Jacobians and poorly scaled systems can cause difficulties.
- A successful solution is not evidence that all roots have been identified.
- Complex solutions require appropriate numerical initialization.

Consequently, `nsolve()` is a numerical root-finding tool, not a complete global nonlinear solver or optimization system.

### 7.5 Inequalities and symbolic conditions

SymPy provides `solve_univariate_inequality()`, `reduce_inequalities()`, and related functions for supported inequalities.

It can derive intervals and conditions on one variable, combine certain inequality constraints, and represent unresolved conditions symbolically.

General multivariate real algebraic inequalities are much more difficult, and the inequality solvers have important restrictions on the forms they can handle.

`reduce_inequalities()` should not be mistaken for a complete implementation of unrestricted real quantifier elimination.

Source: `https://docs.sympy.org/latest/modules/solvers/inequalities.html`

### 7.6 Integer and Diophantine equations

The `diophantine()` subsystem solves several specific families of integer equations.

Supported classes documented by SymPy include:

- Linear Diophantine equations.
- General binary quadratic equations.
- Certain homogeneous ternary quadratic equations.
- Extended Pythagorean equations.
- General sums of squares.

The solver classifies the problem and invokes the corresponding specialized algorithms, often producing parameterized integer solutions.

This represents a meaningful capability beyond applying a real-valued solver and filtering its output for integers.

It is not a complete solver for arbitrary integer polynomial constraints.

Source: `https://docs.sympy.org/latest/modules/solvers/diophantine.html`

## 8. Calculus, analytical transformations, and differential equations

### 8.1 Symbolic differentiation

SymPy's differentiation system handles explicit and nested mathematical expressions, higher-order derivatives, partial derivatives, symbolic functions, and implicit differentiation through appropriate transformations.

Important interfaces include `diff()`, `Derivative`, `jacobian()`, `hessian()`, and matrix/array differentiation mechanisms.

An important architectural capability is the derivation of analytical sensitivities for multiple outputs and multiple parameters.

For example, if a model is represented as a vector-valued function

\\[ F:\mathbb{R}^{n}\longrightarrow\mathbb{R}^{m}, \\]

SymPy can construct the symbolic Jacobian

\\[ J\_{ij}(x)=\frac{\partial F_i}{\partial x_j}. \\]

The resulting expressions can then be simplified, factored, subjected to common-subexpression elimination, and translated to numerical functions.

The same applies to higher derivatives and Hessians, where computational cost and resulting expression complexity permit.

This is symbolic differentiation of the mathematical representation. It is distinct from tracing the execution of arbitrary Python or NumPy programs, as automatic-differentiation frameworks do.

### 8.2 Integration algorithms

SymPy supports definite and indefinite symbolic integration through `integrate()` and `Integral`.

The integration system incorporates several classes of algorithms, including:

- Elementary polynomial and rational integration.
- Pattern-based integration methods.
- Extensions related to the Risch integration algorithm.
- Heuristic Risch integration.
- Integration involving special functions.
- Meijer G-function-based methods for supported integrals.
- Manual integration methods that can produce more conventional derivations.

`manualintegrate()` and related integration-step facilities are particularly useful when the intermediate mathematical reasoning is itself relevant.

Failure to produce a closed form does not imply that the integral has no closed form; algorithmic support varies by integrand.

SymPy can preserve the unevaluated integral or, where applicable, evaluate it numerically.

Source: `https://docs.sympy.org/latest/modules/integrals/integrals.html`

### 8.3 Limits, asymptotic expansions, and finite differences

SymPy offers:

- Symbolic limits, including directional and infinite limits.
- Taylor, Laurent, and supported generalized series expansions.
- Big-O remainder representations through `Order`.
- Formal power series via `fps()`.
- Fourier series representations.
- Symbolic sequences and sequence limits.
- Finite-difference weights and derivative approximations.

The `gruntz` algorithm is particularly relevant to asymptotic-limit evaluation involving nested transcendental expressions.

Finite-difference utilities such as `finite_diff_weights()` and `as_finite_difference()` provide symbolic derivative-discretization machinery.

These can generate numerical approximation formulas without hand-deriving each stencil.

However, an algebraically derived finite-difference formula does not automatically establish stability, convergence, suitable boundary treatment, or optimal discretization for a numerical PDE.

Sources:

`https://docs.sympy.org/latest/modules/series/series.html`

`https://docs.sympy.org/latest/modules/series/series_class.html`

`https://docs.sympy.org/latest/modules/calculus/index.html`

### 8.4 Integral transforms

SymPy supports analytical integral transforms including:

| Transform                  | Typical mathematical role                                                  |
| -------------------------- | -------------------------------------------------------------------------- |
| Laplace / inverse Laplace  | Differential equations, initial-value problems, control systems            |
| Fourier / inverse Fourier  | Frequency-domain representation and signal analysis                        |
| Mellin / inverse Mellin    | Scale transforms and special-function analysis                             |
| Hankel / inverse Hankel    | Radially symmetric transformations                                         |
| Sine and cosine transforms | Transform representations under particular symmetry or boundary conditions |

The transform system can return associated convergence conditions and retain unevaluated transforms when necessary.

This is particularly valuable when the convergence domain is integral to the mathematical result. A formal transform expression should not be assumed valid for every value of its parameters.

Transform operations interact with special functions, symbolic integration, distributions such as the Dirac delta, and ODE-solving workflows.

Source: `https://docs.sympy.org/latest/modules/integrals/integrals.html`

### 8.5 Ordinary differential equations

`dsolve()` handles a range of analytically solvable ordinary differential equations and some systems.

The ODE module provides a classification-and-hint architecture.

`classify_ode()` identifies applicable methods, while `dsolve(..., hint=...)` allows specific solution methods to be selected.

Supported methods include appropriate subclasses of:

- Separable, exact, Bernoulli, and linear first-order ODEs.
- Riccati-type and homogeneous equations.
- Linear constant-coefficient systems.
- Euler-type equations.
- Variation of parameters and undetermined coefficients.
- Selected special-function solutions.
- Power-series methods.
- Some Lie-group-based and conservation-related methods.

A useful characteristic of the hint system is that methods can return solutions retaining unevaluated integrals, allowing integration to be addressed separately.

`checkodesol()` can evaluate whether a proposed expression satisfies a differential equation within the checking algorithm's capabilities.

The classification mechanism is also an extension point for additional ODE-solving methods.

Source: `https://docs.sympy.org/latest/modules/solvers/ode.html`

### 8.6 Partial differential equations

`pdsolve()` handles selected classes of PDEs, with documented solver methods concentrated on particular first-order linear forms.

SymPy also provides additive and multiplicative separation-of-variables utilities.

It can represent arbitrary symbolic partial derivatives, derive PDE expressions, transform terms, and manipulate boundary or initial-condition expressions even when no analytical PDE solution method applies.

These capabilities are distinct from solving general nonlinear PDEs numerically.

Source: `https://docs.sympy.org/latest/modules/solvers/pde.html`

### 8.7 Recurrence relations and symbolic summation

SymPy also works with discrete-time equations and recurrence relations.

Relevant capabilities include `rsolve()` and the concrete summation subsystem:

- Solving supported linear recurrences.
- Symbolic finite and infinite sums.
- Symbolic finite and infinite products.
- Gosper's algorithm for hypergeometric summation.
- Related algorithms for hypergeometric summation and recurrence manipulation.

These operations connect symbolic algebra with discrete dynamical systems, combinatorics, and algorithmic summation.

Sources:

`https://docs.sympy.org/latest/modules/solvers/solvers.html`

`https://docs.sympy.org/latest/modules/concrete.html`

## 9. Special functions, holonomic functions, and advanced analytical representations

### 9.1 Special-function infrastructure

SymPy has a wide-ranging special-function subsystem encompassing functions such as:

- Gamma, beta, polygamma, and factorial-related functions.
- Bessel and Hankel functions.
- Airy functions.
- Error functions.
- Elliptic integrals and elliptic functions.
- Zeta and related number-theoretic functions.
- Orthogonal polynomials.
- Hypergeometric functions.
- Meijer G-functions.
- Selected spherical and angular functions.

These objects support mathematical operations appropriate to their families, including identities, simplification, differentiation, series, and numerical evaluation.

This can allow mathematical derivations to remain exact even when their results are not expressible in elementary functions.

Source: `https://docs.sympy.org/latest/modules/functions/special.html`

### 9.2 Hypergeometric and Meijer G representations

The hypergeometric and Meijer G subsystems deserve particular attention because they provide relatively general symbolic forms capable of representing many special functions and integrals.

`hyper()` and `meijerg()` are not merely alternatives for printing a mathematical result.

They can serve as intermediate mathematical representations for identifying transformations, integrating expressions, converting among special functions, and deriving asymptotic or other analytical properties.

`hyperexpand()` can rewrite supported hypergeometric expressions into more familiar special functions.

The applicability of identities depends on parameters, convergence, and analytic continuation, so transformations cannot be interpreted as universally valid real-valued simplifications.

### 9.3 Holonomic functions

One of SymPy's more advanced and easily overlooked subsystems is `sympy.holonomic`.

A holonomic, or D-finite, function satisfies a linear differential equation with polynomial coefficients:

\\[ p_0(x)f(x)+p_1(x)f'(x)+\cdots+p_r(x)f^{(r)}(x)=0. \\]

SymPy represents such functions using a differential operator that annihilates the function, together with appropriate initial-condition information.

The important insight is that the function may be manipulated through its defining differential equation instead of requiring a familiar closed-form expression.

The subsystem supports operations and conversions involving:

- Addition and multiplication of holonomic functions.
- Differentiation and integration.
- Supported algebraic compositions.
- Conversion between holonomic functions and recurrence relations.
- Conversion to and from certain known special-function representations.
- Series-based evaluation and related transformations.

Holonomic representations can be especially powerful for algorithmic manipulation of special functions, recurrence systems, and analytical expressions that are not naturally managed through elementary-function identities.

The module has documented restrictions and should not be interpreted as a universal symbolic differential-equation solver.

Sources:

`https://docs.sympy.org/latest/modules/holonomic/index.html`

`https://docs.sympy.org/latest/modules/holonomic/about.html`

`https://docs.sympy.org/latest/modules/holonomic/represent.html`

The significance of these advanced mathematical representations is architectural: SymPy supports multiple representations of related mathematical objects, and the most productive representation can change as the required operation changes. General expressions, polynomial rings, special functions, and holonomic operators each expose different algorithms.

## 10. Symbolic matrices, arrays, tensors, and differential geometry

An important distinction in SymPy is that explicit matrices, symbolic matrix expressions, N-dimensional arrays, indexed expressions, and abstract tensors are separate but partly interoperable representations. They expose different mathematical operations and avoid different forms of computational overhead.

### 10.1 Matrix expressions without materializing entries

`sympy.matrices.expressions` provides `MatrixSymbol`, `MatrixExpr`, `MatMul`, `MatAdd`, `Inverse`, `Transpose`, `Trace`, `Determinant`, `BlockMatrix`, and related objects.

Unlike an explicit `Matrix`, `MatrixSymbol("A", n, n)` represents an abstract matrix of a given shape. Operations can remain symbolic without constructing \\(n^2\\) individual elements.

This permits representation and manipulation of expressions such as

\\[ \operatorname{tr}\left(A^{-1}BC^\mathsf{T}\right) \\]

without generating every entry of the product.

The system supports symbolic matrix differentiation, structural matrix rewrites, and conversion to explicit representations when required.

The distinction is especially useful when matrix dimensions are large or symbolic, or when matrix-level identities are more important than individual scalar components.

However, `MatrixExpr` is not equivalent to NumPy's lazy execution infrastructure. It expresses mathematical operations; an eventual numerical runtime must perform the concrete computations.

Source: `https://docs.sympy.org/latest/modules/matrices/expressions.html`

### 10.2 N-dimensional arrays and array-expression algebra

SymPy provides explicit `Array`, `ImmutableDenseNDimArray`, and sparse array representations.

Core array operations include:

- `tensorproduct()`
- `tensorcontraction()`
- `tensordiagonal()`
- `permutedims()`
- `derive_by_array()`

The complementary `sympy.tensor.array.expressions` module represents such operations without expanding them.

Notable classes include `ArraySymbol`, `ArrayTensorProduct`, `ArrayContraction`, `ArrayDiagonal`, and `PermuteDims`.

A particularly valuable feature is conversion among indexed, array, and matrix representations:

- `convert_indexed_to_array()`
- `convert_matrix_to_array()`
- `convert_array_to_matrix()`

For example, an indexed summation representing matrix multiplication can become an `ArrayContraction` over a tensor product, and a recognized array contraction can be converted back to matrix multiplication.

These conversions create a bridge between scalar index notation and higher-level linear algebra. They can expose opportunities for structural simplification without expanding the complete component expression.

Not every array expression has an equivalent compact matrix expression, and symbolic conversions should not be assumed lossless for arbitrary custom semantics.

Sources:

`https://docs.sympy.org/latest/modules/tensor/array.html`

`https://docs.sympy.org/latest/modules/tensor/array_expressions.html`

### 10.3 Indexed notation and Einstein summation

`IndexedBase`, `Indexed`, and `Idx` provide index-aware symbolic representations.

They support mathematical expressions involving array subscripts, symbolic dimensions, and summation conventions.

This is relevant to symbolic tensor contractions and code generation because an indexed expression can retain information about loop indices and implied summations that would disappear in a fully expanded scalar expression.

For suitable indexed expressions, code printers and code-generation facilities can derive explicit loops for contracted indices.

The representation is not a complete tensor compiler: dependence analysis, optimal loop ordering, memory layout, fusion, and hardware-specific scheduling remain outside its general guarantees.

Source: `https://docs.sympy.org/latest/modules/tensor/indexed.html`

### 10.4 Abstract tensor algebra and symmetry canonicalization

`sympy.tensor.tensor` supports tensors defined by index types, tensor heads, tensor indices, symmetries, and contraction rules.

Relevant objects include `TensorIndexType`, `TensorIndex`, and `TensorHead`.

These abstractions help represent covariant and contravariant indices, metric relationships, and tensors whose indices obey specified permutation symmetries.

SymPy also provides tensor canonicalization algorithms. In particular, `canon_bp()` and related combinatorial mechanisms can canonicalize tensor expressions under index permutation symmetries.

This can identify that two apparently different tensor expressions are mathematically equivalent because of permitted index exchanges and dummy-index renaming.

The connection to group theory is significant: tensor canonicalization uses permutation-group machinery rather than relying on ad hoc textual index renaming.

Sources:

`https://docs.sympy.org/latest/modules/tensor/tensor.html`

`https://docs.sympy.org/latest/modules/combinatorics/tensor_can.html`

### 10.5 Vector calculus and differential geometry

SymPy includes several distinct geometric frameworks:

| Subsystem              | Role                                                                                                                  |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `sympy.vector`         | Symbolic vector fields, coordinate systems, gradient, divergence, curl, coordinate transformations                    |
| `sympy.physics.vector` | Time-dependent reference frames, kinematics, velocities, accelerations, dyadics                                       |
| `sympy.diffgeom`       | Coordinate systems on manifolds, differential forms, vector fields, Lie derivatives, differential-geometric operators |

The distinction is mathematical rather than merely organizational.

Vector calculus primarily concerns operations on scalar and vector fields in coordinate systems. Mechanics vectors additionally encode reference-frame relationships and time-dependent orientation. Differential geometry represents objects such as forms and vector fields on coordinate patches.

The differential-geometry subsystem also exposes routines for deriving Christoffel symbols, Riemann and Ricci tensor components from metrics.

These modules can support analytical derivation, but they are not general substitutes for specialized computational geometry, numerical differential geometry, or general-relativity simulation software.

Sources:

`https://docs.sympy.org/latest/modules/vector/fields.html`

`https://docs.sympy.org/latest/modules/physics/vector/vectors.html`

`https://docs.sympy.org/latest/modules/diffgeom.html`

## 11. Sets, symbolic logic, number theory, and combinatorics

### 11.1 Mathematical sets as symbolic solution representations

The sets module provides first-class representations of finite and infinite collections:

`FiniteSet`, `Interval`, `Union`, `Intersection`, `Complement`, `ProductSet`, `ImageSet`, `ConditionSet`, and `Range`.

These can represent results that ordinary lists of numerical solutions cannot adequately describe.

For example, a periodic transcendental equation may have a countably infinite solution set, while an unresolved equation can be retained as a `ConditionSet`.

Set operations can remain symbolic if the relevant membership, ordering, or emptiness conditions cannot be determined.

This is particularly important for the `solveset()` architecture: the structure of the solution is itself represented mathematically, instead of being flattened into a finite list of candidate values.

Source: `https://docs.sympy.org/latest/modules/sets.html`

### 11.2 Boolean algebra and satisfiability

`sympy.logic` implements propositional logic and Boolean algebra.

Capabilities include Boolean expression construction, conversion to conjunctive and disjunctive normal forms, simplification, Boolean minimization, and propositional satisfiability checking.

Important functions include:

`to_cnf`, `to_dnf`, `simplify_logic`, `SOPform`, `POSform`, `satisfiable`.

The Boolean logic subsystem can use SAT-solving algorithms and has optional integrations with external SAT backends.

It is useful for symbolic propositions, logical simplification, Boolean-function minimization, and reasoning about finite propositional constraints.

However, SAT over propositions is distinct from full satisfiability modulo theories (SMT). SymPy does not thereby acquire a complete solver for arbitrary nonlinear arithmetic, arrays, bitvectors, or quantified formulas.

Sources:

`https://docs.sympy.org/latest/modules/logic.html`

`https://docs.sympy.org/latest/contributing/dependencies.html`

### 11.3 Number theory

`sympy.ntheory` provides substantial integer and modular-arithmetic functionality.

Principal families include:

| Domain              | Capabilities                                                                    |
| ------------------- | ------------------------------------------------------------------------------- |
| Primes              | Primality testing, prime generation, prime-counting functionality, sieves       |
| Factorization       | Integer factorization, divisor enumeration, multiplicative arithmetic functions |
| Modular arithmetic  | Congruences, modular inverses, Chinese remainder theorem                        |
| Residues            | Quadratic residues, modular square roots, primitive roots                       |
| Discrete logarithms | Algorithms for supported multiplicative groups                                  |
| Integer equations   | Selected Pell-type and Diophantine methods                                      |
| Continued fractions | Construction, expansion, periodicity, rational approximation                    |

These are substantive mathematical algorithms, not merely wrappers around Python integer arithmetic.

The number-theory subsystem is useful for exact mathematical investigations and algorithmic prototyping. It should not automatically be regarded as a cryptographic implementation: constant-time execution, side-channel resistance, and cryptographic security guarantees require separate evaluation.

Source: `https://docs.sympy.org/latest/modules/ntheory.html`

### 11.4 Combinatorics and permutation groups

The combinatorics subsystem handles structured discrete objects, including permutations, permutation groups, partitions, generating objects, and finite groups.

Notable facilities include:

- `Permutation` and `PermutationGroup`.
- Group order, orbits, stabilizers, and membership calculations.
- Schreier–Sims algorithms and base/strong-generating-set representations.
- Named finite groups and permutation-group constructions.
- Integer partitions, set partitions, and combinatorial enumeration.
- Selected finitely presented groups and related algebraic structures.

The group-theoretic algorithms are directly relevant to other SymPy functionality, including tensor canonicalization and Galois-group computations.

This illustrates the value of the library's breadth: apparently separate mathematical subsystems reuse common exact-algebra and group-theory machinery.

Source: `https://docs.sympy.org/latest/modules/combinatorics/perm_groups.html`

### 11.5 Discrete transforms and convolution

`sympy.discrete` includes symbolic discrete transforms such as FFT, inverse FFT, number-theoretic transforms, and related convolution operations.

These are useful where exact arithmetic and symbolic coefficient manipulation matter.

They serve a different purpose from heavily optimized array-oriented FFT libraries such as FFTW, pocketfft, or vendor-specific FFT implementations.

Source: `https://docs.sympy.org/latest/modules/discrete.html`

### 11.6 Symbolic geometry

`sympy.geometry` supports symbolic geometric objects and operations such as points, lines, rays, segments, circles, ellipses, polygons, intersections, geometric relationships, and convex hulls.

It is particularly oriented toward exact and symbolic planar geometry.

A significant advantage is that geometric answers may contain algebraic expressions instead of approximate coordinates. This can preserve relationships that are lost under numerical rounding.

Its geometry support is not equivalent to a comprehensive computational geometry kernel for robust three-dimensional solids, mesh operations, CAD topology, or industrial geometric modeling.

Source: `https://docs.sympy.org/latest/modules/geometry/index.html`

## 12. Probability, statistics, and stochastic processes

The `sympy.stats` subsystem represents random variables and their mathematical relationships symbolically.

### 12.1 Symbolic probability expressions

SymPy supports discrete and continuous random variables, probability distributions, densities, cumulative distribution functions, expectations, conditional probabilities, variances, covariances, and related operations.

Important constructs include:

`P`, `E`, `variance`, `covariance`, `density`, `where`, `given`, and `sample`.

Probability models can retain symbolic parameters. A probability or expectation may be derived as a symbolic formula rather than evaluated at a fixed numerical parameter value.

For example, a distribution with symbolic rate or shape parameters can participate in analytical expressions that are subsequently differentiated or simplified.

### 12.2 Joint distributions and dependence

The subsystem also supports multivariate and joint-distribution representations, conditional random variables, and calculations involving explicitly modeled statistical dependence.

This differs from treating every variable as independently sampled numerical data.

A symbolic joint distribution can support reasoning about conditional probabilities and analytical expectations when the necessary density or probability relationships are known.

The feasibility of deriving a closed form depends on the distributions, support, and complexity of the required integrals or sums.

### 12.3 Stochastic processes

SymPy 1.14 includes symbolic process representations such as:

- `DiscreteMarkovChain`
- `ContinuousMarkovChain`
- Bernoulli processes
- Poisson processes
- Brownian motion
- Gamma processes

The Markov-chain facilities can express transition probabilities, state spaces, and associated symbolic probability questions.

These capabilities are distinct from generic statistical fitting packages. The emphasis is on mathematical process representations and analytical properties, not large-scale stochastic simulation infrastructure.

Source: `https://docs.sympy.org/latest/modules/stats.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 12.4 Relationship to numerical statistical libraries

SymPy's strengths here are symbolic probability calculations, exact distributions, and analytical derivations.

SciPy, NumPy, and specialized probabilistic-programming libraries serve different roles in high-throughput sampling, fitting, numerical inference, diagnostics, and computation over large datasets.

SymPy can complement these libraries by deriving formulas that are then numerically evaluated, but symbolic representation alone does not provide a general-purpose inference engine.

## 13. Mathematical physics, mechanical systems, and control theory

SymPy's physics modules provide domain-level abstractions that can generate and manipulate complete mathematical models. These are more than collections of prewritten physical formulas.

### 13.1 Classical mechanics and multibody dynamics

`sympy.physics.mechanics` provides a symbolic mechanics framework based on entities such as:

- `ReferenceFrame` and `Point`
- `Particle` and `RigidBody`
- Inertia dyadics and mass properties
- `dynamicsymbols`
- Generalized coordinates and generalized speeds
- Forces, torques, loads, and actuators
- Joints, kinematic relationships, and constraints

It supports the derivation of equations of motion through both Kane's method and Lagrange's method.

The `System` class supplies a higher-level representation of multibody systems containing bodies, joints, constraints, loads, and actuators. Its `form_eoms()` interface delegates equation formation to an appropriate mechanics method.

This produces symbolic dynamical relationships that can be represented in forms such as

\\[ M(q,p)\dot u=f(q,u,t,p), \\]

where \\(q\\) denotes generalized coordinates, \\(u\\) generalized speeds, and \\(p\\) model parameters.

Important capabilities include holonomic and nonholonomic constraints, dependent and independent coordinates, kinematic differential equations, and extraction of mass matrices and forcing vectors.

`SymbolicSystem` can represent explicit first-order state equations, implicit combined equations, and implicit dynamics with separate kinematics. It can also identify algebraic constraints requiring DAE treatment.

The separation between the physical model and the derived equations is consequential. It allows the same domain-level model to participate in analytical transformations, local linearization, parameter studies, and numerical code generation.

Sources:

`https://docs.sympy.org/latest/modules/physics/mechanics/api/system.html`

`https://docs.sympy.org/latest/explanation/modules/physics/mechanics/kane.html`

`https://docs.sympy.org/latest/explanation/modules/physics/mechanics/lagrange.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 13.2 Constrained-system linearization

The mechanics linearization machinery can derive linearized systems around a specified operating point, including supported constrained systems.

For appropriate systems, the result takes the form

\\[ \delta\dot x=A\delta x+B\delta r. \\]

This creates a direct relationship between nonlinear symbolic equations of motion and linear state-space analysis.

The availability of exact expressions for \\(A\\) and \\(B\\) can be particularly valuable for examining parameter dependence, stability conditions, and local system sensitivities.

The distinction between ordinary linearization and constrained-system linearization matters. Dependent coordinates, algebraic constraints, and singular operating configurations may change the valid mathematical formulation.

Source: `https://docs.sympy.org/latest/modules/physics/mechanics/linearize.html`

### 13.3 Control-system analysis

`sympy.physics.control` supports symbolic linear time-invariant systems.

The principal representations are:

| Representation                               | Main capability                                          |
| -------------------------------------------- | -------------------------------------------------------- |
| `TransferFunction`                           | Continuous-time transfer functions in the Laplace domain |
| `Series`, `Parallel`, `Feedback`             | Symbolic interconnection of SISO systems                 |
| `TransferFunctionMatrix`                     | MIMO transfer-function systems                           |
| `MIMOSeries`, `MIMOParallel`, `MIMOFeedback` | MIMO interconnections                                    |
| `StateSpace`                                 | State-space models represented by \\(A,B,C,D\\) matrices |

The subsystem supports operations including transfer-function composition, poles and zeros, stability analysis, and state-space controllability and observability calculations.

Conversions between supported state-space and transfer-function representations provide an additional bridge between analytical model derivation and control-system mathematics.

The important limitation is the LTI scope. The presence of a symbolic `StateSpace` object should not be interpreted as general-purpose nonlinear control, optimal control, MPC, or a complete numerical simulation framework.

Sources:

`https://docs.sympy.org/latest/modules/physics/control/control.html`

`https://docs.sympy.org/latest/modules/physics/control/lti.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation

+1



### 13.4 Biomechanics and continuum mechanics

SymPy also exposes more specialized applied-mechanics facilities.

The biomechanics package includes symbolic representations for biomechanical actuation and musculotendon modeling, intended to integrate with the larger mechanics framework.

The continuum-mechanics subsystem includes symbolic structural-analysis capabilities, notably beam models using singularity functions to represent loads and derive shear forces, bending moments, slopes, and deflections.

These modules can replace substantial hand derivation for supported model classes, although their functionality is much narrower than a general-purpose finite-element or multiphysics framework.

Sources:

`https://docs.sympy.org/latest/explanation/modules/physics/biomechanics/biomechanics.html`

`https://docs.sympy.org/latest/modules/physics/continuum_mechanics/index.html`

### 13.5 Quantum mechanics and quantum information

`sympy.physics.quantum` represents quantum states, operators, Hilbert spaces, and related algebraic operations.

Important abstractions include bra-ket notation, `Ket`, `Bra`, `Operator`, tensor products, commutators, anticommutators, and adjoints.

`qapply()` applies supported operators to states, while `represent()` converts abstract quantum objects to matrix or other explicit representations when a suitable basis is available.

Additional facilities cover spin algebra, qubits, gates, quantum circuits, Fourier transforms, and selected demonstrations of quantum algorithms.

The main value is the symbolic treatment of operator and state relationships. SymPy does not thereby become a hardware-oriented quantum execution platform or a large-scale optimized quantum-circuit simulator.

Source: `https://docs.sympy.org/latest/modules/physics/quantum/index.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 13.6 Additional physics capabilities

Other notable subsystems include:

- High-energy physics: gamma-matrix and related relativistic algebra.
- Optics: supported geometrical and Gaussian-optics calculations.
- Hydrogen-atom functions and other analytic quantum-mechanical models.
- Physical quantities, dimensions, units, and unit systems.

The units module is especially relevant to dimensional reasoning. It represents dimensions and physical quantities symbolically and supports unit conversions through `convert_to()` and related abstractions.

The library's `UnitSystem` and `DimensionSystem` distinguish physical dimensions from unit scaling.

These capabilities can support exact dimensional relationships, but they are not a complete replacement for every unit-aware numerical-array, measurement-uncertainty, or dimensional-validation framework.

Sources:

`https://docs.sympy.org/latest/modules/physics/hep/index.html`

`https://docs.sympy.org/latest/modules/physics/optics/index.html`

`https://docs.sympy.org/latest/modules/physics/units/index.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



## 14. Numerical evaluation, generated functions, and compiled code

This is one of SymPy's most important architectural integration areas.

SymPy can derive and transform mathematics symbolically and then hand the resulting expressions to numerical execution mechanisms. Those mechanisms have different semantics, dependencies, and performance characteristics.

### 14.1 Numerical evaluation with `evalf()`

`evalf()` evaluates supported symbolic expressions to a requested decimal precision.

It is built around arbitrary-precision numerical arithmetic, with mpmath as a required dependency.

Capabilities include numerical evaluation of elementary and special functions, numerical integrals, certain infinite sums and products, and expressions containing algebraic numbers.

The evaluation machinery can increase working precision to compensate for loss of significant digits in some cancellation-sensitive calculations.

However, precision is not the same as mathematical correctness under all conditions. Ill-conditioned expressions, nonconvergence, ambiguous branches, and evaluation limits still matter.

`nsimplify()` solves a different problem: it attempts to recognize a plausible exact symbolic expression from an approximate numerical value. Such recognition is heuristic and is not a proof that a measured or computed approximation equals the proposed exact expression.

Source: `https://docs.sympy.org/latest/modules/evalf.html`

### 14.2 `lambdify()`: bridge to numerical libraries

`lambdify()` translates symbolic expressions into callable Python functions backed by a selected numerical namespace.

Representative backends include:

| Backend          | Main significance                                                     |
| ---------------- | --------------------------------------------------------------------- |
| `math` / `cmath` | Python scalar real/complex functions                                  |
| `mpmath`         | Arbitrary-precision numerical evaluation                              |
| `numpy`          | Vectorized NumPy array calculations                                   |
| `scipy`          | Numerical functions, including special functions unavailable in NumPy |
| `numexpr`        | Evaluation using NumExpr's supported expression operations            |
| `jax`            | Functions expressed through JAX-compatible numerical operations       |
| `tensorflow`     | TensorFlow-compatible numerical functions                             |
| `cupy`           | CuPy-compatible GPU-array functions                                   |

These are numerical-library integrations. SymPy does not itself implement NumPy vectorization, JAX compilation, GPU kernels, or TensorFlow's execution runtime.

A typical derivation-to-execution pattern is:

```
from sympy import Matrix, cos, lambdify, sin, symbolsx, y = symbols("x y")residual = Matrix([    x**2 + sin(y),    x*y + cos(x),])jacobian = residual.jacobian([x, y])evaluate = lambdify(    (x, y),    (residual, jacobian),    modules="numpy",    cse=True,)
```

The example illustrates a single numerical callable returning both residual and Jacobian expressions, with common-subexpression elimination requested during function generation. It has not been executed here.

This facility can eliminate the need to manually duplicate analytical derivatives and their corresponding numerical implementations.

A key performance distinction is that `lambdify()` generates ordinary numerical function calls. For array expressions, the backend and expression structure determine whether operations are fused, vectorized, broadcast, or materialized as intermediate arrays.

For JAX specifically, producing a JAX-compatible function does not guarantee that every mathematical expression will support all desired JIT compilation, automatic differentiation, or device execution behaviors.

Source: `https://docs.sympy.org/latest/modules/utilities/lambdify.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation

+1



### 14.3 Code printers versus complete code generators

SymPy distinguishes several levels of code transformation.

Symbolic expressions and mathematical representations

Expression transformations

Algebraic normalization, differentiation, CSE, rewriting, explicit or indexed representation

Code printers

Generate language-specific expressions and assignments

Numerical dispatch

Generate callables through `lambdify` and external libraries

Code generators

Generate compilable routines, source files, and declarations

Autowrap / JIT

Compile supported routines or generate native callables

The code printers support language-specific expression output, including C, Fortran, Rust, JavaScript, Julia, Octave/Matlab, and other formats.

For instance, `rust_code()` emits Rust expressions or assignments using Rust-oriented function mappings and power operations.

This is useful when the symbolic part of a computational system is written in Python but the numerical execution kernel is implemented in another language.

A source-code printer is not the same as a complete production compiler. It does not automatically provide ABI design, package integration, data ownership, error handling, parallel execution, or complete numerical semantics for every symbolic object.

Source: `https://docs.sympy.org/latest/modules/printing.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 14.4 The code-generation AST

`sympy.codegen.ast` supplies structured program-level representations in addition to mathematical expressions.

This includes constructs such as:

`Assignment`, `Variable`, `Declaration`, `CodeBlock`, `For`, `While`, and typed objects.

The AST allows mathematical code generation to be expressed above the level of raw string concatenation.

For example, assignments can be represented structurally, analyzed for dependencies, ordered where appropriate, and printed into supported target languages.

`CodeBlock` also provides functionality such as common-subexpression elimination across represented assignments.

The distinction is important: code-generation AST nodes represent program organization and assignments, whereas ordinary `Expr` objects represent mathematics.

Source: `https://docs.sympy.org/latest/modules/codegen.html`

### 14.5 Full source generation: `codegen()` and `make_routine()`

`sympy.utilities.codegen` operates at a higher level than code printers.

`codegen()` and `make_routine()` can generate source routines and supporting files. The documented `codegen()` languages include C, Fortran 95, and Octave/Matlab.

By comparison, Rust support in the printing subsystem generates Rust code fragments; it should not be conflated with complete automatic Rust project generation or compilation.

This distinction clarifies what SymPy can provide natively and what integration tooling must supply.

### 14.6 `autowrap()`, `ufuncify()`, and native compilation

`sympy.utilities.autowrap` provides facilities for converting eligible symbolic expressions into compiled callable functions.

Important interfaces are:

- `autowrap()`: Generate, compile, import, and return a callable.
- `binary_function()`: Associate a generated implementation with a symbolic function.
- `ufuncify()`: Generate a NumPy-style elementwise numerical function.

Supported mechanisms use backends such as Cython and `f2py`, together with an external compiler.

`ufuncify()` can avoid some Python/NumPy intermediary overhead by compiling supported scalar operations into numerical loops or ufunc implementations.

The advantage depends on expression complexity, number of elements, array shapes, memory layout, backend, and compilation costs.

The official documentation contains illustrative cases where generated compiled functions outperform a NumPy-backed `lambdify()` result, but those timings should not be generalized to arbitrary numerical workloads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 14.7 LLVM JIT support

SymPy also exposes an LLVM-related integration through `sympy.printing.llvmjitcode`.

With `llvmlite` available, `llvm_callable()` can generate native callable functions from supported expressions.

This offers a lower-level compilation route separate from `lambdify()`'s use of external mathematical-function libraries.

Its support is bounded by the implemented LLVM translation functionality; it should not be interpreted as a general-purpose JIT backend for every SymPy object or symbolic algorithm.

Source: `https://docs.sympy.org/latest/contributing/dependencies.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 14.8 Numerical-semantic boundaries

Converting exact symbolic expressions into numerical code can change the practical behavior of calculations.

Important considerations include:

- Floating-point nonassociativity.
- Singularities and cancellation.
- Complex-valued branches and principal values.
- Integer versus floating-point division.
- Backend-specific `Piecewise` evaluation.
- Domain errors and exceptional values.
- Differences between scalar and array evaluation.
- Availability of numerical implementations for specialized SymPy functions.

A mathematically valid transformation need not preserve every floating-point rounding behavior, and a symbolically equivalent expression need not have the same numerical stability.

This is especially relevant when applying expansion, simplification, reassociation, or CSE before compiled execution.

The strongest general pattern is to separate mathematical validity, numerical conditioning, and execution efficiency as distinct properties to establish.

### 14.9 Numerically aware symbolic code optimization

A less obvious but important capability is `sympy.codegen.rewriting`.

This subsystem supports optimization rules that recognize mathematical expressions better implemented using specialized numerical functions.

For instance:

\\[ e^x-1 \longrightarrow \operatorname{expm1}(x) \\]

and

\\[ \log(1+x)\longrightarrow \operatorname{log1p}(x). \\]

These transformations can improve accuracy near zero because direct subtraction or addition may lose significant floating-point digits.

The `optimize()` function applies collections of `Optimization` rules, including the provided `optims_c99` collection. Custom optimization classes can also be defined.

Other transformations can expand small integer powers into multiplication or introduce expressions supported more efficiently by a particular target-language standard.

This provides an important distinction from generic `simplify()`:

- Algebraic simplification generally seeks a mathematically simpler form.
- Code-generation optimization seeks a representation with desirable execution and numerical properties for a particular target.

SymPy provides mechanisms for both, but determining the best transformation sequence remains dependent on the numerical semantics and target backend.

Source: `https://docs.sympy.org/latest/modules/codegen.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



## 15. Parsing, printing, custom mathematical objects, and interactive tooling

### 15.1 Mathematical input and parsing

`sympy.parsing` supports several input formats:

| Input                                | Interface or subsystem | Important boundary                                                    |
| ------------------------------------ | ---------------------- | --------------------------------------------------------------------- |
| Python-like mathematical expressions | `parse_expr()`         | Supports configurable transformations, but uses Python evaluation     |
| LaTeX mathematical expressions       | `parse_latex()`        | ANTLR and Lark backends with different parsing behavior               |
| Mathematica expressions              | `parse_mathematica()`  | Converts supported syntax; not a complete Mathematica interpreter     |
| Maxima expressions                   | `parse_maxima()`       | Parses supported Maxima syntax                                        |
| Autolev mechanics models             | `parse_autolev()`      | Translates supported legacy mechanics syntax into SymPy-oriented code |
| C and Fortran source                 | Specialized parsers    | Experimental or dependency-constrained functionality                  |

`parse_expr()` supports transformations such as implicit multiplication, automatic symbol creation, and conversion of certain mathematical notations.

However, the official documentation states that `parse_expr()` uses `eval` and must not be used on unsanitized input. Similarly, `lambdify()` uses `exec`. Neither is a secure parser or executor for arbitrary untrusted expressions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation

+1



### 15.2 LaTeX parser architectures

`parse_latex()` has two documented parser backends.

The ANTLR backend is the default. It can recover from some malformed inputs, but the documentation cautions that this behavior can silently ignore part of an expression.

The newer Lark backend is stricter, supports ambiguity detection, and exposes mechanisms for grammar and transformer customization.

However, Lark parsing remains experimental in SymPy 1.14, with incomplete support for some mathematical constructs.

This matters because mathematical notation is not always unambiguous. For example, printed expressions can omit semantic information about whether an identifier represents a function, a variable, or a particular mathematical object.

Source: `https://docs.sympy.org/latest/modules/parsing.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 15.3 The Autolev integration

The Autolev parser is a particularly specialized integration.

It translates supported Autolev 4.1 syntax into SymPy mechanics-oriented Python code, offering a migration route for a domain-specific multibody dynamics language.

Its `include_pydy` option can also generate PyDy-related simulation code where applicable.

The implementation does not support every Autolev construct, and its documentation includes specific limitations on statements, options, and numerical behavior.

Source: `https://docs.sympy.org/latest/explanation/modules/physics/mechanics/autolev_parser.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 15.4 Mathematical and executable output formats

SymPy offers several output representations:

- Human-readable plain-text and Unicode mathematical formatting.
- LaTeX and MathML.
- Constructor-oriented representations via `srepr()`.
- Target-language code, including C and Rust.
- Specialized printers for external mathematical systems and SMT-LIB-related expressions.

Printing is extensible. Custom symbolic classes can define their own specialized output behavior, and custom printer subclasses can implement further target representations.

It is important not to conflate serialization with presentation. A pretty-printed formula or LaTeX string does not necessarily preserve every piece of information needed for an exact structural round trip.

Source: `https://docs.sympy.org/latest/modules/printing.html`

### 15.5 Extending SymPy with custom mathematical functions

SymPy's custom-function architecture is one of its more valuable extension mechanisms.

A defined `Function` subclass can participate in the same symbolic operations as built-in functions.

Depending on the desired behavior, relevant hooks include:

| Extension mechanism                | Purpose                                                            |
| ---------------------------------- | ------------------------------------------------------------------ |
| `eval()`                           | Automatic evaluation for explicitly supported arguments            |
| `fdiff()`                          | Derivatives of function arguments                                  |
| `_eval_derivative()`               | Derivative behavior for suitable non-`Function` expression classes |
| `_eval_evalf()`                    | Numerical evaluation                                               |
| `_eval_is_positive`, related hooks | Mathematical assumptions and property reasoning                    |
| `_eval_rewrite()`                  | Representation-changing symbolic rewrites                          |
| `_eval_expand_*()`                 | Supported expansion behavior                                       |
| `doit()`                           | Deliberate evaluation of a symbolic operation                      |
| Custom printer hooks               | LaTeX, mathematical formatting, or generated code                  |

These hooks allow a mathematical object to participate in differentiation, assumptions, transformations, and numerical code generation without implementing an independent symbolic system.

There is an important correctness and performance consideration: automatically evaluating too aggressively in `eval()` can produce excessive expression construction, recursive evaluation, and difficult-to-control simplification.

SymPy's official guidance recommends keeping automatic evaluation conservative and using separate operations for more expensive transformations.

The assumptions hooks must also respect three-valued reasoning; returning `False` when a property is merely unknown can produce incorrect downstream mathematical results.

Source: `https://docs.sympy.org/latest/guides/custom-functions.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 15.6 Plotting and interactive mathematics

SymPy provides symbolic plotting facilities for:

- Explicit two-dimensional functions.
- Parametric curves.
- Implicit equations and inequalities.
- Three-dimensional surfaces.
- Three-dimensional parametric curves and surfaces.

Plot rendering is primarily delegated to Matplotlib, with limited text-based plotting available.

Interactive integration also includes IPython, Jupyter, MathJax display, and the `isympy` shell.

These are presentation and exploration capabilities; plotting is not a substitute for analytical verification or specialized scientific visualization pipelines.

Source: `https://docs.sympy.org/latest/modules/plotting.html`

## 16. Dependencies, acceleration backends, and ecosystem boundaries

### 16.1 Package and runtime characteristics

For SymPy 1.14.0:

| Property                                                 | Status                                                                |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| Python requirement                                       | Python 3.9 or later                                                   |
| License                                                  | BSD                                                                   |
| Required mathematical dependency                         | `mpmath`                                                              |
| Main implementation                                      | Predominantly pure Python                                             |
| Platform-specific native binary required by SymPy itself | No                                                                    |
| Native mathematical acceleration                         | Available through selected optional integrations                      |
| Separate development version                             | 1.15.0.dev documentation exists; not included as stable functionality |

PyPI distributes a platform-independent Python wheel for SymPy 1.14.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 16.2 Important optional dependencies and companion systems

| Package or system | Role                                                                            | Boundary                                                                   |
| ----------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| mpmath            | Required arbitrary-precision numerical mathematics                              | Numerical evaluation engine, not symbolic expression infrastructure        |
| gmpy2             | Accelerates supported integer and rational arithmetic                           | Does not replace SymPy's complete symbolic runtime                         |
| python-flint      | Native exact algebra and selected domain-matrix operations                      | Availability depends on coefficient domain and operation                   |
| SymEngine         | C++ symbolic mathematics engine with Python bindings                            | Experimental, limited backend integration within SymPy                     |
| NumPy             | Array-oriented evaluation of generated functions                                | Numerical backend, not a symbolic algebra engine                           |
| SciPy             | Special-function implementations and scientific algorithms                      | Numerical computation outside SymPy's primary responsibility               |
| NumExpr           | Expression evaluation using a dedicated numerical engine                        | Supports a constrained operation set                                       |
| JAX               | Accelerated numerical execution and automatic-differentiation framework         | SymPy translates compatible expressions; JAX owns compilation and autodiff |
| TensorFlow        | Numerical tensor execution                                                      | Separate numerical framework                                               |
| CuPy              | GPU-array execution                                                             | Depends on supported translations and GPU environment                      |
| Cython / `f2py`   | Compilation and Python wrapping of generated routines                           | Build-time and compiler dependencies                                       |
| llvmlite          | LLVM-backed callable generation                                                 | Limited to supported translation paths                                     |
| Matplotlib        | Plot rendering                                                                  | Visualization backend                                                      |
| PyDy              | Simulation and visualization of dynamics derived using SymPy mechanics          | Separate dynamics application/tooling layer                                |
| SageMath          | Broad mathematical software ecosystem incorporating SymPy among other libraries | Separate, much larger collection of mathematical systems                   |

Sources:

`https://docs.sympy.org/latest/contributing/dependencies.html`

`https://docs.sympy.org/latest/modules/polys/domainmatrix.html`

`https://docs.sympy.org/latest/modules/physics/mechanics/api/system.html`

### 16.3 `gmpy2` acceleration

The optional `gmpy2` package provides access to GMP-backed arbitrary-precision integer arithmetic.

SymPy automatically uses it in supported core and polynomial-domain operations when installed.

This may indirectly benefit factorization, simplification, exact matrices, and other features that use polynomial arithmetic.

The extent of the benefit depends on how much time a workload spends manipulating large integers and rationals versus traversing expression trees, performing symbolic dispatch, or generating intermediate representations.

Source: `https://docs.sympy.org/latest/contributing/dependencies.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 16.4 SymEngine integration: important experimental boundary

SymEngine is an independent C++ symbolic mathematics engine with Python bindings.

SymPy 1.14 documents the `USE_SYMENGINE=1` environment option as an experimental integration.

Critically, the documentation states that the optional backend is presently used only in selected areas, notably `sympy.physics.mechanics` and `sympy.liealgebras`, along with certain direct interfaces through `sympy.core.backend`.

This is not a general guarantee that enabling SymEngine transparently accelerates every SymPy operation.

The documentation explicitly warns that some functionality may not work correctly with the experimental backend enabled.

SymEngine can be relevant when compiled symbolic manipulation is desirable, but its direct Python API and SymPy's experimental backend mode are distinct integration approaches.

Sources:

`https://docs.sympy.org/latest/contributing/dependencies.html`

`https://symengine.org/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



### 16.5 Why backend substitution is not always straightforward

There are at least four different kinds of acceleration:

1. Arithmetic acceleration: Faster integer, rational, polynomial, or matrix arithmetic through GMP or FLINT.
2. Symbolic-engine substitution: Using an alternative symbolic representation or computational engine, such as SymEngine.
3. Numerical evaluation acceleration: Evaluating generated expressions through NumPy, NumExpr, JAX, or GPU libraries.
4. Compiled expression execution: Compiling generated numerical formulas to native routines.

These optimize fundamentally different costs.

A workload dominated by expensive Gröbner basis calculations may benefit from exact-algebra improvements while seeing little benefit from JAX.

A workload dominated by repeated evaluation of already-derived analytical formulas may benefit from compiled numerical execution while seeing little benefit from faster symbolic manipulation.

A workload dominated by expression construction and rewriting may be sensitive to SymPy's object model and transformation choices instead.

The distinction makes it possible to assess performance architecture without treating every accelerator as an interchangeable replacement.

## 17. Capability interactions and consequential design distinctions

The most powerful applications of SymPy often rely on combining several of its mathematical subsystems.

### 17.1 Symbolic residuals and analytical numerical kernels

Consider a family of nonlinear mathematical problems:

\\[ F(x,p)=0 \\]

where \\(x\\) is a state vector and \\(p\\) a parameter vector.

A symbolic representation can support:

- Construction of the residual vector \\(F\\).
- Derivation of \\(J=\partial F/\partial x\\).
- Derivation of \\(\partial F/\partial p\\).
- Structural inspection of sparsity.
- Algebraic simplification and common-subexpression elimination.
- Generation of numerical residual and Jacobian functions.

This can replace separate hand-maintained algebraic implementations of residuals, derivatives, and sensitivity equations.

It does not automatically supply the best nonlinear algorithm, linear solver, preconditioner, scaling method, sparsity-aware data structure, or convergence strategy.

The benefit is mathematical consistency and shared symbolic derivation, with the numerical solver remaining a distinct component.

### 17.2 Exact algebra followed by numerical specialization

For problems containing polynomials, rational functions, and algebraic parameters, the representations can be staged:

\\[ \text{general expressions} \\;\longrightarrow\\; \text{polynomial/field representations} \\;\longrightarrow\\; \text{exact transformations} \\;\longrightarrow\\; \text{numerical expressions}. \\]

The intermediate exact-algebra stage can enable transformations that are difficult to reproduce reliably using approximate floating-point coefficients.

Examples include exact cancellation, algebraic factorization, elimination of variables, and identification of singularity conditions.

The numerical conversion can then be postponed until the mathematical structure is adequately resolved.

The tradeoff is that exact algebra may itself be computationally costly, particularly when polynomial degree, number of variables, or coefficient sizes grow.

### 17.3 Symbolic mechanics to control and numerical execution

A multibody mechanics model can conceptually pass through several native capabilities:

\\[ \text{bodies/joints/loads} \rightarrow \text{equations of motion} \rightarrow \text{linearized state-space model} \rightarrow \text{control analysis}. \\]

Alternatively, the nonlinear equations can be translated into numerical functions for use by an external ODE or DAE solver.

This illustrates the significance of SymPy's domain modeling: high-level physical abstractions can feed general symbolic mathematics and lower-level numerical interfaces.

The integration is not entirely automatic. State conventions, constraints, mass-matrix singularity, initial conditions, and numerical integration requirements must remain mathematically consistent.

### 17.4 Indexed representations and numerical loop generation

The combination of abstract matrix expressions, indexed expressions, array contractions, and language printers permits numerical calculations to be represented at several abstraction levels.

A calculation may start as \\(AB\\), be expressed through an indexed summation, transformed into an array contraction, or emitted as loops in supported code-generation contexts.

These conversions are useful for bridging mathematical descriptions and executable operations.

However, they should not be confused with a fully optimizing tensor compiler. Choices such as BLAS dispatch, tiling, vectorization, memory scheduling, fusion, and accelerator placement often belong to other systems.

### 17.5 Holonomic representations and recurrences

The holonomic subsystem supports a different pattern:

\\[ \text{special function} \longleftrightarrow \text{annihilating differential operator} \longleftrightarrow \text{coefficient recurrence}. \\]

For supported functions, representing the defining differential relation can be more productive than manipulating increasingly complicated closed-form expressions.

This may support symbolic series construction, transformations, and evaluation techniques unavailable through ordinary expression simplification.

### 17.6 Principal limitations to preserve

Several distinctions recur across SymPy's capability families:

| Distinction                                        | Practical implication                                                                          |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Structural equality versus mathematical equality   | An equality test may not prove equivalence                                                     |
| Unknown assumptions versus false assumptions       | `None` must not be interpreted as a negative result                                            |
| Exact algebra versus numerical approximation       | Algebraic correctness does not guarantee numerical stability                                   |
| General `Expr` versus specialized domains          | Representation choice affects available algorithms and efficiency                              |
| `Matrix` versus `MatrixExpr` versus `DomainMatrix` | Entry expansion, algebraic abstraction, and coefficient domains serve different needs          |
| Analytical solver versus numerical root finder     | Different guarantees regarding convergence, completeness, and domains                          |
| Symbolic differentiation versus program autodiff   | SymPy differentiates represented mathematics, not arbitrary executed code                      |
| Code printer versus compiled kernel                | Generation of source text is distinct from producing a deployable runtime                      |
| Optional backend versus universal acceleration     | Acceleration is specific to supported operations and representations                           |
| Symbolic model versus numerical simulation         | Equations must still be discretized, integrated, or solved under appropriate numerical methods |

These distinctions are especially important because many SymPy operations preserve mathematically meaningful unresolved expressions instead of failing outright.

An unevaluated integral, derivative, `ConditionSet`, or abstract matrix operation may be a correct symbolic result, but it is not evidence that the computation has been fully resolved.

## 18. Less prominent capabilities worth knowing

A few additional subsystems deserve mention because they are less visible in SymPy's introductory material.

| Subsystem                    | Capability                                                                               |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| `sympy.liealgebras`          | Root systems, Cartan types, and related Lie-algebra structures                           |
| `sympy.categories`           | Mathematical category-theory objects and diagrams                                        |
| `sympy.polys.polytools`      | Specialized polynomial decomposition, transformations, and root algorithms               |
| `sympy.combinatorics.galois` | Permutation groups used in algebraic Galois-group reasoning                              |
| `sympy.crypto`               | Classical cipher algorithms primarily useful for mathematical and educational purposes   |
| `sympy.codegen.rewriting`    | Numerically aware mathematical rewrites for generated code                               |
| `sympy.printing.smtlib`      | Conversion of supported symbolic expressions to SMT-LIB-oriented textual representations |
| `sympy.testing`              | Project-provided testing helpers and mathematical verification utilities                 |

The existence of a specialized module does not imply feature parity with dedicated systems. For example, SMT-LIB printing is not an embedded SMT solver, and the classical cryptography functionality is not a modern cryptographic security library.

Source: `https://docs.sympy.org/latest/reference/index.html`

## 19. Primary-source navigation guide

The following references are especially useful for deeper investigation. They are direct URLs rather than embedded hyperlinks.

| Topic                            | Primary source                                                            |
| -------------------------------- | ------------------------------------------------------------------------- |
| Full API reference               | `https://docs.sympy.org/latest/reference/index.html`                      |
| Core expressions                 | `https://docs.sympy.org/latest/modules/core.html`                         |
| Assumptions                      | `https://docs.sympy.org/latest/guides/assumptions.html`                   |
| Simplification                   | `https://docs.sympy.org/latest/modules/simplify/simplify.html`            |
| Rewriting and CSE                | `https://docs.sympy.org/latest/modules/rewriting.html`                    |
| Polynomial algorithms            | `https://docs.sympy.org/latest/modules/polys/reference.html`              |
| Coefficient domains              | `https://docs.sympy.org/latest/modules/polys/domainsintro.html`           |
| Algebraic number fields          | `https://docs.sympy.org/latest/modules/polys/numberfields.html`           |
| Polynomial-backed series         | `https://docs.sympy.org/latest/modules/polys/ringseries.html`             |
| Domain matrices                  | `https://docs.sympy.org/latest/modules/polys/domainmatrix.html`           |
| Equation solving                 | `https://docs.sympy.org/latest/modules/solvers/solveset.html`             |
| ODE solving                      | `https://docs.sympy.org/latest/modules/solvers/ode.html`                  |
| Formal power series              | `https://docs.sympy.org/latest/modules/series/formal.html`                |
| Matrix expressions               | `https://docs.sympy.org/latest/modules/matrices/expressions.html`         |
| Array-expression algebra         | `https://docs.sympy.org/latest/modules/tensor/array_expressions.html`     |
| Abstract tensor algebra          | `https://docs.sympy.org/latest/modules/tensor/tensor.html`                |
| Holonomic functions              | `https://docs.sympy.org/latest/modules/holonomic/index.html`              |
| Symbolic mechanics               | `https://docs.sympy.org/latest/modules/physics/mechanics/api/system.html` |
| Symbolic control systems         | `https://docs.sympy.org/latest/modules/physics/control/control.html`      |
| Symbolic probability             | `https://docs.sympy.org/latest/modules/stats.html`                        |
| Code generation and optimization | `https://docs.sympy.org/latest/modules/codegen.html`                      |
| Numerical backend translation    | `https://docs.sympy.org/latest/modules/utilities/lambdify.html`           |
| Custom symbolic functions        | `https://docs.sympy.org/latest/guides/custom-functions.html`              |
| Dependencies and integrations    | `https://docs.sympy.org/latest/contributing/dependencies.html`            |
| Project releases                 | `https://github.com/sympy/sympy/releases`                                 |

Documentation URL clarification: The formal-power-series page is `https://docs.sympy.org/latest/modules/series/formal.html`, rather than the `series_class.html` path included earlier in §8.3.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sympy.org\&sz=32)

SymPy 1.14.0 documentation



## Overall assessment

SymPy is best understood as a general mathematical representation and transformation system, not just a collection of symbolic calculus functions.

Its most architecturally significant capabilities extend well beyond `diff()`, `integrate()`, and `solve()`:

- Exact coefficient domains, polynomial rings, and computational algebra algorithms.
- Domain-aware and fraction-free symbolic linear algebra.
- Abstract matrix, indexed array, and tensor-expression representations.
- Mathematical assumptions and symbolic solution sets.
- Holonomic functions, advanced special functions, and formal series.
- Domain-level mechanics and control-system equation generation.
- Analytical derivative generation, expression optimization, and numerical-code emission.
- Extension mechanisms that let new mathematical functions participate in SymPy's existing operations.

Taken together, these capabilities allow mathematical models to move among high-level domain abstractions, exact algebraic representations, analytical transformations, and executable numerical implementations without requiring every intermediate representation or mathematical algorithm to be independently developed.

The principal constraint is that SymPy does not automatically select the optimal mathematical representation, analytical algorithm, or numerical execution strategy for every workload. Its specialized subsystems are powerful precisely because their semantics, applicable domains, and computational costs differ. A sophisticated use of SymPy depends on recognizing those distinctions and exploiting the appropriate native mathematical machinery.