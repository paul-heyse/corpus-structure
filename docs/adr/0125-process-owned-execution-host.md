---
id: ADR-0125
title: One process execution host owns reusable resources and bounded retirement
status: accepted
date: 2026-11-17
supersedes: [ADR-0083]
superseded-by: null
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: A supported consumer needs concurrent runs within one host or cannot prove retirement without retaining unbounded resources.
---

## Context

The accepted [DDO production-efficiency target](../plans/declared-data-operations/production-efficiency-integration.md)
requires PE-S25: repeated runs reuse immutable preparation and workers, and concurrent MCP calls
share one physical budget. Invocation-owned resources previously recreated those resources and
allowed separate render budgets to exceed the intended process bound (PE-D01). This changes
resource lifetime, while run-owned claims and native settlement remain authoritative. D3 owns
storage/admission, D4 method seams, D6 resource lifetime and D8 entry points. Implementation and
qualification remain open in the [DDO coordinator](../plans/declared-data-operations_2026-11-12.md).

## Options

1. Keep per-run resources. This is simple for a short CLI invocation, but repeatedly prepares
   immutable state and permits independent MCP calls to allocate separate process-sized budgets.
2. Cache prepared objects globally without a lifecycle owner. This avoids some work but has no
   coherent byte charge, retirement or admission boundary; cache presence cannot authorize work.
3. Use one explicit process host and one active run, selected. It centralizes bounded resource
   custody and reuses authenticated preparation without adding concurrent scheduling arithmetic.
   Long-lived services must close or quarantine resources whose retirement is uncertain.
4. Adopt a distributed workflow scheduler. There is no cross-host execution requirement to
   justify another claim, dependency or publication authority.

## Decision

**Proposed accepted target.** One execution host per process owns the shared owned-byte budget,
CPU worker generations, release capsules, prepared ports, provider lanes and verified execution
bases. A short CLI process brackets its runs with this host; MCP holds it for its lifespan.
One run is active per host. Capsules are reference-counted by runs; idle capsules use a byte-bounded
LRU charged to the same budget. Capacity-one uses this same implementation. Encoded owned bodies,
queued packets and completed replies remain charged until their last consumer; this is not an
interpreter RSS bound. ADR-0123 owns admission before hydration and sole-owner reduction.

A run owns claims, renewal, admissions, cancellation and settlement. It finishes only after every
submitted request has proven physical retirement through terminal collection or retirement of
its generation. Cancellation stops admission, signals cooperative kernels and discards late
results. An uncertain generation is quarantined with its charges; bounded shutdown, kill and
join must prove retirement before confirmed release of pending failures. A successor generation
may open only if capacity remains. An unconfirmed join quarantines the host until restart.
Future cancellation alone does not stop an executing kernel or release its capacity.

Native residency extends across runs only under an explicit keep-warm policy, default zero.
The native group holds Nemotron suspended while resident. Expiry, an external GPU borrower or
an incompatible profile retires the generation; two GPU generations never coexist.

Full re-derivation establishes a verified basis at first host use. Reuse requires the same engine,
release, archive digest, finalization, runtime, source root and compiler determinants. Each run
rereads the immutable archive header and runtime binding; activation and registration retain
full verification. Historical archive hydration and arbitrary prepared objects confer no verified
status. This is structural meaning reuse, never admission: execution acquisition, permissions,
trust, source authorization and attempt fences remain live.

The parent retains durable effects, validation, completion and coherent publication. Workers use
Python3.14 ProcessPoolExecutor with explicit spawn, initializer, finite submission and main-thread
formal/construction/contextual kernels. Authenticated immutable capsules and runtime inputs cross
processes; live PreparedRelease objects, readers, callbacks, connections and engines do not.
Provider preparation/inference/reduction and authenticated batch member projection retain their
semantic owners. Real dependencies permit independent progress without stage-wide barriers.
Device, precision and result-affecting batch semantics keep their appropriate provenance;
physical placement does not select fewer families or smaller semantic contexts.

Regional owners retain exact source/projection/recipe/native values, immutable views/indexes and
validation established under the original release/source/closure premises. Public payload access
remains fresh. New or untrusted results validate before publication; a digest is not proof.
Large bodies leave after their final consumer while compact pins remain for composition.
Source-specialized grammar preparation preserves protected lexical positions; transport bounds
do not alter publication limits. There is one execution implementation, with no inline legacy
backend, universal size estimator, arbitrary layer upload or extra knowledge-admission authority.

## Consequences

Reusable resources acquire one explicit lifecycle and budget without duplicating semantic or
native task authority. Ingest, standalone demands, books and MCP share the same route. One active
run deliberately trades concurrent entry-point execution for a coherent physical bound; a future
consumer can reopen that decision. This record carries all surviving clauses of ADR-0083 and
replaces invocation ownership of reusable resources with process ownership. Run-specific regional
lifetimes and effects stay scoped to the run. Existing exact source/choice/coverage, numerical and
knowledge-standing contracts remain. The DDO owner retains implementation, actual-provider,
fault and whole-book obligations; acceptance alone establishes no tested or measured benefit.
