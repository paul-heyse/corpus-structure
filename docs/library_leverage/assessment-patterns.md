# Additional assessment patterns

Additional opportunity patterns discovered during assessment. They are used alongside the
[base patterns](patterns.md) (LOP-01–LOP-12, edition 0.2), with the same reasoning role and the
same limits: a match nominates an investigation; it does not establish a defect, a library fit or
an obligation to adopt. The [framework](library-leverage-framework.md#discover-and-collect-additional-patterns)
owns their lifecycle. Promotion into the base set is a separate, manual operator decision.

**Revision history.** First created by the initial [codebase audit](codebase/README.md) on
2026-10-29 (source baseline `9f8df02`, reconciled through `f697233`). The originating
observations are cited with that baseline; each definition is meant to make sense without them.

| ID | Pattern | First prompted by |
|---|---|---|
| [LOP-X001](#lop-x001) | Surviving code adapts into a retiring model to reuse its kernel | [CBO-005](codebase/consumers-and-operations.md#cbo-005), [CBO-006](codebase/consumers-and-operations.md#cbo-006), [CBO-018](codebase/storage-and-analytics.md#cbo-018) |
| [LOP-X002](#lop-x002) | A frozen derived artifact loses its derivation route | [CBO-008](codebase/storage-and-analytics.md#cbo-008), [CBO-014](codebase/storage-and-analytics.md#cbo-014) |
| [LOP-X003](#lop-x003) | Mirrored implementations across an enforcement boundary | [CBO-015](codebase/storage-and-analytics.md#cbo-015) |
| [LOP-X004](#lop-x004) | A compiled product leaves recurring derivations to its consumers | [CBO-013](codebase/release-preparation.md#cbo-013), [CBO-016](codebase/consumers-and-operations.md#cbo-016) |

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
