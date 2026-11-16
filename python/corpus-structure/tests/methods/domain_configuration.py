"""Typed authored configuration fixtures, independent of a runtime method catalog."""

from pathlib import Path

import yaml

from corpus_structure.methods.m1_source import M1Config


def candidate_configuration(domain: Path, name: str = "default") -> M1Config:
    values = yaml.safe_load((domain / "m1-methods.yaml").read_bytes())
    return M1Config.model_validate(values["configs"]["extract.m1_candidates"][name])
