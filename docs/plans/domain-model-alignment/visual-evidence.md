# Visual nomination, recovery and bounded delivery

**Proposed · 2026-11-08.** D3/D4/D6/D8 govern source custody, request
execution and Reader delivery. This plan supplies DMA-09–11. The
[coordinator](../domain-model-alignment_2026-11-08.md) owns disposition.
The workload is an authenticated 518-page parent with overlapping page
and crop scopes, bounded groups and a shared GPU. Raw recognition,
candidate mapping, explicit inspection and the selected incumbent keep
their existing distinct authority. [Source review](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#separate-a-visual-observation-from-the-work-and-views-built-from-it)

<a id="DMA-09"></a>

## DMA-09 · Record why work was nominated before dispatch

The page-level assessed flag can conceal an unavailable cue. The CLI
also emits routine routing reasons only after dispatch, while native
groups keep the requested scopes and execution identity. An interruption
or a later policy change can leave the original decision unrecoverable.

Make the routing policy version and its required cue coverage explicit.
Retain assessed positive, assessed negative, inconclusive and unassessed
distinctions per applicable cue, with reason and exact source evidence
when available. Missing, unsupported and over-budget inputs do not count
toward required negative coverage. A supported positive cue may nominate
work even when a different cue remains unassessed. An independently
verified blank keeps its own reason.

Freeze the policy, source/cut pins, considered range, cue coverage and
decisions as native versioned run inputs before dispatch. Use existing
run custody and reference that decision from group members. Retain the
decision even if no group is nominated. Resume uses the frozen decisions. The inference key still reflects recognition
determinants, so a changed routing rationale alone does not invalidate
exact raw inference. The dispatch report and by-ID view project the
same authoritative decisions and actual effect progress through DMA-08.
Keep intentional explicit requests distinct from policy nominations.
[Routing](../../../python/corpus-structure/src/corpus_structure/semantic/visual_routing.py) ·
[Dispatch](../../../python/corpus-structure/src/corpus_structure/semantic/visual_dispatch.py) ·
[Review F01](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#F01)

**Closure.** Keep A/B and selected content fixed while one crop cue
becomes missing or oversized. Show an unassessed result, an independently
verified blank, and a supported positive route with another cue unknown.
Interrupt a dispatch after a group settles. Resume from the exact
nomination. Change only policy or reasons and verify that both decisions
are attributable and the unchanged inference can reuse its raw response.

### Completion audit follow-up

**F01 · Source-inspected · 2026-11-08.** The native nomination is retained.
The managed by-ID view carries its ID and returned group IDs, while the
immediate result carries cue coverage and route decisions. Group progress
is added after the group returns. An interruption within a group can
leave committed raw or mapped effects outside the by-ID account. Derive
the same decisions and observable effects from native custody in both
views, including empty nominations and an interrupted active group.
Verify by interrupting after a member settles and comparing immediate
or resumed output with independent native state and by-ID inspection.
[Dispatch progress](../../../python/corpus-structure/src/corpus_structure/semantic/visual_dispatch.py#L224) ·
[Managed routing projection](../../../python/corpus-structure/src/corpus_structure/cli/managed.py#L299)

**DA-064 · Source-inspected · 2026-11-08.** A positive crop disagreement
can still overwrite the availability reason for another crop on the same
page when the router collapses them into one cue. Preserve coverage by
scope alongside the valid positive nomination. Verify a mixed page
whose positive and missing or oversized crop both remain inspectable.
Also qualify a policy-version change against retained old decisions and
ordinary raw reuse when recognition determinants match. The resume
parser accepts the current policy literal, and ordinary reuse keys on
the whole runtime. Explicit raw replay establishes its narrower route.
[Cue aggregation](../../../python/corpus-structure/src/corpus_structure/semantic/visual_routing.py#L783) ·
[Nomination resume](../../../python/corpus-structure/src/corpus_structure/semantic/visual_dispatch.py#L79) ·
[Ordinary reuse](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py#L293)

<a id="DMA-10"></a>

## DMA-10 · Reuse settled visual work before acquisition

Resolve native group, member and stage settlement before preparing
unsettled dependencies. Reuse the singleton's exact retained PNG and raw
response path for mapping after settled inference. A mapping-only
implementation change can reuse a raw response under the same
recognition determinants. It must use its own mapping identity.
Check the exact original and structural pin without reacquiring full
PDF bytes for a stage that does not render. For genuinely new work,
share authenticated original and compatible page preparation within
the useful group lifetime. Keep scope, render, crop and orientation
determinants distinct. Acquire the checkpoint and GPU only for needed
recognition, with the existing bounded cancellation and release scope.

At protected settlement, reference the already retained original and
exact structural input under task, attempt and holder fences. Keep the
initial PDF intake byte path where it has to establish custody. Remove
per-observation whole-PDF submission when the native reference route can
prove the same original, project, page and region. Separate raw
recognition, mapping and publication settlement. Failure or cancellation
keeps completed effects and exact recovery points visible.
[Visual recovery and settlement](../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py) ·
[Native observation custody](../../../python/corpus-structure/src/corpus_structure/semantic/sql/pdf_observation.sql)

**Closure.** Interrupt after inference and resume mapping with provider
artifacts unavailable. Observe no render or checkpoint preparation.
Exercise same-page whole and crop scopes, wrong source and stale attempt
refusals, and cancellation that releases the bounded GPU lease. Use an
independent transfer observation to show that fresh derivative
settlement references the retained original without resending its bytes.

### Completion audit follow-up

**DA-058 · Source-inspected · 2026-11-08.** Settled inference can reopen
its retained raw response for mapping. For fresh compatible whole-page
and crop requests in one group, the original bytes are shared but each
member opens and rasterizes the same full page before crop and
orientation are applied. Share compatible page preparation for the
group lifetime while retaining distinct crop and rotation identities.
Verify an independently counted single page render for compatible
scopes, exact outputs for each scope, and mapping-only recovery with
provider inputs unavailable.

A fresh group or new nomination still prepares the checkpoint and
raster before task creation discovers a reusable raw result. Missing
checkpoint files can prevent that reuse even when an earlier exact raw
result exists. Resolve reusable raw work before acquisition where the
recognition determinants can be established, retaining the exact
runtime fence. Exercise ordinary group dispatch with a compatible raw
result and unavailable provider files, plus a refusal for changed
recognition inputs. The fresh-settlement transfer control and the live
GPU cancellation and release control remain required at the applicable
runtime. Earlier live cancellation evidence retains its original
provider and runtime scope.
[Group execution](../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py#L995) ·
[Fresh task preparation](../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py#L1333) ·
[Page raster path](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_visual_mapping.py#L29)

<a id="DMA-11"></a>

## DMA-11 · Give typed visual addresses bounded native reads

Mapped observations can reach the accepted aggregate row limit, while
a typed read charges custody and scans every row before applying an
exact selector. Use a protected derived PostgreSQL locator and indexed
rows tied to the exact mapped artifact. Reuse native PDF access patterns
and relational keyset reads where the visual address is the same kind
of physical mechanism. Preserve occurrence multiplicity, region
precision and original cell indexing. Validate locator completeness,
ordering and payload correspondence once at publication under the
same custody. Rebuild it from authenticated retained mappings when
necessary. A whole-artifact scan per request is unsuitable. A compact
authenticated sidecar would be viable only if it supplies equivalent
bounded lookup and proof of closure with lower integration burden.

Use the exact source, observation, mapped digest, selector and scope to
bind item, cell, figure and continuation reads. Use native access paths
and bounded work for discovery as well as exact addresses. A result
limit does not bound examined work. Preserve honest over-budget refusals,
raw and PNG byte-page routes, and typed candidate standing. Update
Reader, CLI, MCP and the explicit packet together. Verify earlier
continuations under their supported contract or refuse with an explicit
version mismatch where the contract permits.
[Current full scan](../../../python/corpus-structure/src/corpus_structure/serve/pdf_visual_evidence.py#L715) ·
[Native record Reader](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py)

**Closure.** On a valid artifact near the aggregate limit, retrieve a
specific item and cell and paginate a typed selection without scanning
unrelated candidate bodies. Exercise skewed figures or rich cells, wrong
pins, wrong cursors, exact region bounds and genuine work or output
refusals. Compare independent occurrence and cell expectations through
the actual Reader, CLI, MCP and packet. The ordinary selected source
Reader remains independently authoritative.

### Completion audit follow-up

**DA-066 · Source-inspected · 2026-11-08.** Exact locator and p151 delivery
evidence stand. Region filtering reads geometry from row bodies, and
the row budget charges rows after filtering. A narrow or empty region
can therefore examine off-scope candidate rows across the pinned
artifact. Establish a scoped native access path or an honest bound on
the examined work before body reads. Check sparse and empty regions on
a near-limit artifact under an independent examined-work expectation,
and verify the Reader, CLI, MCP and packet paths at that scope.
[Region filtering and row accounting](../../../python/corpus-structure/src/corpus_structure/serve/pdf_visual_evidence.py#L819) ·
[Dense locator control](../../../python/corpus-structure/tests/semantic/test_pdf_visual_requests.py#L421)
