---
id: ADR-0048
title: Read-only serving scenarios clone a session-local populated seed
status: superseded
date: 2026-11-02
supersedes: []
superseded-by: ADR-0102
design: [§B4]
evidence: Proposed
revisit: The default serving population changes, seeding ceases to remove repeated publication, or a consumer needs publication/lifecycle evidence rather than prepared read state.
---

## Context

TA-05/DTA-018 finds three read consumers rebuilding the same completed serving population.
ADR-0032 already owns session deployment, fresh committed clones, policy replay and authenticated
cleanup. The [scoped review](../design_review/reviews/design_review_ta-scenario-seeds_2026-11-02.md)
accepts extending preparation for this named population without changing those guarantees.

## Options

1. Repeat publication for every read assertion: valid, but repeats unrelated setup.
2. Share a mutable database or rollback-only transaction: loses committed cross-session isolation.
3. Clone a populated session-local source through PgAdmin: selected. It adds one bounded fixture
   lifetime while reusing the existing server, ownership, replay and disposal responsibilities.
4. Persistent seed cache or another fixture janitor: unnecessary invalidation/ownership machinery.

## Decision

Only the repeated default completed serving scenario uses a named immutable session seed.
Its preparation and population recipe bind captured source bytes, model/dependencies/profile,
release identity and source/run/task references. Build through the current composed-execution/proposal path
and actual purpose publication; the synthetic serving model is not a Statistics product claim, settle clients, verify policy, then seal the owned source.
Every reader receives a newly owned database clone, verified policy replay and actual purpose
connections. Seed origin and actual clone context remain distinct in existing receipt events.
Mismatched recipe/preparation identity refuses reuse; no cross-session cache is introduced.

Varied query-pack/coverage scenarios and deployment/publication/write-lifecycle tests remain
independently prepared. Read/export cancellation still exercises its actual operation on a fresh
clone. ADR-0032 and its cold deployment, principal and cleanup obligations remain unchanged.

## Consequences

Repeated publication is removed for named read consumers; no speedup is claimed without measurement.
The seed is setup, not an oracle: independently authored expected results stay at each test.
TA-05/06 and TA-12 in the [coordinator](../plans/test-architecture-and-evidence_2026-11-02.md)
own implementation and qualification. This decision alone does not establish tested closure.
