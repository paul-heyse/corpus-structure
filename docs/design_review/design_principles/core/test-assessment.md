# Assessing test code and test evidence

**Version 1.2 · 2026-10-23 · Assessment guidance.** Repository- and domain-agnostic
companion to the [core principles](design-principles.md), selected through the repository's
standard declaration. Applicable domain profiles continue to supply scientific and other
correctness obligations.

## Purpose and standing

Assess whether the test system provides trustworthy, discriminating and understandable evidence
of intended behavior, with proportionate maintenance and execution costs. Tests are software
with architectural responsibilities, and they are instruments for challenging other software.
Reuse can improve their consistency while making their evidence share the same mistake.

This companion interprets FP-01–FP-07 and their refinements for test scope. The full selected
design standard remains the assessment basis: consider every core foundation, relevant
operational refinements and applicable domain obligations. This companion supplements that
assessment; its topics do not define its limits. Assess the full design standard, giving
particular attention to its efficiency-oriented principles without displacing the others.
Apply those principles primarily through static architectural review; structural efficiency
findings do not require a profiling or benchmark campaign.

It adds no principle, MUST, gate, score, coverage threshold, prescribed test mix or obligation to
inspect every companion topic.
It neither relaxes the core nor turns test code into a miniature production architecture.
Use relevant questions in bounded audits and reviews; ordinary test editing does not initiate
either. The repository binding owns invocation, output and follow-up routes.

The subject includes test bodies and their support system: fixtures, builders, generators,
oracles, assertions, doubles, reference data, collection/configuration and resource lifecycles.
Read production contracts and dependencies far enough to understand the claim and its evidence.
Distinguish scenario construction, exercised behavior, observation, expected-result derivation
and assertion. Ordinary values, functions and modules can express these responsibilities.

## 1. Independence relative to the claim — FP-02, FP-04, FP-06

Ask which plausible production mistake a test can still detect given everything it shares with
production. Independence concerns the relevant failure mechanism, not different files, languages,
libraries or function names. Tests with different assurance roles can legitimately share different
things; do not require every test to independently verify every dependency.

| Reused production element | Assess its role in the evidence |
|---|---|
| Domain types, enums and public interfaces | Normally exercise the real contract. Use independent expectations when representation, admitted values or completeness are the subject. |
| Constructors and builders | Useful for valid downstream setup. A rejection test may need raw or malformed inputs so construction does not reject or repair the case before it reaches the intended boundary. |
| Calculations, validators and decision logic | Useful dependencies when testing another responsibility. Computing both actual and expected results through the logic under test cannot independently establish that logic's correctness. |
| Schemas, registries and constants | Useful for mechanical conformance or generated case selection. Cases and expectations derived entirely from the declaration cannot independently establish its semantic correctness or completeness. |

A serializer/deserializer round trip can establish agreement while both paths implement the
same wrong format. Differential paths can share a backend or data error. Conservation checks
can constrain a result without uniquely identifying the correct one. Describe the property
established and the material blind spots rather than treating any technique as sufficient by name.

An independent oracle is explicitly allowed by FP-04. It is not a second writable production
authority merely because it repeats a mathematical relation or uses another representation.
Assess its derivation, scope, assumptions and maintenance. A copied implementation can preserve
the same error; a small analytic case, independently derived reference or different method may
provide a stronger challenge. No universal second implementation is required.

## 2. Consolidation that preserves meaning — FP-01, FP-03, FP-04, FP-06

Judge sharing by responsibility and consequences. Repeated resource management, scenario
construction or contract assertions may benefit from one maintained implementation. A few repeated
expected values or setup lines may make an example easier to inspect and independently challenge.
Similarity or line count alone establishes neither harmful duplication nor useful abstraction.

A helper earns its scope when consumers share a coherent need and can use it without importing
unrelated policy or infrastructure. Inspect actual adoption: an apparently canonical helper that
consumers bypass may provide little consistency, while forcing superficially similar cases into
one configurable framework can entangle unrelated responsibilities. Local functions, narrow
builders and shared modules are alternatives; a universal test framework is not the default.

Keep case-defining inputs and expected behavior visible at an appropriate call site. Defaults
can hide irrelevant setup, but should not silently determine the property being checked. Follow
relevant defaults, generated values and transformations when judging an assertion. Parameterization,
loops and property generators are legitimate when their cases, properties and failures remain
understandable; straight-line syntax is not a universal requirement.

Test-support boundaries follow assurance responsibilities and shared needs. They need not mirror
production modules. A substantial independent reference model can be justified by a concrete
assurance purpose; assess the parallel maintenance it introduces rather than rejecting or
requiring it categorically.

## 3. Shared helper reliability and correlated evidence — FP-02, FP-05, FP-06

Distinguish a helper setup failure, a shared assertion correctly revealing a broad production
regression, and a defective helper silently accepting many incorrect results. Fan-out alone
does not tell whether consolidation is beneficial or dangerous. Investigate which consumer claims
depend on the helper and whether failures identify the shared cause.

Scrutiny is proportional to consequential logic and the evidence depending on it. Comparators,
reference calculations, protocol fakes and generators may need independent known cases or controls
that show rejection of incorrect results. This does not require a test for every trivial fixture,
recursive verification machinery or a mutation campaign. Source reasoning can settle a question;
use probes when a material uncertainty remains.

Tolerance selection, normalization, sorting, filtering and error handling deserve attention when
they can erase an important difference. A shared comparison mechanism can be useful without one
blanket acceptance tolerance for unrelated quantities or algorithms.

## 4. Assertions that discriminate — FP-02, FP-05, FP-06

Identify what would make the test fail and whether that corresponds to its stated behavior.
Merely reaching a path, obtaining a nonempty result or accepting several incompatible outcomes
may leave the important contract unchecked. Conversely, assert only the details needed for the
claim: unrelated output equality can make tests brittle without strengthening that claim.

For a negative case, establish that it reaches the intended boundary and fails for the intended
reason. For generated cases, consider whether construction, filtering or discard behavior removes
the difficult inputs. For snapshots and golden data, inspect provenance and the basis for accepting
updates; regenerating expectations from current output alone does not establish correctness.

Counterexamples, deliberate perturbations or mutation tools can reveal weak assertions where
useful. Coverage shows execution over its named scope; it does not establish fault sensitivity,
oracle independence or completeness. A missing assertion becomes a finding when connected to a
supported obligation and a consequential behavior it would fail to distinguish, not an arbitrary
quota for cases or branches.

## 5. Contract coupling and doubles — FP-01, FP-02, FP-06

Consider a behavior-preserving implementation change. Which tests need editing, and why? Tests
usually protect consumed behavior; some legitimately protect an internal algorithmic invariant,
allocation property or execution structure. Judge the observation against the protected contract,
not a blanket public-only rule or a ban on white-box tests.

A double's fidelity is relative to the claim. A simple fake may isolate a policy effectively while
providing little evidence about persistence, concurrency, native integration or a remote protocol.
Inspect consequential differences from the real boundary, appropriate contract or integration
coverage, and whether the double introduces its own unexamined decision rules. Neither mock counts
nor real-service counts establish quality. Avoid production changes whose only benefit is enabling
an elaborate test seam when a simpler boundary would preserve the supported behavior.

## 6. Isolation, replay and diagnosis — FP-05, FP-06, FP-07

Inspect ownership of mutable fixtures, temporary resources, stores, clocks, environment changes,
random sources, tasks and cleanup. Shared immutable preparation may be economical. Shared mutable
state can create order dependence, interference or stale evidence. Reuse must retain the validity
premises and lifecycle required by the scenario; fresh state may be part of what is being tested.

Reproducibility means failures can be explained and replayed where practical, not that every test
must use fixed inputs or serial execution. Preserve relevant seeds, cases and execution context for
randomized or concurrent exploration. Treat retries, skips and environment-dependent outcomes
according to the declared scope; do not silently convert missing required evidence into success.

Failure output should identify the scenario, expected property, actual result and relevant
parameters. A support layer that reduces every failure to an opaque Boolean loses diagnostic
value. Distinguish a setup failure from a failure to satisfy the product contract without masking
either. No mandatory logging framework or custom result schema follows from this guidance.

## 7. Domain fidelity and numerical evidence — FP-04, FP-05, applicable profiles

Keep units, conventions, reference conditions, validity envelopes, tolerance rationale and
scaled/unscaled interpretation explicit where they affect the claim. Test data need appropriate
provenance, generating method and applicability limits. An independent reference is still evidence
under assumptions, not proof or a guarantee of physical truth.

Distinguish solver status, numerical residual quality and physical validity. Derivative checks
need the approximation's step-size, conditioning and domain assumptions where material. Useful
metamorphic relations require a justified property and discriminating cases. Shared production
equations or data limit the independence of apparent reference comparisons.

Reuse common domain checks where warranted, with mechanism and case-specific acceptance meaning
kept understandable. In a process simulator, PS-07, PS-10 and PS-13 supply relevant obligations;
the repository selects the applicable profile. This companion neither adds a new scientific
campaign nor replaces the profile's requirements.

## 8. Execution cost in relation to assurance — FP-06, FP-07

Apply the selected efficiency-oriented principles, relevant operational refinements and
architectural heuristics primarily through static review of the test system. The governing
execution-fit criterion here is FP-07/A4. Judge whether representations, algorithms, access
paths, composition boundaries, preparation and resource lifecycles fit the testing
responsibilities, supported workloads and assurance claimed.

The following test-specific examples illustrate those principles. Consider what developers and
agents must instantiate to exercise a responsibility and what evidence the expense buys. Inspect
representative focused-test and broader qualification routes in source and configuration,
including preparation/build, discovery and collection, setup, execution, teardown, and failure
diagnosis or replay. A focused test with cheap assertions can still require substantial
unrelated preparation.

Look for avoidable dependency activation or compilation, repeated process/service startup,
oversized fixtures, repeated loading or conversion, redundant computation, incidental
serialization, contention and ineffective scheduling. Include generated and library-induced
work. Consider both individually expensive operations and small costs amplified across many
tests or frequent development iterations. These are inquiry leads, not presumed defects or
a mandatory checklist. Use relevant execution heuristics from the selected standard.

Real integration work, independent checks and fresh execution may be essential to the claim.
Evaluate possible savings while preserving required validation, isolation, independent
expectations, integration fidelity and applicable scientific obligations. Reuse immutable
preparation only while its validity premises hold; shared mutable state or stale cached
evidence can erase the benefit. Caching, broader fixture scope, doubles and concurrency are
not default remedies. Faster runs with weaker assertions or missing required cases do not
establish an equivalent improvement.

Explain structural causes and consequences in terms of the governing principles. Source
reasoning can establish avoidable amplification or poor execution fit without identifying the
dominant runtime bottleneck. Use targeted execution only to resolve consequential uncertainty
that source inspection cannot settle; do not initiate profiling or benchmark probes merely to
substantiate an otherwise established structural diagnosis. Claims about elapsed time, speedup
or capacity still need measurements under stated conditions. No universal test pyramid, runtime
threshold, full-suite execution or benchmark campaign follows. An inquiry may conclude that no
material efficiency shortfall was established, with its inspected scope and limits stated.

## Using the assessment

Follow representative evidence paths and credible changes or faults where they clarify the
question. Group manifestations only when their structural cause is shared. Explain whether a
problem can conceal defects, cause spurious failures, obstruct diagnosis or amplify maintenance
and execution costs. Preserve contrary evidence, hypotheses and unexamined scope. A passing suite
does not establish the quality of its evidence, and a static audit is not product qualification.

Finding organization and investigation depth remain flexible. Explain how the core architectural
foundations were investigated and which efficiency-oriented principles informed the judgments.
State material omissions or uncertainties; loading the standard alone does not establish
assessment, and no performance investigation or timing results are required. No exhaustive matrix
or finding per principle is required. Findings may arise directly from core/profile criteria without
a corresponding companion topic. Cite those criteria and the companion section where relevant.
The skill and binding own baseline, publication, finding identity and disposition; this companion
owns assessment criteria only.

## Background

The contextual treatment of sharing and readable examples is consistent with
[Software Engineering at Google, chapter 12](https://abseil.io/resources/swe-book/html/ch12.html),
particularly its discussion of test code sharing. Its suggested test mix is not adopted here.
[Google's test-logic guidance](https://testing.googleblog.com/2014/07/testing-on-toilet-dont-put-logic-in.html)
also distinguishes simple examples from nontrivial test utilities. These are explanatory sources;
the selected core and applicable profiles remain the governing standard.
