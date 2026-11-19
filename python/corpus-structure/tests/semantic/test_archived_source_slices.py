"""Archived pack selection survives edits and directory removal."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.orchestrate.source_request import SourceRequestError
from corpus_structure.semantic.regeneration import DOMAINS, acquire_pack, compose_pack_inputs
from corpus_structure.semantic.source_pack_inputs import PACK_BINDINGS, source_slices
from corpus_structure.semantic.types import SourceArtifact


def archived(*artifacts):
    return SimpleNamespace(
        artifacts=tuple(SourceArtifact(name, content) for name, content in artifacts)
    )


def test_source_selection_uses_captured_directory_binding_after_pack_removed(tmp_path):
    inputs = acquire_pack(DOMAINS / "statistics")
    pack = tmp_path / "operator-name"
    pack.mkdir()
    slices = pack / "slices.yaml"
    slices.write_text("default_scope: chosen\nslices: {chosen: [{native_sections: [Archived]}]}\n")
    dependencies = replace(
        inputs.dependencies,
        artifacts=(
            *(a for a in inputs.dependencies.artifacts if a.name != "operation/slices.yaml"),
            SourceArtifact("operation/slices.yaml", slices.read_bytes()),
        ),
    )
    inputs = replace(inputs, name=pack.name, dependencies=dependencies)
    _, dependencies, _ = compose_pack_inputs((inputs,))
    release = archived(*((a.name, a.content) for a in dependencies.artifacts))
    slices.write_text("default_scope: changed\nslices: {}\n")
    slices.unlink()
    pack.rmdir()
    assert source_slices(release, "operator-name") == {
        "default_scope": "chosen",
        "slices": {"chosen": [{"native_sections": ["Archived"]}]},
    }
    assert source_slices(release, None) == source_slices(release, "operator-name")
    with pytest.raises(SourceRequestError, match="archived source pack"):
        source_slices(release, "statistics")


def test_composed_source_pack_choice_and_missing_slices_are_explicit():
    bindings = json.dumps(
        [
            {"name": "left", "module": "semantic_left", "prefix": "pack/left/"},
            {"name": "right", "module": "semantic_right", "prefix": "pack/right/"},
        ]
    ).encode()
    release = archived(
        (PACK_BINDINGS, bindings), ("pack/left/operation/slices.yaml", b"default_scope: saved")
    )
    assert source_slices(release, "left") == {"default_scope": "saved"}
    assert source_slices(release, "right") == {}
    with pytest.raises(SourceRequestError, match="select one"):
        source_slices(release, None)


def test_older_unlabelled_single_pack_uses_only_omitted_selection():
    release = archived(("operation/slices.yaml", b"{}"))
    assert source_slices(release, None) == {}
    with pytest.raises(SourceRequestError):
        source_slices(release, "invented")


def test_older_composed_pack_names_exclude_source_language_question_inputs():
    release = archived(
        ("pack/actual-name/operation/methods.yaml", b"{}"),
        ("pack/actual-name/operation/slices.yaml", b"default_scope: saved"),
        ("pack/characterization/operation/interpretation-questions.yaml", b"{}"),
    )
    assert source_slices(release, "actual-name") == {"default_scope": "saved"}
    assert source_slices(release, None) == {"default_scope": "saved"}


@pytest.mark.parametrize("content", [b"[]", b"null", b"scalar"])
def test_non_mapping_archived_slice_input_refuses(content):
    with pytest.raises(SourceRequestError, match="mapping"):
        source_slices(archived(("operation/slices.yaml", content)), None)
