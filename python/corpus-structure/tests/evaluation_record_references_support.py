"""Shared controlled inputs and builders for evaluation record references support."""

from copy import deepcopy
from dataclasses import replace
from functools import cache

from evaluation_record_alignment_support import MODEL, ROOT, frame, reading

from corpus_structure.evaluate.record_references import reference_inputs
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_contracts import interpretation_identity, record_identity


@cache
def prepared():
    return prepare_release(
        reference_inputs(
            observation_inputs(
                SourceBundle(
                    "statistics_semantic",
                    (
                        SourceArtifact(
                            "statistics_semantic",
                            (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                        ),
                        SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                        SourceArtifact(
                            "statistics_terminology",
                            (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                        ),
                    ),
                )
            )
        )
    )


def fixture(family="measurement"):
    row, contexts = reading(family)
    row = deepcopy(row)
    row["record_id"] = record_identity(prepared().release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    return row, contexts, replace(frame(row), release_id=prepared().release_id)
