"""Read-only retained-source context to actual CPU reports and literal evidence.

This development probe uses an explicitly nonrelease schema. It does not publish
records, grade source reading, claim family accuracy or alter task/default state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import text

from corpus_structure.methods.gliner import (
    GlinerInput, GlinerPack, GlinerProfile, GlinerRefused, map_record_field,
)
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    if args.attempt < 1:
        parser.error("attempt must be positive")
    target = HERE / f"mapped-attempt-{args.attempt:05d}.json"
    packet = HERE / f"mapped-context-{args.attempt:05d}.json"
    if target.exists() or packet.exists():
        raise FileExistsError("retain prior outputs and choose another attempt")
    source_path = HERE.parent / "2026-11-03_m1-population/cpu-source-paragraph.json"
    probe_path = HERE.parent / "2026-11-03_m1-gliner-cpu/attempt-00003.json"
    source, probe = json.loads(source_path.read_bytes()), json.loads(probe_path.read_bytes())
    receipt = {
        "outcome": "failed",
        "claim": "actual source-context/CPU/literal mapping only; probe schema, no accepted records, accuracy, evaluation, release or default claim",
        "source_artifact_sha256": digest(source_path),
        "source_pin": source["pin"],
        "implementation_sha256": {
            name: digest(REPO / name) for name in (
                "python/corpus-structure/src/corpus_structure/methods/gliner.py",
                "python/corpus-structure/src/corpus_structure/methods/gliner_worker.py",
                "python/corpus-structure/src/corpus_structure/semantic/source_contexts.py",
            )
        },
        "helper_sha256": digest(Path(__file__)),
    }
    worker = None
    try:
        # The supplied settings select the retained source database explicitly.
        # Neither a task lease nor a source/evaluator write is requested.
        with open_runtime_engine(Settings(), "ci-m1-mapped-cpu-probe", purpose="read") as engine:
            with engine.connect() as conn:
                conn.execute(text("SET TRANSACTION READ ONLY"))
                receipt["transaction_read_only"] = conn.scalar(text("SHOW transaction_read_only"))
                view = load_source_view(conn, source["pin"]["id"], analysis=False)
                if asdict(view.ref) != source["pin"]:
                    raise ValueError("retained source pin differs from frozen development input")
                frame = native_source_frame(view, (("selected-paragraph", source["start"], source["end"]),))
                context = NativeSourceContext(
                    frame, (), (SourceSlice(view.ref.id, source["start"], source["end"]),),
                    "development CPU literal mapping", "m1-development-only", "bounded selected paragraph",
                )
                if context.text != source["text"]:
                    raise ValueError("source context does not reconstruct the selected paragraph")
        # The source connection is closed before model work. Only detached input crosses IPC.
        with packet.open("x") as output:
            json.dump(asdict(context), output, ensure_ascii=False, indent=2)
            output.write("\n")
        receipt.update(context_digest=context.dependency_digest, context_artifact_sha256=digest(packet))
        snapshot = Path.home() / ".cache/huggingface/hub/models--fastino--gliner2.5-base-v1/snapshots" / probe["revision"]
        profile = GlinerProfile(snapshot, probe["checkpoint"], probe["revision"], tuple(probe["snapshot_files"].items()))
        pack = GlinerPack.from_declaration("PROBE-ONLY-NOT-A-RELEASE", probe["schema_declaration"])
        worker = GlinerWorker(profile)
        calls = []
        for name in ("cold", "warm"):
            report, = worker.extract(pack, (GlinerInput.from_context(context),))
            mapped, classified_refusals = [], 0
            for group_index, group in enumerate(report.raw.get("definition", ())):
                for role in ("term", "description"):
                    if role in group:
                        anchors = map_record_field(pack, "definition", role, report, context, group[role])
                        mapped.append({"group": group_index, "role": role, "anchors": [asdict(anchor) for anchor in anchors]})
                if "category" in group:
                    try:
                        map_record_field(pack, "definition", "category", report, context, group["category"])
                    except GlinerRefused:
                        classified_refusals += 1
                    else:
                        raise AssertionError("classified choices became literal evidence")
            if not mapped or not classified_refusals:
                raise AssertionError("probe did not exercise literal and classified paths")
            calls.append({"name": name, "pid": worker.pid, "report": asdict(report), "mapped_fields": mapped, "classified_literal_refusals": classified_refusals})
        if calls[0]["pid"] != calls[1]["pid"] or calls[0]["report"]["computation"] != calls[1]["report"]["computation"]:
            raise AssertionError("same pinned computation did not reuse its resident worker")
        receipt.update(outcome="passed", calls=calls)
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    finally:
        if worker is not None:
            worker.close()
            receipt["worker_joined"] = worker.closed and worker.pid is None
        with target.open("x") as output:
            json.dump(receipt, output, ensure_ascii=False, indent=2)
            output.write("\n")
    print(json.dumps({key: receipt.get(key) for key in ("outcome", "transaction_read_only", "worker_joined", "context_digest")}))
    if receipt["outcome"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
