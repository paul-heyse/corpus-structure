# Archive and witnessed overlay study

**Tested · 2026-11-08.** The study reader used the exact integrated archive from
producing run 309, task 1389, and validated the five overlay entries against the
retained original and the archived producer's Reader. Overlay digest
`c857d4b3cfdc8513ef199d1f19854d2d00ecf9d8e64a35557758936872c9f593`
was shared by the incumbent-only, explicit, selective and all-page arms.

The dry scan covered all 518 physical pages in nine ranges. It nominated 92
pages for recognition and 13 for incumbent repair, and skipped 413. Relative
to the raw archive v2 scan, p108 moved from recognition to skip after matching
the shared caption and the two located panels. At p151 the overlay resolved
the missing-table trigger and retained the independent disagreement trigger.
The 515-character readable p416 formula left the position-dependent triggers
in place. P506 retained its verified-blank disposition. The study froze 15
additional crop selections, all from existing archive addresses. New overlay
occurrences have whole-page scope.

Exact protected reads compared retained mappings from run 354 for pp1 and
506, and run 362 for p151. The first two nominated no differences. At p151
one Chandra table matched the witnessed Table 4.2 location and values but
differed in empty-cell and row-header representation. The comparison marked
it for source review and attributed the table recovery to the incumbent.
All three observations retained their recorded provider outcome `unknown`.
The explicit, selective and all-page arms compared 1, 1 and 3 scopes
respectively, with 4, 93 and 515 scopes unassessed.

The amended witness and the adoption run substituted for the producing run
were both refused. The ordinary archived formula Reader returned the exact
prior 54,318 bytes with SHA-256
`a74c463c98c1f4dc3e6bef4efb6d2ebc548c62e485d080e256a7758df1d34629`.
These results establish the study route and bounded retained comparison.
Selected publication and ordinary consumers of a repaired product require
their separate qualification.
[Original witnesses](incumbent-recovery.md#original-source-witnesses) ·
[Ordinary archived read](nemotron-mapper-control.md)

## Replay the study

Use an empty destination. The archived pin and bounded group controls come
from the retained receipts.

```sh
evidence=docs/design_review/evidence/2026-11-08_chandra-execution
study=build/chandra-execution/archive-overlay/replay
release=release:7a8352c383c2c6f07fb6d2ed10246466c60faf6db4d382f9cd61b29ed8dc0744
mkdir -p "$study"
jq '.source | del(.run_id)' "$evidence/raw/book-dry-routing-v2.json" > "$study/pin.json"
jq '.group' "$evidence/group-development.json" > "$study/canary-group.json"
jq '.resume | .members |= map(select(.selection.page_no == 151))' \
  "$evidence/group-recovery-development.json" > "$study/recovery-group.json"
uv run python "$evidence/freeze_book_shadow.py" 309 "$study/pin.json" "$study/ranges" \
  "$release" source:chandra-grouped-book "$study/artifacts" "$study/manifest.json" --archive-overlay
uv run python "$evidence/group_shadow_compare.py" "$study" \
  --retained-group "$study/canary-group.json" --retained-group "$study/recovery-group.json" \
  > "$study/retained-comparison.jsonl"
```

`uv run ci test -- python/corpus-structure/tests/semantic/test_visual_routing.py`
passed nine routing checks under managed result `b1c0759c7257419fa1367960913bcff4`.
