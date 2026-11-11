# Source-anchored semantic task panel

**Source frames and independent A/B passes frozen; C adjudication in progress · 2026-11-11.**
The [coordinator](../../../../plans/text-characterization_2026-11-10.md) owns TC-E05 and acceptance.
This is the explicit task-wire refinement of the original [source-first panel](../panel/README.md).
It supplies no producer-quality claim.

## Population and custody

Reference set41, units82–102, preserves the original26 opportunities across21SourceViews and
all12chapters. [Sample](sample.json) and [native receipt](frozen-reference-set.json) retain the
same source496/cut614, original pins, ordered extents, source groups and questions. Only the
guideline, operation/rubric version and explicit applicability provenance change. The original
set40 and A/B/C210–230 remain immutable. The [preparation script](prepare_frames.py) copies
the frozen selection; it performs no new source nomination or answer translation.

The [binder supplement](binder-supplement/README.md) is separately frozen as set42,
units103–104. Its two source-only questions assess the actual declared binder-to-variable-site
family. The original anaphoric questions remain visible with their family/contract limitation;
they cannot be coerced into variable binding or counted as successful semantic assessment.

The [formal supplement](formal-supplement/README.md), set43/units105–106, retains the original
symbol and written-comparison source opportunities under their actual `formal.math` family.
It does not reinterpret inequalities as intervals or generic mathematical symbols as labeled
identifier fields. The [binary control](binary-formal-control/README.md), set44/unit107, adds
one source-only written binary formula with unambiguous operand order. This settles an
independent operator/order question without forcing an association for the original longer chain.

Across sets41–44, both independent authors have signed26 protected passes for31 opportunities.
[A's receipt](author-A-receipt.json) and [B's receipt](author-B-receipt.json) retain exact pass IDs,
digests, reuse lineage, unavailable comparisons and partial claims. A's final binary pass is281;
B's is282. These are reference-authoring outcomes, not producer grades. Original source frames,
earlier passes and their limits are unchanged. No further source-panel expansion is selected.

## Comparison contract

The [version2 guideline](../../../../../domains/statistics/characterization-task-reference-guideline.md)
and the public `SemanticTaskReference` schema define source entities, role schemes, inspected
focus, witness versus complete named slots, conditional assertions and factorized choice queries.
Exact producer graph decomposition is not the reference language. Source-only authors choose
their expectations before grading; declared adapters read retained meanings without new NLP.
Undefined adapters remain unavailable, while missing relationships under a defined adapter are
real source-first misses. Native fidelity and retained identity retain exact graph comparison.

Authors A and B keep independent source-only contexts. They may reuse their own unchanged
native task references or formal scalar assertions only with precise prior-pass lineage and
new-frame signing. New semantic task assertions come from the original source and public wire
meanings. C receives their new protected passes for adjudication. No answer is adjusted using a
producer output, and no source case establishes a future runtime or replay outcome.

The original authoring exposed a representation mismatch before grading. The new authoring
also identified explicit contract limits, including directed anaphora versus binder-site hypotheses
and object-level disjunction versus analytical choice. Those limits are recorded rather than
relabelled into supported tasks. Outbound source-specific wire questions to the implementation
worker are recorded in each author's receipt; they did not expose producer answers or the other
author's reading to either author. Production cannot consume these protected labels.

## Reproduction

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/prepare_frames.py
uv run ci golden operation-create --from-run 496 --source-cut 614 \
  --label tc10-chapter-facet-task-panel-2 --split dev \
  --guideline characterization-reference-2 \
  --guideline-text domains/statistics/characterization-task-reference-guideline.md \
  --partition development \
  --sample docs/design_review/evidence/2026-11-11_text-characterization-assessment/task-panel/sample.json \
  --project nce-grinstead-snell-full-book --json
```

The recorded invocation **passed** and returned set41. Reproduction is not authority to mutate
its frozen frames. Reference submission, adjudication and grading have their own immutable
identities and outcomes; this page's creation receipt establishes source/frame custody only.
