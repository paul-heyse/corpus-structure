# Target archive admission through the protected catalog guard

**Registered; targeted functional integration in progress, 2026-11-14.** The DDO coordinator owns current scope and test outcomes.

The exact eight-case native attempt `a5a2ea89cc34449aaefce5b9937214f5` stopped in setup because the common release guard unconditionally required the former execution model after authenticating a target archive. This successor uses the already authenticated current target archive branch and continues all common physical/catalog checks. It requires no fabricated legacy rows or widened grants. The target storage adapter no longer repeats relation checks already authenticated by that guard.

**passed:** preview `dd0f65aa17294e10ae4280feb34902cb`, rollback-only candidate `3355d3b457784a8c821fd76bc75a6dec`, registration `914df3a50a1f475b9cc92ad9903d9494`. Typed operations/SQL inspection covers all3 body transitions: the existing release guard and two descriptors; zero ordinary schema operations. Owners and ACLs are unchanged.

Frozen `semantic_ddo_admission_v1` follows `semantic_ddo_inputs_v1`. No persistent deployment, activation or cutover occurred. Persistent database remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232 on PostgreSQL18.7 port5434. [Registered hashes](results/registered-files.json) and the [authoring record](records/ddo.target-admission.json) retain custody. Functional retries and actual provider qualification remain separate.
