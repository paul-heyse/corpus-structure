# I04 — Archive, rotation and query primitives

Investigated 2026-11-01, baseline `28f735b87eb2672c521af816aed411ab665b79f4`.
Consumer: logging coordinator I04 and LOG-03/04. Scope is synthetic native/file/query composition,
not production archive implementation, authorization, durability or capacity qualification.

## Sources and commands

Context7 resolved `/websites/duckdb_current` then queried newline-delimited reading and error
behavior. Primary reference: https://duckdb.org/docs/current/data/json/loading_json . Current docs
supply orientation; actual probe uses installed DuckDB2.0.0/Python3.14.10.

- `uv run python docs/design_review/evidence/2026-11-01_logging-archive-queries/probe.py` — passed;
  `raw/probe.json` records assertions. Uses only temporary files and owned spawned processes.
- `/home/paul/.cache/corpus-logging-investigations/telemetry/.venv/bin/python docs/design_review/evidence/2026-11-01_logging-archive-queries/exporter_probe.py`
  — corrected probe passed, `raw/exporter.json`; SDK1.45.1/file exporter0.66b1 from the sibling
  telemetry evidence environment. No environment mutation performed here.
- First native stream-adapter probe failed because its minimal adapter lacked IO.closed. Native
  exporter caught the error and returned failed writes, then the probe itself failed closing the
  absent handle. `raw/exporter-first-failure.json` retains the observed failure/correction; original
  stdout was empty and stderr was observed in the tool receipt. It is not relabelled a native pass.

## Findings and selected direction

1. Native file exporter keeps the supplied stream object and does not close caller-owned streams.
   Reassigning a rolling handler/local stream variable does not rotate that exporter. Select a
   stable, stream-compatible adapter with explicit write/flush/closed/close semantics; rotate complete
   native export batches under one owner. The tiny probe routes two actual native batches to two
   files; it does not implement byte-threshold/production concurrency. Batch size may exceed the
   target segment size, so16MiB is a target, not a guaranteed record splitter.
2. `read_ndjson_objects` rejects incomplete tails and complete corrupt records by default. Select
   a byte-cut snapshot containing complete newline-terminated records plus explicit incomplete-tail
   coverage. Do not pass ignore_errors=True. Complete corrupt records must remain failures/coverage
   defects rather than being treated as a harmless incomplete tail. Probe reads earlier safe prefix
   separately, explicitly retaining the tail state.
3. Select a short selection/prune lock and immutable private snapshot links for closed segments
   on the current POSIX/same-filesystem deployment. The two-process barrier probe proves a hardlink
   survives removal of the original and can be reopened through its snapshot path by another process.
   Active tails must be copied at the declared byte cut, not hardlinked while being mutated. A manifest
   binds closed links, active-prefix copies, filters, compartment and ingestion cut. Production lock
   ordering/manifest atomic publication/cleanup remains LOG-03 implementation.
4. A process-local descriptor is insufficient for cross-command cursors. Explicit snapshot lifetime
   and reopenable private paths are needed; expired snapshots must return expiry, not new data.
   Cleanup must distinguish active references and abandoned process ownership before removing links.
   An intentionally abrupt os._exit(7) reader leaves its snapshot link readable after source
   deletion; the parent cleans it only after observing that exact owned child exit. This establishes
   the need for cleanup and a bounded owned-exit case, not a universal PID/liveness protocol. Cross-filesystem/Windows support is not established; use a bounded copy or
   explicitly unsupported route after platform qualification, never silent weakening.
5. Producer-time cursors skip DEBUG history retained after newer INFO records. Select per-segment
   retained position/ingestion cut plus stable occurrence identity. Producer time remains a filter
   and display attribute. Newly retained old events belong to the next cut, not a rewritten old page.
6. DuckDB raw JSON projection preserves independently specified span links, resource/scope,
   OTLP bool/int/double union distinctions, histogram/exemplar and temporality fields. Avoid early
   inferred flattening; decode typed derived views under known signal/schema. This was a small
   synthetic OTLP fixture, not native metric/span round-trip or a complete query implementation.
7. Trusted compartment selection precedes parsing event fields. A forged scope field inside another
   compartment cannot grant access. The probe demonstrates that selection rule only; current archive
   ACL enforcement, symlink resistance and production principal binding remain implementation checks.

## Outcome and remaining obligations

**passed:** bounded primitive scenarios in the two probes; first failed adapter attempt retained.
**partial:** I04 overall: native rotation/snapshot/query direction is selected, while active-tail
copy/manifest publication, general abandoned-owner cleanup, actual integrated CLI/cursor/prune authorization and
schema projections remain LOG-03 implementation/qualification. No shared hot DuckDB writer or
long-lived snapshot service is required by the selected direction. No broad tests were run.

Files: probe sources, this README and raw receipts only. Temporary files were automatically removed;
no product manifests/settings/database/services or unrelated plans were changed.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**logging-investigations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Settle archive rotation snapshots and cursor primitives](records/logging.i04.json) | LOG-03 | partial | I04, LOG-03 | 2026-11-01 |
<!-- evidence-index:end -->
