"""Independent direct callable, ingress, nominal-role and permission controls."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import (
    DataOperationWireValue,
    HydratedRoleValue,
    PortRefusal,
    PythonRoleValue,
    RoleValue,
    python_port_identity,
    resolve_python_port,
)
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.data_operation_port_support import controlled_port_declaration, fixture_source, kind


def actual():
    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    sources = PythonSourceCollection(
        (PythonSource("corpus_structure.semantic.identity", path.read_bytes(), str(path)),)
    )
    return compile_data_operations(python_sources=sources), sources


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
    metadata: dict[str, Any] = controlled_port_declaration()
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
                "coverage": {"role": "prefix", "description": "one-value"},
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
    metadata: dict[str, Any] = controlled_port_declaration()
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
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_python(())
    monkeypatch.setattr(port.function, "__code__", original_code)
    monkeypatch.setattr(port.function, "__defaults__", (99,))
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_python(())


def test_effects_and_multioutput_need_actual_completion_capability(tmp_path, monkeypatch):
    metadata: dict[str, Any] = controlled_port_declaration()
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
    "root_import", ["from {package}.api import public as renamed", "import {package}.api as api"]
)
def test_import_and_reexport_rebinding_refuses_before_original_callable_body(
    tmp_path, monkeypatch, root_import
):
    package = "ddo_alias_" + tmp_path.name.replace("-", "_")
    package_path = tmp_path / package
    package_path.mkdir()
    (package_path / "__init__.py").write_text("")
    metadata: dict[str, Any] = controlled_port_declaration()
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
    with pytest.raises(
        PortRefusal,
        match=r"authenticated runtime slice changed|runtime consumed import or alias was rebound",
    ):
        check()
    assert called == []


def test_local_function_alias_rebinding_is_checked_transitively(tmp_path, monkeypatch):
    metadata: dict[str, Any] = controlled_port_declaration()
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
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_python(())


def test_frozen_semantic_parameters_drive_original_callable(tmp_path, monkeypatch):
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_demands import ReadyDataRequest
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes

    metadata = controlled_port_declaration()
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
        replicate=None,
    )
    values = (PythonRoleValue("index", kind(model, "index"), 7),)
    from corpus_structure.semantic.data_operation_model import SubjectContext

    resolved = binding.resolved(
        inference="exact",
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="cpu",
        subject_context=SubjectContext(
            "project:test", binding.subject, "source:test", b"{}", subject_definition="document"
        ),
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
    value = controlled_port_declaration()
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
    metadata = controlled_port_declaration()
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
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_python((value,))


def test_native_batch_invokes_one_original_call_and_retains_order(tmp_path, monkeypatch):
    from corpus_structure.semantic.data_operation_ports import PythonBatchMember

    metadata = controlled_port_declaration()
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

    metadata = controlled_port_declaration()
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

    metadata = controlled_port_declaration()
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
    metadata = controlled_port_declaration()
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
    with pytest.raises(PortRefusal, match="acquired file changed"):
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
    metadata = controlled_port_declaration()
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
    metadata = controlled_port_declaration()
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


@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("future_annotations", [False, True])
def test_generated_dataclass_runtime_constructor_keeps_defaults_and_nominal_ingress(
    tmp_path, monkeypatch, frozen, future_annotations
):
    metadata = controlled_port_declaration()
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
    if future_annotations:
        header = "from __future__ import annotations\n" + header
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
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))


def test_generated_typeddict_ingress_preserves_original_kwargs_signature(tmp_path, monkeypatch):
    metadata = controlled_port_declaration()
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


@pytest.mark.parametrize("kw_only", [False, True])
@pytest.mark.parametrize("factory", [False, True])
@pytest.mark.parametrize("mutate_fields", [False, True])
def test_generated_constructor_refuses_mutated_defaults(
    tmp_path, monkeypatch, kw_only, factory, mutate_fields
):
    metadata = controlled_port_declaration()
    metadata["roles"][0]["kind"] = "urn:test:generated-input"
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-input",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item",
        }
    ]
    field_value = "field(default_factory=make_value)" if factory else "(1,)"
    header = f"""from dataclasses import dataclass, field
def make_value() -> tuple[int, ...]:
    return (1,)
@dataclass(kw_only={kw_only})
class Item:
    value: tuple[int, ...] = {field_value}
"""
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return str(index.value)",
        metadata=metadata,
        header=header,
        profiles=("dataclasses-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    constructor = port.function.__globals__["Item"].__init__
    # Keep source fields and generated bytecode untouched. Only the live Python
    # constructor default changes; nested bool/int equality cannot hide it.
    changed = (2,) if factory else (True,)
    attribute = "__kwdefaults__" if kw_only else "__defaults__"
    replacement = {"value": changed} if kw_only else (changed,)
    monkeypatch.setattr(constructor, attribute, replacement)
    if mutate_fields:
        item = port.function.__globals__["Item"]
        monkeypatch.setattr(item.__dataclass_fields__["value"], "default", changed)
        monkeypatch.setattr(item, "value", changed, raising=False)
    message = "default or factory" if mutate_fields else "constructor .*defaults differ"
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b"{}"),))
    with pytest.raises(PortRefusal, match=message):
        resolve_python_port(
            model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "__repr__",
        "__eq__",
        "__replace__",
        "__hash__",
        "__setattr__",
        "__delattr__",
        "wrapped",
        "repr_closure",
        "repr_wrapped_code",
        "repr_running",
        "qualname",
        "match_args",
        "field_behavior",
        "annotations",
        "hash_global",
    ],
)
def test_generated_dataclass_refuses_changed_standard_behavior(tmp_path, monkeypatch, mutation):
    metadata = controlled_port_declaration()
    metadata["roles"][0]["kind"] = "urn:test:generated-input"
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-input",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item",
        }
    ]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return str(index.value)",
        metadata=metadata,
        header=(
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\nclass Item:\n    value: int = 1"
        ),
        profiles=("dataclasses-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    item = port.function.__globals__["Item"]
    assert (
        port.invoke_json((RoleValue("index", kind(model, "index"), b"{}"),)).outputs[0].value()
        == "1"
    )
    if mutation == "wrapped":
        monkeypatch.setattr(item.__repr__, "__wrapped__", lambda self: "changed")
    elif mutation == "repr_closure":
        cells = dict(
            zip(item.__repr__.__code__.co_freevars, item.__repr__.__closure__, strict=True)
        )
        monkeypatch.setattr(cells["fillvalue"], "cell_contents", "changed")
    elif mutation == "repr_wrapped_code":
        monkeypatch.setattr(
            item.__repr__.__wrapped__, "__code__", (lambda self: "changed").__code__
        )
    elif mutation == "repr_running":
        cells = dict(
            zip(item.__repr__.__code__.co_freevars, item.__repr__.__closure__, strict=True)
        )
        monkeypatch.setattr(cells["repr_running"], "cell_contents", {(0, 0)})
    elif mutation == "qualname":
        original = item.__qualname__
        item.__qualname__ = "Changed"
        try:
            with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
                port.invoke_json((RoleValue("index", kind(model, "index"), b"{}"),))
        finally:
            item.__qualname__ = original
        return
    elif mutation == "match_args":
        monkeypatch.setattr(item, "__match_args__", ())
    elif mutation == "field_behavior":
        monkeypatch.setattr(item.__dataclass_fields__["value"], "repr", False)
    elif mutation == "annotations":
        monkeypatch.setattr(item, "__annotations__", {"value": str})
    elif mutation == "hash_global":
        monkeypatch.setitem(port.function.__globals__, "hash", lambda _: 0)
    else:
        monkeypatch.setattr(item, mutation, lambda *args, **kwargs: "changed")
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b"{}"),))


@pytest.mark.parametrize(
    "declaration", ["1", "field(default=1)", "field(default_factory=make_value)", None]
)
def test_generated_dataclass_refuses_changed_class_field_value(tmp_path, monkeypatch, declaration):
    metadata = controlled_port_declaration()
    metadata["roles"][0]["kind"] = "urn:test:generated-input"
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-input",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item",
        }
    ]
    suffix = "" if declaration is None else " = " + declaration
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return str(index.value)",
        metadata=metadata,
        header="from dataclasses import dataclass, field\ndef make_value() -> int:\n    return 1\n"
        "@dataclass\nclass Item:\n    value: int" + suffix,
        profiles=("dataclasses-runtime",),
    )
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    monkeypatch.setattr(port.function.__globals__["Item"], "value", 9, raising=False)
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))


def test_generated_record_output_has_typed_canonical_body(tmp_path, monkeypatch):
    metadata = controlled_port_declaration()
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


def test_ambiguous_success_return_refuses_before_authorization_or_target_import(
    tmp_path, monkeypatch
):
    metadata = controlled_port_declaration()
    metadata["outcomes"].append("other-address")
    metadata["transitions"].append(
        {
            "dimension": "completion",
            "before": "pending",
            "after": "success",
            "outcome": "other-address",
        }
    )
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        metadata=metadata,
        header="raise RuntimeError('target must not import')",
    )
    with pytest.raises(PortRefusal, match="unambiguous"):
        resolve_python_port(
            model,
            inputs,
            model.operations[0].semantic_id,
            authorize=lambda _: pytest.fail("ambiguous return was authorized"),
        )


@pytest.mark.parametrize("through_helper", [False, True])
def test_captured_builtin_mapping_is_authenticated_on_acquisition_and_each_call(
    tmp_path, monkeypatch, through_helper
):
    import builtins
    import importlib
    import types

    body = "return helper(index)" if through_helper else "return str(len((index,)))"
    header = "def helper(index):\n    return str(len((index,)))\n" if through_helper else ""
    model, inputs = fixture_source(tmp_path, monkeypatch, body=body, header=header)
    module = importlib.import_module(inputs.sources[0].module)
    name = "helper" if through_helper else "derive"
    original = getattr(module, name)
    namespace = dict(vars(builtins))
    module.__dict__["__builtins__"] = namespace
    replacement = types.FunctionType(
        original.__code__, module.__dict__, original.__name__, original.__defaults__
    )
    replacement.__annotations__ = original.__annotations__
    setattr(module, name, replacement)
    # A function's captured mapping remains independent of later module globals.
    module.__dict__["__builtins__"] = vars(builtins)
    namespace["len"] = lambda value: 7
    with pytest.raises(PortRefusal, match=r"captured builtin.*len"):
        resolve_python_port(
            model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
        )
    namespace["len"] = len
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    values = (PythonRoleValue("index", kind(model, "index"), 2),)
    assert port.invoke_python(values).outputs[0].value() == "1"
    namespace["unconsumed_name"] = object()
    assert port.invoke_python(values).outputs[0].value() == "1"
    namespace["len"] = lambda value: 9
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_python(values)


def test_generated_method_checks_its_captured_builtin_mapping(tmp_path, monkeypatch):
    import builtins
    import importlib
    import types

    metadata = controlled_port_declaration()
    metadata["roles"][0]["kind"] = "urn:test:generated-input"
    metadata["kinds"] = [
        {
            "id": "urn:test:generated-input",
            "python": "ddo_port_" + tmp_path.name.replace("-", "_") + ".Item",
        }
    ]
    model, inputs = fixture_source(
        tmp_path,
        monkeypatch,
        "index: Item",
        "return str(index.value)",
        metadata=metadata,
        header="from dataclasses import dataclass\n@dataclass\nclass Item:\n    value: int\n",
        profiles=("dataclasses-runtime",),
    )
    module = importlib.import_module(inputs.sources[0].module)
    original = module.Item.__eq__
    namespace = dict(vars(builtins))
    globals_ = dict(original.__globals__, __builtins__=namespace)
    replacement = types.FunctionType(
        original.__code__, globals_, original.__name__, original.__defaults__, original.__closure__
    )
    module.Item.__eq__ = replacement
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    namespace["NotImplemented"] = object()
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        port.invoke_json((RoleValue("index", kind(model, "index"), b'{"value":3}'),))


def test_stream_pull_refuses_changed_captured_builtin_before_next_item(tmp_path, monkeypatch):
    import builtins
    import importlib
    import types

    metadata = controlled_port_declaration()
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
    module = importlib.import_module(inputs.sources[0].module)
    original = module.derive
    namespace = dict(vars(builtins))
    module.__dict__["__builtins__"] = namespace
    replacement = types.FunctionType(original.__code__, module.__dict__, original.__name__)
    replacement.__annotations__ = original.__annotations__
    module.__dict__["derive"] = replacement
    module.__dict__["__builtins__"] = vars(builtins)
    port = resolve_python_port(
        model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
    )
    stream = port.open_stream_python((PythonRoleValue("index", kind(model, "index"), 3),))
    assert next(stream)[1].outputs[0].value() == "3"
    namespace["str"] = lambda value: "changed"
    with pytest.raises(PortRefusal, match="authenticated runtime slice changed"):
        next(stream)
    assert stream.terminal is not None and stream.terminal.state == "failed"


def test_builtin_mapping_subclass_cannot_hide_runtime_lookup(tmp_path, monkeypatch):
    import builtins
    import importlib
    import types

    class AlternateLookup(dict):
        def __getitem__(self, name):
            if name == "len":
                return lambda value: 7
            return super().__getitem__(name)

    model, inputs = fixture_source(tmp_path, monkeypatch, body="return str(len((index,)))")
    module = importlib.import_module(inputs.sources[0].module)
    original = module.derive
    namespace = AlternateLookup(vars(builtins))
    assert namespace.get("len") is len
    module.__dict__["__builtins__"] = namespace
    replacement = types.FunctionType(
        original.__code__, module.__dict__, original.__name__, original.__defaults__
    )
    replacement.__annotations__ = original.__annotations__
    module.__dict__["derive"] = replacement
    module.__dict__["__builtins__"] = vars(builtins)
    with pytest.raises(PortRefusal, match="ordinary dictionary"):
        resolve_python_port(
            model, inputs, model.operations[0].semantic_id, authorize=lambda _: None
        )


def test_historical_effective_model_cannot_authorize_current_pure_port(tmp_path, monkeypatch):
    from dataclasses import replace

    model, inputs = fixture_source(tmp_path, monkeypatch, body='return "fixed"')
    for version in (
        "data-operation-model-v2",
        "data-operation-model-v3",
        "data-operation-model-v4",
        "data-operation-model-v5",
        "data-operation-model-v6",
        "data-operation-model-v7",
    ):
        historical = replace(model, version=version, graph_projections=())
        with pytest.raises(PortRefusal, match="historical model"):
            resolve_python_port(
                historical, inputs, model.operations[0].semantic_id, authorize=lambda _: None
            )


def test_static_correspondence_reuses_only_identical_captured_inputs():
    from corpus_structure.semantic.data_operation_static_preparation import _prepared_python_sources

    model, sources = actual()
    operation = model.operations[0].semantic_id
    _prepared_python_sources.cache_clear()
    first = python_port_identity(model, sources, operation)
    assert python_port_identity(model, sources, operation) == first
    assert _prepared_python_sources.cache_info().misses == 1
    assert _prepared_python_sources.cache_info().hits == 1
    renamed = replace(sources, sources=(replace(sources.sources[0], filename="other.py"),))
    with pytest.raises(PortRefusal):
        python_port_identity(model, renamed, operation)
    assert _prepared_python_sources.cache_info().misses == 2


def test_explicit_compiler_override_bypasses_static_reuse(monkeypatch):
    from corpus_structure.semantic import data_operation_compilation
    from corpus_structure.semantic.data_operation_static_preparation import _prepared_python_sources

    model, sources = actual()
    original = data_operation_compilation.compile_data_operations
    calls = []

    def override(*args, **kwargs):
        calls.append(None)
        return original(*args, **kwargs)

    _prepared_python_sources.cache_clear()
    monkeypatch.setattr(data_operation_compilation, "compile_data_operations", override)
    for _ in range(2):
        python_port_identity(model, sources, model.operations[0].semantic_id)
    assert len(calls) == 2
    assert _prepared_python_sources.cache_info().misses == 0


@pytest.mark.parametrize("change", ["body", "stub", "boundary", "interpreter"])
def test_static_correspondence_input_changes_cannot_hit_old_preparation(change):
    from corpus_structure.semantic.data_operation_static_preparation import _prepared_python_sources
    from corpus_structure.semantic.types import SourceArtifact

    model, sources = actual()
    _prepared_python_sources.cache_clear()
    python_port_identity(model, sources, model.operations[0].semantic_id)
    source = sources.sources[0]
    if change == "body":
        changed = replace(
            sources,
            sources=(replace(source, content=source.content + b"\n# captured source changed\n"),),
        )
    elif change == "stub":
        changed = replace(
            sources,
            sources=(replace(source, stub=b"def claim_source_item(index: int) -> str: ...\n"),),
        )
    elif change == "boundary":
        changed = replace(sources, boundary_contracts=(SourceArtifact("extra-contract", b"{}"),))
    else:
        changed = replace(sources, interpreter="python-3.14-changed-context")
    # Some changes are neutral under the admitted interpretation and some refuse;
    # neither can borrow preparation under the previous captured context.
    with suppress(PortRefusal, ValueError):
        python_port_identity(model, changed, model.operations[0].semantic_id)
    assert _prepared_python_sources.cache_info().misses == 2
    assert _prepared_python_sources.cache_info().hits == 0


def test_colliding_source_subclass_cannot_borrow_warm_static_correspondence():
    from corpus_structure.semantic.data_operation_static_preparation import _prepared_python_sources

    model, sources = actual()
    operation = model.operations[0].semantic_id
    _prepared_python_sources.cache_clear()
    python_port_identity(model, sources, operation)

    class CollidingSources(PythonSourceCollection):
        def __hash__(self):
            return hash(sources)

        def __eq__(self, other):
            return True

    source = sources.sources[0]
    changed = source.content.replace(b"claims/", b"forged/")
    assert changed != source.content
    forged = CollidingSources(
        sources=(replace(source, content=changed),),
        interpreter=sources.interpreter,
        interpretation=sources.interpretation,
        stub_policy=sources.stub_policy,
        boundary_contracts=sources.boundary_contracts,
        generated_interfaces=sources.generated_interfaces,
    )
    assert hash(forged) == hash(sources) and forged == sources
    with pytest.raises(PortRefusal):
        python_port_identity(model, forged, operation)
    assert _prepared_python_sources.cache_info().hits == 0
    assert _prepared_python_sources.cache_info().misses == 1


@pytest.mark.parametrize(
    "annotation,expected_type,collection,presence",
    [
        ("list[int]", "list", "sequence", "optional"),
        ("tuple[int, ...]", "tuple", "sequence", "optional"),
        ("set[int]", "set", "set", "optional"),
        ("frozenset[int]", "frozenset", "set", "optional"),
        ("list[int] | None", "list", "sequence", "optional"),
    ],
)
@pytest.mark.parametrize("population", [(), (2, 1)])
def test_selected_population_uses_acquired_outer_container_without_changing_python_ingress(
    tmp_path, monkeypatch, annotation, expected_type, collection, presence, population
):
    metadata = controlled_port_declaration()
    metadata["roles"][0].update(collection=collection, minimum=0, maximum=None, presence=presence)
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: " + annotation,
        metadata=metadata,
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    hydrated = HydratedRoleValue("index", kind(model, "index"), population)
    arguments = port._arguments((hydrated,), route="python", binding=None, signature=port.signature)
    assert type(arguments.arguments["index"]).__name__ == expected_type
    assert port.invoke_python((hydrated,)).outcome == "addressed"
    assert hydrated.value == population
    if expected_type == "list":
        with pytest.raises(ValidationError):
            port.invoke_python((PythonRoleValue("index", kind(model, "index"), population),))
    with pytest.raises(ValidationError):
        port.invoke_python((HydratedRoleValue("index", kind(model, "index"), (True,)),))


def test_selected_population_rejects_lossy_set_assembly(tmp_path, monkeypatch):
    metadata = controlled_port_declaration()
    metadata["roles"][0].update(collection="bag", minimum=1, maximum=None)
    model, sources = fixture_source(tmp_path, monkeypatch, "index: set[int]", metadata=metadata)
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    with pytest.raises(PortRefusal, match="loses admitted multiplicity"):
        port.invoke_python((HydratedRoleValue("index", kind(model, "index"), (1, 1)),))


def test_selected_container_preparation_preserves_abstract_tuple_and_decimal_members():
    from collections.abc import Collection, Iterable, Sequence
    from decimal import Decimal
    from typing import Annotated

    from corpus_structure.semantic.data_operation_ports import (
        _hydrated_container,
        _validated_python_input,
    )

    assert _hydrated_container(Sequence[int]) is tuple
    assert _validated_python_input(Sequence[int], (2, 1)) == (2, 1)
    # Lazy Iterable validation and unsupported Collection schemas do not
    # establish an eager finite selected population for this callable boundary.
    assert _hydrated_container(Iterable[int]) is None
    assert _hydrated_container(Collection[int]) is None
    annotation = Annotated[list[Decimal], "selected-values"]
    container = _hydrated_container(annotation)
    assert container is list
    original = Decimal("12.3400")
    checked = _validated_python_input(annotation, container((original,)))
    assert str(checked[0]) == "12.3400"
    assert checked[0].as_tuple() == original.as_tuple()


def test_native_sequence_cannot_use_unordered_annotation_or_postvalidation_collapse():
    from typing import Annotated

    from pydantic import AfterValidator

    from corpus_structure.semantic.data_operation_ports import _validated_hydrated_collection

    with pytest.raises(PortRefusal, match="requires an ordered callable container"):
        _validated_hydrated_collection(set[int], (2, 1), set, collection="sequence", role="ordered")
    annotation = set[Annotated[str, AfterValidator(str.lower)]]
    with pytest.raises(PortRefusal, match="loses admitted multiplicity"):
        _validated_hydrated_collection(
            annotation, ("A", "a"), set, collection="bag", role="selected"
        )
    with pytest.raises(PortRefusal, match="not an eager finite population"):
        _validated_hydrated_collection(
            Annotated[list[int], AfterValidator(iter)],
            (2, 1),
            list,
            collection="sequence",
            role="selected",
        )


def test_sequence_with_unordered_callable_container_refuses_at_acquisition(tmp_path, monkeypatch):
    metadata = controlled_port_declaration()
    metadata["roles"][0].update(collection="sequence", minimum=1, maximum=None)
    model, sources = fixture_source(tmp_path, monkeypatch, "index: set[int]", metadata=metadata)
    with pytest.raises(PortRefusal, match="requires an ordered callable container"):
        resolve_python_port(
            model, sources, model.operations[0].semantic_id, authorize=lambda _: None
        )


@pytest.mark.parametrize(
    "annotation,body",
    [
        ("tuple[int, ...]", "return (index, index + 1, index)"),
        ("tuple[int, int, int]", "return (index, index + 1, index)"),
        ("list[int]", "return [index, index + 1, index]"),
    ],
)
def test_eager_sequence_outputs_keep_order_duplicates_and_nominal_item_meaning(
    tmp_path, monkeypatch, annotation, body
):
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes

    declaration = controlled_port_declaration()
    declaration["roles"][-1].update(kind="integer", collection="sequence", minimum=3, maximum=3)
    model, sources = fixture_source(
        tmp_path, monkeypatch, "index: int", body, returns=annotation, metadata=declaration
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    result = port.invoke_python((PythonRoleValue("index", kind(model, "index"), 7),))
    assert [item.value() for item in result.outputs] == [7, 8, 7]
    assert [item.role for item in result.outputs] == ["address"] * 3
    assert {item.kind_contract for item in result.outputs} == {kind(model, "address")}
    assert [item.meaning for item in result.outputs] == [
        canonical_bytes(semantic_value(value)) for value in (7, 8, 7)
    ]
    assert result.outcome == "addressed"


@pytest.mark.parametrize(
    "body", ["return ()", "return (index,)", "return (index, index, index, index)"]
)
def test_eager_sequence_output_cardinality_refuses_before_any_completion(
    tmp_path, monkeypatch, body
):
    declaration = controlled_port_declaration()
    declaration["roles"][-1].update(kind="integer", collection="sequence", minimum=2, maximum=3)
    model, sources = fixture_source(
        tmp_path, monkeypatch, "index: int", body, returns="tuple[int, ...]", metadata=declaration
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    with pytest.raises(PortRefusal, match="item count differs"):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), 7),))


def test_eager_sequence_validates_every_item_before_encoding_completion(tmp_path, monkeypatch):
    declaration = controlled_port_declaration()
    declaration["roles"][-1].update(kind="integer", collection="sequence", minimum=1, maximum=None)
    model, sources = fixture_source(
        tmp_path,
        monkeypatch,
        "index: int",
        "return (index, 'invalid-later-item')",
        returns="tuple[int, ...]",
        metadata=declaration,
    )
    port = resolve_python_port(
        model, sources, model.operations[0].semantic_id, authorize=lambda _: None
    )
    with pytest.raises(ValidationError):
        port.invoke_python((PythonRoleValue("index", kind(model, "index"), 7),))
    from typing import Annotated

    from pydantic import AfterValidator

    with pytest.raises(PortRefusal, match="changed admitted multiplicity"):
        port._complete(
            (7, 8), Annotated[tuple[int, ...], AfterValidator(lambda values: values[:1])]
        )
    with pytest.raises(PortRefusal, match="finite ordered container"):
        port._complete((7, 8), Annotated[tuple[int, ...], AfterValidator(iter)])


@pytest.mark.parametrize("annotation", [set[int], tuple[int, str], Any])
def test_eager_sequence_annotation_does_not_guess_unordered_or_heterogeneous_fields(annotation):
    from corpus_structure.semantic.data_operation_ports import _eager_sequence_annotation

    with pytest.raises(PortRefusal, match="sequence output requires"):
        _eager_sequence_annotation(annotation)


def test_native_scalar_model_json_hydration_restores_tuples_and_exact_primitive_codecs():
    from datetime import date
    from decimal import Decimal

    from pydantic import BaseModel, ConfigDict

    from corpus_structure.semantic.data_operation_ports import (
        PortAdapters,
        _validated_hydrated_model_input,
        _validated_python_input,
    )

    class Input(BaseModel):
        model_config = ConfigDict(
            strict=True, extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
        )
        items: tuple[int, ...]
        amount: Decimal
        day: date
        content: bytes

    amount = Decimal("0.1234567890123456789")
    original = dict(items=[2, 1, 2], amount=amount, day=date(2026, 11, 18), content=b"\xff\x00")
    adapters = PortAdapters()
    hydrated = _validated_hydrated_model_input(Input, original, adapters=adapters)
    assert hydrated.items == (2, 1, 2)
    assert hydrated.amount.as_tuple() == amount.as_tuple()
    assert hydrated.day == date(2026, 11, 18)
    assert hydrated.content == b"\xff\x00"
    assert original["items"] == [2, 1, 2]
    with pytest.raises(ValidationError):
        _validated_python_input(Input, original, adapters=adapters)
    for changed in ({**original, "items": [True]}, {**original, "extra": "not-declared"}):
        with pytest.raises(ValidationError):
            _validated_hydrated_model_input(Input, changed, adapters=adapters)


def test_native_scalar_model_hydration_does_not_serialize_invalid_fields_into_valid_values():
    from pydantic import BaseModel, ConfigDict, model_serializer

    from corpus_structure.semantic.data_operation_ports import (
        PortAdapters,
        _validated_hydrated_model_input,
    )

    class Input(BaseModel):
        model_config = ConfigDict(strict=True, extra="forbid")
        items: tuple[int, ...]

        @model_serializer(mode="plain")
        def wire(self):
            return {"items": [1]}

    adapters = PortAdapters()
    assert _validated_hydrated_model_input(Input, {"items": [2, 3]}, adapters=adapters).items == (
        2,
        3,
    )
    for invalid in ({"items": [True]}, Input.model_construct(items=(True,))):
        with pytest.raises(ValidationError):
            _validated_hydrated_model_input(Input, invalid, adapters=adapters)
