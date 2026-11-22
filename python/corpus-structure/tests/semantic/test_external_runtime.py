"""Finite external API contracts preserve original code and actual runtime bindings."""

import importlib
import sys
from dataclasses import replace

import pytest

from corpus_structure.semantic.code_identity import authenticate_workload, capture_code_identity
from corpus_structure.semantic.external_runtime import acquire_codec_runtime


def test_native_codec_profiles_bind_real_library_symbols_and_files():
    contracts = acquire_codec_runtime()
    assert {item.reference for item in contracts} == {
        "math",
        "rapidjson",
        "decimal",
        "datetime",
        "base64",
        "hashlib",
        "json",
    }
    for item in contracts:
        assert len(item.digest) == 64 and item.files
        assert bool(item.symbols) == (item.reference != "json")
        item.check()


def test_standard_json_keeps_canonical_utf8_and_live_custody(monkeypatch):
    import json

    from corpus_structure.semantic.external_runtime import acquire_standard_json_runtime
    from corpus_structure.semantic.identity import canonical_bytes

    runtime = acquire_standard_json_runtime()
    text = "é\x1f"
    assert canonical_bytes({"text": text}) == b'{"text":"\xc3\xa9\\u001f"}'
    assert json.loads(b'{"text":"\xc3\xa9\\u001f"}') == {"text": text}

    with monkeypatch.context() as patch:
        patch.setattr(json.encoder, "encode_basestring", lambda value: repr(value))
        with pytest.raises(ValueError, match="standard JSON native implementation binding"):
            runtime.check()
        with pytest.raises(ValueError, match="standard JSON native implementation binding"):
            acquire_standard_json_runtime()

    with monkeypatch.context() as patch:
        patch.setattr(vars(json)["_default_encoder"], "ensure_ascii", False)
        with pytest.raises(ValueError, match="standard JSON default wrapper"):
            runtime.check()

    with monkeypatch.context() as patch:
        patch.setattr(json.loads, "__code__", (lambda value, **kwargs: {}).__code__)
        with pytest.raises(ValueError, match="standard JSON wrapper differs"):
            runtime.check()


def test_native_callable_replacement_before_acquisition_is_refused(monkeypatch):
    math = importlib.import_module("math")
    monkeypatch.setattr(math, "isfinite", lambda _: True)
    with pytest.raises(ValueError, match="unsupported external codec symbol"):
        acquire_codec_runtime()


def test_sha256_public_binding_requires_the_actual_openssl_constructor(monkeypatch):
    hashlib = importlib.import_module("hashlib")
    monkeypatch.setattr(hashlib, "sha256", lambda _: None)
    with pytest.raises(ValueError, match="wrapper binding differs"):
        acquire_codec_runtime()


def test_sha256_original_alias_is_rechecked_after_acquisition(monkeypatch):
    contract = next(item for item in acquire_codec_runtime() if item.reference == "hashlib")
    monkeypatch.setattr(importlib.import_module("hashlib"), "sha256", lambda _: None)
    with pytest.raises(ValueError, match="symbol was replaced"):
        contract.check()


def test_sha256_workload_retains_verified_native_runtime(tmp_path, monkeypatch):
    root = tmp_path / "hash_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "import hashlib\ndef digest(value: bytes) -> str:\n"
        " return hashlib.sha256(value).hexdigest()\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    contract = next(item for item in acquire_codec_runtime() if item.reference == "hashlib")
    identity = capture_code_identity(
        root,
        ("hash_example.entry",),
        callables=("hash_example.entry.digest",),
        external_runtime=(contract,),
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity) as verify:
        module = importlib.import_module("hash_example.entry")
        assert module.digest(b"abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        verify()


def test_nested_function_globals_remain_live_authenticated_premises(tmp_path, monkeypatch):
    from corpus_structure._query_custody import SourceCustodyError

    root = tmp_path / "nested_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "OFFSET = 7\n"
        "def result(value: int):\n"
        " def local(item: int):\n"
        "  return item + OFFSET\n"
        " return local(value)\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root, ("nested_example.entry",), callables=("nested_example.entry.result",)
    )
    assert identity.complete, identity.unknowns
    with (
        pytest.raises(SourceCustodyError, match=r"changed|differs"),
        authenticate_workload(root, identity) as verify,
    ):
        module = importlib.import_module("nested_example.entry")
        assert module.result(3) == 10
        monkeypatch.setattr(module, "OFFSET", 9)
        verify()


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


def test_native_external_boundary_is_carried_into_live_workload_authentication(
    tmp_path, monkeypatch
):
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
    selected = capture_code_identity(
        root,
        ("codec_unknown.entry",),
        callables=("codec_unknown.entry.read",),
        external_runtime=acquire_codec_runtime(standard_json_io=True),
    )
    assert selected.complete, selected.unknowns


def test_native_namespace_cannot_admit_an_unselected_native_function(tmp_path):
    root = tmp_path / "codec_unselected"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text("import math\ndef root(value):\n return math.sqrt(value)\n")
    identity = capture_code_identity(
        root,
        ("codec_unselected.entry",),
        callables=("codec_unselected.entry.root",),
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

    values = [
        None,
        False,
        True,
        '\\\\ " snowman ☃\n',
        123,
        Decimal("0.0100"),
        0.25,
        {"z": "last", "a": [1, None, True]},
        (),
    ]
    for value in values:
        tag = semantic_value(value, decimal_fixed_point_digits=100)
        assert (
            tagged_bytes(tag)
            == json.dumps(
                tag, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )


def test_generic_mapping_inputs_keep_nested_tag_meaning_and_key_refusal():
    from collections import UserDict
    from types import MappingProxyType

    from corpus_structure.semantic.data_operation_value_codec import (
        native_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue

    value = UserDict(
        {"outer": [MappingProxyType({"inner": 7}), OptionalValue("present", UserDict({"n": 2}))]}
    )
    expected = [
        "mapping",
        [
            [
                "outer",
                [
                    "sequence",
                    [
                        ["mapping", [["inner", ["integer", "7"]]]],
                        ["present", ["mapping", [["n", ["integer", "2"]]]]],
                    ],
                ],
            ]
        ],
    ]
    assert semantic_value(value, decimal_fixed_point_digits=100) == expected
    assert semantic_value(
        CollectionValue("ordered-bag", (value,)), decimal_fixed_point_digits=100
    ) == ["ordered-bag", [expected]]
    with pytest.raises(TypeError, match="mapping keys must be strings"):
        semantic_value(
            UserDict({"nested": UserDict({1: "invalid"})}), decimal_fixed_point_digits=100
        )
    with pytest.raises(TypeError):
        native_semantic_value(value, decimal_fixed_point_digits=100)


def test_standard_base64_builtin_type_table_cannot_use_custom_equality(monkeypatch):
    module = importlib.import_module("base64")

    class EqualType(type):
        def __eq__(cls, other):
            return True

    class PretendBytes(metaclass=EqualType):
        pass

    monkeypatch.setattr(module, "bytes_types", (PretendBytes, bytearray))
    with pytest.raises(ValueError, match="Base64 global"):
        acquire_codec_runtime()


def test_verified_native_integer_constant_is_data_and_rechecked(tmp_path, monkeypatch):
    root = tmp_path / "constant_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from rapidjson import NM_DECIMAL\ndef result():\n return NM_DECIMAL + 1\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root,
        ("constant_example.entry",),
        callables=("constant_example.entry.result",),
        external_runtime=acquire_codec_runtime(),
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity) as verify:
        module = importlib.import_module("constant_example.entry")
        assert module.result() == 3
        verify()


@pytest.mark.parametrize(
    "expression",
    [
        "rapidjson.loads(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False)",
        "rapidjson.dumps({'value': 7}, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE).encode()",
    ],
)
def test_exact_native_json_codec_configuration_has_authenticated_custody(
    tmp_path, monkeypatch, expression
):
    package = "json_decode_example" if "loads" in expression else "json_encode_example"
    entry = package + ".entry"
    root = tmp_path / package
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "import rapidjson\ndef result(content):\n return " + expression + "\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root,
        (entry,),
        callables=(entry + ".result",),
        external_runtime=acquire_codec_runtime(),
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity) as verify:
        module = importlib.import_module(entry)
        if "loads" in expression:
            from decimal import Decimal

            assert module.result(b'{"value": 0.0100}') == {"value": Decimal("0.0100")}
        else:
            assert module.result({"value": 7}) == b'{"value":7}'
        verify()


@pytest.mark.parametrize(
    "options",
    [
        "number_mode=rapidjson.NM_DECIMAL, allow_nan=False, object_hook=callback",
        "number_mode=rapidjson.NM_NATIVE, allow_nan=False",
        "number_mode=rapidjson.NM_DECIMAL",
        "number_mode=rapidjson.NM_DECIMAL, allow_nan=True",
        "number_mode=rapidjson.NM_DECIMAL, allow_nan=False, parse_mode=1",
        "**callback",
    ],
)
def test_unmodeled_native_json_options_keep_workload_incomplete(tmp_path, options):
    root = tmp_path / "unsupported_json"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "import rapidjson\ndef result(content, callback):\n return rapidjson.loads(content, "
        + options
        + ")\n"
    )
    identity = capture_code_identity(
        root,
        ("unsupported_json.entry",),
        callables=("unsupported_json.entry.result",),
        external_runtime=acquire_codec_runtime(),
    )
    assert not identity.complete
    assert any("exact finite codec configuration" in item.reason for item in identity.unknowns)


@pytest.mark.parametrize(
    "expression",
    [
        "rapidjson.loads.__dict__",
        "rapidjson.dumps({'a':7}, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE).encode().decode().format(content)",
        "rapidjson.dumps('{}', number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE).format(content)",
        "rapidjson.dumps({'a':7}, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE).encode(content)",
        "rapidjson.dumps({'a':content}, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE)",
        "rapidjson.loads(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False).arbitrary()",
        "rapidjson.dumps(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True, ensure_ascii=False, bytes_mode=rapidjson.BM_NONE)",
    ],
)
def test_json_options_do_not_authorize_opaque_attributes_or_unowned_encoding(tmp_path, expression):
    root = tmp_path / "unowned_json"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "import rapidjson\ndef result(content):\n return " + expression + "\n"
    )
    identity = capture_code_identity(
        root,
        ("unowned_json.entry",),
        callables=("unowned_json.entry.result",),
        external_runtime=acquire_codec_runtime(),
    )
    assert not identity.complete


def test_frozen_slotted_snapshot_has_checked_runtime_descriptors(tmp_path, monkeypatch):
    import importlib

    from corpus_structure._query_custody import SourceCustodyError
    from corpus_structure.semantic.code_identity import (
        authenticate_workload,
        capture_code_identity,
    )

    root = tmp_path / "slotted_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True, slots=True)\n"
        "class Snapshot:\n    value: str\n"
        "def result(item):\n"
        "    if type(item) is not Snapshot:\n        raise TypeError('invalid snapshot')\n"
        "    return item.value\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root, ("slotted_example.entry",), callables=("slotted_example.entry.result",)
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity):
        module = importlib.import_module("slotted_example.entry")
        assert module.result(module.Snapshot("owned")) == "owned"
    monkeypatch.setattr(module.Snapshot, "value", "replaced")
    with (
        pytest.raises(SourceCustodyError, match="runtime slice changed"),
        authenticate_workload(root, identity),
    ):
        pass


def test_actual_json_decoder_wrapper_has_live_codec_and_annotation_custody():
    from pathlib import Path

    from corpus_structure.semantic import data_operation_json

    root = Path(data_operation_json.__file__).parents[1]
    identity = capture_code_identity(
        root,
        ("corpus_structure.semantic.data_operation_json",),
        callables=("corpus_structure.semantic.data_operation_json.json_loads",),
        external_runtime=acquire_codec_runtime(),
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity) as verify:
        assert data_operation_json.json_loads(b'{"count":7}') == {"count": 7}
        verify()


@pytest.mark.parametrize("expression", ["Any()", "Any.__mro__", "Any[int]"])
def test_passive_any_annotation_does_not_admit_runtime_or_subscription(tmp_path, expression):
    root = tmp_path / "annotation_example"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from typing import Any\ndef result():\n return " + expression + "\n"
    )
    identity = capture_code_identity(
        root, ("annotation_example.entry",), callables=("annotation_example.entry.result",)
    )
    assert not identity.complete


def test_bare_any_annotation_rechecks_its_consumed_import_binding(tmp_path, monkeypatch):
    from corpus_structure._query_custody import SourceCustodyError

    root = tmp_path / "passive_any"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from typing import Any\ndef result(value: Any) -> Any:\n return value\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root, ("passive_any.entry",), callables=("passive_any.entry.result",)
    )
    assert identity.complete, identity.unknowns
    with (
        pytest.raises(SourceCustodyError, match="changed"),
        authenticate_workload(root, identity) as verify,
    ):
        module = importlib.import_module("passive_any.entry")
        monkeypatch.setattr(module, "Any", int)
        verify()


def test_direct_import_aliases_keep_the_exact_native_json_options(tmp_path, monkeypatch):
    root = tmp_path / "aliased_json"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from rapidjson import loads as decode, NM_DECIMAL as mode\n"
        "def result(content: bytes):\n return decode(content, number_mode=mode, allow_nan=False)\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    identity = capture_code_identity(
        root,
        ("aliased_json.entry",),
        callables=("aliased_json.entry.result",),
        external_runtime=acquire_codec_runtime(),
    )
    assert identity.complete, identity.unknowns
    with authenticate_workload(root, identity) as verify:
        module = importlib.import_module("aliased_json.entry")
        assert module.result(b'{"value":true}') == {"value": True}
        verify()


def test_any_subscription_in_annotation_is_still_required_uncertainty(tmp_path):
    root = tmp_path / "subscribed_any"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "entry.py").write_text(
        "from __future__ import annotations\nfrom typing import Any\n"
        "def result(value: Any[int]):\n return value\n"
    )
    identity = capture_code_identity(
        root, ("subscribed_any.entry",), callables=("subscribed_any.entry.result",)
    )
    assert not identity.complete
    assert any("bare verified annotation" in item.reason for item in identity.unknowns)
