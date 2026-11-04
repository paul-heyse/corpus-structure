"""Actual bounded native codepoint worker with source-only frozen text, no labels."""
from __future__ import annotations
import os
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1")
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from corpus_structure.methods.gliner import GlinerInput
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config, configured_pack_variants
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic.regeneration import prepare_pack

HERE=Path(__file__).resolve().parent
STUDY=HERE.parent/"2026-11-04_m1-source-boundary-fit/attempt-002"
def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def main():
    output=HERE/"interface-001"
    output.mkdir(exist_ok=False)
    output.joinpath("executed-runner.py.txt").write_bytes(Path(__file__).read_bytes())
    budgets=[json.loads(line) for line in (STUDY/"native-budgets.jsonl").read_text().splitlines()]
    maximum=max((row for row in budgets if row["variant"]=="expanded" and row["segmentation"]=="codepoints"),key=lambda row:(row["subwords"],row["source_view_id"],row["index"]))
    contexts=[json.loads(line) for line in (STUDY/"expanded-contexts.jsonl").read_text().splitlines()]
    context=next(row for row in contexts if (row["source_view_id"],row["index"])==(maximum["source_view_id"],maximum["index"]))
    assert context["context_id"]==maximum["context_id"]
    _,_,_,prepared=prepare_pack(Path("domains/statistics"))
    config=registry(Path("domains/statistics")).config("extract.m1_candidates","contextual").config
    assert isinstance(config,M1Config)
    profile=config.profile()
    packs=configured_pack_variants(prepared,config)["formula_context"]
    dump(output/"input.json",dict(release_id=prepared.release_id,context=context,budget_observation=maximum,profile={**asdict(profile),"snapshot":str(profile.snapshot)},variants=[dict(name=name,anchor=anchor,pack=pack.fingerprint,declaration=json.loads(pack.declaration_json)) for name,anchor,pack in packs],source_text_sha256=sha256(context["text"].encode()).hexdigest(),selection="largest independently source-prepared formula request by subword count; no labels or predictions"))
    worker=GlinerWorker(profile)
    summaries=[]
    child_pid=None
    started=perf_counter()
    try:
        for variant,anchor,pack in packs:
            report,=worker.extract(pack,(GlinerInput(context["context_id"],context["context_id"],context["text"]),),threshold=config.threshold)
            if worker._process is not None:
                child_pid=worker._process.pid
            effective=json.loads(report.effective_profile_json)
            assert effective["splitter"]=="UnicodeCodepointSplitter"
            assert effective["device"]=="cpu" and effective["dtype"]=="float32"
            assert effective["threads"]==4 and effective["interop_threads"]==1
            assert report.preparation.consumed_text==context["text"]+report.preparation.synthetic_suffix
            assert report.preparation.words<=profile.max_words and report.preparation.subwords<=profile.max_subwords
            dump(output/(variant+".json"),asdict(report))
            summaries.append(dict(variant=variant,anchor=anchor,pack=pack.fingerprint,profile=report.profile,words=report.preparation.words,subwords=report.preparation.subwords,inference_seconds=report.inference_seconds,resident_reused=report.resident_reused,groups=len(report.raw.get("formula_context",())),child_pid=child_pid))
    finally:
        worker.close()
        dump(output/"settlement.json",dict(closed=worker.closed,child_pid=child_pid,child_absent=child_pid is None or not Path("/proc",str(child_pid)).exists()))
    assert child_pid is not None and not Path("/proc",str(child_pid)).exists()
    assert not summaries[0]["resident_reused"] and summaries[1]["resident_reused"]
    result=dict(outcome="passed",release_id=prepared.release_id,variants=summaries,wall_seconds=perf_counter()-started,child_absent=True,quality_claim="not_established",scope="actual codepoint/CPU/FP32 native worker and maximum observed input; no source record/acceptance or integrated journey claim")
    dump(output/"summary.json",result)
    print(json.dumps(result),flush=True)
if __name__=="__main__":main()
