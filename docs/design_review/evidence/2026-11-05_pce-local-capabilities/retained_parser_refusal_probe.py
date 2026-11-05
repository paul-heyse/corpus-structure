"""Actual native preparation refusal, then valid work on the same resident child."""

import json
from dataclasses import asdict, replace
from pathlib import Path

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker


def main():
    raw = Path(__file__).parent / "raw"
    baseline = json.loads(raw.joinpath("parser-local-whitespace-comparison-001.json").read_text())
    sources = json.loads(raw.joinpath("parser-local-schema-comparison-002.json").read_text())
    configuration = baseline["selected_profile"]
    configuration["snapshot"] = Path(configuration["snapshot"])
    configuration["artifact_hashes"] = tuple(tuple(row) for row in configuration["artifact_hashes"])
    profile = replace(GlinerProfile(**configuration), max_subwords=234)
    worker = GlinerWorker(profile)
    receipt = dict(
        scope="actual native input refusal + subsequent inference; no corpus products",
        profile=asdict(profile),
        results=[],
    )
    try:
        for context in (1, 8):
            prior = next(row for row in baseline["results"] if row["context"] == context)
            source = next(
                row["source"] for row in sources["selected_contexts"] if row["context"] == context
            )
            request = GlinerInput(
                prior["report"]["context_id"], prior["report"]["context_digest"], source
            )
            try:
                (report,) = worker.extract(GlinerPack(**prior["pack"]), (request,), threshold=0.5)
                receipt["results"].append(
                    dict(
                        context=context, outcome="succeeded", report=asdict(report), pid=worker.pid
                    )
                )
                assert context == 8
            except GlinerRefused as error:
                receipt["results"].append(
                    dict(context=context, outcome="limited", reason=str(error), pid=worker.pid)
                )
                assert context == 1 and "subword bound" in str(error)
            assert not worker.closed
        assert receipt["results"][0]["pid"] == receipt["results"][1]["pid"]
        receipt["outcome"] = "passed"
    except Exception as error:
        receipt.update(outcome="failed", error=repr(error))
        raise
    finally:
        worker.close()
        raw.joinpath("parser-local-refusal-survival-002.json").write_text(
            json.dumps(receipt, indent=2, default=str) + "\n"
        )


if __name__ == "__main__":
    main()
