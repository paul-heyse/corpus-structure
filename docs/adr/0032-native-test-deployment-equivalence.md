---
id: ADR-0032
title: Fresh native tests clone a session deployment with explicit database policy replay
status: accepted
date: 2026-10-29
supersedes: []
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: Native consumers require deployment changes that cannot be faithfully replayed on a fresh clone, or session preparation ceases to fit the supported test workload.
---

## Context

SP-I08 consumes the operator-accepted PR-03 interpretation of fresh frozen native deployment.
Semantic consumer fixtures currently repeat the complete migration chain. PostgreSQL clones
copy physical objects but omit database ACLs and database/role defaults; substituting clones
without explicit replay would weaken the restricted-principal contract. I10/CBO-010 in the
[qualification plan](../plans/semantic-model-pivot/qualification-infrastructure.md) owns this work.

## Options

1. Keep per-test deployment: simple and valid, but repeats preparation unrelated to ordinary
   consumer assertions. Retain this route where deployment itself is the subject.
2. Session-local native template and fresh clones with explicit policy replay: selected. It
   removes repeated preparation while preserving committed isolation and actual logins.
3. Rollback/TRUNCATE reset: cannot establish separate-login commits, races or cancellation.
4. Persistent semantic template cache or pytest-postgresql: broader invalidation/ownership or
   janitor adaptation is unnecessary for this session-local contract. Existing native lifecycle
   and leases already fit the dedicated server and restricted backend permissions.

## Decision

The test-support owner builds the frozen semantic head once per session from the extension-only
template. Every consumer receives a new database, real commits and authenticated purpose logins.
The source has no connected clients and is frozen against application connections. Its owner,
connection limit, normalized database ACL including grantors/options, and database/role defaults
are captured, replayed and compared before a clone is exposed. Unavailable replay authorization
refuses setup; neither grants nor settings may silently disappear.

Cold bootstrap, CLI initialization and era-shaped historical revision controls still execute the
actual migration chain. This interprets fresh deployment for consumer isolation; it does not
replace deployment testing. ADR-0031's native admission, no generic writer/admitter TEMP,
protected publisher workspaces, capability-based alternate principals and live checks continue.

One existing test lifecycle owns leased names, creation, cleanup and residue. Close owned
resources and retry normal backend exit boundedly; do not broaden termination rights or use
forced drops. Session templates have no persistent reuse/invalidation key. Unauthenticated
historical residue is not disposal authorization. Legacy fixtures retain their existing cache
and transaction semantics behind the shared lifecycle.

## Consequences

Native consumer preparation is reused without a second fixture janitor or persistent semantic
cache. Replay/equivalence and independent posture controls are necessary because PostgreSQL
does not discharge them. Reduced preparation is structural reasoning, not a measured speedup.
The qualification plan owns implementation, native verification and remaining obligations;
acceptance of this decision alone establishes none of those results. SP-09/SP-10 operational
and complete product acceptance remain separate.
