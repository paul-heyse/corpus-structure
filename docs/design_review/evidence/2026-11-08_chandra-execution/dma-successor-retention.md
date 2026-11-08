# Stopped scope retention through the DMA successor

**Tested · 2026-11-08.** The original campaign group receipts supplied the
raw and mapped pins for 68 settled selections across 17 groups. The
restricted development Reader matched all 136 pins by exact run, task,
product key and content digest after migration to `semantic_dma_05_13_final`.
Every mapped product had an admitted native locator. The managed deployment
receipt is `ab020224d7294bceb6c200600dc326a6`.

The [stopped scope pins](raw/book-shadow-377/dma-stopped-scope-pins.json)
record the settled portion of the
[frozen campaign](book-shadow-execution.md#freeze-and-execution). The
remaining frozen scopes are unassessed. An explicit retained-raw replay after
verification reused task 1633 and produced mapped task 1829 at cut 513.
The [DMA coordinator](../../../plans/domain-model-alignment_2026-11-08.md#dma-13)
owns the adoption disposition.

```sh
uv run python docs/design_review/evidence/2026-11-08_chandra-execution/verify_dma_scope_retention.py
```
