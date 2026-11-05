"""Two explicit whitespace-profile calls on the same two retained source inputs."""

import json
from dataclasses import asdict, replace
from pathlib import Path

from corpus_structure.methods.gliner import (
    WHITESPACE_PROFILE,
    GlinerInput,
    GlinerPack,
    GlinerProfile,
)
from corpus_structure.methods.gliner_worker import GlinerWorker


def main():
    root = Path(__file__).parent / "raw"
    previous = json.loads(root.joinpath("parser-local-schema-comparison-002.json").read_text())
    config = previous["profile"]
    config["snapshot"] = Path(config["snapshot"])
    config["artifact_hashes"] = tuple(tuple(value) for value in config["artifact_hashes"])
    original = GlinerProfile(**config)
    profile = replace(original, version=WHITESPACE_PROFILE)
    output = dict(
        scope="two matching retained-input calls; only explicit splitter recipe changes",
        reference_answers_consumed=False,
        native_products_written=False,
        baseline_profile=asdict(original),
        selected_profile=asdict(profile),
        results=[],
    )
    worker = GlinerWorker(profile)
    try:
        for entry in previous["selected_contexts"]:
            baseline = next(
                value
                for value in previous["results"]
                if value["context"] == entry["context"]
                and value["variant"] == "current_three_entities_with_attributes"
            )
            pack = GlinerPack(**baseline["pack"])
            retained = baseline["report"]
            (report,) = worker.extract(
                pack,
                (GlinerInput(retained["context_id"], retained["context_digest"], entry["source"]),),
                threshold=previous["threshold"],
            )
            output["results"].append(
                dict(
                    context=entry["context"],
                    declared_primary=entry["declared_primary"],
                    pack=asdict(pack),
                    report=asdict(report),
                    baseline_computation=retained["computation"],
                )
            )
        output["outcome"] = "passed"
    except Exception as error:
        output.update(outcome="failed", error=repr(error))
        raise
    finally:
        worker.close()
        root.joinpath("parser-local-whitespace-comparison-001.json").write_text(
            json.dumps(output, indent=2, default=str) + "\n"
        )


if __name__ == "__main__":
    main()
