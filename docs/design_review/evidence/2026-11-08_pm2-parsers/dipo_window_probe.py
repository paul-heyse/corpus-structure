"""Exercise the pinned native DMRST encoder beyond the ordinary stage cap, on CPU."""
import json
import os
import runpy
from importlib.metadata import version
from pathlib import Path
from time import monotonic

assets = Path("build/models/pm2").resolve()
entry = Path("python/corpus-structure/src/corpus_structure/methods/pm2_native.py")
runpy.run_path(str(entry))["_verify_assets"](assets, "dipo")
os.environ.update(
    HF_HUB_CACHE=str(assets / "hub"),
    HF_HUB_OFFLINE="1",
    TRANSFORMERS_OFFLINE="1",
    CUDA_VISIBLE_DEVICES="",
)
import torch
from dipo.rst.parsers.common.encoding import encode_with_offsets
from dipo.rst.parsers.dmrst.modeling_dmrst import DMRSTParser

torch.set_num_threads(8)
torch.set_num_interop_threads(2)
model = DMRSTParser.from_pretrained(
    str(assets / "dipo"), device="cpu", compile_encoder=False, token=False
)
model.eval()
print(json.dumps({
    "dipo": version("dipo"),
    "torch": version("torch"),
    "transformers": version("transformers"),
    "tokenizer_limit": model.tokenizer.model_max_length,
    "encoder_config_positions": model.encoder.config.max_position_embeddings,
    "native_window_limit": model.max_length,
    "stride": model.stride,
    "device": str(next(model.parameters()).device),
}), flush=True)
windows = []
def capture(_encoder, _args, kwargs):
    windows.append({
        "padded_shape": list(kwargs["input_ids"].shape),
        "attended_lengths": kwargs["attention_mask"].sum(dim=1).tolist(),
    })

hook = model.encoder.register_forward_pre_hook(capture, with_kwargs=True)
try:
    for expected in (7997, 7998, 8190, 8191):
        ids, offsets = encode_with_offsets(
            model.tokenizer, " ".join(["token"] * expected), split_cjk=model.config.split_cjk_tokens
        )
        if len(ids) != expected or len(offsets) != expected:
            raise ValueError(f"probe tokenization differs from target: {len(ids)} vs {expected}")
        windows.clear()
        start = monotonic()
        print(json.dumps({"starting_content_tokens": expected}), flush=True)
        try:
            with torch.inference_mode():
                encoded = model._encode_tokens(torch.tensor(ids, dtype=torch.long))
            if encoded.shape[0] != expected or not encoded.isfinite().all():
                raise ValueError("unexpected output length or non-finite encoding")
            outcome = {"outcome": "passed", "encoded_tokens": encoded.shape[0]}
        except (RuntimeError, ValueError, IndexError) as error:
            outcome = {"outcome": "failed", "error": str(error)}
        print(json.dumps({
            "content_tokens": expected, "windows": windows,
            "elapsed_seconds": round(monotonic() - start, 3), **outcome,
        }), flush=True)
finally:
    hook.remove()
