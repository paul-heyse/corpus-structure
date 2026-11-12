# Native layer capacity

**Tested · 2026-11-11.** BEP-E01's exact captured source selection produces a complete
current native layer of **9,253,073 canonical UTF-8 bytes**, larger than the former
8 MiB layer limit and below the selected 64 MiB replacement. This investigation belongs
to the BEP coordinator; it does not establish whole-book acceptance.

The retained selection is run 610, cancelled task 2528, capture 496/cut 614,
SourceView 480, section `#/groups/375`, from integrated product task 1627 with digest
`35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`.
`raw/retained-source.json` preserves the exact native text, pieces, items, ancestors
and selected scope. No PDF recognition, GPU inference or publication was performed.

`reproduce.py` runs the actual spaCy and HanLP CPU providers against that source.
It uses a current locally compiled characterization release, current method version 2,
and current runtime/artifact custody frozen by the existing HanLP preflight before
inference. These differ from original failed method version 1. The original failure's
9,588,829-character SQL parameter representation is not a canonical byte count; the
original full body and hash were not recovered. This recomputation has its own digest:
`3ec0f35ca65ca2f6587d50982beac594aa3a8507d68ce1b43002fa4798765cf0`.

All 13 native families completed. The complete body in `raw/layer.json` has 1,140
occurrences, 5,058 annotations, 9,470 memberships, 2,657 roles and two native runs.
`summary.json` records counts, exact canonical bytes, inventory sizes and response
framing. Its hypothetical primary response reference illustrates framing only;
the cancelled task has no such published product. An independent plain JSON encoding
with sorted keys, compact separators and Unicode preserved equals the retained bytes.

The final command passed:

```sh
uv run python docs/design_review/evidence/2026-11-11_bep-layer-capacity/reproduce.py
```

`raw/attempt-04.log` is its output. Earlier attempts are retained: attempt 01 failed
while serializing task timestamps; attempt 02 selected an incorrect model-cache path
and produced partial coverage; attempt 03 correctly refused historical HanLP custody
that differs from the current runtime. Their partial bodies and summaries remain
explicitly separate from the successful complete body.

The finalized record is `bep.e01-canonical-layer-reproduction`.
Publication, size-refusal, aggregate-framing and detached-replay tests use the generated
capacity migration and are reported separately by their managed test receipt.


A subsequent read-only inventory of capture 496 found 316 effective source views,
with 990,284 projected text codepoints. The failed view 480 ranks 61st by text size.
The five largest are views 561 (26,956 codepoints), 733 (23,930), 612 (23,652),
493 (14,837), and 541 (14,628). All use the same exact integrated source product.
`raw/source-size-inventory.json` retains their pointers and native piece/item counts.
The record `bep.e01-source-capacity-inventory` establishes the selection for an upper-tail
capacity check; it does not predict layer size from source length. No additional NLP
run is included in the inventory.


**Tested · 2026-11-11.** The subsequent actual CPU probe of complete view 561
(`#/groups/456`) completed all 13 families in **49,326,509 canonical
UTF-8 bytes**, fitting 64 MiB. `raw/largest-layer.json` preserves the full body with digest
`9ac4dc41d89ddb3a101dc29f95fbdec0fea566e398667e2aa5e92a67b425fd89`.
It has 6,637 occurrences, 27,823 annotations, 50,116 memberships and 14,551 roles.
`largest_native.py` authenticates capture 496/cut 614 and the same exact integrated
product, uses the shared read-only REPEATABLE READ snapshot route, and freezes current
HanLP custody/configuration before current method-v2 inference. The complete source
including integrated context is retained in `raw/largest-source.json`.

The record `bep.e01-largest-native-layer` and `largest-summary.json` own this upper-tail
result. It demonstrates capacity for the largest-by-text captured unit; it does not
establish that every different parse shape fits, or that native publication and the
whole-book campaign passed. No smaller chunks, semantic truncation or weaker profile
were selected. Attempt 01 was interrupted during local release compilation before
provider launch to select the explicit snapshot route; attempt 02 passed.
