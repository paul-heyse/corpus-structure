"""Compare one-at-a-time and two queued Chandra requests in the local vLLM runtime."""

import argparse
import json
import os
import subprocess
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from time import monotonic


def _probe(model: Path, work: Path):
    from PIL import Image
    from transformers import AutoProcessor
    from vllm import LLM, SamplingParams

    recipe = json.loads((work / "transformers.json").read_bytes())["recipe"]
    decode = recipe["decode"]
    processor = AutoProcessor.from_pretrained(model, local_files_only=True)
    prompt = processor.apply_chat_template(
        [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": recipe["prompt"]}]}],
        tokenize=False,
        add_generation_prompt=True,
    )
    images = [Image.open(work / f"page-{index}.png").convert("RGB") for index in range(2)]
    requests = [{"prompt": prompt, "multi_modal_data": {"image": image}} for image in images]
    options = {
        "dtype": "bfloat16",
        "max_model_len": 18432,
        "gpu_memory_utilization": 0.7,
        "max_num_seqs": 2,
        "limit_mm_per_prompt": {"image": 1, "video": 0},
        "enforce_eager": True,
        "enable_prefix_caching": False,
        "generation_config": "vllm",
    }
    started = monotonic()
    engine = LLM(model=str(model), **options)
    load_seconds = monotonic() - started
    settings = SamplingParams(
        temperature=decode["temperature"],
        max_tokens=decode["max_new_tokens"],
        stop=decode["stop_strings"],
    )

    def measure(mode, outputs, started):
        elapsed = round(monotonic() - started, 3)
        rows = []
        for index, result in enumerate(outputs):
            answer, = result.outputs
            raw = answer.text.encode()
            (work / f"{mode}-{index}.html").write_bytes(raw)
            rows.append(
                {
                    "raster_sha256": sha256((work / f"page-{index}.png").read_bytes()).hexdigest(),
                    "text_sha256": sha256(raw).hexdigest(),
                    "finish_reason": answer.finish_reason,
                    "stop_reason": answer.stop_reason,
                    "prompt_tokens": len(result.prompt_token_ids or ()),
                    "generated_tokens": len(answer.token_ids),
                }
            )
        if len(rows) != len(requests):
            raise ValueError("vLLM result count differs from the requested frame count")
        return {"seconds": elapsed, "outputs": rows}

    started = monotonic()
    serial = [engine.generate([request], settings, use_tqdm=False)[0] for request in requests]
    serial_result = measure("serial", serial, started)
    started = monotonic()
    queued = engine.generate(requests, settings, use_tqdm=False)
    report = {
        "versions": {name: version(name) for name in ("vllm", "torch", "transformers")},
        "model_revision": recipe["revision"],
        "options": options,
        "load_seconds": round(load_seconds, 3),
        "serial": serial_result,
        "queued": measure("queued", queued, started),
    }
    (work / "vllm.json").write_text(json.dumps(report, indent=2) + "\n")


def _control(args):
    from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron
    from corpus_structure.ingest.pdf_chandra import _verify_artifacts
    from corpus_structure.semantic.pdf_visual_mapping import render_visual_input
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_requests import _load_visual_source
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
    from corpus_structure.settings import Settings

    control = json.loads(args.reference.read_bytes())
    source = VisualEvidencePin.model_validate(control["source"])
    settings = Settings()
    with open_runtime_engine(settings, "chandra-vllm-control", purpose="read") as engine:
        with engine.connect() as conn:
            _, _, original, _ = _load_visual_source(conn, source)
    args.output.mkdir()
    (args.output / "transformers.json").write_bytes(args.reference.read_bytes())
    for index, (page, expected) in enumerate(
        zip(control["pages"], control["raster_sha256"], strict=True)
    ):
        png, _ = render_visual_input(original, page, None)
        if sha256(png).hexdigest() != expected:
            raise ValueError("vLLM comparison raster differs from its serial control")
        (args.output / f"page-{index}.png").write_bytes(png)
    model = _verify_artifacts(args.artifacts)
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with suspend_resident_nemotron(settings.nemotron.endpoint):
        subprocess.run(
            [str(args.python), __file__, "probe", str(model), str(args.output)],
            env=env,
            check=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    control = actions.add_parser("control")
    control.add_argument("reference", type=Path)
    control.add_argument("artifacts", type=Path)
    control.add_argument("python", type=Path)
    control.add_argument("output", type=Path)
    probe = actions.add_parser("probe")
    probe.add_argument("model", type=Path)
    probe.add_argument("work", type=Path)
    args = parser.parse_args()
    if args.action == "probe":
        _probe(args.model, args.work)
    else:
        _control(args)
