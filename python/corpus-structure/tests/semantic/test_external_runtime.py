"""Finite external API contracts preserve original code and actual runtime bindings."""

import importlib
import sys
from dataclasses import replace

import pytest

from corpus_structure.semantic.code_identity import authenticate_workload, capture_code_identity
from corpus_structure.semantic.external_runtime import acquire_codec_runtime


def test_native_codec_profiles_bind_real_library_symbols_and_files():
    contracts = acquire_codec_runtime()
    assert {item.reference for item in contracts} == {"math", "rapidjson", "decimal", "datetime", "base64"}
    for item in contracts:
        assert len(item.digest) == 64 and item.files and item.symbols
        item.check()


def test_native_callable_replacement_before_acquisition_is_refused(monkeypatch):
    math = importlib.import_module("math")
    monkeypatch.setattr(math, "isfinite", lambda _: True)
    with pytest.raises(ValueError, match="unsupported external codec symbol"):
        acquire_codec_runtime()


def test_native_callable_rebinding_after_acquisition_is_refused(monkeypatch):
    contract = acquire_codec_runtime()[0]
    monkeypatch.setattr(sys.modules["math"], "isfinite", lambda _: True)
    with pytest.raises(ValueError, match="symbol was replaced"):
        contract.check()


def test_native_codec_constant_mismatch_is_refused(monkeypatch):
    monkeypatch.setattr(importlib.import_module("rapidjson"), "NM_DECIMAL", 1)
    with pytest.raises(ValueError, match="constant differs"):
        acquire_codec_runtime()


def test_native_codec_module_replacement_after_acquisition_is_refused(monkeypatch):
    contract = acquire_codec_runtime()[0]
    monkeypatch.setitem(sys.modules, "math", object())
    with pytest.raises(ValueError, match="module was replaced"):
        contract.check()


def test_native_external_boundary_is_carried_into_live_workload_authentication(tmp_path, monkeypatch):
    root = tmp_path / "codec_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "import math\ndef finite(value: float) -> bool:\n return math.isfinite(value)\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    contract = acquire_codec_runtime()[0]
    identity = capture_code_identity(
        root,
        ("codec_example.entry",),
        callables=("codec_example.entry.finite",),
        external_runtime=(contract,),
    )
    assert identity.complete, identity.unknowns
    assert identity.external_runtime == (contract,)
    with authenticate_workload(root, identity) as verify:
        module = importlib.import_module("codec_example.entry")
        assert module.finite(2.0) and not module.finite(float("inf"))
        verify()
    changed = replace(contract, digest="a" * 64)
    other = capture_code_identity(
        root,
        ("codec_example.entry",),
        callables=("codec_example.entry.finite",),
        external_runtime=(changed,),
    )
    assert other.digest != identity.digest


def test_unadmitted_python_codec_remains_unknown(tmp_path):
    root = tmp_path / "codec_unknown"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text("import json\ndef read(value):\n return json.loads(value)\n")
    identity = capture_code_identity(
        root,
        ("codec_unknown.entry",),
        callables=("codec_unknown.entry.read",),
        external_runtime=acquire_codec_runtime(),
    )
    assert not identity.complete
    assert any("json" in item.reason for item in identity.unknowns)


def test_native_namespace_cannot_admit_an_unselected_native_function(tmp_path):
    root = tmp_path / "codec_unselected"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text("import math\ndef root(value):\n return math.sqrt(value)\n")
    identity = capture_code_identity(
        root, ("codec_unselected.entry",), callables=("codec_unselected.entry.root",),
        external_runtime=acquire_codec_runtime(),
    )
    assert not identity.complete
    assert any("math.sqrt" in item.reason for item in identity.unknowns)


def test_standard_base64_helper_and_table_substitution_are_refused(monkeypatch):
    module = importlib.import_module("base64")
    with monkeypatch.context() as patch:
        patch.setattr(module, "b64encode", lambda value: value)
        with pytest.raises(ValueError, match="Base64 callable"):
            acquire_codec_runtime()
    with monkeypatch.context() as patch:
        patch.setattr(module, "_urlsafe_encode_translation", bytes(range(256)))
        with pytest.raises(ValueError, match="Base64 global"):
            acquire_codec_runtime()


def test_tagged_codec_bytes_keep_the_standard_json_reference():
    import json
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_value_codec import semantic_value, tagged_bytes

    values = [None, False, True, "\\\\ \" snowman ☃\n", 123, Decimal("0.0100"), 0.25,
              {"z": "last", "a": [1, None, True]}, ()]
    for value in values:
        tag = semantic_value(value, decimal_fixed_point_digits=100)
        assert tagged_bytes(tag) == json.dumps(
            tag, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()


def test_generic_mapping_inputs_keep_nested_tag_meaning_and_key_refusal():
    from collections import UserDict
    from types import MappingProxyType

    from corpus_structure.semantic.data_operation_value_codec import (
        native_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue

    value = UserDict({"outer": [MappingProxyType({"inner": 7}), OptionalValue("present", UserDict({"n": 2}))]})
    expected = ["mapping", [["outer", ["sequence", [
        ["mapping", [["inner", ["integer", "7"]]]],
        ["present", ["mapping", [["n", ["integer", "2"]]]]],
    ]]]]]
    assert semantic_value(value, decimal_fixed_point_digits=100) == expected
    assert semantic_value(
        CollectionValue("ordered-bag", (value,)), decimal_fixed_point_digits=100
    ) == ["ordered-bag", [expected]]
    with pytest.raises(TypeError, match="mapping keys must be strings"):
        semantic_value(UserDict({"nested": UserDict({1: "invalid"})}), decimal_fixed_point_digits=100)
    with pytest.raises(TypeError):
        native_semantic_value(value, decimal_fixed_point_digits=100)
