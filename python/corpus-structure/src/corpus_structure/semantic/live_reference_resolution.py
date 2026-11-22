"""Acquire one reference parent through an exact live selection before opening its body."""

from dataclasses import replace
from typing import Literal, overload

from sqlalchemy import Text, column, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .data_operation_consumers import BoundConsumerSelection
from .data_operation_json import json_loads
from .data_operation_jsonb import json_context_equal, json_context_value
from .data_operation_model import BoundRoleMember, EffectiveDataOperationModel
from .data_operation_storage import AdmittedDataRead, admitted_data_read
from .data_operation_support import support_reference_records
from .data_operation_values import decode_semantic_value
from .reference_resolution import (
    AcquiredReferencePartition,
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)


class LiveReferenceAccess:
    """Separate exact current use from the historical bindings used by the resolver."""

    def __init__(
        self,
        connection,
        model: EffectiveDataOperationModel,
        selection: BoundConsumerSelection,
        *,
        demand_id: str,
        read_id: str,
        trust_snapshot: dict,
        max_partition_bytes: int,
    ):
        if type(max_partition_bytes) is not int or max_partition_bytes <= 0:
            raise ValueError("reference reads require positive partition packet capacity")
        self.connection = connection
        self.model = model
        self.selection = selection
        self.demand_id = demand_id
        self.read_id = read_id
        self.trust_snapshot = trust_snapshot
        self.max_partition_bytes = max_partition_bytes
        self._current: tuple[BoundRoleMember, AdmittedDataRead, object] | None = None

    def authorize(self, binding: ProducingReferenceInput) -> None:
        self._current = None
        # Equality of projected replacement inputs never unlocks the original parent.
        members = tuple(
            member
            for member in self.selection.role(binding.role).members
            if (member.product, member.member, member.kind_contract)
            == (binding.product_id, binding.member_id, binding.kind_contract)
        )
        if len(members) != 1 or members[0].multiplicity != 1:
            raise PermissionError("original reference parent is outside the exact current support")
        (member,) = members
        selection = self.selection.binding
        context = selection.subject_context
        if context is None:
            raise PermissionError("live reference requires its acquired subject context")
        read = admitted_data_read(
            self.connection,
            self.demand_id,
            selection.operation,
            self.trust_snapshot,
            self.model,
            read_id=self.read_id,
            subject=context.subject,
            original_source=context.original_source,
            analyzed_scope=json_loads(context.analyzed_scope),
            selected_pins=[{"product_id": member.product, "member_id": member.member}],
        )
        expected_evidence = {read.admission_evidence} if read.accepted_kind_contracts else set()
        if set(selection.admission_evidence) != expected_evidence:
            raise PermissionError("reference selection belongs to another native read boundary")
        rows = read.relation.c
        acquired = self.connection.execute(
            select(rows.meaning_body)
            .where(
                rows.product == member.product,
                rows.member.is_not_distinct_from(member.member),
                rows.kind_contract == member.kind_contract,
                rows.subject == member.subject,
                rows.subject_definition == member.subject_definition,
                rows.original_source.is_not_distinct_from(member.original_source),
                json_context_equal(
                    rows.analyzed_scope, json_context_value(json_loads(member.analyzed_scope))
                ),
                rows.support_evidence == json_context_value(json_loads(member.support_evidence)),
                rows.support_episodes == list(member.support_episodes),
                rows.support_references == support_reference_records(member.support_references),
                rows.position.is_not_distinct_from(member.position),
                rows.multiplicity == member.multiplicity,
            )
            .limit(2)
        ).fetchall()
        if len(acquired) != 1:
            raise PermissionError("exact original reference parent is no longer available")
        self._current = member, read, acquired[0].meaning_body

    def _authorized(self, product_id: str):
        if self._current is None or self._current[0].product != product_id:
            raise PermissionError("reference body requires exact parent authorization")
        return self._current

    def product(self, product_id: str) -> object:
        pin, _, body = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its whole parent body")
        return decode_semantic_value(body)

    def member(self, product_id: str, member_id: str) -> object:
        pin, read, body = self._authorized(product_id)
        if pin.member == member_id:
            return decode_semantic_value(body)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize another member body")
        selected = self.connection.scalar(
            select(func.ops.data_binding_reference_member(*read.binding_arguments, member_id))
        )
        if selected is None:
            raise KeyError(member_id)
        return decode_semantic_value(selected)

    def partition(
        self, product_id: str, collection: str, partition_key: str
    ) -> AcquiredReferencePartition:
        pin, read, _ = self._authorized(product_id)
        if pin.member is not None:
            raise PermissionError("selected member does not authorize its parent's partitions")
        names = {
            identity.owner
            for identity in self.model.identities
            if identity.domain == "kind" and identity.key == pin.kind_contract
        }
        declarations = tuple(
            json_loads(kind.facts).get("collections", {}).get(collection)
            for kind in self.model.kinds
            if kind.semantic_id in names and kind.category == "class"
        )
        if (
            len(declarations) != 1
            or not declarations[0]
            or declarations[0]["unit"] != "partitioned"
        ):
            raise ValueError("reference requires a declared partitioned collection")
        packets = func.ops.data_binding_partitions(
            *read.binding_arguments, self.max_partition_bytes, collection, partition_key
        ).table_valued(column("product_id", Text()), column("packet", JSONB()))
        returned = self.connection.execute(select(*packets.c).limit(2)).fetchall()
        if len(returned) != 1:
            raise KeyError((collection, partition_key))
        returned_product, packet = returned[0]
        if returned_product is None and packet is None:
            raise ValueError("reference partition exceeds owned packet capacity")
        if returned_product != product_id:
            raise PermissionError("reference partition belongs to another parent")
        return AcquiredReferencePartition(
            packet["partition_digest"], packet["body"], tuple(declarations[0]["address"])
        )


def reference_input_address(pin, *, occurrence_binding=False, occurrence_position=False):
    """The use address an original producing input must still match."""
    return (
        None if occurrence_binding or occurrence_position else pin["position"],
        pin["product_id"],
        pin.get("member_id"),
        pin["multiplicity"],
        pin.get("occurrence_label"),
    )


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only: Literal[True]
) -> ProducingReferenceInput: ...


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, with_binding: Literal[True]
) -> tuple[ProducingReferenceInput, object]: ...


@overload
def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only: bool = False
) -> object: ...


def require_selected_output_reference(
    scope, selected, reference, *, path, metadata_only=False, with_binding=False
):
    """Resolve a declared reference or authenticate its exact whole-product binding."""
    from .detached_reference_resolution import (
        IndexedReferenceAccess,
        reference_input_occurrence,
        reference_role_contracts,
    )

    def row_map(relation, *fields):
        return scope.index.mapping(relation, fields)

    cut = scope.cut.record
    # An ordinary report disclosed through a protected issuer can be selected
    # by its exact support edge even when it is outside the issuer frontier.
    use = row_map("ops.demand_use", "id").get(selected.use_id)
    if use is None or use["fate"] != "fulfilled" or use["derivation_id"] != selected.derivation_id:
        raise ValueError("selected reference lacks its exact fulfilled producing use")
    selection = use["selection"]
    episode = row_map("ops.data_derivation", "id")[selected.derivation_id]
    definitions = row_map("sem.data_operation_definition", "release_id", "operation_id")
    definition = definitions[episode["release_id"], selected.operation_id]
    targets = tuple(
        target
        for target in definition["support_contract"].get("reference_targets", ())
        if target["output_role"] == selected.output["role"]
        and target.get("output_collection") is None
        and target["path"] == path
    )
    if len(targets) != 1:
        raise ValueError("selected reference requires its one declared output target")
    (target,) = targets
    contracts = reference_role_contracts(definition["input_roles"], target)
    role = target["input_role"]
    occurrence_field = target.get("occurrence_field")
    occurrence_binding = target.get("occurrence_binding", False)
    occurrence_position = target.get("occurrence_position", False)
    uses_occurrence = occurrence_field is not None or occurrence_binding or occurrence_position
    current_support = {
        reference_input_address(
            pin, occurrence_binding=occurrence_binding, occurrence_position=occurrence_position
        )
        for pin in selection["inputs"]
        if pin["role"] == role
    }
    originals = tuple(
        scope.index.rows_for(
            "ops.data_derivation_input", derivation_id=selected.derivation_id, role=role
        )
    )
    if not uses_occurrence and len(originals) != 1:
        raise ValueError("selected reference lacks its scalar original input")
    if (reference.role, reference.variant, reference.collection) != (
        role,
        target["variant"],
        target.get("collection"),
    ) or (reference.occurrence is not None) != uses_occurrence:
        raise ValueError("reference differs from its declared slot target")

    access = IndexedReferenceAccess(row_map, cut["project_id"])
    bindings = []
    for original in originals:
        product_id, member_id = original["product_id"], original.get("member_id")
        label = original.get("occurrence_label")
        address = reference_input_address(
            original,
            occurrence_binding=occurrence_binding,
            occurrence_position=occurrence_position,
        )
        if address not in current_support:
            continue
        parent = access.products.get(product_id)
        if parent is None or parent["project_id"] != cut["project_id"]:
            continue
        bound_packet = parent if member_id is None else access.members.get((product_id, member_id))
        if bound_packet is None:
            continue
        kind_contract = bound_packet["kind_contract"]
        if kind_contract not in access.kinds or kind_contract not in contracts:
            raise ValueError("selected reference differs from its declared producing input kind")
        binding = ProducingReferenceInput(
            role, product_id, kind_contract, member_id, multiplicity=original["multiplicity"]
        )
        if occurrence_binding:
            binding = replace(binding, occurrence=label, occurrence_binding=True)
        elif occurrence_position:
            binding = replace(
                binding, occurrence=str(original["position"]), occurrence_position=True
            )
        elif occurrence_field is not None:
            body_field = "canonical_body" if member_id is None else "body"
            if bound_packet.get(body_field) is None:
                continue
            binding = replace(
                binding,
                occurrence=reference_input_occurrence(access, binding, occurrence_field),
                occurrence_field=occurrence_field,
            )
        bindings.append(binding)

    if not bindings:
        raise ValueError("original reference parent is unavailable in the exact selected use")
    producing = ProducingReferenceBindings(selected.derivation_id, tuple(bindings))
    binding = producing.resolve(
        reference,
        occurrence_field=occurrence_field,
        occurrence_binding=occurrence_binding,
        occurrence_position=occurrence_position,
    )
    if metadata_only:
        if reference.variant != "product" or binding.member_id is not None:
            raise ValueError("reference metadata requires its exact whole producing input")
        access.authorize(binding)
        return binding
    value = ReferenceResolver(producing, access).resolve(
        reference,
        ReferenceTarget(
            role,
            target["variant"],
            binding.kind_contract,
            target.get("collection"),
            occurrence_field,
            occurrence_binding,
            occurrence_position,
        ),
    )
    return (binding, value) if with_binding else value
