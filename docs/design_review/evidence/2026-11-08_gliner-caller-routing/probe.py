"""Compare public GLiNER requests using the retained model and assertion context."""

import json
import runpy
from hashlib import sha256
from pathlib import Path

from gliner2.inference.schema import Schema

from corpus_structure.methods.gliner import GlinerPack, load_model
from corpus_structure.methods.model_observation import installed_policy


def main():
    previous = Path(__file__).resolve().parent.with_name("2026-11-08_gliner-assertion-anchor")
    retained = runpy.run_path(str(previous / "probe.py"))["retained_request"]
    cfg, packs, failure, control, text, _ = retained()
    model, effective = load_model(cfg.profile())
    assert sha256(effective.encode()).hexdigest() == control["effective_profile_ref"]
    pack = packs["assertion"]
    structure = json.loads(pack.declaration_json)["structures"]["assertion"]
    literal_fields = [field for field in structure["fields"] if not field.get("choices")]
    latent = {"mode": "latent", "fields": structure["fields"]}
    literal = {**structure, "fields": literal_fields}
    schemas = {
        "combined": pack.compile(),
        "latent": GlinerPack.from_declaration(
            pack.release, {"structures": {"assertion": latent}}, version="native-combined-v2"
        ).compile(),
        "literal": Schema.from_dict({"structures": {"assertion": literal}}),
    }
    inference, _ = installed_policy()
    options = {
        key: value for key, value in inference["inference"].items() if key != "operation"
    }

    def observe(source, schema):
        prepared = model.processor.transform_record(source, schema)
        prefix_words = len(prepared.text_tokens) - len(prepared.start_token_idx)
        try:
            (raw,) = model.batch_extract(
                [source], schema, batch_size=1, threshold=cfg.threshold,
                overlap_policy="flat", **options
            )
        except ValueError as exc:
            return {"prefix_words": prefix_words, "error": f"{type(exc).__name__}: {exc}"}
        return {"prefix_words": prefix_words, "result": raw}

    retained_result = {name: observe(text, schema) for name, schema in schemas.items()}
    assert retained_result["combined"]["error"] == failure["reason"], retained_result
    assert retained_result["literal"]["prefix_words"] == 0, retained_result

    clause_pairs = (
        ("The root is real.", "The root is not positive."),
        ("The mean is finite.", "The variance is not finite."),
        ("The population mean equals 10.", "The variance does not equal 0."),
    )
    classes = Schema().classification(
        "polarity",
        {"positive": "affirmative assertion", "negative": "negation of the predicate"},
    ).classification(
        "modality",
        {"asserted": "presented as a fact", "possible": "presented as a possibility"},
    )
    controls = []
    for clauses in clause_pairs:
        source = " ".join(clauses)
        literal_result = observe(source, schemas["literal"])
        for record in literal_result["result"].get("assertion", []):
            for value in record.values():
                if isinstance(value, dict) and "start" in value:
                    assert source[value["start"] : value["end"]] == value["text"], value
        controls.append(
            {
                "source": source,
                "combined": observe(source, schemas["combined"]),
                "literal": literal_result,
                "classification": [
                    {"text": clause, **observe(clause, classes)} for clause in clauses
                ],
            }
        )
    print(
        json.dumps(
            {"source": text, "retained": retained_result, "controls": controls},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
