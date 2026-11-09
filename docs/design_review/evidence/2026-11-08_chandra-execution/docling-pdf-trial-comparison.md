# Matched field comparison for Docling's Chandra PDF route

**Tested and Measured · 2026-11-08.** Physical pages 506–510 from the exact
original SHA-256
`763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e` were
run through Docling's threaded PDF backend and Chandra on the local CUDA device.
The trial is compared against the protected incumbent, its Standard dependency,
the exact retained Chandra whole-page observations, and a fresh detached
legacy timing arm on the same five pages. The timing arm uses a four-page
worker followed by a single-page worker. Both durations include worker launch,
output capture, and shared GPU handoff. Protected publication is outside
this measurement. [Frozen incumbent and legacy receipts](book-shadow-execution.md)

| Physical page | Source-witnessed result in the native serial trial |
| --- | --- |
| 506 | Both running headers survive, and the typed result has no invented body content on this independently verified blank body. |
| 507 | The `Appendices` heading and printed footer `499` agree with the original and the matched legacy result. |
| 508 | The 41×11 normal table agrees on all 451 checked anchors, including the 400 numeric values and the blank corner. The 11 column-header flags and absence of row-header flags preserve the earlier structural limit. After the closed table the native raw output emits a long repeated diamond sequence and stops at the 12,384-token cap. The actual response is 20,035 bytes, compared with 7,487 bytes in the matched legacy arm. The unclosed tail is separately classified as malformed and repetitive. |
| 509 | The sideways table matches 143 of 153 checked values in printed row order, up from 116 in the whole-page legacy result. The totals `928` and `205` survive. The separate `Below` and `62.2` bindings remain unresolved. The row-order result has no authority over header ownership. |
| 510 | All 344 life-table data anchors agree with the original and both whole-page readings. Header and span standing remains separate from the literal check. |

The native serial arm took 292.586 seconds. The fresh matched legacy arm
took 190.603 seconds. On p508, native inference alone took 178.780 seconds
against 65.138 seconds in the matched legacy arm. The native report assigns
`partial_success` after the p508 length stop. Each of the five native
rendered rasters differs in RGB pixels from its matched legacy input,
while sharing the same 1224×1584 dimensions. These observations show the
combined effect of the changed render and native worker lifetime. The
same-frame comparison is needed to isolate those effects.

The comparator validates trial and legacy custody before comparing typed
values. Its Poppler anchor checks cover only the named fields, and
geometric matches nominate candidates. A timed test can be reproduced
from the detached receipts in the development workspace.

```sh
uv run --no-sync python docs/design_review/evidence/2026-11-08_chandra-execution/compare_docling_pdf.py \
  build/chandra-execution/book-shadow-377 \
  build/nce-full-book/corpus/Introduction_to_probability_grinstead_and_snell.pdf \
  build/chandra-docling-pdf/serial/native \
  --legacy-timing build/chandra-docling-pdf/legacy/timing.json
```
