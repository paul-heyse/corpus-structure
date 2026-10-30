# Historical archive controls

These are immutable test inputs, not operational runs or admission evidence.
`reader-v10.json` and `reader-v10-analytics.json` are the genuine pre-change compiler-10
archives already retained for SP-I04. Their recorded aliases, scalar recipes and libraries
remain authoritative for reading.

`reader-v11.json` was produced on 2026-10-29 by the unmodified source at
`c98046a` (full commit in `historical_producer_commit`), using its real
`prepare_release` and `PreparationProfile`, from `reader-v10.json`'s source bytes.
`reader-v12.json` was produced identically from unmodified `b1e23ed` source.
Generation extracted `git archive <commit> python/corpus-structure/src` into a temporary
directory, launched the pinned Python with that directory as `PYTHONPATH`, and serialized
its returned manifest, profile, products and artifacts. No dependency installation or
compiler/profile relabelling was used. Both manifests retain the producing runtime tuple.

The compatibility contract exercised by `tests/semantic/test_release_compatibility.py` is:

| Compiler | Product opening and retained boundary vectors | Full verification by current compiler 13 | New activation by current compiler 13 |
| --- | --- | --- | --- |
| 10 | Supported only with recorded legacy boundary/runtime recipe | Refused: requires historical compatible compiler | Refused |
| 11 | Supported only with recorded boundary/runtime recipe | Refused: requires historical compatible compiler | Refused |
| 12 | Supported with boundary ABI 12 and recorded runtime | Refused: requires historical compatible compiler | Refused |
| 13 | Supported with boundary ABI 12 and recorded runtime | Exact-source/product rederivation | Requires verification and live admission |

Historical reading is not admission. Cache controls additionally distinguish database identity,
current archive bytes, runtime changes, failed verification and finalized immutable projections.
Equal exported JSON Schema is explicitly insufficient for acceptance compatibility.

The selected-answer control restores an independent small historical-shaped completed-result
snapshot over the genuine compiler-10 archive. It is intentionally distinct from operational
runs 1/2 and does not recreate or regrade them. Administrator trigger bypass is limited to
restoring already-finished run/cut metadata; actual selection, public reading, explanation,
ADBC capture, detached export and new activation use their production routes. The control
asserts independently stated exact Decimal values and old release/realization identity before
and after activating a current release. It establishes this fixture journey, not a copied
production database or an alternate-runtime qualification.
