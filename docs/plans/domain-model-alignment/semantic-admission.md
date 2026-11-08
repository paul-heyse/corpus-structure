# Semantic admission and derived-result validity

**Proposed · 2026-11-08.** D1/D2 own encoded meanings and D5 owns semantic
interpretation and eligibility. This plan supplies DMA-03–05. The
[coordinator](../domain-model-alignment_2026-11-08.md) owns disposition.
[Source review](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#govern-semantic-values-numerical-results-and-derivation-at-their-admission-boundaries)

<a id="DMA-03"></a>

## DMA-03 · Validate source-value structure before conversion

A source object encodes an ordered sequence of named values. Python rejects
noncontiguous positions and repeated names. Native aggregation by name can
discard both distinctions before comparing decoded content. LinkML and the
generated shape establish field types. Keep the recursive invariant with the
source-value codec and enforce it in native decoding before aggregation. Use
array ordinality to check zero-based positions and a grouped name check to
reject repeats. Recurse through values while decoding, rather than scanning
the same retained report repeatedly. Use the existing Python codec for its
own boundary and derive a native predicate only if the existing generator
can express the same invariant clearly. A local SQL implementation of that
contract is sufficient. Keep generic JSON conversion separate.

Apply the rule to affected native report entry points and portable consumers.
Avoid permissive normalization or interpretation of malformed old values.
Valid historical values retain their meaning. Affected invalid derived data
follows DMA-13.
[Python codec](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py#L110) ·
[Native codec](../../../python/corpus-structure/src/corpus_structure/semantic/sql/record_publication.sql#L20)

**Closure.** Submit valid nested values and independently construct resealed
position gaps, order changes and repeated names. Native completion and
ordinary and detached decoding agree on validity. No rejected input is
published. Include null, absent and false distinctions.

<a id="DMA-04"></a>

## DMA-04 · Make reported probabilities consistent with displayed support

Retain the existing finite interpreter, candidate-relative standing, native
request reconstruction and detached numerical replay. Add one
result-consistency contract to the interpretation owner. For an event or
requested marginal, sum the displayed assignment mass satisfying that
event or choice. The reported mass must lie between that sum and the sum
plus undisplayed mass, within the declared tolerance. When all positive
support is displayed the bounds coincide. A union counts a displayed
assignment once even when several derivations match. Keep exact completion,
bounded top-k display and unavailable or limited outcomes separate.

Apply the contract to Python construction and protected native admission
using the existing request and result guards. Check only the supplied
support and requested outputs in the admission transaction. Full solver
replay remains a separately advertised, stronger detached check. Readers,
CLI, MCP and export preserve the assurance actually established.
[Value validation](../../../python/corpus-structure/src/corpus_structure/semantic/local_interpretation_reports.py) ·
[Native admission](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql#L3029)

**Closure.** Use independently specified joint probabilities to verify a
valid partial display and a valid complete display. Refuse a resealed zero
event containing positive displayed mass, an overclaimed event or marginal,
and a union that double-counts. Retain the existing co-applicable notes,
units and nested headers, and the dossier's predecessor interpretation and
applicability controls. DA-055 and DA-057 supply preservation cases. The
older band-3 request reconstruction remains outside this new consistency
package. [Review reconciliation](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#govern-semantic-values-numerical-results-and-derivation-at-their-admission-boundaries)

<a id="DMA-05"></a>

## DMA-05 · Authenticate the claimed definition derivation

The definition component owner supplies the basis, exact input witness,
scoped source participants and resulting attachment. For a matched cue,
resolve the retained qualified cue and its actual roles. For native geometry,
check the required cue, adjacent display and source frame. Keep existing
model-reading reconstruction. Bind these facts in the released result and
verify them before native completion. A result without the needed witness
can retain an explicitly weaker candidate under the applicable policy.
Do not recreate model inference, substitute a nearby cue or derive public
eligibility from span authenticity. Public admission continues to require
its own independent evidence.

Migrate the definition producer, native validation, private Reader and its
CLI and MCP adapters, and detached verification together. Carry the exact
portable dependencies needed to check the basis. For old products, derive
a stronger basis only from retained authentic evidence. Otherwise preserve
their actual standing or regenerate under DMA-13.
[Definition producer](../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py) ·
[Native guard](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql#L1929) ·
[Public eligibility](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_publication.sql#L169)

**Closure.** A resealed component joining genuine spans without the claimed
cue or geometry refuses, including in detached verification. Positive
independent cases establish each supported basis and a weaker private
candidate. An independently adjudicated public case still passes through
the distinct publication route.
