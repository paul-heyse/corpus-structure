# Repaired book shadow execution

**Tested and Measured · 2026-11-08.** The source is run 377, task 1627,
cut 492 and the exact integrated product `35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`.
The writer is release `release:1266ff1bc135e28bca2466e2e5e5f273438536d4c56d06c0a8eeec494662d269`
and realization `source:chandra-comparator-projected-book`. The 29 ordinary
views in run 378 are a separate read control. [Comparator custody](incumbent-recovery.md#optimized-comparator--2026-11-08)

## Freeze and execution

The exact [compressed manifest](raw/book-shadow-377/manifest.json.gz) fixes
all 518 physical-page routes, the original digest, producer and writer pins,
the Transformers BF16 runtime, parser and render recipes, and the independent
review strata. It records 92 recognition nominations, 13 incumbent repair
nominations and 413 skips. The four arms share 535 distinct selections.
The explicit arm has eight scopes, the selective arm has 94 and the all-page
arm has 518 whole pages. Seventeen additional crops account for the
difference between the work union and the physical book. The 15-page,
10-group mixed cohort is exact retained evidence with separately pinned
incumbent sources. [Mixed cohort assessment](mixed-cohort/assessment.md)

The retired campaign stored the group key before inference and released
shared GPU capacity between groups of at most four requests. Its frozen
manifest and settled results remain available for comparison. New Chandra
requests require operator-supplied scopes.

```sh
ev=docs/design_review/evidence/2026-11-08_chandra-execution
book=build/chandra-execution/book-shadow-377
uv run python "$ev/group_shadow_compare.py" "$book/groups" > "$book/comparison.jsonl"
```

The comparer checks ordered group scope, protected pins, original and
runtime/parse recipes. It reports coverage and candidate differences by
arm. It marks source adjudication independently from delivery. Running
without `--require-complete` reports progress and unassessed scopes.
The p151 crop and whole page count as distinct scopes. The rotated p509
control uses a separate recipe from the ordinary selective crop.
[Source controls and adjudication](repaired-comparator-witnesses.md) ·
[Frozen held-out source witnesses](book-shadow-held-out.md)

## Runtime comparison

The local RTX 5090 passed a real Torch CUDA operation. Its running kernel
uses NVIDIA 615.71.10. The default NVML library reports version 620.70. The
process-local 615 library directory used by the existing Nemotron service
also enabled standalone vLLM CUDA detection. Torch's reference CUDA path
worked under the default environment.

Docling 2.148.0 `VlmConvertModel.process_images` received the same rendered
p506 and p151 PNGs for both calls. With one loaded model, serial decode took
31.038 s and the two-image call took 24.811 s. Both calls returned two
parseable outputs with unspecified stops. Both raw hashes changed under
batching. This probe establishes the timing and parse boundary. It did not
establish sufficient independent output parity for adopting batching.
The loaded model took 2.656 s to initialize in that run.
[Transformers control](raw/book-shadow-377/transformers-batch.json) ·
[Pinned Docling VLM stage](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/vlm_convert/vlm_convert_model.py)

The local vLLM 0.26.0 eager control used `LLM.generate` with one image per
request, the same source PNG hashes and checkpoint revision, BF16, and
one then two outstanding requests. Startup took 125.009 s. The cold
one-at-a-time calls took 112.851 s with first-use kernel compilation. The
later two-request call took 18.737 s. Both returned provider `stop`,
preserved the two page-header readings on p506 and the four witnessed
Table 4.2 fractions on p151. The raw hashes differed across scheduling
modes and from the Transformers serial outputs. The cold and warm
numbers measure their stated order and do not establish an isolated
throughput ratio. This standalone recipe does not qualify managed
adoption, repeated handoff, wider fidelity or MTP. Retain the serial
Transformers recipe for the book shadow.
[vLLM control](raw/book-shadow-377/vllm.json) ·
[vLLM 0.26.0 LLM API](https://docs.vllm.ai/en/v0.26.0/api/vllm/entrypoints/llm/) ·
[Chandra launcher](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/scripts/vllm.py)

## Post-publication control

`ci source visual-dispatch` recognized the selective p151 crop against cut
492. Run 379 sealed visual cut 494 and retained raw task 1629 and mapped
task 1630. The bounded CLI manifest returned those pins on consecutive
pages. MCP inspection and the explicit packet agreed at digest
`70651b4eb28303cf392ba768b886cb1b79dc41cb87b94d661f5f2e6f235fb4f4`.
The Reader still returned the exact incumbent table while shadow work
was active. The dry p506 control dispatched zero requests for a verified
blank body. The wrong cut control refused before recognition. The
p151 raw crop contains 140 invented formula wrappers, zero tables and
an unknown stop. Its pixels visibly contain the four correct fractions
and C/S headers. This is a recognition error at a known exact frame,
while the whole-page reading supports the incumbent's table.
[Managed dispatch receipt](raw/book-shadow-377/dispatch-p151.json) ·
[Reader and MCP packet receipt](raw/book-shadow-377/dispatch-mcp.json) ·
[Source witness](repaired-comparator-witnesses.md)

## Same-run recovery

Run 380 sealed cut 495 for the first four scopes. During run 381 the CLI
implementation changed in the working tree. The native runtime check
refused the next mapping claim after the p416 raw result settled. An
isolated package copy restored the two exact CLI/dispatch files from
run 381's archived executable. With that copy on `PYTHONPATH`,
`uv run --no-sync ci run resume 381 --project nce-grinstead-snell-full-book --json`
reused task 1639 and sealed cut 496. The campaign then restarted from
the same manifest using an isolated snapshot of the final executable.
It reconstructed both settled groups from protected custody.
