# Nemotron isolated runtime

This is a separate Python 3.12 project. The root application keeps its full Docling
environment. `uv.lock` binds the vendor Python3.12/vLLM0.26/Torch2.11/Transformers5.14.1
tuple and its transitive dependencies. The public package version is3.5.0.post7; that
version was unavailable from PyPI on2026-10-31, so the source comes from the immutable
NVIDIA Hub export4035ffb1d8f8bafcdb867dfaf6f7514f101464f9. The ignored `vendor` link points
at the existing model cache; the installed package is a wheel, not an editable checkout.

From the repository root:

```sh
uv run --no-project --python 3.12 --with huggingface-hub==1.24.0 python services/nemotron-parse/bootstrap.py
uv sync --project services/nemotron-parse --python 3.12
uv pip check --python services/nemotron-parse/.venv/bin/python
```

The independent bootstrap verifies the weight and tokenizer digests. Keep the cached
export after removing a checkout. Do not copy weights or environments into evidence.

The validated2026-10-31 RTX5090/driver615.71.10 launch uses:

```sh
services/nemotron-parse/.venv/bin/python services/nemotron-parse/launch.py \
  --receipts build/recognition-generations
```

The controlled launcher verifies the selected weights/tokenizer before startup, records a
complete export manifest and launch arguments, and embeds a fresh immutable generation in
that server process. The application admits `/corpus/generation` before reuse/inference and
every parser request supplies `x-corpus-generation`; the service refuses a mismatched generation
with409 and binds every response to its executing generation. In-flight responses during graceful
shutdown retain the old generation; restart requires a new admission. This is trusted local
startup custody, not cryptographic proof of GPU contents. Treat the export as immutable under
its operator owner. Never replace bytes in a live export; replacement requires a separately
verified startup generation. `recognition_assurance: provider_reported` explicitly selects an
unmanaged endpoint; its configured digests and reported alias never establish verified custody.

The plugin enables trained one-token MTP. On this Blackwell GPU vLLM rejectsFA3 and
selects effective FlashAttention2; the application recipe records that effective choice.
This is the local validated configuration, not the vendor H100 throughput profile.
The fresh combined producer uses this dedicated endpoint's level-one sleep/wake API.
It offloads Nemotron weights and releases KV memory before Standard Docling runs on
CUDA, closes the native child after its last consumer, then restores Nemotron for triple
recognition. The GPU is restored on native failure and cancellation. Missing control
capability is an actionable failure; the producer never substitutes a CPU or single-pass
route. The archived source recipe names this phase policy. Retained Standard and retained
integrated products reuse their existing content without another Standard conversion.

`worker.py` accepts one input JSON file and exits after a complete public
`DocumentParser.parse_triple(..., triple_regions="union")` call. It has no database.
Its narrow recording backend preserves actual submittedPNG bytes, fullHTTP bodies and
unmodified raw coordinate/class tokens before upstream parsing can reject a result.
Scoped observers retain upstream union/crop decisions and JPEG95 crop roundtrips without
reimplementing the scheduler. A failed crop leaves earlier response files intact.
The application controller owns cancellation, process-group teardown, page release and
recipe-qualified disk replay. Operational settings use `CORPUS_NEMOTRON__*`; generic
`CORPUS_LLM__ENDPOINT` remains a separate service.

The main evidence owner is
`docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/runtime/`: actual startup,
model manifest, effective recipe and book page85/596/614 A/B/C receipts. The coordinator
owns full-book completion and assembled acceptance.
