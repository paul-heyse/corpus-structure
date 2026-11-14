"""Native scoped joins consume retained facts without task or view aliases."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.scoped_relations import discover_relations, retained_procedure_readings
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
from corpus_structure.semantic.constructions.navigation import FAMILY, NativeNavigationIndex, populate_navigation_products
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_formal_readings import declared_formal_layers
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredRecordSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from semantic.formal_products_support import profile as profile, selected


def test_native_scoped_kernel_keeps_actual_artifact_source_and_formal_addresses(profile):
    text = "Table 2.1 (aliases: none)."
    source = selected(profile, text, items=[dict(self_ref="#/texts/0", label="caption", text=text, orig=text)])
    coordinate = source.value["source"]
    context = SubjectContext("p", source_subject(coordinate), coordinate["document"], canonical_bytes({"source": coordinate, "selectors": source.value["selectors"]}))
    pin = DeclaredRecordSource(coordinate["document"], coordinate["projection"], coordinate["section_pointer"], coordinate["membership"], context, "product:source", None, "kind:source").pin()
    frame = DeclaredNativeFrameSource(source.content.decode(), canonical_bytes(pin).decode())
    layer = ConstructionLayer(coordinate, {"selectors": source.value["selectors"]}, {"key": "text.constructions/source-native"}, semantic=True, families=(FAMILY,))
    populate_navigation_products(layer, ConstructionSource.from_native(source), source, None)
    facts = layer.facts()
    navigation_product = CharacterizationSnapshot("product:navigation", canonical_bytes({"source": coordinate, "selectors": source.value["selectors"], "coverage": facts["coverage"], "members": [{"body": {"record_type": tag, **row}} for name, tag in (("annotations", "annotation"), ("occurrences", "occurrence")) for row in facts[name]]}))
    native_formal = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    inspected = tuple(dict(question=question, outcome="empty", inspected_count=0, emitted_count=0, operation_key=question, operation_version="6", computation_dependencies=("product:native",)) for question in ("source_predicate_frames", "source_predicate_interpretation"))
    result = discover_relations(frame, source_work="work:book", navigation=NativeNavigationIndex((navigation_product,), source), formal_layers=declared_formal_layers((native_formal,), source), retained_predicates=(), retained_predicate_operations=inspected, inline_equations_enabled=True, witnessed_links_enabled=True)
    artifacts = tuple(row for row in result["contributions"] if row["semantic_type"] == "structural.artifact")
    assert len(artifacts) == 1
    assert source_python(artifacts[0]["value"])["controlled_code"] == "2.1"
    assert source_python(artifacts[0]["value"])["primary_node"]["product_id"] == navigation_product.semantic_id
    assert artifacts[0]["pin"] == frame.pin.values()
    assert all("primary_products" in operation and "primary_layers" not in operation for operation in (result["operation"], *result["extra_operations"]))
    assert b"source_view_id" not in canonical_bytes(result) and b"task_id" not in canonical_bytes(result)
    with pytest.raises(ValueError, match="actual navigation, formal and retained predicate"):
        discover_relations(frame)


def test_retained_procedure_scalar_projection_preserves_roles_voice_and_partiality():
    members = [dict(role=role, outcome="complete", extents=[dict(start=start, end=end)]) for role, start, end in (("predicate", 2, 4), ("focus", 0, 14), ("actor", 0, 1), ("object", 5, 8))]
    frame = dict(kind="predicate_frame", grammatical_reading="active", annotation="annotation:actual-primary", block="block:original", predicate_token=1, variant="active", frame_members=members)
    rows = [dict(contribution_id="frame", component=frame), dict(contribution_id="reading", component=dict(kind="predicate_reading", frame="frame", reading="described_process", voice="active", polarity="negative")), dict(contribution_id="condition", component=dict(kind="predicate_cue", host_state="located", extents=[dict(start=10, end=14)], variant="if")), dict(contribution_id="qualification", component=dict(kind="predicate_qualifier", host_contribution_id="frame", qualifier_contribution_id="condition", qualifier_kind="condition"))]
    (reading,) = tuple(retained_procedure_readings(rows, (SimpleNamespace(start=0, end=14),)))
    assert reading["action"] == (2, 4) and reading["actor"] == ((0, 1),) and reading["object"] == ((5, 8),)
    assert reading["conditions"] == ((10, 14),) and reading["voice"] == "active" and reading["polarity"] == "negative"
    assert reading["dependency"] == "annotation:actual-primary"
    members[-1]["outcome"] = "partial"
    (narrowed,) = tuple(retained_procedure_readings(rows, (SimpleNamespace(start=0, end=14),)))
    assert narrowed["object"] == () and narrowed["actor"] == reading["actor"]
