"""Captured native rendering and independent frozen-program parity."""

import os

import pytest

from corpus_structure.semantic.types import SourceArtifact


def test_generator_identity_carries_checked_native_codec_capabilities():
    from corpus_structure.semantic.native_program_store import capture_generator_code

    identity = capture_generator_code()
    profiles = {item.reference: item for item in identity.external_runtime}
    assert {"rapidjson", "decimal", "hashlib", "datetime"} <= profiles.keys()
    assert all(item.files and item.symbols for item in profiles.values())
    for item in profiles.values():
        item.check()


def test_generator_capture_rechecks_cached_runtime_bindings(monkeypatch):
    import rapidjson

    from corpus_structure.semantic.native_program_store import capture_generator_code

    identity = capture_generator_code()
    assert any(item.reference == "rapidjson" for item in identity.external_runtime)
    monkeypatch.setattr(rapidjson, "dumps", lambda *args, **kwargs: "null")
    with pytest.raises(ValueError, match=r"external codec symbol was replaced: rapidjson\.dumps"):
        capture_generator_code()


@pytest.mark.parametrize("selection", ("default", "actions", "supplied", "codec"))
def test_renderer_receives_the_captured_interpretation_after_acquisition(monkeypatch, selection):
    from contextlib import contextmanager

    from corpus_structure.model.compiled import running_model
    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic import (
        native_generation,
        native_program_store,
        pdf_domain,
        target_installation,
    )
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.native_protocol_authoring import native_logical_sources
    from corpus_structure.semantic.value_codec import decimal_digit_limit

    current = get_metadata()
    selected = compile_physical(
        dict(current.info["physical_sources"]),
        linkml_types=current.info["physical_linkml_types"],
    )
    cohort = (SourceArtifact("pdf-domain/controlled-cohort", b"prepared sources"),)
    action = SourceArtifact("pdf-domain/native/actions.yaml", b"captured actions")
    logical = native_logical_sources(model_sources=dict(running_model().sources))
    if selection == "codec":
        old_limit = decimal_digit_limit()
        logical["value-codec.yaml"] = logical["value-codec.yaml"].replace(
            str(old_limit).encode(), b"43"
        )
    inputs = native_generation.capture_generator_inputs(
        selected,
        pdf_actions=action if selection == "actions" else None,
        pdf_sources=cohort if selection == "supplied" else None,
        logical_sources=logical if selection in {"supplied", "codec"} else None,
    )
    selected.info["unmodeled_shared_state"] = "must not enter rendering"
    observed = []
    phases = []
    actual_custody = native_program_store.capture_generator_custody

    @contextmanager
    def custody(identity, *, closed=False):
        assert closed
        with actual_custody(identity, closed=closed):
            phases.append("entered")
            yield
            phases.append("verified")

    def prepare(**kwargs):
        assert phases == ["entered"]
        assert selection != "supplied", "an explicit cohort must bypass PDF preparation"
        assert kwargs["physical_sources"] == dict(inputs.physical_sources)
        assert kwargs["linkml_types"] == inputs.linkml_types
        assert kwargs["model_sources"] == dict(inputs.model_sources)
        assert kwargs["analysis_versions"] == inputs.analysis_runtime
        assert kwargs["include_producer"] is False
        expected_action = (
            action
            if selection == "actions"
            else SourceArtifact(
                "pdf-domain/native/actions.yaml", dict(inputs.logical_sources)["pdf-actions.yaml"]
            )
        )
        assert kwargs["actions_source"] == expected_action
        return cohort

    def inspect(captured, *, target_metadata, pdf_sources, decimal_digits):
        assert phases == ["entered"]
        assert captured is inputs
        assert pdf_sources is cohort
        assert target_metadata is not selected
        assert "unmodeled_shared_state" not in target_metadata.info
        assert set(target_metadata.tables) == set(selected.tables)
        assert target_metadata.info["physical_sources"] == dict(inputs.physical_sources)
        assert target_metadata.info["physical_linkml_types"] == inputs.linkml_types
        assert dict(running_model().sources) == dict(inputs.model_sources)
        from corpus_structure.semantic.value_codec import decimal_digit_limit

        assert decimal_digits == (43 if selection == "codec" else decimal_digit_limit())
        observed.append(target_metadata)

    monkeypatch.setattr(target_installation, "render_target_installation", inspect)
    monkeypatch.setattr(pdf_domain, "pdf_domain_sources", prepare)
    monkeypatch.setattr(native_program_store, "capture_generator_custody", custody)
    native_generation._render_captured(inputs)
    assert len(observed) == 1
    assert phases == ["entered", "verified"]


def test_installed_native_candidate_matches_frozen_programs_in_fresh_offline_processes(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    from corpus_structure.semantic.execution_admission import _revision_expectation
    from corpus_structure.semantic.migrations import ALEMBIC_DIR, head_revision
    from corpus_structure.semantic.native_authoring import load_native_state

    root = Path(__file__).resolve().parents[4]
    predecessor = head_revision()
    assert predecessor is not None
    frozen = _revision_expectation(ALEMBIC_DIR / "versions", predecessor)
    state_path, state_digest = frozen.state
    object_count = len(load_native_state(state_path, digest=state_digest))
    unavailable = "postgresql+psycopg://paul@127.0.0.1:1/corpus_d2_offline?connect_timeout=1"
    environment = os.environ | {
        **{
            "CORPUS_DATABASE__" + purpose: unavailable
            for purpose in (
                "URL",
                "MAINTENANCE_URL",
                "READER_URL",
                "EVALUATOR_URL",
                "ADMISSION_URL",
            )
        },
    }
    script = """
import json
import os
import sys
from pathlib import Path

counts = {"render": 0}
def observe(frame, event, arg):
    if event != "call":
        return
    module = frame.f_globals.get("__name__")
    if module == "corpus_structure.semantic.target_installation" and frame.f_code.co_name == "render_target_installation":
        counts["render"] += 1

sys.setprofile(observe)
try:
    from corpus_structure.cli.app import main
    main()
finally:
    sys.setprofile(None)
    Path(os.environ["NATIVE_GENERATOR_COUNTS"]).write_text(json.dumps(counts))
"""
    command = [
        sys.executable,
        "-c",
        script,
        "schema",
        "native-candidate",
        "--expected-predecessor",
        predecessor,
        "--json",
    ]

    def invoke(ordinal):
        count_path = tmp_path / f"counts-{ordinal}.json"
        reply = subprocess.run(
            command,
            cwd=root,
            env=environment | {"NATIVE_GENERATOR_COUNTS": str(count_path)},
            capture_output=True,
            check=False,
            text=True,
            timeout=300,
        )
        assert reply.returncode == 0, reply.stdout + reply.stderr
        return json.loads(reply.stdout), json.loads(count_path.read_text())

    first, first_counts = invoke(1)
    second, second_counts = invoke(2)

    assert first["outcome"] == second["outcome"] == "no_native_change"
    assert first["head_revision"] == second["head_revision"] == predecessor
    assert first["object_count"] == second["object_count"] == object_count
    assert first["kernel_identity"] == second["kernel_identity"]
    observations = {
        "first": first_counts,
        "second": second_counts,
        "native_results": (first, second),
    }
    assert first_counts == second_counts == {"render": 1}, observations
