# Additional assessment patterns

Additional opportunity patterns discovered during assessment. They are used alongside the
[base patterns](patterns.md) (LOP-01–LOP-12, edition 0.2), with the same reasoning role and the
same limits: a match nominates an investigation; it does not establish a defect, a library fit or
an obligation to adopt. The [framework](library-leverage-framework.md#discover-and-collect-additional-patterns)
owns their lifecycle. Promotion into the base set is a separate, manual operator decision.

**Revision history.**
- **Created** by the initial [codebase audit](codebase/README.md) on 2026-10-29: LOP-X001–X004,
  source baseline `9f8df02`, reconciled through `f697233`.
- **Extended** by the first [library assessment](libraries/README.md) on 2026-10-29, source baseline
  `d739b88`:
  - added LOP-X005–X007;
  - refined LOP-X001–X004 where library functionality exposed a missed distinction.

The originating observations are cited with their baselines. Each definition is meant to make sense
without them.

| ID | Pattern | First prompted by |
|---|---|---|
| [LOP-X001](#lop-x001) | Surviving code adapts into a retiring model to reuse its kernel | [CBO-005](codebase/consumers-and-operations.md#cbo-005), [CBO-006](codebase/consumers-and-operations.md#cbo-006), [CBO-018](codebase/storage-and-analytics.md#cbo-018) |
| [LOP-X002](#lop-x002) | A frozen derived artifact loses its derivation route | [CBO-008](codebase/storage-and-analytics.md#cbo-008), [CBO-014](codebase/storage-and-analytics.md#cbo-014) |
| [LOP-X003](#lop-x003) | Mirrored implementations across an enforcement boundary | [CBO-015](codebase/storage-and-analytics.md#cbo-015) |
| [LOP-X004](#lop-x004) | A compiled product leaves recurring derivations to its consumers | [CBO-013](codebase/release-preparation.md#cbo-013), [CBO-016](codebase/consumers-and-operations.md#cbo-016) |
| [LOP-X005](#lop-x005) | A database-derivable set round-trips through the client as a parameter list | [CBO-001](codebase/consumers-and-operations.md#cbo-001), [CBO-020](codebase/consumers-and-operations.md#cbo-020) |
| [LOP-X006](#lop-x006) | An explicit-input guarantee rides on a library resolver with an ambient fallback | [CBO-002](codebase/release-preparation.md#cbo-002), [CBO-021](codebase/release-preparation.md#cbo-021), [CBO-024](codebase/release-preparation.md#cbo-024) |
| [LOP-X007](#lop-x007) | Reused or cloned preparation silently drops state outside its copy boundary | [CBO-010](codebase/engineering-workflows.md#cbo-010) |

<a id="lop-x001"></a>

## LOP-X001 — Surviving code adapts into a retiring model to reuse its kernel

**Articulation.** Code written for a new authoritative model reaches a valuable older algorithm,
engine or rule environment by translating its records into the older model's types. The older
model is being retired, but its kernel is not obsolete. The dependency therefore points backwards,
and the retirement schedule becomes hostage to the kernel's operand model.

**Recognize.**
- Adapter functions in new-model modules that construct legacy types.
- Legacy imports inside new-model operations.
- Private calls into the legacy kernel.
- Type environments assembled from both models.
- Retirement plans that list the legacy model without listing its surviving callers.

**Investigate.**
- Is the kernel's real contract independent of the model?
- Could it accept the authoritative model through one owned adapter, a library-derived schema or a
  narrow stable view?
- Which further consumers will need the same kernel, so that per-consumer adapters would multiply?
- Is the legacy shape actually an external contract, such as authored rule text, that must stay
  stable?

**Counterconditions.**
- The legacy shape can be the deliberate stable contract.
- Retiring or replacing the kernel can be cheaper than rebasing it.
- A temporary adapter with a named removal point can be the right transition.
- Translating into the older model may also strip detail the kernel must not see.

**What the base patterns missed.**
- LOP-11 assumes the old premise is obsolete. Here the kernel stays valuable and only its operand
  model is retiring.
- LOP-06 frames repeated translation, but not the direction of the dependency or its interaction
  with a retirement schedule.
- LOP-09 frames fragmentation, not a single backward-pointing edge.

**Scope.** This shape is useful during model migrations, framework replacements and staged
cutovers, whenever both models coexist for a while.

**Refinement (library assessment, 2026-10-29).** Ask whether the legacy shape can survive as a
declared *logical view* over the authoritative model: a library schema plus an accessor. The
contract (names, types, nullability) then stays while the legacy types and projections retire.
Where authored artifacts are compiled against that view, its declared types become part of the
archived contract, and changing them changes which archived artifacts still compile. Prompted by
the rule-engine logical-view analysis of
[CBO-005](libraries/rule-engine/README.md#applicability-cbo-005).

<a id="lop-x002"></a>

## LOP-X002 — A frozen derived artifact loses its derivation route

**Articulation.** Some artifact is mechanically derived from an authority, but must also be frozen
once published. Examples are immutable migration revisions, reviewed generated SQL and vendored
schemas. The first revision is generated, or written to match the authority. The generator then
goes unused or stale, and later revisions are copied and edited by hand. Nothing re-derives or
compares the next revision against the authority.

**Recognize.**
- Generated-looking text with no repository generator.
- Generator code with no callers.
- Whole-file copies across revisions that differ only in mechanical per-item lines.
- Drift checks that compare a weak projection, such as names, instead of the full derived shape.
- A comparison facility that is configured but never invoked.

**Investigate.**
- Can a repository-owned generator emit the *next* frozen artifact for review, from the same
  authority the runtime uses?
- Can a parity check compare the frozen result with the authority's derivation at full fidelity?
- Which per-revision differences are intended, and how would they be expressed explicitly?

**Counterconditions.**
- The freeze exists so that published artifacts never change silently. Regenerating *past*
  revisions breaks that guarantee.
- Reviewed hand changes can be intentional divergence.
- Runtime verification may already catch drift loudly, which lowers the value of an
  authoring-time route.
- Generated output still needs review.

**What the base patterns missed.**
- LOP-02 assumes derivation happens at build or run time. Here derivation must happen at authoring
  time, under an immutability rule.
- LOP-11 assumes an obsolete premise. Here the freeze premise is valid and only the derivation
  route was lost.

**Refinement (library assessment, 2026-10-29).** An authoring-time route needs a *deterministic*
emitter. Check that the candidate emitter produces byte-stable output across processes before
relying on it for comparison against frozen text. For example, Alembic's offline `CreateTableOp`
emits constraints in set order, while SQLAlchemy's `CreateTable` compile reproduced frozen DDL
exactly. Prompted by [CBO-008](libraries/alembic/README.md#applicability-cbo-008) and
[CBO-014](libraries/sqlalchemy/README.md#applicability-cbo-014).

<a id="lop-x003"></a>

## LOP-X003 — Mirrored implementations across an enforcement boundary

**Articulation.** The same canonical computation is deliberately implemented on both sides of a
trust or enforcement boundary. Examples are identity or value meaning computed in application code
and recomputed inside the database, a client validator mirrored by a server, or two runtimes that
must agree byte for byte. The duplication *is* the guarantee: the enforcing side must not trust the
other.

**Recognize.**
- Byte-equality or identity checks between two languages or runtimes.
- Parity tests between the implementations.
- Comments saying one side recomputes rather than trusting the other.
- Further consumers adding third or fourth copies on the application side.

**Investigate.** The leverage is not consolidation into one implementation.
- Is there one written specification of the canonical form?
- Is conformance between the mirrors tested generatively, with property or differential testing,
  rather than only with hand-picked vectors?
- Are application-side *third* copies (encode, decode, Arrow normalization) consolidated around one
  owner, while the mirror across the boundary is kept?
- Are there pinned independent vectors that would catch a coordinated change to both sides?

**Counterconditions.**
- Consolidating across the boundary removes the protection.
- Generative tests need a trustworthy oracle or a differential property. Agreement between the two
  sides still does not establish correctness of the shared specification.

**What the base patterns missed.** LOP-09 points towards consolidation and treats intentional
difference only as a countercondition. It does not frame the real opportunity, which is
specification, conformance testing and removal of non-boundary copies.

**Refinement (library assessment, 2026-10-29).** A native or vectorized library kernel proposed
to implement the canonical computation is one more mirror. Check it against an independent oracle
at the edges (carry, overflow, scale and precision bounds, signed zero), not only on random data.
Divergence at the edges can be silent, and generative tests drawn from ordinary distributions can
miss it. Prompted by pyarrow 26's decimal256 rounding returning wrong values on carry patterns
([CBO-015](libraries/pyarrow/README.md#applicability-cbo-015)).

<a id="lop-x004"></a>

## LOP-X004 — A compiled product leaves recurring derivations to its consumers

**Articulation.** A compiler, preparation or build step emits an immutable product. Its contract
omits derived facts that several consumers need repeatedly, so each consumer re-derives, re-indexes,
re-parses or re-adapts them from the product's raw fields. Some do this on every item, and each
does it with slightly different semantics.

**Recognize.**
- The same derivation from a product's raw fields in several consumer modules.
- Per-call construction of adapters, indices or parsed metadata from an immutable product.
- Linear scans over the product's tuples by name.
- Docstrings promising "once per product" at call sites that run per item.
- Private attribute access to recover what the product did not expose.

**Investigate.**
- Which derived facts are stable for the product's whole lifetime?
- Should they enter the product's archived identity, or remain a non-identity index built when the
  product is loaded?
- Can one product-side traversal or resolver replace consumer copies, while each consumer keeps its
  own policy?

**Counterconditions.**
- Derived facts that depend on consumer context do not belong in the product.
- Enlarging an archived or identity-bearing contract changes identities and compatibility.
- A cheap, rarely used derivation may not justify a contract change.

**What the base patterns missed.** LOP-07 frames the repetition at each consumer, and LOP-09 frames
it as fragmentation among consumers. Neither directs attention to the producer's output contract,
which is often the single place where a fix serves every consumer.

**Refinement (library assessment, 2026-10-29).**
- **Investigate:** does a re-derivation on the consumer side drop policy that the producer scoped to
  the container rather than to the extracted part? Configuration, strictness and finite-number rules
  are examples. In the observed case, a per-field validator extracted from a strict model accepted
  NaN and infinity, which the model itself refuses.
- **Countercondition:** a derived index placed on a nested record that the product serializes
  structurally enters archived identity even when it is excluded from equality. Put non-identity
  derivations on a root slot outside the archived projection.

Prompted by [CBO-013](libraries/pydantic/README.md#applicability-cbo-013).

<a id="lop-x005"></a>

## LOP-X005 — A database-derivable set round-trips through the client as a parameter list

**Articulation.** An operation reads a set of keys and sends it straight back to the database as
bind parameters, for example `.in_(previous_result)`. The same set was derivable inside the same
statement or snapshot.

**Recognize.**
- `IN (...)` over a collection built from an earlier query in the same transaction.
- Statement text or parameter count that grows with data size.
- Prepared statements that never get reused.

**Investigate.**
- Can a subquery, a CTE or a single array parameter (`= ANY(:array)`) carry the set instead?
- What hard ceiling applies? The PostgreSQL protocol limits a statement to 65,535 bind parameters.
- How does the varying text affect statement caching and server-side prepared statements?

**Counterconditions.**
- The set is filtered by policy that cannot be lowered into the query.
- The sets are small and bounded by contract.
- An array bind is a valid middle ground when the set really must originate in the client.

**What the base patterns missed.** LOP-04 and LOP-05 frame efficiency and planner intent. They do
not frame the *hard failure ceiling* or statement-reuse churn, which make this a robustness issue
rather than only an execution-fit issue.

<a id="lop-x006"></a>

## LOP-X006 — An explicit-input guarantee rides on a library resolver with an ambient fallback

**Articulation.** A purity or explicit-input guarantee depends on a library resolver. That
resolver consults the filesystem, network, installed package data or a user cache whenever the
explicit map does not contain the requested item. The library's default silently widens the input
boundary the caller believes it has.

**Recognize.**
- Pre-checks written by the caller before library calls.
- Loaders that are blocked or monkeypatched.
- Default selectors that download.
- Imports followed by default.
- Mappings to installed namespaces.
- "Materialize" or "derive" helpers that build fresh resolvers without the caller's explicit map.

**Investigate.**
- Does the library offer a refusal or offline mode?
- Can the explicit map be made total?
- Should one guard own every such resolver in the operation?

**Counterconditions.**
- The library has an offline mode that genuinely refuses.
- The fallback is part of the documented contract and acceptable for this consumer.

**What the base patterns missed.** LOP-10 frames friction with a library's model. It does not frame
the inversion in which the library's *default* behaviour enlarges the trusted input set without
any visible friction.

<a id="lop-x007"></a>

## LOP-X007 — Reused or cloned preparation silently drops state outside its copy boundary

**Articulation.** A prepared artifact is reused or cloned to avoid repeating preparation, such as
a template database, a snapshot, a cached object or a copied environment. But the original
preparation also wrote state outside what the copy mechanism copies, so the clone is not
equivalent to a fresh preparation. Documented examples include database-level grants and
`ALTER DATABASE … SET` parameters that `CREATE DATABASE … TEMPLATE` does not copy, cluster-wide
roles, and per-session temporary schemas.

**Recognize.**
- Reuse of preparation whose steps also wrote at an outer scope (cluster, database, process,
  session).
- Copy mechanisms with documented exclusions.
- Security or configuration posture established during preparation.

**Investigate.**
- List what the preparation writes, scope by scope.
- Compare that list with the copy mechanism's documented boundary.
- Replay the excluded state after every clone, or keep that preparation out of the reused artifact.
- Include the outer-scope inputs in any reuse key.

**Counterconditions.** The excluded state is irrelevant to the claims the clone serves, or it is
re-established anyway by every consumer.

**What the base patterns missed.** LOP-07 frames when reuse is valid by its premises and inputs. It
does not prompt a check of the copy mechanism's own boundary. A preparation can be valid to reuse
and still be reproduced incompletely.

Prompted by the TEMP privilege that revisions grant at database level, which a template clone would
lose ([CBO-010](libraries/postgresql/README.md#applicability-cbo-010)).
