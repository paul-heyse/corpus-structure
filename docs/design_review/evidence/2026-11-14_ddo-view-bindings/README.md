# Role-qualified selected source-view binding

**Registered; focused functional qualification is separate, 2026-11-14.** The DDO coordinator owns current execution and remaining scope.

The two-view discovery control exposed a native prefilter that discarded each selected view because its scope differed from the whole-document consumer scope. `ops.data_binding_rows` now preserves scope equality for ordinary same-subject inputs while respecting an explicit declared subject-field association for related contexts. The source-discovery views role associates `/source/document_subject` with the authenticated original document; each selected input retains its real analyzed scope. Exact field/subject association, original source, kind/origin, project, selected admission, read boundary and current trust checks remain in force. This does not widen the frozen source selection or turn the selected views into execution roots.

**passed:** preview `617b19c5938b4bbcb3613c8f7f2d5303`, rollback-only candidate `e1b5b9d133154b3cb402ca5945f9f9c8`, registration `6fbf51bae07c4f82a8287a2aafc02ac7`. Typed operations and SQL inspection account for all3 native transitions: the binding-reader body and two source/catalog descriptors. Owners and ACLs are unchanged; ordinary schema operations are zero.

Frozen `semantic_ddo_viewbind_v1` follows `semantic_ddo_sources_v1`; all predecessors stay exact. Persistent revision remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232 on PostgreSQL18.7 port5434. No persistent deployment, activation or cutover occurred. [Registered hashes](results/registered-files.json) and the [authoring record](records/ddo.view-bindings.json) retain custody. Targeted native and actual provider results are distinct from registration.
