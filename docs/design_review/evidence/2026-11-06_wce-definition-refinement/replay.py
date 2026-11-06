"""Replay exact GS120 source annotations and raw definition replies without inference.

This is exposed method-development evidence, not an independent efficacy assessment.
The database connection is read-only and no PDF or language-model pipeline executes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import yaml

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    decode_definition_components,
    retained_annotation_components,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import load_structural_annotations
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt")
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    output = here / "raw" / args.attempt
    output.mkdir(parents=True, exist_ok=False)
    baseline = args.baseline
    config_path = baseline / "baseline003/gs120-all120-pages/configuration.json"
    cfg = DefinitionComponentsConfig.model_validate(json.loads(config_path.read_bytes())["definition"])
    rules = yaml.safe_load((here.parents[3] / "domains/statistics/m1-methods.yaml").read_text())["configs"]["extract.m1_candidates"]["witnessed"]["annotation_rules"]
    current = DefinitionComponentsConfig.model_validate({**cfg.model_dump(mode="json"), "annotation_rules": rules})
    assert cfg.inputs is not None
    retained_sources = {}
    with open_runtime_engine(Settings(), "gs120-definition-replay", purpose="read") as engine:
        with engine.connect() as conn:
            for source in cfg.inputs.sources:
                retained_sources[source.identity] = load_structural_annotations(
                    conn, cfg.inputs, source.identity, AnnotationProfile(SentenceConfig(exclude=("ner",)))
                )
    results = {}
    for label, selected in (("baseline_rules", cfg), ("current_rules", current)):
        components, operations = {}, []
        for passage in cfg.inputs.passages:
            result = retained_annotation_components(None, cfg.inputs, passage, selected, retained=retained_sources[passage.source_ref])
            components.update((c.component_id, c.model_dump(mode="json")) for c in result.components)
            operations.extend(result.operations)
        results[label] = dict(components=list(components.values()), operation_matches=dict(Counter((o["variant"] for o in operations for _ in range(o["matched_count"])))), operations=operations)
    cues = []
    for passage in cfg.inputs.passages:
        retained = retained_sources[passage.source_ref]
        for product in retained.annotations:
            for i, token in enumerate(product.tokens):
                if token.lemma not in {"define", "call", "give"}:
                    continue
                sentence = next((s for s in product.sentences if s.start <= token.start < s.end), None)
                if sentence is None:
                    continue
                cues.append(dict(passage_id=passage.passage_id, text=retained.source.text[sentence.start:sentence.end], tokens=[dict(i=j, text=retained.source.text[t.start:t.end], head=t.head, dep=t.dependency, lemma=t.lemma, pos=t.pos) for j,t in enumerate(product.tokens) if sentence.start <= t.start < sentence.end]))
    raw_task = json.loads((baseline / "assessment/run139-final001/task-544.json").read_bytes())
    raw_reports = source_python(raw_task["body"]["parse_detail"])["raw_reports"]
    model_components, model_errors = {}, []
    passages = {p.passage_id:p for p in cfg.inputs.passages}
    for index, row in enumerate(raw_reports):
        passage = passages[row["passage_id"]]
        window = passage.model_copy(update=dict(start=row["window_start"], end=row["window_end"], text=passage.text[row["window_start"]-passage.start:row["window_end"]-passage.start]))
        try:
            candidate_errors = []
            found = decode_definition_components(json.loads(row["raw_json"]), window, cfg, candidate_errors=candidate_errors)
            model_components.update((c.component_id,c.model_dump(mode="json")) for c in found)
            if candidate_errors:
                model_errors.append(dict(window=index, retained_components=len(found), candidate_errors=candidate_errors))
        except ValueError as error:
            model_errors.append(dict(window=index, reason=str(error)))
    result = dict(protocol="gs120-definition-refinement-replay-1", inference="not_run", database_writes="not_run", original_sources=len(retained_sources), source_annotation_tasks=[r.annotation_task_id for r in retained_sources.values()], input_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in (config_path, baseline / "assessment/run139-final001/task-544.json")}, implementation_sha256=sha256((here.parents[3]/"python/corpus-structure/src/corpus_structure/methods/definition_applicability.py").read_bytes()).hexdigest(), current_rules_sha256=sha256(canonical_bytes(rules)).hexdigest(), rules=results, model=dict(components=list(model_components.values()), errors=model_errors, windows=len(raw_reports)), cues=cues)
    (output / "result.json").write_bytes(canonical_bytes(result)+b"\n")
    (output / "components.json").write_bytes(canonical_bytes(dict(named=results["current_rules"]["components"], model=list(model_components.values())))+b"\n")
    print(json.dumps(dict(outcome="passed", sources=len(retained_sources), rules={k:len(v["components"]) for k,v in results.items()}, model_components=len(model_components), model_failed_windows=len(model_errors), raw_windows=len(raw_reports))))


if __name__ == "__main__":
    main()
