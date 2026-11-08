"""Verify the M1 request with the production pack builder and resident worker."""

import json
import runpy
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.gliner import GlinerInput, load_model
from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError
from corpus_structure.methods.m1_source import configured_packs
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import open_release
from corpus_structure.settings import Settings

RELEASE = "release:0888dfc502c4d7d21dc0b2e498f0ce99351236b843b98e3aa884d72ef4b40ade"


def main():
    evidence = Path(__file__).resolve().parent.parent
    replay = runpy.run_path(str(evidence / "2026-11-08_gliner-assertion-anchor/probe.py"))
    cfg, _, _, control, text, _ = replay["retained_request"]()
    with (
        open_runtime_engine(Settings(), "m1-assertion-qualification", purpose="read") as engine,
        engine.connect() as conn,
    ):
        packs = configured_packs(open_release(conn, RELEASE), cfg)
    results = {}
    cases = (
        ("assertion", "retained", text),
        ("definition", "retained", text),
        ("measurement", "retained", text),
        ("definition", "control", "The mean is the sum divided by the number of observations."),
        ("measurement", "control", "The sample mean was 12. The standard deviation was 3."),
    )
    worker = GlinerWorker(cfg.profile())
    try:
        for family, case, source in cases:
            key = f"{family}/{case}"
            if case == "retained":
                item = GlinerInput(control["context_id"], control["context_digest"], source)
            else:
                digest = sha256(source.encode()).hexdigest()
                item = GlinerInput(digest, digest, source)
            try:
                (report,) = worker.extract(packs[family], (item,), threshold=cfg.threshold)
            except GlinerWorkerError as error:
                results[key] = {"error": str(error)}
                break
            results[key] = {
                "effective_profile": sha256(report.effective_profile_json.encode()).hexdigest(),
                "pack": report.pack,
                "result": report.raw,
                "source_words": report.preparation.words,
            }
            assert results[key]["effective_profile"] == control["effective_profile_ref"]
    finally:
        worker.close()
    model, effective = load_model(cfg.profile())
    assert sha256(effective.encode()).hexdigest() == control["effective_profile_ref"]
    transformed = model.processor.transform_record(text, packs["assertion"].compile())
    prefix_words = len(transformed.text_tokens) - len(transformed.start_token_idx)
    print(json.dumps({"prefix_words": prefix_words, "requests": results}, indent=2))
    assert prefix_words == 0
    predicates = [
        group.get("predicate") for group in results["assertion/retained"]["result"]["assertion"]
    ]
    assert any(
        pred and (pred["start"], pred["end"], pred["text"]) == (24, 32, text[24:32])
        for pred in predicates
    )
    assert len(results) == len(cases) and all("error" not in row for row in results.values())


if __name__ == "__main__":
    main()
