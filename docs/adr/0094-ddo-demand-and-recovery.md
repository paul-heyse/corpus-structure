---
id: ADR-0094
title: Native demands and requests own fulfillment and recovery
status: accepted
date: 2026-11-12
supersedes: []
superseded-by: null
design: [§B4, §B5, §B6]
evidence: Proposed
revisit: An admitted operation or preservation consumer cannot be represented without duplicated semantic authority or lost custody.
---

## Context

Name/stage maps and run-scoped task sequences do not express complete demand fate, discovery or cross-demand request ownership. The accepted DDO target replaces these semantic responsibilities while retaining physical execution ownership.

## Options

1. Keep stage-run scheduling and add missing dependency lists. This adds policy copies.
2. Introduce a second workflow engine. This duplicates claims and failure authority.
3. Native demand/request semantics over the existing task/attempt fence. Selected.

## Decision

Immutable Demand/DemandUse freezes root/producer/replicate selection and records discovery, coverage, selected fulfillment and every obligation's fate. Typed relational bindings govern all-of/cardinality/distinctness/alternatives/closed populations. Call graphs and topological generations do not establish sufficiency or impose generation barriers.

Equivalent requests coalesce across demands with one fenced producing task per generation. Native uniqueness/locks and existing leases own concurrency. Durable exact completion intents distinguish committed acknowledgement loss, known rollback and unresolved effects. Adoption authenticates the new fence without rewriting original producer attribution. Submission uncertainty retains physical custody until bounded settlement/termination. Native refusal, cancellation, failed/empty/partial and externally awaiting work remain distinct. Shared useful work is not cancelled merely because one demand detaches.

Preserve GPU numerical/device policies, exact batches/source membership, bounded preparation/residency and explicit external-agent delivery; the pipeline does not manufacture an agent answer.

## Consequences

This accepts the target, not completed implementation or native adoption. The
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md) owns package readiness and original
finding dispositions. Current selected protocols and archived interpretations keep their existing
ABI/custody guards until the coordinated adoption package replaces their callers. These records
establish the DDO target; full-record retirement of ADR0063/0060/0027/0081/0082/0084/0090/0033/0014/
0085/0091/0050/0064/0067 is not performed while those records still govern live legacy consumers.
DDO-00 records the scoped replacement route; DDO-11 completes reference retirement at cutover.
No data deletion, migration, activation or provider call is authorized by this record alone.
