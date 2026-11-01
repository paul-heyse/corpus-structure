"""Independent native examples, presence and artifact/native correspondence checks."""

import copy
import json
import math
from hashlib import sha256

import pytest

from corpus_structure.semantic.pdf_record_identity import (
    ScalarDescriptor,
    byte_root,
    describe_scalar,
)
from corpus_structure.semantic.pdf_records import (
    NativeMappingError,
    NativeRow,
    iter_native_records,
    native_record_identity_fields,
    native_schema_bytes,
    prepare_native_schema_mapping,
    reconstruct_native_document,
    validate_native_callbacks,
)


def occurrence_id(address, native_type):
    # Test fixture's stable occurrence inventory. Production producers allocate occurrence IDs.
    return sha256((native_type + ":" + address).encode()).hexdigest()


class Records:
    def __init__(self):
        self.rows = []
        self.streams = {}
        self.profiles = {}
        self.descriptors = {}

    def write(self, stream_id, encoding_profile, chunks):
        stream, profile = stream_id, encoding_profile
        data = tuple(chunks)
        if stream in self.streams:
            assert self.streams[stream] == data
        assert all(len(c) <= 65_536 for c in data)
        self.streams[stream] = data
        self.profiles[stream] = profile
        size, root = byte_root(data)
        descriptor = ScalarDescriptor(
            b"y" if profile == "pdf-record-native-json-v1" else profile[-1:].encode(), size, root
        )
        self.descriptors[stream] = descriptor
        return descriptor

    def record(self, record_id):
        matches = [
            r.values for r in self.rows if r.kind == "native" and r.values["record_id"] == record_id
        ]
        assert len(matches) == 1
        return matches[0]

    def members(self, parent_id, field_name):
        return (
            r.values
            for r in self.rows
            if r.kind == "membership"
            and r.values["parent_id"] == parent_id
            and r.values["field_name"] == field_name
        )

    def scalar(self, stream):
        return self.streams[stream]

    def lower(self, value, *, native_type="DoclingDocument", product_id="p", revision_id="r"):
        self.rows = list(
            iter_native_records(
                value,
                product_id=product_id,
                revision_id=revision_id,
                release_id="release",
                source_digest="a" * 64,
                record_id_for=occurrence_id,
                write_scalar=self.write,
                native_type=native_type,
            )
        )
        return self

    def reconstruct(self, native_type="DoclingDocument"):
        return reconstruct_native_document(
            self,
            occurrence_id("#", native_type),
            scalar_profiles=self.profiles,
            native_type=native_type,
        )


def text(index, label="text", **extra):
    return {
        "self_ref": f"#/texts/{index}",
        "label": label,
        "orig": f"original {index}",
        "text": f"text {index}",
        **extra,
    }


def complete_fixture():
    # Independently authored expected values. No Docling producer/model/export supplies them.
    return {
        "schema_name": "DoclingDocument",
        "version": "1.10.0",
        "name": "All collections",
        "origin": {
            "mimetype": "application/pdf",
            "binary_hash": 17,
            "filename": "input.pdf",
            "uri": None,
        },
        "furniture": {"self_ref": "#/furniture", "name": "furniture", "children": []},
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/texts/0"}, {"$ref": "#/tables/0"}, {"$ref": "#/groups/0"}],
        },
        "groups": [
            {
                "self_ref": "#/groups/0",
                "label": "list",
                "parent": {"$ref": "#/body"},
                "children": [{"$ref": "#/texts/1"}],
            }
        ],
        "texts": [
            text(
                0,
                parent={"$ref": "#/body"},
                comments=[{"$ref": "#/texts/1", "range": [0, 2]}],
                prov=[
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": -0.0,
                            "t": 3.5,
                            "r": 10.25,
                            "b": 13.0,
                            "coord_origin": "TOPLEFT",
                        },
                        "charspan": [0, 6],
                    }
                ],
                meta={"summary": None, "custom": {"exact": ["00.100", None, False], "empty": []}},
            ),
            text(1, "list_item", parent={"$ref": "#/groups/0"}, enumerated=True, marker="2."),
            text(2, "formula"),
            text(3, "code", code_language="Python"),
            text(4, "section_header", level=2),
            text(5, "title"),
            text(6, "field_heading"),
            text(7, "field_value", kind="fillable"),
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "label": "picture",
                "image": {
                    "mimetype": "image/png",
                    "dpi": 72,
                    "size": {"width": 1.0, "height": 2.0},
                    "uri": "data:image/png;base64,AA==",
                },
                "annotations": [
                    {
                        "kind": "molecule_data",
                        "smi": "CC",
                        "confidence": 0.2,
                        "class_name": "small",
                        "segmentation": [[1.0, 2.0], [3.0, 4.0]],
                        "provenance": "p",
                    },
                    {"kind": "misc", "content": {"opaque": [{"keep": "value"}]}},
                ],
            }
        ],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "parent": {"$ref": "#/body"},
                "children": [{"$ref": "#/texts/0"}],
                "data": {
                    "num_rows": 1,
                    "num_cols": 2,
                    "table_cells": [
                        {
                            "start_row_offset_idx": 0,
                            "end_row_offset_idx": 1,
                            "start_col_offset_idx": 0,
                            "end_col_offset_idx": 1,
                            "text": "1.2300",
                        },
                        {
                            "start_row_offset_idx": 0,
                            "end_row_offset_idx": 1,
                            "start_col_offset_idx": 1,
                            "end_col_offset_idx": 2,
                            "text": "rich",
                            "ref": {"$ref": "#/texts/0"},
                        },
                    ],
                },
            }
        ],
        "key_value_items": [
            {
                "self_ref": "#/key_value_items/0",
                "graph": {
                    "cells": [
                        {"label": "key", "cell_id": 10, "text": "K", "orig": "K"},
                        {"label": "value", "cell_id": 20, "text": "V", "orig": "V"},
                    ],
                    "links": [
                        {"label": "to_value", "source_cell_id": 10, "target_cell_id": 20},
                        {"label": "to_value", "source_cell_id": 10, "target_cell_id": 20},
                    ],
                },
            }
        ],
        "form_items": [{"self_ref": "#/form_items/0", "graph": {"cells": [], "links": []}}],
        "field_regions": [{"self_ref": "#/field_regions/0", "label": "field_region"}],
        "field_items": [{"self_ref": "#/field_items/0", "label": "field_item"}],
        "pages": {"1": {"page_no": 1, "size": {"width": 200.0, "height": 300.0}, "image": None}},
    }


def test_decoded_reconstruction_preserves_json_looking_strings_null_and_binary64():
    expected = complete_fixture()
    expected["texts"][0]["text"] = "null"
    records = Records().lower(expected)
    decoded = []
    for row in records.rows:
        body = dict(row.values)
        for field in ("scalars_json", "structure_json", "scalar_json"):
            if field in body and body[field] is not None:
                body[field] = json.loads(body[field])
        decoded.append(NativeRow(row.kind, body))
    records.rows = decoded
    actual = reconstruct_native_document(
        records,
        occurrence_id("#", "DoclingDocument"),
        scalar_profiles=records.profiles,
        json_fields="decoded",
    )
    assert actual == expected
    assert actual["texts"][0]["text"] == "null"
    assert actual["origin"]["uri"] is None
    assert math.copysign(1.0, actual["texts"][0]["prov"][0]["bbox"]["l"]) == -1.0


def test_total_field_categories_rich_cells_parallel_links_and_exact_order():
    expected = complete_fixture()
    records = Records().lower(expected)
    assert records.reconstruct() == expected
    rows = [r.values for r in records.rows if r.kind == "native"]
    assert {
        "DoclingDocument",
        "ProvenanceItem",
        "RichTableCell",
        "TableCell",
        "FineRef",
        "NativeArray",
        "GraphLink",
        "FieldRegionItem",
        "FieldItem",
        "KeyValueItem",
        "FormItem",
    } <= {r["native_type"] for r in rows}
    links = [r for r in rows if r["native_type"] == "GraphLink"]
    assert len(links) == 2 and links[0]["record_id"] != links[1]["record_id"]
    refs = [r for r in records.rows if r.kind == "reference"]
    assert len(refs) >= 10
    bbox = records.reconstruct()["texts"][0]["prov"][0]["bbox"]
    assert math.copysign(1.0, bbox["l"]) == -1.0
    for r in rows:
        assert len(r["scalars_json"].encode()) <= 65_536
        assert len(r["structure_json"].encode()) <= 65_536


@pytest.mark.parametrize("value", [None, [], {}, {"x": []}, {"a": 1, "b": False}])
def test_explicit_extensions_are_lossless(value):
    expected = {"name": "extensions", "body": {"self_ref": "#/body", "meta": {"vendor": value}}}
    assert Records().lower(expected).reconstruct() == expected


def test_absent_null_empty_and_explicit_default_are_distinct():
    cases = [
        {"name": "x"},
        {"name": "x", "origin": None},
        {"name": "x", "texts": []},
        {"name": "x", "version": "1.10.0"},
    ]
    rows = [Records().lower(value) for value in cases]
    assert [r.reconstruct() for r in rows] == cases
    scalars = [r.record(occurrence_id("#", "DoclingDocument"))["scalars_json"] for r in rows]
    assert len(set(scalars)) == 3  # empty texts is a structural presence marker
    assert (
        rows[0].record(occurrence_id("#", "DoclingDocument"))["structure_json"]
        != rows[2].record(occurrence_id("#", "DoclingDocument"))["structure_json"]
    )


def test_huge_scalar_nul_and_opaque_extension_have_bounded_parts():
    huge = "\u03b1\x00\U0001d6cc" * 100_000
    expected = {
        "name": "large",
        "texts": [text(0, text=huge, orig="a\x00b", meta={"nul\x00key": {"large": huge}})],
    }
    records = Records().lower(expected)
    assert records.reconstruct() == expected
    assert len(records.streams) == 3
    assert all("\\u0000" not in r.values.get("scalars_json", "") for r in records.rows)


def test_map_keys_and_native_address_overflow_reconstruct_exactly():
    key = "1" * 1024 + "\x00"
    value = {"name": "key", "pages": {key: {"page_no": 1, "size": {"width": 1, "height": 2}}}}
    records = Records().lower(value)
    assert records.reconstruct() == value
    assert any("member_key_stream_id" in r.values for r in records.rows)
    assert any("native_address_stream_id" in r.values for r in records.rows)


def test_unknown_native_field_and_schema_drift_refuse_precisely():
    with pytest.raises(NativeMappingError, match="#/unknown: unsupported native field"):
        Records().lower({"name": "x", "unknown": 17})
    schema = json.loads(native_schema_bytes())
    schema["properties"]["unknown"] = {"type": "string"}
    with pytest.raises(
        NativeMappingError, match="#/properties/unknown: unsupported native schema change"
    ):
        prepare_native_schema_mapping(json.dumps(schema).encode())
    schema = json.loads(native_schema_bytes())
    schema["$defs"]["Size"]["properties"]["width"]["minimum"] = 123
    with pytest.raises(NativeMappingError, match="minimum: unsupported native schema change"):
        prepare_native_schema_mapping(json.dumps(schema).encode())
    with pytest.raises(NativeMappingError, match="not of type"):
        Records().lower({"name": 12})


def test_reconstruction_inventory_and_containment_tampering_refuse():
    records = Records().lower({"name": "x", "texts": [text(0), text(1)]})
    records.rows = [
        r for r in records.rows if not (r.kind == "membership" and r.values["ordinal"] == 0)
    ]
    with pytest.raises(NativeMappingError, match="membership"):
        records.reconstruct()
    records = Records().lower({"name": "x"})
    row = records.record(occurrence_id("#", "DoclingDocument"))
    row["native_type"] = "TableCell"
    with pytest.raises(NativeMappingError, match="requested native root class differs"):
        records.reconstruct()


def test_callback_validation_keeps_unset_defaults_and_never_mutates_input():
    value = {"name": "small", "body": {"self_ref": "#/body", "children": []}}
    original = copy.deepcopy(value)
    validate_native_callbacks(value)
    assert value == original


def test_native_callback_version_rewrite_is_a_refusal():
    value = {"name": "old", "version": "1.9.0"}
    with pytest.raises(NativeMappingError, match="#/version: native callbacks changed"):
        validate_native_callbacks(value)
    assert value == {"name": "old", "version": "1.9.0"}


def test_native_callback_bbox_clamp_is_a_refusal():
    value = {
        "name": "bbox",
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
        "texts": [
            text(
                0,
                parent={"$ref": "#/body"},
                prov=[
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": -4.0,
                            "t": 1.0,
                            "r": 10.0,
                            "b": 11.0,
                            "coord_origin": "TOPLEFT",
                        },
                        "charspan": [0, 2],
                    }
                ],
            )
        ],
        "pages": {"1": {"page_no": 1, "size": {"width": 100.0, "height": 100.0}}},
    }
    original = copy.deepcopy(value)
    with pytest.raises(NativeMappingError, match="native callbacks changed"):
        validate_native_callbacks(value)
    assert value == original


def test_native_callback_list_repair_is_a_refusal():
    value = {
        "name": "list",
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
        "texts": [text(0, "list_item", parent={"$ref": "#/body"})],
    }
    original = copy.deepcopy(value)
    with pytest.raises(NativeMappingError, match="native callbacks changed"):
        validate_native_callbacks(value)
    assert value == original


def test_ordinary_record_paths_do_not_hydrate_docling(monkeypatch):
    from docling_core.types.doc import DoclingDocument

    monkeypatch.setattr(
        DoclingDocument, "model_validate", lambda *a, **k: pytest.fail("whole-native hydration")
    )
    value = complete_fixture()
    assert Records().lower(value).reconstruct() == value


def test_identity_ignores_operational_qualification_and_uses_oversize_descriptors():
    expected = {"name": "λ" * 100_000, "texts": [text(0)]}
    left = Records().lower(expected)
    right = Records().lower(
        expected, product_id="different-product", revision_id="different-revision"
    )

    def signature(records):
        # Deliberately no scalar body access: identity must consume verified descriptors.
        records.scalar = lambda _: pytest.fail("identity hydrated scalar")
        return [
            native_record_identity_fields(r, scalar_descriptor=records.descriptors.__getitem__)
            for r in records.rows
        ]

    assert signature(left) == signature(right)
    row = left.record(occurrence_id("#", "DoclingDocument"))
    descriptor = json.loads(row["structure_json"])["fields"]["name"]
    assert left.descriptors[descriptor["stream_id"]] == describe_scalar(expected["name"])


def test_scalar_storage_change_preserves_logical_fields():
    left = Records().lower({"name": "x"})
    right = Records().lower({"name": "x"})
    r = right.record(occurrence_id("#", "DoclingDocument"))
    descriptor = right.write("relocated", "pdf-record-scalar-v1:s", [b"x"])
    r["scalars_json"] = "{}"
    r["structure_json"] = json.dumps(
        {"schema_path": "#", "fields": {"name": {"kind": "parts", "stream_id": "relocated"}}}
    )
    a = next(row for row in left.rows if row.kind == "native")
    b = NativeRow("native", r)
    af = native_record_identity_fields(a, scalar_descriptor=left.descriptors.__getitem__)
    bf = native_record_identity_fields(b, scalar_descriptor=right.descriptors.__getitem__)
    assert af is not None and bf is not None
    assert af[:2] == bf[:2]
    assert describe_scalar(af[2][-1][1]) == descriptor == bf[2][-1][1]


def _native_example(schema, definitions):
    """Native-schema example construction, independent of the record lowering algorithm."""
    if "$ref" in schema:
        return _native_example(definitions[schema["$ref"][8:]], definitions)
    if "default" in schema:
        return copy.deepcopy(schema["default"])
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema or "oneOf" in schema:
        choices = schema.get("anyOf", schema.get("oneOf"))
        return _native_example(
            next((s for s in choices if s.get("type") == "null"), choices[0]), definitions
        )
    kind = schema.get("type")
    if kind == "object":
        return {
            name: _native_example(member, definitions)
            for name, member in schema.get("properties", {}).items()
        }
    if kind == "array":
        return (
            [_native_example(item, definitions) for item in schema.get("prefixItems", [])]
            if "prefixItems" in schema
            else [
                _native_example(schema["items"], definitions)
                for _ in range(schema.get("minItems", 0))
            ]
        )
    if kind == "null":
        return None
    if kind == "boolean":
        return False
    if kind == "integer":
        return schema.get("minimum", 0)
    if kind == "number":
        return float(schema.get("minimum", 0))
    if kind == "string":
        return "#" if "pattern" in schema else "sample"
    raise AssertionError(schema)


_NATIVE_DEFINITIONS = json.loads(native_schema_bytes())["$defs"]
_NATIVE_OBJECT_TYPES = [
    name for name, schema in _NATIVE_DEFINITIONS.items() if "properties" in schema
]


@pytest.mark.parametrize("native_type", _NATIVE_OBJECT_TYPES)
def test_every_supported_native_object_and_declared_field_roundtrips(native_type):
    schema = _NATIVE_DEFINITIONS[native_type]
    expected = _native_example(schema, _NATIVE_DEFINITIONS)
    records = Records().lower(expected, native_type=native_type)
    assert records.reconstruct(native_type) == expected
    root = records.record(occurrence_id("#", native_type))
    actual_fields = (
        json.loads(root["scalars_json"]).keys()
        | json.loads(root["structure_json"])["fields"].keys()
    )
    assert actual_fields == schema["properties"].keys()


def test_native_empty_collections_survive_callback_serializer_omission():
    # Docling's model serializer drops these explicitly empty collections. Callback validation
    # checks fields-set/model state, so it must not confuse serializer omission with mutation.
    value = {"name": "empty", "field_regions": [], "field_items": []}
    validate_native_callbacks(value)
    assert Records().lower(value).reconstruct() == value


def test_native_callbacks_reject_numeric_coercion_before_identity():
    value = {"name": "coercion", "pages": {"1": {"page_no": 1, "size": {"width": 1, "height": 2}}}}
    with pytest.raises(NativeMappingError, match="native callbacks changed"):
        validate_native_callbacks(value)


def test_callback_graph_and_track_rules_missing_from_jsonschema_are_enforced():
    graph = {
        "name": "graph",
        "key_value_items": [
            {
                "self_ref": "#/key_value_items/0",
                "graph": {
                    "cells": [],
                    "links": [{"label": "to_value", "source_cell_id": 17, "target_cell_id": 19}],
                },
            }
        ],
    }
    Records().lower(graph)  # Native JSON Schema cannot express the graph endpoint rule.
    with pytest.raises(ValueError, match="Invalid source_cell_id"):
        validate_native_callbacks(graph)
    track = {
        "name": "track",
        "texts": [text(0, source=[{"kind": "track", "start_time": 2.0, "end_time": 1.0}])],
    }
    Records().lower(track)
    with pytest.raises(ValueError, match="End time must be greater"):
        validate_native_callbacks(track)


def test_native_map_logical_identity_ignores_physical_object_delivery_order():
    first = {
        "name": "map",
        "pages": {
            "2": {"page_no": 2, "size": {"width": 2.0, "height": 3.0}},
            "1": {"page_no": 1, "size": {"width": 2.0, "height": 3.0}},
        },
    }
    second = copy.deepcopy(first)
    second["pages"] = dict(reversed(list(first["pages"].items())))

    def signature(value):
        records = Records().lower(value)
        result = [
            native_record_identity_fields(row, scalar_descriptor=records.descriptors.__getitem__)
            for row in records.rows
        ]
        return sorted((r for r in result if r is not None), key=lambda r: (r[0], r[1]))

    assert signature(first) == signature(second)
    assert Records().lower(first).reconstruct() == first


def test_record_json_wire_has_explicit_typed_physical_projection():
    records = Records().lower({"name": "physical", "texts": [text(0)]})
    for row in records.rows:
        physical = row.physical_values()
        if row.kind == "native":
            assert isinstance(physical["scalars_json"], dict)
            assert isinstance(physical["structure_json"], dict)
        assert physical.keys() == row.values.keys()


def test_native_validation_placements_retain_the_bounded_oracle_limit():
    from corpus_structure.semantic.pdf_records import native_validation_contract

    contract = native_validation_contract()
    assert contract["docling_core_version"] == "2.105.0"
    assert "actual reference and artifact verification" in contract["frozen_union_enforcement"]
    assert "identity-bearing" in contract["opaque_extension_profile"]


def test_extensions_cannot_inject_declared_native_fields():
    records = Records().lower({"name": "x", "body": {"self_ref": "#/body", "meta": {"vendor": 1}}})
    meta = next(
        r.values
        for r in records.rows
        if r.kind == "native" and r.values["native_type"] == "BaseMeta"
    )
    stream = json.loads(meta["structure_json"])["extensions"]["stream_id"]
    records.streams[stream] = (b'{"summary":null}',)
    with pytest.raises(NativeMappingError, match="overwrite declared"):
        records.reconstruct()


def test_coherent_wrong_root_class_is_not_a_document():
    records = Records()
    records.rows = [
        NativeRow(
            "native",
            {
                "record_id": "root",
                "native_type": "GroupItem",
                "family": "node",
                "native_address": "#",
                "scalars_json": '{"self_ref":"#/body","name":"x"}',
                "structure_json": '{"schema_path":"#/$defs/GroupItem","fields":{}}',
            },
        )
    ]
    with pytest.raises(NativeMappingError, match="requested native root"):
        reconstruct_native_document(records, "root", scalar_profiles={})
