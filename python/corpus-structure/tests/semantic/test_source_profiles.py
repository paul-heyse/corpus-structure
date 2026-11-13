"""Independent source metric vectors and original declared callable correspondence."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_ports import (
    PythonRoleValue,
    python_port_identity,
    resolve_python_port,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import FrozenNativeSource, native_projection_identity
from corpus_structure.semantic.source_profiles import (
    source_profile_inputs,
    source_profile_operation_sources,
    source_profile_values,
)
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@pytest.fixture(scope="module")
def acquired():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_profile_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = source_profile_operation_sources()
    dependencies = data_operation_dependencies(ResolvedDependencies(), python_sources=sources)
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    return bundle, sources, prepared, bound_data_operation_model(prepared)


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


def test_unknown_ancestry_and_missing_math_parent_do_not_become_false_absence(acquired):
    value = original(acquired[2]).value
    value["items"][1]["parent"] = "#/unavailable"
    with pytest.raises(ValueError, match="parent is unavailable"):
        source_profile_values(value)
    value["selectors"] = [
        dict(projection=value["source"]["projection"], native_pointer="#/groups/0")
    ]
    with pytest.raises(ValueError, match="ancestry is unavailable"):
        source_profile_values(value)


def test_original_profile_callable_is_statically_complete_and_nominal(acquired):
    bundle, sources, prepared, model = acquired
    operation = model.operation("profile.segments/source-native")
    implementation = next(
        item for item in model.implementation_slices if item.root == operation.implementation_root
    )
    assert implementation.complete, implementation.unknowns
    identity = python_port_identity(
        model, sources, operation.semantic_id, schema=bundle, prepared=prepared
    )
    port = resolve_python_port(
        model,
        sources,
        operation.semantic_id,
        authorize=lambda actual: None,
        schema=bundle,
        prepared=prepared,
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
