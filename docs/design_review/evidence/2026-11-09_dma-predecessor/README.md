# DMA-13 retained predecessor qualification

The [DMA-13 disposition](../../../plans/domain-model-alignment_2026-11-08.md#dma-13)
owns predecessor eligibility and cutover. This development work reuses the
Standard and Nemotron integrated product from task 1627
(`35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`),
bound to the same 518-page original. Chandra is outside this qualification.
No new document intake or recognition ran.

On 2026-11-09 the [acquired database](raw/acquired-development.json) was
`corpus_structure_dev`, OID 25921445, port 5434, at
`semantic_pm2_contextual_queries`. The original DMA release
`675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56`
remains separately pinned. Run 404/cut 514 is its source-only reference;
run 407/cut 517 completed the full-book candidate execution over those same
29 views.

## Source-only extent

Run 407's meaningful chapter views include at least 33,222 characters and
1,093 native items per view. Reading only one sentence from one such chapter
does not cover the predictions supplied by the complete view. The original
[set 32 refusal](../2026-11-08_dma-audit-repair/raw/full_book_grade.json)
remains retained.

Protected [set 34](raw/full-view-freeze.json) freezes all of view 381 (Preface,
7,075 projected characters and 44 native items) and view 382 (Chapter 1
heading, nine characters and two items), selecting both by source extent and
role. The preface exercises qualified assertions and the heading is an
inspected no-reading control. [Packet 51](raw/source-51.json) and [packet
52](raw/source-52.json) contain no model output. The scope includes native
and projected coordinates, excludes synthetic separators, and does not assign
an absence decision to any unauthored view.

Existing retained M1 ingestion also supports a complete bounded native
subsection. [Source-only run 424](raw/section-source-run.json) sealed cut 527
with view 408 (`#/groups/590`, Moment Generating Functions), a complete
541-character projection of 11 native items under the same integrated
product and projection recipe. [Protected set 35](raw/section-freeze.json)
and [packet 53](raw/source-53.json) bind that exact view. This route can
replay the incumbent stages over an explicitly corresponding native source
extent; it does not crop predictions from chapter view 401.

Both sets are development controls from one known source origin. The retained
whole-book incumbent predates this freeze and the earlier sentence challenge
was already exposed. No grade here can establish held-out quality or a
performance conclusion over the full book.

The frame preparer uses the existing run-bound Reader and protected source
binding. It reads only cut membership, source pins and published item
metadata. Installed `ci golden record-create` revalidates the frame and
records it under evaluator authority. For these initial freezes the CLI had
not yet reported protected unit IDs, so a bounded read of
`eval.reference_unit` located the exact IDs for the packet commands. Current
record creation returns those IDs in its ordinary receipt.

## Acquired target and preserved reads

On the recorded development revision, the explicit archived DMA release
[verified](raw/dma-release-archive-check.json). The ordinary read-only
[native check for that archived release](raw/dma-release-native-check.json)
refused with SQLSTATE 42501: the deployment has its prior admission, but no
admission for that release under the current guard descriptor. The
[same native check](raw/pm2-release-native-check.json) passed for the already
admitted PM2 release. Archive verification and readable historical cuts
are separate from eligibility on the acquired current target.

The exact p416 formula [CLI response](raw/source-p416.json) returned
`source_ready` and one row. A [fresh MCP process](raw/source-p416-mcp.json)
returned the same complete Reader response and refused a changed integrated
product digest. The prior selected-source closure bundle
`ea341ab7e1164874b00f6a3c1c44fa31` [verified again without the
database](raw/retained-detached-inspect.json), binding run 407/cut 517 and
1,107 source proof rows for the title view.

The [focused CLI and native record checks](raw/record-reference-tests.json),
managed result `647b994391b343e6a29b7fb3b278b859`, passed 41 selected
tests, including two-view source binding and guarded reference custody.
They do not account for the ordinary, fault, Rust and applicable provider
union for assembled qualification.

## Protected readings

[A](pass-a-source-reading.md) and [B](pass-b-source-reading.md) read the
frozen source without predictions or each other's readings. C adjudicated
their independently stored bytes and only then opened native grading.
The [adjudication account](pass-c-adjudication.md) preserves the negative
heading and meaning-changing conditional roles, rejects unsupported
nested attribution, and keeps flattened formula limitations explicit.

| Set | Unit | A | B | C | C readings |
| --- | --- | --- | --- | --- | --- |
| 34 | 51 | 135 | 153 | 156 | Assertion and illustrative trial bound |
| 34 | 52 | 136 | 154 | 157 | Inspected zero-reading heading |
| 35 | 53 | 137 | 155 | 158 | Definition, qualified assertion and three located formula bindings |

B's initial serialization incorrectly tagged the inapplicable supplemental
normalized field as meaning-changing. Native validation refused that exact
submission. The [original refusal](raw/first-b-submission/pass-51-b.log)
is retained; correcting the serialization flag kept B's source decision
unchanged. The protected retry stored the independently authored reading.

## Native grade of the retained full-book run

`uv run ci eval run --run 407 --set-id 34 --project nce-grinstead-snell-full-book --json`
passed on 2026-11-09 and persisted [evaluation 42](raw/full-view-grade.json).
Exact whole-view alignment succeeds for these two units without repeating
the earlier sentence/whole-view mismatch. The preface had two independent
readings, zero accepted predictions and zero core, full or evidence matches.
Both readings were missing in the native gap account. The heading had zero
reference readings and zero accepted predictions. Each producer report
was `produced` and retained one private candidate, so neither view is an
unattempted producer case. The [preface candidate](raw/records-381.json)
uses an unrelated assertion and the [heading candidate](raw/records-382.json)
treats a chapter title as a definition. Both retained private candidate
standing. Quality remains `not_established`; run 407 is not eligible.

## Matching bounded replay on the admitted release

After deployment `b560839795524057ad2a12183eb90649` reached
[`semantic_pm2_definition_scope`](raw/post-repair-development.json),
the run-bound Reader regenerated both source-only sample files byte for
byte. The existing CPU M1 routes then processed the exact native
subsection over the current admitted release. Run 437's retained projection,
annotation and candidate tasks [settled](raw/section-task-settlement.json)
as 2139, 2140 and 2141. [Finalization](raw/section-finalize.json) sealed
private cut 537 with six reports and zero occurrences.

`uv run ci eval run --run 437 --set-id 35 --project nce-grinstead-snell-full-book --json`
passed on 2026-11-09 and persisted [evaluation 43](raw/section-grade.json).
The native binding authenticated the exact physical correspondence
between old view 408 and current view 409, with unchanged product,
projection and recipe. The producer report settled as `produced`,
but all five protected readings were graded `no_output`: the definition,
qualified assertion and three located formula bindings. No accepted
prediction or match is claimed. Successful exact grading and reader
custody do not qualify the predecessor; the candidate/reading path
must first preserve the protected source readings. The broad final
qualification union and project selection did not run in this slice.

The [ordinary Reader](raw/section-reader.json) retained both producer
reports and returned zero records. Exact-closure detached result
`cc5cf964cae84b5ca41257f58de52b20` [verified offline](raw/section-review-inspect.json):
one selected candidate report and 1,107 source proof rows, bound to
run 437/cut 537. Protected labels were not included in this delivery.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**dma-predecessor**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Current admitted bounded DMA predecessor replay and grade](records/dma.predecessor-bounded-grade.json) | DMA-13 | partial | DMA-13 | 2026-11-09 |
| [Protected whole-view grading of the retained DMA predecessor](records/dma.predecessor-whole-view-grade.json) | DMA-13 | partial | DMA-13 | 2026-11-09 |
<!-- evidence-index:end -->
