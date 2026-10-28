---
name: plan-improvement-review
description: Review the remaining change footprint of an implementation plan or coordinated plan series for worthwhile design-principle alignment, general enhancements and execution improvements. Develop coherent amendments across materially affected components and consumers, judging benefits and integration burden. Use at requested or explicitly planned improvement boundaries; ordinary execution and claimed-completion assessment have separate workflows.
---

# Review plan improvements

Investigate how the remaining changes could produce a better system and a better route to
delivery. Give the selected change footprint comprehensive consideration, including opportunities
to improve design-principle alignment and the general quality and capabilities of affected
components. An improvement can be worthwhile on its own merits without directly advancing the
plan's functional target or being necessary to implement it.

Develop recommendations that fit coherently into the existing undertaking. A sound existing
approach, one focused amendment and several complementary improvements are all legitimate
conclusions. Use this at a requested or explicitly planned boundary; ordinary execution does
not initiate another review.

## Establish the remaining change footprint

Identify the plan or coordinated series, intended outcomes, accepted obligations, implemented
foundations and remaining work. Read the substantive target and reasoning alongside work tables
and checkpoints. For a series, understand the combined capability and relevant cross-plan
dependencies. Distinguish accepted design, implementation, evidence and proposals, including
relevant uncommitted changes.

Establish the footprint from responsibilities being revised, contracts being changed,
implementations and consumers requiring adaptation, and tests or operational paths undergoing
consequential modification. Components substantially changed to accommodate the plan belong in
scope even when their own capabilities are outside its functional target. File and package
boundaries provide navigation; the substance of the changes determines the inquiry.

Read current architectural owners and decisive code. Follow dependencies and adjacent consumers
far enough to understand opportunities and their consequences. Extending a recommended change
should have a concrete integration reason, such as completing a shared contract correction,
migrating its consumers or removing the mechanism it replaces. Discovering an opportunity does
not automatically bring every dependency into general exploration. State material coverage limits.

## Review for design-principle alignment improvements

Load the applicable standard through the repository's `standard.toml`: core principles,
efficient architecture heuristics, applicable profiles and their assessment guidance, and the
binding. When tests or test evidence are in scope, load the selected test-assessment companion.
Use the full applicable standard to inform judgment within the footprint, selecting relevant
questions and depth rather than producing an exhaustive checklist or verdict matrix.

Actively investigate opportunities for stronger alignment in both the remaining target design
and the affected existing components. Examine responsibilities, semantic authorities, domain
distinctions, contracts, composition, change locality, explicit structure and execution fit where
they bear on the work. Consider how affected tests establish behavior and how their setup and
dependencies support local reasoning. Look for improvements that a subsequent principle review
could reasonably recommend and that fit the changes already being undertaken.

Ground a recommendation in the actual responsibility, interaction or supported scenario and
explain the design consequence. Name relevant principle references and show how the amendment
improves the design; a principle label or preferred code shape alone is insufficient. Preserve
useful existing strengths and guarantees. Opportunities can improve an adequate design as well
as correct a demonstrated defect; a violation is not a prerequisite.

Current decisions and plan mechanisms explain the baseline and its commitments. Reconsider
stated design elements when a better amendment emerges, carrying forward reasoning whose
premises remain applicable. Identify consequential rule impacts as proposals for the existing
decision routes. This review has no broad diagnostic-audit prerequisite, does not refresh an
audit account, and does not substitute for a formal design review due under the binding.

## Explore useful possibilities

Use the clearer target, implementation experience and interactions across remaining packages
to discover opportunities. A changed fact or prior mistake is not required. Useful questions
include:

- What has become simpler, unnecessary or possible now that the combined target is clearer?
- Which planned mechanism or distinction no longer earns its integration burden?
- Could a revised responsibility or contract improve several affected consumers together?
- Which general enhancement would leave a substantially modified component more useful,
  coherent or easier to change, beyond the immediate feature?
- Could existing repository or library capabilities take fuller responsibility and remove
  surrounding machinery?
- Would different sequencing reveal a consequential assumption earlier, avoid an interim
  mechanism or make a coherent capability usable sooner?
- What could remain awkward or ineffective if every package were implemented exactly as written?

These are prompts for inquiry, not required sections or a sequence. Consider removal,
consolidation and better composition alongside additions. Use capability overviews for
orientation and Context7 followed by primary sources for consequential library or tooling
questions. Preserve concrete enabling mechanisms, source references and material limitations
when a recommendation depends on them.

## Judge the whole intervention

Assess benefits alongside implementation, migration, verification and continuing operational
burden. Explain why making the improvement as part of the remaining changes is worthwhile.
Shared change responsibilities, consumer migrations and verification surfaces can support a
combined correction; sharing a file or test suite alone does not establish that fit.

Judge scope by consequences. Substantial restructuring can be appropriate when it completes a
coherent correction within the footprint and its benefits justify disruption. A small edit can
introduce a much broader architectural commitment. Completed work matters through the effects
of changing it; prior effort alone does not settle the recommendation.

An improvement's independent value does not make it a separate undertaking. Distinguish proposals
whose principal work introduces capabilities, migrations or architectural replacements outside
the footprint and can be separated from the planned changes without compromising the proposed
correction. Report their value and the broader decision needed, keeping them distinct from
amendments recommended for this plan. Keep serious correctness problems visible even when
their remedies exceed the review's integration boundary.

Assess recommendations together. Individually attractive amendments can accumulate into a
different undertaking or create conflicting responsibilities and transition assumptions.
Use qualitative comparison and revealing scenarios; no change-size budget, scoring system,
recommendation quota or mandatory probe follows. Run a probe when it settles consequential
uncertainty. Quantitative benefit claims require measurements.

## Make recommendations usable

For a consequential amendment, explain the current approach, proposed behavior or responsibility
change, expected benefit and why it fits. Identify affected packages and consumers, material
prerequisites, preserved guarantees, intentional behavior changes and uncertainty that could
change the recommendation. Compare retaining the current approach with credible alternatives
where the choice matters. Challenge the amendment with a legitimate case that could expose lost
meaning, weakened guarantees, misplaced authority or disproportionate transition burden.

Give enough detail to locate the amendment within remaining work and identify suitable closure
evidence. Detailed implementation packages are useful when requested or needed to establish
feasibility. Separate consequence-based priority from prerequisite order and explain interacting
or alternative recommendations coherently.

Distinguish optional enhancements, alignment opportunities, observed defects and missing accepted
obligations. Preserve existing finding identities and their disposition owners. A proposed
improvement does not redefine completion or weaken acceptance; claimed-completion assessment
belongs to [plan-completion-audit](../plan-completion-audit/SKILL.md).

## Publish a review for subsequent plan revision

Publish a standalone document under the
[plan-improvement review conventions](../../../docs/plan_improvement_reviews/README.md).
Explain the date, inspected baseline, selected footprint, combined judgment, recommendations,
interactions and material limits. For a series, produce one coherent assessment of the selected
scope and link to the affected coordinator and supporting packages. Organize the document around
the reasoning; no mandatory report schema or separate mutable disposition ledger is needed.

Give recommendations stable references such as `I01` with explicit anchors for later plan
revision. Preserve existing source finding IDs and link to their disposition owners. Follow the
repository's evidence vocabulary; source inspection and reasoned proposals do not establish
tested behavior or measured benefits.

Review authorization covers publishing the assessment. Updating the plan from that document is
a separate instruction; conducting this review does not itself amend accepted design, scheduled
scope or progress, or authorize production changes. When plan revision is requested, use the
existing planning and decision routes and retain the review's references, reasoning and concrete
mechanisms at their relevant owners. No separate update skill or mandatory new planning cycle
is required. Routine implementation choices already within authorized scope remain ordinary
execution judgment. A requested broader redesign or capability inquiry can use
[design-review](../design-review/SKILL.md) or
[functional-extension-review](../functional-extension-review/SKILL.md). This review does not
automatically initiate those workflows or a completion audit.
