"""Actual detached CPU source producer on a retained MAIN source snapshot; no database."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import resource
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from corpus_structure.core.method import SourceViewRef, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--retained",type=Path,required=True)
    parser.add_argument("--checkout",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-view",type=int,default=3)
    args=parser.parse_args()
    with gzip.open(args.retained,"rt") as handle:
        selected=next(row for row in json.load(handle) if row["pin"]["id"] == args.source_view)
    pin=dict(selected["pin"])
    pin["native_product"]=ProductReference(**pin["native_product"])
    view=PreparedSourceView(SourceViewRef(**pin),selected["text"],tuple(selected["pieces"]),tuple(selected["items"]),tuple(selected["ancestors"]),selected["health"])
    model=args.checkout/"python/corpus-structure/src/corpus_structure/model/semantic"
    prepared=prepare_release(observation_inputs(SourceBundle("statistics_semantic",(
        SourceArtifact("statistics_semantic",(args.checkout/"domains/statistics/semantic.yaml").read_bytes()),
        SourceArtifact("semantic_core",(model/"core.yaml").read_bytes()),
    ))))
    method=M1Candidates()
    cfg=registry(args.checkout/"domains/statistics").overlay(method.name,"default")
    paths = ["methods/source_preparation.py", "methods/m1_source.py", "methods/record_assembly.py",
        "methods/record_packs.py", "methods/gliner.py", "methods/gliner_worker.py",
        "ingest/annotations.py", "ingest/sentences.py", "semantic/source_contexts.py"]
    sources = [args.checkout/"python/corpus-structure/src/corpus_structure"/path for path in paths]
    sources += [args.checkout/"domains/statistics"/name for name in ("semantic.yaml", "m1-methods.yaml", "m1-guideline.md")]
    def hashes():
        return {str(path.relative_to(args.checkout)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    started=time.monotonic()
    report=dict(date="2026-11-03",claim="actual detached CPU candidate producer only; no database fencing, accuracy, accepted output, release or ordinary-workload qualification",source_pin=selected["pin"],retained_sha256=hashlib.sha256(args.retained.read_bytes()).hexdigest())
    report["source_hashes_before"] = hashes()
    try:
        (result,)=method.run((SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW,view.ref.id,view.ref.key)),),cfg,SimpleNamespace(reader=SimpleNamespace(prepared=prepared,source_view=lambda identity:view),check_active=lambda:None))
        report.update(outcome="failed" if result.error else "passed",result=asdict(result),record_counts=dict(Counter(row["family"] for row in result.records or ())),error=result.error)
    except BaseException as error:
        report.update(outcome="failed",error=f"{type(error).__name__}: {error}")
        raise
    finally:
        method.close()
        report.update(worker_joined=method._worker is None,elapsed_seconds=time.monotonic()-started,parent_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        report["source_hashes_after"] = hashes()
        report["source_unchanged"] = report["source_hashes_before"] == report["source_hashes_after"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+"\n")
        print(json.dumps({key:value for key,value in report.items() if key != "result"},default=str))


if __name__ == "__main__":
    main()
