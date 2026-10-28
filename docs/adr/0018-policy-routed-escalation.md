---
id: ADR-0018
title: Escalation is routed by versioned policies over measurements
status: proposed
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§B6]
evidence: Proposed
---

## Context

The operator's original question asked for "conditional use of capabilities in response to measured
gaps", and the old repository's failure mode was unvetted accumulation of mechanisms
([design rationale](../design/rationale.md) §1.2, §2, P4). Which method runs on which unit, and when
a unit escalates to the local LLM or the agent, must be inspectable, versioned and tied to the
measurements that triggered it, so interventions can scale back as cheaper methods prove themselves.

## Options

1. **Hard-coded routing in the orchestrator.** Simple, but routing is code, not versionable as
   policy, and its triggers are not recorded.
2. **Versioned policy chains over measurements**, compiled to rule-engine `Chain`s with typed
   contexts: ordered first-match entries per routing point (`propose`, `escalate`, `adjudicate`,
   `identity`, `gaps`), each task recording the rule that fired and the metric values that made it
   fire.
3. **SHACL or another RDF-bound rule language.** RDF-bound, and a second expression language beside
   the validation rules.
4. **A learned router.** Needs labelled outcomes that do not exist yet; a later input to thresholds,
   not a replacement.

## Decision

Option 2, as D6 §7 states it: `policies.yaml` per domain holds budgets, thresholds, priors and
chains; conditions are rule-engine expressions over typed unit and run contexts, so a broken rule
fails compilation; every task records its policy rule and trigger values (D3 `ops.task`); conditional
methods enter only through gap proposals and experiments (D6 §7.3, D7 §7). One expression engine
serves validation (M19) and routing.

**Proposed until S4 reports** (operator decision, 2026-10-28): OPEN-D2-3 (rule-engine syntax;
functions or resolver-backed attributes) decides how conditions over claims and condition trees are
written. Acceptance follows S4 and the design/target review that precedes phase 0 execution.

## Consequences

- "Why did this unit go to the agent" is a query over the task's trigger. Scale-back is a policy
  version whose thresholds rise as measured reliability improves (D6 §7.5).
- Policies are data under experiment control, so a routing change is evaluated like any other.
- **Revisit** if rule-engine cannot express a needed routing condition over measurements, or routing
  needs learned scores (then thresholds become fitted parameters, not a new mechanism).
