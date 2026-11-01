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
services/nemotron-parse/.venv/bin/vllm serve services/nemotron-parse/vendor \
  --served-model-name nemotron-parse --trust-remote-code --dtype bfloat16 \
  --distributed-executor-backend uni --tensor-parallel-size 1 --data-parallel-size 1 \
  --max-model-len 16384 --max-num-seqs 4 --max-num-batched-tokens 16384 \
  --no-enable-prefix-caching --limit-mm-per-prompt '{"image":1}' \
  --attention-config '{"flash_attn_version":3}' \
  --chat-template services/nemotron-parse/vendor/chat_template.jinja \
  --host 127.0.0.1 --port 8035 --gpu-memory-utilization 0.72
```

The plugin enables trained one-token MTP. On this Blackwell GPU vLLM rejectsFA3 and
selects effective FlashAttention2; the application recipe records that effective choice.
This is the local validated configuration, not the vendor H100 throughput profile.
The parent operation phases GPU ownership with native Docling and other model services.

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
