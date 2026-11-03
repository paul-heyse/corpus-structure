# Thin native GLiNER CPU worker operation

**Tested, 2026-11-03, scoped:** the thin detached worker executes native combined extraction
on the retained 439-byte development paragraph, keeps the same model resident for the warm
call, returns per-context reports and joins its child. This is a prerequisite for M1-06/07,
not their completion. The [coordinator](../../../plans/first-production-milestone_2026-11-03.md)
owns assembled integration and qualification.

## Scope and identity

The implementation is [gliner.py](../../../../python/corpus-structure/src/corpus_structure/methods/gliner.py)
and [gliner_worker.py](../../../../python/corpus-structure/src/corpus_structure/methods/gliner_worker.py).
It uses strict native `Schema.from_dict`, explicit natural anchors, ordered declarations, native
`processor.transform_record` preflight and `batch_extract`. There is no custom decoder, replica
preprocessor, generic hidden-state cache or automatic retry. Preflight and public extraction each
invoke native preparation; the second pass is native collation inside the public API.

The declaration is the earlier retained combined probe's declaration with the obvious
`PROBE-ONLY-NOT-A-RELEASE` identity. No released GLiNER pack existed at this boundary. Input is the
exact clipped paragraph from `2026-11-03_m1-population/cpu-source-paragraph.json`; its native pin,
source offset, input and artifact hashes are retained. Its detached context digest identifies the
paragraph artifact, **not** `NativeSourceContext.dependency_digest`. This run does not establish
actual retained-context mapping or record quality. An independent fixture check exercises the
real context owner's literal mapping and synthetic-crossing refusal.

`attempt-00005.json` binds the corrected final implementation file hashes, exact five model artifacts at
revision `54785d51df8d86a0d8f2eb212fec15871aad2c4d`, declaration, profile and each native payload.
The effective model configuration, boundary settings, Python/package versions, CPU FP32,
whitespace splitter and standard attention are retained in each report. Torch intra-op4 and
inter-op1 are explicit. Pool/suppression/count/abstention/feasibility diagnostics are
**unavailable** on the selected public combined surface, never inferred as zero or false.

Reports fingerprint effective profile, schema/release, source context/text, threshold, overlap
policy and exact ordered batch inputs. This binds a computation; it promises no encoding reuse.
Logical profile identity excludes acquisition location and canonicalizes artifact-name/hash order.
The complete effective configuration and `snapshot` location remain report provenance; only the
known `config._name_or_path` loader locator and top-level `snapshot` are excluded from effective
computation identity. Model semantic settings, versions, precision and splitter remain bound.
Snapshot admission permits exactly the five declared files and their required directory, and
refuses every extra entry, including optional tokenizer inputs and cache metadata. Both field
mapping and strict schema admission refuse ambiguous duplicate field names; record-field mapping
first requires the report's exact pack fingerprint before interpreting field kind.

Batch work is serial and has one schema/profile. Admission permits one bounded live batch and
zero queued batches; saturation fails immediately for caller-owned backpressure. There is no
aggregate spaCy/Torch/DuckDB resource admission or released CPU policy here.

Input text and schema payload bounds are separate from explicit detached-metadata and complete
wire-frame bounds. `max_metadata_bytes` covers IDs/release/version metadata; profile metadata is
bounded too. `max_request_frame_bytes` and `max_reply_frame_bytes` cap the entire serialized
finite request/reply, including preparation, context IDs, effective configuration and envelope.
The parent checks the request before starting a child, and both pipe receivers enforce the
corresponding frame limit. Oversized replies fail and retire the worker. These are finite-frame
checks using the actual multiprocessing serializer, not object-size estimates or raw-payload-only
counts.

The parent retains lease callbacks and database ownership. Only detached text/declaration/profile
requests cross IPC. Native model work stays in the spawned child. Bounded polling supervises an
I/O thread so a blocked send/receive can also be interrupted; timeout, lease loss, cancellation,
crash and invalid replies retire the owner and stop/join the child before propagation. Terminate
failure still attempts kill/join and IPC cleanup; individual teardown causes remain notes.
Successful reports are returned to the existing caller, not persisted by the child. Child cleanup
of inherited DB/provider/evaluator environment variables is defense in depth, not an OS sandbox
or demonstrated credential-isolation guarantee. Offline settings are applied before native loading.

## Observed operation

Corrected final source attempt00005: **passed**. Cold wall 3.949s (native call 0.206s); warm wall
0.148s (native call 0.146s), identical resident PID and computation identity. Native preflight observed
77 word tokens and 149 schema-conditioned input IDs. The child joined cleanly.

Parent peak RSS was 774740 KiB; child peak RSS was 2432904 KiB. Parent strict schema admission
imports the native package/Torch, accounting for a material parent footprint. These are the two
processes' individual peak RSS values, not simultaneous aggregate measurements or a supported
resource envelope. Calling the stdlib-only module itself does not import GLiNER/Torch; native
admission is explicitly selected through `compile`/`from_declaration` or child execution.

The model-type warnings in `attempt-00005.log` remain visible. Actual selected combined operation
compatibility is established for this input; those warnings have not been promoted to full-profile
qualification. Attempts00001–00004 remain retained successful development runs with their earlier
source identities. The earlier actual-operation proof remains valid for its exact five-file
snapshot and input; the corrected source adds the review-required guards and identity semantics. The current helper refuses overwriting numbered attempt outputs.

Commands (run from MAIN so its pinned uv environment is used):

```bash
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-gliner/python/corpus-structure/src uv run python /home/paul/.cache/corpus-structure-m1-gliner/docs/design_review/evidence/2026-11-03_m1-gliner-runtime/check_runtime.py --attempt 5
PYTHONPATH=/home/paul/.cache/corpus-structure-m1-gliner/python/corpus-structure/src:/home/paul/.cache/corpus-structure-m1-gliner/python/corpus-structure/tests uv run pytest /home/paul/.cache/corpus-structure-m1-gliner/python/corpus-structure/tests/methods/test_gliner.py
```

Focused tests **passed**, 31 checks in `pytest-review-fixes.log`: strict schema/order, native Unicode
splitter coordinates, distinct preprocessing limits and synthetic delta, actual source-context
mapping, classified choice refusal, artifact/profile identity, controlled empty versus failed
output, stale response, crash, timeout, cancellation before/during work, saturation and teardown
escalation. Added independent negatives cover foreign-pack reinterpretation, both duplicate
field orders, optional tokenizer inputs, unexpected cache metadata, actual copied fixture files
with a permuted hash manifest, controlled effective-config locator equivalence, meaningful
configuration invalidation, oversized detached metadata and complete IPC frame limits. Controlled
children are lifecycle evidence only, never provider evidence.
Scoped Ruff **passed** (`ruff-review-fixes.log`). Scoped Pyrefly **passed**, 0 errors
(`pyrefly-review-fixes.log`), with explicit MAIN config/site-packages and isolated source/test search
paths. Initial isolated-config Pyrefly emitted a missing-venv warning; that run was replaced by
the correctly configured check. Interim E501 formatting and incompatible test-double typing
diagnostics were repaired; the actual context owner now supplies that mapping test. The first
full-frame test run exposed serializer memoryview cleanup warnings; conversion to an owned byte
frame removed the retained export, and the final 31-check run has no warnings. Earlier finalized
validation logs remain unchanged. Review follow-up typing of authored JSON declarations was
corrected before the final diagnostic pass.

Released family quality, real-context provider mapping, Classifier/JointIE wrappers, full-session
secret isolation, CPU policy/registry/observation persistence, aggregate admission, all-family
resource fit and assembled qualification: **not_run**. No dependency installation, downloads,
database writes, general LLM/GPU service, staging, commits or turn-end maintenance occurred here.

## Integrated retained-source mapping journey

**Bounded Tested, 2026-11-03.** Root integrated the corrected files. Independent implementation
review accepts this private combined/serial slice with no unresolved material finding after
repairing duplicate field names, report/pack mismatch, tokenizer-file closure, operational-path
identity and full finite IPC byte accounting. Root's68 runtime/context tests and scoped Ruff/
Pyrefly pass on the integrated tree. The preceding records retain their own source scope.

`check_mapped_runtime.py --attempt 1` uses the explicitly selected source database and a transaction
with `transaction_read_only=on`. Actual view5 still matches the frozen development pin; the old
native99 source reader remains usable. The connection closes before a detached mapped input reaches
the spawned child. Both cold and warm calls map six literal fields into the actual native source
pieces, refuse three classified fields as literal evidence, retain one child PID and join it.
The mapped context and raw payloads/coordinates are retained in numbered artifacts.

This uses `PROBE-ONLY-NOT-A-RELEASE`. Native labels such as `definition` are candidate output,
not correctness judgments. No source task, evaluator reference, accepted record, database/default
selection or live migration is written. Full producer registration/coverage/assembly/publication,
credential-isolation journey and aggregate operating envelope remain open.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 1 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Reviewed finite-frame GLiNER CPU worker cold and warm operation](records/m1.cpu-resident-worker-reviewed-operation.json) | M1-06/M1-07 | passed | — | 2026-11-03 |
| [Actual retained source-context CPU literal mapping](records/m1.cpu-mapped-source-operation.json) | M1-07 | passed | — | 2026-11-03 |

**Superseded**

| Record | Superseded by | Finalized |
|---|---|---|
| [Detached offline GLiNER CPU worker cold and warm operation](records/m1.cpu-resident-worker-operation.json) | m1.cpu-resident-worker-reviewed-operation | 2026-11-03 |
<!-- evidence-index:end -->
