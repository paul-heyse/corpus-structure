"""Independent binding facts and source-expression setup.

The Boolean evaluator observes expression truth only; it is not a full BindingResult
or protected-admission parity executor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from pglast import ast
from scenario_recipes import register_scenario_builder
from sqlalchemy import text

from corpus_structure.semantic.data_operation_binding_native import binding_native_sql
from corpus_structure.semantic.data_operation_bindings import (
    BindingReason,
    BindingResult,
    BindingStatus,
)
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ResolvedRoleBinding,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.prepared_sql import prepare_sql


@dataclass(frozen=True)
class BindingSourceRecipe:
    codecs: bytes
    helpers: bytes


@dataclass(frozen=True)
class BindingSourceStage:
    names: tuple[str, ...]

    @property
    def seed_files(self) -> tuple[Path, ...]:
        return ()

    def validate_clone(self, admin):
        with admin.connect() as connection:
            present = set(
                connection.scalars(
                    text(
                        "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                        "WHERE n.nspname IN ('ops','data') AND p.proname = ANY(:names)"
                    ),
                    {"names": list(self.names)},
                )
            )
            if present != set(self.names):
                raise ValueError("binding source seed functions are missing")


@cache
def binding_source_recipe():
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    # The source now contains captured Core projection placeholders. Resolve the
    # production template once before selecting its three independent codec helpers.
    return BindingSourceRecipe(
        native_sql(native_protocol_sources()).encode(), binding_native_sql().encode()
    )


def build_binding_source(recipe, admin, writer, directory, *, purpose_engine=None):
    names = []
    with admin.begin() as connection:
        for content, codecs in ((recipe.codecs, True), (recipe.helpers, False)):
            prepared = prepare_sql(content.decode(), source="binding-source-seed")
            for index, raw in enumerate(prepared.statements):
                if not isinstance(raw.stmt, ast.CreateFunctionStmt):
                    continue
                name = (raw.stmt.funcname or ())[-1].sval
                if (codecs and name in {"ddo_normalize", "ddo_field", "ddo_json"}) or (
                    not codecs and name != "ddo_require_binding"
                ):
                    connection.exec_driver_sql(
                        prepared.excerpt(index), execution_options={"no_parameters": True}
                    )
                    names.append(name)
    return BindingSourceStage(tuple(names))


register_scenario_builder(BindingSourceRecipe, build_binding_source)


@pytest.fixture
def binding_native_connection(scenario_seeds):
    with scenario_seeds.rollback_family(binding_source_recipe()) as case:
        yield case.connection


def row(value: Any, *, product=None, member=None, kind="integer") -> dict[str, Any]:
    value_tag = [kind, str(value)] if kind != "string" else [kind, value]
    return {
        "product": product or f"p{value}",
        "member": member or f"m{value}",
        "kind_contract": "kind:item",
        "subject": "doc",
        "original_source": "source",
        "position": value if isinstance(value, int) else 0,
        "multiplicity": 1,
        "body": {"value": value, "base": "b", "member": member or f"m{value}"},
        "meaning_body": [
            "mapping",
            [
                ["base", ["string", "b"]],
                ["member", ["string", member or f"m{value}"]],
                ["value", value_tag],
            ],
        ],
    }


def context(*values: Any) -> dict[str, Any]:
    members = [row(value) for value in values]
    population = {
        "identity": "population:fixed",
        "complete": True,
        "members": [item["member"] for item in members],
        "evidence": {"authentic": True},
    }
    return {
        "model": {
            "kinds": [
                {
                    "semantic_id": "primitive:integer",
                    "name": "integer",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "integer"}},
                },
                {
                    "semantic_id": "primitive:string",
                    "name": "string",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "string"}},
                },
                {
                    "semantic_id": "primitive:float",
                    "name": "float",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "float"}},
                },
                {
                    "semantic_id": "urn:item",
                    "name": "Item",
                    "category": "class",
                    "facts": {"json": {}},
                },
                {
                    "semantic_id": "urn:item/property/value",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:integer"}},
                },
                {
                    "semantic_id": "urn:item/property/base",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:string"}},
                },
                {
                    "semantic_id": "urn:item/property/member",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:string"}},
                },
            ]
        },
        "roledefs": [
            {
                "name": name,
                "kind": "urn:item",
                "kind_contract": "kind:item",
                "accepted_kind_contracts": ["kind:item"],
                "collection": "set",
            }
            for name in ("items", "left", "right", "shared")
        ],
        "roles": {"items": members, "left": [], "right": [], "shared": []},
        "universe": members,
        "populations": {"retained": population},
        "witnesses": {"items": population},
        "parameters": {"allowed": [2, 3]},
        "parameterdefs": {},
        "choices": {},
        "subject": "doc",
        "original_source": "source",
    }


def field(role="items", name="value", value_type="integer"):
    return {
        "kind": "field",
        "value_type": value_type,
        "field": {"role": role, "projection": "urn:item", "field": name},
    }


def literal(value):
    return {"kind": "literal", "value_type": "integer", "value": {"json": ["integer", str(value)]}}


def evaluate(connection, node, facts):
    return connection.scalar(
        text("SELECT ops.ddo_binding_test(CAST(:node AS jsonb),CAST(:facts AS jsonb))"),
        {"node": json.dumps(node), "facts": json.dumps(facts)},
    )


class WireCheckedStorage:
    """Routing double that enforces the real native input and result contracts.

    Replies are hand-authored by the case. This supplies wire evidence only, not
    database execution, protected admission, or native semantic evidence.
    """

    def __init__(self, replies):
        from copy import deepcopy

        self.replies = deepcopy(replies)
        self.calls = []

    def invoke(self, name, payload):
        from copy import deepcopy

        from corpus_structure.semantic.data_operation_wire import validate_native_wire

        if name not in self.replies:
            raise ValueError("unknown configured native data operation")
        payload = validate_native_wire(name, "input", payload)
        self.calls.append((name, deepcopy(payload)))
        return validate_native_wire(name, "output", deepcopy(self.replies[name]))


# Independently authored admitted facts. The relational fixture does not consume
# these expectations; equal text/value never erases member/source/support identity.


def _authored_member(product, member, position, episode, *, source="source"):
    return BoundRoleMember(
        product=product,
        kind_contract="kind:fixed",
        subject="doc",
        original_source=source,
        analyzed_scope=b'{"page":1}',
        coverage=b'{"complete":true}',
        support_episodes=(episode,),
        support_evidence=b'{"trust":"pinned"}',
        position=position,
        multiplicity=1,
        member=member,
        support_references=(ComputationalSupportReference(derivation_id=episode),),
    )


P1 = _authored_member("p1", "m1", 2, "ep1")
P2 = _authored_member("p2", "m2", 1, "ep2")
P3 = _authored_member("p3", "m3", 0, "ep3")


def _authored_result(roles, *, status: BindingStatus = "ready", reasons=(), choices=b"{}"):
    return BindingResult(
        operation="urn:op",
        subject="doc",
        roles=roles,
        status=status,
        reasons=reasons,
        parameters=b'["mapping",[]]',
        choices=choices,
        model_version=MODEL_VERSION,
        definition="definition:fixed",
        eligibility="eligibility:fixed",
        admission_evidence=(b'{"trust":"pinned"}',),
        source_sets=b"{}",
        subject_context=None,
    )


def _cardinality(role):
    return BindingReason(
        "role-cardinality", "urn:op/" + role, "selected role does not satisfy declared cardinality"
    )


def _open_role(role):
    return BindingReason(
        "role-population-open", "urn:op/" + role, "empty SQL selection does not prove absence"
    )


@dataclass(frozen=True)
class BindingEvidenceCase:
    name: str
    expected: BindingResult
    sample_value: int | None = None
    native_refusal: tuple[str, str] | None = None


# Meanings are shared across observations; a compiled insufficient result and a
# protected-admission refusal are different outcomes, not Boolean parity.
BINDING_EVIDENCE_CASES = (
    BindingEvidenceCase(
        "range-ready",
        _authored_result((ResolvedRoleBinding("items", "present", (P2,)),)),
        sample_value=15,
    ),
    BindingEvidenceCase(
        "range-outside",
        _authored_result(
            (ResolvedRoleBinding("items", "unknown", ()),),
            status="awaiting-inputs",
            reasons=(_cardinality("items"), _open_role("items")),
        ),
        sample_value=5,
        native_refusal=("23514", "selected native input bundles violate frozen binding"),
    ),
    BindingEvidenceCase(
        "role-too-few",
        _authored_result(
            (ResolvedRoleBinding("items", "present", (P2,)),),
            status="awaiting-inputs",
            reasons=(_cardinality("items"),),
        ),
    ),
    BindingEvidenceCase(
        "role-too-many",
        _authored_result(
            (ResolvedRoleBinding("items", "present", (P1, P2, P3)),),
            status="awaiting-inputs",
            reasons=(_cardinality("items"),),
        ),
    ),
    BindingEvidenceCase(
        "optional-unknown",
        _authored_result(
            (ResolvedRoleBinding("items", "present", ()),),
            status="unknown",
            reasons=(
                BindingReason(
                    "unknown-comparison", "urn:op/binding", "SQL NULL in qualified predicate"
                ),
            ),
        ),
    ),
    BindingEvidenceCase(
        "optional-present-empty", _authored_result((ResolvedRoleBinding("items", "present", ()),))
    ),
    BindingEvidenceCase(
        "negative-incomplete",
        _authored_result(
            (
                ResolvedRoleBinding(
                    "items",
                    "known-absent",
                    (),
                    b'{"complete":true,"evidence":{"closed":true},"identity":"population:missing-facts","members":["not-materialized"]}',
                ),
            ),
            status="awaiting-inputs",
            reasons=(
                BindingReason(
                    "negative-candidate-facts",
                    "urn:op/items",
                    "closed negative population has members without admitted candidate facts",
                ),
            ),
        ),
    ),
    BindingEvidenceCase(
        "member-added",
        _authored_result(
            (
                ResolvedRoleBinding(
                    "items",
                    "present",
                    (P1, P2),
                    b'{"complete":true,"evidence":{"closed":true},"identity":"population:selected","members":["m1","m2"]}',
                ),
            )
        ),
    ),
    BindingEvidenceCase(
        "member-removed",
        _authored_result(
            (
                ResolvedRoleBinding(
                    "items",
                    "known-absent",
                    (),
                    b'{"complete":true,"evidence":{"closed":true},"identity":"population:selected","members":["m2"]}',
                ),
            ),
            status="not-applicable",
            reasons=(
                _cardinality("items"),
                BindingReason(
                    "binding-forall",
                    "urn:op/binding/0/items",
                    "relational binding constraint unsatisfied",
                ),
            ),
        ),
    ),
    BindingEvidenceCase(
        "unselected-alternative",
        _authored_result(
            (
                ResolvedRoleBinding(
                    "left",
                    "known-absent",
                    (),
                    b'{"complete":true,"members":[],"reason":"unselected-declared-branch","selection":{"producer":"right"}}',
                ),
                ResolvedRoleBinding("right", "present", (P2,)),
            ),
            choices=b'{"producer":"right"}',
        ),
    ),
    BindingEvidenceCase(
        "wrong-source-join",
        _authored_result(
            (
                ResolvedRoleBinding("left", "unknown", ()),
                ResolvedRoleBinding("right", "unknown", ()),
            ),
            status="awaiting-inputs",
            reasons=(
                _cardinality("left"),
                _cardinality("right"),
                _open_role("left"),
                _open_role("right"),
            ),
        ),
    ),
    BindingEvidenceCase(
        "distinct-same-text",
        _authored_result(
            (
                ResolvedRoleBinding(
                    "left",
                    "present",
                    (_authored_member("p1", "m1", 2, "ep1", source="original:left"),),
                ),
                ResolvedRoleBinding(
                    "right",
                    "present",
                    (_authored_member("p2", "m2", 1, "ep2", source="original:right"),),
                ),
            )
        ),
    ),
)


BINDING_RANGE_CASES = {
    case.name: case for case in BINDING_EVIDENCE_CASES if case.sample_value is not None
}


def discover(
    ddo_kernel,
    *,
    complete=True,
    ambiguous=False,
    values=(5, 15, 25),
    inference="inference:test",
    member_contexts=None,
    member_body_contexts=None,
    additional_discovery_targets=(),
):
    from corpus_structure.semantic.data_operation_demands import (
        DiscoverySelection,
        RootSubject,
        freeze_demand,
    )
    from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.data_operation_demand_support import claim, publish

    scope = {"page": 1}
    root = {"subject": "doc", "original_source": "source:test", "analyzed_scope": scope}
    selection = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("doc", "source:test", canonical_bytes(scope)),),
        targets=("urn:consumer",),
        inference=inference,
        execution_profile="execution:test",
        discovery=(DiscoverySelection("urn:discover", "result", "urn:child", "all-items"),)
        + tuple(
            DiscoverySelection("urn:discover", "result", target, "all-items")
            for target in additional_discovery_targets
        )
        + (
            (DiscoverySelection("urn:discover", "result", "urn:child", "other-items"),)
            if ambiguous
            else ()
        ),
    ).record
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": ddo_kernel["prepared"].release_id,
                "runtime_id": ddo_kernel["runtime"],
                "root": [root],
                "selection": selection,
                "strength": "value",
            },
        )
        producer = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:discover",
                **root,
                "parameters": {},
            },
        )
        consumer = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": "urn:consumer",
                **root,
                "parameters": {},
            },
        )
        acquired = storage.invoke("read_demand_result", demand)
        request = SemanticRequestKey(
            ddo_kernel["identities"]["urn:discover", "recipe"],
            "doc",
            {},
            {"parameters": {}, "replicate": None},
            inference,
            subject_context=SubjectContext(
                "ddo-test", "doc", root["original_source"], canonical_bytes(root["analyzed_scope"])
            ),
        )
        attached = storage.invoke(
            "attach_data_request",
            {
                **producer,
                "request_meaning": json.loads(request.identity.canonical_input),
                "request_key": request.identity.key,
                "replicate": None,
                "binding": {
                    "inputs": [],
                    "support": [],
                    "parameters": semantic_value(request.parameters),
                    "request_inputs": semantic_value({}),
                    "inference": inference,
                    "populations": [],
                    "read_id": acquired["read_id"],
                },
            },
        )
    sample_kind = ddo_kernel["identities"][
        next(k.semantic_id for k in ddo_kernel["model"].kinds if k.name == "Sample"), "kind"
    ]
    population_kind = ddo_kernel["identities"][
        next(k.semantic_id for k in ddo_kernel["model"].kinds if k.name == "Population"), "kind"
    ]
    packets = [
        {
            "member_id": f"m{value}",
            "kind_contract": sample_kind,
            "context": (
                member_body_contexts[position]
                if member_body_contexts is not None
                else member_contexts[position]
                if member_contexts is not None
                else {
                    "subject": f"item:{value}",
                    "original_source": "source:test",
                    "analyzed_scope": scope,
                }
            ),
            "body": {"value": value, "document_subject": "doc"},
        }
        for position, value in enumerate(values)
    ]
    fence = claim(ddo_kernel, attached)
    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **fence,
                "runtime_id": ddo_kernel["runtime"],
                "completion": {
                    "outcome": "success",
                    "inputs": [],
                    "support": [],
                    "implementation_revision": "native-test-source-v1",
                    "outputs": [
                        {
                            "role": "result",
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": population_kind,
                                "body": semantic_value({"complete": complete, "members": packets}),
                                "members": [
                                    {
                                        **packet,
                                        "context": member_contexts[position]
                                        if member_contexts is not None
                                        else packet["context"],
                                        "body": semantic_value(packet["body"]),
                                    }
                                    for position, packet in enumerate(packets)
                                ],
                            },
                        }
                    ],
                },
            },
        )
    receipt = publish(ddo_kernel, fence, intent)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        products = storage.invoke(
            "read_demand_result",
            {"demand_id": demand["demand_id"], "view": "products"},
        )
        product = next(use["products"][0] for use in products["uses"] if use["products"])
        parent = storage.invoke(
            "close_data_population",
            {
                "demand_id": demand["demand_id"],
                "name": "all-items",
                "product_id": product["product_id"],
                "derivation_id": receipt["derivation_id"],
                "member_role": "result",
            },
        )
        if ambiguous:
            storage.invoke(
                "close_data_population",
                {
                    "demand_id": demand["demand_id"],
                    "name": "other-items",
                    "product_id": product["product_id"],
                    "derivation_id": receipt["derivation_id"],
                    "member_role": "result",
                },
            )
    return demand, consumer, parent


@dataclass(frozen=True)
class TypedBindingEvidenceCase:
    name: str
    primitive: str
    left: object
    right: object
    core_equal: bool | None
    native_refuses: bool = False


# The planner may expose SQL unknown; the protected interpreter instead refuses
# a selected unknown operand. These are deliberately independent expectations.
TYPED_BINDING_EVIDENCE_CASES = (
    TypedBindingEvidenceCase(
        "integer-beyond-bigint",
        "integer",
        ["integer", "1208925819614629174706177"],
        ["integer", "1208925819614629174706177"],
        True,
    ),
    TypedBindingEvidenceCase(
        "adjacent-float",
        "float",
        ["float", "0x1.0000000000000p+0"],
        ["float", "0x1.0000000000001p+0"],
        False,
    ),
    TypedBindingEvidenceCase("typed-null", "integer", ["null"], ["integer", "1"], None, True),
    TypedBindingEvidenceCase("missing-field", "integer", None, ["integer", "1"], None, True),
    TypedBindingEvidenceCase(
        "leap-day-boundary", "date", ["date", "2000-02-29"], ["date", "2000-03-01"], False
    ),
    TypedBindingEvidenceCase(
        "adjacent-utc-instants",
        "datetime",
        ["datetime", "2000-01-01T00:00:00+00:00"],
        ["datetime", "2000-01-01T00:00:00.000001+00:00"],
        False,
    ),
)
