# GS120 current source recovery

**Actual source recovery passed2026-11-06.** This folder owns the actual source-adoption journey and neutral
packets for the already authenticated Grinstead–Snell physical191–310 corpus.
It does not own product changes, native deployment, semantic extraction or independent
reference judgments.

`inventory_sources.py` reads source run137/cut176, authenticates one retained organized
native product for each of the twelve original ten-page files, and checks every original
file hash against the source manifest. `native-inputs.json` and `inventory001.log` retain
that passed read-only result. It changes no database state.

`recover_sources.py 001` completed12 ordinary runs140–151 under native158 and recipev7.
`attempt001/coverage.json` and `result.json` retain48 nonempty views, all120 native provenance
pages and all120 projected-text pages, with zero duplicate projected fields. It refuses the prior
native156/157 checkpoints and source recipev6 before writing. Its actual graph:

1. Archives and admits the current statistics release through existing purpose operations.
2. Creates twelve source runs, one exact retained product and original file per registered
   `ingest.pdf/retained` configuration, then produces current `extract.m1_annotations` products.
3. Seals and consolidates each run normally. No PDF conversion, recognition or GLiNER call is
   present in its graph; original file bytes are read for the normal registration/hash boundary.
4. Prepares one combined exact source/reference closure across completed runs and writes twelve
   new neutral source packets. It preserves the original packets and author files.
5. Accounts separately for native item/page coverage and projected text/page coverage, rejects
   duplicate projected native fields, and requires all120 physical pages in selected native
   item provenance. Semantic quality and graphical-region inspection remain unassessed.

Completed command:

```bash
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/recover_sources.py 001 > docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/attempt001.log 2>&1
```

Attempt folders are append-only. Failure files retain their actual stage and do not establish
successful source recovery. A failed or interrupted attempt must be inspected before deciding
how to resume its existing runs; it must not trigger automatic conversion or re-extraction.

Passed preparation checks:

- `uv run python docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/inventory_sources.py`
- `uv run python -m py_compile docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/inventory_sources.py docs/design_review/evidence/2026-11-06_wce-gs120/source-recovery/recover_sources.py`

The syntax check establishes preparation only. Actual source adoption/coverage passed in
`attempt001/`, finalized record `wce.gs120-source-recovery`. Semantic capture, graphical inspection
and full final-source WCE qualification are separate obligations.
