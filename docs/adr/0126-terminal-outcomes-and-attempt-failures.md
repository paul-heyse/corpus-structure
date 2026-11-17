---
id: ADR-0126
title: Native demands publish terminal outcomes while execution failures stay with attempts
status: accepted
date: 2026-11-17
supersedes: [ADR-0094]
superseded-by: null
design: [§B4, §B5, §B6]
evidence: Proposed
revisit: An admitted provider cannot distinguish input outcomes from execution failures without losing actual evidence or retry custody.
---

## Context

The accepted DDO production-efficiency plan PE-S09 corrects reuse of recognition deployment,
transport and initialization failures as input results. The existing native demand/request owner
and durable completion intents remain. The [DDO coordinator](../plans/declared-data-operations_2026-11-12.md)
owns implementation and qualification; this record changes failure classification and restates
all surviving demand/recovery clauses of ADR-0094.

## Options

1. Retain failed results and a caller-controlled reuse flag. This requires callers to repair
   provenance after the fact and can repeatedly reuse an endpoint failure as an input judgment.
2. Retry everything inside the adapter. This hides attempt boundaries and duplicates native
   retry, cancellation and lease ownership.
3. Classify at the failure origin and use existing fenced attempts, selected. Terminal input
   outcomes can be reused; execution failures remain evidence for retry and physical retirement.

## Decision

**Proposed accepted target.** Immutable Demand/DemandUse freezes root, producer and replicate
selection and records discovery, coverage, selected fulfillment and every obligation's fate.
Typed relational bindings govern all-of, cardinality, distinctness, alternatives and closed
populations. Call graphs and topological generations neither establish sufficiency nor impose
generation barriers. Equivalent requests coalesce across demands with one fenced producing task
per generation. Native uniqueness, locks and existing leases own concurrency. Shared useful work
is not cancelled merely because one demand detaches.

An operation result is a terminal provider outcome under its admitted generation, including
completed empty/partial readings and declared input refusal. Execution failure describes the
physical attempt: transport, timeout, unavailable service, generation crossing, package or
configuration drift, initialization failure, crash, cancellation or lease loss. It is retained
as attempt evidence, never published or reused as an operation result. Missing classification
is execution failure. The `reuse_failures` override is removed.

The classification implementation scope is recognition/PDF; other provider changes need an
explicitly recorded concrete finding. Recognition classifies HTTP400/413/422 and adapter-declared input refusals as terminal; finish
caps, partial/empty readings and parser failure after all responses were received are terminal.
Other HTTP statuses, including401/403/404/409/5xx, are execution failures. An admitted-generation
response is necessary for terminal provider attribution. The operation completes pages it can;
any execution-failed page makes the request retryable instead of publishing the set. Existing
attempts own retries; no adapter retry loop is added. Repetition recovery remains bound to
terminal capped pages.

Durable exact completion intents distinguish committed acknowledgement loss, known rollback
and unresolved effects. Adoption authenticates the new fence without rewriting original producer
attribution. Submission uncertainty retains physical custody until bounded settlement/termination.
Native refusal, cancellation, terminal outcome and externally awaiting work remain distinct.
Current support, trust, purpose, source authorization and attempt fencing remain live.

GPU numerical/device policies, exact batch/source membership, bounded preparation/residency and
explicit external-agent delivery remain; the pipeline manufactures no agent answer. DDO's
native-only target replaces historical stage/name maps and run-scoped sequencing without a second
workflow engine or semantic authority. Generated historical data may remain inert or be regenerated;
it does not justify a compatibility execution path.

## Consequences

A failed endpoint cannot become a reusable judgment about an input. Adapters must emit typed
classification at origin and preserve partial attempt evidence without publishing an incomplete
set. The existing native retry and resource-retirement owners carry the burden. This accepts the
target rather than completed implementation, migration, activation, provider execution or adoption.
The coordinator retains all source finding IDs and applicable native/provider/fault/whole-book
acceptance. No measured benefit is claimed.
