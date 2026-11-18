"""Shared authored scenarios and fixtures for m1 declared products test support."""

from pathlib import Path

from statistics_pack_support import statistics_bundle

from corpus_structure.methods.m1_source import M1Config
from corpus_structure.semantic.m1_products import (
    m1_operation_sources,
)

ROOT = Path(__file__).resolve().parents[4]


def record_schemas():
    return statistics_bundle()


def configuration():
    from methods.domain_configuration import candidate_configuration

    return M1Config.model_validate(candidate_configuration(ROOT / "domains/statistics", "default"))


def sources():
    """Capture controlled provider metadata only; never acquire an executable model."""
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    config = configuration()
    selected = NativeSelection(
        NativeProfile(
            "spacy",
            {"fixture": "preparation"},
            {"files": {}},
            config.sentences.model_dump(mode="json"),
            "float32",
            "cupy",
        ),
        Path("."),
    )
    return m1_operation_sources(
        config, record_schemas=record_schemas(), sentence_selection=selected
    )
