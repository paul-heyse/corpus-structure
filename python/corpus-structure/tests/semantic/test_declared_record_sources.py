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
        "source": "source:section", "document": "original:doc", "projection_digest": "a" * 64,
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
