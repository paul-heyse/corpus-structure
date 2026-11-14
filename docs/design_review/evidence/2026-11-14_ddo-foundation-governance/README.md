# Declared-data foundations and frozen governance

**Registered; independent functional qualification remains with the DDO coordinator, 2026-11-14.** This folder records the combined final-source successor, including the reopened native authoring, privilege-policy, Core/binding and provider-contract foundation changes. Current scope and completion state belong to the declared-data-operations plan.

**Tested, 2026-11-14:** fixed source `9885b8d47ad5d1922ac3df38ce4438293b00daa7` produced preview `c09ac8c551fd41b8a495849b2b308abd`, complete rollback-only candidate `d1a42177213a44f9bcd291901c8fd4ed` and registration `9e722ce4c1794745a3e57ba454cacb8c`, all **passed**. Authoring replays the exact registered base, executes the complete rendered upgrade under its bound migration authority, independently checks native and privilege catalogs and runs the frozen physical/catalog guard, then rolls everything back. The candidate was not accepted merely because normalization succeeded.

All operation and SQL pages were inspected before registration: **19 native transitions** (15 changed functions, 4 new private provider functions), **212 privilege normalizations** (207 tables, 5 schemas), and **5 ordinary operations** (four explicit CHECK replacement operations, one frozen physical-contract insertion). Initial ACL/column before-state remains explicitly unrecorded and cannot be reversed as an invented exact state. Later recorded transitions retain exact reversible facts. Purpose roles have no effective schema CREATE, PUBLIC is treated as the PostgreSQL pseudo-role, and delegated grants are revoked explicitly in dependency order. Owner column grants are cleared without erasing implicit owner rights. Seven foundational reference tables now declare evaluator-only reads, retaining the protected evaluation boundary.

Final trigger ownership follows the declared final parent-table policy; staging ownership follows frozen predecessor facts. Old v2 namespace bindings keep their interpretation. Final literal trigger facts clear the realized binding, and the targeted actual intermediate transition → parent transfer → final admission → unchanged second-pass comparison passed (`57761654e3314b1caf69bda904c53564`). The frozen v1 envelope still decodes exactly; the new tagged v2 envelope retains native and privilege operations separately. [Artifact inspection](results/frozen-artifact-inspection.json) records those boundaries.

Frozen `semantic_ddo_found_v1` follows `semantic_ddo_origeps_v1`; existing frozen predecessors were not edited. [Registered hashes](results/registered-files.json), [candidate inspection](results/candidate-inspection.json) and the [authoring record](records/ddo.foundation-governance.json) retain the result. The acquired development database remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232, PostgreSQL18.7 on port5434; the checkout head is `semantic_ddo_found_v1`. No persistent deployment, activation or cutover occurred. [Target closure](results/acquired-target-closure.json) records the read-only observation.

[Failed/interrupted attempts](results/retained-authoring-attempts.json) retain their original managed receipts and dispositions. The three `diagnose_*.py` probes and their results are bounded historical rollback diagnoses at the source which exposed each defect; they are not current production routes or qualification substitutes. The dependency probe at `f5884daee` found explicit grant delegation dependencies, the policy probe at `6f658f0d1` identified an owner-column ACL residue, and the catalog probe at `a6b48f5f9` identified the independently enforced reference isolation failure. Their source may no longer reproduce a refusal after its owning repair.

New reference-policy/schema-USAGE and safe catalog-phase/rollback tests passed (`f06643b2b18a4fdeafae381c84660d46`, `a39048943bef4ed9992d08fbc8e86dea`). Final source types and Ruff passed (`6cc0709bd86f44d6bd14553d91dec3b6`, `85cf69340f2f479f9b016931dc00c9ef`). These bounded checks and registration do not establish full functional or provider qualification. The coordinator accounts for the required union and all retained failures.

The ordinary-operation count initially required reviewing the delivered exact source bundle because the managed candidate summary omitted the authoring counts. That CLI omission is repaired: `uv run ci model change inspect-candidate d1a42177213a44f9bcd291901c8fd4ed --json` now returns typed `operation_counts` with 19 native, 212 privilege and 5 ordinary operations directly. The view authenticates retained hashes and parses the upgrade structure without executing it. The focused old-v1/new-v2 reporting and tamper-refusal cases passed (`6fa27138d8004ac8bbdf6c86a4bd7fa8`); original reporting/test assertion failures remain `ef5af49088c546cbbef8149194530de9` and `8126c6ca6a7043359d0ccb45ac403b55`. This reporting-only repair does not change frozen artifacts, migration behavior or the registered authoring evidence.

## Explicit discovery input association successor

**Registered; rollback authoring Tested, 2026-11-14.** `semantic_ddo_drole_v1` follows
`semantic_ddo_found_v1`, implementing ADR-0104's optional explicit discovery input-role association.
The planner and native admission bind that role to its authenticated parent product/member and full
child context. Existing original/computed eligibility remains; no implicit origin preference or
cross-product body deduplication is introduced. Omitting the association preserves frozen intent
meaning. Functional child publication is assessed separately in the coordinator.

Fixed authoring source `cf772c04a` produced preview `e0e4820bcfb846099c211e8924fd5781`, complete
rollback candidate `a149225c771e4f8ab803bbe388e295df` and registration
`15152b56c69f4a3ea382c390663288bc`, all **passed**. All seven typed operations and their complete
parsed statement-kind inventories were inspected, plus the new private helper's full SQL. There are
seven native transitions: one private membership helper, four binding/population function body
changes and two descriptor changes. No trigger transition is emitted on this actual next pass.
Ordinary and privilege operations are both zero. The helper is
publisher-owned with PUBLIC EXECUTE revoked; existing purpose ACLs remain unchanged. The candidate
executes the complete upgrade and independently verifies catalogs in rollback-only authoring.

The [first request](change-discovery-role.yaml) at `0a8a60473` produced candidate
`33d506da4e884aeab95efa4a871088e8`, which **failed** before registration: raw series trigger
definitions still assumed namespace ownership after the predecessor parent became publisher-owned.
The previous direct intermediate/final comparison test did not exercise raw-definition preparation
on that second pass. The corrected [forward request](change-discovery-role-forward.yaml) at
`cf772c04a` projects staging ownership before normalization from frozen parent facts, using declared
target policy only when a new/moved parent lacks predecessor facts. Conflicting explicit literal
owners and invalid bindings refuse; the independent owning-relation guard is unchanged. No live
owner is adopted. Actual found/origeps artifacts and raw definitions now cover this next-pass
regression: `1bc7a9ba9f23432ca4450974ae96a9d3` **passed** after the retained fixture-prerequisite
failure `235bb23fc4b34a3fa860713d0f61be2a`. Final types `00b9d102fd1540508055dd784b2cf7de` and
scoped Ruff **passed**; independent source review found no material blocker.

[Operation inspection](results/discovery-role-operations.json),
[candidate verification](results/discovery-role-candidate-inspection.json),
[registered hashes](results/discovery-role-registered-files.json),
[retained refusal](results/discovery-role-attempts.json) and the
[authoring record](records/ddo.discovery-role-governance.json) retain exact scope.
The [read-only target closure](results/discovery-role-target-closure.json) confirms the development
revision remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232, PostgreSQL18.7
port5434. The checkout head is `semantic_ddo_drole_v1`; registration did not deploy or activate it.
Frozen predecessor files and earlier evidence records are unchanged.

## Captured wire ingress follow-up

**Registered; rollback authoring Tested, 2026-11-14.** Actual source retry
`26d785913a624aab9f000f64e2d3e792` failed before native association behavior because the closed
wire definition still allowed only the original four discovery fields. Source `17391b934` adds
optional identifier `target_role` to the authoritative protocol YAML. Python and native wire SQL
use the same captured schema; additional properties remain closed, and null/empty/nonstring values
refuse. Omission retains its existing meaning. Release-specific role/member eligibility remains
native admission's separate responsibility. The new wire control passed
`e5d1ee6367dc4f73b9e994219f36f6b9`; types `e53eb2b1bae84b0aafc5b3c78ab013e9`, scoped Ruff and
independent ingress-consumer review passed.

The raw protocol dependency changes physical/type source IDs and the generated protocol SHA;
fate memberships and the recordable fate SQL fragment are unchanged. Public call digests use their
field/correspondence contracts rather than this raw protocol hash, so their shapes/implementation
remain unchanged. The [fixed wire request](change-discovery-wire.yaml) produced preview
`5e06720b11284175be18219403660455`, complete rollback candidate
`037eaddc1677428f87f70dcb9b7895b8` and registration `9b1b758fd5724871bcdd999588747277`, all
**passed**. `semantic_ddo_drole_v2` follows immutable v1. Its seven native operations update the
wire validator, two descriptors and four dependent companion projection-ID literals. Those four
read queries retain their semantics; their inspected textual change is the projection identifier.
There are zero privilege operations and one ordinary publisher-owned `INSERT` into
`sem.physical_contract` for the captured source. No trigger or physical table DDL is emitted.

[Candidate verification](results/discovery-wire-candidate-inspection.json),
[all native operations](results/discovery-wire-operations.json),
[ordinary statement inspection](results/discovery-wire-ordinary-inspection.json),
[registered hashes](results/discovery-wire-registered-files.json) and the
[wire authoring record](records/ddo.discovery-wire-governance.json) retain scope.
The [target closure](results/discovery-wire-target-closure.json) again records unchanged development
revision/OID/system/port; the checkout head is now `semantic_ddo_drole_v2`. No deployment or
activation occurred. Actual scoped child publication remains with the coordinator's focused
functional receipt; authoring alone does not establish that behavior.

## Scoped functional closure

**Tested, 2026-11-14:** exact source-discovery replacement
`6a71d58d9ef64e319beb7f3e0278e7ba` **passed** the one selected closed-two-scopes identity,
including actual publication of both child products with exact parent/member input references,
native invalid-role registration refusal and same-context standalone-original substitution refusal
with valid rebuilt keys. It ran from committed `d87f1acb8` without product/test source changes,
against freshly built and verified `cs_sem_head_a931f08d5bdaf700`, deployment key
`a931f08d5bdaf7008ca6bae906168cc524ad171a691441d405bc05bbf8245d4e`; no deployment-key gap and
complete reporting. The original cardinality, wire-ingress and fixture failures remain retained.
This is bounded functional evidence; full final-head/provider/series qualification remains open.
The coordinator owns the complete selection/replacement account, with named managed receipts held.
