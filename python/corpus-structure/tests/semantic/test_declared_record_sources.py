"""Independent original-relative pin expectations; no producer or native-admission claim."""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource, declared_record_inputs
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def address(scope=b'{"page":1}'):
    return DeclaredRecordSource("original:doc", "a" * 64, "#/groups/3", "descendants", SubjectContext("p", "source:section", "original:doc", scope), "product:source", "member:section", "kind:source")


def test_declared_record_pin_has_exact_original_coordinates_without_task_or_view_alias():
    pin = address().pin()
    assert pin == {
        "format": "declared-native-source-v1", "source": '["product:source","member:section"]', "subject": "source:section", "document": "original:doc", "projection_digest": "a" * 64,
        "section_pointer": "#/groups/3", "membership": "descendants", "project_id": "p",
        "original_source": "original:doc", "analyzed_scope_meaning": '["mapping",[["page",["decimal","1"]]]]',
        "source_product": "product:source", "source_member": "member:section", "kind_contract": "kind:source",
    }
    assert not {"source_view_id", "native_product_task_id", "run_id", "task_id"} & pin.keys()
    assert address(b'{"page":1.0}').pin() == pin
    assert address(b'{"page":true}').pin() != pin


def test_declared_projection_changes_only_selected_pin_contract_and_retains_old_artifact():
    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    raw = (root / "observations.yaml").read_bytes()
    bundle = SourceBundle("observations", (SourceArtifact("observations", raw),))
    projected = declared_record_inputs(bundle)
    old = yaml.safe_load(raw)
    new = yaml.safe_load(projected.sources[0].content)
    assert bundle.sources[0].content == raw
    assert "native_product_task_id" in old["classes"]["RecordSourcePin"]["attributes"]
    assert "native_product_task_id" not in new["classes"]["RecordSourcePin"]["attributes"]
    for required in ("document", "source_product", "kind_contract", "project_id", "analyzed_scope_meaning"):
        assert new["classes"]["RecordSourcePin"]["attributes"][required]["required"]
    old["classes"].pop("RecordSourcePin")
    new["classes"].pop("RecordSourcePin")
    assert new == old
    assert declared_record_inputs(projected).sources == projected.sources


def test_declared_projection_refuses_independent_pin_override():
    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    module = yaml.safe_load((root / "observations.yaml").read_bytes())
    module["classes"]["RecordSourcePin"]["attributes"]["unexpected"] = {"required": True}
    bundle = SourceBundle("observations", (SourceArtifact("observations", yaml.safe_dump(module).encode()),))
    with pytest.raises(ValueError, match="independently changed"):
        declared_record_inputs(bundle)


def test_declared_member_maps_literal_spans_without_a_physical_view_or_task():
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredSourceSlice
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources, evidence_anchor
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    prepared = prepare_release(declared_record_inputs(source_product_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))))
    text = "A valve opens."
    source = FrozenNativeSource.from_projection(
        prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants",
        text=text, pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": len(text)}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": text, "orig": text, "prov": []}],
    )
    member = BoundRoleMember("product:population", "kind:source", "subject:section", "original:doc", b'{"page":1}', b'{}', (), b'{}', member="member:one")
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    assert not hasattr(frame, "source_view_id") and not hasattr(frame, "native_product")
    preparation = PreparedNativeSources((frame,))
    context = NativeSourceContext(frame, (), (DeclaredSourceSlice(frame.source_key, 2, 7),), "definition", "declared-test", "selected", version=2, preparation=preparation)
    assert context.text == "valve"
    (piece,) = context.map_span(0, 5, literal="valve")
    assert piece.quote == "valve" and (piece.start, piece.end) == (2, 7)
    anchor, coordinate = evidence_anchor(context, piece)
    assert anchor["pin"]["source_product"] == "product:population"
    assert anchor["pin"]["source_member"] == "member:one"
    assert anchor["pin"]["subject"] == "subject:section"
    assert "source_view_id" not in anchor["pin"]
    prepared.validate_python("RecordAnchor", anchor)
    assert coordinate["text"] == "A valve opens."


def test_declared_literal_record_assembly_preserves_semantic_member_pin():
    from corpus_structure.methods.record_assembly import LiteralSpan, NativeRecordGroup, RoleInput, assemble_native_records
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources, source_slice
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    repository = Path(__file__).resolve().parents[4]
    bundle = SourceBundle("statistics_semantic", (
        SourceArtifact("statistics_semantic", (repository / "domains/statistics/semantic.yaml").read_bytes()),
        SourceArtifact("statistics_terminology", (repository / "domains/statistics/terminology.yaml").read_bytes()),
        SourceArtifact("semantic_core", (root / "core.yaml").read_bytes()),
    ))
    prepared = prepare_release(declared_record_inputs(source_product_inputs(bundle)))
    text = "A valve opens."
    native = FrozenNativeSource.from_projection(
        prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants",
        text=text, pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": len(text)}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": text, "orig": text, "prov": []}],
    )
    member = BoundRoleMember("product:population", "kind:source", "subject:section", "original:doc", b'{"page":1}', b'{}', (), b'{}', member="member:one")
    frame = DeclaredNativeFrameSource.acquire(prepared, native.value, member, project="p")
    context = NativeSourceContext(frame, (), (source_slice(frame, 0, len(text)),), "definition", "declared-test", "selected", version=2, preparation=PreparedNativeSources((frame,)))
    result = assemble_native_records(prepared, context, contract="DefinitionRecordFields", occurrence_roles=("term",), policy_version="reading-1", groups=(NativeRecordGroup((RoleInput("term", spans=(LiteralSpan(2, 7, "valve"),)),), "explicit term"),))
    assert len(result.records) == 1
    record = result.records[0].model_dump(mode="python")
    assert {anchor["pin"]["source_product"] for anchor in record["anchors"]} == {"product:population"}
    assert {anchor["pin"]["source_member"] for anchor in record["anchors"]} == {"member:one"}
    assert all("source_view_id" not in anchor["pin"] for anchor in record["anchors"])


def test_candidate_preparation_accepts_explicit_declared_frame_without_view_reference():
    from types import SimpleNamespace
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    prepared = prepare_release(declared_record_inputs(source_product_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))))
    text = "A valve opens."
    native = FrozenNativeSource.from_projection(prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants", text=text,
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": len(text)}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": text, "orig": text, "prov": []}])
    member = BoundRoleMember("product:population", "kind:source", "subject:section", "original:doc", b'{"page":1}', b'{}', (), b'{}', member="member:one")
    frame = DeclaredNativeFrameSource.acquire(prepared, native.value, member, project="p")
    data = SimpleNamespace(text=text, pieces=native.value["pieces"], items=native.value["items"], health={})
    result = prepare_source(data, source_frame=frame, persisted_annotations=())
    assert result.source is frame
    assert result.regions[0].pointer == "#/texts/0"
    assert result.preparation.sources[0] is frame


def test_declared_formula_occurrence_keeps_original_member_address_without_conversion_alias():
    from corpus_structure.methods.math.pdf import DeclaredFormulaOccurrence, formula_matches_source, formula_occurrence
    from corpus_structure.methods.record_assembly import native_formula_group
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
    from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources, source_slice
    from corpus_structure.semantic.source_products import FrozenNativeSource, source_product_inputs

    root = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic"
    prepared = prepare_release(declared_record_inputs(source_product_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))))
    item = {"self_ref": "#/texts/0", "label": "formula", "text": "x+y", "orig": "x+y", "prov": []}
    native = FrozenNativeSource.from_projection(prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants", text="x+y",
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "orig", "start": 0, "end": 3}], items=[item])
    member = BoundRoleMember("product:population", "kind:source", "subject:section", "original:doc", b'{"page":1}', b'{}', (), b'{}', member="member:one")
    frame = DeclaredNativeFrameSource.acquire(prepared, native.value, member, project="p")
    occurrence = formula_occurrence(frame, item, "succeeded")
    assert isinstance(occurrence, DeclaredFormulaOccurrence)
    assert occurrence.source.values()["source_member"] == "member:one"
    assert not hasattr(occurrence, "conversion_digest")
    assert formula_matches_source(occurrence, frame)
    context = NativeSourceContext(frame, (), (source_slice(frame, 0, 3),), "formula", "declared-test", "selected", version=2, preparation=PreparedNativeSources((frame,)))
    group = native_formula_group(context, occurrence, scope_pointer="#/groups/0")
    assert group.fields[0].spans[0].text == "x+y"
    other = DeclaredNativeFrameSource.acquire(prepared, native.value, replace(member, member="member:other"), project="p")
    assert not formula_matches_source(occurrence, other)
