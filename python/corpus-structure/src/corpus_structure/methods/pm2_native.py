"""Offline native PM2 worker entry point. Run with the profile's exact interpreter."""

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

_MAX_MESSAGE = 8_388_608
_ARTIFACT_GROUPS = {
    "d1": ("d1",),
    "dipo": ("dipo", "ettin"),
    "hanlp": ("hanlp", "modernbert"),
    "maverick": ("maverick", "deberta"),
}
_RUNTIME_PACKAGES = {
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


def _runtime_identity(provider: str) -> Payload:
    """Identify this isolated interpreter without importing any model packages."""
    python = platform.python_version()
    expected_python = "3.14.10" if provider in {"d1", "hanlp"} else "3.12.3"
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
    project = root if provider == "d1" else root / f"services/pm2-{provider}"
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


def _preflight(provider: str, assets: Path) -> Payload:
    if provider not in _ARTIFACT_GROUPS:
        raise ValueError("unrecognized PM2 provider")
    return {
        "runtime_identity": _runtime_identity(provider),
        "assets": _verify_assets(assets.resolve(strict=True), provider),
    }


def _load_profile(profile_path: Path) -> tuple[Payload, Inference]:
    profile = json.loads(profile_path.read_bytes())
    provider, device = profile["provider"], profile["device"]
    if device not in {"cpu", "cuda"}:
        raise ValueError("unrecognized PM2 device")
    if provider == "d1" and device != "cuda":
        raise ValueError("d1 execution requires CUDA; CPU execution is not selected")
    assets = Path(profile["assets"]).resolve(strict=True)
    checked = _preflight(provider, assets)
    expected_runtime = profile.get("runtime_identity")
    if expected_runtime is not None and expected_runtime != checked["runtime_identity"]:
        raise ValueError("native PM2 runtime differs from the preflight identity")
    os.environ.update(
        HF_HUB_CACHE=str(assets / "hub"),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    if device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch

    threads, interop = profile.get("threads", 4), profile.get("interop_threads", 1)
    if any(type(value) is not int or value < 1 for value in (threads, interop)):
        raise ValueError("native thread settings must be positive integers")
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(interop)

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA device unavailable")
    if provider == "d1":
        loader = _load_d1
    else:
        file = "pm2_hanlp.py" if provider == "hanlp" else "pm2_dispatched.py"
        loader = runpy.run_path(str(Path(__file__).with_name(file)))[f"load_{provider}"]
    metadata, infer = loader(assets, device)
    return {
        "provider": provider,
        "python": checked["runtime_identity"]["python"],
        "packages": dict(_RUNTIME_PACKAGES[provider]),
        "torch_build": torch.__version__,
        "cuda_build": torch.version.cuda,
        "device_name": torch.cuda.get_device_name() if device == "cuda" else None,
        **checked,
        **metadata,
        "native_threads": {
            "intra_op": torch.get_num_threads(),
            "inter_op": torch.get_num_interop_threads(),
        },
    }, infer


def _send(out: BinaryIO, message: Payload) -> None:
    data = json.dumps(message, ensure_ascii=False, allow_nan=False).encode()
    if len(data) >= _MAX_MESSAGE:
        raise ValueError("native result exceeds the worker message bound")
    out.write(data + b"\n")
    out.flush()


def _serve(profile_path: Path, out: BinaryIO) -> None:
    try:
        metadata, infer = _load_profile(profile_path)
        _send(out, {"kind": "ready", "payload": metadata})
    except Exception as exc:
        _send(out, {"kind": "error", "message": f"{type(exc).__name__}: {exc}"[:4000]})
        return
    while line := sys.stdin.buffer.readline(_MAX_MESSAGE + 1):
        if len(line) > _MAX_MESSAGE or not line.endswith(b"\n"):
            raise ValueError("worker request exceeds the message bound")
        message = json.loads(line)
        request_id = message["request_id"]
        try:
            if message["kind"] != "infer" or not isinstance(message["payload"], dict):
                raise ValueError("invalid native inference request")
            result = infer(message["payload"])
            _send(out, {"kind": "result", "request_id": request_id, "payload": result})
        except Exception as exc:
            _send(
                out,
                {
                    "kind": "error",
                    "request_id": request_id,
                    "message": f"{type(exc).__name__}: {exc}"[:4000],
                },
            )
            return


if __name__ == "__main__":
    # Libraries may write progress directly to fd 1. Keep the wire stream separate.
    with os.fdopen(os.dup(sys.stdout.fileno()), "wb") as protocol:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        if sys.argv[1] == "--preflight":
            try:
                provider, assets = sys.argv[2:]
                _send(protocol, {"kind": "ready", "payload": _preflight(provider, Path(assets))})
            except Exception as exc:
                _send(protocol, {"kind": "error", "message": f"{type(exc).__name__}: {exc}"[:4000]})
        else:
            _serve(Path(sys.argv[1]), protocol)
