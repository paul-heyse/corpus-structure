---
id: ADR-0015
title: The agent tier works a recorded queue; the pipeline never calls it
status: superseded
date: 2026-10-28
supersedes: []
superseded-by: ADR-0034
design: [§B3]
evidence: Proposed
---

## Context

Near term, the strong model is Opus in the operator's Claude Code session, not an API
([design rationale](../design/rationale.md) §1.3, §4.11). Phase 0 is a walking skeleton in which
the agent extracts claims while cheaper methods do not exist yet (D0). Interventions must be
recorded so they can scale back as automated methods mature, and the operator's binding constraint
during debugging is output and context size (P10).

## Options

1. **The pipeline calls a model API** for agent work. Not available for the session model; and it
   would make the agent's work an invisible side effect of a run.
2. **The agent works a database queue through tools.** The pipeline creates `awaiting_agent` tasks;
   the session pulls bounded packets and submits observations through MCP tools; a run waits at a
   barrier or finishes with those items explicitly unresolved.
3. **A workflow engine** (Prefect, Dagster, Temporal, Airflow) orchestrating agent steps. Each would
   be a second authority over task state the database already records.

## Decision

Option 2:

- **The pipeline never calls the agent.** Policies (D6 §7) create agent tasks; the run either waits
  at its barrier (`--agent-mode wait`) or completes with the tasks unresolved.
- **The agent works through MCP tools** (D8 §2): `queue_next` and `read_unit` serve capped packets
  (D8 §3); submissions are validated, located and stored as observations plus an `ops.intervention`
  row; nothing the agent writes bypasses consolidation (ADR-0014).
- **Golden authoring** goes through the same tools, by fresh Sonnet subagents the session dispatches
  (ADR-0011).
- **The queue persists**, so a run's agent tasks are worked across as many sessions as it takes
  (D6 §7.4).

## Consequences

- Every agent act is a recorded, bounded, resumable task, so `intervention.share` is measurable and
  the scale-back of phases 1–3 is visible.
- A run that needs the agent cannot finish unattended; slice runs and budgets keep that bounded.
- The same packet format serves the local LLM and later hosted models, which then become callable
  methods (D4 §4).
- **Not yet built:** the phase 0 series (orchestration, agent-interface). OPEN-D8-1 (one process
  or two) is decided there.
- **Revisit** when a hosted model API replaces the session as the strong tier: it becomes a method
  the pipeline calls, and the queue remains for the session's work.
