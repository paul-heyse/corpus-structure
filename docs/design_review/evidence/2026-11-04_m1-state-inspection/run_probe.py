"""Nine serial native calls on frozen detached inputs; no database access."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import time

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker

HERE = Path(__file__).parent


def cpu(pid):
    if pid is None:
        return 0.0
    stat = Path(f"/proc/{pid}/stat").read_text().split(")", 1)[1].split()
    return (int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK")


def main():
    frozen_bytes = (HERE / "frozen-inputs.json").read_bytes()
    frozen = json.loads(frozen_bytes)
    profile_data = frozen["profile"]
    profile_data["snapshot"] = Path(profile_data["snapshot"])
    profile_data["artifact_hashes"] = tuple(tuple(entry) for entry in profile_data["artifact_hashes"])
    profile = GlinerProfile(**profile_data)
    worker = GlinerWorker(profile)
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(),
                   input_sha256=hashlib.sha256(frozen_bytes).hexdigest(), calls=[], outcome="running")
    output = HERE / "results.jsonl"
    started = time.perf_counter()
    with output.open("x") as stream:
        try:
            for context in frozen["contexts"]:
                item = GlinerInput(context["context_id"], context["context_digest"], context["text"])
                for variant in context["variants"]:
                    pack = GlinerPack.from_declaration(frozen["release_id"], variant["schema"])
                    before_cpu = cpu(worker.pid)
                    before_wall = time.perf_counter()
                    (report,) = worker.extract(pack, (item,), threshold=frozen["threshold"])
                    row = dict(context_index=context["context_index"], family=context["family"],
                               variant=variant["name"], outcome="passed", report=asdict(report),
                               wall_seconds=time.perf_counter() - before_wall,
                               child_cpu_seconds=cpu(worker.pid) - before_cpu,
                               child_pid=worker.pid, cpu_scope="whole call including lazy load/preparation; Linux utime+stime")
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stream.flush()
                    receipt["calls"].append({key: row[key] for key in ("context_index", "variant", "outcome", "wall_seconds", "child_cpu_seconds")})
                    print(json.dumps(receipt["calls"][-1]), flush=True)
            receipt["outcome"] = "passed"
        except BaseException as exc:
            receipt.update(outcome="failed", error=repr(exc))
            raise
        finally:
            pid = worker.pid
            worker.close()
            receipt.update(wall_seconds=time.perf_counter() - started,
                           process_joined=worker.closed and (pid is None or not Path(f"/proc/{pid}").exists()),
                           child_pid=pid, finished_at=datetime.now(timezone.utc).isoformat(),
                           child_usage=asdict_usage(resource.getrusage(resource.RUSAGE_CHILDREN)))
            with (HERE / "receipt.json").open("x") as receipt_stream:
                json.dump(receipt, receipt_stream, indent=2)
                receipt_stream.write("\n")


def asdict_usage(usage):
    return dict(user_seconds=usage.ru_utime, system_seconds=usage.ru_stime, max_rss_kib=usage.ru_maxrss)


if __name__ == "__main__":
    main()
