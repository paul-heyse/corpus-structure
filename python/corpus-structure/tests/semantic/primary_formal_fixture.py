"""Shared prepared characterization schema for finite released-report fixtures."""
from functools import lru_cache
from pathlib import Path
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs

@lru_cache(maxsize=1)
def release():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )

