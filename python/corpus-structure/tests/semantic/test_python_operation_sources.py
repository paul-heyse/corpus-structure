"""Selected generated interfaces remain source-closed and faithful to callable custody."""

import json
from dataclasses import replace

import griffe
import pytest

from corpus_structure.semantic.data_operation_model import OpaqueBoundary
from corpus_structure.semantic.python_operation_sources import (
    ClosedPythonSources,
    PythonSource,
    PythonSourceCollection,
)
from corpus_structure.semantic.types import PreparationError, SourceArtifact


def sources(code, *profiles, module="example"):
    return PythonSourceCollection(
        (PythonSource(module, code.encode(), module + ".py"),),
        generated_interfaces=profiles,
    )


def test_generated_dataclass_preserves_keyword_fields_and_unevaluated_factory():
    code = """from dataclasses import dataclass, field
raise RuntimeError("analysis must not import this module")
def make_items() -> list[int]:
    raise RuntimeError("analysis must not call factories")
@dataclass(kw_only=True)
class Item:
    value: int
    items: list[int] = field(default_factory=make_items)
"""
    captured = ClosedPythonSources(sources(code, "dataclasses"))
    facts = captured.kind_facts("example.Item")
    parameters = facts["constructor"]["parameters"]
    assert [p["name"] for p in parameters] == ["self", "value", "items"]
    assert [p["kind"] for p in parameters[1:]] == ["keyword-only", "keyword-only"]
    factory = parameters[-1]["default"]
    assert factory["expression"] == "ExprCall"
    assert factory["parts"][0]["reference"] == "example.make_items"
    records = facts["owned_definition"]
    assert any(n["id"] == "python:example.make_items" for n in records["nodes"])
    assert facts["constructor"]["origin"] == "modeled"
    # Static constructor shape does not establish all decorator/runtime behavior.
    assert not facts["complete"]
    assert "constructor" not in ClosedPythonSources(sources(code)).kind_facts("example.Item")


def test_generated_dataclass_uses_supplied_cross_module_inheritance():
    captured = ClosedPythonSources(
        PythonSourceCollection(
            (
                PythonSource(
                    "pkg.child",
                    b"from dataclasses import dataclass\nfrom .base import Base\n"
                    b"@dataclass\nclass Child(Base):\n    extra: str = 'ok'\n",
                    "pkg/child.py",
                ),
                PythonSource(
                    "pkg.base",
                    b"from dataclasses import dataclass\n@dataclass\nclass Base:\n    value: int\n",
                    "pkg/base.py",
                ),
            ),
            generated_interfaces=("dataclasses",),
        )
    )
    facts = captured.kind_facts("pkg.child.Child")
    assert [p["name"] for p in facts["constructor"]["parameters"]] == ["self", "value", "extra"]
    assert (
        next(f for f in facts["fields"] if f["name"] == "value")["owner"] == "pkg.base.Base.value"
    )


def test_typeddict_expansion_preserves_fields_and_original_kwargs_signature():
    code = """from typing import TypedDict, NotRequired, Unpack
class Options(TypedDict):
    value: int
    label: NotRequired[str]
def run(**kwargs: Unpack[Options]) -> int:
    return kwargs['value']
"""
    captured = ClosedPythonSources(sources(code, "unpack-typeddict"))
    facts = captured.kind_facts("example.Options")
    assert [f["name"] for f in facts["fields"]] == ["label", "value"]
    generated = facts["constructor"]["parameters"]
    assert [(p["name"], p["default"]) for p in generated] == [
        ("self", None),
        ("value", None),
        ("label", "..."),
    ]
    function = captured.resolve("example.run")
    assert isinstance(function, griffe.Function)
    actual = captured._surface("example.run", function)
    assert [(p.name, p.kind) for p in actual.parameters] == [("kwargs", "variadic keyword")]
    expanded = captured.boundary_surfaces["example.run"]
    assert [(p.name, p.kind) for p in expanded.parameters] == [
        ("value", "keyword-only"),
        ("label", "keyword-only"),
    ]
    implemented = captured.implementation_slice("example.run", (actual,), (), ())
    boundary = next(n for n in implemented.nodes if n.category == "modeled_unpack_boundary")
    assert [p["name"] for p in json.loads(boundary.payload)["parameters"]] == ["value", "label"]


def test_generated_default_type_references_distinguish_same_spelled_names():
    base = sources(
        "from dataclasses import dataclass\nfrom first import Value\n"
        "@dataclass\nclass Item:\n    value: Value\n",
        "dataclasses",
    )
    first = ClosedPythonSources(base).kind_facts("example.Item")["constructor"]
    second = ClosedPythonSources(
        replace(
            base,
            sources=(
                replace(
                    base.sources[0], content=base.sources[0].content.replace(b"first", b"second")
                ),
            ),
        )
    ).kind_facts("example.Item")["constructor"]
    assert first["parameters"][1]["annotation"]["reference"] == "first.Value"
    assert second["parameters"][1]["annotation"]["reference"] == "second.Value"


@pytest.mark.parametrize("profiles", [("unknown",), ("dataclasses", "dataclasses")])
def test_unadmitted_generated_profile_refuses(profiles):
    with pytest.raises(PreparationError, match="generated interface"):
        ClosedPythonSources(sources("class A: pass", *profiles))


def test_dataclass_disabled_init_does_not_export_griffe_empty_constructor_as_runtime_fact():
    captured = ClosedPythonSources(
        sources(
            "from dataclasses import dataclass\n@dataclass(init=False)\n"
            "class Item:\n    value: int\n",
            "dataclasses",
        )
    )
    facts = captured.kind_facts("example.Item")
    assert facts["constructor"] is None
    assert not facts["complete"]
    assert any("init=False" in u["reason"] for u in facts["unknowns"])


def implementation(code, entry="run", inputs=("item",)):
    captured = ClosedPythonSources(sources(code))
    target = "example." + entry
    function = captured.resolve(target)
    assert isinstance(function, griffe.Function)
    return captured.implementation_slice(target, (captured._surface(target, function),), (), inputs)


@pytest.mark.parametrize(
    "expression",
    [
        "item.__class__.__firstlineno__",
        "item.label.__code__.co_firstlineno",
        "item.value.__class__.__name__",
        "str(item)",
    ],
)
def test_nominal_data_input_does_not_admit_runtime_metadata(expression):
    code = (
        'class Item:\n    value: str\n    def label(self) -> str:\n        return "label"\n'
        + "def run(item: Item) -> str:\n    return "
        + expression
        + "\n"
    )
    result = implementation(code)
    assert not result.complete
    assert any("attribute access" in u.reason or "escape" in u.reason for u in result.unknowns)


def test_nominal_field_and_primitive_value_method_profiles_preserve_layout_locality():
    code = (
        "class Item:\n    value: str\n"
        "def run(item: Item) -> str:\n    return item.value.strip().lower()\n"
    )
    first = implementation(code)
    second = implementation("\n\n" + code)
    assert first.complete and second.complete
    assert first.semantic_records() == second.semantic_records()


def test_nominal_method_body_is_retained_but_unqualified_dispatch_withholds_identity():
    code = (
        'class Item:\n    def label(self) -> str:\n        return "first"\n'
        "def run(item: Item) -> str:\n    return item.label()\n"
    )
    first = implementation(code)
    second = implementation(code.replace('"first"', '"second"'))
    assert not first.complete and not second.complete
    assert any("concrete receiver" in u.reason for u in first.unknowns)
    assert "python:example.Item.label" in {node.id for node in first.nodes}
    assert any(
        edge.relation == "possible_call" and edge.target == "python:example.Item.label"
        for edge in first.edges
    )
    assert first.semantic_records() != second.semantic_records()


@pytest.mark.parametrize(
    "body",
    [
        "values = []\n    values.append(1)\n    values.pop()\n    return len(values)",
        "values = list()\n    values.extend((1, 2))\n    return values.count(1)",
        "values = {}\n    values.update({'answer': 1})\n    return values.get('answer')",
        "values = {name: 1 for name in ('answer',)}\n    return values.get('answer')",
        "values = [name for name in ('answer',)]\n    return values.count('answer')",
    ],
)
def test_owned_container_construction_retains_primitive_method_provenance(body):
    result = implementation("def run():\n    " + body + "\n", inputs=())
    assert result.complete, result.unknowns


def test_shadowed_builtin_constructor_keeps_receiver_dispatch_unknown():
    result = implementation(
        "def run(list):\n    values = list()\n    return values.copy()\n", inputs=()
    )
    assert not result.complete
    assert any("values.copy" in unknown.reason for unknown in result.unknowns)


def test_owned_list_does_not_admit_arbitrary_callbacks_or_elements():
    result = implementation(
        "def run(callback):\n    values = []\n    values.append(callback)\n"
        "    return values[0]()\n",
        inputs=(),
    )
    assert not result.complete
    assert any("dynamic call target" in unknown.reason for unknown in result.unknowns)


def test_exact_type_guard_supplies_nominal_field_provenance():
    result = implementation(
        "class Item:\n    value: str\n"
        "def run(item):\n    if type(item) is Item:\n"
        "        return item.value.strip()\n    return ''\n"
    )
    assert result.complete, result.unknowns


def test_instance_guard_keeps_subclass_dispatch_unknown():
    result = implementation(
        "class Item:\n    value: str\n"
        "def run(item):\n    if isinstance(item, Item):\n"
        "        return item.value.strip()\n    return ''\n"
    )
    assert not result.complete


def test_assignment_within_type_guard_invalidates_receiver_provenance():
    result = implementation(
        "class Item:\n    value: str\n"
        "def run(item, replacement):\n    if type(item) is Item:\n"
        "        item = replacement\n        return item.value.strip()\n    return ''\n"
    )
    assert not result.complete


def test_direct_nested_function_calls_retain_the_captured_body():
    code = (
        "def run(value: int):\n"
        "    def decrement(item: int):\n"
        "        return decrement(item - 1) if item else 7\n"
        "    return decrement(value)\n"
    )
    first = implementation(code)
    second = implementation(code.replace("else 7", "else 8"))
    assert first.complete, first.unknowns
    assert second.complete, second.unknowns
    assert first.semantic_records() != second.semantic_records()
    assert "python:example.run.<locals>.decrement" in {node.id for node in first.nodes}


def test_nested_function_dynamic_dependency_remains_required():
    result = implementation(
        "def run(value):\n"
        "    def invoke(item):\n"
        "        return item.execute()\n"
        "    return invoke(value)\n"
    )
    assert not result.complete
    assert any("item.execute" in item.reason for item in result.unknowns)


def test_nested_function_cannot_escape_as_a_callback():
    result = implementation(
        "def run(receiver):\n    def value():\n        return 7\n    return receiver(value)\n"
    )
    assert not result.complete
    assert any("escape" in item.reason for item in result.unknowns)


def test_exact_destructuring_preserves_local_container_provenance():
    result = implementation(
        "def run():\n"
        "    values, (name, count) = [], ('owned', 2)\n"
        "    values.append(name.strip())\n"
        "    return values.count('owned') + count\n",
        inputs=(),
    )
    assert result.complete, result.unknowns


def test_dynamic_destructuring_does_not_claim_owned_values():
    result = implementation(
        "def run(item):\n    values, name = item\n    return values.copy()\n",
        inputs=(),
    )
    assert not result.complete


def test_type_identity_refusal_does_not_authorize_dynamic_class_construction():
    result = implementation(
        "def run(item):\n"
        "    if type(item) is not int:\n        raise TypeError('integer required')\n"
        "    return item\n",
        inputs=(),
    )
    assert result.complete, result.unknowns
    dynamic = implementation("def run():\n    return type('Created', (), {})\n", inputs=())
    assert not dynamic.complete


def test_exact_nominal_type_refusal_does_not_pass_the_object_to_dynamic_code():
    result = implementation(
        "class Item:\n    value: str\n"
        "def run(item: Item):\n"
        "    if type(item) is not Item:\n        raise TypeError('item required')\n"
        "    return item.value.strip()\n"
    )
    assert result.complete, result.unknowns


def test_shadowed_type_does_not_admit_a_nominal_object_handoff():
    result = implementation(
        "class Item:\n    value: str\n"
        "def run(item: Item, type):\n    return type(item) is not Item\n"
    )
    assert not result.complete
    assert any("escape" in unknown.reason for unknown in result.unknowns)


@pytest.mark.parametrize(
    ("argument", "nominal", "bridge", "admitted"),
    [
        ("item", "same", "same", True),
        ("Item", "same", "same", False),
        ("item.label", "same", "same", False),
        ("item", None, "same", False),
        ("item", "different", "same", False),
        ("item", "same", None, False),
    ],
)
def test_nominal_value_handoff_requires_exact_shared_revisioned_boundary(
    argument, nominal, bridge, admitted
):
    code = (
        "class Item:\n    value: str\n"
        "    def label(self) -> str:\n        return self.value\n"
        "def bridge(value) -> str:\n    return 'opaque'\n"
        f"def run(item: Item) -> str:\n    return bridge({argument})\n"
    )
    captured = ClosedPythonSources(sources(code))
    function = captured.resolve("example.run")
    boundaries = tuple(
        OpaqueBoundary(
            reference=reference,
            contract="example.nominal-transfer.v1",
            role="prepared nominal data handoff",
            content_digest=SourceArtifact("contract", revision.encode()).digest,
        )
        for reference, revision in (("example.Item", nominal), ("example.bridge", bridge))
        if revision is not None
    )
    from griffe import Function

    assert isinstance(function, Function)
    result = captured.implementation_slice(
        "example.run", (captured._surface("example.run", function),), boundaries, ("item",)
    )
    assert result.complete is admitted
    if not admitted:
        assert any("escape" in unknown.reason for unknown in result.unknowns)


@pytest.mark.parametrize(
    "factory",
    [
        "return {}",
        "value = dict()\n    return value",
        "value = {}\n    if flag:\n        return value\n    return value",
    ],
)
def test_captured_constructor_results_supply_exact_value_provenance(factory):
    code = (
        "def create(flag):\n    "
        + factory
        + "\ndef run():\n    return create(False).get('answer')\n"
    )
    result = implementation(code, inputs=())
    assert result.complete, result.unknowns


def test_captured_return_correspondence_uses_actual_argument_value():
    result = implementation(
        "def same(value):\n    return value\ndef run():\n    return same({}).get('answer')\n",
        inputs=(),
    )
    assert result.complete, result.unknowns


@pytest.mark.parametrize(
    "factory",
    [
        "def create(value) -> dict:\n    return value\n",
        "def create(value):\n    result = {}\n    for result in value:\n        pass\n    return result\n",
        "def create(value):\n    if value:\n        return {}\n",
        "def create(value):\n    yield {}\n",
        "def create(value):\n    result = {}\n    result = value\n    return result\n",
        "def create(value):\n    if value:\n        value = []\n    return value\n",
        "def create(value):\n    return value\n    value = {}\n",
        "def create(value):\n    result = {}\n    def result():\n        return 1\n    return result\n",
        "def create(value):\n    result = {}\n    with value as result:\n        pass\n    return result\n",
        "def create(value):\n    result = {}\n    try:\n        value()\n    except ValueError as result:\n        pass\n    return result\n",
        "def create(value):\n    result = {}\n    match value:\n        case result:\n            pass\n    return result\n",
        "def create(value):\n    result = {}\n    import math as result\n    return result\n",
        "def create(value):\n    result = {}\n    def change():\n        nonlocal result\n        result = value\n    change()\n    return result\n",
    ],
)
def test_unproved_return_values_cannot_inherit_declared_dictionary_behavior(factory):
    result = implementation(
        factory + "def run(value):\n    return create(value).get('answer')\n", inputs=()
    )
    assert not result.complete
    assert any("create(value).get" in item.reason for item in result.unknowns)


@pytest.mark.parametrize("expression", ["b'owned'.encode()", "create().encode()"])
def test_bytes_literals_and_constructed_results_keep_bytes_methods(expression):
    result = implementation(
        "def create():\n    return b'owned'\ndef run():\n    return " + expression + "\n", inputs=()
    )
    assert not result.complete
    assert any("attribute access" in item.reason for item in result.unknowns)


@pytest.mark.parametrize("value_type", ["dict", "str"])
def test_return_proof_does_not_promote_annotated_parameters(value_type):
    result = implementation(
        "def same(value):\n    return value\n"
        "def run(value: " + value_type + "):\n    return same(value).copy()\n",
        inputs=(),
    )
    assert not result.complete
    assert any("same(value).copy" in item.reason for item in result.unknowns)


def test_bound_method_does_not_reinterpret_its_implicit_receiver_as_an_argument():
    result = implementation(
        "class Item:\n    def make(self, value):\n        return self\n"
        "def run(item: Item):\n    return item.make({}).get('answer')\n",
        inputs=(),
    )
    assert not result.complete
    assert any("item.make({}).get" in item.reason for item in result.unknowns)


def test_decorated_function_cannot_inherit_its_source_body_return_profile():
    result = implementation(
        "def alter(function):\n    return function\n"
        "@alter\ndef make():\n    return {}\n"
        "def run():\n    return make().get('answer')\n",
        inputs=(),
    )
    assert not result.complete
    assert any("make().get" in item.reason for item in result.unknowns)
