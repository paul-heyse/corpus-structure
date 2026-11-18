---
id: ADR-0134
title: Bind scenario recipes at acquisition and seal eligible captures
status: accepted
date: 2026-11-18
supersedes: [ADR-0102]
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: A seed premise ceases to hold, or consumers need producer lifecycle evidence rather than committed prepared state.
---

## Context

Scenario content can be reused across workers and clone claims, while a workspace location
has its own owner and lifetime. The operator accepted RC08 and RC11 in the
[test-domain coordinator](../plans/test-domain-model-and-execution_2026-11-17.md#rule-changes)
to separate binding from content and permit certified controlled captures in eligible seeds.

## Options

1. Rebuild every scenario: valid but repeats setup unrelated to each assertion.
2. General sealed seeds with claim-specific clones: selected; reuses existing PgAdmin ownership.
3. Persistent scenario cache: adds invalidation with no selected need.
4. Shared mutable state for all claims: cannot establish committed cross-session isolation.

## Decision

Any eligible recipe may build one immutable seed per worker/session, keyed by the frozen data-only
recipe and acquired head. A recipe carries content only. Its one registered builder receives
a workspace and asset binding separately. Build a seed inside its own directory. Consumers that
write to a bound location build within their own clones and writable bindings, without sealing
or retaining a seed. Key a binding-dependent memo by both recipe and binding and invalidate its
entries at binding teardown. Compositions and patches remain local to their support owner.
Recipes are requested through fixtures.

Build through real purpose engines after deployment verification, settle clients, verify policy
and seal. No task may remain claimed or running even when its lease expired. A controlled
boundary producer is seedable only when its content is represented in recipe identity and the
production protocol and checks run. Record that origin. Other implementation overrides make a
scenario ineligible. The published-capture route refuses new capture or transform work before
writes. Protect scenario files from mutation and keep their reservation live through authenticated
readers. Revalidate OID, policy, sealing and absence of clients before cloning.

Committing consumers receive new owned databases with replay and real purpose connections.
Rollback-compatible refusal families can share a family clone with fresh case transactions;
claims requiring commits, races or separate-session visibility keep their stronger isolation.
Seed boundary precedes the task claim where lease/attempt freshness matters. Lifecycle, cold
migration, producer-under-test and override-dependent variants retain independently prepared
state where that is part of their claim. ADR-0133 owns deployment and cleanup guarantees.

Seed origin and actual acquired clone context remain distinct in receipts; expected results
remain independently authored at each test. No persistent scenario cache, second janitor or
writable shared semantic engine is introduced. Failure cleanup disposes only acknowledged owned
resources; family clones settle before seeds, and source files live through their consumers.

## Consequences

Preparation can be shared without silently reusing a task lease or mutable expected result.
A transaction rollback does not reset sequences, clocks, session state or external effects;
classify actual consumers accordingly. TDM-07/08/09 implement the target and TDM-18 owns qualification. The preparation and
controlled-producer contracts are accepted and pending implementation.
