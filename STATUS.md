# Status
_Updated 2026-11-06; test execution stopped at operator request; WCE planned; historical PCE qualified nondefault._

## Current scope and owners

- [Test resolution](docs/plans/test-audit-resolution_2026-11-05.md) owns TR-00–10 and all 23 DTA dispositions.
  Implementation and assembled review are delivered; full qualification remains incomplete. Do not resume automatically.
- [Witnessed enrichment](docs/plans/witnessed-corpus-enrichment_2026-11-05.md) owns WCE00–12 and scheduled findings:
  Proposed, implementation not started. RC01–06 accepted for planning; WCE00 routes formal adoption.
- [Enrichment review](docs/design_review/reviews/design_review_production-enrichment-improvements_2026-11-05.md)
  is recommendation-audited: native witnesses, factor policies, evaluation/reuse and identity pilot;
  F01–07/RC01–06 remain at their owner. Its target assumption does not establish test qualification.
- Six WCE companions retain semantic/native/read, parser, composition, factor/event, identity and qualification contracts.
- [PCE coordinator](docs/plans/progressive-corpus-enrichment_2026-11-04.md) retains PCE acceptance/F01–F43/qualification.
  ADR-0062/0063 preserve progressive products/runtime separation,0064 local admission and0065 cross-source custody.
  Complete records remain stronger; source isolation and independent judgments remain; no default was activated.
- [Production audit](docs/design_review/audit/README.md) and [test audit](docs/design_review/test-audit/README.md)
  retain their bc2208f9 diagnostic baseline; neither is a fresh alignment certificate.

- [PostgreSQL tool inventory](docs/libraries/postgresql/system-tool-usage.md): operational/test-only use, extensions and installed candidates; verified 2026-11-06, documentation-only.

## Test checkpoint — 2026-11-06

- Initial serial `CORPUS_TEST_NATIVE_AUTH_CRASH=1 just test-all` interrupted by operator:
  3371 passed, 1 failed, 1 incomplete, 1389 not_run of 4762;504 completed native claims have item-bound context.
  All 8 auth fault controls passed. Owned process group drained with no survivors; Rust not_run after cancellation.
- The sole renderer assertion failure was corrected; only that exact failed node was rerun and passed.
  3372 original nodes now have successful results;1390 remain pending. Receipts/selection are at the coordinator.
- Default pytest now uses 16 xdist workers; shared math preparation is grouped; `just test-native-faults` is exclusive serial.
  Compatible pytest 9.1.1 / xdist 3.8.0 is held in [pins](docs/pins.md) ; 9.2 silently broke grouping.
- [New parallel evidence](docs/design_review/evidence/2026-11-06_parallel-test-execution/README.md): 40 new cases passed,
  16 concurrent worker PIDs, one worker for 8 grouped cases, 2 overlapping real bare clones with complete native context.
  This is not complete 16-worker application-template/capacity qualification. Existing successful product cases were not replayed.
- Development DB migrated 151→152 only ; 158 table counts, 4 project defaults and 404 relation/ACL fingerprints unchanged.
  Only the semantic validator/descriptor changed; no release/default activation. Native 152 fixes temporary-rowtype caching.
- Earlier focused math 28 / native 39 / classifier 24 / native-152 guards 18 and CLI/render controls passed at their recorded sources.
  Full qualification/hygiene remain unfinished; source changes and failed/interrupted attempts retain their real limits.
- Stop-checkpoint `just turn-end`, `just docs-check`, `just types`, `uv run ruff check`, `just deps` and `just evidence` passed.
  Evidence retains 40 existing repository warnings; no full hygiene or runtime-qualification closure is claimed.

## Earlier verified scope and limits

- WCE documentation publication: `just docs-check`, `just turn-end`, scoped `git diff --check` passed; product tests not_run.
- [PCE evidence](docs/design_review/evidence/2026-11-05_pce-structural-products/README.md),2026-11-05:
  broad attempted 4722; focused repairs established 4714 selected required cases including 829 native. Broad failures remain failed.
  PCE excluded 8 auth controls; the new test attempt ran them. Historical Rust empty selection supplied no functional coverage.
- PCE render/provenance/replay/budget, 18 typed/metadata and 130 runtime/consumer controls passed with compiler 17 / execution 27.
  Types/Ruff/ready/model/applicable hygiene and its assembled review passed for that historical source.
- Public98/cut132 and reviewed supplied statements retain original receipts. Logicalbf5e216e…/native151 and
  producer98/runtimed86238… keep their archived meaning; prior installed7b2bc478… is not retagged as current qualification.
- [Portable006/MCP002](docs/design_review/evidence/2026-11-05_pce-portable-review/README.md) retain 14 relations versus 005.
  Four project defaults remain null/null/generation0. Automatic 51/52 retain raw outputs: 20 pairs judged 12 supported / 8 wrong;
  whole automatic statements unsupported. Manual 005 is separate. Source 92 / output 24 gaps and partial products remain bounded.
- No full-corpus scientific truth, unseen-origin, calibration, transfer, inference/training/ANN or broader adoption claim follows.

## Next

- Stop test work here. A separately authorized resumption uses only remaining/failing nodes; successful cases are retained.
- Next enrichment execution, when authorized: WCE00 reconciliation/RC adoption, then WCE01 shared contracts and WCE02 early slice.
- Historical PCE has no required execution remaining; F37/F39 retain their triggers at the PCE owner.
