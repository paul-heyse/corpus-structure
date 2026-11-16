"""Real local library/model control, explicitly without external provider qualification."""

import pytest


@pytest.fixture(scope="module")
def controlled_selection(tmp_path_factory):
    from semantic.current_contextual_support import controlled_encoder

    directory = tmp_path_factory.mktemp("controlled-model")
    return directory, controlled_encoder(directory / "encoder")


def test_controlled_model_uses_actual_profile_tokenizer_pooling_and_assets(controlled_selection):
    from corpus_structure.methods.contextual_embeddings import ContextInput, encode_contexts

    _, selected = controlled_selection
    result = encode_contexts(
        (
            ContextInput(
                "target",
                "controlled-curated-source",
                "document",
                "Ada",
                "Ada acts",
                0,
                3,
                representation_digest="controlled-description",
            ),
        ),
        selected.profile,
        model_path=str(selected.model_path),
        artifact_hashes=selected.artifacts,
        check_active=lambda: None,
    )
    assert len(result.vectors) == len(result.inputs) == 1
    assert result.vectors[0].object_id == "target"
    assert len(result.vectors[0].values) == 8
    assert result.inputs[0].text == "Mention: Ada\nType: unknown\nContext: Ada acts"
    assert (
        dict(result.implementation)["sentence_transformers"]
        == selected.profile.sentence_transformers_version
    )


def test_current_contextual_fixture_captures_actual_source_and_complete_scalar_consumers(
    controlled_selection,
):
    from semantic.current_contextual_support import contextual_recipe
    from semantic.data_operation_kernel_support import prepare_kernel

    directory, encoder = controlled_selection
    compiled = directory / "prepared"
    compiled.mkdir()
    prepared = prepare_kernel(contextual_recipe(directory, encoder), directory=compiled)
    assert all(item.complete for item in prepared.model.implementation_slices), [
        (item.root, item.unknowns)
        for item in prepared.model.implementation_slices
        if not item.complete
    ]
    for operation in (
        "fixture.structural_inventory",
        "retrieve.contextual_query/declared",
        "retrieve.contextual_target_vector/declared",
        "retrieve.contextual_vectors/selection",
        "retrieve.contextual_scores/declared",
        "retrieve.contextual/declared",
    ):
        assert prepared.model.operation(operation).capabilities.prepared_factory is not None
    assert prepared.model.operation(
        "retrieve.contextual_target_vector/declared"
    ).capabilities.forms == ("scalar",)
