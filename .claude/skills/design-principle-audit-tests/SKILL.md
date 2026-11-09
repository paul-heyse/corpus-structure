---
name: design-principle-audit-tests
description: Audit test code, test evidence and shared test infrastructure against the full selected design standard, emphasizing efficiency-oriented principles through static architectural review and using the test-assessment companion to interpret the principles for test scope. Maintain a separate living diagnostic account. Use for an explicit test-scope audit or a test-focused diagnostic review prerequisite; ordinary test editing does not initiate an audit.
---

# Audit test design and evidence

Use AGENTS.md's validation judgment: expected gains generally need no demonstration of their size;
consider performance experiments for serious regression concerns. Numerical claims need measurement
support. Its design-stage guidance favors coherent replacements, affected consumer migration and
removal of superseded machinery within authorized scope.

Audit test code and its supporting system against the full selected design standard: core
foundations and operational refinements, applicable domain profiles and the repository binding.
The test-assessment companion supplements that standard; assessing its topics alone does not
constitute a design-principle audit. Test scope narrows the software examined, not the set of
design principles to consider.

Develop a current, evidence-grounded account of structural weaknesses. Assess the full design
standard, giving particular attention to its efficiency-oriented principles without displacing
the others. Diagnose causes and consequences without requiring a predetermined remedy, library
preference or test technique.

## Load the criteria and scope

Find the layered standard through repository instructions and standard.toml. Read the core
principles, heuristic companion, applicable domain profiles and repository binding. Load the
test-assessment companion selected by the core's test_assessment entry; it interprets the selected
principles for testing responsibilities. If that companion is unavailable, report the limitation
rather than inventing a standard or claiming a complete test-specific assessment. Loading criteria
does not initiate another audit.

Scope follows testing responsibilities, beyond directory names: inline tests, doctests, fixtures,
builders, generators, oracles, assertions, doubles, reference data and relevant collection,
execution configuration and resource lifecycle. Read production contracts and dependency paths
far enough to judge independence, coupling and supported obligations. A production cause can be
reported without authorizing its repair or expanding into a broad production audit.

The binding owns invocation and applicability to subsequent reviews. A test-only engagement
does not require a broad production audit. Mixed scope identifies the applicable accounts and
their limits. Ordinary implementation, test maintenance and process installation do not trigger
this audit or a full test campaign.

## Establish the account

In this repository, maintain [the test audit collection](../../../docs/design_review/test-audit/README.md)
under docs/design_review/test-audit/, following the
[binding](../../../docs/design_review/design_principles/binding/corpus-structure.md#test-code-design-principle-audit).
An empty scaffold establishes no audited baseline, findings or alignment evidence.

Identify the audited source commit, included uncommitted changes, date, applied standard and
companion versions, inspected scope and meaningful limits. Distinguish source from publication
revision. A refresh uses intervening test, production-contract, dependency and configuration
changes as leads, then follows affected responsibilities into unchanged code as needed. Revisit
earlier findings when their premises change. Inherited observations retain their evidence date
and applicability limits; the broad audit's baseline cannot substitute for this account's.

## Investigate evidence and architecture

Consider every core architectural foundation within the inspected test scope, following relevant
operational refinements and domain obligations. Examine responsibility boundaries, contract
stability, composition, domain meaning and authority, explicit constraints, local reasoning and
testability, and execution fit. Choose depth according to evidence and uncertainty; do not
restrict findings to issues named in the test companion. A finding may arise directly from a
core principle even when no companion section describes it.

Choose breadth and depth according to uncertainty. Representative evidence paths can connect
scenario construction, exercised behavior, observation, expected-result derivation and assertion.
Credible refactors, contract changes, new cases and faults can expose coupling or blind spots.
These are inquiry techniques, not a fixed tracing sequence or exhaustive matrix.

Apply the companion's distinctions when judging production reuse, deliberate duplication,
shared helpers, correlated failures, assertion strength, doubles, isolation, domain fidelity and
execution fit. Ask which relevant mistakes the test would still detect. Similar-looking code,
an import, a large fixture, many dependent failures or a passing suite alone establishes no
architectural verdict.

Read decisive sources, including material contrary evidence. Use source reasoning where it
settles the question and targeted probes where consequential uncertainty remains. Perturbations
or known-correct/incorrect controls can be useful; no mandatory mutation campaign, test for every
helper, full-suite execution, benchmark or additional assurance framework follows. Quantitative
claims require measurements under named conditions. Follow repository environment and acceptance
timing for any execution; library questions use its documentation research route.

## Emphasize efficiency-oriented design principles

Give particular attention to the selected standard's efficiency-oriented principles, refinements
and architectural heuristics, while continuing to assess all other applicable principles. In
this repository, FP-07/A4 supplies the governing execution-fit criterion.

Apply these criteria primarily through thoughtful static review of test code, support
infrastructure, dependencies and execution configuration. Examine whether representations,
algorithms, access paths, composition boundaries, preparation and resource lifecycles fit the
testing responsibilities and supported workloads. Companion §8 illustrates their application
to test scope.

Ask what work is necessary for the assurance claimed, what repeats because of incidental
architectural boundaries, and whether established preparation or guarantees can be preserved
while their validity premises hold. Consider repeated reconstruction, unnecessary dependencies
and data movement, unsuitable algorithms, excessive live state, and avoidable coordination or
recovery amplification. Use relevant heuristics selectively; this is not a checklist.

Establish findings through concrete structural causes and consequences. Static evidence can
demonstrate unnecessary work or poor execution fit without proving that a path is the dominant
runtime bottleneck. Preserve required validation, isolation, independent expectations,
integration fidelity and applicable scientific obligations. Shared preparation, caching, doubles
and concurrency require judgment about validity and failure behavior; none is a default remedy.

Use targeted execution only when it resolves a consequential uncertainty that source inspection
cannot settle. Do not initiate profiling or benchmark probes merely to substantiate an otherwise
established structural diagnosis. Quantitative claims about elapsed time, speedup or capacity
still require measurements under stated conditions.

## Publish diagnosis with clear ownership

Explain how the investigation addressed the core architectural foundations and which
efficiency-oriented principles informed its architectural judgments. Identify material omissions
and unresolved questions. Listing loaded documents does not demonstrate assessment. A brief
narrative suffices; no exhaustive principle matrix, finding per principle or performance
investigation is required. Findings cite governing core/profile criteria and, where relevant,
the test companion.

Distinguish demonstrated unnecessary work from suspected bottlenecks and measured performance.
Source evidence can establish repeated initialization or avoidable processing without timing
it; claims about elapsed time, speedup or capacity require measurements under stated conditions.

Use the shared [finding-writing guidance](../design-principle-audit/references/audit-writing.md).
Explain the claim at risk, structural cause, concrete consequence, known footprint, evidence,
uncertainty and relevant counterevidence. Distinguish established diagnosis from a suspected
wider footprint using the existing evidence vocabulary. A solution lead may help a later reviewer,
but the audit need not select a remedy, priority or implementation package.

Keep one primary home per finding across both audit collections. New test findings use the
binding's DTA-nnn identities; an existing broad finding retains its identity and home and is
linked, not copied or freshly dated. Preserve lineage across moves, splits and merges, and never
reuse retired IDs. Update this account in place; Git preserves prior accounts. Remove resolved
material only when current evidence establishes the correction, with closure evidence recoverable
through the removal commit. Link plans for scheduled disposition and progress rather than
maintaining a second execution ledger.

Use the shared coordination contract when delegation improves coverage or independent judgment.
Read-only contributors return sources, baseline, findings and limits; the coordinator reconciles
and publishes the account. Deliver its inspected baseline, material discoveries and coverage
limits. The account does not certify complete alignment, authorize repairs or automatically
start a solution review.
