"""Independent score codec/ranking controls; controlled rows carry no native standing."""

import struct
from copy import deepcopy
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.contextual_numerics import default_retrieval_numerics
from corpus_structure.semantic.contextual_operations import prepare_contextual_retrieval
from corpus_structure.semantic.contextual_scores import candidates_from_scores, score_product
from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
from corpus_structure.semantic.observations import source_python, source_value
from semantic.test_declared_contextual_operations import inputs
from semantic.contextual_linguistic_support import linguistic_observation


def controlled_scores():
    values = inputs()
    acquired = prepare_contextual_retrieval(**values)
    rows = [
        SimpleNamespace(kind="membership", target_id=target, channel=None, rank=None, score=None)
        for target in ("one", "two")
    ]
    for channel, scores in (
        ("alias", (1.0, 1.0)),
        ("dense", (1.0, 0.0)),
        ("lexical", (0.10000000149011612, 0.10000000149011612)),
    ):
        rows.extend(
            SimpleNamespace(kind="hit", channel=channel, target_id=target, rank=rank, score=score)
            for rank, (target, score) in enumerate(zip(("one", "two"), scores, strict=True), 1)
        )
    return values, acquired, score_product(acquired, values["query"], rows, linguistic_observation=linguistic_observation())


def test_score_product_keeps_exact_float8_bits_and_independent_rrf_order():
    values, acquired, scores = controlled_scores()
    assert scores["membership"] == ["one", "two"]
    assert scores["hits"][4]["score_float8_hex"] == "3fb99999a0000000"
    actual = candidates_from_scores(
        acquired,
        scores,
        values["query"],
        values["policy"],
        numerical_policy=default_retrieval_numerics(),
    )
    assert [(hit.target_id, hit.rank, hit.fusion_score) for hit in actual.candidates] == [
        ("one", 1, 3 / 61),
        ("two", 2, 3 / 62),
    ]
    assert [
        hit.score
        for channel in actual.channel_results
        if channel.channel == "lexical"
        for hit in channel.hits
    ] == [0.10000000149011612, 0.10000000149011612]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "foreign",
        "profile",
        "query",
        "inventory",
        "rank",
        "channel",
        "order",
        "nonfinite",
        "encoding",
        "extra",
    ],
)
def test_cpu_reduction_refuses_changed_native_score_correspondence(change):
    values, acquired, scores = controlled_scores()
    if change == "missing":
        scores["membership"].pop()
    elif change == "duplicate":
        scores["membership"].append("two")
    elif change == "foreign":
        scores["hits"][0]["target_id"] = "foreign"
    elif change == "profile":
        scores["profile_id"] = "another-profile"
    elif change == "query":
        scores["query_vector_id"] = "another-query-vector"
    elif change == "inventory":
        scores["inventory_id"] = "another-inventory"
    elif change == "rank":
        scores["hits"][0]["rank"] = 2
    elif change == "channel":
        scores["hits"][0]["channel"] = "approximate"
    elif change == "order":
        scores["hits"].reverse()
    elif change == "nonfinite":
        scores["hits"][0]["score_float8_hex"] = struct.pack(">d", float("nan")).hex()
    elif change == "encoding":
        scores["hits"][0]["score_float8_hex"] = "3FB99999A0000000"
    else:
        scores["invented"] = "provenance"
    with pytest.raises(ValueError):
        candidates_from_scores(
            acquired,
            scores,
            values["query"],
            values["policy"],
            numerical_policy=default_retrieval_numerics(),
        )


@pytest.mark.parametrize("change", ["missing-observation", "unknown-material", "provider-version", "old-version"])
def test_score_consumer_requires_current_closed_linguistic_observation(change):
    values, acquired, scores = controlled_scores()
    observation = source_python(scores["linguistic_observation"])
    if change == "missing-observation":
        del scores["linguistic_observation"]
    elif change == "old-version":
        scores["version"] = "contextual-native-scores-1"
    else:
        if change == "unknown-material":
            observation["unobserved_material"]["libc_build"] = "complete-fingerprint"
        else:
            observation["database_locale"].update(recorded_provider_version="one", actual_provider_version="two")
        scores["linguistic_observation"] = source_value(observation)
    with pytest.raises(ValueError):
        candidates_from_scores(acquired, scores, values["query"], values["policy"], numerical_policy=default_retrieval_numerics())


def test_lexical_projection_keeps_python_unicode_and_rejects_invented_forms():
    values = inputs()
    rows = source_python(values["vectors"]["lexical_targets"])
    assert rows[0] == dict(target_id="one", search_text="alpha alpha one", exact_forms=["alpha"])
    changed = deepcopy(rows)
    changed[0]["exact_forms"] = ["another-label"]
    values["vectors"]["lexical_targets"] = source_value(changed)
    with pytest.raises(ValueError, match="lexical targets"):
        prepare_contextual_retrieval(**values)


def test_lexical_projection_retains_exact_python_unicode_case_semantics():
    from corpus_structure.semantic.contextual_retrieval import (
        freeze_inventory,
        target_representation,
    )
    from corpus_structure.semantic.contextual_storage import lexical_target_rows

    selected = freeze_inventory(
        (target_representation("unicode", "curated-source", "İ", "Meaning", aliases=("ẞ",)),),
        source_selection="unicode-input",
        scope="global",
    )
    assert lexical_target_rows(selected) == (
        dict(target_id="unicode", search_text="İ Meaning ẞ", exact_forms=["i\u0307", "ß"]),
    )


def test_score_product_is_valid_under_its_current_nominal_contract():
    from pathlib import Path

    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.contextual_operations import (
        contextual_inputs,
        contextual_operation_declarations,
        contextual_operation_sources,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
    )

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        contextual_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        data_operation_dependencies(
            ResolvedDependencies(),
            declarations=(
                contextual_operation_declarations(),
                structural_operation_declarations(),
            ),
            python_sources=contextual_operation_sources(),
        ),
        PreparationProfile(version="semantic-2"),
    )
    _, _, scores = controlled_scores()
    actual = prepared.validate_json("DdoContextualNativeScores", json_bytes(scores)).model_dump(
        mode="python", exclude_unset=True
    )
    assert json_bytes(actual) == json_bytes(scores)
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from semantic.test_contextual_witnesses import project, witness_case

    frame, context, roles, _ = witness_case()
    bindings = project(frame, context, roles)
    actual_bindings = prepared.validate_json("DdoContextualWitnessBindings", json_bytes(bindings))
    assert json_bytes(actual_bindings.model_dump(mode="python", exclude_unset=True)) == json_bytes(
        bindings
    )
    model = bound_data_operation_model(prepared)
    producer = model.operation("retrieve.contextual_witnesses/declared")
    consumer = model.operation("retrieve.contextual/with-witnesses")
    assert producer.capabilities.forms == ("scalar",)
    assert {role.name for role in producer.roles if role.direction == "input"} == {
        "source",
        "query",
        "inventory",
        "hypotheses",
        "cues",
    }
    assert "witnesses" in {role.name for role in consumer.roles if role.direction == "input"}
