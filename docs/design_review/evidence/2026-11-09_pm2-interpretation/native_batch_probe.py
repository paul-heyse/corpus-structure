"""Run a bounded native typed batch before any development publication."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from corpus_structure.methods import pm2_native
from corpus_structure.methods.pm2_worker import open_pm2_worker
from corpus_structure.semantic.interpretation_questions import (
    QUESTION_INPUT,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.types import SourceArtifact
from corpus_structure.settings import Settings


def main():
    root = Path.cwd()
    assets = root / "build/models/pm2"
    config = root / "domains/statistics/interpretation-questions.yaml"
    families = declared_families(compile_question_families((SourceArtifact(QUESTION_INPUT, config.read_bytes()),)))
    choice = families["passage_function_v1"].questions[0]
    literal, quantity, date = families["literal_completion_v1"].questions
    relation = families["relation_interpretation_v1"].questions[0]
    requests = [
        {"state": {"source": "The café opened on January 7, 2025 and served 12 guests."},
         "questions": {item.key: item.native([]) for item in (quantity, date)}},
        {"state": {"source": "A random variable is simply an expression whose value is the outcome of a particular experiment."},
         "questions": {item.key: item.native([]) for item in (choice, literal)}},
        {"state": {"source": "The pump stopped because the inlet valve jammed.",
                   "focus": "The pump stopped", "candidates": ["the inlet valve jammed"]},
         "questions": {relation.key: relation.native([])}},
        {"state": {"source": "limit control"},
         "questions": {f"q{i}": literal.native([]) for i in range(17)}},
    ]
    with TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile.json"
        profile.write_text(json.dumps({"provider": "d1", "device": "cuda", "assets": str(assets)}))
        with open_pm2_worker(
            python=Path(sys.executable), script=Path(pm2_native.__file__), profile=profile,
            device="cuda", nemotron_endpoint=Settings().nemotron.endpoint,
        ) as worker:
            print(json.dumps({"startup": worker.startup}, ensure_ascii=False), flush=True)
            result = worker.infer({"batch": requests})["batch"]
            for request, response in zip(requests, result, strict=True):
                print(json.dumps({"request": request, "response": response}, ensure_ascii=False))
    assert [response["outcome"] for response in result] == ["succeeded"] * 3 + ["limited"]
    assert list(result[0]["native"]["answers"]) == ["quantity", "date"]
    assert list(result[1]["native"]["answers"]) == ["passage_functions", "literal"]
    assert result[2]["native"]["answers"]["reported_reason"]["type"] == "noul"


if __name__ == "__main__":
    main()
