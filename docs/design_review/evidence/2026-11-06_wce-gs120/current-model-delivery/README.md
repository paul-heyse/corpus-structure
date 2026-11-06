# Final model 161 delivery

This evidence-only delivery reads finished, sealed **run 161 / cut 245** through
ordinary current contribution and portable-review services. Its producing release
is `release:cb08727ec668c048998c82db31ef0e1242d714ca23e2b0f2a223eb88c6061a29`,
producing runtime is
`runtime:70a610fa285397ef7234acca6190db4e0f710b459a2f36d3b3e593c77e0a0d38`,
and producing code is `1d7e00c33d3c3e43f9e45793b10a8d0fa9748800+dirty`.
No producer, model, source, release or runtime is changed by delivery.

`source-inventory-pin.json` authenticates the final structural task 1069's current
`structural-product-3`, **44 components**, and the exact 48 original source
references and typed passage values against the neutral recovered packet. Its
retained physical-page coverage is 191–310. A failed initial raw-dictionary equality
check is retained: the report omits optional null keys present in the packet;
current typed passage comparison passed without changing any text or coordinates.

## Completed ordinary contribution delivery

**passed**, 2026-11-06: all 48 per-source selections, bounded continuation pages,
and atomic selected file exports. `delivery001/source-results.json` records:

| Retained population | Count |
| --- | ---: |
| Source reports | 96 |
| Operations | 42,781 |
| Explicit zero-output operations | 39,098 |
| Contributions | 66,638 |
| Interpretation rows | 66,638 |
| Public claims / assessment rows | 0 |

The read-only normalized census independently counted the exact completed-cut
contribution/operation population per source; every ordinary Reader selection
matched it. Operation rows are read independently of emitted contributions, so
zero outputs remain visible. Every contribution's interpretation facet is included.
There is no global contribution-inventory read or 10,000-row truncation: each
source is selected before hydration; the largest source has 5,929 contributions.

Each `delivery001/source-<id>/` contains streamed `pages.jsonl`, its exact page
receipt, `export/items.jsonl` and atomic export manifest, plus a result receipt.
Page responses retain the existing 16,000,000-byte bound. The unchanged ordinary
selected-file contract caps a source at 128 MiB; it was sufficient for every view.
The page stream also has an explicit cumulative 128 MiB source bound. Pages publish
to the final path only after the entire continuation is complete. API file exports
remain atomic and their hashes are checked on reuse.

Executed command:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/current-model-delivery/export_model.py --attempt delivery001 --phase all
```

`delivery001.log` retains stdout/stderr. After all 48 source exports completed,
the root requested a pause for native163 deployment. The process exited 130 from
a clean Python interrupt during first portable preparation. No portable bundle,
partial page stream or portable temporary directory remained. The interruption's
failure receipt and traceback are preserved; `upgrade-pause001.json` records the
exact resume state. This interruption does not invalidate the completed source
exports.

## Completed portable closure

The portable selection partitions the same source inventory into six
exact groups of eight views, plus a separate structural bundle. Every partition
starts with a 256 MiB complete-file budget, retains interpretations, and uses the
ordinary full source/raw-closure exporter and detached verifier. `delivery-index.json` and `delivery001/portable-index.json` verify the union contains
exactly all 48 source contexts and all 97 accepted original raw task bodies. Every
raw body matches its captured immutable canonical SHA256. There are zero missing
or extra reports and zero source/materialization omissions.

**passed**, 2026-11-06, after root GO under native163
(`semantic_wce_batch_20261106`) in a fresh consumer process. The command exited 0:

```sh
uv run python docs/design_review/evidence/2026-11-06_wce-gs120/current-model-delivery/export_model.py --attempt delivery001 --phase portable
```

This reused the finished source exports and invoked no ML provider. All seven
bundles passed the ordinary detached verifier under their initial 256 MiB bounds.
Their complete files total **1,027,161,039 bytes** (JSONL/Parquet relation files:
1,027,064,544 bytes); the largest partition has 207,887,189 relation bytes. The six
source bundles retain all 176,153 inventory rows, 42,781 capability/operation rows,
39,098 explicit gap/zero-output rows and 66,638 assessment-matrix rows. The separate
structural bundle includes the final 44-component product and raw task 1069.
The gap rows are declared operation states, not missing transport records or an
independent recall judgment.

`delivery-index.json` is the entrypoint: it pins all 48 ordinary file manifests and
page receipts, all seven portable manifests, the copied accepted-raw manifest, the
PDF source manifest, original producing runtime/release, and interruption/resume
receipts. `accepted-raw-manifest.json` and `source-manifest.json` are byte-identical
copies of their original source inventories. The portable
bundles claim only their declared native source/context closure. The parent PDF
and selected PDF cuts remain at the locations and hashes in `../source-manifest.json`
and the GS120 corpus files; the bundle does not embed or claim completeness of the
original PDF. Inventory/transport success supplies no semantic-quality, scientific
truth, public-admission or source-recall claim.

**not_run:** product edits, provider/model execution, release generation, database
writes, broad qualification, root maintenance and commits.
