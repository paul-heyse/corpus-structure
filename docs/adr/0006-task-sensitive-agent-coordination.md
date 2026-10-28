---
id: ADR-0006
title: Delegate by task and strengthen evidence and review defaults within bounded workflows
status: accepted
date: 2026-10-28
supersedes: [ADR-0005]
superseded-by: null
design: [§2]
evidence: Implemented
revisit: Repeated delegation overhead, missed semantic contracts or runtime changes warrant revisiting role boundaries or review scope.
---

## Context

The project needs explicit domain meaning and independent architectural assessment without a
standing modeling exercise for ordinary implementation. Reusable roles help when their benefits
justify coordination; a general preference for parallelism, repeated startup tours and implicit
escalation can add handoffs or obscure uncertainties. Native model settings need explicit effort
and workable escalation routes without treating unmeasured quality expectations as evidence.

[DESIGN §2](../design/DESIGN.md#section-2) owns this workflow. ADR-0002's review cadence and the
binding's single finding-disposition owner remain in force. This record carries forward ADR-0005's
bounded model-adequacy criteria, six roles, skill pairs and existing verification owners. It replaces
its general preference for parallel execution and previous evidence/review model defaults.

## Options

1. **Keep previous defaults and broad parallel preference.** Smaller evidence workers and familiar
   instructions keep configuration stable, but leave context and escalation costs implicit.
2. **Require a fixed pipeline, caps or calibration campaign.** More uniform control adds obligations
   without evidence that they serve this single-operator project.
3. **Task-sensitive coordination and stronger review defaults (chosen).** Preserve reusable roles
   and bounded reviews while improving task context, evidence and routing without new ceremonies.

## Decision

- Adopt core/template 3.3 and code-intelligence guidance 1.4, preserving principle IDs and historical review versions.
- An explicit, coherent domain model must govern behavior wherever domain meaning is established
  or interpreted. FP-04/A2 assess model adequacy and authoritative realization. A deferral cannot
  waive an in-scope MUST gap for supported behavior, even with correct current outputs.
- Model operations as well as concepts; own invariants, contextual bindings and representation
  contracts. Ordinary types, relations and domain functions suffice; no modeling framework is
  prescribed. Keep architectural and fidelity judgments independent.
- FP-07/A4 require qualitative assessment of execution fit for the intended workload, including
  relevant growth, skew, concurrency and failure. Distinguish semantic authority from physical lowerings and operational
  granularity; compare composed library capabilities, necessary work and total machinery. Reuse
  established immutable validity while retaining checks for distinct failure/trust boundaries.
  Drain writers and freeze content/definitions before final persisted reconciliation and publication.
  Explain material tradeoffs in plain language. This consideration requires no numerical estimates,
  cost models, estimators, runtime cost accounting, execution-planning machinery, instrumentation,
  formal cost proofs or additional proof artifacts. Such mechanisms need a separate concrete
  functional or operational requirement. Quantitative performance/capacity claims still require
  measurements; semantic correctness obligations remain.
- CI-05 permits a graph-native canonical artifact; CI-07 preserves analysis semantics without
  mandating runtime placement; CI-08 distinguishes examined work from bounded output; CI-13 pins
  the complete realization across the declared consumer journey and its returned references.
- Assess these criteria during requested or scheduled design reviews. Ordinary implementation
  does not initiate a domain-model review. Follow a flow only where it resolves a concrete
  uncertainty; static source and contract inspection can suffice.
- The coordinator is accountable for design coherence, integration and acceptance. Six shared roles
  provide code mapping, library research, independent design review, execution, implementation review
  and functional testing. Shape contributions around useful results, shared decisions and dependencies;
  components, documents and roles offer possible boundaries. Delegation can provide progress, earlier
  learning or independent judgment, including serial work or deliberately overlapping investigations.
  No fixed role sequence, lane taxonomy or agent count applies.
- Assess readiness for the requested result. An investigation may resolve a contract; consumer
  preparation may need agreed semantics; working integration needs implemented prerequisites. Workers
  exercise delegated judgment within accepted outcomes and contracts. Reconcile changes affecting
  another contribution or semantic owner. Existing operating rules govern conflicting effects,
  contract publication, shared resources and validation. Reconsider assignments as evidence changes
  their premises, coordination burden or usefulness; keep useful independent authorized work moving.
- [Shared contracts](../../.agents/roles/README.md) own responsibilities. Native Codex adapters
  own model settings, inheriting session permissions and tools. Explicit user/runtime settings
  retain authority. Library researchers may write assigned evidence folders, not the central
  library-skill store. The shared role table owns current routing; quality improvements and
  resource savings remain unmeasured.
- Workers use instructions already present and load missing applicable instructions, their common
  and assigned contracts and task-relevant skills once. Root orientation is task-specific; workers
  do not repeat the root tour. Permission, preservation and testing constraints remain universal,
  and workers follow dependencies beyond the brief's named files where read-only evidence needs it.
- Briefs state outcomes, settled decisions, exact baselines including relevant dirty changes,
  permitted effects, sibling ownership, dependencies and expected evidence. Returns distinguish
  observations from inference and report search coverage and limits for consequential negatives.
- Conflicting evidence, consequential absence claims, unresolved
  ownership/contract decisions or a second failed repair trigger coordinator reassessment. Narrow,
  inspect, check, handle directly or route stronger work as appropriate; do not automatically rerun.
  Shared roles document runtime-specific escalation without assuming custom Codex role overrides
  work.
- Independent reviewers receive concrete criteria, affected consumers and relevant failure cases.
  Focused advice and formal review retain the binding's distinct requirements.
- Three [skill pairs](../../.claude/skills/README.md) prepare and perform design review, plan
  creation and execution. Preparation is ordinarily conversational. Existing plans own execution
  receipts and scheduled findings; no additional ledger is introduced.
- Plan creation includes focused assessment of the foundations the intended capabilities will
  use. Carry necessary improvements into prerequisite work. Focused design advice belongs in the
  plan and cannot replace a formal review due under the binding. A read-only formal reviewer
  returns the complete report for coordinator publication without changing its judgment.
- Existing test timing, preservation rules and automatic checks keep their declared owners.
  These workflows add no worker cap, planning-mode hook, mandatory probe requirement, calibration
  exercise, benchmark campaign or recurring telemetry.

## Consequences

Role contracts, native definitions and workflow skills are Implemented scaffold capabilities.
Product conformance, workflow effectiveness and resource savings require evidence from actual use
and remain Proposed. Provider settings can evolve without copying behavior into every workflow.
Workers retain local discretion within their brief; the coordinator resolves material contradictions.
Historical reviews keep their original scope and version.

Fresh projects receive this self-contained replacement seed. Existing projects keep their own
decisions and checkpoints when updating the template, and adopt changed policy under their next
available ADR identifier.
