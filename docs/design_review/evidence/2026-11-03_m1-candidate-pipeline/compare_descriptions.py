"""Paired actual CPU development observation; no reference answers or accuracy gate."""

from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from threadpoolctl import ThreadpoolController

from corpus_structure.core.method import SourceViewRef
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import pipeline
from corpus_structure.methods.gliner import GlinerInput
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import _retained_report, configured_packs
from corpus_structure.methods.record_assembly import NativeRecordGroup, RoleInput, assemble_records
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView


def main():
    parser=argparse.ArgumentParser()
    for name in ("retained","paragraph","checkout","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    paragraph=json.loads(args.paragraph.read_text())
    with gzip.open(args.retained,"rt") as handle:
        selected=next(row for row in json.load(handle) if row["pin"]["id"]==paragraph["pin"]["id"])
    if selected["pin"] != paragraph["pin"]:
        raise ValueError("development paragraph has another retained source pin")
    pin=dict(selected["pin"])
    pin["native_product"]=ProductReference(**pin["native_product"])
    view=PreparedSourceView(SourceViewRef(**pin),selected["text"],tuple(selected["pieces"]),tuple(selected["items"]),tuple(selected["ancestors"]),selected["health"])
    model=args.checkout/"python/corpus-structure/src/corpus_structure/model/semantic"
    prepared=prepare_release(observation_inputs(SourceBundle("statistics_semantic",(
        SourceArtifact("statistics_semantic",(args.checkout/"domains/statistics/semantic.yaml").read_bytes()),
        SourceArtifact("semantic_core",(model/"core.yaml").read_bytes()),
    ))))
    cfg=registry(args.checkout/"domains/statistics").overlay("extract.m1_candidates","described")
    packs={"before":configured_packs(prepared,cfg.model_copy(update={"pack_descriptions":{}})),
        "after":configured_packs(prepared,cfg)}
    pipeline(cfg.sentences)
    controller=ThreadpoolController()
    with controller.limit(limits=cfg.parent_threads):
        source=prepare_source(view,profile=AnnotationProfile(cfg.sentences),max_chars=cfg.max_context_chars,max_pieces=cfg.max_context_pieces,max_annotation_chars=cfg.max_annotation_chars)
    (selection,)=tuple(s for s in source.selections if (s.start,s.end)==(paragraph["start"],paragraph["end"]) and "definition" in s.families)
    context=selection.context(source.source,max_chars=cfg.max_context_chars,max_pieces=cfg.max_context_pieces)
    if context.text != paragraph["text"]:
        raise ValueError("development context does not reconstruct the retained paragraph")
    paths=[args.checkout/"domains/statistics/m1-methods.yaml",args.checkout/"python/corpus-structure/src/corpus_structure/methods/m1_source.py"]
    def hashes():
        return {str(path.relative_to(args.checkout)):sha256(path.read_bytes()).hexdigest() for path in paths}
    result=dict(date="2026-11-03",standing="development observation only; no independent accuracy, calibration, release or adoption claim",
        source_pin=selected["pin"],selection=asdict(selection),context_digest=context.dependency_digest,
        input_text_sha256=sha256(context.text.encode()).hexdigest(),profile=cfg.profile().fingerprint,
        source_hashes_before=hashes(),effective_profiles={},comparisons={})
    worker=GlinerWorker(cfg.profile())
    try:
        for name,families in packs.items():
            pack=families["definition"]
            (report,)=worker.extract(pack,(GlinerInput.from_context(context),),threshold=cfg.threshold)
            groups=report.raw.get("definition",())
            supplements={i:NativeRecordGroup((RoleInput("scope",native_pointer=view.ref.section_pointer),),"selected native section is the explicit definition scope") for i,_ in enumerate(groups)}
            assembled=assemble_records(prepared,context,pack,report,contract="DefinitionRecordFields",anchor_role="term",policy_version=cfg.policy,supplements=supplements)
            result["comparisons"][name]=dict(pack_fingerprint=pack.fingerprint,declaration=json.loads(pack.declaration_json),report=_retained_report(report,result["effective_profiles"]),records=[record.model_dump(mode="python") for record in assembled.records],diagnostics=[asdict(d) for d in assembled.diagnostics])
        result["outcome"]="passed"
    finally:
        worker.close()
        result["worker_joined"]=worker.pid is None
        result["source_hashes_after"]=hashes()
        result["source_unchanged"]=result["source_hashes_before"]==result["source_hashes_after"]
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+"\n")
    print(json.dumps({"outcome":result.get("outcome"),"worker_joined":result["worker_joined"],"source_unchanged":result["source_unchanged"],"records":{k:len(v["records"]) for k,v in result["comparisons"].items()}}))


if __name__ == "__main__":
    main()
