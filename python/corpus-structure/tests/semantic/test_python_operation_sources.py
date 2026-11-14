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
    result = captured.implementation_slice(
        "example.run", (captured._surface("example.run", function),), boundaries, ("item",)
    )
    assert result.complete is admitted
    if not admitted:
        assert any("escape" in unknown.reason for unknown in result.unknowns)
