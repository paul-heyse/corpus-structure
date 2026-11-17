# Joint audit refresh: cost map from stored test results — 2026-11-17

**Question.** Where does the time of the test scope go at the current state of the suite, as
far as results already on disk can say? The 2026-11-17 refresh of the
[test audit](../../test-audit/README.md) uses the answer for its numerical statements.

**Consumer.** [Test audit, measurements](../../test-audit/execution-and-qualification.md#measurements).
No record is finalized: this is a reading of existing receipts, not a measurement campaign.

## Method

No test, build or database operation was run. The script from the
[2026-11-13 refresh](../2026-11-13_test-audit-refresh/README.md) (`cost_map.py`, stdlib only,
unchanged) read managed results under the local, untracked `build/ci/`:

```console
python3 ../2026-11-13_test-audit-refresh/cost_map.py narrowed build/ci 120                          > raw/narrowed-last120.md
python3 ../2026-11-13_test-audit-refresh/cost_map.py full build/ci/873f904c33084cc7801833dfef7ef7df > raw/narrowed-873f904c.md
python3 ../2026-11-13_test-audit-refresh/cost_map.py full build/ci/42cd4f8b8e9247168655cd7c1d28a616 > raw/narrowed-failed-42cd4f8b.md
```

Run on 2026-11-17 with the system Python 3. The three outputs under `raw/` are the retained
copy.

## Conditions and limits

- **No passed full run exists after `2e2a0e30…` (2026-11-10).** The largest results since then
  are interrupted or failed. There is therefore no current full-run profile; the 2026-11-13
  figures predate the declared-data-operations tests, the test-system work and the retirements
  of 2026-11-16.
- **`narrowed-last120.md`**: the last 120 passed narrowed runs, 2026-11-16 15:19 to
  2026-11-17 16:53, with 1 to 16 workers.
- **`873f904c…`**: the largest passed narrowed run since 2026-11-13 (2026-11-14, 685 tests,
  4 workers). It predates most of the production-efficiency slices.
- **`42cd4f8b…`**: a failed five-test run on a private host, 2026-11-17. It shows where time
  went in that run, not an ordinary cost, and nothing here explains why.
- The workstation was shared during every run. Treat durations as the order of magnitude under
  ordinary development conditions. Nothing here measures a speedup.
- A phase duration says where time was spent, not why. Attribution to a cause is from source
  reading in the audit and is labelled there.

## Also checked

Stored results since 2026-11-15 were searched for three tests that source reading says cannot
pass or set up. None has a result after the change that affected it:
`test_deployed_contextual_product_identity_matches_literal` (no run),
`tests/semantic/test_source_routing.py` (no run), and consumers of the copied PDF converter
(last runs predate commit `7f3951adf` of 2026-11-17 14:08).
