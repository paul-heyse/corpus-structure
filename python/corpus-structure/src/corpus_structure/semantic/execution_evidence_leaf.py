"""Bounded selected CPU-member provenance, without sibling bodies or standing.

The native/capture custodian authenticates this projection. Detached consumers can
check its declared correspondence, not replay the undisclosed whole physical reply.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from ._data_operation_wire import WireAttemptFence, WireCompletion
from .cpu_receipts import CPUExecutionReceipt

if TYPE_CHECKING:
    from .native_program_registry import ProgramDeclaration


class NativeExecutionEvidenceLeaf(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    format: Literal["ddo-native-execution-evidence-leaf-v1"]
    derivation_id: str = Field(min_length=1)
    use_id: str | None
    issuer_operation: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    recipe: str = Field(min_length=1)
    producer: WireAttemptFence
    intent_id: str = Field(min_length=1)
    intent_payload_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    selected_completion: WireCompletion
    publication_receipt_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    kind_contract: str = Field(min_length=1)
    output_role: str = Field(min_length=1)
    output_position: int = Field(ge=0)
    cpu_receipt: CPUExecutionReceipt
    whole_reply_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    member: str = Field(min_length=1)
    member_ordinal: int = Field(ge=0)
    cohort_size: int = Field(ge=1)
    cohort_membership_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    input_basis_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    member_output_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    physical_cohort: Literal["undisclosed"]
    verification: Literal["native-checked-member-projection"]

    @model_validator(mode="before")
    @classmethod
    def projected_completion(cls, value):
        from .data_operation_cpu_basis import _producer_fence
        from .data_operation_wire import validate_wire_schema, wire_record_schema

        if not isinstance(value, dict):
            raise ValueError("execution leaf requires its explicitly projected completion")
        _producer_fence(value.get("producer"))
        completion = value.get("selected_completion")
        if not isinstance(completion, dict):
            raise ValueError("execution leaf requires its selected completion facts")
        if "cpu_replies" in completion.get("execution_evidence", {}):
            raise ValueError(
                "selected execution projection must not disclose physical cohort replies"
            )
        validate_wire_schema(wire_record_schema("completion"), completion)
        return value

    @field_validator("cpu_receipt", mode="before")
    @classmethod
    def decode_receipt(cls, value):
        from .identity import canonical_bytes

        if isinstance(value, CPUExecutionReceipt):
            return value
        return TypeAdapter(CPUExecutionReceipt).validate_json(canonical_bytes(value))

    @model_validator(mode="after")
    def original_receipt(self):
        if (
            self.whole_reply_digest != self.cpu_receipt.result_digest
            or self.member_ordinal >= self.cohort_size
        ):
            raise ValueError(
                "execution leaf differs from its actual whole CPU receipt or member position"
            )
        evidence = self.selected_completion.get("execution_evidence", {})
        if any(evidence.get(key) != value for key, value in self.producer.items()) or (
            evidence.get("runtime_id") != self.runtime_id
            or evidence.get("cpu_receipts") != [self.cpu_receipt.record()]
        ):
            raise ValueError("selected completion differs from its original producer/CPU receipt")
        return self


def execution_evidence_leaf_schema():
    """Compose the leaf with the exact native contract of its selected completion."""
    from .data_operation_wire import NativeJsonSchema, schema_closure, wire_record_schema

    leaf = NativeExecutionEvidenceLeaf.model_json_schema(schema_generator=NativeJsonSchema)
    completion = wire_record_schema("completion")
    leaf["properties"]["selected_completion"] = {"$ref": completion["$ref"]}
    local = leaf.pop("definitions")
    native = completion["definitions"]
    if any(local[name] != native[name] for name in local.keys() & native.keys()):
        raise ValueError("execution leaf schema conflicts with a native completion definition")
    return schema_closure(leaf, {**local, **native})


def validate_execution_evidence_leaf(
    value, *, products, requests, derivations, receipts, definitions, runtimes, outputs, uses=None
):
    """Interpret the bounded native assertion without claiming hidden-reply replay."""
    from .data_operation_json import json_bytes
    from .identity import canonical_bytes

    leaf = NativeExecutionEvidenceLeaf.model_validate_json(json_bytes(value))
    producer = leaf.producer
    request = requests[producer["request_id"]]
    episode = derivations[leaf.derivation_id]
    receipt = receipts[leaf.publication_receipt_id]
    product = products[leaf.product_id]
    definition = definitions[leaf.release_id, leaf.issuer_operation]
    if (
        request["operation_id"] != leaf.issuer_operation
        or episode["request_id"] != producer["request_id"]
        or episode["intent_id"] != leaf.intent_id
        or episode["producer_task_id"] != producer["task_id"]
        or episode["producer_attempt"] != producer["attempt"]
        or episode["generation"] != producer["generation"]
        or episode["runtime_id"] != leaf.runtime_id
        or episode["release_id"] != leaf.release_id
        or episode["recipe"] != leaf.recipe
        or receipt["intent_id"] != leaf.intent_id
        or receipt["derivation_id"] != leaf.derivation_id
        or product["kind_contract"] != leaf.kind_contract
        or not any(
            output["derivation_id"] == leaf.derivation_id
            and output["product_id"] == leaf.product_id
            and output["role"] == leaf.output_role
            and output["position"] == leaf.output_position
            and output["member_id"] is None
            for output in outputs
        )
        or (leaf.release_id, leaf.runtime_id) not in runtimes
    ):
        raise ValueError(
            "execution evidence leaf differs from its actual selected producer/publication"
        )
    if leaf.use_id is not None:
        if uses is None:
            raise ValueError("execution evidence leaf requires its actual selected use")
        use = uses[leaf.use_id]
        if (use["derivation_id"], use["request_id"], use["generation"], use["fate"]) != (
            leaf.derivation_id,
            producer["request_id"],
            producer["generation"],
            "fulfilled",
        ):
            raise ValueError("execution evidence leaf differs from its selected use")
    capability = definition["support_contract"]["capabilities"]
    if (
        capability["forms"] != ["batch"]
        or capability["preparation"] != "resource"
        or definition["profile"] != "derivation"
        or definition["support_contract"]["effects"] != []
        or definition["recipe"] != leaf.recipe
    ):
        raise ValueError(
            "execution evidence leaf lacks its explicit captured prepared batch contract"
        )
    roles = definition["output_roles"]
    result_fields = definition["support_contract"].get("result_fields")
    if (
        not any(
            role["name"] == leaf.output_role and role["kind_contract"] == leaf.kind_contract
            for role in roles
        )
        or not isinstance(result_fields, dict)
        or (
            result_fields
            and (
                not isinstance(result_fields.get(leaf.output_role), str)
                or not result_fields[leaf.output_role]
            )
        )
        or (not result_fields and (len(roles) != 1 or roles[0]["name"] != leaf.output_role))
    ):
        raise ValueError("execution evidence leaf lacks its exact archived output projection")
    selected_outputs = leaf.selected_completion["outputs"]
    if len(selected_outputs) != 1 or any(
        (
            selected_outputs[0]["role"] != leaf.output_role,
            selected_outputs[0]["position"] != leaf.output_position,
            selected_outputs[0].get("member_id") is not None,
            selected_outputs[0]["multiplicity"] != 1,
            selected_outputs[0]["product"]["kind_contract"] != leaf.kind_contract,
            selected_outputs[0]["product"]["body"] != product["canonical_body"],
        )
    ):
        raise ValueError("selected completion differs from its exact logical output")
    from hashlib import sha256

    if sha256(canonical_bytes(product["canonical_body"])).hexdigest() != leaf.member_output_digest:
        raise ValueError("execution member projection differs from its exact selected product")
    return leaf


def combine_execution_evidence_leaves(
    leaves: Iterable[NativeExecutionEvidenceLeaf],
) -> dict[str, tuple[NativeExecutionEvidenceLeaf, WireCompletion]]:
    """Join exact output projections while preserving their common original custody.

    Each leaf authenticates one output occurrence. The caller checks the combined
    output inventory against the retained episode edges to detect missing leaves.
    This reconstructs disclosed semantic completion facts, never the private intent.
    """
    grouped: dict[str, dict[tuple[str, int], NativeExecutionEvidenceLeaf]] = {}
    output_fields = {
        "product_id",
        "kind_contract",
        "output_role",
        "output_position",
        "member_output_digest",
        "selected_completion",
    }
    for leaf in leaves:
        common = leaf.model_dump(mode="python", exclude=output_fields)
        completion = {
            name: value for name, value in leaf.selected_completion.items() if name != "outputs"
        }
        outputs = grouped.setdefault(leaf.intent_id, {})
        if outputs:
            previous = next(iter(outputs.values()))
            previous_common = previous.model_dump(mode="python", exclude=output_fields)
            previous_completion = {
                name: value
                for name, value in previous.selected_completion.items()
                if name != "outputs"
            }
            if common != previous_common or completion != previous_completion:
                raise ValueError("bounded execution evidence repeats conflicting member custody")
        key = (leaf.output_role, leaf.output_position)
        if key in outputs and outputs[key] != leaf:
            raise ValueError("bounded execution evidence repeats conflicting output custody")
        outputs[key] = leaf
    result: dict[str, tuple[NativeExecutionEvidenceLeaf, WireCompletion]] = {}
    for intent_id, outputs in grouped.items():
        first = next(iter(outputs.values()))
        result[intent_id] = (
            first,
            {
                **first.selected_completion,
                "outputs": [
                    leaf.selected_completion["outputs"][0] for _, leaf in sorted(outputs.items())
                ],
            },
        )
    return result


def execution_evidence_leaf_native_programs(model) -> tuple[ProgramDeclaration, ...]:
    """Project one declared output while retaining its original private CPU proof."""
    from sqlalchemy import BigInteger, Text, and_, cast, column, func, literal, select
    from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by
    from sqlalchemy.types import NullType

    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM
    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        NativeRoutine,
        Parameter,
        Raise,
        Return,
        SelectInto,
        core_relation_row,
        core_variable,
        pg_type,
    )
    from .native_program_registry import ProgramDeclaration

    episodes, requests, intents, receipts, products, outputs, uses, definitions = (
        model.tables[name]
        for name in (
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "kb.data_product",
            "ops.data_derivation_output",
            "ops.demand_use",
            "sem.data_operation_definition",
        )
    )

    def value(name, kind=None):
        return core_variable(name, Text() if kind is None else kind)

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def episode(field):
        return row("episode", episodes, field)

    def request(field):
        return row("request", requests, field)

    def intent(field):
        return row("intent", intents, field)

    def product(field):
        return row("product", products, field)

    def definition(field):
        return row("definition", definitions, field)

    def selected(table, where, name):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(where), (name,), strict=True
        )

    def refuse(condition, message):
        return If(condition, (Raise(message, "23514"),))

    payload = intent("payload")
    evidence = payload["execution_evidence"]
    actual = value("projected", JSONB())
    reply = value("reply", JSONB())
    fence = value("fence", JSONB())
    chosen = value("chosen", JSONB())
    selected_output = value("selected_output", JSONB())
    role, position = value("selected_role"), value("selected_position", BigInteger())
    selected_use = value("selected_use")
    result_field = value("result_field")
    result_fields = definition("support_contract")["result_fields"]
    output_items = (
        func.jsonb_array_elements(payload["outputs"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="declared_output")
    )
    item = output_items.c.value
    batch = (
        func.jsonb_array_elements(reply["members"])
        .table_valued(column("item", JSONB()), with_ordinality="ordinal")
        .render_derived(name="batch")
    )
    batch_item = batch.c.item
    cohort = (
        select(
            func.jsonb_agg(
                aggregate_order_by(batch_item.op("-")(literal("output")), batch.c.ordinal)
            )
        )
        .select_from(batch)
        .scalar_subquery()
    )
    request_record = value("request", NullType())
    scalar_contract = and_(
        func.jsonb_array_length(definition("output_roles")) == 1,
        definition("output_roles")[0]["name"].astext == role,
    )
    parameters = (
        Parameter("episode_id", pg_type("text")),
        Parameter("selected_product", pg_type("text")),
        Parameter("selected_role", pg_type("text")),
        Parameter("selected_position", pg_type("int8")),
        Parameter("selected_use", pg_type("text")),
    )
    program = NativeRoutine(
        "ops",
        "ddo_cpu_execution_leaf",
        parameters=parameters,
        returns=pg_type("jsonb"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                selected(episodes, episodes.c.id == value("episode_id"), "episode"),
                selected(requests, requests.c.id == episode("request_id"), "request"),
                selected(
                    intents,
                    and_(
                        intents.c.id == episode("intent_id"),
                        intents.c.request_id == request("id"),
                        intents.c.generation == episode("generation"),
                    ),
                    "intent",
                ),
                selected(
                    receipts,
                    and_(
                        receipts.c.derivation_id == episode("id"),
                        receipts.c.intent_id == intent("id"),
                    ),
                    "receipt",
                ),
                refuse(
                    and_(
                        selected_use.is_not(None),
                        ~select(1)
                        .select_from(uses)
                        .where(
                            uses.c.id == selected_use,
                            uses.c.derivation_id == episode("id"),
                            uses.c.request_id == episode("request_id"),
                            uses.c.generation == episode("generation"),
                            uses.c.fate == "fulfilled",
                        )
                        .exists(),
                    ),
                    "execution leaf differs from actual selected use",
                ),
                selected(
                    products,
                    and_(
                        products.c.id == value("selected_product"),
                        products.c.project_id == request("project_id"),
                    ),
                    "product",
                ),
                refuse(
                    ~select(1)
                    .select_from(outputs)
                    .where(
                        outputs.c.derivation_id == episode("id"),
                        outputs.c.product_id == product("id"),
                        outputs.c.role == role,
                        outputs.c.position == position,
                        outputs.c.member_id.is_(None),
                        outputs.c.multiplicity == 1,
                    )
                    .exists(),
                    "execution projection requires its exact logical output occurrence",
                ),
                SelectInto(
                    select(item)
                    .select_from(output_items)
                    .where(
                        item["role"].astext == role,
                        cast(item["position"].astext, BigInteger()) == position,
                        item["member_id"].astext.is_(None),
                        cast(item["multiplicity"].astext, BigInteger()) == 1,
                        item["product"]["kind_contract"].astext == product("kind_contract"),
                        item["product"]["body"] == product("canonical_body"),
                    ),
                    ("selected_output",),
                    strict=True,
                ),
                Assign(("request", "release_id"), episode("release_id")),
                Assign(("request", "runtime_id"), episode("runtime_id")),
                Assign(("request", "recipe"), episode("recipe")),
                Assign(("request", "generation"), episode("generation")),
                selected(
                    definitions,
                    and_(
                        definitions.c.release_id == episode("release_id"),
                        definitions.c.operation_id == request("operation_id"),
                    ),
                    "definition",
                ),
                Assign(
                    "projected",
                    cast(func.ops.ddo_cpu_reply_output(request_record, payload), JSONB()),
                ),
                refuse(
                    func.jsonb_typeof(result_fields).is_distinct_from("object"),
                    "execution output lacks its archived result-field projection",
                ),
                If(
                    result_fields != cast(literal("{}"), JSONB()),
                    (
                        Assign("result_field", result_fields[role].astext),
                        refuse(
                            result_field.is_(None),
                            "execution output lacks its exact archived result field",
                        ),
                        Assign(
                            "projected", cast(func.data.ddo_field(actual, result_field), JSONB())
                        ),
                    ),
                    (
                        refuse(
                            ~scalar_contract,
                            "execution output requires its archived single-output contract",
                        ),
                    ),
                ),
                refuse(
                    actual.is_distinct_from(product("canonical_body")),
                    "execution projection differs from its actual selected member output",
                ),
                Assign("reply", cast(func.ops.ddo_cpu_reply_value(payload), JSONB())),
                refuse(
                    reply["version"].astext.is_distinct_from("cpu-authority-batch-reply-1"),
                    "execution evidence leaf requires its actual whole batch reply",
                ),
                Assign(
                    "fence",
                    cast(func.ops.ddo_cpu_original_producer(request_record, payload), JSONB()),
                ),
                SelectInto(
                    select(batch_item, batch.c.ordinal - 1)
                    .select_from(batch)
                    .where(batch_item["producer"] == fence),
                    ("chosen", "member_index"),
                    strict=True,
                ),
                Return(
                    func.jsonb_build_object(
                        "format",
                        "ddo-native-execution-evidence-leaf-v1",
                        "derivation_id",
                        episode("id"),
                        "use_id",
                        selected_use,
                        "issuer_operation",
                        request("operation_id"),
                        "release_id",
                        episode("release_id"),
                        "runtime_id",
                        intent("runtime_id"),
                        "recipe",
                        episode("recipe"),
                        "producer",
                        fence,
                        "intent_id",
                        intent("id"),
                        "intent_payload_digest",
                        intent("payload_digest"),
                        "publication_receipt_id",
                        row("receipt", receipts, "id"),
                        "selected_completion",
                        func.jsonb_set(
                            func.jsonb_set(
                                payload,
                                "{execution_evidence}",
                                evidence.op("-")(literal("cpu_replies")),
                            ),
                            "{outputs}",
                            func.jsonb_build_array(selected_output),
                        ),
                        "product_id",
                        product("id"),
                        "kind_contract",
                        product("kind_contract"),
                        "output_role",
                        role,
                        "output_position",
                        position,
                        "cpu_receipt",
                        evidence["cpu_receipts"][0],
                        "whole_reply_digest",
                        evidence["cpu_receipts"][0]["result_digest"].astext,
                        "member",
                        chosen["member"].astext,
                        "member_ordinal",
                        value("member_index", BigInteger()),
                        "cohort_size",
                        func.jsonb_array_length(reply["members"]),
                        "cohort_membership_digest",
                        func.ops.ddo_digest(cohort),
                        "input_basis_digest",
                        chosen["input_basis_digest"].astext,
                        "member_output_digest",
                        func.ops.ddo_digest(actual),
                        "physical_cohort",
                        "undisclosed",
                        "verification",
                        "native-checked-member-projection",
                    )
                ),
            ),
            tuple(
                Local(name, table)
                for name, table in (
                    ("episode", episodes),
                    ("request", requests),
                    ("intent", intents),
                    ("receipt", receipts),
                    ("product", products),
                    ("definition", definitions),
                )
            )
            + tuple(
                Local(name, pg_type("jsonb"))
                for name in ("reply", "projected", "chosen", "fence", "selected_output")
            )
            + (Local("member_index", pg_type("int8")), Local("result_field", pg_type("text"))),
        ),
    )
    return (
        ProgramDeclaration(
            program,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        ),
    )


def execution_evidence_leaf_native_sql(model) -> str:
    """Render the captured member projector and its existing private ACL projection."""
    from .native_objects import native_privilege_sql, native_sql_script

    return native_sql_script(
        statement
        for declaration in execution_evidence_leaf_native_programs(model)
        for statement in (
            declaration.routine.render(),
            native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
        )
    )
