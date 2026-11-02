import base64
import json
from datetime import UTC, datetime
from hashlib import file_digest

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.companion_export import (
    CompanionExportManifest,
    FamilyFile,
    PublishedSourcePin,
    _export_schema,
    _publish_directory,
    compare_companion_exports,
    inventory_companion_export,
)


def _export(
    root,
    rows,
    *,
    release="r",
    producer_release="producer-r",
    projection_id=None,
    task=1,
    include_inputs=False,
):
    from corpus_structure.semantic.companion_projection import projection

    root.mkdir()
    pin = PublishedSourcePin(
        project_id="p",
        run_id=1,
        selection_release_id=release,
        task_id=task,
        product_key="integrated",
        content_digest="a" * 64,
    )
    spec = projection("relation")
    projection_id = projection_id or spec.projection_id
    schema = _export_schema(spec, pin, producer_release_id=producer_release)
    schema = schema.with_metadata({**schema.metadata, b"cs.projection": projection_id.encode()})
    batch = pa.RecordBatch.from_pylist(
        [
            dict(
                **pin.model_dump(),
                producer_release_id=producer_release,
                projection_id=projection_id,
                relation_outcome="unknown",
                comparison="fixture",
                policy="fixture",
                evidence="fixture",
                endpoint_role="target",
                target_task_id=1,
                target_product_key="integrated",
                target_content_digest="a" * 64,
                target_occurrence_id="#/items/0",
                **row,
            )
            for row in rows
        ],
        schema=schema,
    )
    batches = {"relation": batch}
    if include_inputs:
        batches["input"] = pa.RecordBatch.from_pylist(
            [
                dict(
                    **pin.model_dump(),
                    producer_release_id=producer_release,
                    projection_id=projection_id,
                    input_ordinal=0,
                    input_role="structural",
                    input_task_id=99,
                    input_product_key="native",
                    input_content_digest="b" * 64,
                ),
            ],
            schema=_export_schema(projection("input"), pin, producer_release_id=producer_release),
        )
    entries = {}
    for family, family_batch in batches.items():
        path = root / (family + ".parquet")
        pq.write_table(pa.Table.from_batches([family_batch]), path)
        logical = LogicalRows(family_batch.schema)
        logical.write(family_batch)
        with path.open("rb") as source:
            digest = file_digest(source, "sha256").hexdigest()
        entries[family] = FamilyFile(
            path=path.name,
            rows=family_batch.num_rows,
            sha256=digest,
            byte_length=path.stat().st_size,
            logical_digest=logical.digest,
            schema_base64=base64.b64encode(family_batch.schema.serialize().to_pybytes()).decode(),
        )
    manifest = CompanionExportManifest(
        pin=pin,
        producer_release_id=producer_release,
        projection_id=projection_id,
        profile_id="flat-exact-companion-v2",
        created_at=datetime.now(UTC),
        families=entries,
        not_requested=tuple(
            family for family in ("input", "coverage", "mapping_report") if family not in entries
        ),
    )
    (root / "manifest.json").write_text(manifest.model_dump_json())
    return root / "manifest.json"


def test_inventory_counts_relation_occurrences_not_endpoints(tmp_path):
    path = _export(
        tmp_path / "left",
        [dict(relation_id="r1", relation_kind="support", endpoint_ordinal=i) for i in range(2)],
    )
    result = inventory_companion_export(path)
    assert result["families"]["relation"]["rows"] == 2
    assert result["families"]["relation"]["relation_count"] == 1
    assert result["families"]["relation"]["distribution"] == [("support", 1)]
    assert result["families"]["relation"]["target_scope"] == [("own_product", 2)]
    assert result["families"]["relation"]["endpoints"]["rows"] == [
        ("support", "target", 1, "integrated", "a" * 64, "#/items/0", 2)
    ]
    (path.parent / "relation.parquet").write_bytes(b"corrupt")
    with pytest.raises(SemanticRefusal, match="binding"):
        inventory_companion_export(path)


def test_compare_preserves_multiset_difference(tmp_path):
    row = dict(relation_id="r1", relation_kind="support", endpoint_ordinal=0)
    left = _export(tmp_path / "left", [row, row])
    right = _export(tmp_path / "right", [row])
    result = compare_companion_exports(left, right)
    assert result["comparable"]
    removed = result["differences"]["relation"]["removed"]
    assert len(removed) == 1
    observed = dict(zip(result["differences"]["relation"]["columns"], removed[0], strict=True))
    assert {key: observed[key] for key in row} == row
    assert observed["target_content_digest"] == "a" * 64
    assert result["differences"]["relation"]["added"] == []
    other_release = _export(tmp_path / "other", [row], release="other")
    assert not compare_companion_exports(left, other_release)["comparable"]
    changed = json.loads(right.read_text())
    changed["pin"]["selection_release_id"] = "other"
    right.write_text(json.dumps(changed))
    with pytest.raises(SemanticRefusal, match="pin binding"):
        compare_companion_exports(left, right)


def test_different_projection_reports_incomparability_without_interpreting_unknown_fields(tmp_path):
    row = dict(relation_id="r1", relation_kind="support", endpoint_ordinal=0)
    left = _export(tmp_path / "left", [row])
    right = _export(tmp_path / "right", [row], projection_id="different-design-projection")
    result = compare_companion_exports(left, right)
    assert not result["comparable"]
    assert result["differences"] == {}
    assert result["right"]["families"]["relation"] == {
        "rows": 1,
        "semantic_inventory": "unsupported_projection_or_profile",
    }


def test_cross_product_local_ids_never_establish_correspondence(tmp_path):
    row = dict(relation_id="r1", relation_kind="support", endpoint_ordinal=0)
    left = _export(tmp_path / "left", [row], task=1, include_inputs=True)
    right = _export(tmp_path / "right", [row], task=2, include_inputs=True)
    result = compare_companion_exports(left, right)
    assert result["comparable"]
    relations = result["differences"]["relation"]
    assert relations["correspondence"] == "none"
    assert relations["left_pin"]["task_id"] == 1
    assert relations["right_pin"]["task_id"] == 2
    assert len(relations["removed"]) == len(relations["added"]) == 1


def test_publication_refuses_existing_empty_directory(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "value").write_text("x")
    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        _publish_directory(source, destination)
    assert source.exists() and list(destination.iterdir()) == []


def test_producer_binding_is_independent_and_manifest_tampering_refuses(tmp_path):
    row = dict(relation_id="r1", relation_kind="support", endpoint_ordinal=0)
    path = _export(tmp_path / "source", [row], release="consumer", producer_release="producer")
    inventory = inventory_companion_export(path)
    assert inventory["pin"]["selection_release_id"] == "consumer"
    assert inventory["producer_release_id"] == "producer"
    value = json.loads(path.read_bytes())
    value["producer_release_id"] = "substituted"
    path.write_text(json.dumps(value))
    with pytest.raises(SemanticRefusal, match="pin binding"):
        inventory_companion_export(path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("relation_id", None),
        ("selection_release_id", "producer"),
        ("producer_release_id", "consumer"),
    ],
)
def test_projection_batch_refuses_missing_values_and_misbound_releases(tmp_path, field, value):
    from corpus_structure.semantic.companion_projection import projection
    from corpus_structure.serve.companion_export import _admit_batch

    path = _export(
        tmp_path / "source", [dict(relation_id="r1", relation_kind="support", endpoint_ordinal=0)]
    )
    manifest = CompanionExportManifest.model_validate_json(path.read_bytes())
    batch = pq.read_table(path.parent / "relation.parquet").to_batches()[0]
    index = batch.schema.get_field_index(field)
    batch = batch.set_column(index, batch.schema.field(index), pa.array([value], type=pa.string()))
    with pytest.raises(SemanticRefusal, match=r"null|binding differs"):
        _admit_batch(projection("relation"), batch, manifest.pin, manifest.producer_release_id)
