"""Private authored relationship hypotheses bound to genuine current source cues.

The author asserts the relationship and basis. Computation authenticates selected
source/target/cue custody; it does not claim a provider inferred the relationship.
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass
from typing import Any

from .identity import canonical_bytes

STANDING = "private_authored_source_binding_hypotheses"


def contextual_input_reference(row, *, contribution=False):
    from .contextual_cpu import contextual_input_role
    from .data_operation_model import json_context_meaning
    from .declared_structural_references import DeclaredContributionRef, DeclaredProductRef

    actual = contextual_input_role(row)
    reference = dict(
        product_id=actual.product_id,
        member_id=actual.member_id,
        kind_contract=actual.kind_contract,
        project_id=actual.context.project_id,
        subject=actual.context.subject,
        subject_definition=actual.context.subject_definition,
        original_source=actual.context.original_source,
        analyzed_scope_meaning=json_context_meaning(actual.context.analyzed_scope).decode(),
    )
    if contribution:
        return DeclaredContributionRef(**reference, contribution_id=actual.body["contribution_id"])
    return DeclaredProductRef(**reference)


def project_contextual_witnesses(input_basis, frame_record, *, check_active):
    from corpus_structure.methods.contextual_candidates import retained_occurrences
    from corpus_structure.methods.contextual_embeddings import identity

    from .contextual_cpu import checked_frame_source, contextual_basis_values, contextual_input_role
    from .contextual_links import RelationshipWitness
    from .contextual_operations import admitted_contextual_inventory
    from .declared_structural_references import DeclaredContributionRef
    from .observations import source_value

    check_active()
    roles, context = contextual_basis_values(input_basis)
    if (
        set(roles) != {"source", "query", "inventory", "hypotheses", "cues"}
        or any(len(roles[name]) != 1 for name in ("source", "query", "inventory", "hypotheses"))
        or not roles["cues"]
    ):
        raise ValueError(
            "witness binding requires exact source/query/inventory/authored hypotheses and cues"
        )
    query, hypotheses = roles["query"][0]["body"], roles["hypotheses"][0]["body"]
    if contextual_input_role(roles["query"][0]).context != context:
        raise ValueError("witness query product differs from its exact selected context")
    frame = checked_frame_source(frame_record, contextual_input_role(roles["source"][0]))
    pin = frame.pin.values()
    if query["source_pin"] != pin:
        raise ValueError("witness query differs from its actual source/header")
    inventory = admitted_contextual_inventory(roles["inventory"][0]["body"])
    carrier = DeclaredContributionRef.model_validate(query["carrier"])
    import json

    native = json.loads(frame.native_context)
    nodes = {node.get("self_ref", node.get("pointer")): node for node in native["items"]}
    for pointer, node in tuple(nodes.items()):
        for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
            nodes[f"{pointer}/data/table_cells/{index}"] = cell
    cues = {}
    for row in roles["cues"]:
        if not row["support"] or any(value["kind"] != "computation" for value in row["support"]):
            raise ValueError("witness cues require their original computational support")
        ref = contextual_input_reference(row, contribution=True)
        key = canonical_bytes(ref.model_dump(mode="json"))
        if key in cues:
            raise ValueError("witness cue population repeats an exact source carrier")
        body = row["body"]
        if body["pin"] != pin or not body.get("occurrence_id"):
            raise ValueError("witness cue belongs to another actual source occurrence")
        products, _, _ = retained_occurrences(
            {"contributions": (body,)},
            nodes,
            pin,
            "contextual-authored-cue-validation",
            required_occurrence_ids=(body["occurrence_id"],),
        )
        if len(products) != 1 or any(anchor["precision"] != "exact" for anchor in body["anchors"]):
            raise ValueError("witness cue lacks its actual exact source anchors")
        cues[key] = (ref, body)
    carrier_key = canonical_bytes(carrier.model_dump(mode="json"))
    if carrier_key not in cues or cues[carrier_key][1]["occurrence_id"] != query["occurrence_id"]:
        raise ValueError(
            "witness binding lacks the exact query carrier, including same-span role identity"
        )
    authored = [item for item in roles["hypotheses"][0]["support"] if item["kind"] == "authored"]
    if not authored or not hypotheses["author_assertion"]:
        raise ValueError("witness hypotheses lack their explicit admitted authored attribution")
    target_ids = set(inventory.target_ids)
    selected, seen = [], set()
    for assertion in hypotheses["hypotheses"]:
        if assertion["hypothesis_id"] in seen or assertion["target_id"] not in target_ids:
            raise ValueError(
                "authored witness repeats an assertion or names a target outside selected inventory"
            )
        seen.add(assertion["hypothesis_id"])
        cited = tuple(
            DeclaredContributionRef.model_validate(value) for value in assertion["cue_refs"]
        )
        keys = tuple(canonical_bytes(value.model_dump(mode="json")) for value in cited)
        if (
            len(set(keys)) != len(keys)
            or carrier_key not in keys
            or any(key not in cues for key in keys)
        ):
            raise ValueError(
                "authored witness requires its exact qualifying carrier and selected cue refs"
            )
        witness_id = identity(
            "contextual-authored-witness",
            [
                contextual_input_reference(roles["hypotheses"][0]).model_dump(mode="json"),
                assertion,
                carrier.model_dump(mode="json"),
                inventory.inventory_id,
            ],
        )
        selected.append(
            asdict(
                RelationshipWitness(
                    witness_id,
                    query["occurrence_id"],
                    assertion["target_id"],
                    assertion["relation"],
                    pin["source"],
                    inventory.scope,
                    inventory.effective_version,
                    tuple(value.contribution_id for value in cited),
                    assertion["asserted_basis"],
                    "unassessed",
                )
            )
        )
    check_active()
    return dict(
        standing=STANDING,
        support_state="unassessed",
        author_assertion=hypotheses["author_assertion"],
        authored_support=source_value(authored),
        query_input=contextual_input_reference(roles["query"][0]).model_dump(
            mode="python", exclude_none=True
        ),
        inventory_input=contextual_input_reference(roles["inventory"][0]).model_dump(
            mode="python", exclude_none=True
        ),
        source_input=contextual_input_reference(roles["source"][0]).model_dump(
            mode="python", exclude_none=True
        ),
        hypotheses_input=contextual_input_reference(roles["hypotheses"][0]).model_dump(
            mode="python", exclude_none=True
        ),
        cues_input=[
            cues[key][0].model_dump(mode="python", exclude_none=True) for key in sorted(cues)
        ],
        hypotheses=hypotheses["hypotheses"],
        witnesses=source_value(selected),
    )


def execute_contextual_witness_kernel(
    input_basis: list, frame_record: dict, *, check_active
) -> dict:
    from .data_operation_cpu_basis import cpu_authority_reply

    return cpu_authority_reply(
        input_basis,
        project_contextual_witnesses(input_basis, frame_record, check_active=check_active),
    )


def execute_witness_profile(receiver, source, query, inventory, hypotheses, cues):
    return receiver.execute(source, query, inventory, hypotheses, cues)


@dataclass
class ContextualWitnessPlan:
    prepared: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .contextual_operations import contextual_operation_sources
        from .data_operation_cpu_basis import cpu_authority_value, cpu_input_basis_from_binding
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult
        from .declared_record_sources import DeclaredNativeFrameSource

        if binding is None or binding.subject_context is None:
            raise ValueError("witness binding requires its actual selected source context")
        values = {
            name: arguments.arguments[name]
            for name in ("source", "query", "inventory", "hypotheses", "cues")
        }
        basis = cpu_input_basis_from_binding(
            self.port.identity.recipe,
            binding,
            {name: tuple(value) if name == "cues" else (value,) for name, value in values.items()},
        )
        (source_member,) = next(role.members for role in binding.roles if role.role == "source")
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared,
            values["source"],
            source_member,
            project=binding.subject_context.project_id,
        )
        kernel = execute_contextual_witness_kernel
        bound = inspect.signature(kernel).bind(
            input_basis=basis, frame_record=frame.record, check_active=check_active
        )
        reply = yield from self.port.plan_cpu_reply(
            kernel,
            bound,
            contextual_operation_sources(),
            check_active=check_active,
            execution_owner=execution_owner,
        )
        checked = self.prepared.validate_json(
            "DdoContextualWitnessBindings",
            json_bytes(cpu_authority_value(reply.content, expected_basis=basis)),
        ).model_dump(mode="python", exclude_unset=True)
        return PreparedCallResult(
            checked,
            cpu_execution_evidence=canonical_bytes(reply.execution_receipt.record()),
            cpu_execution_reply=reply.content,
        )


def resolve_witness_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_witnesses import ContextualWitnessOperation

    from .contextual_operations import contextual_operation_sources, contextual_retrieval_assets
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ContextualWitnessOperation.__data_operation__["id"]:
        raise PortRefusal("witness factory differs from its actual declared binding operation")
    receiver = ContextualWitnessOperation(None)
    plan = ContextualWitnessPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_witnesses.ContextualWitnessPlan.plan",
        authorize,
        (contextual_retrieval_assets(),),
        contextual_operation_sources(),
        functions=(
            (
                "corpus_structure.semantic.contextual_witnesses.execute_contextual_witness_kernel",
                execute_contextual_witness_kernel,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
