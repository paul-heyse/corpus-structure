# PDF original-retention guard correction

**Date:** 2026-11-13. **Status:** Implemented and tested on isolated clones; persistent deployment is outside scope.

The operator authorized this narrow repair after the test-system execution exposed a native
fixture setup defect. The declared-data-operations pause remains in force. No persistent
working-database deployment, adoption, activation or cutover is authorized by this repair.

## Failure and repair

**Interface-checked by source inspection, 2026-11-13.**
`ops.retain_pdf_original` declared a PL/pgSQL local named `recipe_digest`, the same name as
`ops.source_build.recipe_digest`. Its replay guard compared
`source.recipe_digest=recipe_digest`, which PostgreSQL refused as an ambiguous column reference.
The correction renames that local and its references to `recipe_digest_`; the column name,
operation signature, return value, messages, ACLs and custody/replay policy stay the same.

Managed test result `36b9f71e784440c8be83ef6d0f68ecf6` **failed**: 68 selected, 18 passed,
50 failed. The bounded typed `ci test failures` view established that all 50 failures occurred
in setup with this same `AmbiguousColumn` defect, before the refusal assertions could execute.
The original result remains retained and is not reported as passed.

## Operational boundary

`uv run ci db status --maintenance --json` observed persistent database
`corpus_structure_dev`, OID `25921445`, PostgreSQL system identifier `7701811359771751232`,
port 5434, at revision `semantic_bep_located_v2`; checkout head was
`semantic_ddo_archive_v5`. These are the before-repair observations of 2026-11-13.

The request in `change.yaml` uses the ordinary preview/candidate/register route to author
successor `semantic_test_pdf_recipe_guard` after the unchanged registered v5 artifacts.
Candidate authoring replays the pending registered chain inside its existing rollback-only
transaction. Registration adds new frozen artifacts. Verification targets disposable test
clones; the persistent revision and adoption state are preserved.

The first preview `a2c12e025100445fa5deda2acac0a89e` **passed**, with no canonical model,
physical source or generated effects. The snapshot worker then regenerated the preexisting
stale typed-column model IDs through their owning generator, so the preview is refreshed
before authoring to bind the final source.

## Verification scope

The focused test
`tests/semantic/test_pdf_staging.py::test_original_pdf_retention_replays_exact_recipe_and_refuses_changed_recipe`
uses the existing authenticated PDF build on an isolated semantic clone. The fixture's first
retention establishes presence; an exact replay must return the same original digest; an
altered recipe must refuse with SQLSTATE `23514`, exact primary message
`original PDF source build replay differs` and the `ops.retain_pdf_original` diagnostic context.
The rejected call must preserve the original source-build tuple and leave no alternate recipe
artifact. Frozen candidate deployment is verified on clones through the existing native
deployment controls.

## Accepted operational evidence

**Tested, 2026-11-13.** The final post-format preview
`75be1461b3d04d308f63d57a04d6c107` **passed**, bound to release
`release:58941fab8b2825ad50bd46e177cf3c487ebeff4b56d723737543ab4881ec9623`.
Rollback-only candidate `f30321b9c826481db3e53d499cae59d6` **passed**. Its inspection shows
exactly two function-body transitions: `ops.retain_pdf_original` and the generated
`data.execution_contract_descriptor`; ordinary schema operations are zero. Owners and ACLs
are unchanged. The SQL view shows exactly the local-variable rename and its references.

Registration `88c9a9683a5f4c9b90a3b4adc1eb8979` **passed** and added the four ordinary frozen
successor files. `git diff --name-only -- python/corpus-structure/semantic_alembic/versions`
was empty after registration: no earlier tracked frozen file changed.

The following exact command **passed**, managed result
`e0b76cad67e1435199d8009c1147d9a3`, three selected identities, three passed:

```sh
uv run ci test --workers 1 --json -- \
  python/corpus-structure/tests/semantic/test_pdf_staging.py::test_original_pdf_retention_replays_exact_recipe_and_refuses_changed_recipe \
  python/corpus-structure/tests/semantic/test_model_deployment.py::test_exact_native_deployment_resumes_before_separate_activation
```

The first identity verifies authentic initial retention, identical replay, the exact changed-recipe
refusal and atomic absence of the alternate artifact. The two existing deployment identities
verify direct-predecessor and pending-chain forward deployment/resume on isolated databases.
Their clone-local activation control does not activate anything in the persistent development
database. This is bounded guard/deployment evidence, not DDO qualification or completion of TS-09.

`uv run ci db status --maintenance --json` confirms the persistent database remains at
`semantic_bep_located_v2`, with the same database OID and PostgreSQL system identifier; only the
checkout head advances to `semantic_test_pdf_recipe_guard`. No `model change deploy` was run.

The accepted record is `records/test-system.pdf-original-guard.json`. Raw typed operation and SQL
views, the managed clone result, and database observations are retained under `raw/`.


## Forward seal producer-column correction

**Interface-checked by source inspection, 2026-11-13.** The next consumer run reached
`ops.check_pdf_build` and found its reference to the retired `ops.data_derivation.task_id`.
The governing physical model declares `producer_task_id`. The one-line correction uses that
current column; it does not restore a retired column or alter the current DDO architecture.

The [completion/reconciliation contract](../../../plans/declared-data-operations/demand-planning-and-execution.md)
and [takeover/historical-receipt contract](../../../plans/declared-data-operations/products-and-support.md#takeover-and-historical-receipt-semantics)
keep the original producer fence distinct from the adopting publication fence. Intent retention
records the producing task/attempt; publication authenticates the original or adopted current
fence and stores the intent's original producer fields in the append-only derivation. The task
joined by this PDF reuse query is the task of the earlier published PDF. Its matching derivation
therefore uses `producer_task_id`. Exact request/generation/intent enforcement remains with the
retention/adoption/publication owners. The query's existing legacy sealed-run alternative and
`ops.ddo_support_valid(episode.id)` gate remain unchanged: historical receipt availability does
not itself establish support validity for a new/current admission.

The normal post-format preview `e0abdab9e29b4228a0fffd37d8b78a12`, rollback-only candidate
`b4371764ac044e64a6ecc4c42fd2bef5`, and registration
`9deaffe25e42429a8c1d9642c7393458` **passed**. Four new
`semantic_test_pdf_seal_producer` files follow the unchanged first correction. Inspection shows
two function-body transitions (`ops.check_pdf_build` and the generated descriptor), no ordinary
schema operations, unchanged owners/ACLs, and exactly one source-line replacement in the guard.
The persistent database stayed at `semantic_bep_located_v2` with its original OID/system identity.

Managed consumer run `fc82fd2a666343f2916dac2b2cea448e` **failed**: 79 selected, 32 passed,
47 setup failures. All 19 attributed-source cases, three serving-lifecycle cases, the authored-policy
case and nine refusal-helper controls passed. The other 47 cases failed fixture lookup before
SQL execution (45 `semantic_db_engine`, two `semantic_database_at`). Their native identity,
refusal, replay and forward-deployment obligations remain unqualified by this run.

### Fixture registration boundary exposed by the mixed selection

**Tested by collection-only diagnostic, 2026-11-13.** The exact mixed selection created two
separate `pytest.Package` objects with the same semantic directory/node ID. Pytest 9.1.1's
installed `_pytest/fixtures.py` (`FixtureManager._matchfactories`, lines 2155–2169 at inspection)
uses collector-object membership when `FixtureDef.node` exists; the string `baseid` fallback
applies only when that node is absent. The semantic-local fixture definition was bound to the
first package object and did not match cases under the second. Its source definition had not
been removed, and the problem reproduced without xdist or database setup.

The accepted shared-fixture route now places those eight native fixture definitions under
`native_fixture_support`, registers them once in the package conftest and removes the old
semantic/acceptance conftest definitions and their re-export chains. No test ordering rule was
added. `fixture_collection_probe.py` repeats the exact 16-selector, 79-case selection without executing
fixtures; `raw/fixture-collection-after.txt` reports all eight definitions registered once and
zero missing fixture matches. The subsequent deployment-handle integration and bounded actual native retry below cross this
registration boundary. The larger 79-case union remains unqualified by that smaller retry.

### SQL reference boundary

Source and library references inform the narrow correction: SQLAlchemy Core supplies typed SQL
construction where applicable; pglast provides structural and PL/pgSQL inspection; SQLGlot can
qualify extracted query scopes against explicit schemas. PL/pgSQL variable/column binding and
catalog behavior still receive native authoring and real PostgreSQL controls. These references
supply no blanket SQL rewrite or additional validator. The fixture-visibility failure is owned
and repaired at pytest registration.


### Bounded native retry after shared registration

**Tested, 2026-11-13.** Managed result `11b3407a76f34ac09274b5585fe1fa6d` **passed**,
11 selected identities, 11 passed, with one worker. The exact selection comprises the sealed-head
control, all deployed data-operation identity controls,
`test_compatible_predecessor_reuses_exact_access_for_changed_companion`, and cold private-template
construction/disposal. The PDF case exercises real seal and compatible-predecessor reuse across
a changed companion, with the current producer-column guard installed. The deployed identity
module crosses the prior mixed-collector fixture-lookup boundary. This establishes bounded
native behavior; it supplies no cross-invocation head-reuse or complete DDO qualification claim.

The earlier `fc82fd2a666343f2916dac2b2cea448e` failure is preserved, as are earlier prerequisite
failures `20712b25d82c46a494fcdaf50d03791f` and `e67fcd551fcc4a138b2d3d0ec24b6cdd`.
The persistent database remains at `semantic_bep_located_v2` with its original OID and system
identity. `records/test-system.pdf-seal-producer.json` owns the second bounded repair result,
separately from the original-retention record. No frozen predecessor was rewritten.
