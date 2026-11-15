# DDO model archive shape

Targeted diagnosis of retained test result `2950f7ac49574c4a970e491119d89972`,
`test_actual_definition_demand_retains_provider_pair_and_exact_component_source`.
The failure is PostgreSQL `ProgramLimitExceeded` while
`sem.require_execution_projection` converts the entire `data_operations.json`
artifact to JSONB to read its version. Its native release was
`release:97786abad65ba4a2e3087b7b07d89f92330ed92ef7d58ec31366d2adc6f178e1`.

## Scope and reproduction

The coordinator authorized one static reproduction, capped at 300 seconds. It uses
the existing `_captured_definition_recipe` with actual provider assets and its
existing metadata preflight. It performs acquisition and release preparation only:
no database connection, runtime binding, inference, publication or provider model
resident. Input names, sizes and SHA-256 digests are retained in `inputs.json`;
the result records the Git heads and interpreter. This is a size-limit correctness
diagnosis, not a runtime benchmark or provider verification.

```bash
CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 \
  timeout 300 .venv/bin/python \
  docs/design_review/evidence/2026-11-14_ddo-model-archive-shape/probe.py \
  > docs/design_review/evidence/2026-11-14_ddo-model-archive-shape/stdout.txt \
  2> docs/design_review/evidence/2026-11-14_ddo-model-archive-shape/stderr.txt
```

**Outcome: passed**, exit 0, observed 2026-11-14. `result.json` holds the full
bounded summary. Both Git heads were
`c767ef5f779c5ef199d7844aebc6839c40cbfd47`; input digests also identify captured
bytes independently of concurrent working-tree edits. No production files were
changed by this investigation. Native/provider verification is **not_run**.

## Observed shape

The static reproduction exported `data_operations.json` at **223,217,117 bytes**,
SHA-256 `ef2f3921f69738db0239ea41dd522b744bf77601c9f1bbd44ed85bb3d3c58ae0`.
The probe retained only summaries, not another full copy of that artifact.

| Array | Records | Serialized bytes |
|---|---:|---:|
| identities | 6,277 | 204,671,906 |
| kinds | 6,056 | 7,739,168 |
| nodes | 6,180 | 6,627,944 |
| edges | 11,828 | 2,925,167 |
| operations | 62 | 559,831 |
| implementation_slices | 35 | 383,720 |
| bindings | 62 | 307,414 |
| graph_projections | 3 | 1,817 |

Kind identity preimages alone occupy **200,472,407 bytes**. Implementation-slice
preimages occupy 1,706,780 bytes. The largest kind preimages are
`SourceObservationBatch` (2,994,782 bytes), its `structural_product` property
(2,523,420), and `StructuralProductReport` (2,520,611). The largest governing kind
fact is only 64,261 bytes. Provider model bytes and implementation slices are not
the dominant model body. The native definition projection is 8,021,373 bytes.

The serialized text is below the reported JSONB container limit; conversion adds
the binary representation's per-value/container overhead. The retained native
failure and this array distribution support the duplicated identity array as the
dominant cause. This probe did not separately convert arrays in PostgreSQL, so it
does not claim to have located the exact failing binary sub-container.

## Structural owners

- `data_operation_compilation.py:_compile_identities` retains the entire canonical
  input in every `EffectiveIdentity`, including a complete rooted graph per kind.
- `data_operation_identity.py:SemanticGraph.rooted_record` repeats shared node
  payloads across overlapping closures. `SemanticGraph` already encodes payloads
  with `semantic_value`; `canonical_identity` encodes the entire rooted record
  again. This framing is existing identity semantics and must not be changed
  casually to reduce representation size.
- `data_operation_model.py:EffectiveDataOperationModel.content` exports all these
  identity witnesses, as well as the governing kinds, graph and implementation
  slices. A witness is derivable from those governing facts by the existing pure
  fingerprint functions; repeated witness material is distinct from independent
  retained source or execution evidence.
- `nominal_schema_kinds.py`, `data_operation_wire.py:schema_closure` and
  `data_operation_compilation.py:_materialize_json_schema_properties` also retain
  self-contained schema closures. Small pure probes found current native wire
  declarations total 330,514 bytes, their projected field schemas 349,386 bytes,
  structural nominal declarations 616,857 bytes, their field schemas 814,382
  bytes, and math nominal declarations 20,543 bytes. These figures identify some
  duplication but do not alone explain the full-model failure.

Whole-model JSONB conversions also occur in `runtime_bindings.sql`,
`data_operation_bindings.sql` and `data_operations.sql`. Repairing only the
version query would leave the same representation requirement in subsequent
admission, demand and binding checks.

## Candidate repairs

**Preserve the current archive format.** PostgreSQL `json` preserves text and
offers `json_array_elements` and path extraction independently of JSONB. Native
admission can extract the required governing arrays/headers without converting
the complete archive, retain exact archive digest checks, and put authenticated
bounded operational facts in the existing native catalog. Hot calls should use
those admitted facts rather than repeatedly parse the full archive. This preserves
current archive bytes, but retaining repeated witnesses still costs Python
serialization, archive space and static preparation memory.

**Compact the archive explicitly.** A new current model format can retain kinds,
graph, implementation slices and identity `(owner, domain, key)` headers, with
exact canonical identity inputs reconstructed on demand from those same governing
facts. Preserve existing DDO-02 encoding and identity keys, strict decoding,
historical exact bytes, and execution refusal for old model versions. This removes
repeated derived witnesses rather than deleting semantic facts, but is a deliberate
archive-format migration. The coordinator owns the version/decision route.

**Recommendation:** compact the current model at this explicit version boundary.
This removes the measured dominant repeated body, preserves the full governing
model, and avoids introducing a second operational catalog solely to work around
the current duplication. Keep independent exact DDO-02 preimage/key vectors and
add focused archived-model witness reconstruction, strict malformed-input refusal,
historical exact-byte readback and actual definition-demand archive checks.
Do not alter the existing double semantic tagging to reduce size: that would
change identity semantics, whereas omitting reconstructible repeated witnesses
need not change any kind/definition/eligibility/implementation/recipe key.

The bounded-native-projection route remains a separate option if preserving v4
serialization is chosen. It must cover all full-model consumers, not just the
first version guard, and retain correspondence to the exact original artifact
digest. Repeatedly reparsing a 223 MB text archive on each input-binding operation
would leave a material efficiency issue.

PostgreSQL contracts: [JSON types](https://www.postgresql.org/docs/18/datatype-json.html)
describe the textual and decomposed representations; [JSON functions](https://www.postgresql.org/docs/18/functions-json.html)
document typed extraction. No PostgreSQL limit increase or validation bypass is
proposed.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Declared data operations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Captured effective model repeated identity witness diagnosis](records/ddo.model-archive-shape.json) | DDO-06–08 | partial | — | 2026-11-14 |
<!-- evidence-index:end -->
