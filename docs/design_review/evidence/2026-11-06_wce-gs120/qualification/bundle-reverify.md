# Final-source portable bundle re-verification

Executed 2026-11-06 after coordinator GO: **passed**, all 23 declared bundles.
The [per-bundle result](bundle-reverify-run001.json) and
[streamed outcomes](bundle-reverify-run001.jsonl) retain the exact manifests,
selection digests, relation counts and final verifier source hash. Result SHA256:
`0ffa5dc2d6456a49bad65403d550d36828bd5fbaa5d775e38f2c1f55a508d80a`.
No bundle failed or remained unrun; source and manifest guards passed throughout.

Prepared 2026-11-06. This bounded
followup reassesses existing successful current portable bundles after the R12
offline verifier repair. It creates no bundles and accesses no database or provider.

The frozen [inventory](bundle-reverify-inventory.json) binds 23 bundle manifests to
their earlier successful indexes or detached verification receipts: seven model161
partitions, three sources002 policy arms, ten contextual closures, comparison163,
artifact183 and publication169. The contextual closures include the named160
definition-component selection; no separate named160 portable manifest was found
in the GS120 metadata inventory outside excluded dossier/temporary paths. Dossiers
belong to their current export writer. Failed baseline/product2/temporary outputs
and ordinary exports without portable manifests are excluded and preserved.

Preparation read only manifests and successful receipt metadata. Their declared
JSONL/Parquet files total 2,513,399,258 bytes; the actual execution subsequently
verified these files through the ordinary offline verifier. Exact manifest hashes,
selections, relation counts and prior receipt
hashes are in the inventory. The verifier source is
`python/corpus-structure/src/corpus_structure/serve/review_bundle.py`, SHA256
`f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928`.

The [standalone script](bundle-reverify.py) performs metadata checks by default;
the production offline `verify_review_bundle` is imported and called only with
`--execute`. The successful command, from the repository root, was:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/qualification/bundle-reverify.py --execute --attempt 001
```

Each completed bundle is immediately appended to `bundle-reverify-run001.jsonl`.
The final JSON retains all per-bundle outcomes, unchanged manifest/source hashes,
selection digests and relation counts. Failures get separate traceback files and
independent bundles continue; interruption retains completed results. Exclusive
file creation prevents overwriting an earlier attempt. A new attempt number is
required for any later run. Source and manifest hash guards surround each call.
The inventory's `not_run_waiting_root_go` fields are the preserved preparation
checkpoint; `bundle-reverify-run001.json` supplies the superseding actual outcome.

This establishes only the verifier's declared-context integrity and JSONL/Parquet
equivalence for these exact immutable bundles. It does not establish semantic
quality, scientific truth, original PDF completeness, producer execution on this
final source, or assembled qualification. Captured producer runtimes and releases
remain unchanged. The root owns union accounting and the qualification README.
