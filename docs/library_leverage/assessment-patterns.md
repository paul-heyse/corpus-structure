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
- **Extended** by the first [comparative review](reviews/README.md) on 2026-10-29, source baseline
  `0350a7a`:
  - added LOP-X008–X011;
  - refined LOP-X001, X002, X006 and X007 where comparing complete options exposed a missed
    distinction.

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
| [LOP-X008](#lop-x008) | A declared invariant is stood in for by a recheck | [CBO-019](codebase/storage-and-analytics.md#cbo-019), [CBO-003](codebase/release-preparation.md#cbo-003) |
| [LOP-X009](#lop-x009) | A consumer re-runs the producer to trust an immutable product | [CBO-003](codebase/release-preparation.md#cbo-003), [CBO-009](codebase/release-preparation.md#cbo-009) |
| [LOP-X010](#lop-x010) | A replacement boundary grows beside the kernel's public route | [CBO-001](codebase/consumers-and-operations.md#cbo-001) |
| [LOP-X011](#lop-x011) | Outcome evidence is written only at orderly completion | [CBO-011](codebase/engineering-workflows.md#cbo-011) |

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

**Refinement (comparative review, 2026-10-29): two kernels are a symptom.**
- The pattern can also show up as a new-model consumer writing *its own* kernel instead of adapting
  into the old one.
- **Investigate:** do the two copies give the same outcome for the same inputs? Separate the shared
  evidence (what the kernel reports) from each consumer's policy (what that evidence decides), and
  give the kernel one owner.
- In the observed case, the two kernels disagreed on whether numeric agreement proves equality, and
  one of them drives selection.

Prompted by [CBO-006](reviews/retirement-dependencies.md#cbo-006).

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

**Refinement (comparative review, 2026-10-29): name the freeze point.**
- Frozen artifacts can have an informal edit window. An in-place edit of a committed artifact that a
  retained database has already applied creates drift *between databases*. A check on a fresh
  database never sees it.
- Hand-written names that embed a digest of an expression lose fidelity once the expression is
  edited and the name kept.
- **Investigate:**
  - Where does the freeze begin?
  - Does a corrective artifact converge every history? For example, drop and re-add from the
    authority rather than rename.
  - Does any drift check run against long-lived databases, not only fresh ones?

Prompted by in-place edits of committed migration revisions under
[CBO-008](reviews/native-integrity-and-execution.md#cbo-008).

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

**Refinement (comparative review, 2026-10-29): repository-owned derivations.** The same widening
shape occurs without a library. A credential or capability derivation can fall back to a broader
principal when its expected input is absent. In the observed case, a read connection fell back to
the configured login whenever that login was not the expected writer, so an owner URL silently read
with owner powers.
- **Investigate:** does the derivation refuse when it cannot produce the declared principal? Does
  the opened connection check what it actually got?

Prompted by [CBO-004](reviews/engineering-workflows.md#cbo-004).

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

**Refinement (comparative review, 2026-10-29): assert equivalence where the clone is made.** Assert
that the clone matches the template for the excluded state inside the fixture or factory that
clones. No downstream test may observe the loss. In the observed case, nothing in the suite checked
the database-level privilege the clone dropped, so a clone without replay would have passed every
test. Prompted by [CBO-010](reviews/engineering-workflows.md#cbo-010).

<a id="lop-x008"></a>

## LOP-X008 — A declared invariant is stood in for by a recheck

**Articulation.** A design declares an invariant that nothing natively enforces, for example "these
rows are immutable once admitted". In its place, a whole-state revalidation or recomputation runs
on each later operation. The recheck catches violations only incidentally:
- late, at the next operation that happens to run it;
- never after the last one;
- at a cost that grows with accumulated state.

Persisting derived keys or recording a verification is then unsound, because nothing guarantees the
inputs stayed put.

**Recognize.**
- Loops that recompute identities or meanings for *all* existing rows on each batch.
- Comments or decisions saying rows "are immutable" with no trigger, grant or constraint behind them.
- Derived values recomputed by every consumer instead of stored, because nobody trusts storage.
- Write grants that the declared invariant says should never be used.

**Investigate.**
- Can the invariant be enforced natively, for example with refusal triggers or grant revocation?
- Can the guard itself be verified by the existing catalog or admission checks, so that a disabled
  guard is refused?
- Which parts of the recheck defend only the invariant, and which carry a legitimate cumulative
  obligation? For example, newly added memberships can change which constraints apply to old rows.
- What becomes possible once enforcement holds: persisted derived keys, recorded verification,
  narrower checks?

**Counterconditions.**
- A legitimate correction or retention workflow needs in-place change.
- Owners and superusers can always bypass native guards, so enforcement narrows the threat rather
  than removing it.
- A cumulative recheck may still be required even with the invariant enforced.

**What the base patterns missed.**
- LOP-07 frames repeated work valid under unchanged premises, but not the case where the repetition
  *is* the only thing standing in for an unenforced premise.
- LOP-X003's deliberate mirrors defend a trust boundary. Here the recheck defends against writes the
  design says cannot happen.

Prompted by [CBO-019](reviews/native-integrity-and-execution.md#cbo-019) and the
[shared immutability decision](reviews/native-integrity-and-execution.md#sem-immutability). The
decision also conditions [CBO-003](reviews/release-lifecycle.md#cbo-003).

<a id="lop-x009"></a>

## LOP-X009 — A consumer re-runs the producer to trust an immutable product

**Articulation.** Every use of an archived, immutable product re-runs its producer and compares the
result. Loading therefore:
- needs the whole production toolchain;
- refuses on producer library-version labels;
- regenerates outputs that the consumer never reads.

Verification and opening are fused into one operation, run at every use.

**Recognize.**
- A load that re-prepares and compares.
- Refusals keyed on library version labels at load time.
- Unused artifacts regenerated on load.
- Identity bound to labels whose effect the content already captures.
- Consumer-local caches that exist mainly to avoid the load's cost.

**Investigate.**
- Split producer-side verification (at archival, activation, run start or on explicit request) from
  consumer-side opening (the archived product plus a cheap integrity check).
- Which determinants actually shape consumer-visible bytes or behaviour, and which only gate
  acceptance?
- What does the product omit that prevents rebuilding the runtime boundary from it
  ([LOP-X004](#lop-x004))?
- What integrity guarantee does opening rely on ([LOP-X008](#lop-x008))?

**Counterconditions.**
- Adversarial writers and a mutable archive, where derivability at every use *is* the guarantee.
- Runtime objects that cannot be rebuilt without source-level information.
- A cheap producer, for which the coupling costs little.

**What the base patterns missed.** LOP-07 frames the lifetime of preparation. It does not frame
*which operation* verifies, or the dependency coupling that ties every reader to the producer's
toolchain.

Prompted by [CBO-003](reviews/release-lifecycle.md#cbo-003) and
[CBO-009](reviews/release-lifecycle.md#cbo-009).

<a id="lop-x010"></a>

## LOP-X010 — A replacement boundary grows beside the kernel's public route

**Articulation.** A new consumer layer is built on a kernel's *private* internals, while the
kernel's own public route keeps only test callers. Two contracts then coexist, such as:
- two continuation or identity schemes;
- two resolvers;
- two caches.

External authors may already import the private names, which turns them into an unacknowledged
API.

**Recognize.**
- Imports of underscore names from a kernel, including from plugins or packs.
- A public API whose only callers are tests.
- Parallel token, cursor or identity formats.
- Duplicate adapter or resolver caches that choose differently.

**Investigate.**
- Which route holds the authority?
- Which primitives does the new layer actually need? Promote those, keep policy in the consumer
  layer, and retire the duplicate scheme.
- Move the old route's *independent* test expectations onto the survivor rather than deleting them.

**Counterconditions.**
- The old route may be the only independent oracle for its tests.
- Retiring it must not collapse distinctions it carried. In the observed case, it distinguished a
  stale snapshot from a wrong release.
- Moving serving policy into the kernel can be worse than the duplication.

**What the base patterns missed.**
- LOP-09 frames fragmentation among peers.
- LOP-X001 frames a backward edge into a *retiring* model.

Here the kernel is current and authoritative, and the new layer bypasses its public contract.

Prompted by [CBO-001](reviews/consumer-read-boundary.md#cbo-001).

<a id="lop-x011"></a>

## LOP-X011 — Outcome evidence is written only at orderly completion

**Articulation.** A route must classify the outcome of every item, but its report artifact is
written only when the run ends normally. The report is missing in exactly the failures the route
most needs to classify: hang, crash, kill or watchdog exit. The route then falls back to "missing
report means failed", which loses every completed outcome and forces a rerun.

**Recognize.**
- Reports in XML or JSON written at session end.
- `os._exit` watchdogs.
- "Missing report means failed" rules.
- Outcome vocabularies (`not_run`, `blocked`) that the report format cannot express once a run is
  interrupted.

**Investigate.**
- Can each item's record be streamed and flushed as it completes?
- Is the collected manifest recorded first, so that an item with no record classifies as `not_run`?
- Is there an end-of-run marker, so that its absence marks an interrupted run?
- Do the watchdog and the code under test compete for the same timer or signal?

**Counterconditions.**
- The run is cheap to repeat.
- Outcomes are genuinely all or nothing.
- Streaming adds a dependency that its benefit does not justify.

**What the base patterns missed.** LOP-08 frames failure lifecycles coordinated locally, but not the
*failure-time availability of evidence*: how much of an interrupted run can still be classified.

Prompted by [CBO-011](reviews/engineering-workflows.md#cbo-011).
