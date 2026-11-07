---
id: ADR-0069
title: Route routine operations through ci with owned effects and result custody
status: accepted
date: 2026-11-07
supersedes: []
superseded-by: null
design: [§2]
evidence: Proposed
revisit: A supported deployment requires multi-host result custody, or diagnostics needed for a named operator action no longer fit the receipt boundary.
---

## Context

The CLI plan records the operator's acceptance of CLI-RC01–03. Routine shell sequences and
caller-selected output paths obscure authority, custody and settlement. The target review
identifies lock lifetime, process ownership, explicit effect fences and read-purpose issues.

## Options

1. Keep the existing command surfaces and use documented shell recipes for every combined
   journey. This reuses tools but leaves result identity and recovery with the caller.
2. Use a single CLI facade with the existing recipes, application owners and managed result
   custody. One invocation record supports recovery and disposal without duplicating native
   settlement. Local locking and bounded reads fit the supported single-host workload.
3. Add a global workflow or telemetry service. Its separate storage and coordination burden
   has no named consumer in this scope.

## Decision

Use installed `ci` as the routine interface. Repository automation remains owned by `just`.
Product actions call their application owners. Bootstrap and recovery can invoke their existing
tools directly. Preserve typed output, explicit effect targets and the applicable purpose roles.

Manage invocation artifacts under one local result owner with explicit settlement and leases.
Expire unheld successes after one day and failures or interruptions after one week. Only
managed derived data is eligible. Keep dependent receipts and candidates protected while in use.
Diagnostics begin with existing status, receipts and refusals.

Require reviewable preview, apply by exact preview ID and explicit deployment against a bound
target. Activation and selection are explicit. Reuse native transactions and generation fences.
Checkout file fencing covers cooperating writers, with exact file digests checked at each write.

## Consequences

The CLI integrates existing owners through thin adapters. A retry creates its own invocation
and names the earlier one. Managed output can be discovered by ID. A cleanup preview and a
bounded diagnostic view help the operator decide the next action. Implementation and acceptance
remain with the [CLI plan](../plans/cli-operations_2026-11-07.md).
