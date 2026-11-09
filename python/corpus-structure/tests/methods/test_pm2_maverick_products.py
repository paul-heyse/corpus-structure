"""Maverick detection, membership and participant alternatives have distinct populations."""

from semantic.test_record_contracts import release_inputs

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.pm2_maverick_products import (
    LocalCluster,
    earlier_local_members,
    maverick_products,
)
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import PM2TokenMap, ProviderToken, SourceMapRefused
from corpus_structure.orchestrate.pm2_stage import _partition

from .test_pm2_source import identity_map


def test_maverick_retains_nested_and_unassigned_detection_independently_of_clusters():
    text = "Ada checks her chart. She files it."
    mapping = PM2TokenMap(
        identity_map(text),
        (
            ProviderToken("Ada", 0, 3, 0),
            ProviderToken("checks", 4, 10, 0),
            ProviderToken("her", 11, 14, 0),
            ProviderToken("chart", 15, 20, 0),
            ProviderToken(".", 20, 21, 0),
            ProviderToken("She", 22, 25, 1),
            ProviderToken("files", 26, 31, 1),
            ProviderToken("it", 32, 34, 1),
            ProviderToken(".", 34, 35, 1),
        ),
    )
    request = {"sentences": [["Ada", "checks", "her", "chart", "."], ["She", "files", "it", "."]]}
    reply = {
        "outcome": "succeeded",
        "tokens": [token.text for token in mapping.tokens],
        "mentions": [[0, 0], [2, 2], [2, 3], [3, 3], [5, 5], [7, 7], [4, 5]],
        "clusters": [[[0, 0], [2, 2], [5, 5]], [[2, 3], [7, 7]]],
    }
    product = maverick_products(mapping, request, reply)
    by_key = {row.key: row for row in product.products}
    assert by_key["mention:3:3"].value["clustered"] is False
    assert by_key["mention:2:3"].value["detected"] is True
    assert isinstance(product.locations["mention:4:5:extent"], SourceMapRefused)
    assert earlier_local_members(
        "mention:5:5", LocalCluster.model_validate(by_key["cluster:0"].value)
    ) == ("mention:0:0", "mention:2:2")

    profile = {"provider": "maverick"}
    question = PARSER_QUESTIONS["maverick"]
    dimensions = {"question": question, "operation_version": "1"}
    result = pm2_unit_result(
        UnitRef(TaskUnitType.SOURCE_VIEW, 1, "unit:1"),
        mapping,
        profile=profile,
        request=request,
        reply=reply,
        input_digest=pm2_input_digest(mapping, profile, request, **dimensions),
        prepared=release_inputs()[2],
        **dimensions,
    )
    assert result.contributions is not None
    rows = {row["item_key"]: row for row in result.contributions}
    assert rows["cluster:0"]["members"] == tuple(
        rows[key]["contribution_id"] for key in by_key["cluster:0"].members
    )
    assert rows["cluster:0"]["contract"] == "PM2MaverickClusterContributionV1"
    assert rows["mention:4:5"]["contract"] == "PM2MaverickMentionContributionV1"
    assert rows["mention:4:5"]["kind"] == "proposal"
    assert "occurrence_id" not in rows["mention:4:5"]

    paired = maverick_products(mapping, {**request, "predefined_mentions": [[2, 4]]}, reply)
    supplied = next(row for row in paired.products if row.key == "mention:2:4")
    assert supplied.value == dict(first=2, last=4, detected=False, supplied=True, clustered=False)


def test_limit_fallback_splits_only_at_owned_sentence_boundaries():
    bounds = [(1, 7), (8, 15), (16, 30), (31, 40)]
    assert _partition((1, 40), bounds) == ((1, 16), (16, 40))
    assert _partition((16, 30), bounds) == ()
