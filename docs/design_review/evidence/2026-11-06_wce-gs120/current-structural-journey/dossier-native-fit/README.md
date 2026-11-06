# Full dossier native execution repair

Current disposition: **Tested on the full declared workload, 2026-11-06.** The coordinator integrated,
froze and deployed the batch repair as native163. Actual full8280-member dossier runs184/185 both
passed the ordinary registered completion path under the unchanged120-second deadline. Server
statement durations were93,576.252ms for greedy and16,183.975ms for source order. Both complete
Reader products and full portable bundles subsequently verified; see `../dossiers002/result.json`
and the parent journey README. This establishes fit for this actual workload, not a speedup or a
scaling guarantee. Global database temp counters are retained with nonexclusive attribution.

The proposal sources and patch text below retain their pre-integration baseline. They are historical
repair evidence; current package code and the deployed frozen descriptor own implementation.
`prepare_proposal.py` expects that original source baseline and is not an updater for the already
integrated native package. The later portable-consumer WCE-R12 failure and repair are separately
retained in `../dossiers002/`; they did not invalidate accepted native membership.

**Proposed, 2026-11-06.** This folder preserves the failed native completion and a reviewable repair. No package SQL, catalog function, schema, release, task result, timeout or consumer budget was changed by preparing these files.

The actual greedy dossier run182/task1068 failed while validating an 18,786,617-character completion envelope. It has **zero accepted task results**, is failed and unsealed. The full membership attempt used all8210 coupled contributions from run180/cut243 plus the protected structural predecessor run169/cut225, with48 original sources/passages and8212 declared dependencies. The control dossier has not started. The failed attempt remains under `../dossiers001/`.

`observed-failure.json` retains deployed function source, exact failed task/run and original runtime/release. Native `ops.structural_dossier(jsonb,jsonb)` body line38 was:

```sql
member_:=ops.dossier_contribution_member(inputs,reference);members:=members||jsonb_build_array(member_);
```

The fresh writer session has no session-wide statement timeout; completion applies a **120-second transaction-local deadline**, from the effective `Settings().database.completion_statement_timeout_seconds`, through `semantic/claim_lifetime.py:_deadlines`. The repair retains this deadline. No30-second limit was established.

The observed source performs two repeated operations at full population size: it rereads/decodes a large original producer body for every reference and reconstructs a growing JSONB membership on every append. The one-reference member projection additionally scans the8212-element dependency array each time. These are source-level growth findings; this preparation does not claim a measured division of runtime among them.

## Proposed implementation

`native-batch-members.patch` is an unapplied patch against the current package. `proposed-dossier-contributions.sql.txt` is its complete proposed source for inspection. `prepare_proposal.py` recreates the patch text without mutating package files. The batch resolver source is also isolated in `batch-resolver.sql.txt`.

The **single** custody/closure validation owner becomes private `ops.resolve_retained_source_contributions(jsonb)`, returning reference/contributions/sources rows. It groups exact references by all custody fields except contribution ID, loads and indexes each backing result once per exact binding, validates the union of all requested transitive endpoint/member closures, and shares original native source/projection custody. Each individual root still gets its complete, sorted closure. No rows enter from caller-supplied semantics.

The existing public one-reference resolver delegates to the batch owner with one reference and preserves its `{contributions,sources}` result and guards. Its one-reference source order remains first appearance in sorted closure order. There is no parallel historical validation route.

Private `ops.dossier_contribution_member_from_retained(jsonb,jsonb,jsonb,jsonb,jsonb)` owns the existing citation/role projection, shared by the single and batch member callers. Its inputs are typed input JSON, exact reference, authenticated raw closure, authenticated sources and dependency membership index. The existing one-reference member wrapper authenticates through the unchanged public resolver API. Private `ops.dossier_contribution_members(jsonb,jsonb)` authenticates through the same batch resolver and builds the dependency index once. The48-source/48-passage citation checks remain explicit and unchanged; no large dependency or original producer report is rescanned per member.

`ops.structural_dossier` aggregates streamed source members once with `jsonb_agg`, then performs the existing total ordering, selection, full omission list, facet calculation and digests. The small structural predecessor branch remains unchanged; source membership never depends on the display budget. The source route stays proposed and contributes no independent support facets. Protected assertions remain the sole existing source of those facets.

New internal declarations and authoring order, all captured by the accompanying `native_candidate.py` hunk:

1. `ops.resolve_retained_source_contributions(jsonb) RETURNS TABLE(reference jsonb,contributions jsonb,sources jsonb)`
2. Existing `ops.resolve_retained_source_contribution(jsonb)` wrapper
3. `ops.dossier_contribution_member_from_retained(jsonb,jsonb,jsonb,jsonb,jsonb) RETURNS jsonb`
4. Existing `ops.dossier_contribution_member(jsonb,jsonb)` wrapper
5. `ops.dossier_contribution_members(jsonb,jsonb) RETURNS SETOF jsonb`
6. Existing `ops.structural_dossier(jsonb,jsonb)` from `structural_products.sql`

Every helper has explicit `REVOKE ALL ... FROM PUBLIC`; only the existing singular resolver retains reader/writer EXECUTE. New helper bodies are inventoried and frozen with no application grants. SECURITY DEFINER functions retain the existing fixed `pg_catalog,pg_temp` search path. Root integrates the native descriptor/migration and candidate source capture.

The patch preserves exact reference fields/types, completed and final-cut custody, selected/origin/run/project/release/revision/runtime bindings, original task unit identity, contribution canonical identity, recursive endpoint closure, original run source membership, complete native pins and anchor pins. Projection retains exact source/piece bridges, quote/bounds, every original endpoint citation and computation dependency, declared passage coverage, semantic role/scope and proposed standing. It preserves all8210 source members, original typed structural distinctions, protected support facets, mandatory overflow and both display policies. No new store, workflow, semantic flag, timeout increase or output truncation is introduced.

## Pre-integration verification and handoff

**passed:** `git apply --check native-batch-members.patch` and `git apply --check regression-tests.patch` from the repository root using the full evidence paths. Offline pglast SQL parse passed11 statements; PLpgSQL syntax parse passed5 bodies after replacing the unresolved project composite declaration `kb.source_view` with `record` for the offline parser only. Proposed Python tests parse through `ast.parse`. These are syntax/applicability checks, not native catalog or performance qualification. `proposal-static-checks.json` records this boundary.

`regression-tests.patch` adapts the existing explicitly composition-only resolver substitution to the single new owner; it does not present substituted custody as a production pass. New controls exercise both real resolver entry points on malformed references, private helper grants, and literal endpoint citations/dependencies/proposed standing through the projection helper.

At proposal capture, installing/admitting the combined native candidate, native test execution and
actual full dossier completion were **not_run** under the coordinator's source/DB hold. Those were
subsequently performed through the ordinary registered native163 route, with the full current
results linked above. The accepted full runs retain identical complete member/facet digests;
all members, omissions, endpoint citations and continuation pages survive native acceptance,
ordinary Reader and complete portable export. The failed run182 remains failed and unsealed.
No direct-function-only pass or substituted custody is used as full qualification.

`batch-members.sql.txt` is a superseded initial draft, retained as proposal history. It is not an
input to `prepare_proposal.py`, not part of the accepted patch and not a production implementation.
The accepted native package has one current batch custody-validation owner with the singular
resolver delegating to it.
