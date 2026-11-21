---
id: ADR-0142
title: Deliver selected results as bounded structured JSON
status: accepted
date: 2026-11-20
supersedes: []
superseded-by: null
design: [D8]
evidence: Proposed
revisit: A supported selected-result client needs to round-trip a domain value that the finite display model cannot represent.
---

## Context

Selected MCP reads carried their payload as a serialized JSON string inside the SDK's structured
response. The client decoded it a second time, and the text and structured SDK projections
duplicated the payload. The operator selected a coordinated structured cutover under DMO-05.
[D8](../design/D8-agent-and-query-interfaces.md) · [DMO-05](../plans/domain-model-operability/json-contracts-and-settings.md#dmo-05)

## Options

1. Keep the serialized string to carry the prior literal spelling. Every client must parse a
   second document and the SDK schema cannot describe that document as the delivered object.
2. Deliver a versioned structured result. The SDK carries one payload and the caller uses the
   native pins and handles for identity-sensitive operations. Displayed fractions follow the
   application interchange number policy. Selected.

## Decision

The existing semantic readers retain authority over results, cut IDs, continuation handles and
resource replay. Their MCP adapters deliver the structured object with finite JSON numbers,
including in resource replay. The MCP delivery boundary checks the complete SDK result size.
Current live authority still governs reads and replay. D1 scope equality, native cut identity
and archived bytes retain their own owners and interpretation.

## Consequences

Consumers read the structured result field and use the supplied IDs and handles for replay.
A rendered approximate number can lose precision relative to a native scope determinant.
The native determinant remains part of the authenticated cut. The plan owns delivery checks,
the remaining numeric migration, and integrated qualification.
