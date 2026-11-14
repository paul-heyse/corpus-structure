---
id: ADR-0103
title: Freeze complete table and schema privilege policy in compared operations
status: accepted
date: 2026-11-14
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

DDO SQLAlchemy/Alembic I04/I05 replaces creation-only table grants and author-login role
restoration strings. Frozen predecessors record table owners/read roles but not complete ACLs
or schema usage. Live grants cannot become declared migration custody.

## Options

1. Keep string fix-ups and refuse existing-table policy changes at admission: preserves duplicated
policy and cannot author the declared target.
2. Adopt the live ACL as predecessor: falsely authenticates stray grants.
3. Explicit initial normalization followed by complete compared policy transitions: selected.

## Decision

The physical authoring owner declares table ownership, exact nonowner SELECT grants without grant
options, empty column grants, and schema usage derived from declared table/view/function capabilities.
PUBLIC and undeclared grantees have no rights. Publisher CREATE/USAGE remains available for authoring;
purpose roles cannot CREATE. Schema ownership and cluster membership remain separate authorities.

Initial normalization checks recorded legacy owner/read/write premises and explicitly labels missing
ACL/schema before facts unrecorded. It installs the complete declared after policy and independently
checks the catalog. It refuses reverse because missing historical facts cannot be reconstructed.
Later transitions carry exact frozen before/after policy and reject stale state. Desired policy never
comes from reflected grants. Frozen artifact envelope v2 tags native and privilege operations while
existing v1 artifacts/native payloads retain exact reading and execution.

This qualifies ADR-0074's retained-walk rationale: owned operations now retain ordinary DDL/FK role
context and restoration; global physical retirement ordering remains an explicit pass. No public
Rewriter conversion or replacement migration engine follows. Cross-owner FK authorization uses actual
constraint vectors/declared owners and revokes only temporarily introduced REFERENCES capability.

Revision-specific data movement uses closed first-party named Core builders captured in preview
staleness premises, compiled once into frozen SQL. Upgrade never imports a current builder. Frozen
forward-base replay supplies historical data prerequisites; type-only savepoint scaffolding does
not install defaults, constraints or migration data effects.

## Consequences

Existing-table policy changes become inspectable operations. Native admission compares the complete
policy independently; owner restoration no longer depends on the authoring login. Current target
source and focused tests are implemented separately from registration/deployment and broad qualification.
The DDO coordinator owns those states. Revisit if new privilege capabilities require widening the
modeled policy; do not silently admit additional rights. Expected simplification is qualitative,
not measured runtime improvement.
