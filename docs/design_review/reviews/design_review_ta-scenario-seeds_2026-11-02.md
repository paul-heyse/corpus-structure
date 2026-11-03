# TA scenario-seed design review

**Date:** 2026-11-02  
**Review lens:** Combined design and target review; scoped to the proposed default serving-scenario seed.  
**Disposition:** Accept scoped, **Proposed**. This is a design judgment, not implementation or qualification evidence.

## Scope and inputs

This review assesses the proposal to avoid rebuilding one completed serving population for its
three read-only consumers. The current target is the default `test_serving.completed()` scenario
used by:

- named semantic pages, explanations and source search (`test_serving.py`, around lines 152–155);
- full projection export and cancellation cleanup (around lines 322–328); and
- real CLI query, explain and export (around lines 624–635).

The population uses the same statistics/default query input, one source PDF, one completed run and
task, and three Alice/Bob claims. The `query_pack` override and `complete_coverage=True` cases are
different inputs and remain cold. Publication, race, cancellation, migration and CLI-initialization
tests remain lifecycle or write-path evidence, not seed consumers. The two unlike `install_pack`
populations are outside this proposal.

The review uses the selected test-audit account and TA-05/DTA-018, current test source, ADR-0032,
and the proposed ADR-0048. DTA-018 identifies repeated scenario preparation; this review does not
infer that it is a measured bottleneck. Production-path details are checked against
`scripts/native_test_support.py` and `tests/semantic/conftest.py`.

## Judgment

Accept one session-local, immutable source database for the named default completed scenario,
provided its preparation uses the current composed scenario and actual purpose-publication path.
After producer work settles, verify policy, close clients and seal the source. Each consumer must
continue to obtain its own PgAdmin-owned committed database clone, replay and verify policy, and
connect through its actual purpose principal. Existing ownership and cleanup remain with ADR-0032.

The seed is prepared input, not an oracle. Keep independent expected facts, occurrences, source
links, and explanations in each consumer. Keep the seed's source/run/task identity separate from
the physical clone's database identity and policy context in the existing receipt stream.

The eligibility boundary should be the existing prepared scenario/release identity and its actual
captured inputs. Because the fixture is session-local and rebuilt for the invocation, do not add a
second persistent recipe registry, cache, or invalidation subsystem. Refuse a mismatch in the
identity already carried by the preparation path. No speed or capacity claim follows without
measurement; the copy and each real consumer operation still execute.

## Alternatives and failure behavior

Repeating publication for each read assertion is correct but performs the same unrelated setup
three times. A shared mutable database or rollback-only transaction would stop exercising the
committed, independently authenticated read path. A persistent cache or second janitor would add
ownership and invalidation state without a cross-invocation consumer. The existing PgAdmin clone
route is the narrow option that removes repeated population while retaining committed per-reader
state.

The source must not be exposed while publication or client work is active. If preparation,
publication, policy verification or sealing fails, fixture setup must fail and dispose of its
owned source through the existing lifecycle owner. If cloning or policy replay fails, that
consumer must fail before making semantic assertions. A consumer must not fall back to reading the
seed directly. Cancellation still runs against that consumer's fresh clone and retains its
cleanup assertions. These are target contracts; this review does not claim they have been
implemented or tested.

## Principle and gate impacts

- **FP-01 / A1:** The seed represents one explicit completed-serving population. It must not become
  a general scenario registry or silently absorb unlike coverage and query-pack populations.
- **FP-02 / A2:** The semantic authority remains the composed execution and purpose-publication
  path. The seed is not a parallel source of semantic truth; independent consumer expectations
  remain necessary.
- **FP-03 / A3:** Existing PgAdmin lifecycle ownership, fresh committed clones, purpose
  authentication and policy replay remain the resource and isolation boundary. No second owner is
  introduced.
- **FP-04:** Prepared population identity and physical acquired-clone identity have distinct
  meanings and must remain distinguishable in existing receipts.
- **FP-05:** Independent expected results and source/evidence links remain at each consumer; a
  shared seed must not turn setup data into a shared expected-value oracle.
- **FP-06:** Failure and cancellation paths keep their current cleanup responsibilities. A partial
  producer must not publish a usable seed.
- **FP-07 / A4:** For this three-consumer, fixed session scenario, one population plus fresh clones
  is a qualitative fit. This is not a measured runtime, scaling, or capacity conclusion.
- **G1 — Authority:** The source seed is a prepared input under the existing PgAdmin owner; it
  must not become a second lifecycle authority.
- **G2 — Semantic fidelity:** Keep scenario/release identity distinct from each acquired clone's
  physical identity; exclude changed query/coverage populations from seed eligibility.
- **G3 — Validity:** Producer, policy verification and seal failures must stop setup; clone or
  replay failures must stop that consumer before assertions.
- **G4 — Hidden behaviour:** The producer still runs the actual composed publication route and
  consumers still perform their actual serving/export operation. A synthetic scenario is not a
  Statistics product capability claim.
- **G5 — Consistency and recovery:** Close producer clients before sealing; preserve fresh committed
  clone state and existing authenticated cleanup.
- **G6 — Transformation and reuse:** Reuse only the named session scenario's prepared population,
  then replay policy for each fresh clone. No cross-invocation cache or broad reuse claim follows.
- **G7 — Truthful capability claims:** Describe setup removed, not a measured speedup; focused
  native tests and final qualification remain future evidence.
- **G8 — Library leverage:** This fixture lifetime does not add generic caching, scheduling,
  concurrency or data-copy machinery, so no library-selection work is indicated.
- **Code-intelligence profile:** Graph-specific CI gates do not apply to this database-fixture
  change. CI-11/CI-G2 still matters where the serving assertions require source-backed claims to
  retain their existing evidence route; CI-12/CI-G3 calls for independently authored expectations,
  which the seed must not replace.

## Rule and account effects

This is a scoped addition under ADR-0048; it does not revise ADR-0032's lifecycle owner, cold
deployment controls, principal checks, policy replay, or cleanup contract. It does not change the
test-audit baseline or close DTA-018. The TA-05 coordinator remains the owner of implementation and
qualification disposition. The implementation should preserve the existing default scenario
producer and vary only preparation lifetime for these three consumers; other serving scenarios
remain independently prepared.

## Limits and next evidence

The recommendation is **Proposed**. It does not establish that the fixture exists, that the
producer is sealed, that clones have distinct database identities, that policies and purpose
principals are verified, or that cancellation and failure cleanup pass. Those require focused
implementation tests and the selected native qualification lane after source is stable. No
quantitative benefit is claimed. Revisit if the default serving population changes, seeding no
longer removes repeated publication, or a consumer needs publication/lifecycle evidence rather
than prepared read state.
