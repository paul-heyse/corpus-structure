"""Launch the dedicated verified export; every process lifetime gets an immutable generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from bootstrap import PINS
from custody import generation_record, verify_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, default=Path(__file__).parent / "vendor")
    parser.add_argument("--runtime", type=Path, default=Path(__file__).parent / ".venv/bin/vllm")
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8035)
    args = parser.parse_args()
    root = args.export.resolve(strict=True)
    manifest = verify_export(root, PINS)
    command = [str(args.runtime.resolve()), "serve", str(root),
               "--served-model-name", "nemotron-parse", "--trust-remote-code", "--dtype", "bfloat16",
               "--distributed-executor-backend", "uni", "--tensor-parallel-size", "1",
               "--data-parallel-size", "1", "--max-model-len", "16384", "--max-num-seqs", "4",
               "--max-num-batched-tokens", "16384", "--no-enable-prefix-caching",
               "--limit-mm-per-prompt", '{"image":1}',
               "--attention-config", '{"flash_attn_version":3}',
               "--chat-template", str(root / "chat_template.jinja"),
               "--host", "127.0.0.1", "--port", str(args.port),
               "--gpu-memory-utilization", "0.72", "--enable-sleep-mode",
               "--middleware", "custody.GenerationMiddleware"]
    record = generation_record(root, manifest, command)
    args.receipts.mkdir(parents=True, exist_ok=True)
    receipt = args.receipts / (record["generation"] + ".json")
    with receipt.open("x") as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    environment = dict(os.environ)
    environment["VLLM_SERVER_DEV_MODE"] = "1"
    environment["CORPUS_RECOGNITION_GENERATION"] = json.dumps(record)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    os.execve(command[0], command, environment)


if __name__ == "__main__":
    main()
