"""Three authorized baseline-only recall canaries at threshold 0.15."""
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
    out = HERE / "attempt-low-threshold001"
    out.mkdir(exist_ok=False)
    request = dict(frozen_input_sha256=hashlib.sha256(frozen_bytes).hexdigest(),
                   authorized_followup="exactly three calls, same frozen contexts/baseline schemas, threshold 0.15",
                   threshold=0.15, context_indices=[context["context_index"] for context in frozen["contexts"]],
                   baseline_pack_fingerprints=[context["variants"][0]["pack_fingerprint"] for context in frozen["contexts"]],
                   frozen_at=datetime.now(timezone.utc).isoformat(), quality_claim="not established")
    (out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    worker = GlinerWorker(profile)
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), calls=[], outcome="running", **request)
    started = time.perf_counter()
    with (out / "results.jsonl").open("x") as stream:
        try:
            for context in frozen["contexts"]:
                item = GlinerInput(context["context_id"], context["context_digest"], context["text"])
                variant = context["variants"][0]
                assert variant["name"] == "baseline_actual_pack"
                pack = GlinerPack.from_declaration(frozen["release_id"], variant["schema"])
                assert pack.fingerprint == variant["pack_fingerprint"]
                before_cpu, before_wall = cpu(worker.pid), time.perf_counter()
                (report,) = worker.extract(pack, (item,), threshold=0.15)
                row = dict(context_index=context["context_index"], family=context["family"], threshold=0.15,
                           variant=variant["name"], outcome="passed", report=asdict(report),
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
