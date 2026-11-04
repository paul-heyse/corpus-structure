"""Three authorized core-only natural-schema calls on frozen development inputs."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import time

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker

from run_probe import asdict_usage, cpu

HERE = Path(__file__).parent


def main():
    frozen_bytes = (HERE / "frozen-inputs.json").read_bytes()
    frozen = json.loads(frozen_bytes)
    profile_data = frozen["profile"]
    profile_data["snapshot"] = Path(profile_data["snapshot"])
    profile_data["artifact_hashes"] = tuple(tuple(entry) for entry in profile_data["artifact_hashes"])
    profile = GlinerProfile(**profile_data)
    out = HERE / "attempt-core-only001"
    out.mkdir(exist_ok=False)
    requests = []
    for context in frozen["contexts"]:
        baseline = context["variants"][0]
        assert baseline["name"] == "baseline_actual_pack"
        schema = json.loads(json.dumps(baseline["schema"]))
        removed = []
        for structure in schema["structures"].values():
            removed.extend(field["name"] for field in structure["fields"]
                           if field["name"].endswith(("__state", "__cue")))
            structure["fields"] = [field for field in structure["fields"]
                                   if not field["name"].endswith(("__state", "__cue"))]
        pack = GlinerPack.from_declaration(frozen["release_id"], schema)
        requests.append(dict(context_index=context["context_index"], family=context["family"],
                             schema=schema, schema_sha256=hashlib.sha256(pack.declaration_json.encode()).hexdigest(),
                             pack_fingerprint=pack.fingerprint, baseline_pack_fingerprint=baseline["pack_fingerprint"],
                             removed_fields=removed, context_id=context["context_id"],
                             context_digest=context["context_digest"], text_sha256=context["text_sha256"]))
    request = dict(frozen_input_sha256=hashlib.sha256(frozen_bytes).hexdigest(),
                   authorized_followup="exactly three calls, same frozen contexts and baseline schemas; remove only __state/__cue fields; threshold 0.5",
                   threshold=0.5, requests=requests, frozen_at=datetime.now(timezone.utc).isoformat(),
                   quality_claim="not established; source-inspection/admission obligations not waived")
    (out / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    worker = GlinerWorker(profile)
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), calls=[], outcome="running",
                   request_sha256=hashlib.sha256((out / "request.json").read_bytes()).hexdigest(),
                   frozen_input_sha256=request["frozen_input_sha256"], threshold=0.5)
    started = time.perf_counter()
    with (out / "results.jsonl").open("x") as stream:
        try:
            for context, selected in zip(frozen["contexts"], requests, strict=True):
                item = GlinerInput(context["context_id"], context["context_digest"], context["text"])
                pack = GlinerPack.from_declaration(frozen["release_id"], selected["schema"])
                assert pack.fingerprint == selected["pack_fingerprint"]
                before_cpu, before_wall = cpu(worker.pid), time.perf_counter()
                (report,) = worker.extract(pack, (item,), threshold=0.5)
                row = dict(context_index=context["context_index"], family=context["family"], threshold=0.5,
                           variant="baseline_core_only", outcome="passed", report=asdict(report),
                           wall_seconds=time.perf_counter() - before_wall,
                           child_cpu_seconds=cpu(worker.pid) - before_cpu, child_pid=worker.pid)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                receipt["calls"].append({key: row[key] for key in ("context_index", "outcome", "wall_seconds", "child_cpu_seconds")})
                print(json.dumps(receipt["calls"][-1]), flush=True)
            receipt["outcome"] = "passed"
        except BaseException as exc:
            receipt.update(outcome="failed", error=repr(exc))
            raise
        finally:
            pid = worker.pid
            worker.close()
            receipt.update(wall_seconds=time.perf_counter() - started, child_pid=pid,
                           process_joined=worker.closed and (pid is None or not Path(f"/proc/{pid}").exists()),
                           finished_at=datetime.now(timezone.utc).isoformat(),
                           child_usage=asdict_usage(resource.getrusage(resource.RUSAGE_CHILDREN)))
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
