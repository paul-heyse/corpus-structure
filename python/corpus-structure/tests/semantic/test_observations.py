"""Source-report fidelity and identity, independent from admitted fact meaning."""

import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import BaseModel, JsonValue

from corpus_structure.core.method import ObservationDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
from corpus_structure.semantic import PreparedRelease, SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import (
    bind_result,
    observation_inputs,
    source_python,
    source_value,
)


def prepared():
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    )


def test_source_value_preserves_scalar_types_empty_containers_and_field_order():
    raw = {
        "absent_is_not_null": None,
        "integer": 2**100,
        "boolean": False,
        "negative_zero": -0.0,
        "text": "2",
        "array": [[], {}, {"β": "😀"}],
    }
    value = source_value(raw)
    assert value["fields"][1]["value"] == {"kind": "integer", "integer": 2**100}
    assert value["fields"][2]["value"] == {"kind": "boolean", "boolean": False}
    assert value["fields"][3]["value"] == {"kind": "float", "hexadecimal": "-0x0.0p+0"}
    restored = source_python(value)
    assert restored == raw
    assert list(restored) == list(raw)
    assert math.copysign(1.0, restored["negative_zero"]) == -1.0
    assert source_python(source_value({})) == {}


def test_source_tree_rejects_nonfinite_numbers_nonstring_fields_and_duplicate_names():
    with pytest.raises(ValueError, match="nonfinite"):
        source_value(float("nan"))
    with pytest.raises(TypeError, match="keys"):
        source_value({1: "not a string key"})
    with pytest.raises(ValueError, match="repeated"):
        source_python(
            {
                "kind": "object",
                "fields": [
                    {"name": "x", "position": 0, "value": {"kind": "null"}},
                    {"name": "x", "position": 1, "value": {"kind": "null"}},
                ],
            }
        )


def nested_source_detail() -> Mapping[str, JsonValue]:
    return {"nested": [{"Name": None, "name": False, "é": 1, "e\u0301": 2}]}


def malform_source_fields(fields, case):
    if case == "gap":
        fields[1]["position"] = len(fields)
    elif case == "order":
        fields[0], fields[1] = fields[1], fields[0]
    elif case == "repeat":
        # A duplicate with identical meaning would silently collapse in JSON aggregation.
        fields.append(dict(fields[0], position=len(fields)))


def test_source_tree_keeps_exact_field_names_and_explicit_null_false():
    detail = nested_source_detail()
    restored = source_python(source_value(detail))["nested"][0]
    assert list(restored) == ["Name", "name", "é", "e\u0301"]
    assert restored["Name"] is None and restored["name"] is False
    assert "absent" not in restored


@pytest.mark.parametrize("case", ("gap", "order", "repeat"))
def test_nested_source_object_refuses_malformed_fields(case):
    import json

    encoded = json.loads(json.dumps(source_value(nested_source_detail())))
    fields = encoded["fields"][0]["value"]["items"][0]["fields"]
    malform_source_fields(fields, case)
    with pytest.raises(ValueError, match=r"source report.*(ordered|repeated)"):
        source_python(encoded)


@pytest.mark.parametrize("position", (False, 0.0, "0"))
def test_source_object_position_requires_exact_integer(position):
    with pytest.raises(ValueError, match="contiguous and ordered"):
        source_python(
            {
                "kind": "object",
                "fields": [{"position": position, "name": "x", "value": {"kind": "null"}}],
            }
        )


@pytest.mark.parametrize(
    "encoded",
    (
        {"kind": "integer", "integer": False},
        {"kind": "integer", "integer": 1.0},
        {"kind": "boolean", "boolean": 0},
        {"kind": "float", "hexadecimal": "0x1p+0"},
    ),
)
def test_source_scalar_requires_declared_canonical_type(encoded):
    with pytest.raises(ValueError, match="source report"):
        source_python(encoded)


class Payload(BaseModel):
    text: str


def unit_result():
    draft = ObservationDraft(
        kind=ObservationKind.MENTION,
        payload=Payload(text="μ"),
        payload_class=Payload,
        payload_version="1",
        span=(4, 5),
    )
    return UnitResult(
        ref=UnitRef(TaskUnitType.SEGMENT, 99, "page#unit1"),
        outcome=ObservationOutcome.PRODUCED,
        observations=(draft, draft),
    )


def bind(
    release: PreparedRelease,
    *,
    input_hash: str = "input:1",
    invocation_key: str = "invocation:test",
    result: UnitResult | None = None,
    coverage: Sequence[Mapping[str, str]] = (),
):
    return bind_result(
        release,
        source="source:original-content",
        method="extract",
        operation_version="2",
        configuration_hash="config:1",
        input_hash=input_hash,
        invocation_key=invocation_key,
        result=unit_result() if result is None else result,
        coverage=coverage,
    ).model_dump(mode="python")


def test_binding_retains_repeated_items_and_replays_stable_keys():
    release = prepared()
    bound = bind(release)
    assert bound == bind(release)
    rows = bound["observations"]
    assert [row["item_key"] for row in rows] == ["mention/0", "mention/1"]
    assert len({row["observation_key"] for row in rows}) == 2
    assert [source_python(row["payload"]) for row in rows] == [{"text": "μ"}, {"text": "μ"}]
    assert [(row["span_start"], row["span_end"]) for row in rows] == [(4, 5), (4, 5)]
    fresh = bind(release, invocation_key="invocation:fresh")
    assert {r["observation_key"] for r in fresh["observations"]}.isdisjoint(
        r["observation_key"] for r in rows
    )
    changed = bind(release, input_hash="input:changed")
    assert changed["observations"][0]["observation_key"] != rows[0]["observation_key"]
    assert "SourceObservationBatch" in {definition.name for definition in release.definitions}


def test_coverage_is_explicit_and_not_inferred_from_empty_assertion_output():
    release = prepared()
    unit = UnitResult(
        ref=UnitRef(TaskUnitType.RENDITION, 4, "page"), outcome=ObservationOutcome.EMPTY
    )
    bound = bind(
        release,
        result=unit,
        coverage=(
            {
                "family": "math",
                "scope": "page#math1",
                "outcome": "partial",
                "reason": "ambiguous parse",
            },
        ),
    )
    assert bound["observations"] == ()
    assert bound["coverage"][0]["outcome"] == "partial"
    assert bound["outcome"] == "empty"


def test_bind_grouped_comparison_preserves_encoded_condition_fields():
    from corpus_structure.methods.structural_products import compare_clauses
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.semantic.structural_products import (
        DIMENSIONS,
        ClauseField,
        ClauseFieldGroup,
        ClauseReading,
    )

    from .test_typed_structural_composition import threshold_inputs

    inputs = threshold_inputs("If x > 2.", "If x > 5.")
    left, right = inputs.passages
    condition = {"kind": "escape", "text": left.text, "details": ["source limitation"]}
    fields = {dimension: ClauseFieldGroup(state="absent") for dimension in DIMENSIONS}
    fields["condition"] = ClauseFieldGroup(
        state="present",
        grouping="singleton",
        members=(
            ClauseField(
                dimension="condition",
                lexical_value=left.text,
                evidence=(left.passage_id,),
                condition=source_value(condition),
            ),
        ),
    )
    reference = RetainedContributionRef(
        contribution_id="source-contribution:" + "1" * 64,
        project_id="project",
        run_id=1,
        cut_id=1,
        release_id="release",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    report = compare_clauses(
        inputs,
        left=ClauseReading(passage_id=left.passage_id, groups=fields),
        right=ClauseReading(
            passage_id=right.passage_id,
            groups={dimension: ClauseFieldGroup(state="absent") for dimension in DIMENSIONS},
        ),
        left_reading=reference,
        right_reading=reference.model_copy(
            update={"contribution_id": "source-contribution:" + "2" * 64}
        ),
    )
    bound = bind_result(
        prepared(),
        source="source",
        method="structure.compare",
        operation_version="3",
        configuration_hash="config",
        input_hash="input",
        invocation_key="invocation",
        result=UnitResult(
            ref=UnitRef(TaskUnitType.RUN, unit_key=inputs.identity),
            outcome=ObservationOutcome.PRODUCED,
            structural_product=report.model_dump(mode="json"),
        ),
    ).model_dump(mode="json", exclude_none=True)
    dimension = next(
        item
        for item in bound["structural_product"]["comparison"]["dimensions"]
        if item["dimension"] == "condition"
    )
    assert source_python(dimension["left_group"]["members"][0]["condition"]) == condition


def test_structural_subtree_extension_uses_each_release_without_new_traversal():
    """An existing opaque producer subtree gains a nested contract through declarations."""
    import yaml
    from pydantic import ValidationError

    from corpus_structure.methods.structural_products import compare_clauses
    from corpus_structure.semantic.structural_products import ClauseReading

    from .test_structural_products import inputs

    model_path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"

    def boundary(minimum):
        schema = yaml.safe_load((model_path / "observations.yaml").read_bytes())
        schema["classes"]["DmcNestedDetail"] = {
            "attributes": {
                "values": {
                    "range": "integer",
                    "multivalued": True,
                    "required": True,
                    "minimum_value": minimum,
                }
            }
        }
        schema["classes"]["ContextualEnrichmentReport"]["attributes"]["extension"] = {
            "range": "DmcNestedDetail",
            "inlined": True,
            "required": True,
        }
        bundle = SourceBundle(
            "core", (SourceArtifact("core", (model_path / "core.yaml").read_bytes()),)
        )
        return prepare_release(
            observation_inputs(bundle, model_content=yaml.safe_dump(schema).encode())
        )

    looser, stricter = boundary(2), boundary(5)
    basis = inputs()
    product = compare_clauses(
        basis, left=ClauseReading(passage_id="a"), right=ClauseReading(passage_id="b")
    ).model_dump(mode="json")
    product["retrieval_report"] = {
        "version": "contextual-enrichment-2",
        "product_counts": dict(
            profiles=0, vectors=0, inventories=0, candidate_lists=0, relationship_decisions=0
        ),
        "extension": {"values": [3]},
    }

    def bind(release):
        return bind_result(
            release,
            source="source",
            method="structure.compare",
            operation_version="3",
            configuration_hash="configuration",
            input_hash="input",
            invocation_key="invocation",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.RUN, unit_key=basis.identity),
                outcome=ObservationOutcome.PRODUCED,
                structural_product=product,
            ),
        )

    assert bind(looser).model_dump(mode="python")["structural_product"]["retrieval_report"][
        "extension"
    ]["values"] == (3,)
    with pytest.raises(ValidationError) as failure:
        bind(stricter)
    location = failure.value.errors()[0]["loc"]
    assert location == ("retrieval_report", "extension", "values", 0)
    product["retrieval_report"]["extension"]["values"] = [7]
    assert bind(stricter).model_dump(mode="python")["structural_product"]["retrieval_report"][
        "extension"
    ]["values"] == (7,)
    product["retrieval_report"]["extension"]["values"] = [3]
    assert bind(looser).model_dump(mode="python")["structural_product"]["retrieval_report"][
        "extension"
    ]["values"] == (3,)
