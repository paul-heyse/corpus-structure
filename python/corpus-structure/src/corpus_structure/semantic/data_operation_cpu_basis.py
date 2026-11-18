"""Finite typed input correspondence for captured CPU authority conclusions.

Source headers identify actual selected inputs; the child combines them with the
actual typed values it processes. Native builds the same meaning from immutable
products and the request's frozen binding. This adds no execution or receipt owner.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_model import SubjectContext
from .data_operation_support import (
    ComputationalSupportReference,
    SupportReference,
    support_reference_records,
)
from .identity import canonical_bytes
from .selected_support import ProducerOutputOccurrence

CPU_INPUT_BASIS_VERSION = "cpu-input-basis-3"
CPU_AUTHORITY_REPLY_VERSION = "cpu-authority-reply-2"
CPU_AUTHORITY_BATCH_REPLY_VERSION = "cpu-authority-batch-reply-1"

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult
    from .data_operation_model import ResolvedRoleBinding


@dataclass(frozen=True)
class CPUInputRole:
    role: str
    position: int | None
    multiplicity: int
    product_id: str
    member_id: str | None
    kind_contract: str
    context: SubjectContext
    body: Any
    support: tuple[SupportReference, ...]
    producer_output: ProducerOutputOccurrence | None = field(kw_only=True)

    def __post_init__(self) -> None:
        computed = any(isinstance(item, ComputationalSupportReference) for item in self.support)
        if computed != (self.producer_output is not None):
            raise ValueError("CPU computational input requires its exact emitting occurrence")
        if self.producer_output is not None and (
            not isinstance(self.producer_output, ProducerOutputOccurrence)
            or (
                self.producer_output.member_id is not None
                and self.producer_output.member_id != self.member_id
            )
        ):
            raise ValueError("CPU selected member differs from its emitting occurrence")


def cpu_input_basis(
    recipe: str,
    context: SubjectContext,
    roles: tuple[CPUInputRole, ...],
    *,
    parameters: bytes,
    replicate: str | None,
) -> list:
    """Reconstruct the exact basis with context and typed-value number semantics."""
    parameter_values = decode_semantic_value(json.loads(parameters))
    if not isinstance(parameter_values, dict):
        raise ValueError("CPU input parameters require their exact tagged mapping")
    if replicate is not None and (type(replicate) is not str or not replicate):
        raise ValueError("CPU input replicate requires an explicit selection or null")
    entries = []
    for role in roles:
        support = {
            canonical_bytes(semantic_value(item)): item
            for item in support_reference_records(role.support)
        }
        entries.append(
            {
                "role": role.role,
                "position": role.position,
                "multiplicity": role.multiplicity,
                "product_id": role.product_id,
                "member_id": role.member_id,
                "kind_contract": role.kind_contract,
                "context": role.context.identity_record,
                "body": role.body,
                "support": [support[key] for key in sorted(support)],
                "producer_output": (
                    None
                    if role.producer_output is None
                    else role.producer_output.model_dump(mode="python")
                ),
            }
        )
    entries.sort(
        key=lambda item: (
            item["role"],
            (item["position"] is not None, item["position"]),
            item["product_id"],
            (item["member_id"] is not None, item["member_id"]),
            item["kind_contract"],
            canonical_bytes(semantic_value(item["support"])),
            canonical_bytes(semantic_value(item["producer_output"])),
        )
    )
    return semantic_value(
        {
            "version": CPU_INPUT_BASIS_VERSION,
            "recipe": recipe,
            "context": context.identity_record,
            "roles": entries,
            "parameters": parameter_values,
            "replicate": replicate,
        }
    )


def cpu_input_basis_from_binding(
    recipe: str,
    binding: BindingResult,
    bodies_by_role: Mapping[str, tuple[Any, ...]],
) -> list:
    """Pair actual consumed values with their existing selected headers and support."""
    if not binding.sufficient or binding.subject_context is None:
        raise ValueError("CPU authority basis requires its sufficient native binding")
    return cpu_input_basis_from_roles(
        recipe,
        binding.subject_context,
        binding.roles,
        bodies_by_role,
        parameters=binding.parameters,
        replicate=binding.replicate,
    )


def cpu_input_basis_from_roles(
    recipe: str,
    context: SubjectContext,
    selected_roles: tuple[ResolvedRoleBinding, ...],
    bodies_by_role: Mapping[str, tuple[Any, ...]],
    *,
    parameters: bytes,
    replicate: str | None,
) -> list:
    """Pair actual role values with complete headers, shared by parent and CPU consumer."""
    roles = []
    declared = {role.role for role in selected_roles}
    if len(declared) != len(selected_roles):
        raise ValueError("CPU authority selected headers repeat a role")
    if set(bodies_by_role) != declared:
        raise ValueError("CPU authority values differ from their actual bound roles")
    for selected in selected_roles:
        bodies = bodies_by_role[selected.role]
        if len(bodies) != len(selected.members):
            raise ValueError("CPU authority values differ from their actual selected population")
        for member, body in zip(selected.members, bodies, strict=True):
            roles.append(
                CPUInputRole(
                    selected.role,
                    member.position,
                    member.multiplicity,
                    member.product,
                    member.member,
                    member.kind_contract,
                    SubjectContext(
                        context.project_id,
                        member.subject,
                        member.original_source,
                        member.analyzed_scope,
                        subject_definition=member.subject_definition,
                    ),
                    body,
                    member.support_references,
                    producer_output=member.producer_output,
                )
            )
    return cpu_input_basis(
        recipe,
        context,
        tuple(roles),
        parameters=parameters,
        replicate=replicate,
    )


def cpu_basis_values(
    input_basis: list,
    *,
    scalar_roles: tuple[str, ...],
    set_roles: tuple[str, ...],
    sequence_roles: tuple[str, ...] = (),
) -> tuple[dict[str, tuple[CPUInputRole, ...]], SubjectContext]:
    """Decode finite actual input headers and values, without authenticating them.

    Empty set grouping is only a decoded population. Native authorization,
    execution correspondence and domain inspection/coverage remain with callers.
    """
    from .data_operation_json import json_bytes
    from .data_operation_support import read_support_references

    _require_current_basis(input_basis)
    basis = decode_semantic_value(input_basis)
    if (
        type(basis["recipe"]) is not str
        or not basis["recipe"]
        or not isinstance(basis["roles"], list)
    ):
        raise ValueError("CPU input basis requires its actual recipe and role sequence")
    names = (*scalar_roles, *set_roles, *sequence_roles)
    if len(set(names)) != len(names) or any(type(name) is not str or not name for name in names):
        raise ValueError("CPU input decoder requires distinct finite role names")

    def context(value):
        if (
            not isinstance(value, dict)
            or set(value)
            != {"project_id", "subject", "subject_definition", "original_source", "analyzed_scope"}
            or not isinstance(value["analyzed_scope"], dict)
        ):
            raise ValueError("CPU input context differs from its complete typed contract")
        return SubjectContext(
            value["project_id"],
            value["subject"],
            value["original_source"],
            json_bytes(value["analyzed_scope"]),
            subject_definition=value["subject_definition"],
        )

    selected_context = context(basis["context"])
    grouped = {name: [] for name in names}
    seen = set()
    for row in basis["roles"]:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "role",
                "position",
                "multiplicity",
                "product_id",
                "member_id",
                "kind_contract",
                "context",
                "body",
                "support",
                "producer_output",
            }
            or type(row["role"]) is not str
            or row["role"] not in grouped
            or type(row["multiplicity"]) is not int
            or row["multiplicity"] != 1
        ):
            raise ValueError("CPU inputs differ from their exact finite scalar/set roles")
        if (
            any(
                type(row[field]) is not str or not row[field]
                for field in ("product_id", "kind_contract")
            )
            or (
                row["member_id"] is not None
                and (type(row["member_id"]) is not str or not row["member_id"])
            )
            or (
                row["position"] is not None
                and (type(row["position"]) is not int or row["position"] < 0)
            )
        ):
            raise ValueError("CPU input header lacks its exact product/member/position")
        if not isinstance(row["support"], list):
            raise ValueError("CPU input support requires its exact selected reference sequence")
        meaning = canonical_bytes(semantic_value(row))
        if meaning in seen:
            raise ValueError("CPU input population repeats an exact selected header/value")
        seen.add(meaning)
        grouped[row["role"]].append(
            CPUInputRole(
                row["role"],
                row["position"],
                row["multiplicity"],
                row["product_id"],
                row["member_id"],
                row["kind_contract"],
                context(row["context"]),
                row["body"],
                read_support_references(row["support"]),
                producer_output=(
                    None
                    if row["producer_output"] is None
                    else ProducerOutputOccurrence.model_validate(row["producer_output"])
                ),
            )
        )
    if any(len(grouped[name]) != 1 for name in scalar_roles):
        raise ValueError("CPU computation requires each exact scalar input")
    for name in sequence_roles:
        if tuple(row.position for row in grouped[name]) != tuple(range(len(grouped[name]))):
            raise ValueError("CPU sequence inputs require exact contiguous ordered positions")
    return {name: tuple(rows) for name, rows in grouped.items()}, selected_context


def require_consumed_cpu_basis(
    input_basis: list,
    context: SubjectContext,
    roles: tuple[ResolvedRoleBinding, ...],
    bodies_by_role: Mapping[str, tuple[Any, ...]],
    *,
    parameters: bytes,
) -> None:
    """Check actual consumed headers, bodies and parameters against the native basis."""
    _require_current_basis(input_basis)
    supplied = decode_semantic_value(input_basis)
    expected = cpu_input_basis_from_roles(
        supplied["recipe"],
        context,
        roles,
        bodies_by_role,
        parameters=parameters,
        replicate=supplied["replicate"],
    )
    if canonical_bytes(expected) != canonical_bytes(input_basis):
        raise ValueError("CPU arguments differ from their actual exact input basis")


def cpu_authority_reply(input_basis: list, output: Any) -> dict:
    """Bind an actual child result to the exact typed inputs it processed."""
    _require_current_basis(input_basis)
    return {
        "version": CPU_AUTHORITY_REPLY_VERSION,
        "input_basis_digest": sha256(canonical_bytes(input_basis)).hexdigest(),
        "output": semantic_value(output),
    }


def cpu_authority_value(content: bytes, *, expected_basis: list) -> Any:
    """Decode the retained exact result without losing typed scalar meaning."""
    _require_current_basis(expected_basis)
    reply = json.loads(content)
    if (
        not isinstance(reply, dict)
        or set(reply) != {"version", "input_basis_digest", "output"}
        or reply["version"] != CPU_AUTHORITY_REPLY_VERSION
        or not isinstance(reply["input_basis_digest"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", reply["input_basis_digest"])
        or reply["input_basis_digest"] != sha256(canonical_bytes(expected_basis)).hexdigest()
    ):
        raise ValueError("CPU authority reply differs from its actual processed input basis")
    return decode_semantic_value(reply["output"])


def _require_current_basis(basis):
    value = decode_semantic_value(basis)
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "recipe", "context", "roles", "parameters", "replicate"}
        or (
            value["version"] != CPU_INPUT_BASIS_VERSION
            or not isinstance(value["parameters"], dict)
            or (
                value["replicate"] is not None
                and (type(value["replicate"]) is not str or not value["replicate"])
            )
        )
    ):
        raise ValueError("CPU authority requires the current exact input basis")


def _producer_fence(producer):
    if (
        not isinstance(producer, dict)
        or set(producer) != {"request_id", "generation", "task_id", "attempt", "holder"}
        or (
            any(
                type(producer[name]) is not int or producer[name] < 1
                for name in ("generation", "task_id", "attempt")
            )
            or any(
                type(producer[name]) is not str or not producer[name]
                for name in ("request_id", "holder")
            )
        )
    ):
        raise ValueError("CPU batch member requires its exact original producer fence")
    return producer


def _batch_members(members):
    members = tuple(members)
    if not members or any(
        not isinstance(value, dict)
        or set(value) != {"member", "producer", "input_basis"}
        or type(value["member"]) is not str
        or not value["member"]
        for value in members
    ):
        raise ValueError("CPU batch requires its explicit ordered logical membership")
    for value in members:
        _producer_fence(value["producer"])
        _require_current_basis(value["input_basis"])
    if len({value["member"] for value in members}) != len(members) or len(
        {(value["producer"]["request_id"], value["producer"]["generation"]) for value in members}
    ) != len(members):
        raise ValueError("CPU batch repeats a logical member or producing request generation")
    return members


def cpu_authority_batch_reply(members, outputs) -> dict:
    """One actual reply retains the complete ordered cohort and each original fence."""
    members, outputs = _batch_members(members), tuple(outputs)
    if len(outputs) != len(members):
        raise ValueError("CPU batch output population differs from its actual cohort")
    return {
        "version": CPU_AUTHORITY_BATCH_REPLY_VERSION,
        "members": [
            {
                "member": member["member"],
                "producer": dict(member["producer"]),
                "input_basis_digest": sha256(canonical_bytes(member["input_basis"])).hexdigest(),
                "output": semantic_value(output),
            }
            for member, output in zip(members, outputs, strict=True)
        ],
    }


def cpu_authority_batch_values(content: bytes, *, expected_members) -> tuple[Any, ...]:
    """Scatter only the original whole reply; never mint a per-member receipt."""
    expected_members = _batch_members(expected_members)
    reply = json.loads(content)
    if (
        not isinstance(reply, dict)
        or set(reply) != {"version", "members"}
        or (
            reply["version"] != CPU_AUTHORITY_BATCH_REPLY_VERSION
            or not isinstance(reply["members"], list)
            or len(reply["members"]) != len(expected_members)
        )
    ):
        raise ValueError("CPU batch reply differs from its actual ordered membership")
    values = []
    for actual, expected in zip(reply["members"], expected_members, strict=True):
        if (
            not isinstance(actual, dict)
            or set(actual) != {"member", "producer", "input_basis_digest", "output"}
            or (
                actual["member"] != expected["member"]
                or actual["producer"] != expected["producer"]
                or actual["input_basis_digest"]
                != sha256(canonical_bytes(expected["input_basis"])).hexdigest()
            )
        ):
            raise ValueError("CPU batch reply differs from its original member/fence/input basis")
        values.append(decode_semantic_value(actual["output"]))
    return tuple(values)


def cpu_input_basis_native_sql(*, target_metadata=None) -> str:
    """Lower exact CPU input/producer/reply correspondence from captured relations."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Integer,
        Text,
        and_,
        cast,
        column,
        func,
        literal,
        null,
        or_,
        select,
    )
    from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array

    from .metadata import get_metadata
    from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
    from .native_program import (
        Assign,
        Block,
        ForQuery,
        If,
        Local,
        Parameter,
        Perform,
        Raise,
        Return,
        SelectInto,
        column_type,
        core_variable,
        function,
        pg_type,
        variable,
    )

    model = get_metadata() if target_metadata is None else target_metadata
    requests = model.tables["ops.data_request"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    intents = model.tables["ops.data_completion_intent"]
    tasks = model.tables["ops.task"]
    runtimes = model.tables["sem.runtime_binding"]
    definitions = model.tables["sem.data_operation_definition"]
    policy = ("pg_catalog", "pg_temp")
    request = core_variable("r", JSONB())
    completion = core_variable("completion", JSONB())

    def row(local, relation, name):
        return core_variable(local, relation.c[name].type, name)

    def rf(name):
        return row("r", requests, name)

    def json_(value):
        return cast(literal(json.dumps(value, ensure_ascii=False, separators=(",", ":"))), JSONB())

    def object_(*values):
        return func.jsonb_build_object(*values, type_=JSONB())

    def array_(*values):
        return func.jsonb_build_array(*values, type_=JSONB())

    def mapping_(*pairs):
        return array_("mapping", array_(*(array_(name, value) for name, value in pairs)))

    def json_meaning(value):
        return func.data.ddo_json_meaning(value, type_=JSONB())

    def normalize(value):
        return func.data.ddo_normalize(value, type_=JSONB())

    def field(value, name):
        return func.data.ddo_field(value, name, type_=JSONB())

    def nullable_tag(kind, value):
        from sqlalchemy import case

        return case((value.is_(None), json_(["null"])), else_=array_(kind, value))

    def items(value, name):
        return func.jsonb_array_elements(value).table_valued(column("value", JSONB())).alias(name)

    def digest(value):
        return func.ops.ddo_digest(value, type_=Text())

    def has_all(value, names):
        return value.has_all(array(names, type_=Text()))

    def without(value, names):
        return value.op("-", return_type=JSONB())(array(names, type_=Text()))

    def routine(name, body, locals_, *, reply=False):
        parameters = (Parameter("r", pg_type("ops", "data_request")),)
        if reply:
            parameters += (Parameter("completion", pg_type("jsonb")),)
        identity = NativeIdentity(
            "function",
            "ops",
            name,
            ("ops.data_request", "jsonb") if reply else ("ops.data_request",),
        )
        return native_sql_script(
            (
                function(
                    "ops",
                    name,
                    parameters=parameters,
                    returns=pg_type("jsonb"),
                    body=Block(body, locals_),
                    volatility="stable",
                    security_definer=True,
                    search_path=policy,
                ),
                native_privilege_sql(identity, "PUBLIC", grant=False),
            )
        )

    selected, roles, support_refs, meaning, context_meaning, output_meaning = (
        core_variable(name, JSONB())
        for name in (
            "selected",
            "roles",
            "support_refs",
            "meaning",
            "context_meaning",
            "output_meaning",
        )
    )
    inputs = items(rf("binding")["inputs"], "inputs")
    entry = (
        func.ops.ddo_input_support_refs(rf("binding"), selected)
        .table_valued(
            column("item", JSONB()),
        )
        .render_derived(name="entry")
    )
    item = entry.c.item
    from sqlalchemy import case

    reference = func.jsonb_strip_nulls(
        case(
            (
                func.coalesce(item["kind"].astext, "computation") == "computation",
                object_(
                    "kind",
                    "computation",
                    "derivation_id",
                    item["derivation_id"].astext,
                    "admission_use_id",
                    item["admission_use_id"].astext,
                ),
            ),
            else_=object_(
                "kind",
                item["kind"].astext,
                "admission_id",
                item["admission_id"].astext,
                "source_reference",
                item["source_reference"].astext,
            ),
        ),
        type_=JSONB(),
    )
    admitted = (
        select(reference.label("reference")).distinct().select_from(entry).subquery("admitted")
    )
    support_order = func.convert_to(
        func.data.canonical_json(json_meaning(admitted.c.reference)), "UTF8"
    )
    computational = items(support_refs, "ref")
    has_computation = (
        select(1)
        .select_from(computational)
        .where(
            computational.c.value["kind"].astext == "computation",
        )
        .exists()
    )
    selected_output = selected["producer_output"]

    def pf(name):
        return row("product", products, name)

    def mf(name):
        return row("member", members, name)

    role_rows = items(roles, "role_rows")
    value = role_rows.c.value
    role_order = (
        field(value, "role")[1].astext.collate("C"),
        cast(field(value, "position")[1].astext, BigInteger()).nulls_first(),
        field(value, "product_id")[1].astext.collate("C"),
        field(value, "member_id")[1].astext.collate("C").nulls_first(),
        field(value, "kind_contract")[1].astext.collate("C"),
        *(
            func.convert_to(func.data.canonical_json(normalize(field(value, name))), "UTF8")
            for name in ("support", "producer_output")
        ),
    )
    basis = routine(
        "ddo_cpu_input_basis",
        (
            If(
                field(rf("binding")["parameters"], "replicate").is_distinct_from(
                    json_meaning(object_("replicate", rf("replicate"))["replicate"])
                ),
                (
                    Raise(
                        "CPU input basis requires the actual exact request replicate wrapper",
                        "23514",
                    ),
                ),
            ),
            ForQuery(
                ("selected",),
                select(inputs.c.value),
                (
                    SelectInto(
                        select(products).where(
                            products.c.id == selected["product_id"].astext,
                            products.c.project_id == rf("project_id"),
                        ),
                        ("product",),
                        strict=True,
                    ),
                    Assign("member", null()),
                    If(
                        selected["member_id"].astext.is_not(None),
                        (
                            SelectInto(
                                select(members).where(
                                    members.c.product_id == pf("id"),
                                    members.c.member_id == selected["member_id"].astext,
                                ),
                                ("member",),
                                strict=True,
                            ),
                        ),
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_agg(
                                    aggregate_order_by(admitted.c.reference, support_order)
                                ),
                                json_([]),
                            )
                        ).select_from(admitted),
                        ("support_refs",),
                    ),
                    If(
                        or_(
                            ~selected.has_key("producer_output"),
                            and_(
                                has_computation,
                                func.jsonb_typeof(selected_output).is_distinct_from("object"),
                            ),
                            and_(~has_computation, selected_output.is_distinct_from(json_(None))),
                            and_(
                                selected_output["member_id"].astext.is_not(None),
                                selected_output["member_id"].astext.is_distinct_from(
                                    mf("member_id")
                                ),
                            ),
                        ),
                        (
                            Raise(
                                "CPU input basis requires its exact emitting occurrence and selected member",
                                "23514",
                            ),
                        ),
                    ),
                    Assign(
                        "output_meaning",
                        case(
                            (selected_output == json_(None), json_(["null"])),
                            else_=mapping_(
                                (
                                    "member_id",
                                    nullable_tag("string", selected_output["member_id"].astext),
                                ),
                                ("role", array_("string", selected_output["role"].astext)),
                                ("position", array_("integer", selected_output["position"].astext)),
                                (
                                    "multiplicity",
                                    array_("integer", selected_output["multiplicity"].astext),
                                ),
                            ),
                        ),
                    ),
                    Assign(
                        "context_meaning",
                        json_meaning(
                            object_(
                                "project_id",
                                rf("project_id"),
                                "subject",
                                func.coalesce(mf("subject"), pf("subject")),
                                "subject_definition",
                                func.coalesce(mf("subject_definition"), pf("subject_definition")),
                                "original_source",
                                case(
                                    (mf("member_id").is_(None), pf("original_source")),
                                    else_=mf("original_source"),
                                ),
                                "analyzed_scope",
                                func.coalesce(mf("analyzed_scope"), pf("analyzed_scope")),
                            )
                        ),
                    ),
                    Assign(
                        "meaning",
                        mapping_(
                            ("role", array_("string", selected["role"].astext)),
                            ("position", nullable_tag("integer", selected["position"].astext)),
                            ("multiplicity", array_("integer", selected["multiplicity"].astext)),
                            ("product_id", array_("string", pf("id"))),
                            ("member_id", nullable_tag("string", mf("member_id"))),
                            (
                                "kind_contract",
                                array_(
                                    "string",
                                    func.coalesce(mf("kind_contract"), pf("kind_contract")),
                                ),
                            ),
                            ("context", context_meaning),
                            ("body", func.coalesce(mf("body"), pf("canonical_body"))),
                            ("support", json_meaning(support_refs)),
                            ("producer_output", output_meaning),
                        ),
                    ),
                    Assign("roles", roles.op("||")(array_(meaning))),
                ),
            ),
            SelectInto(
                select(
                    func.coalesce(func.jsonb_agg(aggregate_order_by(value, *role_order)), json_([]))
                ).select_from(role_rows),
                ("roles",),
            ),
            Return(
                normalize(
                    mapping_(
                        ("version", array_("string", CPU_INPUT_BASIS_VERSION)),
                        ("recipe", array_("string", rf("recipe"))),
                        (
                            "context",
                            json_meaning(
                                object_(
                                    "project_id",
                                    rf("project_id"),
                                    "subject",
                                    rf("subject"),
                                    "subject_definition",
                                    func.ops.ddo_operation_subject(
                                        rf("release_id"), rf("operation_id")
                                    ),
                                    "original_source",
                                    rf("original_source"),
                                    "analyzed_scope",
                                    rf("analyzed_scope"),
                                )
                            ),
                        ),
                        ("roles", array_("sequence", roles)),
                        ("parameters", normalize(field(rf("binding")["parameters"], "parameters"))),
                        ("replicate", normalize(field(rf("binding")["parameters"], "replicate"))),
                    )
                )
            ),
        ),
        (
            Local("selected", pg_type("jsonb")),
            Local("product", products),
            Local("member", members),
            Local("roles", pg_type("jsonb"), json_([])),
            *(
                Local(name, pg_type("jsonb"))
                for name in ("support_refs", "meaning", "context_meaning", "output_meaning")
            ),
        ),
    )

    original = core_variable("original", JSONB())
    result = core_variable("result", JSONB())
    runtime = core_variable("runtime", runtimes.c.runtime_id.type)

    def of(name):
        return row("original", intents, name)

    def tf(name):
        return row("task", tasks, name)

    evidence = completion["execution_evidence"]
    retained_intent = select(intents).where(
        intents.c.request_id == rf("id"),
        intents.c.generation == cast(evidence["generation"].astext, Integer()),
    )
    already_retained = (
        select(1)
        .select_from(intents)
        .where(
            intents.c.request_id == rf("id"),
            intents.c.generation == rf("generation"),
        )
        .exists()
    )
    admitted_runtime = (
        select(1)
        .select_from(runtimes)
        .where(
            runtimes.c.release_id == rf("release_id"),
            runtimes.c.runtime_id == runtime,
            cast(func.convert_from(runtimes.c.manifest_bytes, "UTF8"), JSONB())[
                "execution_profile"
            ].astext
            == rf("binding")["execution_profile"].astext,
        )
        .exists()
    )
    result_fields = (
        func.jsonb_each(result)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .alias("field")
    )
    producer = routine(
        "ddo_cpu_original_producer",
        (
            SelectInto(retained_intent, ("original",)),
            If(
                core_variable("found", Boolean()),
                (
                    If(
                        or_(
                            of("payload_digest").is_distinct_from(digest(completion)),
                            of("payload").is_distinct_from(completion),
                        ),
                        (
                            Raise(
                                "CPU batch completion differs from immutable original intent digest/payload",
                                "23514",
                            ),
                        ),
                    ),
                    Assign(
                        "result",
                        object_(
                            "request_id",
                            of("request_id"),
                            "generation",
                            of("generation"),
                            "task_id",
                            of("producer_task_id"),
                            "attempt",
                            of("producer_attempt"),
                            "holder",
                            of("producer_holder"),
                        ),
                    ),
                    Assign("runtime", of("runtime_id")),
                ),
                (
                    If(
                        already_retained,
                        (
                            Raise(
                                "CPU batch completion differs from immutable original retained intent",
                                "23514",
                            ),
                        ),
                    ),
                    SelectInto(
                        select(tasks).where(
                            tasks.c.id == rf("live_task_id"),
                            tasks.c.data_request_id == rf("id"),
                            tasks.c.data_generation == rf("generation"),
                            tasks.c.status == "running",
                            tasks.c.lease_until > func.clock_timestamp(),
                        ),
                        ("task",),
                        strict=True,
                    ),
                    Assign(
                        "result",
                        object_(
                            "request_id",
                            rf("id"),
                            "generation",
                            rf("generation"),
                            "task_id",
                            tf("id"),
                            "attempt",
                            tf("attempt"),
                            "holder",
                            tf("claimed_by"),
                        ),
                    ),
                    Assign("runtime", evidence["runtime_id"].astext),
                    Perform(func.sem.require_runtime_binding(rf("release_id"), runtime)),
                    Perform(
                        func.ops.ddo_require_provider_profile(
                            rf("release_id"), rf("operation_id"), runtime
                        )
                    ),
                    If(
                        ~admitted_runtime,
                        (
                            Raise(
                                "CPU original runtime execution profile differs from admitted request",
                                "23514",
                            ),
                        ),
                    ),
                ),
            ),
            If(
                or_(
                    select(1)
                    .select_from(result_fields)
                    .where(
                        result_fields.c.value.is_distinct_from(
                            evidence.op("->", return_type=JSONB())(result_fields.c.key)
                        )
                    )
                    .exists(),
                    evidence["runtime_id"].astext.is_distinct_from(runtime),
                ),
                (
                    Raise(
                        "CPU batch evidence differs from its native original producer owner",
                        "23514",
                    ),
                ),
            ),
            Return(result),
        ),
        (
            Local("original", intents),
            Local("task", tasks),
            Local("result", pg_type("jsonb")),
            Local("runtime", column_type(runtimes.c.runtime_id)),
        ),
        reply=True,
    )

    reply = core_variable("reply", JSONB())
    forms = core_variable("forms", JSONB())
    batch_item = core_variable("item", JSONB())
    chosen = core_variable("chosen", JSONB())
    batch_producer = core_variable("producer", JSONB())
    matches = core_variable("matches", Integer())
    population = items(reply["members"], "batch_member")
    scalar_keys = ["version", "input_basis_digest", "output"]
    batch_keys = ["version", "members"]
    member_keys = ["member", "producer", "input_basis_digest", "output"]
    producer_keys = ["request_id", "generation", "task_id", "attempt", "holder"]
    expected_basis = digest(func.ops.ddo_cpu_input_basis(original, type_=JSONB()))
    batch = (
        If(
            or_(
                forms.is_distinct_from(json_(["batch"])),
                ~has_all(reply, batch_keys),
                without(reply, batch_keys).is_distinct_from(json_({})),
                func.jsonb_typeof(reply["members"]).is_distinct_from("array"),
                func.jsonb_array_length(reply["members"]) < 1,
            ),
            (
                Raise(
                    "CPU batch reply differs from its actual declared invocation form/membership",
                    "23514",
                ),
            ),
        ),
        If(
            or_(
                select(1)
                .select_from(population)
                .group_by(population.c.value["member"].astext)
                .having(func.count() != 1)
                .exists(),
                select(1)
                .select_from(population)
                .group_by(
                    population.c.value["producer"]["request_id"].astext,
                    population.c.value["producer"]["generation"],
                )
                .having(func.count() != 1)
                .exists(),
            ),
            (
                Raise(
                    "CPU batch reply repeats a logical member or original producing generation",
                    "23514",
                ),
            ),
        ),
        Assign("producer", func.ops.ddo_cpu_original_producer(request, completion)),
        ForQuery(
            ("item",),
            select(population.c.value),
            (
                If(
                    or_(
                        ~has_all(batch_item, member_keys),
                        without(batch_item, member_keys).is_distinct_from(json_({})),
                        func.jsonb_typeof(batch_item["member"]).is_distinct_from("string"),
                        func.nullif(batch_item["member"].astext, "").is_(None),
                        func.jsonb_typeof(batch_item["producer"]).is_distinct_from("object"),
                        ~has_all(batch_item["producer"], producer_keys),
                        without(batch_item["producer"], producer_keys).is_distinct_from(json_({})),
                        batch_item["input_basis_digest"]
                        .astext.op("~")("^[0-9a-f]{64}$")
                        .is_not(True),
                    ),
                    (
                        Raise(
                            "CPU batch member lacks its exact original producer/basis/output",
                            "23514",
                        ),
                    ),
                ),
                Perform(normalize(batch_item["output"])),
                If(
                    and_(
                        batch_item["producer"]["request_id"].astext == rf("id"),
                        batch_item["producer"] == batch_producer,
                    ),
                    (Assign("matches", matches + 1), Assign("chosen", batch_item)),
                ),
            ),
        ),
        If(
            or_(matches != 1, chosen["input_basis_digest"].astext.is_distinct_from(expected_basis)),
            (
                Raise(
                    "CPU batch output differs from original producer fence/exact input basis",
                    "23514",
                ),
            ),
        ),
        Return(normalize(chosen["output"])),
    )
    output = routine(
        "ddo_cpu_reply_output",
        (
            If(
                ~has_all(completion, ["inputs", "support"]),
                (
                    Raise(
                        "CPU reply requires its original completion input/support binding", "23514"
                    ),
                ),
            ),
            Assign(
                ("original", "binding"),
                rf("binding").op("||")(
                    object_(
                        "inputs",
                        completion["inputs"],
                        "support",
                        completion["support"],
                    )
                ),
            ),
            SelectInto(
                select(definitions.c.support_contract["capabilities"]["forms"]).where(
                    definitions.c.release_id == rf("release_id"),
                    definitions.c.operation_id == rf("operation_id"),
                ),
                ("forms",),
                strict=True,
            ),
            If(
                reply["version"].astext == CPU_AUTHORITY_REPLY_VERSION,
                (
                    If(
                        or_(
                            forms.is_distinct_from(json_(["scalar"])),
                            ~has_all(reply, scalar_keys),
                            without(reply, scalar_keys).is_distinct_from(json_({})),
                            reply["input_basis_digest"].astext.is_distinct_from(expected_basis),
                        ),
                        (
                            Raise(
                                "CPU authority reply differs from exact native input basis/form",
                                "23514",
                            ),
                        ),
                    ),
                    Return(normalize(reply["output"])),
                ),
                (
                    If(
                        reply["version"].astext == CPU_AUTHORITY_BATCH_REPLY_VERSION,
                        batch,
                        (
                            Raise(
                                "CPU authority reply has no current scalar or batch contract",
                                "23514",
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            Local("reply", pg_type("jsonb"), func.ops.ddo_cpu_reply_value(completion)),
            Local("original", requests, variable("r")),
            *(Local(name, pg_type("jsonb")) for name in ("forms", "item", "chosen", "producer")),
            Local("matches", pg_type("int4"), literal(0)),
        ),
        reply=True,
    )
    return native_sql_script((basis, producer, output)) + "\n"
