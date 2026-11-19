"""Current private record schema placement, independent of old run/publication fixtures."""

from importlib.resources import files

import pytest
import yaml

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.record_contracts import record_product_classes
from corpus_structure.semantic.releases import _projection_rows
from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle
from semantic.record_contracts_support import PIN, release_inputs


def test_private_record_products_keep_schema_and_exclude_ordinary_graph_projection():
    prepared = release_inputs()[2]
    products = record_product_classes(prepared.definitions)
    assert products
    private = {prepared.index.definitions[name].iri for name in products}
    rows = _projection_rows(prepared)
    assert private <= {row["class_id"] for row in rows["class_definition"]}
    for name in (
        "property_applicability",
        "identity_slot",
        "operation_property_role",
        "conditional_rule",
    ):
        assert not private & {row["class_id"] for row in rows[name]}
    entity = prepared.index.definitions["Entity"].iri
    assert any(row["class_id"] == entity for row in rows["property_applicability"])
    assert any(
        row["class_id"] == entity and row["role"] == "identity"
        for row in rows["operation_property_role"]
    )
    prepared.validate_json("RecordSourcePin", canonical_bytes(PIN))
    with pytest.raises(ValueError):
        prepared.validate_json(
            "RecordSourcePin", canonical_bytes({**PIN, "projection_digest": "not-a-digest"})
        )
    with pytest.raises(ValueError):
        prepared.validate_json("RecordSourcePin", canonical_bytes({**PIN, "source_view_id": 17}))


@pytest.mark.parametrize("inlined", [True, False])
def test_ordinary_graph_properties_cannot_range_into_private_record_products(inlined):
    schema = dict(
        id="https://example/graph-range",
        name="graph_range",
        imports=["core"],
        classes={
            "GraphRecord": dict(attributes={"pin": dict(range="RecordSourcePin", inlined=inlined)})
        },
    )
    bundle = observation_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact(
                    "core",
                    files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
                ),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        )
    )
    with pytest.raises(PreparationError, match="cannot range into a private record product"):
        prepare_release(bundle)
