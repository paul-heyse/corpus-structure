"""Independent direct callable, ingress, nominal-role and permission controls."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import (
    DataOperationWireValue,
    PortRefusal,
    PythonRoleValue,
    RoleValue,
    python_port_identity,
    resolve_python_port,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


def actual():
    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    sources = PythonSourceCollection(
        (PythonSource("corpus_structure.semantic.identity", path.read_bytes(), str(path)),)
    )
    return compile_data_operations(python_sources=sources), sources


def kind(model, role):
    name = next(r.kind for r in model.operations[0].roles if r.name == role)
    return next(i.key for i in model.identities if i.owner == name and i.domain == "kind")


def fixture_source(
    tmp_path,
    monkeypatch,
    signature="index: int = 2",
    body="return str(index)",
    *,
    metadata=None,
    header="",
):
    declaration = copy.deepcopy(metadata or claim_source_item__data_operation__)
    name = "ddo_port_" + tmp_path.name.replace("-", "_")
    source = (
        f"{header}\ndef derive({signature}) -> str:\n    {body}\n"
        f"derive__data_operation__ = {declaration!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    inputs = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    return compile_data_operations(python_sources=inputs), inputs


def test_actual_direct_function_uses_exact_roles_and_original_callable():
    model, sources = actual()
    observed = []
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=observed.append
    )
    assert port.function.__name__ == "claim_source_item"
    completed = port.invoke_python((PythonRoleValue("index", kind(model, "index"), 7),))
    assert completed.outputs[0].value() == "claims/7"
    assert completed.outputs[0].kind_contract == kind(model, "address")
    assert len(observed) == 2  # acquisition and invocation use the acquired owner
    assert observed[0].recipe.startswith("recipe:")
    with pytest.raises(ValidationError):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), True),))
    with pytest.raises(PortRefusal, match="nominal kind"):
        port.invoke_python((PythonRoleValue("index", kind(model, "address"), 7),))
    with pytest.raises(PortRefusal, match="unknown or repeated"):
        port.invoke_python((PythonRoleValue("other", kind(model, "index"), 7),))


def test_original_defaults_positional_only_and_keyword_only_are_authoritative(
    tmp_path, monkeypatch
):
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"].insert(
        1,
        {
            "name": "prefix",
            "parameter": "prefix",
            "kind": "string",
            "direction": "input",
            "minimum": 1,
            "maximum": 1,
            "collection": "scalar",
            "presence": "required",
            "support": {
                "provenance": "value_substitution",
                "source": "prefix",
                "coverage": "one-value",
            },
        },
    )
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int = 2, /, *, prefix: str = 'p'",
        "return prefix + str(index)",
        metadata=metadata,
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert port.invoke_python(()).outputs[0].value() == "p2"
    assert (
        port.invoke_json((RoleValue("prefix", kind(model, "prefix"), b'"q"'),)).outputs[0].value()
        == "q2"
    )
    with pytest.raises(PortRefusal, match="unknown or repeated"):
        port.invoke_python(
            (
                PythonRoleValue("prefix", kind(model, "prefix"), "a"),
                PythonRoleValue("prefix", kind(model, "prefix"), "b"),
            )
        )


def test_invalid_original_default_refuses_even_when_call_could_override_it(tmp_path, monkeypatch):
    model, inputs = fixture_source(tmp_path, monkeypatch, "index: int = 'wrong'")
    with pytest.raises(ValidationError):
        resolve_python_port(
            model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
        )


def test_strict_json_and_python_collection_routes_are_deliberately_different(tmp_path, monkeypatch):
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"][0].update(collection="sequence", minimum=1, maximum=None)
    model, inputs = fixture_source(
        tmp_path, monkeypatch, "index: tuple[int, ...]", metadata=metadata
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert (
        port.invoke_json((RoleValue("index", kind(model, "index"), b"[1,2]"),)).outputs[0].value()
        == "(1, 2)"
    )
    with pytest.raises(ValidationError):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), [1, 2]),))
    assert (
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), (1, 2)),))
        .outputs[0]
        .value()
        == "(1, 2)"
    )
    with pytest.raises(ValidationError):
        port.invoke_json((RoleValue("index", kind(model, "index"), b"[true]"),))


def test_static_source_preparation_never_imports_target_and_extraction_is_not_permission(
    tmp_path, monkeypatch
):
    model, sources = fixture_source(
        tmp_path, monkeypatch, header="raise RuntimeError('must not execute')"
    )
    identity = python_port_identity(model, sources, model.operations[0].semantic_id)
    assert identity.declaration.endswith(".derive")

    def denied(_):
        raise PermissionError("target is not admitted")

    with pytest.raises(PermissionError, match="not admitted"):
        resolve_python_port(model, sources, model.operations[0].semantic_id, authorize=denied)


def test_changed_source_or_runtime_function_cannot_keep_an_admitted_port(tmp_path, monkeypatch):
    model, inputs = fixture_source(tmp_path, monkeypatch)
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    original_code = port.function.__code__

    def replaced(index: int = 2) -> str:
        return "wrong"

    monkeypatch.setattr(port.function, "__code__", replaced.__code__)
    with pytest.raises(PortRefusal, match="implementation differs"):
        port.invoke_python(())
    monkeypatch.setattr(port.function, "__code__", original_code)
    monkeypatch.setattr(port.function, "__defaults__", (99,))
    with pytest.raises(PortRefusal, match="default differs"):
        port.invoke_python(())


def test_effects_and_multioutput_need_actual_completion_capability(tmp_path, monkeypatch):
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"].append({**metadata["roles"][-1], "name": "second-address"})
    metadata["profile"] = "command"
    metadata["effects"] = [
        {
            "name": "publish",
            "authorization": ["native-publication"],
            "idempotency": "one-bundle",
            "fulfillment": "native-receipt",
        }
    ]
    model, sources = fixture_source(tmp_path, monkeypatch, metadata=metadata)
    assert python_port_identity(model, sources, model.operations[0].semantic_id).recipe
    with pytest.raises(PortRefusal, match="explicit admitted implementation capability"):
        resolve_python_port(
            model, sources, model.operations[0].semantic_id, authorize=lambda _: None
        )
    # Matching output contents never manufacture an effect or publication receipt.
    assert (
        json.loads(RoleValue("address", kind(model, "address"), b'"claims/2"').content)
        == "claims/2"
    )


def test_wire_defaults_extra_fields_model_construct_and_nested_ownership():
    class Input(DataOperationWireValue):
        payload: dict[str, list[int]]

    original = {"items": [1, 2]}
    value = Input.model_validate({"payload": original}, strict=True)
    original["items"].append(3)
    value.payload["items"].append(4)
    assert value.payload == {"items": [1, 2]}
    untrusted = Input.model_construct(payload={"items": [True]})
    with pytest.raises(ValidationError):
        Input.model_validate(untrusted, strict=True)
    with pytest.raises(ValidationError):
        Input.model_validate_json('{"payload":{"items":[1]},"extra":2}', strict=True)

    class InvalidDefault(DataOperationWireValue):
        count: int = cast(Any, "bad")

    with pytest.raises(ValidationError):
        InvalidDefault()


def test_caller_forged_definition_cannot_reuse_complete_identities():
    model, sources = actual()
    operation = replace(model.operations[0], behavior="different-behavior")
    forged = replace(model, operations=(operation,))
    with pytest.raises(PortRefusal, match="facts differ"):
        python_port_identity(forged, sources, operation.semantic_id)


@pytest.mark.parametrize(
    "relative,module",
    [
        ("semantic/operation_policy.py", "corpus_structure.semantic.operation_policy"),
        ("methods/interpretations.py", "corpus_structure.methods.interpretations"),
    ],
)
def test_actual_score_and_authored_family_unknown_recipes_do_not_gain_execution(relative, module):
    source = Path(__file__).parents[2] / "src/corpus_structure" / relative
    sources = PythonSourceCollection((PythonSource(module, source.read_bytes(), str(source)),))
    model = compile_data_operations(python_sources=sources)
    assert model.operations
    for operation in model.operations:
        with pytest.raises(PortRefusal):
            resolve_python_port(
                model,
                sources,
                operation.semantic_id,
                authorize=lambda _: pytest.fail(
                    "incomplete extraction cannot reach acquired execution authority"
                ),
            )


@pytest.mark.parametrize(
    "root_import", ["from {package}.api import public as renamed", "import {package}.api as api"]
)
def test_import_and_reexport_rebinding_refuses_before_original_callable_body(
    tmp_path, monkeypatch, root_import
):
    package = "ddo_alias_" + tmp_path.name.replace("-", "_")
    package_path = tmp_path / package
    package_path.mkdir()
    (package_path / "__init__.py").write_text("")
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    reference = "renamed" if root_import.startswith("from ") else "api.public"
    sources = {
        package: (package_path / "__init__.py", ""),
        package + ".impl": (
            package_path / "impl.py",
            "def helper(index: int) -> str:\n    return str(index)\n",
        ),
        package + ".api": (package_path / "api.py", "from .impl import helper as public\n"),
        package + ".application": (
            package_path / "application.py",
            root_import.format(package=package)
            + f"\ndef derive(index: int = 2) -> str:\n    return {reference}(index)\n"
            + f"derive__data_operation__ = {metadata!r}\n",
        ),
    }
    for path, content in sources.values():
        path.write_text(content)
    monkeypatch.syspath_prepend(str(tmp_path))
    collection = PythonSourceCollection(
        tuple(
            PythonSource(name, content.encode(), str(path))
            for name, (path, content) in sources.items()
        )
    )
    model = compile_data_operations(python_sources=collection)
    import importlib

    check: Callable[[], object]
    if any(item.required for item in model.implementation_slices[0].unknowns):
        # The current static frontend withholds a module-object recipe. Preserve
        # that refusal and independently challenge the runtime guard on those
        # captured facts; this never fabricates execution admission.
        with pytest.raises(PortRefusal, match="correspondence is unavailable"):
            resolve_python_port(
                model,
                collection,
                model.operations[0].semantic_id,
                authorize=lambda _: pytest.fail("incomplete module cannot be admitted"),
            )
        from corpus_structure.semantic.data_operation_ports import _verify_runtime_sources

        modules = {
            source.module: importlib.import_module(source.module) for source in collection.sources
        }

        def check():
            return _verify_runtime_sources(model, model.operations[0], collection, modules)

        check()
    else:
        port = resolve_python_port(
            model, collection, model.operations[0].semantic_id, authorize=lambda _: None
        )
        assert port.invoke_python(()).outputs[0].value() == "2"

        def check():
            return port.invoke_python(())

    application = importlib.import_module(package + ".application")
    api = importlib.import_module(package + ".api")
    called = []

    def malicious(index: int) -> str:
        called.append(index)
        return "different"

    if reference == "renamed":
        monkeypatch.setattr(application, "renamed", malicious)
    else:
        monkeypatch.setattr(api, "public", malicious)
    with pytest.raises(PortRefusal, match="rebound"):
        check()
    assert called == []


def test_local_function_alias_rebinding_is_checked_transitively(tmp_path, monkeypatch):
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    name = "ddo_local_alias_" + tmp_path.name.replace("-", "_")
    text = (
        "def helper(index: int) -> str:\n    return str(index)\nrenamed = helper\n"
        "def derive(index: int = 2) -> str:\n    return renamed(index)\n"
        + f"derive__data_operation__ = {metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(text)
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection((PythonSource(name, text.encode(), str(path)),))
    model = compile_data_operations(python_sources=sources)
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    assert port.invoke_python(()).outputs[0].value() == "2"
    import importlib

    module = importlib.import_module(name)
    monkeypatch.setattr(module, "renamed", lambda index: "wrong")
    with pytest.raises(PortRefusal, match="rebound"):
        port.invoke_python(())
