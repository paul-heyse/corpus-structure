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
    returns="str",
    profiles=(),
):
    declaration = copy.deepcopy(metadata or claim_source_item__data_operation__)
    name = "ddo_port_" + tmp_path.name.replace("-", "_")
    source = (
        f"{header}\ndef derive({signature}) -> {returns}:\n    {body}\n"
        f"derive__data_operation__ = {declaration!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    inputs = PythonSourceCollection(
        (PythonSource(name, source.encode(), str(path)),), generated_interfaces=profiles
    )
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
    assert completed.outcome == "addressed"
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


def test_frozen_semantic_parameters_drive_original_callable(tmp_path, monkeypatch):
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_demands import ReadyDataRequest
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["parameters"] = {"prefix": {"value_type": "string", "default": "p"}}
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int, *, prefix: str = 'p'",
        "return prefix + str(index)",
        metadata=metadata,
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    binding = BindingResult(
        port.identity.operation,
        "subject:one",
        (),
        "ready",
        (),
        canonical_bytes(semantic_value({"prefix": "selected:"})),
        b"{}",
        model.version,
        port.identity.definition,
        port.identity.eligibility,
        (),
    )
    values = (PythonRoleValue("index", kind(model, "index"), 7),)
    from corpus_structure.semantic.data_operation_model import SubjectContext

    resolved = binding.resolved(
        inference="exact",
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="cpu",
        subject_context=SubjectContext("project:test", binding.subject, "source:test", b"{}"),
    )
    ready = ReadyDataRequest(
        "obligation:one",
        binding.operation,
        binding.subject,
        b"{}",
        b"{}",
        b'{"action":"compute","retained_intent_id":null}',
        b"{}",
        resolved,
        binding,
    )
    assert (
        port.invoke_python(values, binding=ready.binding_result).outputs[0].value() == "selected:7"
    )
    with pytest.raises(ValueError, match="original binding"):
        replace(ready, binding_result=replace(binding, parameters=b"different"))
    assert (
        port.invoke_json((RoleValue("index", kind(model, "index"), b"7"),), binding=binding)
        .outputs[0]
        .value()
        == "selected:7"
    )
    for altered in (replace(binding, definition="stale"), replace(binding, eligibility="stale")):
        with pytest.raises(PortRefusal, match="admitted contract"):
            port.invoke_python(values, binding=altered)
    with pytest.raises(ValueError, match="string"):
        port.invoke_python(
            values,
            binding=replace(binding, parameters=canonical_bytes(semantic_value({"prefix": 3}))),
        )
    with pytest.raises(PortRefusal, match="undeclared"):
        port.invoke_python(
            values,
            binding=replace(binding, parameters=canonical_bytes(semantic_value({"unknown": "x"}))),
        )


def bundle_metadata():
    value = copy.deepcopy(claim_source_item__data_operation__)
    value["roles"].append({**value["roles"][-1], "name": "other"})
    value["result_fields"] = {"address": "left", "other": "right"}
    return value


def test_explicit_atomic_mapping_outputs_preserve_roles_and_archived_correspondence(
    tmp_path, monkeypatch
):
    from corpus_structure.semantic.data_operation_model import read_effective_data_operations

    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        'return {"left": str(index), "right": str(index + 1)}',
        returns="dict[str, str]",
        metadata=bundle_metadata(),
    )
    reopened = read_effective_data_operations(model.content)
    assert reopened == model
    assert dict(reopened.operations[0].result_fields) == {"address": "left", "other": "right"}
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    values = (PythonRoleValue("index", kind(model, "index"), 7),)
    completed = port.invoke_python(values)
    assert [(v.role, v.value()) for v in completed.outputs] == [("address", "7"), ("other", "8")]
    assert [v.kind_contract for v in completed.outputs] == [
        kind(model, "address"),
        kind(model, "other"),
    ]
    assert port.invoke_json((RoleValue("index", kind(model, "index"), b"7"),)) == completed


@pytest.mark.parametrize(
    "body",
    [
        'return {"left": str(index)}',
        'return {"left": str(index), "right": str(index), "extra": "surprise"}',
        'return {"left": str(index), "right": 3}',
    ],
)
def test_invalid_atomic_mapping_never_returns_partial_completion(tmp_path, monkeypatch, body):
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        body,
        returns="dict[str, str]",
        metadata=bundle_metadata(),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    with pytest.raises((PortRefusal, ValidationError)):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), 1),))


@pytest.mark.parametrize(
    "mapping",
    [
        {"address": "left"},
        {"address": "left", "other": "left"},
        {"address": "left", "unknown": "right"},
    ],
)
def test_invalid_output_correspondence_refuses_compilation(tmp_path, monkeypatch, mapping):
    from corpus_structure.semantic.types import PreparationError

    metadata = bundle_metadata()
    metadata["result_fields"] = mapping
    with pytest.raises(PreparationError, match="result fields"):
        fixture_source(
            tmp_path,
            monkeypatch,
            "index: int",
            'return {"left": str(index), "right": str(index)}',
            returns="dict[str, str]",
            metadata=metadata,
        )


def test_atomic_field_nominal_kind_must_match_original_return_type(tmp_path, monkeypatch):
    from corpus_structure.semantic.types import PreparationError

    metadata = bundle_metadata()
    metadata["roles"][-1]["kind"] = "integer"
    with pytest.raises(PreparationError, match="kind differs"):
        fixture_source(
            tmp_path,
            monkeypatch,
            "index: int",
            'return {"left": str(index), "right": str(index)}',
            returns="dict[str, str]",
            metadata=metadata,
        )


def test_plain_inherited_receiver_is_authenticated_and_keeps_nominal_outputs(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["entrypoints"] = ["run"]
    name = "receiver_" + tmp_path.name.replace("-", "_")
    source = (
        "class Base:\n    prefix = 'base:'\n"
        "    def run(self, index: int) -> str: return self.prefix + str(index)\n"
        "class Child(Base):\n    prefix = 'child:'\n"
        f"Child.__data_operation__ = {metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    inputs = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    model = compile_data_operations(python_sources=inputs)
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    value = PythonRoleValue("index", kind(model, "index"), 3)
    result = port.invoke_python((value,))
    assert result.outputs[0].value() == "child:3"
    assert result.outputs[0].meaning == b'["string","child:3"]'
    import inspect

    assert inspect.ismethod(port.function)
    monkeypatch.setattr(type(port.function.__self__), "prefix", "changed:")
    with pytest.raises(PortRefusal, match="constant determinant"):
        port.invoke_python((value,))


def test_native_batch_invokes_one_original_call_and_retains_order(tmp_path, monkeypatch):
    from corpus_structure.semantic.data_operation_ports import PythonBatchMember

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["batch"]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: tuple[int, ...]",
        "return tuple(str(item) for item in index)",
        metadata=metadata,
        returns="tuple[str, ...]",
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    members = tuple(
        PythonBatchMember(name, (PythonRoleValue("index", kind(model, "index"), value),))
        for name, value in (("second", 2), ("first", 1))
    )
    result = port.invoke_batch_python(members)
    assert [(key, completed.outputs[0].value()) for key, completed in result.members] == [
        ("second", "2"),
        ("first", "1"),
    ]
    with pytest.raises(PortRefusal, match="distinct"):
        port.invoke_batch_python((members[0], members[0]))
    with pytest.raises(PortRefusal, match="explicit member"):
        port.invoke_python(members[0].values)


@pytest.mark.parametrize(
    "body", ["return tuple(str(item) for item in index[:-1])", "return tuple(index)"]
)
def test_native_batch_refuses_incomplete_or_wrong_typed_whole_result(tmp_path, monkeypatch, body):
    from corpus_structure.semantic.data_operation_ports import PythonBatchMember

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["batch"]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: tuple[int, ...]",
        body,
        metadata=metadata,
        returns="tuple[str, ...]",
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    members = (PythonBatchMember("one", (PythonRoleValue("index", kind(model, "index"), 1),)),)
    with pytest.raises((PortRefusal, ValidationError)):
        port.invoke_batch_python(members)


def test_native_batch_json_uses_strict_individual_ingress(tmp_path, monkeypatch):
    from corpus_structure.semantic.data_operation_ports import JSONBatchMember

    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["batch"]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: tuple[int, ...]",
        "return tuple(str(item) for item in index)",
        metadata=metadata,
        returns="tuple[str, ...]",
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    result = port.invoke_batch_json(
        (JSONBatchMember("one", (RoleValue("index", kind(model, "index"), b"1"),)),)
    )
    assert result.members[0][1].outputs[0].meaning == b'["string","1"]'
    with pytest.raises(ValidationError):
        port.invoke_batch_json(
            (JSONBatchMember("one", (RoleValue("index", kind(model, "index"), b"true"),)),)
        )


def test_receiver_refuses_unmodeled_custom_construction(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["entrypoints"] = ["run"]
    name = "receiver_constructor_" + tmp_path.name.replace("-", "_")
    source = (
        "class Receiver:\n    def __init__(self): self.prefix = 'dynamic'\n"
        "    def run(self, index: int) -> str: return str(index)\n"
        f"Receiver.__data_operation__ = {metadata!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    inputs = PythonSourceCollection((PythonSource(name, source.encode(), str(path)),))
    model = compile_data_operations(python_sources=inputs)
    with pytest.raises(PortRefusal, match="construction"):
        resolve_python_port(
            model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
        )


def test_logical_archive_origin_can_resolve_exact_relocated_runtime(tmp_path, monkeypatch):
    model, inputs = fixture_source(tmp_path, monkeypatch)
    source = inputs.sources[0]
    archived = replace(source, filename="captured/operation.py")
    sources = replace(inputs, sources=(archived,))
    model = compile_data_operations(python_sources=sources)
    port = resolve_python_port(
        model,
        sources,
        model.operations[0].semantic_id,
        authorize=lambda identity: None,
        runtime_locations={source.module: Path(source.filename)},
    )
    assert port.invoke_python(()).outputs[0].value() == "2"
    Path(source.filename).write_text('def derive(index: int = 2) -> str:\n    return "wrong"\n')
    with pytest.raises(PortRefusal, match="source changed"):
        port.invoke_python(())


def test_execution_admission_serializes_capability_meaning_and_checks_exact_identity():
    from corpus_structure.semantic.data_operation_admission import (
        AcquiredPythonExecution,
        _source_identity_bytes,
    )
    from corpus_structure.semantic.refusals import SemanticRefusal

    model, sources = actual()
    identity = python_port_identity(model, sources, model.operations[0].semantic_id)
    captured = _source_identity_bytes(identity)
    assert json.loads(captured)["capabilities"]["forms"] == ["scalar"]
    admission = AcquiredPythonExecution(captured, "release", "runtime", "attestation")
    admission.authorize(identity)
    with pytest.raises(SemanticRefusal, match="differs"):
        admission.authorize(replace(identity, implementation="wrong"))


def test_data_stream_is_pull_bounded_typed_and_has_terminal_standing(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["stream"]
    metadata["opaque"] = [
        {
            "reference": "collections.abc.Iterator",
            "contract": "python-iterator-annotation",
            "role": "annotation",
            "content_digest": "a" * 64,
        }
    ]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "yield str(index)\n    yield str(index + 1)",
        metadata=metadata,
        header="from collections.abc import Iterator",
        returns="Iterator[str]",
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    stream = port.open_stream_python((PythonRoleValue("index", kind(model, "index"), 3),))
    assert stream.terminal is None
    assert next(stream)[1].outputs[0].value() == "3"
    assert stream.terminal is None
    assert next(stream)[0] == 1
    with pytest.raises(StopIteration):
        next(stream)
    assert stream.terminal is not None
    assert (stream.terminal.state, stream.terminal.items) == ("complete", 2)
    stream.close()
    assert stream.terminal.state == "complete"


def test_data_stream_close_and_cancel_never_mark_prefix_complete(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["capabilities"]["forms"] = ["stream"]
    metadata["opaque"] = [
        {
            "reference": "collections.abc.Iterator",
            "contract": "python-iterator-annotation",
            "role": "annotation",
            "content_digest": "a" * 64,
        }
    ]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "yield str(index)\n    yield str(index + 1)",
        metadata=metadata,
        header="from collections.abc import Iterator",
        returns="Iterator[str]",
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    value = PythonRoleValue("index", kind(model, "index"), 3)
    with port.open_stream_python((value,)) as stream:
        assert next(stream)[0] == 0
    assert stream.terminal is not None
    assert (stream.terminal.state, stream.terminal.items) == ("cancelled", 1)
    calls = []

    def active():
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError("cancelled")

    stream = port.open_stream_python((value,), check_active=active)
    next(stream)
    with pytest.raises(RuntimeError, match="cancelled"):
        next(stream)
    assert stream.terminal is not None
    assert stream.terminal.state == "failed"
    import inspect

    assert inspect.isgenerator(stream._iterator)
    assert stream._iterator.gi_frame is None


def test_publication_port_requires_the_native_effect_receipt_and_preserves_replay():
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_ports import ResolvedPublicationPort

    seen = []
    result = {
        "receipt_id": "receipt:one",
        "derivation_id": "derivation:original",
        "replayed": False,
        "trust_snapshot": {},
    }

    def invoke(name, payload):
        seen.append((name, payload))
        return result

    port = ResolvedPublicationPort(SimpleNamespace(invoke=invoke), "request:kind", "result:kind")
    value = RoleValue("request", "request:kind", b'{"intent_id":"original"}')
    first = port.invoke_json(value)
    assert first.receipt_id == "receipt:one"
    assert first.derivation_id == "derivation:original"
    result["replayed"] = True
    replay = port.invoke_json(value)
    assert replay.receipt_id == first.receipt_id
    assert replay.result.value()["replayed"] is True
    assert seen == [("publish_data_derivation", {"intent_id": "original"})] * 2
    result.clear()
    result["output"] = first.result.value()
    with pytest.raises(PortRefusal, match="required effect receipt"):
        port.invoke_json(value)
    with pytest.raises(PortRefusal, match="nominal request"):
        port.invoke_json(RoleValue("request", "another:kind", value.content))


@pytest.mark.parametrize("frozen", [False, True])
def test_generated_dataclass_runtime_constructor_keeps_defaults_and_nominal_ingress(
    tmp_path, monkeypatch, frozen
):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"][0]["kind"] = "urn:test:generated-input"
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-input",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item",
        }
    ]
    header = f"""from dataclasses import dataclass, field

def make_label() -> str:
    return 'default'

@dataclass(kw_only=True, frozen={frozen})
class Item:
    value: int
    label: str = field(default_factory=make_label)
"""
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return str(index.value) + index.label",
        metadata=metadata,
        header=header,
        profiles=("dataclasses-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    completed = port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))
    assert completed.outputs[0].value() == "3default"
    import importlib

    module = importlib.import_module(inputs.sources[0].module)
    checked = module.Item(value=4, label="chosen")
    assert (
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), checked),))
        .outputs[0]
        .value()
        == "4chosen"
    )
    object.__setattr__(checked, "value", True)
    with pytest.raises(ValidationError):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), checked),))
    with pytest.raises(PortRefusal, match="undeclared fields"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3,"extra":1}'),))
    monkeypatch.setattr(module.Item, "__init__", lambda self, **kwargs: None)
    with pytest.raises(PortRefusal, match="constructor implementation"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))


def test_generated_typeddict_ingress_preserves_original_kwargs_signature(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"][0].update(kind="urn:test:generated-options", parameter="kwargs")
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-options",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Options",
        }
    ]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "**kwargs: Unpack[Options]",
        "return str(kwargs['value'])",
        metadata=metadata,
        header=(
            "from typing import TypedDict, Unpack, NotRequired\n"
            "class Options(TypedDict):\n    value: int\n    label: NotRequired[str]"
        ),
        profiles=("unpack-typeddict-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    import inspect

    assert port.signature.parameters["kwargs"].kind == inspect.Parameter.VAR_KEYWORD
    completed = port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":5}'),))
    assert completed.outputs[0].value() == "5"
    with pytest.raises((PortRefusal, ValidationError)):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":true}'),))
    with pytest.raises(PortRefusal, match="undeclared fields"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":5,"other":1}'),))


def test_generated_record_output_has_typed_canonical_body(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    owner = "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item"
    metadata["kinds"] = [{"id": "urn:test:record", "python": owner}]
    for role in metadata["roles"]:
        role["kind"] = "urn:test:record"
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return index",
        metadata=metadata,
        header=(
            "from dataclasses import dataclass\n@dataclass(kw_only=True)\n"
            "class Item:\n    value: int"
        ),
        returns="Item",
        profiles=("dataclasses-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    result = port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))
    assert result.outputs[0].value() == {"value": 3}
    assert result.outputs[0].meaning == b'["mapping",[["value",["integer","3"]]]]'


def test_ambiguous_success_return_refuses_before_authorization_or_target_import(tmp_path, monkeypatch):
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["outcomes"].append("other-address")
    metadata["transitions"].append({"dimension": "completion", "before": "pending",
                                    "after": "success", "outcome": "other-address"})
    model, inputs = fixture_source(tmp_path, monkeypatch, metadata=metadata,
                                  header="raise RuntimeError('target must not import')")
    with pytest.raises(PortRefusal, match="unambiguous"):
        resolve_python_port(model, inputs, model.operations[0].semantic_id,
                            authorize=lambda _: pytest.fail("ambiguous return was authorized"))
