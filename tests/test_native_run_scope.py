"""Current source intent preserves explicit native choices and refuses legacy scope shapes."""

import pytest
from pydantic import ValidationError

from corpus_structure.orchestrate.source_request import (
    NamedScope,
    SourceRunRequest,
    WholeDocument,
    source_selection,
)


@pytest.mark.parametrize(
    "legacy",
    [
        {"name": "trace", "locators": ["special/Normal.html#rel1"], "hash": "a" * 64},
        {"kind": "rendition", "name": "transfer", "locators": ["inspection.html"]},
        {"kind": "native_sections", "sections": ["Sets"]},
    ],
)
def test_current_source_intent_refuses_legacy_scope_payloads(legacy):
    with pytest.raises(ValidationError):
        SourceRunRequest.model_validate(
            dict(project_id="source", release_id="release", runtime_id="runtime", selection=legacy)
        )


@pytest.mark.parametrize("removed", ["scope_record", "registry", "graph", "fresh"])
def test_current_source_intent_refuses_removed_runtime_authority(removed):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SourceRunRequest.model_validate(
            dict(project_id="source", release_id="release", runtime_id="runtime", **{removed: {}})
        )


def test_current_source_intent_preserves_named_native_scope_and_whole_document():
    named = SourceRunRequest(
        project_id="source",
        release_id="release",
        runtime_id="runtime",
        selection=source_selection(scope="selected"),
        membership="descendants",
    )
    assert isinstance(named.selection, NamedScope) and named.selection.name == "selected"
    assert named.membership == "descendants"
    whole = named.model_copy(update={"selection": source_selection(whole_document=True)})
    assert isinstance(whole.selection, WholeDocument)
    assert named.selection.name == "selected"
