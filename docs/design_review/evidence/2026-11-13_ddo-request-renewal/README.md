# DDO native request renewal · 2026-11-13

DDO-06 consumer: add exact fenced renewal for runless requests while retaining the persistent
working database at its acquired predecessor. The coordinator owns qualification and remaining scope.

- Preview `4a995948c9ed47e8898219b36738d7ed`, apply `0e592cb60c724548b2198caba750ec58`,
  candidate `c0bc9cb2ef864ae5a1f920afe97975db` and registration
  `183339d45b524c9f8501d66ba10d8830`: **passed**, normal `uv run ci model change` route.
- Immediate predecessor `semantic_ddo_recovery_v1`; frozen successor `semantic_ddo_renewal_v1`.
  Rollback-only authoring temporarily replayed the registered chain from `semantic_bep_located_v2`
  on corpus_structure_dev/OID25921445, PostgreSQL system7701811359771751232, port5434.
- Five native transitions: renewal implementation/wrapper, wire validator and native/execution
  descriptors. Zero ordinary schema operations; no table or column drops.
- Candidate hashes: Python `f8082ecfe98333d04ed1a1d07c92635a3ce607fd6bb2bed3ac8cd2383187f9cd`,
  operations `01c04ab9d7bec5886561f009cb81b1d96daf03c1e89c0f2198a82f11b06a162b`,
  admission `4d9d8a16d116c82006850caa6ba90bc2e543dfe2785ed67eb2cdb45ed3dca4d6`.
- Preview `df2c037e923c4c569b01610b46f8c2d5` predates the final compiler typing repair and was
  replaced before candidate authoring. Later claim-owner exception-custody changes require fresh
  source/target acquisition for future adoption; this receipt does not establish deploy readiness.

Native renewal checks use the installed frozen successor in isolated databases. No persistent
migration, deployment, activation or provider-model execution is performed by this work.

## Native qualification

**Passed:** 22 selected controls, `d8b1d561275843cda53b427d28a7056c`, normal installed
frozen-head/native-admission fixtures. The coordinator records the exact two-path selection.
`uv run ci db status --maintenance --json` confirms corpus_structure_dev remains at
`semantic_bep_located_v2`, with repository head `semantic_ddo_renewal_v1`.
