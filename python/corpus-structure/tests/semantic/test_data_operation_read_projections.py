"""Compiler controls for projected reads and the separate exact role contract."""

from __future__ import annotations

import json

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import (
    PartitionHalo,
    ProjectedCollection,
    read_effective_data_operations,
)
from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle
from semantic.data_operation_declaration_support import contract, declarations, identity
from semantic.test_data_operation_partitions import _bundle


def _schema(*, unobserved: str = "string", observed: str = "integer") -> SourceBundle:
    original = _bundle().sources[0].content.decode()
    content = (
        original.replace(
            "      end: {range: integer, required: true}",
            f"      end: {{range: {observed}, required: true}}\n"
            f"      label: {{range: {unobserved}}}",
        )
        .replace(
            '["start","end"]}}',
            '["start","end"],"lexical":["label"]}}',
        )
        .replace(
            "    attributes:\n      tokens:",
            "    attributes:\n      source: {range: string}\n      coverage: {range: integer}\n"
            "      tokens:",
        )
    )
    return SourceBundle("sbx", (SourceArtifact("sbx", content.encode()),))


def _compile(projection=None, *, schema=None, output=False):
    authored = contract()
    role = authored["roles"][int(output)]
    role["kind"] = "Collection"
    if projection is not None:
        role["read_projection"] = projection
    return compile_data_operations(schema or _schema(), declarations(authored))


def _projection(model):
    return model.operations[0].roles[0].read_projection


def _whole(*, groups=None, header=None):
    return {
        "scope": "whole",
        "header": ["source", "coverage"] if header is None else header,
        "collections": [
            {"name": "tokens", "groups": ["geometry"] if groups is None else groups},
        ],
    }


def test_projection_compiles_typed_observations_and_preserves_existing_recipe():
    before = _compile()
    model = _compile(_whole())
    projection = _projection(model)
    assert projection is not None
    assert projection.version == 1
    assert projection.scope == "whole"
    assert projection.header == ("coverage", "source")
    assert projection.collections == (
        ProjectedCollection("tokens", ("geometry",), False, False, False),
    )
    assert projection.halo is None
    assert projection.fingerprint.startswith("input-read-projection:")
    assert identity(before) == identity(model)
    assert identity(before, domain="definition") != identity(model, domain="definition")
    assert _projection(read_effective_data_operations(model.content)) == projection
    assert _projection(read_effective_data_operations(before.content)) is None
    assert "read_projection" not in json.loads(before.content)["operations"][0]["roles"][0]
    assert {
        (edge.target, edge.role)
        for edge in model.edges
        if edge.relation == "projection-read" and edge.role == "tokens/geometry"
    } == {
        ("urn:sbx:Item/property/start", "tokens/geometry"),
        ("urn:sbx:Item/property/end", "tokens/geometry"),
        ("type:urn:sbx#integer", "tokens/geometry"),
    }


def test_identity_ignores_unobserved_fields_but_observes_declared_fields_and_layout():
    def fingerprint(model):
        projection = _projection(model)
        assert projection is not None
        return projection.fingerprint

    baseline = _compile(_whole())
    assert fingerprint(_compile(_whole(header=["coverage", "source"]))) == fingerprint(baseline)
    changed = _compile(_whole(), schema=_schema(unobserved="integer"))
    assert identity(changed) != identity(baseline)
    assert fingerprint(changed) == fingerprint(baseline)
    assert fingerprint(_compile(_whole(), schema=_schema(observed="string"))) != fingerprint(
        baseline
    )
    assert fingerprint(_compile(_whole(groups=["lexical"]))) != fingerprint(baseline)
    placed = _whole()
    placed["collections"][0]["placement"] = True
    assert fingerprint(_compile(placed)) != fingerprint(baseline)


def test_halo_compiles_as_a_distinct_bounded_partition_observation():
    authored = {
        "scope": "halo",
        "collections": [{"name": "tokens", "membership": True, "order": True}],
        "halo": {"before": 1, "after": 2},
    }
    projection = _projection(_compile(authored))
    assert projection is not None
    assert projection.halo == PartitionHalo(1, 2)
    assert projection.scope == "halo"
    assert projection.collections == (ProjectedCollection("tokens", (), True, True, False),)
    shifted = _projection(_compile({**authored, "halo": {"before": 2, "after": 1}}))
    assert shifted is not None and shifted.fingerprint != projection.fingerprint
    partition = _projection(
        _compile({"scope": "partition", "collections": authored["collections"]})
    )
    assert partition is not None and partition.halo is None
    assert partition.fingerprint != projection.fingerprint


@pytest.mark.parametrize(
    ("data", "diagnostic"),
    [
        (_whole(groups=["unknown"]), "distinct declared groups"),
        (_whole(groups=["geometry", "geometry"]), "distinct declared groups"),
        (_whole(header=["unknown"]), "owned property"),
        (_whole(header=["tokens"]), "nonpartition fields"),
        ({"scope": "partition", "header": ["source"]}, "requires a partition collection"),
        (
            {**_whole(), "scope": "halo", "halo": {"before": 1, "after": 0}},
            "must observe partition order",
        ),
        ({**_whole(), "halo": {"before": 1, "after": 0}}, "requires halo scope"),
    ],
)
def test_invalid_observations_refuse_compilation(data, diagnostic):
    with pytest.raises(PreparationError, match=diagnostic):
        _compile(data)


def test_projection_cannot_be_declared_on_an_output():
    with pytest.raises(PreparationError, match="belong to input roles"):
        _compile(_whole(), output=True)
