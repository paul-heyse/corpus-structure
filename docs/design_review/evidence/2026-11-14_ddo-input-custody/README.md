# Native semantic input and receipt custody

**Registered; functional integration in progress, 2026-11-14.** The DDO coordinator owns current DDO-06–08 scope and targeted test outcomes.

This immutable successor combines exact product/member header selection, authenticated semantic FrozenSourceSets and source-set association, complete member-specific support, unordered physical ledger slots, explicit retained cross-demand input reads and provider logical receipt fences. Source positions and semantic identities remain unchanged. Cross-demand pins still require the current consumer read/trust, exact project and declared producer/kind context. The existing admission guard handles its restricted purpose without widening grants.

**passed:** preview `186a1fb54a1a4f9eaadeec42e340dbc2`, rollback-only candidate `6ce46f76dabb4f5baabd1993667745cf`, and registration `3418bdeb62ea44b9b5451b3fefa644db`. Typed operation inspection covers15 transitions:11 body changes and4 new publisher-private functions. Existing owners/ACLs are unchanged; there are zero ordinary schema operations. SQL inspection covered ordinals1–14 and continuation15; every statement parsed. No persistent deployment or activation occurred.

`semantic_ddo_inputs_v1` follows `semantic_ddo_context_v1`. Frozen predecessors stay exact. Persistent revision remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232 on PostgreSQL18.7 port5434. [Registered file hashes](results/registered-files.json) and the [authoring record](records/ddo.input-custody.json) retain custody. Functional and actual provider checks are separate obligations, not established by registration.
