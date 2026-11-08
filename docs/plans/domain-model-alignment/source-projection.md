# Source projection and retained formula witnesses

**Proposed · 2026-11-08.** D3/D4 own the selected PDF and its projection. This
plan supplies DMA-06 and DMA-07. The [coordinator](../domain-model-alignment_2026-11-08.md)
owns disposition. [PDF scope and authority](../../design/DESIGN.md#section-b5)

<a id="DMA-06"></a>

## DMA-06 · Verify the required text inventory

Item membership and authentic supplied spellings are necessary. The current
native guard can still accept a first projection that omits ordinary prose
and reseals the remaining text, offsets and digest. Packet validation then
authenticates the incomplete projection as its source.

Have the released section projection define the ordered field addresses for
a selected scope. The address identifies the occurrence, source field and
qualified cell position where relevant. The native publisher derives the
expected addresses from authenticated selected records using the released
policy. Compare order and multiplicity before validating submitted text,
extents and separators. Share the semantic policy and field eligibility with
the projector. A producer-supplied list or hash alone cannot authenticate
coverage. Reuse native section membership, caption checks and indexed
record access. Compose the expected addresses without reconstructing a
second complete text artifact. This keeps work bounded to the section's
actual selected input rather than repeatedly traversing unrelated pages.

Cover direct and descendant scopes, residual body, furniture exclusion,
rich-cell subtrees, chart fields, formula spellings and caption placement.
Retain exact source links and distinguish intentionally excluded fields from
omitted required text. Migrate source search, source packets, downstream
interpretations and detached verification to the same immutable projection.
Make historical retention and current execution eligibility separate
under DMA-13.
[Projector](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py) ·
[Native publication and frame guard](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql) ·
[Review F02](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#F02)

**Closure.** From a fresh first publication, omit one nonempty prose field
and reseal the output with the original item inventory. Refuse that case,
a repeated or reordered required address, and a fabricated field spelling.
Accept valid exclusions, the current caption and formula cases and an
exact idempotent replay. Follow an independently specified text fragment
through Reader, source search, packet and downstream interpretation.

### Completion audit follow-up

**F02 · Source-inspected · 2026-11-08.** Native publication derives the
ordered field inventory. Detached verification still lets the submitted
row select its own assurance level. Removing `projection_inputs` and
claiming `selected_projection_only` bypasses current inventory replay.
Even with replay requested, the supplied recipe and frontier can
classify an omitted native item as excluded without authenticating that
classification against the selected product. Bind replay requirements
to the archived contract and the membership and excluded frontier to
the selected product. Verify refusal of resealed current bundles that
drop a required field by downgrading coverage or by fabricating the
frontier. Preserve valid current replay and supported archived reads.
[Detached replay branch](../../../python/corpus-structure/src/corpus_structure/serve/review_source_projection.py#L62) ·
[Archived contract capture](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py#L150) ·
[Bundle verification](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py#L2599)

<a id="DMA-07"></a>

## DMA-07 · Resolve readable originals from their exact retained policy

Replace the singleton global witness with a released collection of
source-local witnesses. Each witness binds the authenticated original,
qualified occurrence, frame or locators and exact original-spelling
digest. Require correspondence to the selected product before applying
a witness. A product change elsewhere may preserve the witness only when
those premises still correspond. Preserve the product digest for delivery
and provenance. Refuse ambiguous or mismatched witnesses. The ordinary
recognized text, source-verified readable spelling and positioned or
mathematical interpretation remain distinct.

Apply the same released witness decision to section preparation, the
DMA-06 address check, native publication and formula inspection. For a
supported archived PDF, resolve the policy and witness from the exact
retained release or its versioned projection. Remove reliance on an
installed recipe match for that read. Preserve the supported p416 v9
representation when the successor is installed. Use the existing retained
recipe and release custody, rather than a separate witness store or a
historical semantic executor.
[Installed recipe dependency](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py#L239) ·
[Exact formula Reader](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py#L582) ·
[Current-only decision](../../adr/0067-witnessed-current-only-cutover.md)

**Closure.** Add a second independently checked witness. Change unrelated
selected content and demonstrate the preserved correspondence. Changing the
occurrence, frame or spelling must invalidate reuse. After a successor
recipe is installed, the explicitly supported archived p416 response
preserves its prior readable and recognized forms. Rebuilt current search
and packets use the new exact projection.

### Completion audit follow-up

**DA-061 · Source-inspected · 2026-11-08.** The released witness
collection and archived policy lookup are implemented. The current v10
recipe contains one released witness. The two-witness fixture builds both
digests from artificial native original text. It establishes collection
behavior and scoped refusals, with no independent second released
original. The p416 archived response and current exact Reader have
bounded evidence. Qualify an independently checked second witness and
its occurrence substitution refusal. Trace the rebuilt current recipe
through search and packet delivery on the same source cut.
[Witness collection control](../../../python/corpus-structure/tests/ingest/test_pdf_body_selection.py#L124) ·
[Development adoption](../domain-model-alignment_2026-11-08.md#development-adoption-on-2026-11-08)
