"""Actual pinned CPU local-schema call; bounded provider contract, not corpus quality."""

import dataclasses
import json
from pathlib import Path

import yaml

from corpus_structure.methods.gliner import GlinerInput, GlinerPack
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config


def main():
    config = M1Config.model_validate(yaml.safe_load(Path("domains/statistics/m1-methods.yaml").read_text())["configs"]["extract.m1_candidates"]["default"])
    pack = GlinerPack.from_declaration("provider-contract:pce07-local-1", {
        "entities": ["distribution"],
        "entity_attributes": {"role": {"labels": ["defined_term", "alias"], "applies_to": ["distribution"], "qualify_labels": True}},
        "relations": ["alias_of"],
    }, version="native-local-v1")
    text = "The normal distribution is also called the Gaussian distribution."
    from hashlib import sha256
    profile = config.profile()
    worker = GlinerWorker(profile)
    result = dict(scope="one controlled text CPU native schema contract; not corpus assessment", profile=profile.fingerprint, pack=dataclasses.asdict(pack), text=text)
    try:
        (report,) = worker.extract(pack, (GlinerInput("pce07-local", sha256(text.encode()).hexdigest(), text),))
        result.update(outcome="passed", report=dataclasses.asdict(report))
    except Exception as error:
        result.update(outcome="failed", error=repr(error))
        raise
    finally:
        worker.close()
        Path(__file__).with_name("raw").joinpath("native-local-001.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
