---
id: ADR-0007
title: Separate diagnostic audit, solution review and independent completion assessment
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Repeated ambiguity in diagnostic ownership, review revisions or completion claims.
---

## Context

A broad diagnostic account, design solutioning, critique of recommendations and assessment of
completed scope answer different questions. Keeping them explicit improves focused reasoning
without turning ordinary implementation into a recurring architecture audit. Large library
skills also obscure the holistic capabilities that make a focused investigation valuable.

## Options

- Keep diagnosis, solutioning and completion assessment implicit in existing review turns.
- Add fixed pipelines and exhaustive gates, with duplicate output registers.
- Separate callable assessments with clear existing document owners (chosen).

## Decision

[DESIGN §2](../design/DESIGN.md#section-2) owns the process; the binding owns local mechanics.

- Refresh the applicable broad or test-scope diagnostic audit before a new diagnostic solution-review engagement. Use its previous
  source baseline and intervening changes to focus current codebase inspection. Maintain stable
  finding identities in flexible Markdown clusters; ordinary execution does not load this account.
- Test-only engagements use design-principle-audit-tests and a separate living test account,
  with independent baselines and stable DTA-nnn identities. Each finding has one primary home
  across both accounts. The test-assessment companion interprets the existing Core 3.3
  criteria; no new principles, gates or test campaign are introduced. Installing this
  process performs no audit. Copier protects authored content in both audit collections.
- The operator selects holistic, library-targeted, principle-focused or combined solution focus.
  Reviewers choose methods and depth; libraries are enabling hypotheses, not required adoption.
- Functional enhancement uses `plan-functional-extension-review` / `functional-extension-review`
  within the operator's selected outcome, workflow, subsystem or ecosystem. Explore useful product,
  developer, operator and research capabilities without requiring an audit finding, current caller
  or diagnostic audit. Principles shape realizations; `docs/functional_reviews/` owns proposals
  and recommendation-audit companions, and existing plans own selected scheduled scope.
- A requested recommendation audit accounts for all original recommendations and omissions in
  a net-change companion, and integrates a newly attributed principal review at the original path.
  Preserve its exact input in Git. Editorial dispositions never replace plan execution status.
  Functional-review audits preserve the value/opportunity lens alongside design assessment.
- A requested completion audit reconstructs accepted obligations across consumers and packages,
  distinguishing implementation, qualification and benefit evidence. Correct the same owning plan
  rather than adding another artifact. Audit authority alone does not authorize production repairs.
- These are deliberate requested or explicitly planned boundaries, without automatic slice
  audits, new roles, runtime hooks or mandatory probe campaigns. Keep the current core/profile
  criteria and independent architectural and semantic judgments.
- Optional repository-agnostic library overviews give capability orientation; Context7 and
  primary sources resolve consequential details. Retire active central
  library-skill selection and synchronization, retaining inactive reference identities as needed.
- Shared native role routing targets Codex; `.claude/skills` remains the tracked source exposed
  through `.agents/skills`. Existing accepted project ADRs remain immutable on template updates.

## Consequences

Scaffolded workflows and document ownership are Implemented policy; their effectiveness requires
actual use. Fresh projects receive empty audit scaffolds, not findings or conformance claims.
Copier preserves the living audit and project-owned overview index during future updates.
