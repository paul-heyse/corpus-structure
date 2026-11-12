"""Verified native loaders and observed runtime/artifact identity for the shared host."""

from __future__ import annotations

import importlib
import json
import os
import platform
import re
import runpy
import sys
from collections.abc import Callable
from hashlib import file_digest, sha256
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Any, BinaryIO

ArtifactTable = dict[str, Any]
Payload = dict[str, Any]
Inference = Callable[[Payload], Payload]

_ARTIFACT_GROUPS = {
    "d1": ("d1",),
    "dipo": ("dipo", "ettin"),
    "hanlp": ("hanlp", "modernbert"),
    "maverick": ("maverick", "deberta"),
}
_RUNTIME_PACKAGES = {
    "gliner": {"gliner2": "2.1.0", "torch": "2.15.0", "transformers": "5.22.1"},
    "spacy": {"spacy": "3.8.18", "cupy-cuda13x": "14.2.0"},
    "d1": {
        "torch": "2.15.0",
        "transformers": "5.22.1",
        "torchvision": "0.29.2",
        "pillow": "13.0.0",
    },
    "dipo": {"dipo": "0.2.1", "torch": "2.15.0", "transformers": "5.22.1"},
    "hanlp": {"hanlp": "2.1.7", "torch": "2.15.0", "transformers": "5.22.1"},
    "maverick": {"maverick-coref": "1.0.7", "torch": "2.15.0", "transformers": "5.22.1"},
}


def _verify_assets(root: Path, provider: str) -> ArtifactTable:
    table = json.loads(Path(__file__).with_name("pm2_artifacts.json").read_bytes())
    selected = {}
    for group in _ARTIFACT_GROUPS[provider]:
        manifest = table.get(group)
        if not manifest:
            raise ValueError(f"no reviewed artifact manifest for {group}")
        directory = root / group
        snapshot = None
        if group in {"modernbert", "deberta", "ettin"}:
            repository = root / "hub" / ("models--" + manifest["id"].replace("/", "--"))
            revision = manifest["revision"]
            if (repository / "refs" / "main").read_text().strip() != revision:
                raise ValueError(f"offline backbone reference differs for {group}")
            snapshot = repository / "snapshots" / revision
        for name, identity in manifest["files"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != identity["size"]:
                raise ValueError(f"missing or wrong-sized artifact {group}/{name}")
            if snapshot is not None and (snapshot / name).resolve() != path.resolve():
                raise ValueError(f"offline backbone file differs for {group}/{name}")
            with path.open("rb") as stream:
                if file_digest(stream, "sha256").hexdigest() != identity["sha256"]:
                    raise ValueError(f"artifact digest differs for {group}/{name}")
        selected[group] = manifest
    return selected


def _load_d1(assets: Path, device: str) -> tuple[Payload, Inference]:
    if device != "cuda":
        raise ValueError("d1 execution requires CUDA; CPU execution is not selected")
    import torch
    from transformers import AutoModel

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("d1 CUDA profile requires CUDA and BF16 support")
    dtype = torch.bfloat16
    model = AutoModel.from_pretrained(
        str(assets / "d1"),
        trust_remote_code=True,
        local_files_only=True,
        dtype=dtype,
    ).to(device)
    parameter = next(model.parameters())
    if parameter.device.type != "cuda" or parameter.dtype != torch.bfloat16:
        raise RuntimeError("d1 loaded device or dtype differs from CUDA bfloat16")
    engine = model.engine
    module = type(engine).__module__.rpartition(".")[0]
    prompt = importlib.import_module(f"{module}.prompt")
    json_spans = importlib.import_module(f"{module}.json_spans")
    if engine.attention != "set" or engine.set_size != 16:
        raise RuntimeError("unexpected d1 attention or independent-question group size")

    def prepare(request: Payload) -> tuple[tuple, str, list[int]] | Payload:
        state, questions = request.get("state"), request.get("questions")
        if not isinstance(state, (str, dict)) or not isinstance(questions, dict) or not questions:
            raise ValueError("d1 text requests require a source state and named questions")
        if len(questions) > 16:
            return {"outcome": "limited", "reason": "question_count", "limit": 16}
        if any(
            not isinstance(question, dict)
            or question.get("type") not in {"text", "number", "date", "choice", "noul"}
            or not isinstance(question.get("instructions"), str)
            or "range" in question
            for question in questions.values()
        ):
            raise ValueError("this d1 profile admits bounded reads and text decisions")
        named = engine.named(questions)
        rendered = prompt.state_text(state, engine.state_style)
        sequences = engine._sequences([(state, list(named.values()), ())], set_size=16)
        lengths = [len(row[2]) for row in sequences]
        if max(lengths) > 4096:
            return {
                "outcome": "limited",
                "reason": "packed_row_tokens",
                "limit": 4096,
                "row_tokens": lengths,
            }
        return (state, questions), rendered, lengths

    def infer(request: Payload) -> Payload:
        batched = "batch" in request
        requests = request["batch"] if batched else [request]
        if not isinstance(requests, list) or not 1 <= len(requests) <= 16:
            raise ValueError("d1 batches require one to sixteen independent requests")
        prepared = [prepare(item) for item in requests]
        # The pinned runner repacks by row length and scatters back by request ordinal.
        ready = [item[0] for item in prepared if isinstance(item, tuple)]
        native = iter(model.system_one_batch(ready, set_size=16) if ready else ())
        outputs = []
        for item in prepared:
            if isinstance(item, dict):
                outputs.append(item)
                continue
            (state, questions), rendered, lengths = item
            result = next(native)
            if result["usage"]["input_tokens"] != sum(lengths):
                raise RuntimeError("d1 packed preflight and native inference differ")
            answers = result["answers"]
            if tuple(answers) != tuple(questions):
                raise RuntimeError("d1 returned a different question population")
            outputs.append(
                {
                    "outcome": "succeeded"
                    if any(
                        answer.get("span") is not None or answer["type"] in {"choice", "noul"}
                        for answer in answers.values()
                    )
                    else "empty",
                    "rendered_state": rendered,
                    "state_fields": json_spans.string_paths(rendered)
                    if isinstance(state, dict)
                    else [],
                    "row_tokens": lengths,
                    "native": result,
                }
            )
        if next(native, None) is not None:
            raise RuntimeError("d1 returned a different request population")
        return {"batch": outputs} if batched else outputs[0]

    parameter = next(model.parameters())
    return {
        "dtype": str(parameter.dtype),
        "device": str(parameter.device),
        "attention": engine.attention,
        "attention_implementation": model.config._attn_implementation,
        "set_size": engine.set_size,
        "token_budget": engine.token_budget,
        "state_style": engine.state_style,
    }, infer


def _runtime_identity(provider: str, *, project: Path | None = None) -> Payload:
    """Identify this isolated interpreter without importing any model packages."""
    python = platform.python_version()
    expected_python = "3.14.10"
    if python != expected_python:
        raise ValueError(f"{provider} requires CPython {expected_python}, got {python}")
    packages = {name: version(name) for name in _RUNTIME_PACKAGES[provider]}
    if packages != _RUNTIME_PACKAGES[provider]:
        raise ValueError(f"{provider} package identity differs: {packages}")
    inventory = {}
    for installed in distributions():
        name = re.sub(r"[-_.]+", "-", installed.metadata["Name"]).lower()
        if name in inventory:
            raise ValueError(f"duplicate installed PM2 distribution {name}")
        record = installed.read_text("RECORD")
        if not record:
            raise ValueError(f"missing installed PM2 distribution record for {name}")
        inventory[name] = (installed.version, sha256(record.encode()).hexdigest())
    root = Path(__file__).resolve().parents[5]
    project = root if project is None else project
    with (project / "uv.lock").open("rb") as lock, Path(sys.executable).open("rb") as binary:
        return {
            "version": "pm2-runtime-1",
            "python": python,
            "platform": [sys.platform, platform.machine(), sys.implementation.cache_tag],
            "python_sha256": file_digest(binary, "sha256").hexdigest(),
            "lock_sha256": file_digest(lock, "sha256").hexdigest(),
            "distributions_sha256": sha256(
                json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
