---
id: ADR-0079
title: Keep safe observation custody under the canonical interface authority
status: accepted
date: 2026-11-10
supersedes: [ADR-0078]
superseded-by: null
design: [§2]
evidence: Proposed
revisit: A supported observation consumer requires multiple writing hosts or independent telemetry retention.
---

## Context

This record restates every decision and consequence of ADR-0078 under canonical workflow
authority §2. Its predecessor used an unresolvable design metadata reference. No observation,
effect, retention or verification decision changes; the predecessor is retired to Git.

CLD adds correlated inspection of interrupted operations to the existing CLI result owner.
Current settled artifact reads authenticate published files; they do not promise that an
actively appended file is immutable. Provider observations and native settlement have different
authority. D8 owns these boundaries; ADR-0069 expiry, holds and effects remain in force.

## Options

1. Retain only final snapshots. This is simplest but loses the last available observations
   when the producer dies before publishing its final report.
2. Use one bounded owner-written safe journal and a dedicated live reader, then seal it for
   settled replay. Existing leases, publication identities and custody remain reusable.
3. Publish immutable chunks or add an independent telemetry store. Both introduce indexing,
   publication and cleanup machinery without a supported multi-host or remote consumer.

## Decision

Select option2 for the single-host workload. The managed invocation owns its writer and
retention. Live reads authenticate that designated role, bound examined and returned data,
return complete records only and disclose unsealed, partial or corrupt standing. Generic
settled-artifact access remains unchanged. Seal length/digest before ordinary settlement;
failed sealing reports unavailable diagnostics without rewriting native outcomes. Each independent
settled read verifies the complete sealed journal, capped at8MiB, before page selection. This
bounded integrity scan avoids another authenticated chunk index; inode identity is not a digest.

Normalize each event to owned safe nested data before journal/presentation fan-out. Use
structlog26.1 with stdlib producers and one final presentation owner; no RichHandler traceback
stacking. Process routes outlive invocation context, whose tokens and endpoints are restored.
Child processes transfer bounded safe observations to their parent; they never write its
journal. Native task state, provider-reported assurance and timestamp ordering remain distinct.
No global trace identity, new workflow engine or remote service is selected.

## Consequences

Interrupted investigation and replay become possible without rerunning providers or validators.
The live reader and child drain require explicit partial-write/cancellation behavior and focused
verification. Disclosure, expiry, effect authority and original receipts retain their owners.
The operator excludes the real Claude CLI provider journey from CLD qualification; controlled
processes, local MCP and native integration remain required. This changes verification scope,
not product authority. Implementation and qualification remain with the
[CLD coordinator](../plans/cli-and-logging_2026-11-10.md); acceptance of this decision does not
establish delivery. Expected benefits remain Proposed.
