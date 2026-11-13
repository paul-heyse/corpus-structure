---
id: ADR-0102
title: Reuse eligible committed scenarios through worker-local sealed seeds
status: accepted
date: 2026-11-13
supersedes: [ADR-0048]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: A seed premise ceases to hold, or consumers need producer lifecycle evidence rather than committed prepared state.
---

## Context

Serving-only seeds leave identical scenario preparation repeated by many native families.
The operator accepted RC04 and the no-unfinished-task rule in the
[test-system coordinator](../plans/test-system-target-design_2026-11-13.md).

## Options

1. Rebuild every scenario: valid but repeats setup unrelated to each assertion.
2. General sealed seeds with claim-specific clones: selected; reuses existing PgAdmin ownership.
3. Persistent scenario cache: adds invalidation with no selected need.
4. Shared mutable state for all claims: cannot establish committed cross-session isolation.

## Decision

Any eligible recipe may build one immutable seed per worker/session, keyed by the frozen data-only
recipe and acquired head. Each recipe type has one builder; compositions and patches remain local
to its support owner. Recipes are requested through fixtures, never test bodies. Build through
real producers/purpose engines after deployment verification, settle clients, verify policy and
seal. No task may remain claimed or running even when its lease expired; completed attempts are
allowed. Nothing built under an implementation override is seedable. Scenario files are protected
against mutation. Revalidate OID, policy, sealing and absence of clients before cloning.

Committing consumers receive new owned databases with replay and real purpose connections.
Rollback-compatible refusal families can share a family clone with fresh case transactions;
claims requiring commits, races or separate-session visibility keep their stronger isolation.
Seed boundary precedes the task claim where lease/attempt freshness matters. Lifecycle, cold
migration, producer-under-test and override-dependent variants retain independently prepared
state where that is part of their claim. ADR-0101 owns deployment and cleanup guarantees.

Seed origin and actual acquired clone context remain distinct in receipts; expected results
remain independently authored at each test. No persistent scenario cache, second janitor or
writable shared semantic engine is introduced. Failure cleanup disposes only acknowledged owned
resources; family clones settle before seeds, and source files live through their consumers.

## Consequences

Preparation can be shared without silently reusing a task lease or mutable expected result.
A transaction rollback does not reset sequences, clocks, session state or external effects;
classify actual consumers accordingly. TS-06/07/08/10/11/18 implement the target and TS-23 owns
qualification. Accepting this decision is not implementation, closure or measured duration gain.
