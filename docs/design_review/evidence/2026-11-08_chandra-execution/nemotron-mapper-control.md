# CH-01 retained Nemotron mapper replay

**Tested · 2026-11-08.** The CPU control used the six original book pages from run 312 and the retained first attempts. The two arms were Docling/Slim 2.145.0 with Core 2.105.0 from an isolated overlay, and the installed 2.148.0 with Core 2.106.0. Both used PDFium 5.14.0 and Pillow 13.0.0. The application replay and projection ran through the same source in both arms. [CH-01 scope](../../../plans/chandra-2-post-nemotron/docling-upgrade-and-baseline.md) · [Replay script](nemotron_mapper_control.py)

The script matched every response to its saved HTTP choice and receipt digest. It reproduced all six original page PNGs and all 15 crop JPEGs and submitted PNGs byte for byte. It reconstructed observations with the production recipe and request reader, validated their retained artifacts through `prepare_integrated_pdf_product`, and called `map_pdf_observation` with the retained page and composed crop affine. A separate call to `parse_nemotron_parse_v3_5` used the exact response text and submitted width and height. The production section projection ran over each application-mapped body.

| Page | Retained requests | Control |
|---|---|---|
| 108 | A, B, C2–4 | A retained two chart pictures. C4 retained two chart panels with identical enclosing PDF-point boxes in both arms. |
| 151 | A, B, C2–3 | A retained two tables and the attachment of the Table 4.2 caption. C3 retained its 5×4 grid and all four fractions. Its 313×162 submitted raster used affine `[2, 0, 0, 2, -454, -378]`, with the table box at approximately `[241.21, 198.94, 366.54, 263.99]` in PDF points. |
| 301 | A, B, C2–3 | The two line-chart grids and the Figure 7.3 caption attachment matched. A preserved a space in the printed page number in native furniture, with identical body projection. |
| 398 | A, B, C2 | Both mapped table candidates retained their 21×13 dimensions and identical cells across the upgrade. |
| 416 | A, B, C2–7 | A mapped the six matrices as 4×4 tables. One crop kept its 4×5 grid and the other five kept their 4×4 grids. A and five crops changed the inline spacing in projected text, including `P1= Nice` becoming `P1 = Nice`. |
| 509 | A, B, C2 | A retained the 16×21 table and the crop retained the 17×21 table in the source frame. A preserved a space in the projected citation. |

All 27 observation payload hashes and application dispositions matched. The six B responses carried 45 raw occurrences and each produced one evidence-only disposition with no mapped body items. A and C produced 57 mapped raw blocks. The two arms agreed on all ordered, located geometry values in both the direct parser and application mapper. The p151 A native document gained two whitespace-only text children with no direct provenance. This changed the native reference paths, the path-indexed geometry digest, and the origin map from 36 to 38 links. Projected text grew from 1,734 to 1,742 characters and from 81 to 83 pieces, including `aremutually` becoming `are mutually`.

Nine requests differed in native content across both replay paths, comprising A on p151, p301, p416 and p509 and C2/3/4/5/7 on p416. Eight changed the exact projected text and position pieces, with p301 A identical at the projection boundary. The emitted native version changed from 1.10.0 to 1.11.0 for every request. These results establish physical geometry parity and identify the native content and pointer changes that a new publication must bind to its own producing release. The earlier 21-response report compared a narrower native summary. [Earlier replay](../2026-11-08_chandra-post-nemotron/raw/nemotron-replay.json)

The installed target also read the retained run 312 p416 formula at `#/texts/2550`. The result was `source_ready` with `population_complete=true` and one row. The 54,318-byte JSON matched the earlier retained read byte for byte. Its SHA-256 is `a74c463c98c1f4dc3e6bef4efb6d2ebc548c62e485d080e256a7758df1d34629`. This replay covers observation publication preparation, projection and the retained Reader path. Fresh selected product publication and adoption are separate CH-01 obligations.

## Reproduction

From the repository root with the target installed and the run 312 receipts available, the following commands passed. Keep the summary and full native comparison files in the build directory.

```sh
ev=docs/design_review/evidence/2026-11-08_chandra-execution
work=build/chandra-execution
pdf=docs/statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf
run=build/nce-full-book/integrated-source
uv pip install --target "$work/old-site" --no-deps \
  'docling==2.145.0' 'docling-slim==2.145.0' 'docling-core==2.105.0'
CUDA_VISIBLE_DEVICES="" PYTHONPATH="$PWD/$work/old-site" .venv/bin/python \
  "$ev/nemotron_mapper_control.py" "$pdf" "$run" "$work/nemotron-old" --docling 2.145.0
env -u PYTHONPATH CUDA_VISIBLE_DEVICES="" .venv/bin/python \
  "$ev/nemotron_mapper_control.py" "$pdf" "$run" "$work/nemotron-target" --docling 2.148.0
uv run --no-sync ci source inspect 312 --producing-task 1389 --product integrated \
  --native-digest a491d3ddbf3ee964a8a95e6fc6bed59648fb5c5a77bc57cb84411a9205a749f2 \
  --pointer '#/texts/2550' --native-view formula --max-bytes 8388608 --json \
  > "$work/nemotron-retained-p416-reader.json"
sha256sum "$work/nemotron-retained-p416-reader.json"
```

The source SHA-256 was `763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e`. The retained recipe SHA-256 was `918bc3f313f04dc91a1d0a68b8472009681450f196d54e6b4bded4c1fd30b6b9`. Compare the `rows` arrays in the two `summary.json` files by page and request. `geometry_sha256` includes serialized field paths and `located_geometry_sha256` compares the ordered nonempty values. The per-request `*.native.json` files expose the changed values and projected position pieces. The two summary SHA-256 values were `24a5121e298b4c1f8b30f5546ad411b7fe98c2df4b93ffbe16eccfe2e9612f53` and `88657dd77ae25ef926838693f1b48a6f56242a462132a2e70b72f494de291293` in baseline and candidate order.
