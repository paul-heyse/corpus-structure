# Native child-edge guard — bounded 0061 closeout

Tested 2026-11-01. This correction expands all native child edges once and checks
missing targets and parent backpointers through one document-wide join. The native
publisher owns the guard; integrated publication derives that same guard. Parent
existence, recursive walk/order/scope, custody, fences and projection comparisons
retain their existing meaning. Frozen migrations 0057–0060 are unchanged.

Passed: 7 targeted functional checks, 10 deselected, 2 warnings. Both protected
native and integrated publishers reject missing child targets, wrong backpointers
and multiple parents; valid leaves publish. The generated-query generic plan
places child integrity in an uncorrelated InitPlan. This is planner evidence,
without ANALYZE or an actual book-scale loop/runtime measurement. Exact head
reproduction, explicit current candidate provenance and function/effect/constraint
counterfactual controls remain enforced. Head-witness selection is checked by its
exact source digest rather than assuming two revisions have different provenance.

Command, from the isolated worker checkout with the root environment:

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src /home/paul/corpus-structure/.venv/bin/python -m pytest python/corpus-structure/tests/semantic/test_native_child_edge_guard.py python/corpus-structure/tests/semantic/test_native_closure.py -k 'child_target or child_integrity or model_products_match_frozen or forward_reproduction' -o addopts='' -q --disable-warnings --tb=short
```

Passed: scoped warning-inclusive Pyrefly (0 diagnostics), Ruff and format checks.
Pyrefly reports the explicit worker PYTHONPATH environment notice separately.
The final change after functional checks only split two SQL string literals into
adjacent literals with identical values. Lint and format checks cover that edit.
Logs are adjacent. `git diff --check` passed.

0061 admission descriptor SHA256:
`8ced014764d1d1f90c58326583b4d9a62b55b53377cb4e00a7d1b95c9888b56b`.

Not run: production deployment, full-book publication, integrated qualification.
Production remains on 0060. The coordinator owns deployment and broad qualification.
No worker inference, service or production database mutation occurred, and all
owned checks completed before closeout.
