"""Shared controlled inputs and builders for evaluation characterization assessment native support."""

from corpus_structure.evaluate.record_references import reference_inputs
from corpus_structure.semantic.characterization import characterization_inputs


def characterization_references(bundle):
    return reference_inputs(characterization_inputs(bundle))
