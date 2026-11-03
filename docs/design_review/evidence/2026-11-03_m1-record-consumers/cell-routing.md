# Native cell evidence handles

**Tested, 2026-11-03: controlled adapter behavior only.** The cell-only `cell-routing.patch` imports the semantic owner's public `source_record_address` parser. A canonical `#/tables/0/data/table_cells/3` anchor now emits a native source handle with `view=cell`, `pointer=#/tables/0`, `cell_index=3`; the full original anchor and its coarse/exact precision remain unchanged. Other item handles keep their existing route.

The patch baseline contains the root's archived RecordStanding validation. Apply only its source-handle and test hunks. Do not recopy the complete consumer: root owns concurrent reader pagination and service/presentation adaptation.

- **passed**: `cell-focused-002.log`, 20 focused tests via `PYTHONPATH=/home/paul/.cache/corpus-structure-m1-record-consumers/python/corpus-structure/src uv run pytest /home/paul/.cache/corpus-structure-m1-record-consumers/python/corpus-structure/tests/semantic/test_record_consumers.py --tb=short`, run from the main checkout. The added tests check canonical cell handle shapes and unchanged anchors, then drive the real native inspection adapter against a controlled retained parent table and independently expected fourth-cell content. Storage/context resolution is substituted; this is not database or provider qualification.
- **passed**: `cell-ruff-002.log`, `uv run ruff check` on worktree `serve/record_results.py` and `tests/semantic/test_record_consumers.py`.
- **passed**: `cell-pyrefly-002.log`, `uv run pyrefly check --config /home/paul/.cache/corpus-structure-m1-record-consumers/record-consumers-pyrefly.toml` on those same two files.
- **failed, superseded**: `cell-ruff-001.log`, one long test line, wrapped without a behavior change. Earlier `cell-focused-001.log` also passed all 20 tests.
- **not_run**: native database/provider journeys, root maintenance, assembled qualification, commits, or main-tree source writes.

`cell-routing-source-hashes.json` identifies the two worker source files, and `cell-dependency-copy-manifest.json` names their copied dependency snapshot, including the public parser owner. Those copied production dependencies are read-only inputs and must not be copied back into main.
