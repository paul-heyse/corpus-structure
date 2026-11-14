# Bounded native execution acquisition

**Registered; focused functional qualification is separate, 2026-11-14.** The DDO coordinator owns current execution and remaining scope.

The remaining restricted CLI case exposed direct reads of private native definition/runtime tables. `inspect_data_execution` now supplies the one selected immutable contract and optional same-release runtime hashes through the existing closed native protocol, using the admission purpose. Callable acquisition compares the exact admitted recipe, implementation and runtime custody; publication acquisition reuses the selected contract projection. It does not transfer full runtime archives or re-admit every kind/operation for each selected port. Existing table ACLs stay private.

**passed:** preview `b28708ffe5774ae8842c74c4e32c3803`, rollback-only candidate `8bbe70261a3e4506a034f3ff4fda1642`, registration `84bb266238c4481ba74e95196c060c3d`. Typed operations and SQL inspection account for all5 transitions:3 changed bodies plus the private implementation and public closed-wire wrapper. The wrapper grants EXECUTE only to the existing admission principal; the implementation is publisher-private. There are zero ordinary schema operations. No persistent deployment, activation or cutover occurred.

Frozen `semantic_ddo_acquire_v1` follows `semantic_ddo_admission_v1`. All predecessors stay exact. Persistent revision remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232 on PostgreSQL18.7 port5434. [Registered hashes](results/registered-files.json) and the [authoring record](records/ddo.execution-admission.json) retain custody. Targeted native and actual provider results are distinct from registration.
