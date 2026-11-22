"""Independent source metric vectors and original declared callable correspondence."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic.composed import (
    data_operation_dependencies,
    read_data_operation_inputs,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_ports import (
    PythonRoleValue,
    python_port_identity,
    resolve_python_port,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_products import FrozenNativeSource, native_projection_identity
from corpus_structure.semantic.source_profiles import (
    source_profile_declarations,
    source_profile_inputs,
    source_profile_operation_sources,
    source_profile_values,
)
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@pytest.fixture(scope="module")
def acquired():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_profile_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = source_profile_operation_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), (source_profile_declarations(),), python_sources=sources
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    captured = read_data_operation_inputs(dependencies)
    assert captured is not None and captured[1] is not None
    return bundle, captured[1], prepared, bound_data_operation_model(prepared)


def original(prepared, selectors=None):
    text = "A x=1. B"
    items = [
        dict(
            self_ref=f"#/texts/{n}",
            label="formula" if n == 1 else "text",
            text=value,
            orig=value,
            parent="#/groups/0" if n == 1 else "#/body",
            prov=[{"page_no": 1}],
        )
        for n, value in enumerate(("A ", "x=1", ". B"))
    ]
    ancestors = [
        dict(self_ref="#/groups/0", label="inline", parent="#/body", prov=[]),
        dict(self_ref="#/body", label="document", prov=[]),
    ]
    pieces = [
        dict(kind="native_text", start=start, end=end, item_ref=f"#/texts/{n}", source_field="text")
        for n, (start, end) in enumerate(((0, 2), (2, 5), (5, 8)))
    ]
    projection = native_projection_identity(text, pieces, items, [], ancestors)
    value = dict(
        source=dict(
            document="original:profile",
            document_subject=original_document_subject("original:profile"),
            section_pointer="#/body",
            membership="descendants",
            projection=projection,
        ),
        text=text,
        items=items,
        pieces=pieces,
        ancestors=ancestors,
        recognition=[],
        selectors=[
            dict(projection=projection, **selector)
            for selector in (selectors if selectors is not None else [{}])
        ],
    )
    return FrozenNativeSource.acquire(prepared, value)


def test_exact_full_and_overlapping_selected_interval_metrics(acquired):
    prepared = acquired[2]
    full = source_profile_values(original(prepared).value)
    assert (full["chars"], full["math_share"], full["inline_math"], full["display_math"]) == (
        8,
        0.375,
        1,
        0,
    )
    partial = source_profile_values(
        original(prepared, [dict(start=1, end=4), dict(start=2, end=6)]).value
    )
    assert (partial["chars"], partial["math_share"], partial["inline_math"]) == (5, 0.6, 1)
    pointed = source_profile_values(
        original(prepared, [dict(native_pointer="#/groups/0", page=1)]).value
    )
    assert (pointed["chars"], pointed["math_share"], pointed["inline_math"]) == (3, 1.0, 1)
    prepared.validate_json("DdoSourceProfile", canonical_bytes(pointed))


def test_acquired_native_source_keeps_validation_and_selector_identity(acquired, monkeypatch):
    from corpus_structure.semantic.data_operation_ports import _validated_python_input

    prepared = acquired[2]
    source = original(prepared)
    another = original(prepared)
    assert another is not source and another._value is source._value
    with pytest.raises(TypeError, match="validating acquisition"):
        FrozenNativeSource(source.content)

    validate = type(prepared).validate_json

    def require_existing(self, name, content):
        if name == "DdoSelectedNativeSource":
            pytest.fail("an acquired same-contract source was validated again")
        return validate(self, name, content)

    monkeypatch.setattr(type(prepared), "validate_json", require_existing)
    assert FrozenNativeSource.acquire(prepared, source) is source
    assert _validated_python_input(FrozenNativeSource, source) is source
    assert source.selector_index() is source.selector_index()
    assert source.value is source.value
    assert source.native_items() is source.native_items()
    with pytest.raises(TypeError):
        source.value["text"] = "caller mutation"
    with pytest.raises(AttributeError):
        source.value["items"].clear()
    forged = object.__new__(FrozenNativeSource)
    object.__setattr__(forged, "content", source.content)
    with pytest.raises(TypeError, match="validating acquisition"):
        _validated_python_input(FrozenNativeSource, forged)


def test_unknown_ancestry_and_missing_math_parent_do_not_become_false_absence(acquired):
    value = thaw_native(original(acquired[2]).value)
    value["items"][1]["parent"] = "#/unavailable"
    with pytest.raises(ValueError, match="parent is unavailable"):
        source_profile_values(value)
    value["selectors"] = [
        dict(projection=value["source"]["projection"], native_pointer="#/groups/0")
    ]
    with pytest.raises(ValueError, match="ancestry is unavailable"):
        source_profile_values(value)


def test_mixed_source_runtime_correspondence_retains_external_declarations(tmp_path):
    from corpus_structure.semantic.composed import read_data_operation_inputs
    from semantic.current_pdf_source_support import current_pdf_recipe

    captured = current_pdf_recipe(tmp_path).captured_inputs
    assert captured is not None
    prepared = prepare_release(captured.bundle, captured.dependencies, captured.profile)
    inputs = read_data_operation_inputs(captured.dependencies)
    assert inputs is not None and inputs[1] is not None
    declarations, sources = inputs
    assert sources is not None
    model = bound_data_operation_model(prepared)
    identity = python_port_identity(
        model,
        sources,
        "source.visual/map",
        schema=captured.bundle,
        prepared=prepared,
        declarations=declarations,
        captured_contracts=captured.dependencies.artifacts,
    )
    assert identity.operation == "source.visual/map" and identity.recipe.startswith("recipe:")
    assert model.operation(identity.operation).dependencies == ("source.visual/recognize",)


def test_original_profile_callable_is_statically_complete_and_nominal(acquired):
    bundle, sources, prepared, model = acquired
    operation = model.operation("profile.segments/source-native")
    implementation = next(
        item for item in model.implementation_slices if item.root == operation.implementation_root
    )
    assert implementation.complete, implementation.unknowns
    identity = python_port_identity(
        model,
        sources,
        operation.semantic_id,
        schema=bundle,
        prepared=prepared,
        declarations=(source_profile_declarations(),),
    )
    port = resolve_python_port(
        model,
        sources,
        operation.semantic_id,
        authorize=lambda actual: None,
        schema=bundle,
        prepared=prepared,
        declarations=(source_profile_declarations(),),
        runtime_locations={
            item.module: Path(item.filename) for item in source_profile_operation_sources().sources
        },
    )
    assert port.identity == identity
    role = next(role for role in operation.roles if role.direction == "input")
    contract = next(
        item.key for item in model.identities if (item.owner, item.domain) == (role.kind, "kind")
    )
    answer = port.invoke_python((PythonRoleValue("source", contract, original(prepared).value),))
    assert answer.outputs[0].value()["chars"] == 8


def test_native_admission_roles_preserve_exact_archived_defaults(acquired):
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )

    prepared, model = acquired[2:]
    model = replace(
        model,
        operations=tuple(
            replace(
                operation,
                roles=tuple(
                    replace(role, support=replace(role.support, origins=("computation",)))
                    if role.support
                    else role
                    for role in operation.roles
                ),
            )
            for operation in model.operations
        ),
    )
    archived = json.loads(model.content)
    projection = json.loads(
        data_operation_definition_projection(prepared, model, native_digest="test")
    )
    by_operation = {operation["semantic_id"]: operation for operation in archived["operations"]}
    identities = {
        (identity["owner"], identity["domain"]): identity["key"]
        for identity in archived["identities"]
    }
    for operation in projection["operations"]:
        declared = by_operation[operation["operation_id"]]
        for direction in ("input", "output"):
            expected = []
            for role in declared["roles"]:
                if role["direction"] != direction:
                    continue
                expected.append(
                    {
                        **role,
                        "kind_contract": identities[role["kind"], "kind"],
                        "identity_requirements": (role["support"] or {}).get(
                            "identity_requirements", []
                        ),
                        **(
                            {"accepted_kind_contracts": [identities[role["kind"], "kind"]]}
                            if direction == "input"
                            else {}
                        ),
                    }
                )
            assert operation[direction + "_roles"] == expected


def test_spawned_kernel_accepts_the_sealed_acquired_source(acquired, tmp_path, monkeypatch):
    import importlib
    import inspect
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic import source_products
    from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
    from semantic.data_operation_port_support import scope

    name = "source_kernel_" + tmp_path.name.replace("-", "_")
    content = (
        b"from collections.abc import Callable\n"
        b"from corpus_structure.semantic.source_products import FrozenNativeSource\n"
        b"def run(source: FrozenNativeSource, *, check_active: Callable[[], None]) -> str:\n"
        b"    check_active()\n    return source.value['text']\n"
    )
    path = tmp_path / (name + ".py")
    path.write_bytes(content)
    monkeypatch.syspath_prepend(str(tmp_path))
    signature = inspect.signature(importlib.import_module(name).run)
    source_path = Path(source_products.__file__).resolve()
    descriptor = PythonCPUDescriptor(
        ((name, str(path), content), (source_products.__name__, str(source_path), source_path.read_bytes())),
        name + ".run",
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    source = original(acquired[2])
    cpu = scope()
    try:
        reply = drive_prepared_work(
            plan_cpu_call(
                descriptor,
                signature.bind(source=source, check_active=lambda: None),
                signature,
                verify=lambda: None,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        assert json.loads(reply.content) == source.value["text"]
        assert reply.execution_receipt.request_digest
    finally:
        cpu.close()
