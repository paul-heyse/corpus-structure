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
  occurrence. The deployed comparator still needs to exercise this result.
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
