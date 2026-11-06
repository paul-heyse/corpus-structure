# Artifact configuration ABI correction preparation

Prepared 2026-11-06 by independent assessor/integration worker B, under root's bounded preparation-only brief. **The production patch is not applied.** No production files, migrations, provider calls, database writes, global generation or commits belong to this preparation. Root owns application after active GLiNER161 completes, final source/runtime freezing and qualification.

The defect is native decoding of registered configuration, not the registrar's canonical serialization. Actual ordinary artifact run181/task1067/config307 is failed, unsealed, task cancelled, with **zero accepted task results**. Its stored `title_threshold` is string `"70"`; all five stored policy probabilities are decimal strings. The existing typed configuration restores the expected floats, and `canonical_numbers(typed.model_dump(mode="json"))` exactly reproduces all stored params. The direct numeric helper controls exercised a different representation and therefore missed this boundary.

## Exact contracts and owner

- [registry.py](../../../../../python/corpus-structure/src/corpus_structure/orchestrate/registry.py), `canonical_numbers` line88 and `MethodRegistry.resolve` lines217–224: finite floats become canonical decimal strings before configuration hashing/registration; integers/bools are preserved by that generic serializer. The typed artifact fields determine what is valid for this method.
- [canonical.py](../../../../../python/corpus-structure/src/corpus_structure/core/canonical.py), `CANONICAL_DECIMAL` line31 and `decimal_of_float` line118: finite shortest-roundtrip decimal strings, with no exponent or redundant zero spelling. Configuration custody bytes must not be rewritten to numbers.
- [artifact_identity.py](../../../../../python/corpus-structure/src/corpus_structure/methods/artifact_identity.py), `ArtifactIdentityConfig` lines33–46: title threshold is a float in `[0,100]`; policy is the declared typed artifact model. The method emits the typed numeric policy in its product.
- [semantic/artifact_identity.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py), `ArtifactScoringPolicy` line173: exactly five strict probabilities in `(0,1)`. These are declared model assumptions, with no calibration or scientific-truth claim.
- [identity.sql](../../../../../python/corpus-structure/src/corpus_structure/semantic/sql/identity.sql), `data.decimal_canonical` line8: existing native finite-decimal lexical/normalization owner, reused locally to check canonical config strings. Exponent strings are refused before normalization can expand them.
- The actual SQL owner is [structural_products.sql](../../../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql), `ops.validate_artifact_identity` line507. There is no separate `artifact_identity.sql` owner in this route. Its original number-only threshold guard and direct product-policy/config-policy JSONB comparison reject the ordinary canonical registrar representation. Numeric product policy remains the model-ID hash input through `data.canonical_json(policy)`; this ABI is preserved.

## Proposed correction

[artifact-config-abi.patch](artifact-config-abi.patch) is an exact unapplied diff against the two production baseline hashes in [patch-preparation.json](patch-preparation.json), plus one new native regression module. SHA256: `5bc4390329527460668bce484561311a2c4af773930d227e701122ef03bc7bb1`.

The SQL change decodes only `title_threshold` and the five declared policy fields into local finite double-precision values. It accepts the canonical decimal strings emitted by the registry and retains the existing direct JSON-number helper representation. It requires the exact policy keys, rejects wrong scalar/container types, noncanonical strings, nonfinite/overflow values and out-of-range values, then compares the product's numeric policy with the decoded configured policy. The decoded threshold is used in the existing lexical route calculation. Conversion exceptions are retained as invariant refusals (`23514`).

The patch does not change method config serialization/hashing, semantic product/model identity, candidate routes, pair likelihood replay, exact source custody, purpose permissions, runtime guards or source discovery. No manually recoded configuration or output bridge is proposed.

The new ordinary-path regression uses the existing real completed native source fixture, actual `MethodRegistry.resolve`, actual `run_source_methods`, actual method execution, stored canonical config and accepted native completion. This controlled native source has no numbered artifacts, so its empty artifact cohort isolates the registrar/completion ABI. It does not establish pair likelihood quality or corpus artifact discovery. A second fresh ordinary registered run deliberately forges a valid numeric product policy against its unchanged registered config and requires native refusal plus no accepted result.

The existing nonempty replay test is extended to compare numeric and canonical-string config representations and reject malformed threshold/probability types, missing/extra policy keys, NaN/infinity spellings, overflow, noncanonical exponent/trailing-zero spellings, boundary violations, valid changed-threshold/frozen-route forgeries and exact-policy forgeries. It retains its explicitly controlled source-replay boundary; it is not promoted to real-source custody qualification.

## Checks and execution limits

| Outcome | Command | Scope |
|---|---|---|
| passed | `uv run python docs/design_review/evidence/2026-11-06_wce-gs120/artifact-config-abi/inspect_registered181.py` | Purpose `evaluate`, explicit read-only transaction; actual181/1067/307 metadata and typed/canonical roundtrip. Receipt: [read-only-custody-receipt.json](read-only-custody-receipt.json). |
| passed | `uv run python docs/design_review/evidence/2026-11-06_wce-gs120/artifact-config-abi/build_patch.py` | Exact source replacements; proposed Python AST; patch generation into evidence only. Receipt: [patch-preparation-receipt.json](patch-preparation-receipt.json). |
| passed | `uv run python docs/design_review/evidence/2026-11-06_wce-gs120/artifact-config-abi/validate_preparation.py` | Baseline hashes unchanged, patch hash, Python syntax, stored config typed/canonical roundtrip, `git apply --check` only. Receipt: [validation-receipt.json](validation-receipt.json). |
| not_run | `uv run pytest python/corpus-structure/tests/semantic/test_artifact_identity_native.py python/corpus-structure/tests/semantic/test_artifact_identity_registered_native.py` | Proposed native tests require root's patch application/DB-authoring GO. No SQL/native execution is claimed from AST or dry-run success. |
| not_run | artifact-only rerun on the same frozen corpus | Root-owned after correction and final runtime/source qualification; run181 remains a failed record. |

The Python import path emitted `UserWarning: Can't initialize NVML` during the read-only inspection/validation; these commands invoked no model or provider. An initial metadata-only probe referenced nonexistent `cfg.key` and failed with undefined-column before the corrected read-only inspection; it supplied no custody evidence. The successful full config snapshot is retained separately as [registered181-params.json](registered181-params.json).

There is no accepted result body for task1067. This preparation neither captures nor claims the full rejected completion payload, its cohort/pair counts, or a successful artifact execution. It settles the observed representation mismatch and prepares regression coverage. It establishes no complete qualification, corpus-wide benefit, model calibration, scientific truth or additional publication permission.
