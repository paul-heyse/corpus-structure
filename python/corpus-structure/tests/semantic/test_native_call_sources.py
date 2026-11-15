"""Fixed call assets resolve from explicit sources without legacy operation authority."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_call_contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from corpus_structure.semantic.native_call_sources import resolve_call_bindings
from corpus_structure.semantic.types import PreparationError


def _activation_call():
    return OperationCallBinding(
        id="activate_release", symbol="sem.activate_release",
        parameters=(OperationFieldBinding(
            "release_id", "physical:sem.release.release_id", False,
            native_parameter="r", semantic_type="ReleaseId",
        ),),
        result_fields=(), cardinality="none", ordered=False, result_mode="void",
    )


def _resolve(call, physical=None, logical=None):
    return resolve_call_bindings(
        (("release-activation-asset", call),),
        physical_sources=metadata.info["physical_sources"] if physical is None else physical,
        logical_sources={"linkml:types": metadata.info["physical_linkml_types"]} if logical is None else logical,
    )[0][1]


def test_current_call_assets_preserve_exact_source_constraints_and_nominal_type():
    original = _activation_call()
    resolved = _resolve(original)
    assert original.parameters[0].resolved is None
    assert resolved.parameters[0] == replace(original.parameters[0], resolved=OperationFieldType("string", False, False))
    assert resolved.result_fields == ()
    assert resolved.cardinality == "none"
    assert resolved.source_digest is not None and len(resolved.source_digest) == 64

    sources = dict(metadata.info["physical_sources"])
    document = yaml.safe_load(sources["physical.yaml"])
    document["classes"]["release"]["attributes"]["release_id"]["pattern"] = "^release:"
    sources["physical.yaml"] = yaml.safe_dump(document).encode()
    changed = _resolve(original, physical=sources)
    assert changed.source_digest != resolved.source_digest
    with pytest.raises(PreparationError, match="resolved source representation differs"):
        _resolve(resolved, physical=sources)


def test_native_call_sources_do_not_acquire_missing_logical_imports():
    with pytest.raises(PreparationError, match="undeclared import linkml:types"):
        _resolve(_activation_call(), logical={})
