"""Compare bounded GLiNER2.5 antecedent proposals with independent source controls."""

import argparse
import json
from pathlib import Path

import yaml
from gliner2.joint_ie import JointIE, JointIEConfig

from corpus_structure.methods.gliner import GlinerProfile, load_model
from corpus_structure.schema.pack import DOMAINS

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    with (args.bundle / "sources.jsonl").open() as rows:
        original = next(
            row["text"]
            for line in rows
            if (row := json.loads(json.loads(line)["payload_json"]))["source_view_id"] == 147
        )
    declaration = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_bytes())
    declared = declaration["configs"]["extract.m1_candidates"]["default"]
    profile = GlinerProfile(
        snapshot=Path(declared["snapshot"]),
        checkpoint=declared["checkpoint"],
        revision=declared["revision"],
        artifact_hashes=tuple(tuple(item) for item in declared["artifact_hashes"]),
        threads=declared["threads"],
    )
    model, effective = load_model(profile)
    joint = JointIE(model)
    relation = "refers to an earlier expression that denotes the same set"
    cases = {
        "exact": original[175:351],
        "competing": (
            "We consider the set of points such that x = 0 and the set of points such that y = 0. "
            "This set of points is called the boundary."
        ),
        "missing": "We first choose a line. This set of points is called the boundary.",
    }
    result = {}
    for case, source in cases.items():
        predictions = {}
        for threshold in (0.5, 0.2):
            schema = (
                joint.create_schema()
                .entity("demonstrative set reference", "Short referring phrase starting with this or that")
                .entity("earlier set description", "Full earlier noun phrase defining the set and its criterion")
                .relation(
                    relation,
                    head="demonstrative set reference",
                    tail="earlier set description",
                    max_per_head=1,
                    threshold=threshold,
                )
                .no_self_loops()
            )
            reading = joint.extract(
                source, schema,
                config=JointIEConfig(beam_size=16, entity_threshold=threshold),
            )
            assert all(source[e.start:e.end] == e.text for e in reading.entities)
            predictions[str(threshold)] = reading.to_dict()
        result[case] = {"source": source, "predictions": predictions}
    print(json.dumps({"effective": json.loads(effective), "cases": result}, indent=2))


if __name__ == "__main__":
    main()
