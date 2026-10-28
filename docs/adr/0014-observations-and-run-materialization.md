---
id: ADR-0014
title: Methods write observations; only consolidation writes knowledge, materialized per run
status: accepted
date: 2026-10-28
supersedes: []
superseded-by: null
design: [§B2]
evidence: Proposed
---

## Context

Every method (encoders, rules, the local LLM, the agent) proposes facts, and the old repository
adopted tools per gap without ever comparing them on one scoreboard. It also had five separate
history promises and process custody ([design rationale](../design/rationale.md) §2). The design
needs nominations never to pass as facts, two methods to be comparable on the same inputs,
consolidation to be changeable without re-running extraction, and runs to be comparable and
immutable (rationale §3, P3 and P8). Storage (D3), orchestration (D6) and consolidation (D5) all
depend on where knowledge is written and how long it lives.

## Options

1. **Methods write knowledge directly** (claims and entities). Simple, but a nomination can pass as
   a fact, supports are lost, and changing consolidation needs re-extraction.
2. **Methods write append-only observations; consolidation alone writes knowledge**, rebuilt on
   each pass from the observations and judgments.
3. **One mutable global knowledge base updated in place.** No per-run copies, but experiments
   cannot compare a candidate against a baseline, and rollback is a data repair.
4. **Run-scoped materialization.** Each run materializes its own entities, claims and links,
   immutable once finished; promotion picks a run.

## Decision

Options 2 and 4 together:

- **Writes.** Methods write `kb.observation` rows (append-only, keyed by input digest and method
  configuration); the agent is a method under this rule, so its proposals are observations plus an
  intervention row. Only consolidation (M17, M18) writes `kb.entity`, `kb.claim` and their evidence,
  supports and links (D5).
- **Rebuild.** Each consolidation pass rebuilds knowledge from observations and judgments (D5 §1).
  Deterministic keys (ADR-0013, D1 §10.1) let judgments and verifications carry forward.
- **Runs.** Knowledge is materialized per run and immutable once the run finishes (D1 §10.2).
  Reuse by input digest (D6 §4) makes a baseline nearly free and makes two configurations compare
  on exactly the same inputs. Promotion (D7 §7) picks the run that answers queries by default.

## Consequences

- Every claim lists its supports; re-consolidation is cheap and deterministic; an experiment is two
  runs over the same cached observations.
- **Cost:** storage for per-run materialization, acceptable at about 10⁴–10⁵ claims per run
  (D3 §11), and deletion of non-promoted runs after their experiments close.
- **Not yet built:** the phase 0 series realizes it (foundations, orchestration,
  consolidation-and-queries).
- **Revisit** if runs grow so large that per-run materialization dominates storage or rebuild time,
  or a consumer needs knowledge updated between runs.
