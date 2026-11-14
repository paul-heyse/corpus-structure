"""Explicit policy selection and unchanged phase0 dispatch, without database access."""

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "arguments, message",
    [
        (
            ["--extraction-policy", "m1-candidate"],
            (
                "M1 requires one exact retained integrated PDF product pin; "
                "conversion and fallback are disabled"
            ),
        ),
        (
            ["--m1-configuration", "described"],
            "nondefault M1 configuration requires the m1-candidate policy",
        ),
        (
            ["--extraction-policy", "m1-candidate", "--m1-configuration", "unknown"],
            (
                "Invalid value for '--m1-configuration': 'unknown' is not one of "
                "'default', 'described', 'readings', 'contextual', 'source-only'."
            ),
        ),
        (
            ["--integrated-product-task", "23"],
            "integrated product task, key and digest must be supplied together",
        ),
        (
            [
                "--integrated-product-task",
                "23",
                "--integrated-product-key",
                "integrated",
                "--integrated-product-digest",
                "bad",
            ],
            "product reference requires its SHA-256 content digest",
        ),
    ],
)
def test_refused_pin_never_opens_database(cli, monkeypatch, arguments, message):
    from corpus_structure.cli import orchestrate

    def forbidden(*args, **kwargs):
        pytest.fail("invalid explicit selection opened a database")

    monkeypatch.setattr(orchestrate, "ENGINE", forbidden)
    result = cli("run", *arguments)
    assert result.exit_code == 2
    assert message in " ".join(result.output.replace("│", "").split())


def test_contextual_policy_resolves_real_registry_and_keeps_reading_resolution():
    from corpus_structure.methods.m1_source import M1Config
    from corpus_structure.orchestrate.m1 import registry, source_graph

    root = Path(__file__).resolve().parents[4]
    selected = registry(root / "domains/statistics")
    cfg = selected.config("extract.m1_candidates", "contextual").config
    assert isinstance(cfg, M1Config)
    assert cfg.source_inspection and cfg.formula_prose
    assert cfg.profile().version == "gliner2-2.1.0-cuda-fp32-standard-whitespace-v1"
    assert (cfg.max_words, cfg.max_subwords) == (4096, 4096)
    assert (cfg.max_context_chars, cfg.max_context_pieces) == (4096, 128)
    steps = [step.config for _, stage in source_graph("contextual").stages for step in stage]
    assert steps == [
        "ingest.pdf_integrated/default",
        "extract.m1_annotations/default",
        "extract.m1_candidates/contextual",
        "resolve.m1_readings/default",
    ]
    assert not source_graph("contextual").policy_propose
