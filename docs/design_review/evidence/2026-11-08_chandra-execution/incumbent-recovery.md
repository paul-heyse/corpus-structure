# Incumbent PDF recovery

**Tested · 2026-11-08.** This account covers the CH-08 source witnesses, protected
predecessor, and first Standard rebuild attempt. The [Chandra coordinator](../../../plans/chandra-2-post-nemotron_2026-11-08.md)
owns publication and qualification status.

## Archived and current native contracts

The exact integrated export selected run 312, producing task 1389, product
`integrated`, digest `a491d3ddbf3ee964a8a95e6fc6bed59648fb5c5a77bc57cb84411a9205a749f2`.
It contains 518 pages in Docling document schema 1.10.0. Its native schema
artifact digest begins `3123788c`. The current artifact digest begins `91d32d74`.
The protected projection refusal from run 351 remains applicable to direct
adoption of that exact predecessor.

Validating the retained native graph with Core 2.106.0 upgrades the declared
version to 1.11.0 and inserts legacy inline separators in 12,937 text fields.
After removing only the verified computed table grids, the native graph diff
contains the version and those text fields. The application projects literal
fields with offsets, so that transformation changes ordinary source payloads.
The rebuild uses the original PDF and current Standard, with the matching
successful Nemotron receipts retained for all 518 pages and 1,246 requests.

```sh
uv run ci source native-export --run 312 --producing-task 1389 \
  --product integrated \
  --digest a491d3ddbf3ee964a8a95e6fc6bed59648fb5c5a77bc57cb84411a9205a749f2 \
  --format integrated-json --output build/nce-full-book/integrated-baseline/ch08-archived
```

## Original-source witnesses

- **Physical p108.** The rendered original shows one printed Figure 3.5 caption
  beneath two charts. Docling Parse visible text identifies the caption and
  `p = .5` and `p = .3` inside separate connected vector frames. Positioned axis
  labels extend each panel frame without entering the caption or its neighbor.
  A bounded transformation of the archived graph retained the existing two
  picture identities and gave each a reference to the same new caption
  occurrence. The protected comparator exercised the same recovery below.
- **Physical p151.** The rendered original shows a horizontal header rule and
  a vertical divider. Docling Parse `get_shape_lines()` returned no rules for
  this table. `get_bitmap_rects()` locates the single-pixel PDF stencil drawings
  that paint both rules. The segmented page's positioned words independently
  give S over both outcome columns and C across both outcome rows. The
  verified values for C=0 are 40/60 and 10/60, and the values for C=1 are 7/60
  and 3/60. Retained Nemotron crop request 3, block 0, independently preserves
  the four values and supplies a retained input address. The transformed
  archive retained Table 4.1 and added one 4×4 Table 4.2 with exact positioned
  cell readings and the existing caption reference.
- **Physical p416.** The fresh Standard Reader returned the same 515
  original characters as the verified archived `orig` at `#/texts/2550`.
  The new raw product uses `#/texts/7745` and still has a 15-character
  recognized transcription. The spelling
  digest is `1508f789b24611a648bac9a83d37c3653bedda12ce78311c8c0fb67351e83b16`.
  The new selected product must qualify its own exact occurrence and readable
  projection. The spelling check establishes no positioned matrix grammar.

```sh
uv run ci source inspect 356 --producing-task 1566 --product native \
  --native-digest 2877d6cc3cc649c8d494eb5bf29e66e49b6a54531884d2178305b47933c69569 \
  --pointer '#/texts/7745' --native-view formula --json
```

[Pinned Docling Parse text, vector and bitmap access](https://github.com/docling-project/docling/blob/v2.148.0/docling/backend/docling_parse_backend.py#L147-L246) ·
[Pinned Core floating caption references](https://github.com/docling-project/docling-core/blob/v2.106.0/docling_core/types/doc/items/node.py#L204-L217)

## Managed outcomes

The first CUDA Standard attempt was run 352, task 1559. It captured and
acknowledged 518 assembly, 518 raster, and 518 candidate streams. A concurrent
development release DDL attempt queued an exclusive lock on `ops.task` during
global assembly and both claim renewals timed out. The managed run is terminal
failed and the private build has zero finalized native records. The retained
pages precede the Standard formula enrichment stage. Resume from a frozen
build or completed native IPC therefore cannot finish this attempt. Separate
development DDL from the fresh replay campaign.

The fresh run 356 raw Standard product passed protected publication after
all 518 pages and 1,402 formula outcomes completed. Nemotron resumed after
the raw product sealed. The CPU-only replay preflight re-rendered and matched
all 518 physical frames and verified all 1,246 retained requests, including
raw responses, submitted images and crop receipts. That preflight acquired
no GPU lease and used an unreachable configured endpoint. The organized
source and integrated comparator have separate publication gates.

Run the bounded recovery operation against the active development release and
the source realization for `nce-grinstead-snell-full-book`. Its preflight
checks the original, the retained attempt inventory and the Nemotron
service generation. The optional fourth argument supplies an already
published Standard run in the same release for an integration-only retry.

```sh
bash docs/design_review/evidence/2026-11-08_chandra-execution/incumbent_recovery.sh \
  "$release" "$realization" build/chandra-execution/ch08-comparator
```

`uv run ci test -- python/corpus-structure/tests/semantic/test_pdf_reconciliation.py
python/corpus-structure/tests/semantic/test_pdf_stream_reconciliation.py
python/corpus-structure/tests/ingest/test_pdf_body_selection.py` passed as
`16498b1a7a9543449a871aad9eeda5fb`.
`uv run ci test -- python/corpus-structure/tests/semantic/test_pdf_incumbent_recovery.py`
passed as `37fcd156bc8b4130ae2949cfc24009af`. That test checks a shared caption
without duplication, separate p301 captions, neighboring table preservation
and precise cell occurrence geometry. It does not exercise a protected
full-book publication.

## Optimized comparator · 2026-11-08

**Tested.** Run 377, task 1627, reached source-ready cut 492 with selected
`integrated` digest `35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`.
The frozen build from cancelled run 373 remained read-only. The successor used
run 356's exact organized product and verified all 1,246 retained recognition
requests against the original. The protected inventory covered 518 pages and
53,156 relations. All four checks and the projection seal recorded receipts
for the live attempt. The book used full validation because it had no
compatible integrated predecessor.

The ordinary Reader returned p108 pictures `#/pictures/37` and
`#/pictures/38` with the same single caption `#/texts/24965`. P151
`#/tables/56` has S spanning two columns, C spanning two rows, and the
four witnessed fractions. P151 `#/tables/34` matches all 16 typed Table 4.1
cells, including their offsets, spans and header flags, from archived
`#/tables/32`. P416 `#/texts/2341` has the exact 515-character original
spelling with the independently witnessed digest above. These Reader
requests used an 8 MiB budget.

```sh
uv run ci status 377 --project nce-grinstead-snell-full-book --json
uv run ci source native-products 377 --json
uv run ci source inspect 377 --producing-task 1627 --product integrated \
  --native-digest 35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb \
  --pointer '#/texts/2341' --native-view formula --max-bytes 8388608 --json
```

**Measured.** Three database workers were active together. Protected
checks ran from 10:19:31 to 10:23:38 EST. PostgreSQL attributed 244.890 s
to section ancestry inside access correspondence. The remaining elapsed
time includes staging and the native callback. A forward correction
assigns the nearest section once per rooted component and checks the
result with a set difference. It refuses unreachable cyclic components.
On the exact sealed input, three rollback-only section checks took
114.3–120.2 ms and full revised access correspondence took 2.956 s.
Those readings characterize the check on sealed data. Run 377 remains
the single whole-book publication.

**Tested.** Projection-only adoption run 378 reached cut 493 and published
29 views with the same integrated pin. Its formula Reader returned all
515 witnessed characters from `orig`. Descendant source view 345 under
`#/groups/614` carries the formula as the attributed piece at offsets
7293–7808. Source search returned that view and the ordinary native proposal
packet carried the exact text with digest
`77aaf0da447e470ba73d364201d4977dfdcb4d09c763edd05402c12881d77a33`.
The source-ready search used the source search API behind MCP. The generic
`ci query find` path requires a completed semantic result. The archived
run 312 formula response retained SHA-256
`a74c463c98c1f4dc3e6bef4efb6d2ebc548c62e485d080e256a7758df1d34629`.

```sh
uv run ci status 378 --project nce-grinstead-snell-full-book --json
uv run ci source inspect 378 --producing-task 1627 --product integrated \
  --native-digest 35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb \
  --pointer '#/texts/2341' --native-view formula --max-bytes 8388608 --json
```
