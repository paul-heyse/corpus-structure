"""Independent literal graphs validated as actual current nominal products."""

from dataclasses import dataclass, replace
from typing import Any

import pytest
from methods.declared_primary_fixture import profiles, selected_source

from corpus_structure.semantic.characterization import occurrence_id
from corpus_structure.semantic.construction_products import (
    _stage_construction_support,
    interpreted_member_contracts,
    interpreted_product_value,
    validate_interpreted_product,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_formal_readings import declared_formal_layers
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.source_products import FrozenNativeSource


@dataclass(frozen=True)
class GraphSource:
    source: FrozenNativeSource
    context: SubjectContext


def selected_graph(text="all", *, selectors=None, **kwargs):
    selected, _frame, context = selected_source(text, **kwargs)
    if selectors is not None:
        value = dict(selected.value)
        value["selectors"] = [
            dict(projection=value["source"]["projection"], **row) for row in selectors
        ]
        selected = FrozenNativeSource.acquire(profiles()[1].prepared, value)
        context = replace(
            context,
            analyzed_scope=canonical_bytes(
                dict(source=value["source"], selectors=value["selectors"])
            ),
        )
    return GraphSource(selected, context)


@pytest.fixture(scope="module")
def graph_source():
    return selected_graph()


@pytest.fixture(scope="module")
def prepared():
    return profiles()[1].prepared


def literal_inventory(case) -> dict[str, Any]:
    coordinate = case.source.value["source"]
    selector = case.source.value["selectors"][0]
    extent = dict(
        projection=coordinate["projection"],
        native_pointer="#/texts/0",
        start=0,
        end=3,
        text="all",
        synthetic=False,
    )
    occurrence = dict(local_id=occurrence_id(coordinate, [extent]), extents=[extent])

    def term(key, kind, value, children=()):
        return dict(
            local_id=key,
            family="scope",
            kind=kind,
            vocabulary="literal-logic",
            value=value,
            status="interpreted",
            occurrences=[occurrence["local_id"]],
            children=[dict(role=role, target=target, structural=True) for role, target in children],
        )

    return dict(
        outcome="complete",
        occurrences=[occurrence],
        annotations=[],
        memberships=[],
        roles=[],
        choices=[],
        terms=[
            term("p", "predicate", "P"),
            term("x", "participant", "x"),
            term("r", "predicate", "R"),
            term(
                "forall", "binder", "all", [("variable", "x"), ("restrictor", "r"), ("body", "p")]
            ),
            term("not_all", "operator", "not", [("target", "forall")]),
            term("not_p", "operator", "not", [("target", "p")]),
            term(
                "all_not",
                "binder",
                "all",
                [("variable", "x"), ("restrictor", "r"), ("body", "not_p")],
            ),
            term("or", "operator", "or", [("left", "p"), ("right", "r")]),
        ],
        coverage=[
            dict(
                family="scope",
                operation="literal.scope",
                profile="literal-logic",
                eligible=[selector],
                examined=[selector],
                unexamined=[],
                availability="available",
                outcome="complete",
            )
        ],
    )


def product_value(case, facts, dependencies=()) -> dict[str, Any]:
    profile = profiles()[1]
    facts = thaw_native(facts)
    try:
        annotations, formal = _stage_construction_support(facts, dependencies)
    except KeyError as error:
        raise ValueError("authored external premise lacks its member address") from error
    return {
        **interpreted_product_value(
            case.source,
            facts,
            interpreted_member_contracts(profile.prepared, profile.model),
        ),
        "annotation_support": annotations,
        "formal_support": formal,
    }


def validate_product(case, value, dependencies=()):
    profile = profiles()[1]
    return validate_interpreted_product(
        profile.prepared,
        profile.model,
        value,
        case.source,
        dependencies,
        subject_context=case.context,
    )


def current_product(case, facts=None, dependencies=()):
    facts = literal_inventory(case) if facts is None else facts
    return validate_product(case, product_value(case, facts, dependencies), dependencies)


def current_inventory(case, product):
    return declared_formal_layers((product,), case.source)[product.reference]
