---
id: ADR-0034
title: Agents execute the semantic queue through supervised or interactive MCP sessions
status: accepted
date: 2026-10-30
supersedes: [ADR-0015]
superseded-by: null
design: [§B3]
evidence: Implemented
revisit: A second scheduling authority or provider transport is required beyond the current queue and process supervisor.
---

## Context

ADR-0015 made a persistent database queue and bounded MCP packets authoritative, but also
forbade the pipeline from calling the agent. Current `intervene.automated.extract_run` already
starts a fresh Claude Code process with a run-bound MCP server. ADR-0030 accepts that route and
separates independent automated reference grading. The prohibition and its unattended-run
consequence now contradict the implemented contract. CA-08 in the semantic-pivot coordinator
owns this reconciliation; accepting this record alone does not close regeneration or qualification.

## Options

1. Require interactive operator sessions for all extraction. The queue remains sound, but every
   otherwise unattended regeneration needs manual dispatch and the accepted automatic route is lost.
2. Supervise a fresh model process over the same queue and MCP operations. This reuses the run's
   release, task attempts, source frames and protected completion rather than adding another state
   machine. Interactive sessions can still work the queue under the same contracts.
3. Introduce a workflow engine or model-specific task store. That duplicates scheduling and
   recovery authority already held by PostgreSQL without a current consumer requiring it.

## Decision

Choose option 2. PostgreSQL is the task/lifecycle authority. The supervisor invokes the model
recorded in the run's method configuration; a fresh run-bound stdio MCP process serves only that
run's archived interpretation, capped source packets and protected proposal operations. Model
process exit is transport status, not semantic task completion. Finalization consumes the sealed
cut through the existing domain operations; the process cannot write final knowledge directly.

The extraction child receives no reference credentials, builtin filesystem tools, inherited MCP
servers or project customizations. Its owned process group is drained on cancellation or timeout.
Restart resumes the recorded run and attempts; it does not silently create replacement occurrences.
Interactive MCP sessions retain the same queue, lease, packet and submission contracts. This does
not promise the unimplemented legacy wait-barrier option or any additional MCP inspection profile.

Independent reference authoring, adjudication and grading remain automated and separate under
ADR-0030 and the surviving author/input-independence decision ADR-0011. No human grading step is
required. The earlier golden-through-the-same-tools clause does not authorize reference access
through the source extractor; current evaluator operations use their restricted purpose login.

## Consequences

Unattended regeneration is supported without a second workflow authority. The persistent queue
still allows work across sessions, and direct model invocation never bypasses native attempts,
publication or provenance. The supervisor owns process lifetime; PostgreSQL owns semantic lifetime.
This adds provider authentication and process availability as explicit operational prerequisites.

The former prohibition on pipeline invocation and the claim that agent-dependent runs cannot
finish unattended are rejected. Bounded packets, durable tasks, intervention custody and separation
of source extraction from final knowledge survive. Legacy timestamp-cut/wait-barrier descriptions
remain historical or proposed detail where explicitly labeled; they are not alternate current APIs.
The SP-09/SP-10 owners retain actual provider journeys and final qualification as open until their
receipts establish completion. No speed, model-quality or full-product acceptance claim follows.
