# Native scoped populations and cancellation

**Implemented; qualification in progress · 2026-11-13.** Normal rollback-only authoring
registered `semantic_ddo_population_v1` after `semantic_ddo_renewal_v1`. No persistent
migration, deployment or activation occurred. The acquired development database remains
`corpus_structure_dev`, OID25921445, system7701811359771751232, port5434, acquired revision
`semantic_bep_located_v2`.

- Current preview `f063189a6f404d2ab5107146a3c6f7a5`; apply
  `69b0c89f795c41b4abe503afb65e5bff`; candidate
  `452fdebd362042d79efc1a9e50d20769`; registration
  `834f73e19e1a4d54aaf1afb26b45ac4c`: **passed** through the installed
  `ci model change preview/apply/candidate/register` routes.
- Candidate contains 39 native changes and seven ordinary physical operations. Ordinary
  changes add the immutable demand cancellation table, selected-obligation population
  column/index/FK/consistency check and corresponding ownership. No source/product rows
  or original evidence are removed.
- Frozen native behavior includes request-generation orphan fencing, shared-demand
  cancellation, subject association, explicit authenticated cross-source sets,
  read-derived selected populations, context-scoped population currentness and
  product-qualified member closure. Formal extraction/provider migrations remain separate.
- Earlier preview `61405dc2a70d4c38a2fa60add871970e`, apply
  `519d423c6b8045738860a2dbb50f0ea6`, preview
  `40f635be75d24779946b60974fd575b9`, apply
  `6d22a20429eb4f6da034187087fec8b8` and candidate
  `8f6b8dea7f324c71a79129a37484be14` are superseded authoring observations. The latter
  correctly lost registration standing after `semantic/composed.py` changed during
  implementation. The final candidate reacquired that source; no bypass was used.

The coordinator owns targeted qualification and remaining implementation. Future adoption
must reacquire the exact final source, target and registered forward chain; registration
alone does not authorize or establish production adoption.
