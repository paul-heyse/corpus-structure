# Positive math transport test deadline

2026-11-06 diagnosis: **passed** for identifying an unsupported test deadline;
functional rerun **not_run**, awaiting the coordinator's GO after the ongoing full
parallel qualification. Only `tests/math/test_workers.py` is changed. The shared
helper, production code, dependencies and native runtime remain unchanged.

The original `just test-all` invocation uses the existing `-n auto` / `loadgroup`
configuration. Its retained receipt is
`build/test-receipts/qualification/20261106T211956Z-2681505/`. In
`reportlog.jsonl`, the call phase of
`test_real_spawn_transports_each_stage_without_preparation_or_reparsing` failed on
worker `gw6`, from Unix time `1794000181.949783` to `1794000211.9565117`, duration
`30.006729422020726` seconds. The exact diagnostic is:

```text
math_support.PageWorkError: page submission-to-result deadline exceeded: ['independent-small-page']
completed pages: []; incomplete pages: ['independent-small-page']; not submitted pages: []
```

The failure is the first `read_content` submission, before any result or assertion
about its transported values. `math_support._run_pages` defaults to 300 seconds,
starts its deadline immediately before `pool.submit`, explicitly includes spawned
process startup, and kills the pool on failure. The real workload also imports its
mathematical dependencies in the fresh process. The 30-second overrides in the two
positive transport tests are not a declared performance requirement.

Current event records show all 16 xdist workers had work overlapping the failed
call. Concrete concurrent mathematical jobs include the grouped scope consumer
`test_held_out_and_example_standing_contexts@math_preparation` (`gw3`,
`1794000106.1136243`–`1794000220.069262`), the real spawned vendored-page control
(`gw0`, `1794000183.7681682`–`1794000255.6954346`) and corpus coverage (`gw10`,
started `1794000169.7245924`, still active at the snapshot). These establish nested
spawn/preparation overlap, not a measured allocation of the failed call's startup
versus parsing time. No global serialization or new scheduling group is needed to
remove a timing requirement that does not belong to this test.

The fix removes five `timeout=30` arguments across the two positive transport
tests and uses the existing bounded 300-second helper default. Each pool still has
`workers=1`. All real spawn, token coordinates, prepared-state absence, immutable
macros, parse outcomes, printing, mentions, relations, scope, ordinary pickle and
parent-product reuse assertions remain intact. The 2-second deliberate stall
deadline and its completed/incomplete/unsubmitted diagnostics, 15-second worker
error/exit/interruption controls and lifecycle settlement assertions are unchanged.

The intended semantic patch is:

```diff
@@ test_real_spawn_transports_each_stage_without_preparation_or_reparsing
-    readings = _run_pages(read_content, {page.page: page}, workers=1, timeout=30)[page.page]
+    # Exercise transport under the helper's ordinary deadline, including spawn/import
+    # startup during parallel qualification. This test has no shorter timing contract.
+    readings = _run_pages(read_content, {page.page: page}, workers=1)[page.page]
-    assert _run_pages(reading_positions, {page.page: readings}, workers=1, timeout=30)[
+    assert _run_pages(reading_positions, {page.page: readings}, workers=1)[
-    values, extraction = _run_pages(extract_readings, {page.page: readings}, workers=1, timeout=30)[
+    values, extraction = _run_pages(extract_readings, {page.page: readings}, workers=1)[
-        scope_extraction, {page.page: (page, values, extraction)}, workers=1, timeout=30
+        scope_extraction, {page.page: (page, values, extraction)}, workers=1
@@ test_staged_corpus_relations_preserve_direct_page_semantics
-        _run_pages(reading_positions, {key: staged.readings}, workers=1, timeout=30)[key]
+        _run_pages(reading_positions, {key: staged.readings}, workers=1)[key]
```

Source inspection commands:

```sh
cat python/corpus-structure/tests/math/test_workers.py
cat python/corpus-structure/tests/math_support.py
sed -n '1,100p' conftest.py
sed -n '40,75p' pyproject.toml
git diff -- python/corpus-structure/tests/math/test_workers.py
```

The existing grouping belongs to consumers of shared preparation fixtures; these
positive cold transport controls deliberately create independent process handoffs.
Keep global `-n auto`. After GO, the affected file's functional controls must be
rerun with that configuration; full qualification and final-harness union remain
the coordinator's responsibility. The failed full-run record is preserved.
